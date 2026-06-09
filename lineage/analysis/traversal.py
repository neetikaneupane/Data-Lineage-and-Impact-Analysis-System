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

def dead_columns(exclude_layers: list[str] = None) -> list[dict]:
    client = Neo4jClient()

    if exclude_layers is None:
        exclude_layers = ["rpt_"]

    result = client.run(
        """
        MATCH (c:Column)
        WHERE NOT (c)-[:DERIVES_INTO]->()
        RETURN c.table AS table_name, c.column AS column_name
        ORDER BY c.table, c.column
        """
    )

    client.close()

    filtered = []
    for row in result:
        table = row["table_name"]
        if not any(table.startswith(layer) for layer in exclude_layers):
            filtered.append(row)

    return filtered