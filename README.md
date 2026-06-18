# Data Lineage & Impact Analysis System

A Python tool that parses SQL and Python scripts, extracts column-level lineage, stores it as a directed graph in Neo4j, and provides a CLI and interactive dashboard to answer questions like:

> *"If I rename `raw_customers.email`, which downstream tables, columns, and scripts break and in what order do I fix them?"*

Built from scratch without relying on existing lineage tools like OpenLineage.

---

## Demo

```
$ python -m cli.main impact raw_customers.email

Impact analysis for change to raw_customers.email:

  [depth 1] stg_customers.email
             via: 07_stg_customers.sql

  [depth 2] dim_customers.email
             via: 07_stg_customers.sql -> 12_dim_customers.sql
  [depth 2] fct_orders.customer_email
             via: 07_stg_customers.sql -> 14_fct_orders.sql

  [depth 3] rpt_churn_risk.email
             via: 07_stg_customers.sql -> 12_dim_customers.sql -> 22_rpt_churn_risk.sql
```

---

## Features

### Column-Level Lineage
- Parses SQL files using `sqlglot` AST — handles `CREATE TABLE AS SELECT`, `INSERT INTO SELECT`, CTEs, subqueries, and multi-table JOINs
- Parses Python scripts using Python's `ast` module to extract `pandas` `read_csv` / `read_parquet` / `to_parquet` calls
- Stores everything as a directed graph in Neo4j: `Table`, `Column`, and `File` nodes connected by `FEEDS`, `DERIVES_INTO`, `PROCESSED_INTO`, and `LANDS_INTO` edges

### CLI
| Command | Description |
|---|---|
| `up <table.column>` | Show all upstream sources |
| `down <table.column>` | Show all downstream consumers |
| `impact <table.column>` | Full downstream impact with depth and script paths |
| `dead` | Dead column detector with depth, reason, and last script |
| `orphans` | Columns with no upstream or downstream connections |
| `simulate-rename <table.column> <new_name>` | Migration checklist for a column rename |
| `simulate-type <table.column> <old> <new>` | Migration checklist for a type change |
| `visualize` | Export interactive HTML lineage graph |

All commands support `--format json` for machine-readable output.

### Schema Change Simulator
Running `simulate-rename raw_customers.email email_address --output migration.md` produces:
- Every downstream column affected, sorted by dependency depth
- Severity score per column (`LOW` / `MEDIUM` / `HIGH` / `CRITICAL`)
- Indirect break detection (columns whose names contain the renamed source)
- Safe script execution order (shallow scripts must be updated before deep ones)
- Rollback action for every step
- Markdown export for use as a migration document

### Dead Column Detector
Running `dead --layer fct` finds all columns in `fct_` tables with no downstream usage, and for each shows:
- Pipeline depth
- Reason: `never_forwarded`, `renamed`, or `orphan`
- Which SQL file last touched it
- Cross-layer summary count

### Interactive Visualizer
Running `visualize --mode table` generates a self-contained HTML file with:
- Node-per-table or node-per-column graph
- Layer color coding (red=raw, yellow=stg, blue=dim/fct, green=mrt, purple=rpt)
- Search/filter panel with highlight and fade
- Node detail panel on click (layer, edge counts, SQL files)
- `--focus table.column` mode to render only the reachable subgraph

### IDE-Style Dashboard
```
uvicorn dashboard.main:app --reload --port 8000
```
A FastAPI web dashboard with:
- Sidebar explorer with all tables grouped by layer
- Table inspector showing columns, upstream, and downstream tables
- Command palette (`⌘K`) to search tables and run commands
- Dead column panel with layer summary
- Schema simulator with execution order, severity badges, and rollback
- Embedded interactive graph visualizer

<img width="1469" height="733" alt="image" src="https://github.com/user-attachments/assets/605ecc27-a78d-4cae-8aa7-0bac3be86bee" />


---

## Stack

| Component | Technology |
|---|---|
| SQL parsing | `sqlglot` |
| Python parsing | `ast` (stdlib) |
| Graph database | Neo4j 5.18 |
| Graph client | `neo4j` Python driver |
| CLI | `click` |
| Visualizer | `pyvis` |
| Dashboard | `FastAPI` + `Jinja2` |
| Infrastructure | Docker Compose |
| Testing | `pytest` (51 tests) |

---

## Project Structure

```
data-lineage-system/
├── data/
│   ├── sql_scripts/          # 22 SQL files across 5 layers (raw → stg → dim/fct → mrt → rpt)
│   └── python_scripts/       # 3 pandas pipeline scripts
├── lineage/
│   ├── parser/
│   │   ├── sql_parser.py     # sqlglot AST parsing, CTE exclusion, column mapping extraction
│   │   └── python_parser.py  # ast module pandas I/O extraction
│   ├── graph/
│   │   ├── neo4j_client.py   # Neo4j driver, constraints, indexes
│   │   └── ingester.py       # Two-pass graph ingestion with column membership map
│   └── analysis/
│       ├── traversal.py      # Upstream, downstream, impact, dead column, orphan queries
│       ├── simulator.py      # Schema change simulator with severity scoring
│       └── visualizer.py     # pyvis HTML export with legend, search, focus mode
├── cli/
│   └── main.py               # Click CLI with 8 commands
├── dashboard/
│   ├── main.py               # FastAPI routes
│   └── templates/
│       └── index.html        # IDE-style single-page dashboard
├── tests/
│   ├── conftest.py           # Session-scoped Neo4j fixture
│   ├── test_sql_parser.py
│   ├── test_python_parser.py
│   ├── test_traversal.py
│   ├── test_impact.py
│   ├── test_ingester.py
│   └── test_simulator.py
├── docker-compose.yml
├── run_ingest.py
├── requirements.txt
└── pyproject.toml
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- Docker

### Setup

```bash
# Clone the repository
git clone https://github.com/neetikaneupane/Data-Lineage-and-Impact-Analysis-System.git
cd Data-Lineage-and-Impact-Analysis-System

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Start Neo4j
docker compose up -d

# Ingest the SQL and Python lineage into Neo4j
python run_ingest.py
```

### Run the CLI

```bash
# Upstream lineage
python -m cli.main up fct_orders.customer_id

# Downstream lineage
python -m cli.main down raw_customers.email

# Impact analysis
python -m cli.main impact raw_customers.email

# Dead columns in fct_ layer
python -m cli.main dead --layer fct

# Orphan columns
python -m cli.main orphans

# Simulate a column rename
python -m cli.main simulate-rename raw_customers.email email_address --output migration.md

# Simulate a type change
python -m cli.main simulate-type raw_customers.email VARCHAR NUMERIC

# Export table graph
python -m cli.main visualize --mode table --output table_graph.html

# Export column graph with focus
python -m cli.main visualize --mode column --focus raw_customers.email --output focus.html
```

### Run the Dashboard

```bash
uvicorn dashboard.main:app --reload --port 8000
# Open http://localhost:8000
```

### Run Tests

```bash
pytest tests/ -v
```

---

## Graph Model

After ingesting the 22-file e-commerce domain:

| Metric | Value |
|---|---|
| Total nodes | 275 |
| Total edges | 283 |
| `FEEDS` edges (table-to-table) | 33 |
| `DERIVES_INTO` edges (column-to-column) | 246 |
| `PROCESSED_INTO` edges (Python file-to-file) | 4 |
| Uniqueness constraints | 3 |
| Tests passing | 51 / 51 |

---

## Test Domain

A fake e-commerce data warehouse with 22 SQL scripts across 5 layers:

| Layer | Tables | Description |
|---|---|---|
| `raw_` | 6 | Source schema definitions |
| `stg_` | 5 | Light cleaning (LOWER, TRIM, COALESCE) |
| `dim_` / `fct_` | 5 | Warehouse layer with JOINs |
| `mrt_` | 4 | Business aggregations with CTEs |
| `rpt_` | 2 | Final reporting tables |

---

## Hard Problems Solved

**Column-level lineage through CTEs** : CTE aliases are detected and excluded from input table lists. Only real source tables referenced inside CTE bodies appear in the graph.

**Precise column-to-table matching in JOINs** :A two-pass ingestion builds a column membership map first, so `order_id` only gets a `DERIVES_INTO` edge from the table that actually owns it, not every table in the JOIN.

**Rename detection across layers** : `raw_customers.email` becoming `fct_orders.customer_email` via a column alias is automatically detected and flagged as an indirect break in the schema simulator.

**Connecting Python and SQL lineage** : Output file names from Python scripts (e.g. `customers.parquet`) are matched to SQL table names (`customers`) and connected via `LANDS_INTO` edges.

---

## Environment Variables

Create a `.env` file in the project root:

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here
```
