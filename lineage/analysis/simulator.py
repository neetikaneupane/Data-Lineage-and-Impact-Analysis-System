from lineage.graph.neo4j_client import Neo4jClient


RISKY_PATTERNS = {
    ("VARCHAR",   "NUMERIC"):   ("HIGH",   "string-to-number cast may fail on non-numeric values"),
    ("VARCHAR",   "INTEGER"):   ("HIGH",   "string-to-number cast may fail on non-numeric values"),
    ("NUMERIC",   "VARCHAR"):   ("MEDIUM", "numeric aggregations (SUM, AVG) will break"),
    ("INTEGER",   "VARCHAR"):   ("MEDIUM", "numeric aggregations (SUM, AVG) will break"),
    ("NUMERIC",   "INTEGER"):   ("MEDIUM", "precision loss — decimal values will be truncated"),
    ("FLOAT",     "INTEGER"):   ("MEDIUM", "precision loss — decimal values will be truncated"),
    ("TIMESTAMP", "VARCHAR"):   ("HIGH",   "date functions (DATE, EXTRACT) will break"),
    ("VARCHAR",   "TIMESTAMP"): ("MEDIUM", "string comparisons on this column will break"),
    ("TIMESTAMP", "DATE"):      ("LOW",    "time component will be lost"),
    ("DATE",      "TIMESTAMP"): ("LOW",    "verify downstream date comparisons"),
    ("BOOLEAN",   "INTEGER"):   ("LOW",    "true/false will become 1/0 — verify filters"),
    ("INTEGER",   "BOOLEAN"):   ("MEDIUM", "non 0/1 integers will fail boolean cast"),
}

LAYER_SEVERITY = {
    "raw": 1,
    "stg": 2,
    "dim": 3,
    "fct": 3,
    "mrt": 4,
    "rpt": 5,
}


def _deduplicate_steps(steps: list[dict]) -> list[dict]:
    """Keep each script only at its shallowest depth."""
    seen_scripts = {}
    for step in steps:
        script = step["script"]
        if script not in seen_scripts:
            seen_scripts[script] = step
        else:
            if step["depth"] < seen_scripts[script]["depth"]:
                seen_scripts[script] = step
    return sorted(seen_scripts.values(), key=lambda x: x["depth"])


def _get_layer(table_name: str) -> str:
    for prefix in ["raw_", "stg_", "dim_", "fct_", "mrt_", "rpt_"]:
        if table_name.startswith(prefix):
            return prefix.rstrip("_")
    return "other"


def _severity_score(depth: int, table: str) -> tuple[str, int]:
    layer       = _get_layer(table)
    layer_score = LAYER_SEVERITY.get(layer, 3)
    total       = depth + layer_score
    if total >= 8:
        return ("CRITICAL", total)
    if total >= 6:
        return ("HIGH", total)
    if total >= 4:
        return ("MEDIUM", total)
    return ("LOW", total)


def _safe_execution_order(steps: list[dict]) -> list[str]:
    """Return scripts sorted by depth so shallower scripts run first."""
    seen   = set()
    result = []
    for step in sorted(steps, key=lambda x: x["depth"]):
        if step["script"] not in seen:
            result.append(step["script"])
            seen.add(step["script"])
    return result


def _layer_summary(steps: list[dict]) -> dict:
    summary = {}
    seen_scripts = set()
    for step in steps:
        if step["script"] in seen_scripts:
            continue
        seen_scripts.add(step["script"])
        layer = _get_layer(step["affected_table"])
        if layer not in summary:
            summary[layer] = {"columns": 0, "scripts": 0}
        summary[layer]["scripts"] += 1
    for step in steps:
        layer = _get_layer(step["affected_table"])
        if layer not in summary:
            summary[layer] = {"columns": 0, "scripts": 0}
        summary[layer]["columns"] += 1
    return summary


def simulate_rename(table: str, column: str, new_name: str) -> dict:
    client  = Neo4jClient()
    node_id = f"{table}.{column}"

    rows = client.run(
        """
        MATCH path = (src:Column {id: $id})-[:DERIVES_INTO*]->(tgt:Column)
        RETURN tgt.table AS affected_table,
               tgt.column AS affected_column,
               length(path) AS depth,
               [r IN relationships(path) | r.sql_file] AS via_scripts
        ORDER BY depth ASC
        """,
        {"id": node_id}
    )
    client.close()

    raw_steps = []
    for row in rows:
        last_script = row["via_scripts"][-1] if row["via_scripts"] else "unknown"
        severity, score = _severity_score(row["depth"], row["affected_table"])
        indirect = column in row["affected_column"] and row["affected_column"] != column

        raw_steps.append({
            "depth":            row["depth"],
            "affected_table":   row["affected_table"],
            "affected_column":  row["affected_column"],
            "script":           last_script,
            "action":           f"Rename reference '{column}' → '{new_name}' in {last_script}",
            "change_type":      "rename",
            "severity":         severity,
            "severity_score":   score,
            "indirect_break":   indirect,
            "rollback_action":  f"Revert '{new_name}' → '{column}' in {last_script}"
        })

    steps         = _deduplicate_steps(raw_steps)
    exec_order    = _safe_execution_order(steps)
    layer_summary = _layer_summary(raw_steps)

    return {
        "change_type":   "rename",
        "source":        f"{table}.{column}",
        "new_name":      new_name,
        "steps":         steps,
        "total":         len(raw_steps),
        "exec_order":    exec_order,
        "layer_summary": layer_summary
    }


def simulate_type_change(table: str, column: str, old_type: str, new_type: str) -> dict:
    client  = Neo4jClient()
    node_id = f"{table}.{column}"

    rows = client.run(
        """
        MATCH path = (src:Column {id: $id})-[:DERIVES_INTO*]->(tgt:Column)
        RETURN tgt.table AS affected_table,
               tgt.column AS affected_column,
               length(path) AS depth,
               [r IN relationships(path) | r.sql_file] AS via_scripts
        ORDER BY depth ASC
        """,
        {"id": node_id}
    )
    client.close()

    old_up             = old_type.upper()
    new_up             = new_type.upper()
    risk_level, risk_note = RISKY_PATTERNS.get(
        (old_up, new_up),
        ("MEDIUM", "verify downstream aggregations, filters, and casts")
    )

    raw_steps = []
    for row in rows:
        last_script     = row["via_scripts"][-1] if row["via_scripts"] else "unknown"
        severity, score = _severity_score(row["depth"], row["affected_table"])

        raw_steps.append({
            "depth":           row["depth"],
            "affected_table":  row["affected_table"],
            "affected_column": row["affected_column"],
            "script":          last_script,
            "action":          f"Review {last_script} — {risk_note}",
            "change_type":     "type_change",
            "severity":        severity,
            "severity_score":  score,
            "risk_level":      risk_level,
            "rollback_action": f"Revert type of {column} back to {old_type} in {last_script}"
        })

    steps         = _deduplicate_steps(raw_steps)
    exec_order    = _safe_execution_order(steps)
    layer_summary = _layer_summary(raw_steps)

    return {
        "change_type":   "type_change",
        "source":        f"{table}.{column}",
        "old_type":      old_type,
        "new_type":      new_type,
        "risk_level":    risk_level,
        "risk_note":     risk_note,
        "steps":         steps,
        "total":         len(raw_steps),
        "exec_order":    exec_order,
        "layer_summary": layer_summary
    }


def export_markdown(result: dict, output_path: str):
    lines = []

    if result["change_type"] == "rename":
        lines.append("# Migration Checklist: Column Rename\n")
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| Source | `{result['source']}` |")
        lines.append(f"| Rename to | `{result['new_name']}` |")
        lines.append(f"| Total affected columns | {result['total']} |")
        lines.append(f"| Scripts to update | {len(result['exec_order'])} |\n")
    else:
        lines.append("# Migration Checklist: Type Change\n")
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| Source | `{result['source']}` |")
        lines.append(f"| Type change | `{result['old_type']}` → `{result['new_type']}` |")
        lines.append(f"| Risk level | {result['risk_level']} |")
        lines.append(f"| Risk note | {result['risk_note']} |")
        lines.append(f"| Total affected columns | {result['total']} |")
        lines.append(f"| Scripts to update | {len(result['exec_order'])} |\n")

    # layer summary table
    lines.append("## Impact Summary by Layer\n")
    lines.append("| Layer | Affected Columns | Scripts to Update |")
    lines.append("|-------|-----------------|-------------------|")
    for layer, counts in sorted(result["layer_summary"].items()):
        lines.append(f"| {layer} | {counts['columns']} | {counts['scripts']} |")

    # execution order
    lines.append("\n## Safe Script Execution Order\n")
    for i, script in enumerate(result["exec_order"], 1):
        lines.append(f"{i}. `{script}`")

    # steps
    lines.append("\n## Steps (ordered by dependency depth)\n")
    current_depth = None
    for step in result["steps"]:
        if step["depth"] != current_depth:
            current_depth = step["depth"]
            lines.append(f"\n### Depth {current_depth}\n")
        severity     = step.get("severity", "")
        indirect     = " ⚠️ indirect break" if step.get("indirect_break") else ""
        lines.append(f"- **{step['affected_table']}.{step['affected_column']}** `[{severity}]`{indirect}")
        lines.append(f"  - Script: `{step['script']}`")
        lines.append(f"  - Action: {step['action']}")
        lines.append(f"  - Rollback: {step['rollback_action']}\n")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Migration checklist written to {output_path}")