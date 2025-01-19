import os
import pandas as pd
import requests
import urllib3
import re
import schedule
import time
from datetime import datetime
from sqlalchemy import create_engine

# Disable SSL warnings (only for debugging purposes)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def pull_and_insert_data():
    """
    This function pulls data from an Excel file (v2_All_products.xlsx),
    makes API calls to OEM Secrets, cleans and transforms the data,
    adds a DataPulledTime column, and inserts the result into MySQL.
    """
    print(f"[{datetime.now()}] Starting data pull...")

    # --------------------------------------------------------------------------
    # 1. Load environment variables
    # --------------------------------------------------------------------------
    mysql_user = os.environ.get("MYSQL_USER", "root")
    mysql_password = os.environ.get("MYSQL_PASSWORD", "12345***")
    mysql_host = os.environ.get("MYSQL_HOST", "localhost")
    mysql_port = os.environ.get("MYSQL_PORT", "3306")
    mysql_database = os.environ.get("MYSQL_DATABASE", "productcatalog")
    mysql_table = os.environ.get("MYSQL_TABLE", "productdetails")

    # Example: reading comma-separated API keys from a single variable
    api_keys_str = os.environ.get("API_KEYS", "")
    api_keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]

    # --------------------------------------------------------------------------
    # 2. Verify the Excel file exists
    # --------------------------------------------------------------------------
    input_path = "v2_All_products.xlsx"
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Read the Excel sheet
    sheet_name = "Sheet1"
    df = pd.read_excel(input_path, sheet_name=sheet_name)
    df.columns = df.columns.str.strip()

    # --------------------------------------------------------------------------
    # 3. Make API calls to OEM Secrets
    # --------------------------------------------------------------------------
    api_base_url = "https://oemsecretsapi.com/partsearch"

    def get_part_info(part_number):
        """
        Cycles through API keys to fetch data for a given part_number.
        Returns the JSON response if successful, otherwise None.
        """
        for api_key in api_keys:
            url = f"{api_base_url}?apiKey={api_key}&searchTerm={part_number}&countryCode=DE&currency=EUR"
            try:
                response = requests.get(url, verify=False)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as http_err:
                if response.status_code == 401:
                    print(f"API key exhausted: {api_key}")
                    continue
                elif response.status_code in {400, 404}:
                    print(f"No data for {part_number}: {http_err}")
                    return None
                else:
                    print(f"HTTP error for {part_number}: {http_err}")
                    return None
            except requests.exceptions.RequestException as e:
                print(f"Request error for {part_number}: {e}")
                return None

        print("All API keys exhausted.")
        return None
    # --------------------------------------------------------------------------
    # 4. Build a new DataFrame from the API response
    # --------------------------------------------------------------------------
    columns = [
        "Part_Number", "Categories", "Sub_Categories", "Sub_Categories2", "Category",
        "Manufacturer", "Description", "Lead_time", "Lead_time_weeks", "Lead_time_format",
        "Unit_break_QTY", "Unit_price_EUR", "Quantity_in_stock", "Factory_stock_quantity",
        "On_order_quantity", "Partner_stock_quantity", "Distributor_name",
        "Distributor_region", "Distributor_country", "Image_URL", "Buy_now_URL"
    ]
    new_data = []

    for idx, row in df.iterrows():
        part_number = row["Part_Number"]
        categories = row["Categories"]
        sub_categories = row["Sub_Categories"]
        sub_categories2 = row["Sub_Categories2"]

        # Fetch the JSON for the current part number
        part_info = get_part_info(part_number)
        if not part_info or "stock" not in part_info or not part_info["stock"]:
            print(f"No data found for {part_number}")
            continue

        # Each "stock" entry may have multiple price breaks
        for stock_info in part_info["stock"]:
            prices = stock_info.get("prices", {})
            if not isinstance(prices, dict):
                print(f"Skipping entry due to unexpected 'prices' format: {prices}")
                continue

            price_list = prices.get("EUR", [])

            manufacturer = stock_info.get("manufacturer", "N/A")
            description = stock_info.get("description", "N/A")
            category = stock_info.get("category", "N/A")
            quantity_in_stock = stock_info.get("quantity_in_stock", "N/A")
            factory_stock_quantity = stock_info.get("factory_stock_quantity", "N/A")
            on_order_quantity = stock_info.get("on_order_quantity", "N/A")
            partner_stock_quantity = stock_info.get("partner_stock_quantity", "N/A")
            distributor_name = stock_info.get("distributor", {}).get("distributor_name", "N/A")
            distributor_region = stock_info.get("distributor", {}).get("distributor_region", "N/A")
            distributor_country = stock_info.get("distributor", {}).get("distributor_country", "N/A")
            lead_time = stock_info.get("lead_time", "N/A")
            lead_time_weeks = stock_info.get("lead_time_weeks", "N/A")
            lead_time_format = stock_info.get("lead_time_format", "N/A")
            image_url = stock_info.get("image_url", "N/A")
            buy_now_url = stock_info.get("buy_now_url", "N/A")

            # If there's a price list, iterate over each price break
            if isinstance(price_list, list) and price_list:
                for price in price_list:
                    unit_break_qty = price.get("unit_break", "N/A")
                    unit_price_eur = price.get("unit_price", "N/A")

                    new_data.append([
                        part_number, categories, sub_categories, sub_categories2, category,
                        manufacturer, description, lead_time, lead_time_weeks, lead_time_format,
                        unit_break_qty, unit_price_eur, quantity_in_stock, factory_stock_quantity,
                        on_order_quantity, partner_stock_quantity, distributor_name,
                        distributor_region, distributor_country, image_url, buy_now_url
                    ])
            else:
                # No price data or empty list
                unit_break_qty = "N/A"
                unit_price_eur = "N/A"
                new_data.append([
                    part_number, categories, sub_categories, sub_categories2, category,
                    manufacturer, description, lead_time, lead_time_weeks, lead_time_format,
                    unit_break_qty, unit_price_eur, quantity_in_stock, factory_stock_quantity,
                    on_order_quantity, partner_stock_quantity, distributor_name,
                    distributor_region, distributor_country, image_url, buy_now_url
                ])

    # Create a new DataFrame
    new_df = pd.DataFrame(new_data, columns=columns)
    
    # ------------------------------------------------------------------------------
    # 7. Data Cleaning and Standardization
    # ------------------------------------------------------------------------------
    new_df["Manufacturer"] = new_df["Manufacturer"].str.lower()

    name_mapping = {
        "white-rodgers": "white-rodgers",
        "whiterodgers": "white-rodgers",
        "american power conversion": "american power conversion",
        "american power conversion apc": "american power conversion",
        "apex tool group mfr.": "apex tool group",
        "apex tool group": "apex tool group",
        "cal": "cal controls",
        "cal controls": "cal controls",
        "bud industries inc.": "bud industries",
        "bud industries": "bud industries",
        "bud": "bud industries",
        "eaton hac": "eaton",
        "eaton": "eaton",
        "semikron danfoss": "semikron",
        "semikron": "semikron",
        "sick, inc.": "sick electronics",
        "sick electronics": "sick electronics",
        "tallysman": "tallysman",
        "tallysman wireless": "tallysman",
        "visaton": "visaton",
        "visaton gmbh & co": "visaton",
        "schneider electric-legacy relays": "schneider electric",
        "schneider electric": "schneider electric",
        "qualtek electronics": "qualtek electronics",
        "qualtek electronics corp": "qualtek electronics",
    }
    new_df["Manufacturer"] = new_df["Manufacturer"].replace(name_mapping)
    new_df["Manufacturer"] = new_df["Manufacturer"].str.split("/").str[0].str.strip()

    def remove_suffixes(name):
        pattern = r"\b(?:llc|inc|ltd|corporation|co|company|gmbh|s\.a|srl|plc|pvt|mfr|corp)\b\.?"
        return re.sub(pattern, "", name, flags=re.IGNORECASE).strip()

    new_df["Manufacturer"] = new_df["Manufacturer"].apply(remove_suffixes)
    new_df["Manufacturer"] = new_df["Manufacturer"].str.replace(r"[^\w\s]", "", regex=True)
    new_df["Manufacturer"] = new_df["Manufacturer"].str.replace(r"\s+", " ", regex=True).str.strip()

    # Fill blanks with 0 for quantity columns
    quantity_cols = [
        "Quantity_in_stock",
        "Factory_stock_quantity",
        "On_order_quantity",
        "Partner_stock_quantity"
    ]
    for col in quantity_cols:
        new_df[col] = pd.to_numeric(new_df[col], errors="coerce").fillna(0).astype(int)

    # Convert Unit_break_QTY to numeric
    new_df["Unit_break_QTY"] = pd.to_numeric(new_df["Unit_break_QTY"], errors="coerce").fillna(0).astype(int)

    # Convert Unit_price_EUR to numeric
    new_df["Unit_price_EUR"] = pd.to_numeric(new_df["Unit_price_EUR"], errors="coerce").fillna(0)

    # Convert lead time columns to lowercase
    time_cols = ["Lead_time", "Lead_time_weeks", "Lead_time_format"]
    for col in time_cols:
        new_df[col] = new_df[col].astype(str).str.lower()

    def calculate_new_lead_time(row):
        """
        Compute an integer-based "New_Lead_Time" (in days) 
        from the lead_time, lead_time_weeks, and lead_time_format columns.
        """
        lead_time = row["Lead_time"]
        lead_time_weeks = row["Lead_time_weeks"]
        lead_time_format = row["Lead_time_format"]

        def extract_number(text):
            numbers = re.findall(r"\d+", text)
            return int(numbers[0]) if numbers else 0

        # If both lead_time_format and lead_time_weeks are known
        if lead_time_format != "unknown" and lead_time_weeks != "unknown":
            lead_time_numeric = extract_number(lead_time)
            lead_time_weeks_numeric = extract_number(lead_time_weeks) * 7
            if lead_time_format == "weeks":
                return max(lead_time_numeric * 7, lead_time_weeks_numeric)
            elif lead_time_format == "days":
                return max(lead_time_numeric, lead_time_weeks_numeric)
            else:
                return 0

        # If lead_time_weeks == "unknown" but lead_time_format != "unknown"
        if lead_time_weeks == "unknown" and lead_time_format != "unknown":
            if lead_time.strip() == "" or lead_time == "unknown":
                return 0
            else:
                number = extract_number(lead_time)
                if lead_time_format == "weeks":
                    return number * 7
                elif lead_time_format == "days":
                    return number
                else:
                    return number * 7  # default assumption weeks

        # If lead_time_format == "unknown" and lead_time_weeks != "unknown"
        if lead_time_format == "unknown" and lead_time_weeks != "unknown":
            number = extract_number(lead_time)
            if "day" in lead_time:
                return number
            elif "week" in lead_time:
                return number * 7
            else:
                return number * 7  # default assumption weeks

        # If both are unknown
        if lead_time_weeks == "unknown" and lead_time_format == "unknown":
            number = extract_number(lead_time)
            if "week" in lead_time:
                return number * 7
            elif "day" in lead_time:
                return number
            elif lead_time.isdigit():
                return int(lead_time)
            else:
                return 0

        return 0

    new_df["New_Lead_Time"] = new_df.apply(calculate_new_lead_time, axis=1)

    # Final columns order
    final_columns = [
        "Categories", "Sub_Categories", "Sub_Categories2", "Part_Number", "Manufacturer",
        "Unit_break_QTY", "Unit_price_EUR", "Lead_time", "Lead_time_weeks", "Lead_time_format",
        "Quantity_in_stock", "Factory_stock_quantity", "On_order_quantity", 
        "Partner_stock_quantity", "Distributor_name", "Distributor_region", 
        "Distributor_country", "Image_URL", "Buy_now_URL", "Category", 
        "Description", "New_Lead_Time"
    ]
    new_df = new_df[final_columns]

    # --------------------------------------------------------------------------
    # 6. Add Timestamp Column (DataPulledTime)
    # --------------------------------------------------------------------------
    new_df["DataPulledTime"] = datetime.now()
    # --------------------------------------------------------------------------
    # 7. Insert into MySQL (append)
    # --------------------------------------------------------------------------
    connection_url = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}"
    try:
        engine = create_engine(connection_url)
        new_df.to_sql(name=mysql_table, con=engine, if_exists="append", index=False)
        print(f"Data inserted into MySQL database successfully at {datetime.now()}!")
    except Exception as e:
        print(f"Error inserting data into MySQL: {e}")

# ------------------------------------------------------------------------------
# Scheduling: run pull_and_insert_data() once per day at HH:MM and keep alive
# ------------------------------------------------------------------------------
schedule.every().day.at("21:30").do(pull_and_insert_data)

print("Scheduler started. The script will run 'pull_and_insert_data()' daily at 21:30.")

# Optional: run immediately on container startup (uncomment if desired)
pull_and_insert_data()

# Keep the container running, checking for tasks every minute
while True:
    schedule.run_pending()
    time.sleep(60)