from lineage.graph.neo4j_client import Neo4jClient


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

    steps = []
    for row in rows:
        last_script = row["via_scripts"][-1] if row["via_scripts"] else "unknown"
        steps.append({
            "depth":          row["depth"],
            "affected_table": row["affected_table"],
            "affected_column": row["affected_column"],
            "script":         last_script,
            "action":         f"Rename reference to '{column}' → '{new_name}' in {last_script}",
            "change_type":    "rename"
        })

    return {
        "change_type": "rename",
        "source":      f"{table}.{column}",
        "new_name":    new_name,
        "steps":       steps,
        "total":       len(steps)
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

    # scripts that are likely to break on type changes
    RISKY_PATTERNS = {
        ("VARCHAR", "NUMERIC"): "string-to-number cast may fail on non-numeric values",
        ("NUMERIC", "VARCHAR"): "numeric aggregations (SUM, AVG) will break",
        ("TIMESTAMP", "VARCHAR"): "date functions (DATE, EXTRACT) will break",
        ("VARCHAR", "TIMESTAMP"): "string comparisons on this column will break",
    }

    old_up = old_type.upper()
    new_up = new_type.upper()
    risk_note = RISKY_PATTERNS.get((old_up, new_up), "verify downstream aggregations and filters")

    steps = []
    for row in rows:
        last_script = row["via_scripts"][-1] if row["via_scripts"] else "unknown"
        steps.append({
            "depth":           row["depth"],
            "affected_table":  row["affected_table"],
            "affected_column": row["affected_column"],
            "script":          last_script,
            "action":          f"Review {last_script} — {risk_note}",
            "change_type":     "type_change"
        })

    return {
        "change_type": "type_change",
        "source":      f"{table}.{column}",
        "old_type":    old_type,
        "new_type":    new_type,
        "risk_note":   risk_note,
        "steps":       steps,
        "total":       len(steps)
    }


def export_markdown(result: dict, output_path: str):
    lines = []

    if result["change_type"] == "rename":
        lines.append(f"# Migration Checklist: Column Rename\n")
        lines.append(f"**Source:** `{result['source']}`  ")
        lines.append(f"**Rename to:** `{result['new_name']}`  ")
    else:
        lines.append(f"# Migration Checklist: Type Change\n")
        lines.append(f"**Source:** `{result['source']}`  ")
        lines.append(f"**Type change:** `{result['old_type']}` → `{result['new_type']}`  ")
        lines.append(f"**Risk:** {result['risk_note']}  ")

    lines.append(f"**Total affected:** {result['total']} downstream columns  \n")
    lines.append(f"---\n")
    lines.append(f"## Steps (ordered by dependency depth)\n")

    current_depth = None
    for step in result["steps"]:
        if step["depth"] != current_depth:
            current_depth = step["depth"]
            lines.append(f"\n### Depth {current_depth}\n")
        lines.append(f"- **{step['affected_table']}.{step['affected_column']}**")
        lines.append(f"  - Script: `{step['script']}`")
        lines.append(f"  - Action: {step['action']}\n")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Migration checklist written to {output_path}")