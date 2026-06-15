from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lineage.graph.neo4j_client import Neo4jClient
from lineage.analysis.traversal import upstream, downstream, impact, dead_columns
from lineage.analysis.simulator import simulate_rename, simulate_type_change
from lineage.analysis.visualizer import export_graph

app          = FastAPI()
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
app.mount("/static", StaticFiles(directory=TEMPLATES_DIR), name="static")
templates    = Jinja2Templates(directory=TEMPLATES_DIR)


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

@app.get("/api/tables")
def get_tables():
    client = Neo4jClient()
    result = client.run("MATCH (t:Table) RETURN t.name AS name ORDER BY t.name")
    client.close()
    return {"tables": [r["name"] for r in result]}

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

@app.get("/api/table/lineage")
def get_table_lineage(table: str):
    client = Neo4jClient()

    upstream_tables = client.run(
        """
        MATCH (src:Table)-[:FEEDS]->(tgt:Table {name: $name})
        RETURN src.name AS source_table
        """,
        {"name": table}
    )

    downstream_tables = client.run(
        """
        MATCH (src:Table {name: $name})-[:FEEDS]->(tgt:Table)
        RETURN tgt.name AS target_table
        """,
        {"name": table}
    )

    columns = client.run(
        """
        MATCH (c:Column {table: $name})
        RETURN c.column AS column_name
        ORDER BY c.column
        """,
        {"name": table}
    )

    client.close()
    return {
        "table": table,
        "upstream":   [r["source_table"] for r in upstream_tables],
        "downstream": [r["target_table"] for r in downstream_tables],
        "columns":    [r["column_name"] for r in columns]
    }


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
    

@app.get("/api/search/column")
def search_column(q: str):
    client = Neo4jClient()

    result = client.run(
        """
        MATCH (c:Column)
        WHERE toLower(c.column) CONTAINS toLower($q)
        WITH c.column AS column_name, c.table AS table_name
        OPTIONAL MATCH (src:Column {column: column_name, table: table_name})-[:DERIVES_INTO]->()
        WITH column_name, table_name, COUNT(src) AS downstream_count
        OPTIONAL MATCH ()-[:DERIVES_INTO]->(tgt:Column {column: column_name, table: table_name})
        RETURN column_name, table_name,
               COUNT(tgt) AS upstream_count,
               downstream_count
        ORDER BY table_name, column_name
        """,
        {"q": q}
    )

    client.close()
    return {"query": q, "results": result, "total": len(result)}

@app.get("/api/broken-pipeline")
def get_broken_pipeline():
    client = Neo4jClient()

    result = client.run(
        """
        MATCH (src:Table)-[r:FEEDS]->(tgt:Table)
        WHERE NOT ()-[:FEEDS]->(src)
          AND NOT src.name STARTS WITH 'raw_'
        RETURN src.name AS missing_table,
               collect(DISTINCT tgt.name) AS referenced_by,
               collect(DISTINCT r.sql_file) AS in_scripts
        ORDER BY src.name
        """
    )

    # also find tables referenced in FEEDS that have no column nodes
    orphan_tables = client.run(
        """
        MATCH (t:Table)
        WHERE NOT (t)-[:FEEDS]->()
          AND NOT ()-[:FEEDS]->(t)
        RETURN t.name AS isolated_table
        ORDER BY t.name
        """
    )

    client.close()
    return {
        "phantom_sources": result,
        "isolated_tables": [r["isolated_table"] for r in orphan_tables],
        "total_phantoms":  len(result),
        "total_isolated":  len(orphan_tables)
    }

@app.get("/api/health")
def get_health():
    client = Neo4jClient()

    tables = client.run("MATCH (t:Table) RETURN t.name AS name ORDER BY t.name")

    scores = []
    for row in tables:
        table = row["name"]

        # total columns
        total_cols = client.run(
            "MATCH (c:Column {table: $t}) RETURN COUNT(c) AS count",
            {"t": table}
        )[0]["count"]

        # dead columns
        dead_cols = client.run(
            """
            MATCH (c:Column {table: $t})
            WHERE NOT (c)-[:DERIVES_INTO]->()
            RETURN COUNT(c) AS count
            """,
            {"t": table}
        )[0]["count"]

        # downstream table count
        downstream = client.run(
            """
            MATCH (t:Table {name: $t})-[:FEEDS*]->(d:Table)
            RETURN COUNT(DISTINCT d) AS count
            """,
            {"t": table}
        )[0]["count"]

        # upstream table count
        upstream = client.run(
            """
            MATCH (u:Table)-[:FEEDS*]->(t:Table {name: $name})
            RETURN COUNT(DISTINCT u) AS count
            """,
            {"name": table}
        )[0]["count"]

        # compute score
        dead_ratio   = dead_cols / total_cols if total_cols > 0 else 0
        dead_penalty = dead_ratio * 50

        # more downstream dependents = more critical = bigger penalty for issues
        criticality_penalty = min(dead_ratio * downstream * 3, 30)

        # isolation penalty
        isolation_penalty = 10 if upstream == 0 and downstream == 0 else 0

        score = max(0, round(100 - dead_penalty - criticality_penalty - isolation_penalty))

        if score >= 90:   grade = "A"
        elif score >= 75: grade = "B"
        elif score >= 60: grade = "C"
        elif score >= 40: grade = "D"
        else:             grade = "F"

        layer = "other"
        for prefix in ["raw_","stg_","dim_","fct_","mrt_","rpt_"]:
            if table.startswith(prefix):
                layer = prefix.rstrip("_")
                break

        scores.append({
            "table":       table,
            "layer":       layer,
            "score":       score,
            "grade":       grade,
            "total_cols":  total_cols,
            "dead_cols":   dead_cols,
            "dead_ratio":  round(dead_ratio * 100),
            "downstream":  downstream,
            "upstream":    upstream,
        })

    client.close()

    scores.sort(key=lambda x: x["score"])
    avg = round(sum(s["score"] for s in scores) / len(scores)) if scores else 0

    grade_counts = {"A":0,"B":0,"C":0,"D":0,"F":0}
    for s in scores:
        grade_counts[s["grade"]] += 1

    return {
        "scores":       scores,
        "average_score": avg,
        "grade_counts": grade_counts,
        "total_tables": len(scores)
    }