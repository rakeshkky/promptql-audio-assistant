import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# Path to the directory containing TSV files
DATA_DIR = 'iem_measurements'

def load_data_to_db():
    # Connect to the PostgreSQL database using the URL
    pg_url = os.getenv('PG_URL')
    if not pg_url:
        print("Please set the PG_URL environment variable with the PostgreSQL connection string.")
        return
    conn = psycopg2.connect(pg_url)
    cursor = conn.cursor()

    try:
        # Loop through each TSV file in the data directory
        for filename in os.listdir(DATA_DIR):
            if filename.endswith('.tsv'):
                iem_name = filename.replace('.tsv', '')

                # Insert or fetch the IEM ID for the IEM name
                cursor.execute("INSERT INTO iems (iem_name) VALUES (%s) ON CONFLICT (iem_name) DO NOTHING RETURNING iem_id;", (iem_name,))
                if cursor.rowcount > 0:
                    iem_id = cursor.fetchone()[0]  # New IEM, proceed with data insertion
                else:
                    # IEM exists; get its id and check if it already has frequency response data
                    cursor.execute("SELECT iem_id FROM iems WHERE iem_name = %s;", (iem_name,))
                    iem_id = cursor.fetchone()[0]

                    # Check if frequency data already exists for this IEM
                    cursor.execute("SELECT 1 FROM frequency_responses WHERE iem_id = %s LIMIT 1;", (iem_id,))
                    if cursor.fetchone():
                        print(f"Data for {iem_name} already exists. Skipping insertion.")
                        continue  # Skip to the next file

                # Read TSV file into DataFrame, excluding phase column
                file_path = os.path.join(DATA_DIR, filename)
                df = pd.read_csv(file_path, sep='\t', comment='*', usecols=[0, 1], names=['frequency_hz', 'amplitude'])

                # Prepare frequency and amplitude data for batch insertion
                values = [(iem_id, row['frequency_hz'], row['amplitude']) for _, row in df.iterrows()]

                # Insert data into `frequency_responses` table
                execute_values(cursor, "INSERT INTO frequency_responses (iem_id, frequency_hz, amplitude) VALUES %s", values)
                conn.commit()
                print(f"Data for {iem_name} inserted successfully.")

    except Exception as e:
        conn.rollback()
        print(f"Error occurred: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    load_data_to_db()
