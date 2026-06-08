from lineage.analysis.traversal import upstream, downstream, impact


def test_upstream_fct_orders_customer_id():
    rows = upstream("fct_orders", "customer_id")
    sources = [(r["source_table"], r["source_column"]) for r in rows]
    assert ("stg_customers", "customer_id") in sources
    assert ("stg_orders", "customer_id") in sources


def test_downstream_raw_customers_email():
    rows = downstream("raw_customers", "email")
    targets = [(r["target_table"], r["target_column"]) for r in rows]
    assert ("stg_customers", "email") in targets


def test_downstream_depth_ordering():
    rows = downstream("raw_customers", "customer_id")
    depths = [r["depth"] for r in rows]
    assert depths == sorted(depths)


def test_upstream_empty_for_raw_table():
    rows = upstream("raw_customers", "customer_id")
    assert rows == []