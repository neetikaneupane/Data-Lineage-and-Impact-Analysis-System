from lineage.parser.sql_parser import parse_sql_file, parse_all_sql_files


def test_raw_table_has_no_inputs():
    result = parse_sql_file("data/sql_scripts/01_raw_customers.sql")
    assert result["output_table"] == "raw_customers"
    assert result["input_tables"] == []
    assert result["column_mappings"] == []


def test_stg_table_has_correct_input():
    result = parse_sql_file("data/sql_scripts/07_stg_customers.sql")
    assert result["output_table"] == "stg_customers"
    assert "raw_customers" in result["input_tables"]


def test_stg_column_mappings_extracted():
    result = parse_sql_file("data/sql_scripts/07_stg_customers.sql")
    targets = [m["target_column"] for m in result["column_mappings"]]
    assert "email" in targets
    assert "customer_id" in targets


def test_join_extracts_multiple_inputs():
    result = parse_sql_file("data/sql_scripts/14_fct_orders.sql")
    assert "stg_orders" in result["input_tables"]
    assert "stg_customers" in result["input_tables"]


def test_cte_inputs_excluded_from_input_tables():
    result = parse_sql_file("data/sql_scripts/17_mrt_customer_lifetime_value.sql")
    input_tables = result["input_tables"]
    assert "order_totals" not in input_tables
    assert "payment_totals" not in input_tables


def test_parse_all_returns_22_files():
    results = parse_all_sql_files("data/sql_scripts")
    assert len(results) == 22