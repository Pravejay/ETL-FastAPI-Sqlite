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
