import streamlit as st
import pandas as pd
import plotly.express as px

# Optional: Apriori
try:
    from mlxtend.frequent_patterns import apriori, association_rules
    MLXTEND_INSTALLED = True
except ModuleNotFoundError:
    MLXTEND_INSTALLED = False

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

df["tran_date"] = pd.to_datetime(df["tran_date"], errors="coerce")
st.success("POS Data Loaded Successfully ✔")

# ----------------------------
# FILTERS
# ----------------------------
st.sidebar.header("Filter Data")
pos_options = ["All"] + sorted(df["pos_name"].unique().tolist())
selected_pos = st.sidebar.selectbox("Select POS Name", pos_options)
min_date = df["tran_date"].min()
max_date = df["tran_date"].max()
selected_dates = st.sidebar.date_input("Select Date Range", [min_date, max_date])

filtered_df = df.copy()
if selected_pos != "All":
    filtered_df = filtered_df[filtered_df["pos_name"] == selected_pos]

filtered_df = filtered_df[
    (filtered_df["tran_date"].dt.date >= selected_dates[0]) &
    (filtered_df["tran_date"].dt.date <= selected_dates[1])
]

if filtered_df.empty:
    st.warning("No data for selected filters.")
    st.stop()

# ----------------------------
# POS + TRAN NO VALIDATION
# ----------------------------
st.subheader("⚠️ POS + Tran No Validation")
tran_check = filtered_df.groupby(["pos_name", "tran_no"]).size().reset_index(name="item_count")
st.dataframe(tran_check)

# ----------------------------
# KEY METRICS
# ----------------------------
st.subheader("📊 Key Metrics")
total_sales = filtered_df["item_total"].sum()
total_items = filtered_df["qty"].sum()
total_bills = filtered_df.groupby(["pos_name", "tran_no"]).ngroups
avg_basket_value = total_sales / total_bills
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Sales", f"{total_sales:,.2f}")
col2.metric("Total Bills", total_bills)
col3.metric("Total Items Sold", int(total_items))
col4.metric("Avg Basket Value", f"{avg_basket_value:,.2f}")

# ----------------------------
# HOURLY SALES TREND
# ----------------------------
st.subheader("⏰ Hourly Sales Trend")
filtered_df["hour"] = filtered_df["tran_date"].dt.hour
hourly_sales = filtered_df.groupby("hour")["item_total"].sum().reset_index()
hourly_sales["hour_label"] = hourly_sales["hour"].apply(lambda x: f"{x}:00")
fig_hour = px.bar(hourly_sales, x="hour_label", y="item_total",
                  labels={"hour_label": "Hour of Day", "item_total": "Total Sales"},
                  title="Hourly Sales",
                  text="item_total")
fig_hour.update_traces(texttemplate="%{text:.2f}", textposition="outside")
fig_hour.update_layout(xaxis_tickangle=-45, yaxis_tickformat=".2f")
st.plotly_chart(fig_hour, use_container_width=True)

# ----------------------------
# HALF-HOUR INTERVAL SALES TREND
# ----------------------------
st.subheader("⏱ Half-Hour Interval Sales Trend")
filtered_df["half_hour"] = filtered_df["tran_date"].dt.floor("30T")
half_hour_sales = filtered_df.groupby("half_hour")["item_total"].sum().reset_index()
fig_half = px.line(half_hour_sales, x="half_hour", y="item_total", markers=True,
                   labels={"half_hour": "Time", "item_total": "Total Sales"},
                   title="Sales by 30-Min Interval")
fig_half.update_layout(xaxis_tickformat="%d-%b %H:%M")
st.plotly_chart(fig_half, use_container_width=True)

# ----------------------------
# TOP SELLING ITEMS
# ----------------------------
st.subheader("🏆 Top Selling Items (by Sales)")
item_sales = filtered_df.groupby("item_name")["item_total"].sum().reset_index().sort_values(by="item_total", ascending=False)
fig_sales = px.bar(item_sales.head(20), x="item_total", y="item_name", orientation="h",
                   labels={"item_total": "Sales Amount", "item_name": "Item Name"},
                   title="Top Selling Items by Sales")
st.plotly_chart(fig_sales, use_container_width=True)

st.subheader("📦 Top Selling Items (by Quantity)")
item_qty = filtered_df.groupby("item_name")["qty"].sum().reset_index().sort_values(by="qty", ascending=False)
fig_qty = px.bar(item_qty.head(20), x="qty", y="item_name", orientation="h",
                 labels={"qty": "Quantity Sold", "item_name": "Item Name"},
                 title="Top Selling Items by Quantity")
st.plotly_chart(fig_qty, use_container_width=True)

# ----------------------------
# ITEMS BOUGHT TOGETHER
# ----------------------------
st.subheader("🤝 Items Bought Together (Top 30)")

if MLXTEND_INSTALLED:
    basket = filtered_df.groupby(['pos_name', 'tran_no'])['item_name'].apply(list).reset_index()
    all_items = sorted(filtered_df['item_name'].unique())
    encoded = pd.DataFrame(0, index=basket.index, columns=all_items)
    for idx, items in enumerate(basket['item_name']):
        for item in items:
            encoded.at[idx, item] = 1

    freq_items = apriori(encoded, min_support=0.02, use_colnames=True)
    rules = association_rules(freq_items, metric="confidence", min_threshold=0.2)

    if rules.empty:
        st.warning("Not enough data to generate item combinations.")
    else:
        rules = rules.sort_values(by="confidence", ascending=False)
        rules["Combination"] = rules.apply(
            lambda x: " + ".join(list(x["antecedents"])) + " → " + " + ".join(list(x["consequents"])), axis=1
        )
        rules["Chance (%)"] = (rules["confidence"] * 100).round(2)
        st.dataframe(rules[["Combination", "Chance (%)"]].head(30))
else:
    st.warning("mlxtend not installed – cannot show 'items bought together'.")

# ----------------------------
# MOST FREQUENT ITEM PAIRS
# ----------------------------
st.subheader("🔗 Most Common Two-Item Combos")
pair_counts = {}
basket = filtered_df.groupby(['pos_name', 'tran_no'])['item_name'].apply(list).reset_index()
for items in basket["item_name"]:
    items = list(set(items))
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            pair = tuple(sorted([items[i], items[j]]))
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

pair_df = pd.DataFrame([{"Item 1": a, "Item 2": b, "Count": c} for (a,b), c in pair_counts.items()])
pair_df = pair_df.sort_values(by="Count", ascending=False)
st.dataframe(pair_df.head(10))

# ----------------------------
st.info("Dashboard Loaded Successfully ✔")
