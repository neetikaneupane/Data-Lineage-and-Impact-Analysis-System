from lineage.parser.sql_parser import parse_all_sql_files

results = parse_all_sql_files("data/sql_scripts")

for r in results:
    print(f"\nFile: {r['file']}")
    print(f"  Output: {r['output_table']}")
    print(f"  Inputs: {r['input_tables']}")
    print(f"  Mappings: {r['column_mappings'][:2]}")  # first 2 only