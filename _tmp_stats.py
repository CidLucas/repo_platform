import pandas as pd

df = pd.read_csv("products_invoices.csv", low_memory=False)
df["emittedat_operatorinvoice"] = pd.to_datetime(df["emittedat_operatorinvoice"], errors="coerce")

mat = df["material"].fillna("").str.strip().str.lower()
desc = df["description_product"].fillna("").str.strip()
mask = (mat != "") & (mat != "unknown") & (desc != "")
df_clean = df[mask].copy()
df_clean["year"] = df_clean["emittedat_operatorinvoice"].dt.year

print(f"Original rows: {len(df)}")
print(f"After removing unknown/empty material + empty description: {len(df_clean)}")
print(f"Unique materials: {df_clean['material'].nunique()}")
print(f"Unique states: {df_clean['emitterstateuf'].nunique()}")
print()

yearly = df_clean.groupby("year").size().reset_index(name="count")
yearly["pct"] = (yearly["count"] / yearly["count"].sum() * 100).round(1)
print("=== Rows per year ===")
for _, r in yearly.iterrows():
    yr = int(r["year"])
    cnt = int(r["count"])
    pct = r["pct"]
    print(f"  {yr}: {cnt:>6} rows  ({pct}%)")
print()

natop = df_clean["natop_operatorinvoice"].fillna("").str.strip().str.lower()
inter_mask = natop.str.contains("interestadual|fora do estado|fora estado|outros estados", regex=True)
venda_kw = natop.str.contains("venda|vda|vnd|saida|remessa|sucata", regex=True)
compra_kw = natop.str.contains("compra|cpa|entrada|aquisicao", regex=True)

df_clean["cat"] = "OUTROS"
df_clean.loc[venda_kw & ~inter_mask, "cat"] = "VENDA"
df_clean.loc[compra_kw & ~inter_mask, "cat"] = "COMPRA"
df_clean.loc[venda_kw & inter_mask, "cat"] = "VENDA INTERESTADUAL"
df_clean.loc[compra_kw & inter_mask, "cat"] = "COMPRA INTERESTADUAL"

df_final = df_clean[df_clean["cat"] != "OUTROS"]
print(f"After removing OUTROS category: {len(df_final)} rows")
print()

yearly2 = df_final.groupby("year").size().reset_index(name="count")
yearly2["pct"] = (yearly2["count"] / yearly2["count"].sum() * 100).round(1)
print("=== Final clean rows per year ===")
for _, r in yearly2.iterrows():
    yr = int(r["year"])
    cnt = int(r["count"])
    pct = r["pct"]
    print(f"  {yr}: {cnt:>6} rows  ({pct}%)")
print()

print("=== Per year x category ===")
yc = df_final.groupby(["year", "cat"]).size().unstack(fill_value=0)
print(yc.to_string())
