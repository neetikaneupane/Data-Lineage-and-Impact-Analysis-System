import pandas as pd

df = pd.read_parquet("data/processed/orders_enriched.parquet")
summary = df.groupby("country")["total_amount"].sum().reset_index()
summary.to_csv("data/output/revenue_by_country.csv", index=False)