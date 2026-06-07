from lineage.graph.neo4j_client import Neo4jClient


def ingest_all(parsed_files: list[dict]):
    client = Neo4jClient()

    print("Clearing existing graph...")
    client.clear_all()

    for pf in parsed_files:
        sql_file     = pf["file"]
        output_table = pf["output_table"]
        input_tables = pf["input_tables"]
        mappings     = pf["column_mappings"]

        if not output_table:
            continue

        # create output table node
        client.run(
            "MERGE (t:Table {name: $name})",
            {"name": output_table}
        )

        # create table-level edges from each input table
        for input_table in input_tables:
            client.run(
                "MERGE (t:Table {name: $name})",
                {"name": input_table}
            )
            client.run(
                """
                MATCH (src:Table {name: $src})
                MATCH (tgt:Table {name: $tgt})
                MERGE (src)-[:FEEDS {sql_file: $file}]->(tgt)
                """,
                {"src": input_table, "tgt": output_table, "file": sql_file}
            )

        # create column nodes and column-level edges
        for mapping in mappings:
            target_col = mapping["target_column"]
            source_cols = mapping["source_columns"]

            target_node = f"{output_table}.{target_col}"
            client.run(
                "MERGE (c:Column {id: $id, table: $table, column: $col})",
                {"id": target_node, "table": output_table, "col": target_col}
            )

            for sc in source_cols:
                for input_table in input_tables:
                    source_node = f"{input_table}.{sc}"
                    client.run(
                        "MERGE (c:Column {id: $id, table: $table, column: $col})",
                        {"id": source_node, "table": input_table, "col": sc}
                    )
                    client.run(
                        """
                        MATCH (src:Column {id: $src})
                        MATCH (tgt:Column {id: $tgt})
                        MERGE (src)-[:DERIVES_INTO {sql_file: $file}]->(tgt)
                        """,
                        {"src": source_node, "tgt": target_node, "file": sql_file}
                    )

    client.close()
    print(f"Ingested {len(parsed_files)} files into Neo4j.")

def ingest_python_lineage(parsed_files: list[dict]):
    client = Neo4jClient()

    for pf in parsed_files:
        py_file = pf["file"]
        inputs  = pf["inputs"]
        outputs = pf["outputs"]

        for path in inputs:
            client.run(
                "MERGE (f:File {path: $path})",
                {"path": path}
            )

        for path in outputs:
            client.run(
                "MERGE (f:File {path: $path})",
                {"path": path}
            )

        # input file -> output file edges
        for src in inputs:
            for tgt in outputs:
                client.run(
                    """
                    MATCH (src:File {path: $src})
                    MATCH (tgt:File {path: $tgt})
                    MERGE (src)-[:PROCESSED_INTO {py_file: $file}]->(tgt)
                    """,
                    {"src": src, "tgt": tgt, "file": py_file}
                )

        # connect output files to SQL table nodes where names overlap
        for path in outputs:
            filename = path.split("/")[-1].split(".")[0]
            client.run(
                """
                MATCH (f:File {path: $path})
                MATCH (t:Table {name: $name})
                MERGE (f)-[:LANDS_INTO]->(t)
                """,
                {"path": path, "name": filename}
            )

    client.close()
    print(f"Ingested {len(parsed_files)} Python files into Neo4j.")