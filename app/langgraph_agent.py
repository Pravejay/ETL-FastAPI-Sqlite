# LangGraph agent for handling user interactions and generating responses.

import os
from langgraph.graph import END, StateGraph
import sqlglot

from typing import TypedDict

from app.utils import get_connection, setup_logger
from app.llm_provider import llm

DB_PATH = os.getenv("DB_PATH", "orders.db")

# Set up logger
logger = setup_logger("ai.log")

class AgentState(TypedDict):
    question: str
    sql: str
    rows: list
    answer: str
    error: str
    retries: int

def sql_writer(state: AgentState):
    logger.info(f"langraph_agent.sql_writer invoked with question: {state['question']} and error: {state.get('error')}")
    sql = llm.generate_sql(
        question = state["question"],
        error = state.get("error")
    )
    return {
        **state,
        "sql": sql
    }

def sql_executor(state: AgentState):
    logger.info(f"langraph_agent.sql_executor invoked with SQL: {state['sql']}")
    sql = state["sql"]
    try:
        if sql == "UNANSWERABLE":
            return {
                **state,
                "error": "UNANSWERABLE"
            }
        # Returns a single Expression object if the SQL is valid, otherwise raises an exception.
        sqlglot.parse_one(sql)

        if not sql.upper().startswith("SELECT"):
            raise ValueError("Only SELECT allowed in SQL queries!")

        # Execute the SQL query against the SQLite database and fetch results.
        conn = get_connection(DB_PATH)
        rows = conn.execute(sql).fetchall()
        conn.close()

        result_rows = [
            dict(r)
            for r in rows
        ]

        return {
            **state,
            "rows": result_rows,
            "answer": f"Found {len(result_rows)} rows",
            "error": None
        }

    except Exception as e:
        logger.error(f"Error occurred while executing SQL: {str(e)}")
        return {
            **state,
            "error": str(e),
            "retries": state["retries"] + 1
        }

def router(state: AgentState):
    if state.get("error") is None:
        return END
    if state["error"] == "UNANSWERABLE":
        return END
    if state["retries"] >= 2:
        return END
    return "sql_writer"

# Define the workflow for the agent using LangGraph.
workflow = StateGraph(AgentState)
workflow.add_node("sql_writer", sql_writer)
workflow.add_node("sql_executor", sql_executor)
workflow.set_entry_point("sql_writer")
workflow.add_edge("sql_writer", "sql_executor")
workflow.add_conditional_edges("sql_executor",router)

# Compile the workflow into an executable agent that can be invoked with user questions.
agent = workflow.compile()
