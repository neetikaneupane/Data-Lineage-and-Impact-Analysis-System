from lineage.parser.python_parser import parse_python_file, parse_all_python_files


def test_load_customers_inputs():
    result = parse_python_file("data/python_scripts/01_load_customers.py")
    assert "data/raw/customers.csv" in result["inputs"]


def test_load_customers_outputs():
    result = parse_python_file("data/python_scripts/01_load_customers.py")
    assert "data/processed/customers.parquet" in result["outputs"]


def test_load_orders_multiple_inputs():
    result = parse_python_file("data/python_scripts/02_load_orders.py")
    assert "data/raw/orders.csv" in result["inputs"]
    assert "data/processed/customers.parquet" in result["inputs"]


def test_export_report_output():
    result = parse_python_file("data/python_scripts/03_export_report.py")
    assert "data/output/revenue_by_country.csv" in result["outputs"]


def test_parse_all_returns_3_files():
    results = parse_all_python_files("data/python_scripts")
    assert len(results) == 3