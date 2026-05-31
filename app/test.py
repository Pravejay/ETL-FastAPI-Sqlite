# Test file for the application
from app.llm_provider import llm

print(
    llm.generate_sql(
        "What is the total revenue from customer C123 in the last 30 days?"
        #"How many orders were placed in the last 7 days and what is the total amount in USD?"
    )
)