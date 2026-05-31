# Semantic search implementation for handling user queries and retrieving relevant information.
import json
import os
import faiss
import numpy as np

from sentence_transformers import SentenceTransformer
from app.utils import get_connection, setup_logger

DB_PATH = os.getenv("DB_PATH", "orders.db")
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "data/faiss.index")
METADATA_PATH = os.getenv("METADATA_PATH", "data/metadata.json")

# Using a high-quality semantic understanding, extreme computational efficiency, and a lightweight footprint.
model = SentenceTransformer("all-MiniLM-L6-v2")

# Set up logger
logger = setup_logger("semantic_search.log")

# Rebuild the FAISS index from the database. This should be called post ETL load operation.
def rebuild_index(db_path):
    logger.info("Rebuilding FAISS index from database.")
    # Load all orders from the database and create embeddings for semantic search.
    conn = get_connection(db_path)
    rows = conn.execute(
        """
        SELECT
            order_id, customer_id, amount_usd, order_date
        FROM orders
        """
    ).fetchall()
    conn.close()

    texts = []
    metadata = []

    # Create a text representation for each order and store metadata for retrieval.
    for row in rows:
        text = (
            f"order {row['order_id']}, "
            f"customer {row['customer_id']}, "
            f"{row['amount_usd']} USD, "
            f"{row['order_date']}"
        )
        texts.append(text)
        metadata.append(dict(row))
    
    logger.info(f"Generated text representations for {len(texts)} orders for embedding.")
    logger.info("Generating embeddings for orders using SentenceTransformer model.")
    # Generate embeddings for all orders and build the FAISS index for efficient similarity search.
    embeddings = model.encode(texts, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype=np.float32)
    # The dimension of the embeddings is determined by the model used
    # and the FAISS index is built using inner product (IP) for similarity search.
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    logger.info(f"FAISS index built with {index.ntotal} vectors and dimension {dimension}.")
    # Save the FAISS index and corresponding metadata to disk for later retrieval during search operations.
    os.makedirs("data", exist_ok=True)
    faiss.write_index(index, FAISS_INDEX_PATH)
    logger.info("FAISS index saved successfully.")

    logger.info("Saving JSON metadata.")
    # Save metadata to a JSON file for later retrieval during search operations.
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info("JSON metadata saved successfully.")
index = None
metadata = None


# Load the FAISS index and metadata into memory at application startup for efficient search operations.
def load_index():
    global index
    global metadata

    logger.info("Loading FAISS index and metadata.")
    index = faiss.read_index(FAISS_INDEX_PATH)
    with open(METADATA_PATH) as f:
        metadata = json.load(f)
logger.info("FAISS index and metadata loaded successfully.")


# Perform a semantic search over the orders based on the user's query and return the top K most relevant results.
def search_orders(query: str, top_k: int = 5):
    logger.info(f"Performing semantic search for query: {query}")
    # Generate an embedding for the user's query
    # and perform a similarity search against the FAISS index to retrieve the most relevant orders.
    embedding = model.encode(query, normalize_embeddings=True)
    # FAISS expects a 2D array for search, so we reshape the embedding accordingly.
    embedding = np.array([embedding], dtype=np.float32)

    logger.info("Performing search on FAISS index.")
    # Perform the search and retrieve the scores and indices of the top K most similar orders from the FAISS index.
    scores, indices = index.search(embedding, top_k)
    logger.info(f"Search completed. Scores: {scores}, Indices: {indices}")

    results = []
    for score, idx in zip(
        scores[0],
        indices[0]
    ):
        row = metadata[idx]
        row["score"] = round(float(score), 4)
        results.append(row)

    logger.info(f"Search results: {results}")
    return results

