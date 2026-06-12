from lineage.parser.sql_parser import parse_all_sql_files
from lineage.parser.python_parser import parse_all_python_files
from lineage.graph.ingester import ingest_all, ingest_python_lineage
from lineage.graph.neo4j_client import Neo4jClient

client = Neo4jClient()

# drop existing indexes so constraints can replace them
client.run("DROP INDEX column_id IF EXISTS")
client.run("DROP INDEX table_name IF EXISTS")
client.run("DROP INDEX file_path IF EXISTS")

client.create_constraints()
client.close()

parsed_sql = parse_all_sql_files("data/sql_scripts")
ingest_all(parsed_sql)

parsed_py = parse_all_python_files("data/python_scripts")
ingest_python_lineage(parsed_py)

print("Done.")