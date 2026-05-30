# utils.py
import sqlite3
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from dateutil import parser
from decimal import Decimal, InvalidOperation

# Function to get a database connection
def get_connection(db_path="orders.db"):
    conn = sqlite3.connect(db_path)
    # Setting row_factory to sqlite3.Row allows us to access columns by name.
    conn.row_factory = sqlite3.Row
    return conn

# Function to create the ORDERS table if it doesn't exist.
def create_orders_table(conn):
    # Note:
    # SQLite does not have a dedicated date/time data type. So storing order_date as ISO 8601 string for efficient range queries. 
    # SQLite does support DECIMAL type, but it is stored as TEXT. Using Decimal to convey the intention of precision for amount.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ORDERS (
        order_id INTEGER PRIMARY KEY,
        customer_id TEXT NOT NULL,
        order_date TEXT NOT NULL,
        amount_usd DECIMAL(12,2) NOT NULL)
    """)

    # Create indexes for faster queries
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_customer_id ON ORDERS (customer_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_date ON ORDERS (order_date)
    """)
    conn.commit()

# This function converts various date formats into a consistent ISO 8601 format (YYYY-MM-DD).
def normalize_date(date_str: str) -> str:
    # Convert multiple date formats into ISO 8601 YYYY-MM-DD
    try:
        parsed = parser.parse(date_str)
        return parsed.strftime("%Y-%m-%d")
    except parser.ParserError:
        # Safety net. Try parsing with dayfirst=True for formats like Indian date format DD/MM/YYYY
        try:
            parsed = parser.parse(date_str, dayfirst=True)
            return parsed.strftime("%Y-%m-%d")
        except Exception:
            raise ValueError(f"Invalid date: {date_str}")

# Normalize amount and convert to USD using FX rates
def normalize_amount(amount_str: str, currency: str, FX_RATES: dict) -> Decimal:
    # Convert amount into USD
    if not amount_str or amount_str.strip() == "":
        amount = Decimal("0")
    else:
        try:
            amount = Decimal(amount_str)
        except InvalidOperation:
            amount = Decimal("0")

    currency = currency or "USD"
    rate = FX_RATES.get(currency.upper())

    if not rate:
        raise ValueError(f"Unsupported currency: {currency}")

    return amount * rate

# Function to set up logging
# In a real-world application, we would likely use a more robust logging configuration,
# possibly with different log levels and handlers for different environments (e.g., development vs production).
def setup_logger(log_filename: str):
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / log_filename

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    if logger.handlers:
        return logger
    
    # Using RotatingFileHandler to prevent log files from growing indefinitely.
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, # 10 MB
                                   backupCount=3)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    # Adding console logging too
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger
