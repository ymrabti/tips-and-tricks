import pandas as pd
from sqlalchemy import create_engine

# CSV file path
csv_file = "SALARIES.csv"

# Read CSV into DataFrame
df = pd.read_csv(csv_file, on_bad_lines='warn', low_memory=False)

# MySQL connection setup
engine = create_engine("mysql+pymysql://root@localhost/admin_dashboard")

# Table name to create
table_name = "salaires"

# Write to MySQL (auto-creates the table schema based on DataFrame)
df.to_sql(table_name, con=engine, if_exists="replace", index=False)

print(f"✅ Table '{table_name}' created and data inserted.")
