# models.py
# Pydantic models for API responses.
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

class OrderResponse(BaseModel):
    order_id: int
    customer_id: str = Field(..., pattern=r"^[A-Za-z0-9]+$")
    order_date: date
    amount_usd: Decimal

    model_config = {
        "json_encoders": {
            Decimal: lambda v: str(v)
        }
    }

class StatsResponse(BaseModel):
    total_revenue: Decimal
    avg_order_value: Decimal
    orders_per_day: dict[str, int]

    model_config = {
        "json_encoders": {
            Decimal: lambda v: str(v)
        }
    }

# Models for /orders/ask service
class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str
    sql_used: str
    rows: list[dict]
    retries: int = 0

# Model for /orders/semantic_search service
class SemanticSearchResult(BaseModel):
    order_id: int
    customer_id: str
    amount_usd: Decimal
    order_date: date
    score: float

# Schema context for LLM to generate SQL queries based on user questions.
SCHEMA_CONTEXT = """
Table: ORDERS

Columns:
order_id INTEGER PRIMARY KEY
customer_id TEXT
order_date TEXT
amount_usd DECIMAL(12,2)

Example queries:
SELECT *
FROM ORDERS
WHERE customer_id='C001';

SELECT SUM(amount_usd)
FROM ORDERS;

Rules:
Generate SQL only.
Use table ORDERS only
Use only existing columns.
Never reference columns other than order_id, customer_id, order_date, amount_usd
Never invent columns or tables.
Return Only SELECT statements.

If question cannot be answered, return exactly:
UNANSWERABLE

For aggregate functions use the following aliases:
SUM(amount_usd)      -> AS "Total Revenue"
AVG(amount_usd)      -> AS "Average Order Value"
COUNT(*)             -> AS "Order Count"
"""
