from pyvis.network import Network
from lineage.graph.neo4j_client import Neo4jClient


LAYER_COLORS = {
    "raw_":  "#e06c75",
    "stg_":  "#e5c07b",
    "dim_":  "#61afef",
    "fct_":  "#61afef",
    "mrt_":  "#98c379",
    "rpt_":  "#c678dd",
}
DEFAULT_COLOR = "#abb2bf"

LEGEND_HTML = """
<div style="
    position: fixed;
    top: 20px;
    left: 20px;
    background: #2a2a3e;
    border: 1px solid #444;
    border-radius: 8px;
    padding: 14px 18px;
    font-family: monospace;
    font-size: 13px;
    color: white;
    z-index: 9999;
">
  <div style="margin-bottom: 8px; font-weight: bold; font-size: 14px;">Layer Legend</div>
  <div><span style="color:#e06c75;">&#9679;</span> raw_   &nbsp; source tables</div>
  <div><span style="color:#e5c07b;">&#9679;</span> stg_   &nbsp; staging</div>
  <div><span style="color:#61afef;">&#9679;</span> dim_ / fct_  &nbsp; warehouse</div>
  <div><span style="color:#98c379;">&#9679;</span> mrt_   &nbsp; marts</div>
  <div><span style="color:#c678dd;">&#9679;</span> rpt_   &nbsp; reports</div>
  <div><span style="color:#abb2bf;">&#9679;</span> other</div>
</div>
"""


def export_graph(output_path: str = "lineage_graph.html", mode: str = "table"):
    client = Neo4jClient()

    if mode == "table":
        _export_table_graph(client, output_path)
    elif mode == "column":
        _export_column_graph(client, output_path)

    client.close()
    print(f"Graph exported to {output_path}")


def _inject_legend(output_path: str):
    with open(output_path, "r") as f:
        html = f.read()
    html = html.replace("<body>", f"<body>{LEGEND_HTML}", 1)
    with open(output_path, "w") as f:
        f.write(html)


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
    _inject_legend(output_path)


def _export_column_graph(client: Neo4jClient, output_path: str):
    net = Network(
        height="900px",
        width="100%",
        directed=True,
        bgcolor="#1e1e2e",
        font_color="white"
    )
    net.barnes_hut(
        gravity=-12000,
        central_gravity=0.1,
        spring_length=250,
        spring_strength=0.01,
        damping=0.09
    )

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
            net.add_node(
                src,
                label="",
                title=src,
                color=_node_color(src_table),
                size=10
            )
            nodes.add(src)
        if tgt not in nodes:
            net.add_node(
                tgt,
                label="",
                title=tgt,
                color=_node_color(tgt_table),
                size=10
            )
            nodes.add(tgt)

        net.add_edge(src, tgt, title=file, color="#444444")

    net.save_graph(output_path)
    _inject_legend(output_path)

def _node_color(name: str) -> str:
    for prefix, color in LAYER_COLORS.items():
        if name.startswith(prefix):
            return color
    return DEFAULT_COLOR