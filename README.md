# Orders ETL Pipeline and FastAPI Service

## Overview

This project implements an end-to-end ETL pipeline and FastAPI service for processing order data from CSV files.

### Features

* Extract order data from CSV files
* Normalize inconsistent date formats into ISO 8601 (`YYYY-MM-DD`)
* Convert all amounts into USD using fixed exchange rates
* Handle missing and invalid data
* Store cleaned data in SQLite
* Expose REST APIs using FastAPI
* Prometheus metrics endpoint
* In-memory caching for statistics endpoint using TTLCache
* CLI support for ETL operations

---

## Dataset Schema

Sample input CSV file follow the schema:

```csv
order_id,customer_id,order_date,amount,currency
1001,C123,2020-01-01,200,USD
1002,C124,01/02/2020,150,EUR
```

### Assumptions

* `order_id` is unique
* `customer_id` is alphanumeric
* `order_date` may contain inconsistent formats
* Missing amount values are set to `0`
* Missing currency values default to `USD`

---

## ETL Pipeline

### Transformations

#### Date Normalization

Converts:

```text
2020-01-01
01/02/2020
1-Jan-2020
```

into:

```text
2020-01-01
2020-01-02
2020-01-01
```

#### Currency Conversion

Exchange rates:

```text
1 USD = 1.0 USD
1 EUR = 1.1 USD
```

Examples:

```text
100 USD -> 100.00 USD
100 EUR -> 110.00 USD
```

#### Data Validation

| Condition           | Action     |
| ------------------- | ---------- |
| Missing order_id    | Drop row   |
| Missing customer_id | Drop row   |
| Missing amount      | Set to 0   |
| Invalid amount      | Set to 0   |
| Missing currency    | Assume USD |

---

## SQLite Schema

Note:
SQLite does not have a dedicated date/time data type. So storing order_date as ISO 8601 string for efficient range queries. 
SQLite does support DECIMAL type, but it is stored as TEXT. Using Decimal to convey the intention of precision for amount.

```sql
CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id TEXT NOT NULL,
    order_date TEXT NOT NULL,
    amount_usd DECIMAL(12,2) NOT NULL
);
```

Indexes:

```sql
CREATE INDEX idx_customer_id
ON orders(customer_id);
```
```sql
CREATE INDEX idx_order_date
ON orders(order_date);
```

---

## ETL Commands

### Load CSV Data
I have not used Pydantic models here for more flexible error handling during ETL and to avoid overhead of validation on each row. Load and transform CSV data into SQLite:

```bash
python etl.py load data/orders.csv
```

Example output:

```text
INFO - Loading CSV into SQLite
INFO - Starting ETL pipeline
INFO - ETL Summary: Processed 6 rows, Inserted 5 rows, Skipped 0 rows, Duplicates 1 rows
INFO - ETL pipeline completed successfully
```

---

### Show Statistics

Display revenue and average order value:

```bash
python etl.py show-stats
```

Example output:

```text
INFO - Showing order statistics
INFO - Total Orders: 5
INFO - Total Revenue (USD): 2065.00
INFO - Average Order Value (USD): 413.00
INFO - Orders stats displayed successfully
```

---

## FastAPI Service

### Start the API

From the project root:

```bash
uvicorn app.app:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000/
```

---

## API Documentation

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

OpenAPI JSON:

```text
http://127.0.0.1:8000/openapi.json
```

---

## API Endpoints

### Health Check

#### Request

```http
GET /healthz
```

#### Response

```json
{
  "status": "OK"
}
```

---

### Get Orders by Customer

#### Request

```http
GET /orders/customer/{customer_id}
```

#### Example

```http
GET /orders/customer/C123
```

#### Response

```json
[
  {
    "order_id": 1001,
    "customer_id": "C123",
    "order_date": "2020-01-01",
    "amount_usd": "200"
  }
]
```

---

### Get Statistics
Note: Not implementing pre-computed aggregates or Materialized View here for assessment purpose.
Caching the order stats for 60 seconds (TTL) to avoid hitting DB for every request. cachetools package has been used to maintain the cache efficiently.
#### Request

```http
GET /orders/stats
```

#### Response

```json
{
  "total_revenue": "15230.50",
  "avg_order_value": "245.65",
  "orders_per_day": {
    "2020-01-01": 12,
    "2020-01-02": 15
  }
}
```

---

### Get Recent Orders

Returns orders from the last N days. For performance reasons, limiting max to 365 days.

#### Request

```http
GET /orders/recent?days=30
```

#### Example

```http
GET /orders/recent?days=7
```

#### Response

```json
[
  {
    "order_id": 1005,
    "customer_id": "C456",
    "order_date": "2025-05-22",
    "amount_usd": "110"
  }
]
```

---

## Metrics

Prometheus metrics endpoint implemented using prometheus-fastapi-instrumentator:

```http
GET /metrics
```

Example metrics:

```text
http_requests_total
http_request_duration_seconds
http_requests_inprogress
```

Metrics can be scraped by Prometheus and visualized in Grafana.

---

## Caching

The `/orders/stats` endpoint uses an in-memory TTL cache.

Configuration:

```text
TTL = 60 seconds
```

Benefits:

* Reduced database load
* Faster response times
* Simple implementation

---

## Logging

ETL logs are written to:

```text
logs/etl.log
```

App (FastAPI) logs are written to:

```text
logs/app.log
```

Logging includes:

* ETL start/end
* Rows processed
* Rows inserted
* Duplicate order IDs
* Validation failures
* Unexpected exceptions
* FastAPI service actions and exceptions, if any.
---

## Project Structure

```text
sap-test/
│
├── app/
│   ├── __init__.py
│   ├── etl.py
│   ├── app.py
│   ├── utils.py
│   ├── models.py
│
├── data/
│   └── orders.csv
│
├── logs/
│   └── etl.log
│   └── app.log
│
├── k8s/
│   └── configmap.yaml
│   └── deployment.yaml
│   └── service.yaml
│
├── orders.db
├── Dockerfile
├── .dockerignore
├── requirements.txt
└── README.md
```

---
