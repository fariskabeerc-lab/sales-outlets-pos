import streamlit as st
import pandas as pd
import plotly.express as px
from mlxtend.frequent_patterns import apriori, association_rules

# ============================================================
# PAGE SETTINGS
# ============================================================
st.set_page_config(page_title="POS Analytics", layout="wide")
st.title("🛒 POS Billing Analytics Dashboard")

# ============================================================
# LOAD DATA
# ============================================================
try:
    df = pd.read_excel("pos.xlsx")
except:
    st.error("❌ pos.xlsx not found — place the file in the app folder.")
    st.stop()

# Clean columns
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

required = ["barcode", "item_name", "qty", "pos_name", "tran_no",
            "tran_date", "rate", "item_total"]

for c in required:
    if c not in df.columns:
        st.error(f"Missing column: {c}")
        st.stop()

df["tran_date"] = pd.to_datetime(df["tran_date"], errors="coerce")

st.success("✔ Data loaded successfully!")

# ============================================================
# BARCODE SEARCH
# ============================================================
st.subheader("🔍 Search by Barcode")

barcode = st.text_input("Enter barcode to search", "")

if barcode:
    result = df[df["barcode"].astype(str).str.contains(barcode)]
    st.write(f"Results for: **{barcode}**")
    st.dataframe(result)

# ============================================================
# KPIs
# ============================================================
st.subheader("📊 Key Metrics")

total_sales = df["item_total"].sum()
total_items = df["qty"].sum()
total_bills = df.groupby(["pos_name", "tran_no"]).ngroups
avg_basket_value = total_sales / total_bills

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Sales", f"{total_sales:,.2f}")
c2.metric("Total Bills", total_bills)
c3.metric("Items Sold", int(total_items))
c4.metric("Avg Basket Value", f"{avg_basket_value:,.2f}")

# ============================================================
# HOURLY SALES (BAR CHART)
# ============================================================
st.subheader("⏰ Hourly Sales Trend")

df["hour"] = df["tran_date"].dt.hour
hour_sales = df.groupby("hour")["item_total"].sum().reset_index()

fig_hour = px.bar(hour_sales, x="hour", y="item_total",
                  title="Hourly Sales", text_auto=True)
st.plotly_chart(fig_hour, use_container_width=True)

# ============================================================
# HALF-HOUR INTERVAL SALES (LINE CHART)
# ============================================================
st.subheader("🕒 Half-Hour Interval Sales Trend")

df["half_hour"] = df["tran_date"].dt.floor("30min")
hh_sales = df.groupby("half_hour")["item_total"].sum().reset_index()

fig_hh = px.line(hh_sales, x="half_hour", y="item_total",
                 title="Half-Hour Sales Trend", markers=True)
st.plotly_chart(fig_hh, use_container_width=True)

# ============================================================
# TOP SELLING ITEMS
# ============================================================
st.subheader("🏆 Top 20 Selling Items")

item_sales = df.groupby("item_name")["item_total"].sum().reset_index()
item_sales = item_sales.sort_values("item_total", ascending=False)

fig_top = px.bar(item_sales.head(20), x="item_total", y="item_name",
                 orientation="h", title="Top Selling Items")
st.plotly_chart(fig_top, use_container_width=True)

# ============================================================
# MARKET BASKET ANALYSIS (TOP 30 WITH % CHANCE)
# ============================================================
st.subheader("🤝 Items Bought Together — Top 30 with % Chance")

# Build transaction basket
basket = df.groupby(["pos_name", "tran_no"])["item_name"].apply(list)

# Create unique item list
unique_items = sorted(df["item_name"].unique())
encoded = pd.DataFrame(0, index=basket.index, columns=unique_items)

for idx, items in enumerate(basket):
    for it in items:
        encoded.at[idx, it] = 1

# Apriori Algorithm
freq_items = apriori(encoded, min_support=0.02, use_colnames=True)
rules = association_rules(freq_items, metric="confidence", min_threshold=0.2)

if rules.empty:
    st.warning("⚠️ Not enough data to generate rules.")
else:
    rules["antecedents"] = rules["antecedents"].apply(lambda x: ", ".join(list(x)))
    rules["consequents"] = rules["consequents"].apply(lambda x: ", ".join(list(x)))
    rules["chance_%"] = (rules["confidence"] * 100).round(2)

    final_rules = rules[["antecedents", "consequents", "support",
                         "confidence", "lift", "chance_%"]]

    final_rules = final_rules.sort_values("chance_%", ascending=False)

    st.dataframe(final_rules.head(30), height=500)

st.info("✔ Dashboard Ready")

