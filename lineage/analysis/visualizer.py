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

COMBINED_UI_HTML = """
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
    z-index: 99999;
    width: 220px;
">
  <div style="margin-bottom: 8px; font-weight: bold; font-size: 14px;">Layer Legend</div>
  <div><span style="color:#e06c75;">&#9679;</span> raw_ &nbsp; source tables</div>
  <div><span style="color:#e5c07b;">&#9679;</span> stg_ &nbsp; staging</div>
  <div><span style="color:#61afef;">&#9679;</span> dim_ / fct_ &nbsp; warehouse</div>
  <div><span style="color:#98c379;">&#9679;</span> mrt_ &nbsp; marts</div>
  <div><span style="color:#c678dd;">&#9679;</span> rpt_ &nbsp; reports</div>
  <div><span style="color:#abb2bf;">&#9679;</span> other</div>
  <hr style="border-color:#444; margin: 10px 0;">
  <div style="margin-bottom: 6px; font-weight: bold;">Search</div>
  <input
    id="searchBox"
    type="text"
    placeholder="e.g. raw_customers"
    style="
        background: #1e1e2e;
        border: 1px solid #555;
        border-radius: 4px;
        color: white;
        padding: 6px 10px;
        font-family: monospace;
        font-size: 12px;
        width: 180px;
        outline: none;
        display: block;
        margin-bottom: 6px;
    "
    oninput="doSearch(this.value)"
  />
  <button onclick="clearSearch()" style="
        background: #555;
        border: none;
        border-radius: 4px;
        color: white;
        padding: 5px 10px;
        cursor: pointer;
        font-family: monospace;
        font-size: 12px;
        width: 100%;
  ">Clear</button>
</div>

<div id="detailPanel" style="
    display: none;
    position: fixed;
    top: 20px;
    right: 20px;
    background: #2a2a3e;
    border: 1px solid #444;
    border-radius: 8px;
    padding: 14px 18px;
    font-family: monospace;
    font-size: 13px;
    color: white;
    z-index: 99999;
    width: 260px;
    line-height: 1.8;
">
  <div style="font-weight: bold; font-size: 14px; margin-bottom: 8px;">Node Detail</div>
  <div id="detailContent"></div>
  <button onclick="document.getElementById('detailPanel').style.display='none'" style="
        margin-top: 10px;
        background: #555;
        border: none;
        border-radius: 4px;
        color: white;
        padding: 5px 10px;
        cursor: pointer;
        font-family: monospace;
        font-size: 12px;
        width: 100%;
  ">Close</button>
</div>

<script type="text/javascript">
function doSearch(val) {
    var query = val.toLowerCase().trim();
    if (!query) { clearSearch(); return; }
    var allNodes = network.body.data.nodes.get();
    var updates = [];
    allNodes.forEach(function(node) {
        var label = (node.title || node.id || "").toLowerCase();
        var match = label.indexOf(query) !== -1;
        updates.push({
            id:    node.id,
            color: match ? {background:"#ffffff",border:"#ffffff"} : {background:"#2a2a3e",border:"#2a2a3e"},
            font:  match ? {color:"#000000",size:16} : {color:"#2a2a3e",size:10},
            size:  match ? 28 : 6
        });
    });
    network.body.data.nodes.update(updates);
}

function clearSearch() {
    document.getElementById("searchBox").value = "";
    var allNodes = network.body.data.nodes.get();
    var updates = [];
    allNodes.forEach(function(node) {
        updates.push({
            id:    node.id,
            color: node.color,
            font:  {color:"white", size:14},
            size:  node.size || 15
        });
    });
    network.body.data.nodes.update(updates);
}

network.on("click", function(params) {
    if (params.nodes.length === 0) return;

    var nodeId   = params.nodes[0];
    var nodeData = network.body.data.nodes.get(nodeId);
    var allEdges = network.body.data.edges.get();

    var upstream   = 0;
    var downstream = 0;
    var scripts    = new Set();

    allEdges.forEach(function(edge) {
        if (edge.to === nodeId)   { upstream++;   if (edge.title) scripts.add(edge.title); }
        if (edge.from === nodeId) { downstream++; if (edge.title) scripts.add(edge.title); }
    });

    var name  = nodeId;
    var layer = "other";
    if (name.startsWith("raw_"))             layer = "raw (source)";
    else if (name.startsWith("stg_"))        layer = "stg (staging)";
    else if (name.startsWith("dim_"))        layer = "dim (warehouse)";
    else if (name.startsWith("fct_"))        layer = "fct (warehouse)";
    else if (name.startsWith("mrt_"))        layer = "mrt (mart)";
    else if (name.startsWith("rpt_"))        layer = "rpt (report)";

    var scriptList = Array.from(scripts).map(function(s) {
        return "<div style='color:#98c379; font-size:11px;'>" + s + "</div>";
    }).join("");

    document.getElementById("detailContent").innerHTML =
        "<div><b>Name:</b> " + name + "</div>" +
        "<div><b>Layer:</b> " + layer + "</div>" +
        "<div><b>Upstream edges:</b> " + upstream + "</div>" +
        "<div><b>Downstream edges:</b> " + downstream + "</div>" +
        "<div style='margin-top:6px;'><b>SQL files:</b></div>" +
        (scriptList || "<div style='color:#888;'>none</div>");

    document.getElementById("detailPanel").style.display = "block";
});
</script>
"""


def _inject_ui(output_path: str):
    with open(output_path, "r") as f:
        html = f.read()

    # fix mynetwork stacking context so our UI panel renders on top
    html = html.replace(
        "position: relative;",
        "position: relative; z-index: 0;",
        1
    )

    html = html.replace("</body>", f"{COMBINED_UI_HTML}</body>", 1)

    with open(output_path, "w") as f:
        f.write(html)

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
    _inject_ui(output_path)


def _export_column_graph(client: Neo4jClient, output_path: str):
    net = Network(
        height="900px",
        width="100%",
        directed=True,
        bgcolor="#1e1e2e",
        font_color="white"
    )
    net.set_options("""
    {
        "physics": {
            "barnesHut": {
                "gravitationalConstant": -12000,
                "centralGravity": 0.1,
                "springLength": 120,
                "springConstant": 0.08,
                "damping": 0.09
            }
        },
        "edges": {
            "smooth": {
                "type": "curvedCW",
                "roundness": 0.2
            }
        }
    }
    """)

    rows = client.run(
        """
        MATCH (src:Column)-[r:DERIVES_INTO]->(tgt:Column)
        RETURN src.id AS src, src.table AS src_table,
               tgt.id AS tgt, tgt.table AS tgt_table,
               r.sql_file AS file
        """
    )

    nodes = set()
    for row in rows:
        src       = row["src"]
        tgt       = row["tgt"]
        src_table = row["src_table"]
        tgt_table = row["tgt_table"]
        file      = row["file"]

        if src not in nodes:
            net.add_node(
                src,
                label="",
                title=src,
                color=_node_color(src_table),
                size=10,
                group=src_table
            )
            nodes.add(src)
        if tgt not in nodes:
            net.add_node(
                tgt,
                label="",
                title=tgt,
                color=_node_color(tgt_table),
                size=10,
                group=tgt_table
            )
            nodes.add(tgt)

        net.add_edge(src, tgt, title=file, color="#444444")

    net.save_graph(output_path)
    _inject_ui(output_path)

def _node_color(name: str) -> str:
    for prefix, color in LAYER_COLORS.items():
        if name.startswith(prefix):
            return color
    return DEFAULT_COLOR