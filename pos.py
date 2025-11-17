import streamlit as st
import pandas as pd

st.set_page_config(page_title="POS Billing Analytics", layout="wide")

# -----------------------------
# 1. Load Data (No Uploader)
# -----------------------------
FILE_PATH = "PosTransactionDetails.xlsx"   # <-- Replace with your actual file path

@st.cache_data
def load_data():
    df = pd.read_excel(FILE_PATH)

    # Normalize column names
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # Required columns
    required = ["barcode", "item_name", "qty", "pos_name", "tran_no", "tran_date", "rate", "item_total"]

    # Verify columns
    for col in required:
        if col not in df.columns:
            st.error(f"Missing column: {col}")
            st.stop()

    return df

df = load_data()
st.success("POS Data Loaded Successfully ✔")

# -----------------------------
# 2. Basic Metrics
# -----------------------------
total_sales = df["item_total"].sum()
total_bills = df.groupby(["pos_name", "tran_no"]).ngroups
total_qty = df["qty"].sum()
unique_items = df["item_name"].nunique()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Sales", round(total_sales, 2))
col2.metric("Total Bills", total_bills)
col3.metric("Total Quantity Sold", total_qty)
col4.metric("Unique Items", unique_items)

# -----------------------------
# 3. Bill Level Metrics
# -----------------------------
bill_summary = df.groupby(["pos_name", "tran_no"]).agg(
    bill_total=("item_total", "sum"),
    items_in_bill=("qty", "sum")
).reset_index()

avg_basket_value = bill_summary["bill_total"].mean()
avg_basket_size = bill_summary["items_in_bill"].mean()

st.subheader("🛍 Basket Metrics")
col1, col2 = st.columns(2)
col1.metric("Average Basket Value (ABV)", round(avg_basket_value, 2))
col2.metric("Average Basket Size", round(avg_basket_size, 2))

# -----------------------------
# 4. POS-level Sales
# -----------------------------
st.subheader("🏪 POS-wise Sales")
pos_sales = df.groupby("pos_name")["item_total"].sum().reset_index()
st.dataframe(pos_sales)

# -----------------------------
# 5. Item-wise Sales
# -----------------------------
st.subheader("📦 Item-wise Sales Summary")
item_sales = df.groupby("item_name").agg(
    total_qty=("qty", "sum"),
    total_sales=("item_total", "sum")
).sort_values(by="total_sales", ascending=False).reset_index()

st.dataframe(item_sales)

# -----------------------------
# 6. Daily Sales Trend
# -----------------------------
df["tran_date"] = pd.to_datetime(df["tran_date"])
daily_sales = df.groupby("tran_date")["item_total"].sum().reset_index()

st.subheader("📈 Daily Sales Trend")
st.line_chart(daily_sales, x="tran_date", y="item_total")

# -----------------------------
# 7. Fast Movers / Slow Movers
# -----------------------------
st.subheader("⚡ Fast Movers & 🐌 Slow Movers")

fast_movers = item_sales.head(10)
slow_movers = item_sales.tail(10)

c1, c2 = st.columns(2)
c1.write("### 🔥 Top 10 Fast Movers")
c1.dataframe(fast_movers)

c2.write("### ❄️ Bottom 10 Slow Movers")
c2.dataframe(slow_movers)

# -----------------------------
# 8. Full Raw Data
# -----------------------------
st.write("### 📄 Full Data")
st.dataframe(df)
