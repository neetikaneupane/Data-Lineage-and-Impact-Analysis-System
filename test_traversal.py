from lineage.analysis.traversal import upstream, downstream, impact

print("\n--- UPSTREAM of fct_orders.customer_id ---")
for row in upstream("fct_orders", "customer_id"):
    print(row)

print("\n--- DOWNSTREAM of raw_customers.customer_id ---")
for row in downstream("raw_customers", "customer_id"):
    print(row)

print("\n--- IMPACT of raw_customers.email ---")
for row in impact("raw_customers", "email"):
    print(row)