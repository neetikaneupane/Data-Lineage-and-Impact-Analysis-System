from lineage.analysis.traversal import impact


def test_impact_email_reaches_rpt():
    rows = impact("raw_customers", "email")
    affected_tables = [r["affected_table"] for r in rows]
    assert "rpt_churn_risk" in affected_tables


def test_impact_email_detects_rename():
    rows = impact("raw_customers", "email")
    affected_columns = [r["affected_column"] for r in rows]
    assert "customer_email" in affected_columns


def test_impact_sorted_by_depth():
    rows = impact("raw_customers", "email")
    depths = [r["depth"] for r in rows]
    assert depths == sorted(depths)


def test_impact_empty_for_terminal_column():
    rows = impact("rpt_churn_risk", "email")
    assert rows == []