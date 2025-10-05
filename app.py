import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

DB_PATH = "C:\Users\yash1\OneDrive\Desktop\local_food\database.db"

@st.cache_data(ttl=60)
def get_conn():
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
return conn

@st.cache_data(ttl=60)
def load_tables(conn):
tables = {}
try:
tables['providers'] = pd.read_sql_query("SELECT * FROM providers", conn)
except Exception:
tables['providers'] = pd.DataFrame()
try:
tables['receivers'] = pd.read_sql_query("SELECT * FROM receivers", conn)
except Exception:
tables['receivers'] = pd.DataFrame()
try:
tables['food_listings'] = pd.read_sql_query("SELECT * FROM food_listings", conn)
except Exception:
tables['food_listings'] = pd.DataFrame()
try:
tables['claims'] = pd.read_sql_query("SELECT * FROM claims", conn)
except Exception:
tables['claims'] = pd.DataFrame()
return tables

def sidebar_filters(tables):
st.sidebar.header("Filters")
listings = tables.get('food_listings', pd.DataFrame())
city = st.sidebar.selectbox("City", options=["All"] + sorted(listings['location'].dropna().unique().tolist()))
provider_type = st.sidebar.selectbox("Provider Type", options=["All"] + sorted(listings['provider_type'].dropna().unique().tolist()))
food_type = st.sidebar.selectbox("Food Type", options=["All"] + sorted(listings['food_type'].dropna().unique().tolist()))
meal_type = st.sidebar.selectbox("Meal Type", options=["All"] + sorted(listings['meal_type'].dropna().unique().tolist()))
return city, provider_type, food_type, meal_type

def filter_listings(df, city, provider_type, food_type, meal_type):
if df is None or df.empty:
return pd.DataFrame()
out = df.copy()
if city and city != "All":
out = out[out['location'] == city]
if provider_type and provider_type != "All":
out = out[out['provider_type'] == provider_type]
if food_type and food_type != "All":
out = out[out['food_type'] == food_type]
if meal_type and meal_type != "All":
out = out[out['meal_type'] == meal_type]
return out

def show_dashboard(tables):
st.header("Dashboard — EDA")
df = tables.get('food_listings', pd.DataFrame())
if df.empty:
st.info("No food listings available. Run data_prep.py to populate the DB.")
return

```
st.subheader("Top food types")
top_foods = df['food_type'].value_counts().reset_index().rename(columns={'index':'food_type','food_type':'count'})
st.bar_chart(top_foods.set_index('food_type'))

st.subheader("Listings per city")
per_city = df['location'].value_counts().reset_index().rename(columns={'index':'city','location':'count'})
st.bar_chart(per_city.set_index('city'))

st.subheader("Quantity per provider (top 10)")
qty = df.groupby('provider_id')['quantity'].sum().reset_index().sort_values('quantity', ascending=False).head(10)
st.dataframe(qty)

st.subheader("Expiry dates distribution")
if 'expiry_date' in df.columns:
    ex = pd.to_datetime(df['expiry_date'], errors='coerce')
    ex = ex.dropna()
    if not ex.empty:
        ex_counts = ex.dt.to_period('D').value_counts().sort_index()
        st.line_chart(ex_counts.astype(int))
```

def show_listings_page(tables, conn):
st.header("Food Listings")
listings = tables.get('food_listings', pd.DataFrame())
claims = tables.get('claims', pd.DataFrame())
st.write("Total listings:", len(listings))
city, provider_type, food_type, meal_type = sidebar_filters(tables)
filtered = filter_listings(listings, city, provider_type, food_type, meal_type)
st.dataframe(filtered)

```
st.subheader("Claim a listing")
with st.form("claim_form"):
    c_food_id = st.number_input("Food ID to claim", min_value=1, step=1)
    c_receiver_id = st.number_input("Your Receiver ID", min_value=1, step=1)
    submitted = st.form_submit_button("Make Claim")
    if submitted:
        cur = conn.cursor()
        cur.execute("INSERT INTO claims(food_id, receiver_id, status, timestamp) VALUES (?, ?, ?, ?)",
                    (int(c_food_id), int(c_receiver_id), 'Pending', datetime.now()))
        conn.commit()
        st.success("Claim submitted. Refresh the page to see updated claims.")
```

def show_providers_page(tables, conn):
st.header("Providers")
providers = tables.get('providers', pd.DataFrame())
st.dataframe(providers)
st.subheader("Add provider")
with st.form("add_provider"):
name = st.text_input("Name")
ptype = st.text_input("Type")
address = st.text_input("Address")
city = st.text_input("City")
contact = st.text_input("Contact")
submitted = st.form_submit_button("Add")
if submitted:
cur = conn.cursor()
cur.execute("INSERT INTO providers(name, type, address, city, contact) VALUES (?, ?, ?, ?, ?)",
(name, ptype, address, city, contact))
conn.commit()
st.success("Provider added.")

def show_receivers_page(tables, conn):
st.header("Receivers")
receivers = tables.get('receivers', pd.DataFrame())
st.dataframe(receivers)
st.subheader("Add receiver")
with st.form("add_receiver"):
name = st.text_input("Name", key="rname")
rtype = st.text_input("Type", key="rtype")
city = st.text_input("City", key="rcity")
contact = st.text_input("Contact", key="rcontact")
submitted = st.form_submit_button("Add receiver")
if submitted:
cur = conn.cursor()
cur.execute("INSERT INTO receivers(name, type, city, contact) VALUES (?, ?, ?, ?)",
(name, rtype, city, contact))
conn.commit()
st.success("Receiver added.")

def show_admin_reports(tables, conn):
st.header("Reports (SQL Queries)")
st.write("Click a query to run and view results.")
# Example queries (full list in EDA_and_SQL_queries.txt)
queries = {
"1. Providers and receivers count per city": """
SELECT city,
(SELECT COUNT(1) FROM providers p WHERE p.city = city_table.city) as providers_count,
(SELECT COUNT(1) FROM receivers r WHERE r.city = city_table.city) as receivers_count
FROM (
SELECT city FROM providers
UNION
SELECT city FROM receivers
) AS city_table;
""",
"5. Total quantity available": "SELECT SUM(quantity) as total_quantity FROM food_listings;",
"10. Claim status distribution": "SELECT status, COUNT(1) as count FROM claims GROUP BY status;",
}

```
for label, q in queries.items():
    if st.button(label):
        try:
            df = pd.read_sql_query(q, conn)
            st.dataframe(df)
        except Exception as e:
            st.error(f"Query failed: {e}")
```

def main():
st.title("Local Food Wastage Management System")
conn = get_conn()
tables = load_tables(conn)

```
menu = st.sidebar.selectbox("Go to", ["Dashboard", "Listings", "Providers", "Receivers", "Reports", "Raw Tables"])
if menu == "Dashboard":
    show_dashboard(tables)
elif menu == "Listings":
    show_listings_page(tables, conn)
elif menu == "Providers":
    show_providers_page(tables, conn)
elif menu == "Receivers":
    show_receivers_page(tables, conn)
elif menu == "Reports":
    show_admin_reports(tables, conn)
elif menu == "Raw Tables":
    st.subheader("Raw DB tables")
    for k, v in tables.items():
        st.markdown(f"**{k}**")
        st.dataframe(v)
```

if **name** == "**main**":
main()
