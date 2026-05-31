# etl.py
# Extract, Transform, Load (ETL) script to process orders.csv and load into SQLite database orders.db
import argparse
import argparse
import csv
import os
import sqlite3
from decimal import Decimal

from app.semantic_search import rebuild_index
from app.utils import get_connection, normalize_date, normalize_amount, create_orders_table, setup_logger

# These constants could be moved to a config file or environment variables in a real-world application.
DB_PATH = os.getenv("DB_PATH", "orders.db")

# Dictionary to hold FX rates for currency conversion.
# In a real-world scenario, this would likely come from an external service or config.
FX_RATES = {
    "USD": Decimal("1.0"),
    "EUR": Decimal("1.1"),
}

# Set up logger
logger = setup_logger("etl.log")

# Load the CSV file, normalize the data, and insert into the SQLite database.
# Note: For simplicity, this script assumes that the CSV file has the following columns:
# order_id, customer_id, order_date, amount, currency
def process_orders_csv(csv_path: str):
    logger.info("Starting ETL pipeline")
    # Create orders table if it doesn't exist
    conn = get_connection(DB_PATH)
    create_orders_table(conn)

    processed_rows = 0
    inserted_rows = 0
    skipped_rows = 0
    duplicate_rows = 0

    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        # Not using Pydantic model here for more flexible error handling during ETL and
        # to avoid overhead of validation on each row!
        for row_num, row in enumerate(reader, start=1):
            try:
                order_id = int(row.get("order_id"))
                customer_id = row.get("customer_id")
                processed_rows += 1

                # Drop rows with missing order ID or customer ID.
                if not order_id or not customer_id:
                    skipped_rows += 1
                    logger.warning(f"Skipping row {row_num} due to missing order_id or customer_id")
                    continue

                normalized_date = normalize_date(
                    row.get("order_date", "")
                )

                amount_usd = normalize_amount(
                    row.get("amount", ""),
                    row.get("currency", "USD"),
                    FX_RATES
                )

                conn.execute("""
                    INSERT INTO ORDERS (order_id, customer_id, order_date, amount_usd)
                    VALUES (?, ?, ?, ?)""", (order_id, customer_id.upper(), normalized_date,
                        str(amount_usd)))
                inserted_rows += 1

            except sqlite3.IntegrityError:
                duplicate_rows += 1
                logger.warning(f"Row {row_num} has duplicate order_id skipped: {order_id}")
            except Exception as e:
                skipped_rows += 1
                logger.error(f"Row {row_num} skipped due to error: {e}")

    conn.commit()
    conn.close()
    logger.info(f"ETL Summary: Processed {processed_rows} rows, Inserted {inserted_rows} rows, "
                f"Skipped {skipped_rows} rows, Duplicates {duplicate_rows} rows")
    logger.info("ETL pipeline completed successfully")

    # For AI agent to perform semantic search.
    # Rebuild the FAISS index after loading new data into the database to ensure semantic search is up-to-date.
    rebuild_index(DB_PATH)
    logger.info("FAISS index rebuilt successfully after ETL load")


# Function to show statistics about the orders in the database
def show_stats():
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total_orders,
            COALESCE(SUM(amount_usd), 0),
            COALESCE(AVG(amount_usd), 0)
        FROM ORDERS
    """)

    result = cursor.fetchone()
    conn.close()

    total_orders = result[0]
    total_revenue = result[1]
    avg_order_value = result[2]

    logger.info(f"Total Orders: {total_orders}")
    logger.info(f"Total Revenue (USD): {Decimal(total_revenue):.2f}")
    logger.info(f"Average Order Value (USD): {Decimal(avg_order_value):.2f}")
    logger.info("Orders stats displayed successfully")


# Command-line interface
# This allows us to run the ETL process or show stats from the command line.
def main():
    logger.info("Starting main function")
    parser = argparse.ArgumentParser(description="Orders ETL Pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # load command
    load_parser = subparsers.add_parser("load", help="Load CSV into SQLite")
    load_parser.add_argument("csv_path", help="Path to Orders CSV file")
    # show-stats command
    subparsers.add_parser("show-stats",help="Show order statistics")

    args = parser.parse_args()

    if args.command == "load":
        logger.info("Loading CSV into SQLite")
        process_orders_csv(args.csv_path)

    elif args.command == "show-stats":
        logger.info("Showing order statistics")
        show_stats()


# Entry point for the script
if __name__ == "__main__":
    main()