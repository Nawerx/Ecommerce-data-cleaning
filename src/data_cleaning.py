import pandas as pd
from pathlib import Path


# =============================================================================
# 1. Configuration
# =============================================================================

pd.set_option("display.max_columns", None)
pd.set_option("display.max_colwidth", None)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "messy_ecommerce_sales_data.csv"
CLEANED_PATH = PROJECT_ROOT / "data" / "cleaned" / "ecommerce_sales_cleaned.csv"


# =============================================================================
# 2. Load raw data
# =============================================================================

df_raw = pd.read_csv(RAW_PATH)
df = df_raw.copy()


# =============================================================================
# 3. Clean column names and string values
# =============================================================================

df.rename(columns=str.strip, inplace=True)

for column in df.columns:
    if pd.api.types.is_string_dtype(df[column]):
        df[column] = df[column].str.strip()


# =============================================================================
# 4. Normalize categorical columns
# =============================================================================

categories = [
    "Product",
    "Category",
    "Payment_Method",
    "Status"
]

for column in categories:
    df[column] = df[column].str.lower()


# =============================================================================
# 5. Fix inconsistent Category values
# =============================================================================

category_mapping = {
    "electronic": "electronics"
}

df["Category"] = df["Category"].replace(category_mapping)


# =============================================================================
# 6. Convert categorical columns to category dtype
# =============================================================================

for column in categories:
    df[column] = df[column].astype("category")


# =============================================================================
# 7. Quantity, Price and Total cleaning
# =============================================================================

# -----------------------------------------------------------------------------
# 7.1 Quantity
# -----------------------------------------------------------------------------

df["Quantity_raw"] = df["Quantity"]

quantity_numeric = pd.to_numeric(
    df["Quantity"],
    errors="coerce"
)

bad_quantities = df[
    quantity_numeric.isna() & df["Quantity"].notna()
]["Quantity"]

# Negative Quantity values were investigated together with Price and Total.
# The relationship Total = Price * Quantity showed that the signs were recorded
# incorrectly in these rows, so the absolute values are used.
df["Quantity"] = quantity_numeric.abs()


# -----------------------------------------------------------------------------
# 7.2 Price
# -----------------------------------------------------------------------------

df["Price_raw"] = df["Price"]

df["Price"] = df["Price"].str.replace("$", "", regex=False)

df["Price"] = df["Price"].replace({
    "four hundred": "400"
})

prices_numeric = pd.to_numeric(
    df["Price"],
    errors="coerce"
)

bad_prices = df[
    prices_numeric.isna() & df["Price_raw"].notna()
]

# The negative Price values were part of the same sign issue found during
# inspection, so the absolute values are used here as well :).
df["Price"] = prices_numeric.abs()

mask = (
    df["Price_raw"].isna() != df["Price"].isna()
)


# -----------------------------------------------------------------------------
# 7.3 Total
# -----------------------------------------------------------------------------

df["Total_raw"] = df["Total"]

# Total was checked against Price * Quantity. Recalculating it also restores
# values where both factors are known. If one factor is missing, Total remains
# missing instead of being estimated.
df["Total"] = (
    df["Price"] * df["Quantity"]
)

diff = (
    df["Total_raw"] - df["Total"]
).abs()

mask = (
    (diff > 0.01)
    |
    (df["Total_raw"].isna() != df["Total"].isna())
)

# This was useful during investigation to compare the original and recalculated
# values. It is intentionally left as a commented diagnostic check.
# print(df.loc[
#     mask,
#     ["Price", "Quantity", "Total_raw", "Total"]
# ])

difference = (
    df["Total_raw"] - df["Total"]
).abs()

df.drop(
    columns=["Total_raw", "Price_raw", "Quantity_raw"],
    inplace=True
)


# =============================================================================
# 8. Duplicate handling
# =============================================================================

# Repeated ID and Order_ID values were investigated before removal.
# The matching records were confirmed to be exact duplicate rows.
# print(df[df.duplicated(keep=False)])
df.drop_duplicates(inplace=True)

# print(df["ID"].unique())
# print(df["Order_ID"].duplicated().sum())


# =============================================================================
# 9. Order_Date cleaning
# =============================================================================

# The original date values were inspected before parsing.
# print(df["Order_Date"].unique())

df["Order_Date_raw"] = df["Order_Date"]

order_date_parsed = pd.to_datetime(
    df["Order_Date_raw"],
    format="mixed",
    errors="coerce",
    dayfirst=False
)

bad_dates = df[
    order_date_parsed.isna()
    & df["Order_Date"].notna()
]

# Invalid values such as "abc" are kept as missing dates instead of being
# replaced with an invented date.
# print(bad_dates)

df["Order_Date"] = order_date_parsed
df.drop(columns=["Order_Date_raw"], inplace=True)

# Unusual 2023 dates were inspected separately and kept because there was not
# enough evidence to treat them as errors.
# print(df["Order_Date"].dt.year.value_counts())


# =============================================================================
# 10. Category restoration
# =============================================================================

# While trying to restore missing Category values, inconsistent Product ->
# Category relationships were discovered. Product + Category frequencies are
# used to identify the dominant category for each product.
product_category_counts = (
    df.groupby(
        ["Product", "Category"],
        observed=True,
        as_index=False
    )
    .agg(
        Count_in_category=("Category", "size")
    )
)

dominant_categories = product_category_counts.groupby(
    ["Product"]
).agg(
    Dominant_Category_ind=("Count_in_category", "idxmax")
)

products_categories = product_category_counts.loc[
    dominant_categories["Dominant_Category_ind"],
    ["Product", "Category"]
].reset_index(drop=True)

category_map = products_categories.set_index("Product")["Category"]

# Rebuilding Category restores missing values and also fixes inconsistent
# categories for products that should belong to one dominant category.
df["Category"] = df["Product"].map(category_map)


# =============================================================================
# 11. Missing data review
# =============================================================================

# Missing values are kept when there is not enough information to restore them
print(df.isna().sum())


# =============================================================================
# 12. Final validation
# =============================================================================

print(df.info())

print("Duplicates:", df.duplicated().sum())

print("Min Quantity:", df["Quantity"].min())
print("Min Price:", df["Price"].min())

print("Date min:", df["Order_Date"].min())
print("Date max:", df["Order_Date"].max())

# =============================================================================
# 13. Final dtype adjustment
# =============================================================================

# Quantity represents whole units, but it also contains missing values.
# Pandas nullable Int64 keeps the integer meaning while supporting <NA>.
df["Quantity"] = df["Quantity"].astype("Int64")

print(df.info())


# =============================================================================
# 14. Export cleaned dataset
# =============================================================================

CLEANED_PATH.parent.mkdir(parents=True, exist_ok=True)

df.to_csv(
    CLEANED_PATH,
    index=False,
    date_format="%Y-%m-%d"
)

print(f"Cleaned CSV saved to: {CLEANED_PATH}")
