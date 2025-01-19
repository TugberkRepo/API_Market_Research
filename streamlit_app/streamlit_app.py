import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import plotly.colors

# 1. Page Config
st.set_page_config(page_title="Product Data Dashboard", layout="wide")
st.title("Product Data Dashboard")

# 2. Load Environment
mysql_user = os.environ.get("MYSQL_USER", "myuser")
mysql_password = os.environ.get("MYSQL_PASSWORD", "mypassword")
mysql_host = os.environ.get("MYSQL_HOST", "db")  # "db" if Docker Compose
mysql_port = os.environ.get("MYSQL_PORT", "3306")
mysql_database = os.environ.get("MYSQL_DATABASE", "productcatalog")
mysql_table = os.environ.get("MYSQL_TABLE", "productdetails")

connection_url = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}"
from sqlalchemy import create_engine
engine = create_engine(connection_url)

@st.cache_data
def load_data():
    query = f"SELECT * FROM {mysql_table};"
    df = pd.read_sql(query, engine)
    return df

df = load_data()
st.write(f"Total rows loaded: {len(df)}")

#######################################
# EXTRA STEP: CREATE DISTRIBUTOR COLOR MAP
#######################################
def create_distributor_color_map(dataframe):
    """
    Build a dictionary so each unique distributor_name
    always has the same color in different charts.
    """
    unique_dists = sorted(dataframe["Distributor_name"].dropna().unique())
    base_palette = plotly.colors.qualitative.Plotly  # e.g., "Plotly" palette
    dist_color_map = {}
    for i, dist in enumerate(unique_dists):
        dist_color_map[dist] = base_palette[i % len(base_palette)]
    return dist_color_map

# We'll create the map after we apply filters (so we only color
# for distributors that appear in the filtered data). That ensures
# we don't define colors for unused distributors if you prefer.
# Alternatively, define it once with df (unfiltered).

# 4. Sidebar Filters
st.sidebar.header("Apply Filters")
all_categories = sorted(df["Categories"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect("Categories", all_categories, default=[])

all_subcat = sorted(df["Sub_Categories"].dropna().unique().tolist())
selected_subcat = st.sidebar.multiselect("Sub Categories", all_subcat, default=[])

all_subcat2 = sorted(df["Sub_Categories2"].dropna().unique().tolist())
selected_subcat2 = st.sidebar.multiselect("Sub Categories 2", all_subcat2, default=[])

all_parts = sorted(df["Part_Number"].dropna().unique().tolist())
selected_parts = st.sidebar.multiselect("Part Number", all_parts, default=[])

all_manufacturers = sorted(df["Manufacturer"].dropna().unique().tolist())
selected_manufacturers = st.sidebar.multiselect("Manufacturer", all_manufacturers, default=[])

all_distributors = sorted(df["Distributor_name"].dropna().unique().tolist())
selected_distributors = st.sidebar.multiselect("Distributor Name", all_distributors, default=[])

all_regions = sorted(df["Distributor_region"].dropna().unique().tolist())
selected_regions = st.sidebar.multiselect("Distributor Region", all_regions, default=[])

all_countries = sorted(df["Distributor_country"].dropna().unique().tolist())
selected_countries = st.sidebar.multiselect("Distributor Country", all_countries, default=[])

all_qty = sorted(df["Unit_break_QTY"].dropna().unique().tolist())
selected_qty = st.sidebar.multiselect("Unit Break QTY", all_qty, default=[])

# 5. Apply Filters
filtered_df = df.copy()
if selected_categories:
    filtered_df = filtered_df[filtered_df["Categories"].isin(selected_categories)]
if selected_subcat:
    filtered_df = filtered_df[filtered_df["Sub_Categories"].isin(selected_subcat)]
if selected_subcat2:
    filtered_df = filtered_df[filtered_df["Sub_Categories2"].isin(selected_subcat2)]
if selected_parts:
    filtered_df = filtered_df[filtered_df["Part_Number"].isin(selected_parts)]
if selected_manufacturers:
    filtered_df = filtered_df[filtered_df["Manufacturer"].isin(selected_manufacturers)]
if selected_distributors:
    filtered_df = filtered_df[filtered_df["Distributor_name"].isin(selected_distributors)]
if selected_regions:
    filtered_df = filtered_df[filtered_df["Distributor_region"].isin(selected_regions)]
if selected_countries:
    filtered_df = filtered_df[filtered_df["Distributor_country"].isin(selected_countries)]
if selected_qty:
    filtered_df = filtered_df[filtered_df["Unit_break_QTY"].isin(selected_qty)]

st.subheader("Filtered Results")
st.write(f"Rows after filtering: {len(filtered_df)}")

# Show only 2 decimals for Unit_price_EUR in the table
display_cols = [
    "Categories",
    "Sub_Categories",
    "Sub_Categories2",
    "Part_Number",
    "Manufacturer",
    "Distributor_name",
    "Distributor_region",
    "Distributor_country",
    "Unit_break_QTY",
    "Unit_price_EUR",
    "New_Lead_Time",
    "DataPulledTime",
    "Quantity_in_stock",
    "Factory_stock_quantity",
    "On_order_quantity",
    "Partner_stock_quantity",
]

df_to_show = filtered_df[display_cols].copy()
df_to_show["Unit_price_EUR"] = df_to_show["Unit_price_EUR"].round(2)
st.dataframe(df_to_show)

#######################################
# CREATE DISTRIBUTOR COLOR MAP (Filtered)
#######################################
# Doing this AFTER applying filters ensures we only map colors
# for distributors present in filtered_df.
distributor_color_map = create_distributor_color_map(filtered_df)

# 6. Graphs with Different Colors
st.subheader("Manufacturer vs. Unit Price")
df_man = filtered_df.groupby("Manufacturer", as_index=False)["Unit_price_EUR"].mean()
fig_man = px.bar(
    df_man,
    x="Manufacturer",
    y="Unit_price_EUR",
    color="Manufacturer",  # different color for each manufacturer
    title="Average Unit Price per Manufacturer",
    labels={"Unit_price_EUR": "Avg. Price (EUR)"},
    # We aren't forcing a color map for manufacturer, only for distributor
)

st.plotly_chart(fig_man, use_container_width=True)

st.subheader("Distributor vs. Unit Price")
df_dist = filtered_df.groupby("Distributor_name", as_index=False)["Unit_price_EUR"].mean()
fig_dist = px.bar(
    df_dist,
    x="Distributor_name",
    y="Unit_price_EUR",
    color="Distributor_name",
    title="Average Unit Price per Distributor",
    labels={"Unit_price_EUR": "Avg. Price (EUR)"},
    color_discrete_map=distributor_color_map  # unified color for distributors
)
st.plotly_chart(fig_dist, use_container_width=True)

# 7. Single-Part Logic - color by distributor in the line chart
if len(selected_parts) == 1:
    single_part = selected_parts[0]
    part_data = filtered_df[filtered_df["Part_Number"] == single_part]

    if not part_data.empty:
        st.subheader(f"Details for Part Number: {single_part}")

        image_url = part_data["Image_URL"].iloc[0]
        buy_url = part_data["Buy_now_URL"].iloc[0]

        if isinstance(image_url, str) and image_url.lower().startswith("http"):
            st.image(image_url, caption=f"Image for {single_part}", use_column_width=True)
        else:
            st.write("No valid Image_URL found.")

        if isinstance(buy_url, str) and buy_url.lower().startswith("http"):
            st.markdown(f"[Buy Now Link]({buy_url})")
        else:
            st.write("No valid Buy_now_URL found.")

        time_cols = ["DataPulledTime", "Unit_price_EUR", "Distributor_name"]
        time_df = part_data[time_cols].sort_values("DataPulledTime")

        if len(time_df) > 1:
            st.subheader("Unit Price Over Time (Filtered)")

            price_fig = px.line(
                time_df,
                x="DataPulledTime",
                y="Unit_price_EUR",
                color="Distributor_name",
                markers=True,
                title="Unit_price_EUR Over Time",
                hover_data=["Distributor_name"],
                color_discrete_map=distributor_color_map,  # same color map
            )
            st.plotly_chart(price_fig, use_container_width=True)

else:
    st.write("Select exactly one Part_Number to see image, buy link, and price over time below.")
