from lineage.parser.sql_parser import parse_all_sql_files
from lineage.parser.python_parser import parse_all_python_files
from lineage.graph.ingester import ingest_all, ingest_python_lineage

parsed_sql = parse_all_sql_files("data/sql_scripts")
ingest_all(parsed_sql)

parsed_py = parse_all_python_files("data/python_scripts")
ingest_python_lineage(parsed_py)