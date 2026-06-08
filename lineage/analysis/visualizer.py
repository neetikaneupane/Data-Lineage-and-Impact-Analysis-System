from pyvis.network import Network
from lineage.graph.neo4j_client import Neo4jClient


def export_graph(output_path: str = "lineage_graph.html", mode: str = "table"):
    client = Neo4jClient()

    if mode == "table":
        _export_table_graph(client, output_path)
    elif mode == "column":
        _export_column_graph(client, output_path)

    client.close()
    print(f"Graph exported to {output_path}")


def _export_table_graph(client: Neo4jClient, output_path: str):
    net = Network(
        height="900px",
        width="100%",
        directed=True,
        bgcolor="#1e1e2e",
        font_color="white"
    )
    net.barnes_hut(gravity=-5000, central_gravity=0.3, spring_length=200)

    rows = client.run(
        """
        MATCH (src:Table)-[r:FEEDS]->(tgt:Table)
        RETURN src.name AS src, tgt.name AS tgt, r.sql_file AS file
        """
    )

    nodes = set()
    for row in rows:
        src  = row["src"]
        tgt  = row["tgt"]
        file = row["file"]

        if src not in nodes:
            net.add_node(src, label=src, color=_node_color(src), size=20, title=src)
            nodes.add(src)
        if tgt not in nodes:
            net.add_node(tgt, label=tgt, color=_node_color(tgt), size=20, title=tgt)
            nodes.add(tgt)

        net.add_edge(src, tgt, title=file, color="#888888")

    net.save_graph(output_path)


def _export_column_graph(client: Neo4jClient, output_path: str):
    net = Network(
        height="900px",
        width="100%",
        directed=True,
        bgcolor="#1e1e2e",
        font_color="white"
    )
    net.barnes_hut(gravity=-8000, central_gravity=0.2, spring_length=150)

    rows = client.run(
        """
        MATCH (src:Column)-[r:DERIVES_INTO]->(tgt:Column)
        RETURN src.id AS src, tgt.id AS tgt, r.sql_file AS file
        """
    )

    nodes = set()
    for row in rows:
        src  = row["src"]
        tgt  = row["tgt"]
        file = row["file"]

        src_table = src.split(".")[0]
        tgt_table = tgt.split(".")[0]

        if src not in nodes:
            net.add_node(src, label=src, color=_node_color(src_table), size=15, title=src)
            nodes.add(src)
        if tgt not in nodes:
            net.add_node(tgt, label=tgt, color=_node_color(tgt_table), size=15, title=tgt)
            nodes.add(tgt)

        net.add_edge(src, tgt, title=file, color="#555555")

    net.save_graph(output_path)


def _node_color(name: str) -> str:
    if name.startswith("raw_"):
        return "#e06c75"
    if name.startswith("stg_"):
        return "#e5c07b"
    if name.startswith("dim_") or name.startswith("fct_"):
        return "#61afef"
    if name.startswith("mrt_"):
        return "#98c379"
    if name.startswith("rpt_"):
        return "#c678dd"
    return "#abb2bf"