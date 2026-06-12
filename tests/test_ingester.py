import pytest
from lineage.graph.ingester import ingest_all, ingest_python_lineage
from lineage.graph.neo4j_client import Neo4jClient


@pytest.fixture(autouse=True)
def clean_graph():
    """Clear the graph before each test and restore full data after."""
    client = Neo4jClient()
    client.clear_all()
    yield
    client.clear_all()
    client.close()


@pytest.fixture
def client():
    c = Neo4jClient()
    yield c
    c.close()


# --- ingest_all tests ---

def test_ingest_creates_table_nodes(client):
    parsed = [
        {
            "file": "test.sql",
            "output_table": "orders",
            "input_tables": ["customers"],
            "column_mappings": []
        }
    ]
    ingest_all(parsed)
    result = client.run("MATCH (t:Table) RETURN t.name AS name")
    names = {r["name"] for r in result}
    assert "orders" in names
    assert "customers" in names


def test_ingest_creates_feeds_edge(client):
    parsed = [
        {
            "file": "test.sql",
            "output_table": "orders",
            "input_tables": ["customers"],
            "column_mappings": []
        }
    ]
    ingest_all(parsed)
    result = client.run(
        """
        MATCH (src:Table {name: 'customers'})-[r:FEEDS]->(tgt:Table {name: 'orders'})
        RETURN r.sql_file AS file
        """
    )
    assert len(result) == 1
    assert result[0]["file"] == "test.sql"


def test_ingest_creates_column_nodes(client):
    parsed = [
        {
            "file": "test.sql",
            "output_table": "stg_orders",
            "input_tables": ["raw_orders"],
            "column_mappings": [
                {"target_column": "order_id", "source_columns": ["order_id"]}
            ]
        }
    ]
    ingest_all(parsed)
    result = client.run("MATCH (c:Column) RETURN c.id AS id")
    ids = {r["id"] for r in result}
    assert "stg_orders.order_id" in ids
    assert "raw_orders.order_id" in ids


def test_ingest_creates_derives_into_edge(client):
    parsed = [
        {
            "file": "test.sql",
            "output_table": "stg_orders",
            "input_tables": ["raw_orders"],
            "column_mappings": [
                {"target_column": "order_id", "source_columns": ["order_id"]}
            ]
        }
    ]
    ingest_all(parsed)
    result = client.run(
        """
        MATCH (src:Column {id: 'raw_orders.order_id'})-[r:DERIVES_INTO]->(tgt:Column {id: 'stg_orders.order_id'})
        RETURN r.sql_file AS file
        """
    )
    assert len(result) == 1
    assert result[0]["file"] == "test.sql"


def test_ingest_skips_file_with_no_output_table(client):
    parsed = [
        {
            "file": "raw.sql",
            "output_table": None,
            "input_tables": [],
            "column_mappings": []
        }
    ]
    ingest_all(parsed)
    result = client.run("MATCH (t:Table) RETURN COUNT(t) AS count")
    assert result[0]["count"] == 0


def test_ingest_column_not_linked_to_wrong_table(client):
    """Column order_id should only link to raw_orders, not raw_customers."""
    parsed = [
        {
            "file": "01_raw_orders.sql",
            "output_table": "raw_orders",
            "input_tables": [],
            "column_mappings": [
                {"target_column": "order_id", "source_columns": ["order_id"]}
            ]
        },
        {
            "file": "02_stg_orders.sql",
            "output_table": "stg_orders",
            "input_tables": ["raw_orders", "raw_customers"],
            "column_mappings": [
                {"target_column": "order_id", "source_columns": ["order_id"]}
            ]
        }
    ]
    ingest_all(parsed)
    result = client.run(
        """
        MATCH (src:Column)-[:DERIVES_INTO]->(tgt:Column {id: 'stg_orders.order_id'})
        RETURN src.id AS src_id
        """
    )
    src_ids = {r["src_id"] for r in result}
    assert "raw_orders.order_id" in src_ids
    assert "raw_customers.order_id" not in src_ids


# --- ingest_python_lineage tests ---

def test_ingest_python_creates_file_nodes(client):
    parsed = [
        {
            "file": "load.py",
            "inputs":  ["data/raw/orders.csv"],
            "outputs": ["data/processed/orders.parquet"]
        }
    ]
    ingest_python_lineage(parsed)
    result = client.run("MATCH (f:File) RETURN f.path AS path")
    paths = {r["path"] for r in result}
    assert "data/raw/orders.csv" in paths
    assert "data/processed/orders.parquet" in paths


def test_ingest_python_creates_processed_into_edge(client):
    parsed = [
        {
            "file": "load.py",
            "inputs":  ["data/raw/orders.csv"],
            "outputs": ["data/processed/orders.parquet"]
        }
    ]
    ingest_python_lineage(parsed)
    result = client.run(
        """
        MATCH (src:File {path: 'data/raw/orders.csv'})-[r:PROCESSED_INTO]->(tgt:File {path: 'data/processed/orders.parquet'})
        RETURN r.py_file AS file
        """
    )
    assert len(result) == 1
    assert result[0]["file"] == "load.py"


def test_ingest_python_multiple_inputs(client):
    parsed = [
        {
            "file": "merge.py",
            "inputs":  ["data/raw/a.csv", "data/raw/b.csv"],
            "outputs": ["data/processed/merged.parquet"]
        }
    ]
    ingest_python_lineage(parsed)
    result = client.run(
        """
        MATCH (src:File)-[:PROCESSED_INTO]->(tgt:File {path: 'data/processed/merged.parquet'})
        RETURN src.path AS path
        """
    )
    paths = {r["path"] for r in result}
    assert "data/raw/a.csv" in paths
    assert "data/raw/b.csv" in paths