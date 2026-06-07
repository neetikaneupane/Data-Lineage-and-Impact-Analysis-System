import pandas as pd

orders = pd.read_csv("data/raw/orders.csv")
customers = pd.read_parquet("data/processed/customers.parquet")
merged = orders.merge(customers, on="customer_id")
merged.to_parquet("data/processed/orders_enriched.parquet")