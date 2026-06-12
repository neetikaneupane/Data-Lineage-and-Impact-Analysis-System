from lineage.graph.neo4j_client import Neo4jClient


def upstream(table: str, column: str) -> list[dict]:
    client = Neo4jClient()
    node_id = f"{table}.{column}"

    result = client.run(
        """
        MATCH path = (src:Column)-[:DERIVES_INTO*]->(tgt:Column {id: $id})
        RETURN src.table AS source_table,
               src.column AS source_column,
               length(path) AS depth,
               [r IN relationships(path) | r.sql_file] AS sql_files
        ORDER BY depth ASC
        """,
        {"id": node_id}
    )

    client.close()
    return result


def downstream(table: str, column: str) -> list[dict]:
    client = Neo4jClient()
    node_id = f"{table}.{column}"

    result = client.run(
        """
        MATCH path = (src:Column {id: $id})-[:DERIVES_INTO*]->(tgt:Column)
        RETURN tgt.table AS target_table,
               tgt.column AS target_column,
               length(path) AS depth,
               [r IN relationships(path) | r.sql_file] AS sql_files
        ORDER BY depth ASC
        """,
        {"id": node_id}
    )

    client.close()
    return result


def impact(table: str, column: str) -> list[dict]:
    client = Neo4jClient()
    node_id = f"{table}.{column}"

    result = client.run(
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
    return result

def dead_columns(exclude_layers: list[str] = None) -> dict:
    client = Neo4jClient()

    if exclude_layers is None:
        exclude_layers = ["rpt_"]

    result = client.run(
        """
        MATCH (c:Column)
        WHERE NOT (c)-[:DERIVES_INTO]->()
        OPTIONAL MATCH path = (root:Column)-[:DERIVES_INTO*]->(c)
        WHERE NOT ()-[:DERIVES_INTO]->(root)
        OPTIONAL MATCH (src)-[r:DERIVES_INTO]->(c)
        RETURN c.table AS table_name,
               c.column AS column_name,
               collect(DISTINCT r.sql_file) AS source_files,
               COALESCE(MAX(length(path)), 0) AS depth
        ORDER BY depth ASC, c.table, c.column
        """
    )

    # collect all column names that exist anywhere downstream
    all_cols = client.run("MATCH (c:Column) RETURN c.column AS column_name")
    all_downstream_columns = set(r["column_name"] for r in all_cols)

    client.close()

    filtered = []
    for row in result:
        table = row["table_name"]
        if any(table.startswith(layer) for layer in exclude_layers):
            continue

        source_files = [f for f in row["source_files"] if f]
        depth        = row["depth"]
        column       = row["column_name"]
        reason       = _classify_dead_column(table, column, source_files, depth, all_downstream_columns)

        filtered.append({
            "table":        table,
            "column":       column,
            "source_files": source_files,
            "depth":        depth,
            "reason":       reason
        })

    summary = {}
    for row in filtered:
        layer = _get_layer(row["table"])
        if layer not in summary:
            summary[layer] = 0
        summary[layer] += 1

    return {
        "columns": filtered,
        "summary": summary,
        "total":   len(filtered)
    }


def _get_layer(table_name: str) -> str:
    for prefix in ["raw_", "stg_", "dim_", "fct_", "mrt_", "rpt_"]:
        if table_name.startswith(prefix):
            return prefix.rstrip("_")
    return "other"

def _classify_dead_column(table: str, column: str, source_files: list, depth: int, all_downstream_columns: set) -> str:
    if not source_files and depth == 0:
        return "orphan"

    # check if a renamed version exists downstream
    for downstream_col in all_downstream_columns:
        if column in downstream_col and downstream_col != column:
            return "renamed"

    return "never_forwarded"

def orphan_columns() -> list[dict]:
    client = Neo4jClient()

    result = client.run(
        """
        MATCH (c:Column)
        WHERE NOT (c)-[:DERIVES_INTO]->()
          AND NOT ()-[:DERIVES_INTO]->(c)
        RETURN c.table AS table_name,
               c.column AS column_name
        ORDER BY c.table, c.column
        """
    )

    client.close()
    return [{"table": r["table_name"], "column": r["column_name"]} for r in result]