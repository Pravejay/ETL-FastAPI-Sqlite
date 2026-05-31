# LLM provider interface
# Allows to use different LLM providers in the future without changing the rest of the codebase.
from abc import ABC, abstractmethod
import os
from google import genai

from app.models import SCHEMA_CONTEXT
from app.utils import setup_logger

# Set up logger
logger = setup_logger("ai.log")

# Abstract LLMProvider interface for different LLM providers (e.g. OpenAI, Gemini, Ollama, etc.)
# and we could switch between them using configuration or environment variables.
class LLMProvider(ABC):
    @abstractmethod
    def generate_sql(self, question: str, error: str | None = None) -> str:
        pass

# Implementation of the LLMProvider interface using Google's Gemini API.
class GeminiProvider(LLMProvider):
    # Initialize the Gemini client. Using my own API key here for testing,
    # but in a real application this should come from a secure source like environment variables or a secrets manager.
    def __init__(self):
        logger.info("Initializing GeminiProvider with Gemini API client.")
        self.client = genai.Client(
            api_key = os.getenv("GEMINI_API_KEY",
                                "<API_KEY_PLACEHOLDER>") # API Key removed for security reasons.
        )
        logger.info("GeminiProvider initialized successfully.")

    # This method generates SQL queries based on the user's natural language question and any previous error messages.
    def generate_sql(self, question: str, error: str | None = None) -> str:
        logger.info(f"Generating SQL for question: {question} with error context: {error}")
        # Generate prompt for the LLM based on the question and any previous error
        prompt = f"""
{SCHEMA_CONTEXT}

Question:
{question}
"""

        if error:
            prompt += f"""
Previous SQL failed:
{error}
Generate corrected SQL.
"""
        logger.info(f"Invoking Gemini API with prompt: {prompt}")
        # Call the Gemini API to generate SQL
        response = self.client.models.generate_content(
            # Using low-latency, cost-effective multimodal model optimized for high-frequency, lightweight tasks.
            model="gemini-3.1-flash-lite",
            contents=prompt
        )
        sql = response.text.strip()
        logger.info(f"Generated SQL: {sql}")
        # Remove any code block formatting from the generated SQL if present.
        sql = sql.replace("```sql", "").replace("```", "")
        logger.info(f"Formatted/Cleaned SQL: {sql}")
        return sql


# Initialize the LLM provider (can be replaced with another provider in the future)
llm = GeminiProvider()
