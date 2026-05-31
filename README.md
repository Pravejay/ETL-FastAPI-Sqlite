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

## Part 1: ETL Pipeline

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
python -m app.etl load data/orders.csv
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
python -m app.etl show-stats
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

## Part 2: FastAPI Service

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

Prometheus metrics endpoint implemented using `prometheus-fastapi-instrumentator`:

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
│   ├── app.py (FastAPI service)
│   ├── utils.py
│   ├── models.py
│   ├── llm_provider.py
│   ├── langgraph_agent.py
│   ├── semantic_search.py
│   ├── test.py
│
├── data/
│   └── orders.csv
│   ├── faiss.index
│   ├── metadata.json
│
├── logs/
│   └── etl.log
│   └── app.log
│   └── semantic_search.log
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
# Part 3: Deployment
Generated following artifacts as per requirements,
Dockerfile:
  - Multi-stage build (builder → runtime).
  - Non-root user.
  - Expose port 8000.
  - Include healthcheck.

Kubernetes manifests:
  - Deployment (with readiness/liveness probes).
  - Service (ClusterIP).
  - ConfigMap for configurable parameters (e.g., DB path).

**Successfully built and run Docker images using `GitHub Workflow Actions` as I could not run the Docker locally on laptop (using office laptop and it restricts Docker).**

---
# Part 4: AI-Augmented Query Layer + Architectural Extension

This project extends the Orders API with AI-powered capabilities for:

1. **Natural Language → SQL Querying** (`/orders/ask`)
2. **Semantic Search over Orders** (`/orders/semantic_search`)
3. **Multi-Step LangGraph Agent with Automatic SQL Retry**
4. **Enterprise Multi-Tenant Architecture Considerations**

---

# 4A. Natural Language Query Endpoint

## Endpoint

```http
POST /orders/ask
Content-Type: application/json

{
  "question": "What is the total revenue from customer C123 in the last 30 days?"
}
```

Example response:

```json
{
  "answer": "Total revenue: $4230.00",
  "sql_used": "SELECT SUM(amount_usd) AS total_revenue FROM orders WHERE customer_id = 'C123' AND order_date >= date('now','-30 days')",
  "rows": [
    {
      "total_revenue": 4230.00
    }
  ]
}
```

---

## Model Selection

### Chosen Model

**Gemini 3.1 Flash Lite**

### Why Gemini?

The solution requires converting natural language questions into executable SQLite SQL statements.

Gemini 3.1 Flash Lite was selected because:

- Excellent SQL generation quality
- Fast response times
- Large free-tier quota available through Google AI Studio
- Lower latency than larger reasoning models
- Simple API integration
- Cost-effective for production workloads
- **Last but not least - Why Gemini? Because it offers a free-tier with generous limits for testing while OpenAI, Anthropic doesn't even allow a single request!!. Installing Ollama locally had overhead of downloading the big models, yes, caching models would be an option.**

Compared to larger models, Gemini Flash Lite provides an excellent balance between:

- Accuracy
- Latency
- Cost

which is ideal for API-driven NL→SQL workloads.

---

## Schema Context

The model receives the database schema in its prompt:

```text
Table: ORDERS

Columns:
order_id INTEGER PRIMARY KEY
customer_id TEXT
order_date TEXT
amount_usd DECIMAL(12,2)

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
```

This constrains SQL generation to known columns and reduces hallucinations.

---

## SQL Validation

Only read-only SQL is allowed.

Accepted:

```sql
SELECT ...
```

Rejected:

```sql
DROP ...
DELETE ...
UPDATE ...
INSERT ...
```

This prevents accidental modification of data.

---

## Logging

Every request logs:

- User question
- Generated prompt
- Generated SQL
- Retry attempts

Example:

```text
Question:
What is the total revenue from customer C123 in the last 30 days?

Generated SQL:
SELECT SUM(amount_usd) AS total_revenue
FROM ORDERS
WHERE customer_id='C123'

Question:
"Which customer generated the highest sales?

Generated SQL:
SELECT customer_id
FROM ORDERS
GROUP BY customer_id
ORDER BY SUM(amount_usd) DESC
LIMIT 1;
```

---

# 4B. Semantic Search Endpoint

## Endpoint

```http
GET /orders/semantic_search?q=high value recent orders&top_k=5
```

Example response:

```json
[
  {
    "order_id": 1001,
    "customer_id": "C123",
    "amount_usd": 320.00,
    "order_date": "2024-03-15",
    "score": 0.91
  }
]
```

---

## Why Semantic Search?

Traditional SQL filtering requires exact conditions.

Users may ask:

```text
high value recent orders
```

which cannot easily be translated into simple SQL filters.

Semantic search allows retrieval based on meaning rather than exact keywords.

---

## Embedding Model

### Chosen Model

**all-MiniLM-L6-v2**

From the Sentence Transformers library.

---

## Why all-MiniLM-L6-v2?

Advantages:

- Small model (~80MB)
- Fast CPU inference
- Low memory footprint
- Excellent semantic similarity quality
- Widely adopted in production retrieval systems

For this assignment it provides an ideal trade-off between:

- Accuracy
- Speed
- Resource consumption

---

## Order Embeddings

Each order record is converted into text:

```text
customer C123, amount 320 USD, date 2024-03-15
```

The text is embedded using:

```python
SentenceTransformer("all-MiniLM-L6-v2")
```

Example vector:

```text
[0.123, -0.281, 0.998, ...]
```

---

## FAISS Index

Embeddings are stored in a FAISS index.

Benefits:

- Fast nearest-neighbor search
- In-memory retrieval
- Scales well to large datasets
- Production-proven vector search library

---

## Index Rebuild

Whenever:

```bash
python -m app.etl load data/orders.csv
```

is executed,

the ETL pipeline automatically:

1. Loads new data
2. Recreates embeddings
3. Rebuilds the FAISS index

This ensures semantic search always reflects the latest data.

**`Handling Concurrency during rebuild`**

To handle the concurrency use-cases, I would use Reentrant Lock before rebuilding the index or searching for orders.
Additionally, we could build an alternative index parallely and swap with the global index upon rebuild completion.

---

# 4C. LangGraph Multi-Step Agent

The initial implementation could generate SQL and execute it immediately.

However, LLM-generated SQL may occasionally contain mistakes.

Examples:

```sql
SELECT SUM(revenue)
FROM orders;
```

where:

```text
revenue
```

does not exist.

To improve robustness, a LangGraph workflow was implemented.

---

## Graph Structure

```text
Question
    │
    ▼
sql_writer
    │
    ▼
sql_executor
    │
 ┌──┴──────┐
 │ Success │
 │         │
 ▼         ▼
 END    Retry
            │
            ▼
      sql_writer
```

---

## Node 1 — sql_writer

Responsibilities:

- Receives user question
- Receives schema context
- Calls Gemini
- Generates SQL

Example:

Question:

```text
What is the total revenue generated in the last 30 days?
```

Generated SQL:

```sql
SELECT SUM(revenue)
FROM orders;
```

---

## Node 2 — sql_executor

Responsibilities:

- Execute generated SQL
- Capture execution errors
- Return query results

Example error:

```text
sqlite3.OperationalError:
no such column: revenue
```

---

## Automatic Retry

When execution fails:

1. Error message is appended to the next prompt.
2. LangGraph routes back to `sql_writer`.
3. Gemini generates corrected SQL.

Example:

Initial SQL:

```sql
SELECT SUM(revenue)
FROM orders;
```

Error:

```text
no such column: revenue
```

Corrected SQL:

```sql
SELECT SUM(amount_usd) AS "Total Revenue"
FROM orders;
```

---

## Example Multi-Hop Execution

```text
Question
↓
What is the total revenue generated in the last 30 days?

sql_writer
↓
SELECT SUM(revenue)
FROM ORDERS
WHERE order_date >= date('now','-30 days')

sql_executor
↓
ERROR:
no such column: revenue

Router
↓
Retry

sql_writer
↓
SELECT SUM(amount_usd) AS "Total Revenue"
FROM ORDERS
WHERE order_date >= date('now','-30 days')

sql_executor
↓
SUCCESS

Answer
↓
Total revenue: 12540.50
```

This demonstrates automatic self-correction of LLM-generated SQL.

---

# LangChain Usage

LangChain is used as the foundational orchestration layer for:

- Prompt management
- LLM abstraction (This project already implements an abstraction layer)
- Future extensibility

Benefits:

- Easy provider replacement
- Standardized interfaces
- Integration with LangGraph

The application can switch between:

- Gemini
- OpenAI
- Anthropic
- Ollama

without changing the agent workflow.

---

# Enterprise Multi-Tenant Architecture Extension

The assignment implementation is single-tenant.

For enterprise deployment across multiple customers and regions, the architecture can be extended as follows.

---

## Regional Deployment

Requirements:

- EU customers → eu-west
- US customers → us-east
- KSA customers → local cloud

High-level architecture:

```text
API Gateway
      │
      ▼
Tenant Routing Layer
      │
 ┌────┼─────┐
 ▼    ▼     ▼

EU   US    KSA

FastAPI + LangGraph
Gemini / Llama
Tenant DB
Tenant Vector Index
```

---

## Tenant Isolation for Vector Search

### One FAISS Index per Tenant

Each customer receives:

```text
tenant_a.index
tenant_b.index
tenant_c.index
```

Pros:

- Strong isolation
- Easier compliance
- Simplified residency guarantees

Cons:

- More memory consumption
- Additional operational overhead

### Trade-off accepted:

Higher infrastructure cost in exchange for stronger security and compliance guarantees.

---

## Tenant-Specific LLM Routing

Some customers may prohibit cloud-hosted models.

Examples:

| Tenant | LLM Backend |
|----------|----------|
| Retail EU | Gemini |
| Bank KSA | Private Llama |
| Healthcare US | Private Llama |

Routing occurs through an abstract provider layer:

```python
provider = llm_factory(tenant_id)
```

This allows LangGraph to remain model-agnostic.

---

## PII Protection

Order data contains:

- customer_id
- amount_usd

Before sending requests to an LLM:

### Schema Minimization

Expose only required schema fields.

### SQL Validation

Allow only read-only SQL (SELECT queries only).

### Prompt Injection Protection

Reject malicious prompts attempting to bypass system instructions.

### Tenant Isolation

Restrict queries to the tenant's own data source.

---

## Cloud vs On-Prem LLM

### Cloud (Gemini)

Additional controls:

- PII masking
- Regional routing
- Encryption in transit

### On-Prem (Llama)

Benefits:

- No external data transfer
- Easier regulatory compliance
- Full control of inference infrastructure

---

# Key Architectural Decision

The highest-leverage architectural decision is:

**One vector index per tenant.**

Why?

- Eliminates cross-tenant data leakage risk.
- Simplifies compliance and audits.
- Enables clean data residency boundaries.

Trade-off accepted:

- Higher memory consumption.
- More operational overhead.

This choice prioritizes security and enterprise compliance over infrastructure efficiency.

**`Final note`**:

The highest-leverage architectural decision was choosing deployment-level isolation instead of application-level tenant filtering. Each tenant (or tenant region) owns its own database, vector index, and AI inference path. This significantly reduces the risk of cross-tenant data leakage through SQL execution, vector retrieval, prompt construction, caching, and logging. The trade-off is increased infrastructure and operational cost, but I accepted that trade-off because the stated requirements (EU, US, and KSA data residency) indicate that compliance, auditability, and security are more important than maximizing infrastructure efficiency.
