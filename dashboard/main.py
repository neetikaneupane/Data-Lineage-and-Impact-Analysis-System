from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lineage.graph.neo4j_client import Neo4jClient
from lineage.analysis.traversal import upstream, downstream, impact, dead_columns
from lineage.analysis.simulator import simulate_rename, simulate_type_change
from lineage.analysis.visualizer import export_graph

app       = FastAPI()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    template = templates.get_template("index.html")
    return HTMLResponse(content=template.render(request=request))


@app.get("/api/stats")
def get_stats():
    client = Neo4jClient()

    total_nodes = client.run("MATCH (n) RETURN COUNT(n) AS count")[0]["count"]
    total_edges = client.run("MATCH ()-[r]->() RETURN COUNT(r) AS count")[0]["count"]

    edge_types = client.run("MATCH ()-[r]->() RETURN TYPE(r) AS type, COUNT(r) AS count")

    layer_counts = client.run(
        """
        MATCH (t:Table)
        RETURN
          CASE
            WHEN t.name STARTS WITH 'raw_' THEN 'raw'
            WHEN t.name STARTS WITH 'stg_' THEN 'stg'
            WHEN t.name STARTS WITH 'dim_' THEN 'dim'
            WHEN t.name STARTS WITH 'fct_' THEN 'fct'
            WHEN t.name STARTS WITH 'mrt_' THEN 'mrt'
            WHEN t.name STARTS WITH 'rpt_' THEN 'rpt'
            ELSE 'other'
          END AS layer,
          COUNT(t) AS count
        ORDER BY layer
        """
    )

    dead = dead_columns(exclude_layers=["rpt_", "mrt_"])
    client.close()

    return {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "edge_types":  edge_types,
        "layer_counts": layer_counts,
        "dead_count":  dead["total"]
    }


@app.get("/api/dead")
def get_dead(exclude: str = "rpt_,mrt_"):
    exclude_layers = [e.strip() for e in exclude.split(",") if e.strip()]
    data = dead_columns(exclude_layers=exclude_layers)
    return data


@app.get("/api/lineage/upstream")
def get_upstream(table: str, column: str):
    rows = upstream(table, column)
    return {"table": table, "column": column, "rows": rows}


@app.get("/api/lineage/downstream")
def get_downstream(table: str, column: str):
    rows = downstream(table, column)
    return {"table": table, "column": column, "rows": rows}


@app.get("/api/lineage/impact")
def get_impact(table: str, column: str):
    rows = impact(table, column)
    return {"table": table, "column": column, "rows": rows}


@app.post("/api/simulate/rename")
async def post_simulate_rename(request: Request):
    body   = await request.json()
    table  = body.get("table")
    column = body.get("column")
    new_name = body.get("new_name")
    result = simulate_rename(table, column, new_name)
    return result


@app.post("/api/simulate/type")
async def post_simulate_type(request: Request):
    body     = await request.json()
    table    = body.get("table")
    column   = body.get("column")
    old_type = body.get("old_type")
    new_type = body.get("new_type")
    result   = simulate_type_change(table, column, old_type, new_type)
    return result


@app.get("/api/visualizer")
def get_visualizer(mode: str = "table", focus: str = None):
    output_path = "/tmp/lineage_dashboard.html"
    export_graph(output_path=output_path, mode=mode, focus=focus)
    with open(output_path) as f:
        return HTMLResponse(content=f.read())