import os
import pytest
from lineage.analysis.simulator import (
    simulate_rename,
    simulate_type_change,
    export_markdown,
    _deduplicate_steps,
    _severity_score,
    _safe_execution_order,
    _layer_summary,
    _get_layer,
)


# --- unit tests (no Neo4j needed) ---

def test_get_layer_all_prefixes():
    assert _get_layer("raw_customers")  == "raw"
    assert _get_layer("stg_orders")     == "stg"
    assert _get_layer("dim_customers")  == "dim"
    assert _get_layer("fct_orders")     == "fct"
    assert _get_layer("mrt_revenue")    == "mrt"
    assert _get_layer("rpt_summary")    == "rpt"
    assert _get_layer("unknown_table")  == "other"


def test_severity_score_critical():
    severity, score = _severity_score(3, "rpt_churn_risk")
    assert severity == "CRITICAL"
    assert score == 8  # depth 3 + layer_score 5


def test_severity_score_low():
    severity, score = _severity_score(1, "stg_customers")
    assert severity == "LOW"
    assert score == 3  # depth 1 + layer_score 2


def test_severity_score_medium():
    severity, score = _severity_score(2, "dim_customers")
    assert severity == "MEDIUM"
    assert score == 5  # depth 2 + layer_score 3


def test_deduplicate_keeps_shallowest():
    steps = [
        {"script": "a.sql", "depth": 2, "affected_table": "stg_orders", "affected_column": "id"},
        {"script": "a.sql", "depth": 1, "affected_table": "stg_orders", "affected_column": "id"},
        {"script": "b.sql", "depth": 3, "affected_table": "fct_orders", "affected_column": "id"},
    ]
    result = _deduplicate_steps(steps)
    assert len(result) == 2
    a = next(s for s in result if s["script"] == "a.sql")
    assert a["depth"] == 1


def test_deduplicate_sorted_by_depth():
    steps = [
        {"script": "b.sql", "depth": 3, "affected_table": "fct_orders", "affected_column": "id"},
        {"script": "a.sql", "depth": 1, "affected_table": "stg_orders", "affected_column": "id"},
    ]
    result = _deduplicate_steps(steps)
    assert result[0]["script"] == "a.sql"
    assert result[1]["script"] == "b.sql"


def test_safe_execution_order_no_duplicates():
    steps = [
        {"script": "a.sql", "depth": 1},
        {"script": "b.sql", "depth": 2},
        {"script": "a.sql", "depth": 3},
    ]
    order = _safe_execution_order(steps)
    assert order == ["a.sql", "b.sql"]


def test_safe_execution_order_sorted_by_depth():
    steps = [
        {"script": "c.sql", "depth": 3},
        {"script": "a.sql", "depth": 1},
        {"script": "b.sql", "depth": 2},
    ]
    order = _safe_execution_order(steps)
    assert order == ["a.sql", "b.sql", "c.sql"]


def test_layer_summary_counts():
    steps = [
        {"script": "a.sql", "affected_table": "stg_customers"},
        {"script": "b.sql", "affected_table": "fct_orders"},
        {"script": "b.sql", "affected_table": "fct_payments"},
    ]
    summary = _layer_summary(steps)
    assert summary["stg"]["scripts"] == 1
    assert summary["stg"]["columns"] == 1
    assert summary["fct"]["scripts"] == 1
    assert summary["fct"]["columns"] == 2


# --- integration tests (require Neo4j) ---

def test_simulate_rename_returns_correct_structure():
    result = simulate_rename("raw_customers", "email", "email_address")
    assert result["change_type"] == "rename"
    assert result["source"]      == "raw_customers.email"
    assert result["new_name"]    == "email_address"
    assert result["total"]       > 0
    assert len(result["steps"])  > 0
    assert len(result["exec_order"]) > 0


def test_simulate_rename_steps_sorted_by_depth():
    result = simulate_rename("raw_customers", "email", "email_address")
    depths = [s["depth"] for s in result["steps"]]
    assert depths == sorted(depths)


def test_simulate_rename_exec_order_correct():
    result = simulate_rename("raw_customers", "email", "email_address")
    assert result["exec_order"][0] == "07_stg_customers.sql"
    assert result["exec_order"][-1] == "22_rpt_churn_risk.sql"


def test_simulate_rename_detects_indirect_break():
    result = simulate_rename("raw_customers", "email", "email_address")
    indirect = [s for s in result["steps"] if s.get("indirect_break")]
    assert len(indirect) > 0
    assert any("customer_email" in s["affected_column"] for s in indirect)


def test_simulate_rename_has_rollback_actions():
    result = simulate_rename("raw_customers", "email", "email_address")
    for step in result["steps"]:
        assert "rollback_action" in step
        assert len(step["rollback_action"]) > 0


def test_simulate_rename_no_duplicate_scripts():
    result = simulate_rename("raw_customers", "email", "email_address")
    scripts = [s["script"] for s in result["steps"]]
    assert len(scripts) == len(set(scripts))


def test_simulate_rename_empty_for_dead_column():
    result = simulate_rename("raw_customers", "total_amount", "total_amount_usd")
    assert result["total"] == 0
    assert result["steps"] == []


def test_simulate_type_change_returns_correct_structure():
    result = simulate_type_change("raw_customers", "email", "VARCHAR", "NUMERIC")
    assert result["change_type"] == "type_change"
    assert result["source"]      == "raw_customers.email"
    assert result["old_type"]    == "VARCHAR"
    assert result["new_type"]    == "NUMERIC"
    assert result["risk_level"]  == "HIGH"
    assert result["total"]       > 0


def test_simulate_type_change_known_risky_pattern():
    result = simulate_type_change("raw_customers", "email", "TIMESTAMP", "VARCHAR")
    assert result["risk_level"] == "HIGH"
    assert "date functions" in result["risk_note"]


def test_simulate_type_change_low_risk_pattern():
    result = simulate_type_change("raw_customers", "email", "TIMESTAMP", "DATE")
    assert result["risk_level"] == "LOW"


def test_simulate_type_change_unknown_pattern_fallback():
    result = simulate_type_change("raw_customers", "email", "JSONB", "TEXT")
    assert result["risk_level"] == "MEDIUM"
    assert "verify" in result["risk_note"]


def test_simulate_type_change_has_rollback_actions():
    result = simulate_type_change("raw_customers", "email", "VARCHAR", "NUMERIC")
    for step in result["steps"]:
        assert "rollback_action" in step
        assert "VARCHAR" in step["rollback_action"]


def test_export_markdown_rename(tmp_path):
    result = simulate_rename("raw_customers", "email", "email_address")
    out = str(tmp_path / "rename.md")
    export_markdown(result, out)
    assert os.path.exists(out)
    content = open(out).read()
    assert "Column Rename" in content
    assert "email_address" in content
    assert "Safe Script Execution Order" in content
    assert "Rollback" in content


def test_export_markdown_type_change(tmp_path):
    result = simulate_type_change("raw_customers", "email", "VARCHAR", "NUMERIC")
    out = str(tmp_path / "type.md")
    export_markdown(result, out)
    assert os.path.exists(out)
    content = open(out).read()
    assert "Type Change" in content
    assert "VARCHAR" in content
    assert "NUMERIC" in content
    assert "Impact Summary by Layer" in content