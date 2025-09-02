import pandas as pd
from psycopg2.extras import execute_values
import re
import csv
import itertools

from db_connection import make_db_connection


# Not used, just here for future reference
def create_table_if_not_exists(cursor, conn):
    # horse_power INTEGER,
    # seating_capacity INTEGER,
    # cubic_capacity INTEGER,
    # no_of_cylinders INTEGER,

    # SQL statement to create the table, as provided in the prompt.
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS vahan_extract (
        customer_name VARCHAR(255),
        relation VARCHAR(255),
        relative_name VARCHAR(255),
        address TEXT,
        city VARCHAR(255),
        mobile_phone BIGINT,
        zip_code VARCHAR(6),
        locality VARCHAR(255),
        tax_mode VARCHAR(255),
        customer_email_address VARCHAR(255),
        manufacturer VARCHAR(255),
        model_category VARCHAR(255),
        model_name VARCHAR(255),
        model_variant VARCHAR(255),
        color VARCHAR(255),

        horse_power INTEGER,
        seating_capacity INTEGER,
        cubic_capacity INTEGER,
        no_of_cylinders INTEGER,


        fuel_used VARCHAR(255),
        type_of_body VARCHAR(255),
        frame_no VARCHAR(255),
        engine_no VARCHAR(255),
        manufacturing_month_and_year VARCHAR(7),
        invoice_no VARCHAR(255),
        invoice_date DATE,
        total_invoice_amount NUMERIC(10, 2),
        registration_date DATE,
        un_laden_weight INTEGER,
        insurance_name VARCHAR(255),
        insurance_start_date DATE,
        insurance_type VARCHAR(255),
        insurance_end_date DATE,
        cover_note_no VARCHAR(255),
        financier VARCHAR(255),
        hypothecation VARCHAR(255),
        customer_category_and_enquiry_category VARCHAR(255)
    );
    """
    cursor.execute(create_table_sql)
    conn.commit()
    print("Table 'vahan_extract' created successfully (if it did not already exist).")

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS vahan (
        invoice_no     VARCHAR(30),
        frame_no       VARCHAR(17),
        app_no         VARCHAR(16),
        regs_charges   NUMERIC(11, 2),
        penalty        NUMERIC(11, 2),
        remarks        VARCHAR(150),
        extra          VARCHAR(50),
        receipt_amt    NUMERIC(11, 2),
        receipt_dt     TIMESTAMP,
        bank_ref       VARCHAR(35),
        reg_no         VARCHAR(15),
        userid         VARCHAR(25)
    );
    """
    cursor.execute(create_table_sql)
    conn.commit()
    print("Table 'vahan' created successfully (if it did not already exist).")


def normalize_string(s):
    """Trim and remove multiple spaces"""
    if pd.isna(s):
        return s
    return ' '.join(str(s).split())

# Normalize column names (improved)
def normalize_column_name(name):
    name = name.strip().lower()
    name = name.replace("#", "no")              # handle "#"
    name = name.replace("&", "and")             # handle "&"
    name = re.sub(r'[^\w\s]', '', name)         # remove remaining punctuation
    name = re.sub(r'\s+', '_', name)            # convert all spaces to underscores
    name = re.sub(r'_+$', '', name)          # remove trailing underscores
    return name



# Check for wrong delimiter in CSV
# This function reads the first few lines of the CSV to detect the delimiter.
# If the detected delimiter is not a comma, it raises an error.
def read_comma_csv(file_path, encoding='utf-8', **kwargs):
    with open(file_path, 'r', encoding=encoding) as f:
        # Peek at first few lines
        # first_chunk = ''.join([next(f) for _ in range(5)])
        # Read up to 2 lines safely
        first_chunk = ''.join(itertools.islice(f, 2))

        if not first_chunk.strip():
            print(f"CSV file {file_path} is empty or contains only whitespace.")
            return pd.DataFrame()  # Return empty DataFrame
        detected = csv.Sniffer().sniff(first_chunk).delimiter

        if detected != ',':
            first_line = first_chunk.splitlines()[0]
            raise ValueError(
                f"Invalid delimiter detected: {repr(detected)}. "
                f"Expected ','. First line: {first_line}"
            )

        # Reset pointer for full read
        f.seek(0)
        return pd.read_csv(f, encoding=encoding, **kwargs)


def load_and_insert_csv(file_path):
    # Load CSV with encoding fallback
    try:
        df = read_comma_csv(file_path, encoding='utf-16', dtype=str)
    except UnicodeError:
        df = read_comma_csv(file_path, encoding='utf-8', dtype=str)

    # Converts "Manufacturing Month & Year" → "manufacturing_month_and_year"
    df.columns = [normalize_column_name(c) for c in df.columns]

    # Opt in to the new behavior (prevents FutureWarning now, default in 3.0)
    pd.set_option('future.no_silent_downcasting', True)
    
    # Replace blank strings and "NaN" strings with NaN
    df = df.replace(r'^\s*$', pd.NA, regex=True).infer_objects(copy=False)
    df = df.replace("NaN", pd.NA).infer_objects(copy=False)


    # Normalize all string columns
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].apply(normalize_string)

    # Format column names to match SQL
    df.columns = [c.strip().lower().replace(" ", "_").replace("#", "no").replace("-", "_") for c in df.columns]

    # Convert data types
    date_cols = ['invoice_date', 'registration_date', 'insurance_start_date', 'insurance_end_date']
    numeric_cols = ['horse_power', 'seating_capacity', 'cubic_capacity', 'no_of_cylinders',
                    'un_laden_weight', 'total_invoice_amount']

    for col in date_cols:
        if col in df.columns:
            # Day comes first in your data (Indian format) — prevents warning

            df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True).dt.date

    for col in numeric_cols:
        if col in df.columns:
            if col == 'total_invoice_amount':
                # Only clean if column is string/object
                if df[col].dtype == object:
                    df[col] = df[col].str.replace(r'[^\d.]', '', regex=True).replace('', pd.NA).astype(float)
                else:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce')

    # Connect to Database
    conn, cur = make_db_connection()

    # Insert into vahan table (invoice_no and frame_no)
    if 'invoice_no' in df.columns and 'frame_no' in df.columns:
        vahan_df = df[['invoice_no', 'frame_no']].dropna(subset=['invoice_no', 'frame_no'])

    # Step: Remove duplicates based on invoice_no
    if 'invoice_no' in df.columns:
        cur.execute("SELECT invoice_no FROM vahan_extract WHERE invoice_no IS NOT NULL")
        existing_invoice_nos = set(row[0] for row in cur.fetchall())

        initial_count = len(df)
        df = df[~df['invoice_no'].isin(existing_invoice_nos)]
        skipped_count = initial_count - len(df)
        print(f"Skipped {skipped_count} rows due to existing invoice_no.")

    # Prepare data
    columns = df.columns.tolist()
    # values = [tuple(x if not pd.isna(x) else None for x in row) for row in df.to_numpy()]
    values = [
        tuple(None if pd.isna(x) else x for x in row)
        for row in df.to_numpy()
    ]

    # Create INSERT query
    insert_query = f"""
        INSERT INTO vahan_extract ({', '.join(columns)})
        VALUES %s
    """



    # Execute batch insert
    execute_values(cur, insert_query, values)
    conn.commit()


    # Insert into vahan table (invoice_no and frame_no)

    # OPTIONAL: prevent duplicate invoice_no insertions in vahan
    cur.execute("SELECT invoice_no FROM vahan WHERE invoice_no IS NOT NULL")
    existing_vahan_invoices = set(row[0] for row in cur.fetchall())
    vahan_df = vahan_df[~vahan_df['invoice_no'].isin(existing_vahan_invoices)]

    vahan_values = [tuple(row) for row in vahan_df.to_numpy()]

    if vahan_values:
        insert_vahan_query = """
            INSERT INTO vahan (invoice_no, frame_no)
            VALUES %s
        """
        execute_values(cur, insert_vahan_query, vahan_values)
        conn.commit()
        print(f"Inserted {len(vahan_values)} rows into vahan table.")
    else:
        print("No new rows to insert into vahan table.")
    cur.close()
    conn.close()

    print("Data inserted successfully.")

# Usage
if __name__ == "__main__":
    file_path = r"d:\downloads\output - 2025-08-15T171251.870.CSV"
    # csv_path = "path/to/your_file.csv"  # <- UPDATE THIS
    # Load .env file into environment
    load_and_insert_csv(file_path)
