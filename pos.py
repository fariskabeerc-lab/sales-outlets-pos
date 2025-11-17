import streamlit as st
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="POS Analytics", layout="wide")
st.title("🛒 POS Billing Analytics Dashboard")

# ----------------------------
# LOAD DATA
# ----------------------------
try:
    df = pd.read_excel("PosTransactionDetails.xlsx")
except:
    st.error("❌ Unable to load pos.xlsx. Make sure the file is in the app folder.")
    st.stop()

# ----------------------------
# CLEAN COLUMN NAMES
# ----------------------------
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
required_cols = ["barcode", "item_name", "qty", "pos_name", "tran_no", "tran_date", "rate", "item_total"]
for col in required_cols:
    if col not in df.columns:
        st.error(f"❌ Missing column in Excel: {col}")
        st.stop()

# Convert Tran Date to datetime
df["tran_date"] = pd.to_datetime(df["tran_date"], errors="coerce")
st.success("POS Data Loaded Successfully ✔")

# ----------------------------
# POS + TRAN NO VALIDATION
# ----------------------------
st.subheader("⚠️ POS + Tran No Validation")
tran_check = df.groupby(["pos_name", "tran_no"]).size().reset_index(name="item_count")
st.dataframe(tran_check)

# ----------------------------
# KEY METRICS
# ----------------------------
st.subheader("📊 Key Metrics")
total_sales = df["item_total"].sum()
total_items = df["qty"].sum()
total_bills = df.groupby(["pos_name", "tran_no"]).ngroups
avg_basket_value = total_sales / total_bills
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Sales", f"{total_sales:,.2f}")
col2.metric("Total Bills", total_bills)
col3.metric("Total Items Sold", int(total_items))
col4.metric("Avg Basket Value", f"{avg_basket_value:,.2f}")

# ----------------------------
# PEAK HOURS (1-HOUR)
# ----------------------------
st.subheader("⏰ Peak Shopping Hours (Hourly)")
df["hour"] = df["tran_date"].dt.hour
hourly_sales = df.groupby("hour")["item_total"].sum()
fig, ax = plt.subplots(figsize=(12,4))
sns.barplot(x=hourly_sales.index, y=hourly_sales.values, palette="viridis", ax=ax)
ax.set_xlabel("Hour of Day")
ax.set_ylabel("Total Sales")
ax.set_title("Sales by Hour")
st.pyplot(fig)

# ----------------------------
# HALF-HOUR INTERVAL TREND
# ----------------------------
st.subheader("⏱ Half-Hour Interval Sales Trend")
df["half_hour"] = df["tran_date"].dt.floor("30T")
half_hour_sales = df.groupby("half_hour")["item_total"].sum()
fig, ax = plt.subplots(figsize=(12,4))
sns.lineplot(x=half_hour_sales.index, y=half_hour_sales.values, marker="o", ax=ax)
ax.set_xlabel("Time")
ax.set_ylabel("Total Sales")
ax.set_title("Sales by 30-Min Interval")
st.pyplot(fig)

# ----------------------------
# TOP SELLING ITEMS
# ----------------------------
st.subheader("🏆 Top Selling Items (by Sales)")
item_sales = df.groupby("item_name")["item_total"].sum().sort_values(ascending=False)
st.dataframe(item_sales.head(20))

st.subheader("📦 Top Selling Items (by Quantity)")
item_qty = df.groupby("item_name")["qty"].sum().sort_values(ascending=False)
st.dataframe(item_qty.head(20))

# ----------------------------
# ITEMS BOUGHT TOGETHER (MARKET BASKET ANALYSIS)
# ----------------------------
st.subheader("🤝 Items Bought Together (Market Basket Analysis)")

# Prepare baskets
basket = df.groupby(['pos_name', 'tran_no'])['item_name'].apply(list).reset_index()
all_items = sorted(df['item_name'].unique())
encoded = pd.DataFrame(0, index=basket.index, columns=all_items)
for idx, items in enumerate(basket['item_name']):
    for item in items:
        encoded.at[idx, item] = 1

# Apriori Algorithm
freq_items = apriori(encoded, min_support=0.02, use_colnames=True)
rules = association_rules(freq_items, metric="confidence", min_threshold=0.2)
if rules.empty:
    st.warning("Not enough data to generate association rules.")
else:
    rules = rules.sort_values(by="confidence", ascending=False)
    rules["antecedents"] = rules["antecedents"].apply(lambda x: ", ".join(list(x)))
    rules["consequents"] = rules["consequents"].apply(lambda x: ", ".join(list(x)))
    st.write("### 🔥 Top Item Combos")
    st.dataframe(rules[["antecedents", "consequents", "support", "confidence", "lift"]].head(20))

# ----------------------------
# MOST FREQUENT ITEM PAIRS
# ----------------------------
st.subheader("🔗 Most Common Two-Item Combos")
pair_counts = {}
for items in basket["item_name"]:
    items = list(set(items))
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            pair = tuple(sorted([items[i], items[j]]))
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

pair_df = pd.DataFrame([{"Item 1": a, "Item 2": b, "Count": c} for (a,b), c in pair_counts.items()])
pair_df = pair_df.sort_values(by="Count", ascending=False)
st.dataframe(pair_df.head(20))

# ----------------------------
# END
# ----------------------------
st.info("Dashboard Loaded Successfully ✔")
