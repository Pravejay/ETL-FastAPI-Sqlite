# api.py
# FastAPI application to serve orders data from SQLite database.
from datetime import timedelta
from decimal import Decimal
from datetime import date
import os

from fastapi import FastAPI, HTTPException, Query, Query
from prometheus_fastapi_instrumentator import Instrumentator

from cachetools import TTLCache

from .models import OrderResponse, StatsResponse
from .utils import get_connection, setup_logger

# FastAPI application instance
app = FastAPI(title="Orders API", version="1.0.0")

# Instrumentator for Prometheus metrics. In a production application, we would likely use this to expose metrics about API usage, performance, and errors.
Instrumentator().instrument(app).expose(app)

# In a production application, we would likely use a caching layer like Redis to cache results of expensive queries and reduce load on the database.
# Cache stats for 60 seconds to reduce load on the database for expensive queries.
stats_cache = TTLCache(maxsize=1, ttl=60)

# These constants could be moved to a config file or environment variables in a real-world application.
DB_PATH = os.getenv("DB_PATH", "orders.db")

# Set up logger
logger = setup_logger("app.log")

# Root endpoint for welcome message.
@app.get("/")
def root():
    return {"message": "Welcome to the Orders API"}


# Health check endpoint to verify that the API is running.
# This can be used by monitoring tools or load balancers to check the health of the application.
@app.get("/healthz")
def healthz():
    return {"status": "OK"}


# Endpoint to get all orders for a specific customer, sorted by order date in descending order.
@app.get("/orders/customer/{customer_id}", response_model=list[OrderResponse])
def get_customer_orders(customer_id: str):
    logger.info(f"Fetching orders for customer_id: {customer_id}")
    conn = get_connection(DB_PATH)
    rows = conn.execute("""
        SELECT * FROM ORDERS
        WHERE customer_id = ?
        ORDER BY order_date DESC
    """, (customer_id.upper(),)).fetchall()

    conn.close()
    if not rows:
        logger.error(f"No orders found for customer_id: {customer_id}")
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )
    
    logger.info(f"Returning orders for customer_id: {customer_id}")
    return [dict(row) for row in rows]


# Endpoint to get statistics about orders.
# This endpoint returns the total revenue, average order value, and the number of orders per day.
@app.get("/orders/stats", response_model=StatsResponse)
def get_stats():
    logger.info("Fetching order stats.")
    # Check if cached stats is still valid. If so, return cached stats to reduce load on the database.
    cached_result = stats_cache.get("stats")
    if cached_result is not None:
        logger.info("Returning cached order stats.")
        return cached_result

    conn = get_connection(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(amount_usd), 0), COALESCE(AVG(amount_usd), 0)
        FROM ORDERS
    """)

    total_revenue, avg_order_value = cursor.fetchone()

    rows = conn.execute("""
        SELECT order_date, COUNT(*) as count
        FROM ORDERS
        GROUP BY order_date
    """).fetchall()

    conn.close()

    orders_per_day = {
        row["order_date"]: row["count"]
        for row in rows
    }

    result = {
        "total_revenue": Decimal(str(total_revenue)),
        "avg_order_value": Decimal(str(avg_order_value)),
        "orders_per_day": orders_per_day
    }
    logger.debug(f"Order stats calculated: {result}")
    # Cache the result to reduce load on the database for expensive queries.
    stats_cache["stats"] = result
    logger.info("Order stats cached.")
    
    return result


# Endpoint to get recent orders within the last N days, sorted by order date in descending order.
# The 'days' query parameter specifies how many days back to look for orders.
# For performance reasons, allowing a positive integer between 1 and 365.
@app.get("/orders/recent", response_model=list[OrderResponse])
def get_recent_orders(days: int = Query(..., gt=0, le=365)):
    logger.info(f"Fetching recent orders from the last {days} days.")
    cutoff_date = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection(DB_PATH)

    rows = conn.execute("""
        SELECT
            order_id,
            customer_id,
            order_date,
            amount_usd
        FROM ORDERS
        WHERE order_date >= ?
        ORDER BY order_date DESC
    """, (cutoff_date,)).fetchall()

    conn.close()
    logger.info(f"Returning recent orders from the last {days} days.")
    return [dict(row) for row in rows]

