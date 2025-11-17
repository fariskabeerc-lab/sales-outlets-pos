import streamlit as st
import pandas as pd
from itertools import combinations
from collections import Counter

st.set_page_config(page_title="POS Analytics", layout="wide")

st.title("🛒 POS Billing Analytics Dashboard")

# -------------------------------------------------
# Load Excel directly (NO UPLOADER)
# -------------------------------------------------
FILE_PATH = r"PosTransactionDetails.xlsx"   # <-- CHANGE THIS PATH

df = pd.read_excel(FILE_PATH)

# -------------------------------------------------
# Preprocessing
# -------------------------------------------------
df['Tran Date'] = pd.to_datetime(df['Tran Date'])
df['Hour'] = df['Tran Date'].dt.hour
df['Day'] = df['Tran Date'].dt.day_name()
df['Date'] = df['Tran Date'].dt.date

st.success("POS Data Loaded Successfully ✔")

# =====================================================================
# SECTION 1 — BASIC METRICS
# =====================================================================
total_sales = df['Item Total'].sum()
total_items = df['QTY'].sum()
total_bills = df.groupby(['POS Name', 'Tran No']).ngroups
avg_basket_value = total_sales / total_bills

col1, col2, col3, col4 = st.columns(4)

col1.metric("💰 Total Sales", f"{total_sales:,.2f}")
col2.metric("🧾 Total Bills", total_bills)
col3.metric("📦 Total Quantity Sold", f"{total_items:,.0f}")
col4.metric("🛍️ Avg Basket Value", f"{avg_basket_value:,.2f}")

st.markdown("---")

# =====================================================================
# SECTION 2 — PEAK HOUR ANALYSIS
# =====================================================================
st.subheader("⏰ Peak Hour Sales")

peak_hour = df.groupby('Hour')['Tran No'].nunique().reset_index(name='Bills')
st.bar_chart(peak_hour, x="Hour", y="Bills")

st.markdown("---")

# =====================================================================
# SECTION 3 — ITEM SUMMARY TABLE
# =====================================================================
st.subheader("📋 Item Summary")

item_summary = df.groupby('Item Name').agg(
    Total_QTY=('QTY', 'sum'),
    Total_Sales=('Item Total', 'sum'),
    Avg_Rate=('Rate', 'mean'),
    Bills=('Tran No', 'nunique')
).sort_values(by="Total_QTY", ascending=False)

st.dataframe(item_summary, use_container_width=True)

st.markdown("---")

# =====================================================================
# SECTION 4 — FREQUENTLY BOUGHT TOGETHER (MBA)
# =====================================================================
st.subheader("🤝 Frequently Bought Together (Top 20 Pairs)")

baskets = df.groupby(['POS Name', 'Tran No'])['Item Name'].apply(list)

pairs = []
for items in baskets:
    combos = combinations(sorted(set(items)), 2)
    pairs.extend(combos)

pair_counts = Counter(pairs)
top_pairs = pd.DataFrame(pair_counts.most_common(20), columns=['Pair', 'Count'])

st.dataframe(top_pairs, use_container_width=True)

st.markdown("---")

# =====================================================================
# SECTION 5 — POS MACHINE PERFORMANCE
# =====================================================================
st.subheader("🏬 POS Machine Performance")

pos_perf = df.groupby('POS Name').agg(
    Bills=('Tran No', 'nunique'),
    Items_Sold=('QTY', 'sum'),
    Sales=('Item Total', 'sum')
)

st.bar_chart(pos_perf, y="Sales")
st.dataframe(pos_perf, use_container_width=True)

st.markdown("---")

# =====================================================================
# SECTION 6 — POS + TRAN NO VALIDATION
# =====================================================================
st.subheader("⚠️ POS and Bill Number Validation")

pos_issue = df.groupby('Tran No')['POS Name'].nunique()
pos_issue = pos_issue[pos_issue > 1]

if len(pos_issue) == 0:
    st.success("No conflicting POS–Tran No detected ✔")
else:
    st.error("Conflicting Bill Numbers Found ❗")
    st.write(pos_issue)

st.subheader("🔍 Missing Bill Numbers per POS")

missing_report = {}
for pos, sub in df.groupby("POS Name"):
    bills = sorted(sub['Tran No'].unique())
    expected = list(range(min(bills), max(bills)+1))
    missing = sorted(set(expected) - set(bills))
    missing_report[pos] = missing

st.write(missing_report)

st.markdown("---")

# =====================================================================
# SECTION 7 — DAILY SALES TREND
# =====================================================================
st.subheader("📈 Daily Sales Trend")

daily = df.groupby('Date')['Item Total'].sum().reset_index()
st.line_chart(daily, x="Date", y="Item Total")

st.markdown("---")
