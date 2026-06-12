from lineage.graph.neo4j_client import Neo4jClient


def ingest_all(parsed_files: list[dict]):
    client = Neo4jClient()

    print("Clearing existing graph...")
    client.clear_all()

    # first pass — create all table nodes
    for pf in parsed_files:
        if pf["output_table"]:
            client.run(
                "MERGE (t:Table {name: $name})",
                {"name": pf["output_table"]}
            )
        for input_table in pf["input_tables"]:
            client.run(
                "MERGE (t:Table {name: $name})",
                {"name": input_table}
            )

    # second pass — build column-to-table membership map
    # so we know which columns actually belong to which table
    table_columns: dict[str, set] = {}
    for pf in parsed_files:
        output_table = pf["output_table"]
        if not output_table:
            continue
        if output_table not in table_columns:
            table_columns[output_table] = set()
        for mapping in pf["column_mappings"]:
            table_columns[output_table].add(mapping["target_column"])

    # third pass — create edges
    for pf in parsed_files:
        sql_file     = pf["file"]
        output_table = pf["output_table"]
        input_tables = pf["input_tables"]
        mappings     = pf["column_mappings"]

        if not output_table:
            continue

        # table-level edges
        for input_table in input_tables:
            client.run(
                """
                MATCH (src:Table {name: $src})
                MATCH (tgt:Table {name: $tgt})
                MERGE (src)-[:FEEDS {sql_file: $file}]->(tgt)
                """,
                {"src": input_table, "tgt": output_table, "file": sql_file}
            )

        # column-level edges — only connect source column to input table
        # if that table actually owns that column
        for mapping in mappings:
            target_col  = mapping["target_column"]
            source_cols = mapping["source_columns"]

            target_node = f"{output_table}.{target_col}"
            client.run(
                "MERGE (c:Column {id: $id, table: $table, column: $col})",
                {"id": target_node, "table": output_table, "col": target_col}
            )

            for sc in source_cols:
                # only connect to input tables that actually have this column
                valid_sources = [
                    t for t in input_tables
                    if sc in table_columns.get(t, set())
                ]

                # if no valid source found fall back to all input tables
                # this handles raw_ tables which have no prior mappings
                if not valid_sources:
                    valid_sources = input_tables

                for input_table in valid_sources:
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