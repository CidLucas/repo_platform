"""
BigQuery Export Script
Usage: python bq_export.py

Exports tables to CSV files in the current directory.
Requires: pip install google-cloud-bigquery db-dtypes pandas
"""
import os
from google.cloud import bigquery
from google.oauth2 import service_account

# --- Configuration ---
SERVICE_ACCOUNT_FILE = "service_account.json"
PROJECT_ID = "analytics-big-query-242119"

QUERIES = {
    "products_invoices.csv": """
        SELECT *
        FROM `analytics-big-query-242119.dataform.products_invoices`
    """,
    "consulta_estoque.csv": """
        SELECT *
        FROM `analytics-big-query-242119.omie_etl_hive.consulta_estoque`
    """,
}
# Add more queries above as needed, e.g.:
# "titulos_new.csv": "SELECT * FROM `analytics-big-query-242119.omie_etl_hive.titulos_new`",

# --- Authenticate ---
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
client = bigquery.Client(credentials=creds, project=PROJECT_ID)

# --- Run queries and export ---
for filename, query in QUERIES.items():
    print(f"Running query for {filename}...")
    df = client.query(query).to_dataframe()
    df.to_csv(filename, index=False)
    print(f"  -> Saved {len(df)} rows x {len(df.columns)} columns to {filename}")

print("\nDone!")
