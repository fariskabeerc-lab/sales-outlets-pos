import streamlit as st
import pandas as pd
import plotly.express as px

# ================================
# Page Config
# ================================
st.set_page_config(page_title="Sales & Profit Dashboard", layout="wide")
st.title("📊 Sales & Profit Insights (Jul-Sep)")

# ================================
# Load Data
# ================================
@st.cache_data
def load_sales_data(file_path):
    df = pd.read_excel(file_path)
    df['Item Code'] = df['Item Code'].astype(str)
    return df

@st.cache_data
def load_price_list(file_path):
    df_price = pd.read_excel(file_path)
    df_price['Item Bar Code'] = df_price['Item Bar Code'].astype(str)
    return df_price

# ================================
# File paths
# ================================
sales_file = "july to sep safa2025.Xlsx"  # replace with your file
price_file = "price list(1).xlsx"        # replace with your file

sales_df = load_sales_data(sales_file)
price_df = load_price_list(price_file)

# Fill missing sales columns if not in sales
for col in ['Jul-2025 Total Sales','Jul-2025 Total Profit',
            'Aug-2025 Total Sales','Aug-2025 Total Profit',
            'Sep-2025 Total Sales','Sep-2025 Total Profit']:
    if col not in sales_df.columns:
        sales_df[col] = 0

# ================================
# Merge all items first
# ================================
df_all = pd.merge(price_df, sales_df, left_on='Item Bar Code', right_on='Item Code', how='left')

# Fill missing columns
sales_cols = ['Jul-2025 Total Sales','Jul-2025 Total Profit',
              'Aug-2025 Total Sales','Aug-2025 Total Profit',
              'Sep-2025 Total Sales','Sep-2025 Total Profit']

for col in sales_cols:
    if col not in df_all.columns:
        df_all[col] = 0
    else:
        df_all[col] = df_all[col].fillna(0)

# Category column
if 'Category' not in df_all.columns:
    df_all['Category'] = 'Unknown'
else:
    df_all['Category'] = df_all['Category'].fillna('Unknown')

# ================================
# Compute Totals
# ================================
def compute_row_totals(row):
    total_sales = sum([row[col] for col in ['Jul-2025 Total Sales','Aug-2025 Total Sales','Sep-2025 Total Sales']])
    total_profit = sum([row[col] for col in ['Jul-2025 Total Profit','Aug-2025 Total Profit','Sep-2025 Total Profit']])
    overall_gp = (total_profit / total_sales) if total_sales != 0 else 0
    return pd.Series([total_sales, total_profit, overall_gp])

df_all[['Total Sales','Total Profit','Overall GP']] = df_all.apply(compute_row_totals, axis=1)

# ================================
# Sidebar Filters
# ================================
st.sidebar.header("Filters")
item_search = st.sidebar.text_input("Search Item Name")
barcode_search = st.sidebar.text_input("Search Item Bar Code")

all_categories = df_all['Category'].dropna().unique().tolist()
all_categories.sort()
all_categories.insert(0, "All")
selected_category = st.sidebar.selectbox("Select Category", all_categories)

# ================================
# Apply Filters
# ================================
filtered_df = df_all.copy()

if item_search:
    filtered_df = filtered_df[filtered_df['Item Name'].str.contains(item_search, case=False, na=False)]

if barcode_search:
    filtered_df = filtered_df[filtered_df['Item Bar Code'].str.contains(barcode_search, case=False, na=False)]

if selected_category != "All":
    filtered_df = filtered_df[filtered_df['Category'] == selected_category]

# ================================
# Key Metrics
# ================================
total_sales = filtered_df['Total Sales'].sum()
total_profit = filtered_df['Total Profit'].sum()
overall_gp = (total_profit / total_sales) if total_sales != 0 else 0

st.markdown("### 🔑 Key Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("Total Sales", f"{total_sales:,.0f}")
col2.metric("Total Profit", f"{total_profit:,.0f}")
col3.metric("Overall GP", f"{overall_gp:.2%}")

# ================================
# Monthly Performance Graph
# ================================
st.markdown("### 📅 Month-wise Performance")
months = ['Jul-2025','Aug-2025','Sep-2025']
month_data = []

for month in months:
    month_sales = filtered_df[f'{month} Total Sales'].sum()
    month_profit = filtered_df[f'{month} Total Profit'].sum()
    month_data.append({'Month': month, 'Type': 'Sales', 'Value': month_sales})
    month_data.append({'Month': month, 'Type': 'Profit', 'Value': month_profit})

monthly_df = pd.DataFrame(month_data)
fig_monthly = px.bar(monthly_df, x='Month', y='Value', color='Type', barmode='group',
                     text='Value', title="Monthly Sales & Profit")
st.plotly_chart(fig_monthly, use_container_width=True)

# ================================
# Category-wise Analysis
# ================================
category_summary = filtered_df.groupby('Category').agg({'Total Sales':'sum','Total Profit':'sum'}).reset_index()
category_summary['GP'] = category_summary['Total Profit'] / category_summary['Total Sales'].replace(0,1)

fig_sales = px.bar(category_summary, x='Category', y='Total Sales', color='Total Sales', text='Total Sales', title="Total Sales by Category")
st.plotly_chart(fig_sales, use_container_width=True)

fig_profit = px.bar(category_summary, x='Category', y='Total Profit', color='Total Profit', text='Total Profit', title="Total Profit by Category")
st.plotly_chart(fig_profit, use_container_width=True)

fig_gp = px.bar(category_summary, x='Category', y='GP', color='GP', text=category_summary['GP'].apply(lambda x:f"{x:.2%}"), title="Gross Profit % by Category")
st.plotly_chart(fig_gp, use_container_width=True)

# ================================
# Item-wise Table
# ================================
st.markdown("### 📝 Item-wise Details")
table_cols = ['Item Bar Code','Item Name','Cost','Selling','Stock',
              'Total Sales','Total Profit','Overall GP',
              'Jul-2025 Total Sales','Jul-2025 Total Profit',
              'Aug-2025 Total Sales','Aug-2025 Total Profit',
              'Sep-2025 Total Sales','Sep-2025 Total Profit']

for col in table_cols:
    if col not in filtered_df.columns:
        filtered_df[col] = 0

filtered_df['Overall GP'] = filtered_df['Overall GP'].apply(lambda x: f"{x:.2%}")

st.dataframe(filtered_df[table_cols].sort_values('Total Sales', ascending=False))
