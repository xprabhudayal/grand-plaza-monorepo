# RAG Pipeline Evaluation

This script evaluates the performance of the RAG (Retrieval-Augmented Generation) pipeline located in `backend/rag_pipeline.py` using the `ragas` library.

## Purpose

The primary goal is to assess the quality of the RAG pipeline based on five core metrics:
- **Contextual Relevancy**: Measures the relevance of the retrieved context to the input query.
- **Contextual Precision**: Measures whether relevant chunks are ranked higher than irrelevant ones.
- **Contextual Recall**: Measures if the retrieved context contains all the necessary information to answer the query.
- **Faithfulness**: Measures whether the generated answer is factually consistent with the retrieved context, checking for hallucinations.
- **Answer Relevancy**: Measures the relevance of the generated answer to the original query.

## Setup

1.  **Install Dependencies**:
    Install all the required Python packages by running the following command from the project root directory:
    ```bash
    pip install -r backend/requirements-ragas.txt
    ```

2.  **Environment Variables**:
    The evaluation script requires API keys for both Mistral (for embeddings in the RAG pipeline) and OpenAI (for the generator LLM in `ragas`). Make sure you have a `.env` file in the root of the project with the following variables set:
    ```
    MISTRAL_API_KEY="your_mistral_api_key"
    OPENAI_API_KEY="your_openai_api_key"
    LANGSMITH_API_KEY="your_langsmith_api_key" # Optional, for tracing
    ```

## How to Run

To run the evaluation, execute the following command from the root directory of the project:

```bash
python -m evaluations.RAG.evaluate_rag
```

The script will:
1.  Initialize the `MenuRAGPipeline`.
2.  Use a predefined set of questions about the restaurant menu.
3.  For each question, it will:
    -   Retrieve relevant context from the ChromaDB vector store.
    -   Generate an answer using an OpenAI model.
4.  Evaluate the generated answers and retrieved contexts against the ground truth using `ragas`.
5.  Print the evaluation results to the console.
6.  Save a detailed CSV report of the results to `evaluations/RAG/rag_evaluation_results.csv`.
