import pandas as pd

df = pd.read_csv("data/raw/customers.csv")
df["email"] = df["email"].str.lower()
df["full_name"] = df["full_name"].str.strip()
df.to_parquet("data/processed/customers.parquet")