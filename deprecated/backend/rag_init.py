# rag_init.py
import os
from dotenv import load_dotenv
from rag_pipeline import get_rag_pipeline

# Load environment variables from .env file
load_dotenv()

# Ensure MISTRAL_API_KEY is set
if not os.getenv("MISTRAL_API_KEY"):
    raise ValueError("MISTRAL_API_KEY is not set in the environment.")

# Get the initialized RAG pipeline instance
try:
    rag_pipeline = get_rag_pipeline()

except Exception as e:
    print(f"An error occurred: {e}")


try:
    while True:
        try:
            query = input("Enter your query: ").strip()
            if not query:
                continue
            context = rag_pipeline.get_context_for_query(query)
            print("--- Retrieved Context ---")
            print(context)
        except Exception as e:
            print(f"Error processing query: {e}")
except KeyboardInterrupt:
    print("\nInterrupted by user (Ctrl+C). Exiting gracefully.")