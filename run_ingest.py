from lineage.parser.sql_parser import parse_all_sql_files
from lineage.graph.ingester import ingest_all

parsed = parse_all_sql_files("data/sql_scripts")
ingest_all(parsed)