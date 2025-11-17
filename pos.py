import streamlit as st
import pandas as pd
import plotly.express as px

# Optional Apriori (not mandatory)
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
except Exception as e:
    st.error("❌ Unable to load PosTransactionDetails.xlsx. Make sure the file is in the app folder.")
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

# Ensure tran_date is datetime
df["tran_date"] = pd.to_datetime(df["tran_date"], errors="coerce")
if df["tran_date"].isna().all():
    st.warning("Warning: tran_date column could not be parsed to dates. Time-based charts may be empty.")

# Helper: lower-case item names for search matching, but keep original names for display
df["item_name_clean"] = df["item_name"].astype(str).str.strip()

st.success("POS Data Loaded Successfully ✔")

# ----------------------------
# Sidebar: page selection + filters
# ----------------------------
page = st.sidebar.selectbox("Page", ["Dashboard", "Item Finder"])

st.sidebar.header("Filters for Dashboard")
pos_options = ["All"] + sorted(df["pos_name"].dropna().unique().tolist())
selected_pos = st.sidebar.selectbox("Select POS Name", pos_options, index=0)

min_date = df["tran_date"].min()
max_date = df["tran_date"].max()
# default date_input expects date objects; protect if NaT
if pd.isna(min_date) or pd.isna(max_date):
    selected_dates = None
else:
    selected_dates = st.sidebar.date_input("Select Date Range", [min_date.date(), max_date.date()])

# ----------------------------
# FILTER FUNCTION
# ----------------------------
def apply_filters(df_in):
    df_f = df_in.copy()
    if selected_pos and selected_pos != "All":
        df_f = df_f[df_f["pos_name"] == selected_pos]
    if selected_dates:
        start, end = selected_dates
        df_f = df_f[(df_f["tran_date"].dt.date >= start) & (df_f["tran_date"].dt.date <= end)]
    return df_f

# ----------------------------
# COMMON PREP for basket calculations
# ----------------------------
def build_baskets(df_b):
    """
    Returns DataFrame with each transaction (pos_name + tran_no) and list of items.
    """
    baskets = df_b.groupby(['pos_name', 'tran_no'])['item_name_clean'].apply(list).reset_index()
    return baskets

def compute_pair_counts(baskets):
    """
    Returns dict: {(itemA,itemB): count} where count = number of transactions containing both
    """
    pair_counts = {}
    trans_count_for_item = {}  # count transactions where item appears
    for items in baskets['item_name_clean']:
        unique_items = list(set(items))
        for item in unique_items:
            trans_count_for_item[item] = trans_count_for_item.get(item, 0) + 1
        for i in range(len(unique_items)):
            for j in range(i+1, len(unique_items)):
                pair = tuple(sorted([unique_items[i], unique_items[j]]))
                pair_counts[pair] = pair_counts.get(pair, 0) + 1
    return pair_counts, trans_count_for_item

# ----------------------------
# DASHBOARD PAGE
# ----------------------------
if page == "Dashboard":
    filtered_df = apply_filters(df)
    if filtered_df.empty:
        st.warning("No data for selected filters.")
        st.stop()

    # POS + Tran no validation
    st.subheader("⚠️ POS + Tran No Validation")
    tran_check = filtered_df.groupby(["pos_name", "tran_no"]).size().reset_index(name="item_count")
    st.dataframe(tran_check)

    # Key metrics
    st.subheader("📊 Key Metrics")
    total_sales = filtered_df["item_total"].sum()
    total_items = filtered_df["qty"].sum()
    total_bills = filtered_df.groupby(["pos_name", "tran_no"]).ngroups
    avg_basket_value = total_sales / total_bills if total_bills > 0 else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Sales", f"{total_sales:,.2f}")
    c2.metric("Total Bills", total_bills)
    c3.metric("Total Items Sold", int(total_items))
    c4.metric("Avg Basket Value", f"{avg_basket_value:,.2f}")

    # Hourly Sales Trend (interactive)
    st.subheader("⏰ Hourly Sales Trend")
    if filtered_df["tran_date"].notna().any():
        filtered_df = filtered_df.copy()
        filtered_df["hour"] = filtered_df["tran_date"].dt.hour
        hourly_sales = filtered_df.groupby("hour")["item_total"].sum().reset_index()
        # ensure all hours 0-23 present (for consistent x-axis)
        all_hours = pd.DataFrame({"hour": list(range(24))})
        hourly_sales = all_hours.merge(hourly_sales, on="hour", how="left").fillna(0)
        hourly_sales["hour_label"] = hourly_sales["hour"].apply(lambda x: f"{x:02d}:00")
        fig_hour = px.bar(hourly_sales, x="hour_label", y="item_total",
                          labels={"hour_label": "Hour of Day", "item_total": "Total Sales"},
                          title="Hourly Sales", text="item_total")
        fig_hour.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_hour.update_layout(xaxis_tickangle=-45, yaxis_tickformat=".2f", margin=dict(t=50))
        st.plotly_chart(fig_hour, use_container_width=True)
    else:
        st.info("No valid tran_date data to display hourly chart.")

    # Half-hour interval sales trend (interactive)
    st.subheader("⏱ Half-Hour Interval Sales Trend")
    if filtered_df["tran_date"].notna().any():
        filtered_df = filtered_df.copy()
        filtered_df["half_hour"] = filtered_df["tran_date"].dt.floor("30T")
        half_hour_sales = filtered_df.groupby("half_hour")["item_total"].sum().reset_index()
        if half_hour_sales.empty:
            st.info("Not enough time data to plot half-hour chart.")
        else:
            fig_half = px.line(half_hour_sales, x="half_hour", y="item_total", markers=True,
                               labels={"half_hour": "Time", "item_total": "Total Sales"},
                               title="Sales by 30-Min Interval")
            fig_half.update_layout(xaxis_tickformat="%d-%b %H:%M", margin=dict(t=50))
            st.plotly_chart(fig_half, use_container_width=True)
    else:
        st.info("No valid tran_date data to display half-hour chart.")

    # Top selling items
    st.subheader("🏆 Top Selling Items (by Sales)")
    item_sales = filtered_df.groupby("item_name_clean")["item_total"].sum().reset_index().sort_values(by="item_total", ascending=False)
    item_sales = item_sales.rename(columns={"item_name_clean": "item_name"})
    fig_sales = px.bar(item_sales.head(20), x="item_total", y="item_name", orientation="h",
                       labels={"item_total": "Sales Amount", "item_name": "Item Name"},
                       title="Top Selling Items by Sales")
    st.plotly_chart(fig_sales, use_container_width=True)

    st.subheader("📦 Top Selling Items (by Quantity)")
    item_qty = filtered_df.groupby("item_name_clean")["qty"].sum().reset_index().sort_values(by="qty", ascending=False)
    item_qty = item_qty.rename(columns={"item_name_clean": "item_name"})
    fig_qty = px.bar(item_qty.head(20), x="qty", y="item_name", orientation="h",
                     labels={"qty": "Quantity Sold", "item_name": "Item Name"},
                     title="Top Selling Items by Quantity")
    st.plotly_chart(fig_qty, use_container_width=True)

    # Items bought together (Top 30) using mlxtend if installed, else compute pair probabilities
    st.subheader("🤝 Items Bought Together (Top 30)")
    baskets = build_baskets(filtered_df)
    if baskets.empty:
        st.info("No basket transactions available for analysis.")
    else:
        if MLXTEND_INSTALLED:
            # Build one-hot table
            all_items = sorted(filtered_df['item_name_clean'].unique())
            encoded = pd.DataFrame(0, index=baskets.index, columns=all_items)
            for idx, items in enumerate(baskets['item_name_clean']):
                for item in items:
                    encoded.at[idx, item] = 1
            try:
                freq_items = apriori(encoded, min_support=0.02, use_colnames=True)
                rules = association_rules(freq_items, metric="confidence", min_threshold=0.1)
                if rules.empty:
                    st.warning("Not enough frequent itemsets to generate association rules.")
                else:
                    rules = rules.sort_values(by="confidence", ascending=False)
                    rules["Combination"] = rules.apply(
                        lambda x: " + ".join(list(x["antecedents"])) + " → " + " + ".join(list(x["consequents"])), axis=1
                    )
                    rules["Chance (%)"] = (rules["confidence"] * 100).round(2)
                    st.dataframe(rules[["Combination", "Chance (%)"]].head(30))
            except Exception as e:
                st.warning("Apriori failed; falling back to co-occurrence counts.")
                MLXTEND_INSTALLED = False  # fall through to manual method

        if not MLXTEND_INSTALLED:
            pair_counts, trans_count_for_item = compute_pair_counts(baskets)
            # For display, compute conditional probability P(B|A) for each pair (A->B)
            results = []
            for (a, b), cnt in pair_counts.items():
                # conditional probability both ways; we'll show chance of B when A is present (and vice versa)
                a_count = trans_count_for_item.get(a, 0)
                b_count = trans_count_for_item.get(b, 0)
                if a_count > 0:
                    chance_b_given_a = (cnt / a_count) * 100
                else:
                    chance_b_given_a = 0.0
                if b_count > 0:
                    chance_a_given_b = (cnt / b_count) * 100
                else:
                    chance_a_given_b = 0.0
                results.append({
                    "Item A": a, "Item B": b, "Cooccurrence": cnt,
                    "P(B|A) %": round(chance_b_given_a, 2),
                    "P(A|B) %": round(chance_a_given_b, 2)
                })
            res_df = pd.DataFrame(results).sort_values(by="P(B|A) %", ascending=False)
            if res_df.empty:
                st.info("No item-pairs found.")
            else:
                st.dataframe(res_df.head(30))

    # Most frequent two-item combos simple table
    st.subheader("🔗 Most Common Two-Item Combos (Count)")
    pair_counts, _ = compute_pair_counts(baskets)
    pair_df = pd.DataFrame([{"Item 1": a, "Item 2": b, "Count": c} for (a, b), c in pair_counts.items()])
    if not pair_df.empty:
        pair_df = pair_df.sort_values(by="Count", ascending=False)
        st.dataframe(pair_df.head(20))
    else:
        st.info("No pair combos to show.")

# ----------------------------
# ITEM FINDER PAGE
# ----------------------------
else:
    st.header("🔎 Item Finder — search by Item Name or Barcode")
    # prepare searchable lists
    # barcode -> possible item names
    barcode_map = df.groupby("barcode")["item_name_clean"].unique().apply(list).to_dict()
    item_names_unique = sorted(df["item_name_clean"].unique().tolist())

    search_mode = st.radio("Search by", ["Item Name", "Barcode"], horizontal=True)

    if search_mode == "Item Name":
        query = st.text_input("Enter full or partial item name (case-insensitive)", "")
        match_button = st.button("Search Item")
        if match_button:
            q = query.strip()
            if not q:
                st.warning("Enter an item name to search.")
            else:
                # find closest matches (simple contains)
                matches = [name for name in item_names_unique if q.lower() in name.lower()]
                if not matches:
                    st.info("No matching item names found.")
                else:
                    chosen = st.selectbox("Matching items", matches)
                    if chosen:
                        st.write(f"Showing items commonly sold WITH **{chosen}**")
                        # filter transactions that contain chosen
                        baskets_all = build_baskets(df)  # use full dataset for co-occurrence counts unless user filtered
                        # if you want to respect sidebar filters, use baskets built from filtered_df instead:
                        use_filtered = st.checkbox("Use current Dashboard filters for co-occurrence calculation", value=True)
                        baskets_source = build_baskets(apply_filters(df) if use_filtered else df)
                        pair_counts, trans_count_for_item = compute_pair_counts(baskets_source)
                        chosen_count = trans_count_for_item.get(chosen, 0)
                        if chosen_count == 0:
                            st.info("No transactions contain this item in the selected dataset.")
                        else:
                            # compute P(other | chosen)
                            rows = []
                            for (a, b), cnt in pair_counts.items():
                                if a == chosen:
                                    rows.append((b, cnt, round((cnt / chosen_count) * 100, 2)))
                                elif b == chosen:
                                    rows.append((a, cnt, round((cnt / chosen_count) * 100, 2)))
                            if not rows:
                                st.info("No co-occurring items found.")
                            else:
                                result_df = pd.DataFrame(rows, columns=["Other Item", "Cooccurrence Count", "Chance (%)"])
                                result_df = result_df.sort_values(by="Chance (%)", ascending=False)
                                st.dataframe(result_df.head(50))
                                # Interactive bar chart
                                fig = px.bar(result_df.head(20), x="Chance (%)", y="Other Item", orientation="h",
                                             title=f"Top items sold together with '{chosen}' (P=Chance %)",
                                             labels={"Chance (%)": "Chance (%)", "Other Item": "Item"})
                                st.plotly_chart(fig, use_container_width=True)

    else:  # Barcode search
        barcode_input = st.text_input("Enter barcode (exact match)", "")
        search_barcode = st.button("Search Barcode")
        if search_barcode:
            bc = str(barcode_input).strip()
            if not bc:
                st.warning("Enter a barcode to search.")
            else:
                matched_items = barcode_map.get(bc)
                if not matched_items:
                    st.info("No items found with that barcode.")
                else:
                    # If barcode maps to multiple item_names, show options
                    chosen = matched_items[0] if len(matched_items) == 1 else st.selectbox("Barcode matched these item names:", matched_items)
                    st.write(f"Showing items commonly sold WITH item for barcode **{bc} → {chosen}**")
                    # compute co-occurrence similar to above
                    use_filtered = st.checkbox("Use current Dashboard filters for co-occurrence calculation", value=True)
                    baskets_source = build_baskets(apply_filters(df) if use_filtered else df)
                    pair_counts, trans_count_for_item = compute_pair_counts(baskets_source)
                    chosen_count = trans_count_for_item.get(chosen, 0)
                    if chosen_count == 0:
                        st.info("No transactions contain this item in the selected dataset.")
                    else:
                        rows = []
                        for (a, b), cnt in pair_counts.items():
                            if a == chosen:
                                rows.append((b, cnt, round((cnt / chosen_count) * 100, 2)))
                            elif b == chosen:
                                rows.append((a, cnt, round((cnt / chosen_count) * 100, 2)))
                        if not rows:
                            st.info("No co-occurring items found.")
                        else:
                            result_df = pd.DataFrame(rows, columns=["Other Item", "Cooccurrence Count", "Chance (%)"])
                            result_df = result_df.sort_values(by="Chance (%)", ascending=False)
                            st.dataframe(result_df.head(50))
                            fig = px.bar(result_df.head(20), x="Chance (%)", y="Other Item", orientation="h",
                                         title=f"Top items sold together with barcode {bc} → '{chosen}'",
                                         labels={"Chance (%)": "Chance (%)", "Other Item": "Item"})
                            st.plotly_chart(fig, use_container_width=True)

st.info("App Ready ✔")
