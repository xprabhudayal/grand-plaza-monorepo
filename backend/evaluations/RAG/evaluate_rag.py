import os
import sys
import asyncio
import time
import logging
import argparse
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
import tiktoken
import backoff
from datetime import datetime, timedelta
from threading import Lock
from ragas import evaluate, EvaluationDataset, SingleTurnSample
from ragas.metrics import (
    Faithfulness,
    AnswerRelevancy,
    ContextRecall,
    ContextPrecision,
    ContextRelevance
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain.schema import LLMResult, Generation
from langchain.callbacks.manager import CallbackManagerForLLMRun
from typing import Optional
from langchain.schema.runnable import RunnablePassthrough
from langchain.prompts import PromptTemplate
from dataclasses import dataclass, field
from typing import Callable, Any, List, Tuple
import nest_asyncio

from rag_pipeline import get_rag_pipeline

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

logger = logging.getLogger(__name__)

# Add backend to sys.path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

# Load environment variables
dotenv_path = project_root / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Loaded .env file from {dotenv_path}")
else:
    print(f"Warning: .env file not found at {dotenv_path}")


class TokenRateLimiter:
    """A thread-safe rate limiter that tracks both RPM and TPM limits."""

    def __init__(self, max_requests_per_minute: int = 30, max_tokens_per_minute: int = 10000):
        self.rpm_limit = max_requests_per_minute
        self.tpm_limit = max_tokens_per_minute
        self.requests_this_minute = 0
        self.tokens_this_minute = 0
        self.minute_start = datetime.now()
        self.lock = Lock()

        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except KeyError:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

        print(f"Rate limiter initialized - RPM: {self.rpm_limit}, TPM: {self.tpm_limit}")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.tokenizer.encode(str(text)))

    def _reset_if_minute_passed(self):
        """Reset counters if a minute has passed. MUST be called inside a lock."""
        now = datetime.now()
        if (now - self.minute_start).total_seconds() >= 60:
            self.requests_this_minute = 0
            self.tokens_this_minute = 0
            self.minute_start = now
            print(f"[{now.strftime('%H:%M:%S')}] Rate limits reset - RPM: 0/{self.rpm_limit}, TPM: 0/{self.tpm_limit}")

    def wait_for_slot(self, estimated_tokens: int):
        """Blocks until a request can be made, then reserves a slot."""
        while True:
            with self.lock:
                self._reset_if_minute_passed()

                reason = ""
                if self.requests_this_minute >= self.rpm_limit:
                    reason = f"RPM limit reached ({self.requests_this_minute}/{self.rpm_limit})"
                elif self.tokens_this_minute + estimated_tokens > self.tpm_limit:
                    reason = f"TPM limit would be exceeded ({self.tokens_this_minute + estimated_tokens}/{self.tpm_limit})"

                if not reason:
                    self.requests_this_minute += 1
                    self.tokens_this_minute += estimated_tokens
                    now_str = datetime.now().strftime('%H:%M:%S')
                    print(f"[{now_str}] Slot acquired - RPM: {self.requests_this_minute}/{self.rpm_limit}, TPM: {self.tokens_this_minute}/{self.tpm_limit} (estimated)")
                    return

            now = datetime.now()
            wait_time = 30 - (now - self.minute_start).total_seconds()
            print(f"🚫 Rate limit hit: {reason}. Waiting {max(1, wait_time):.1f}s for reset...")
            time.sleep(max(1, wait_time))

    async def await_for_slot(self, estimated_tokens: int):
        """Asynchronously waits until a request can be made, then reserves a slot."""
        while True:
            with self.lock:
                self._reset_if_minute_passed()

                reason = ""
                if self.requests_this_minute >= self.rpm_limit:
                    reason = f"RPM limit reached ({self.requests_this_minute}/{self.rpm_limit})"
                elif self.tokens_this_minute + estimated_tokens > self.tpm_limit:
                    reason = f"TPM limit would be exceeded ({self.tokens_this_minute + estimated_tokens}/{self.tpm_limit})"

                if not reason:
                    self.requests_this_minute += 1
                    self.tokens_this_minute += estimated_tokens
                    now_str = datetime.now().strftime('%H:%M:%S')
                    print(f"[{now_str}] Slot acquired - RPM: {self.requests_this_minute}/{self.rpm_limit}, TPM: {self.tokens_this_minute}/{self.tpm_limit} (estimated)")
                    return

            now = datetime.now()
            wait_time = 60 - (now - self.minute_start).total_seconds()
            print(f"🚫 Rate limit hit: {reason}. Waiting {max(1, wait_time):.1f}s for reset...")
            await asyncio.sleep(max(1, wait_time))

    def update_token_count(self, actual_tokens: int, estimated_tokens: int):
        """Updates the token count with the actual value after a request is completed."""
        with self.lock:
            token_diff = actual_tokens - estimated_tokens
            self.tokens_this_minute += token_diff
            now = datetime.now().strftime('%H:%M:%S')
            print(f"[{now}] Token count updated - RPM: {self.requests_this_minute}/{self.rpm_limit}, TPM: {self.tokens_this_minute}/{self.tpm_limit}")

def should_retry_on_rate_limit(e):
    """Check if exception is a rate limit error that should trigger retry."""
    if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
        return e.response.status_code == 429

    # Check for Groq rate limit errors
    error_msg = str(e).lower()
    return any(phrase in error_msg for phrase in [
        'rate limit', 'too many requests', 'quota exceeded',
        'tpm', 'rpm', 'tokens per minute'
    ])

def backoff_handler(details):
    """Handler for backoff events with detailed logging."""
    print(f"⏳ Backing off {details['wait']:.1f}s after {details['tries']} tries. "
          f"Target: {details['target'].__name__}, Error: {details.get('exception', 'N/A')}")

def giveup_handler(details):
    """Handler for when we give up retrying."""
    print(f"❌ Giving up after {details['tries']} tries. "
          f"Target: {details['target'].__name__}, Final error: {details.get('exception', 'N/A')}")

def success_handler(details):
    """Handler for successful calls."""
    if details['tries'] > 1:
        print(f"✅ Success after {details['tries']} tries for {details['target'].__name__}")

class RateLimitedLLM:
    """A wrapper that adds rate limiting and backoff to any LLM."""

    def __init__(self, base_llm, limiter: TokenRateLimiter):
        self.base_llm = base_llm
        self.limiter = limiter
        self.total_requests = 0
        self.total_tokens = 0

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        max_time=300,  # 5 minutes max total retry time
        giveup=lambda e: not should_retry_on_rate_limit(e),
        on_backoff=backoff_handler,
        on_giveup=giveup_handler,
        on_success=success_handler,
        jitter=backoff.full_jitter
    )
    def invoke(self, messages, **kwargs):
        """Sync invoke with rate limiting and backoff."""
        prompt_text = str(messages)
        estimated_prompt_tokens = self.limiter.count_tokens(prompt_text)
        # Estimate 500 tokens for completion, a reasonable default
        estimated_total_tokens = estimated_prompt_tokens + 500

        self.limiter.wait_for_slot(estimated_total_tokens)

        result = self.base_llm.invoke(messages, **kwargs)

        actual_tokens = estimated_total_tokens
        if hasattr(result, 'response_metadata') and 'token_usage' in result.response_metadata:
            actual_tokens = result.response_metadata['token_usage'].get('total_tokens', actual_tokens)

        self.limiter.update_token_count(actual_tokens, estimated_total_tokens)
        self.total_requests += 1
        self.total_tokens += actual_tokens

        return result

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        max_time=300,
        giveup=lambda e: not should_retry_on_rate_limit(e),
        on_backoff=backoff_handler,
        on_giveup=giveup_handler,
        on_success=success_handler,
        jitter=backoff.full_jitter
    )
    async def ainvoke(self, messages, **kwargs):
        """Async invoke with rate limiting and backoff."""
        prompt_text = str(messages)
        estimated_prompt_tokens = self.limiter.count_tokens(prompt_text)
        # Estimate 500 tokens for completion
        estimated_total_tokens = estimated_prompt_tokens + 500

        await self.limiter.await_for_slot(estimated_total_tokens)

        result = await self.base_llm.ainvoke(messages, **kwargs)

        actual_tokens = estimated_total_tokens
        if hasattr(result, 'response_metadata') and 'token_usage' in result.response_metadata:
            actual_tokens = result.response_metadata['token_usage'].get('total_tokens', actual_tokens)

        self.limiter.update_token_count(actual_tokens, estimated_total_tokens)
        self.total_requests += 1
        self.total_tokens += actual_tokens

        return result

    def __getattr__(self, name):
        """Delegate all other attributes to the base LLM."""
        return getattr(self.base_llm, name)

# Rate-limited async function for processing questions
@backoff.on_exception(
    backoff.expo,
    Exception,
    max_tries=5,
    max_time=300,
    giveup=lambda e: not should_retry_on_rate_limit(e),
    on_backoff=backoff_handler,
    on_giveup=giveup_handler,
    on_success=success_handler,
    jitter=backoff.full_jitter
)
async def process_question_async_with_backoff(question: str, rag_pipeline, llm: RateLimitedLLM):
    """
    Async function to process a single question.
    Rate limiting is handled by the wrapped llm object.
    """
    template = """Answer the question based only on the following context:
            {context}

            Question: {question}

            Answer:"""
    prompt = PromptTemplate.from_template(template)

    try:
        # Get context
        retrieved_docs = rag_pipeline.retrieve(question, k=3)
        context_list = [doc['content'] for doc in retrieved_docs]
        context_str = " ".join(context_list)

        # Generate answer using the rate-limited LLM
        formatted_prompt = prompt.format(context=context_str, question=question)
        response = await llm.ainvoke([{"role": "user", "content": formatted_prompt}])

        # Rate limiting and token counting are handled by the llm wrapper

        return {
            "question": question,
            "contexts": context_list,
            "answer": response.content
        }
    except Exception as e:
        logger.error(f"Error processing question '{question}': {e}")
        return {
            "question": question,
            "contexts": ["No context retrieved"],
            "answer": "Error generating answer"
        }

# Evaluation dataset
eval_questions = [
    "What vegetarian pizza options are available?",
    "How much does the BBQ Chicken pizza cost?",
    "What are the ingredients in the Classic Club sandwich?",
    "Which beverages are non-alcoholic?",
    "What is the calorie count of the Quinoa Salad?",
    "Is the Spicy Tofu Banh Mi vegan?",
    "What's on the Chicago Dog?",
    "Do you have any healthy meal options for someone who doesn't eat meat?",
]

ground_truths = [
    "The vegetarian pizza options are the Margherita and the Veggie Supreme.",
    "The BBQ Chicken pizza costs $15.50.",
    "The Classic Club sandwich contains turkey, bacon, lettuce, tomato, and mayonnaise.",
    "The non-alcoholic beverages are Classic Lemonade, Green Smoothie, Mango Lassi, and Sparkling Water. The Iced Mocha can also be considered non-alcoholic.",
    "The Quinoa Salad has 450 calories.",
    "The Spicy Tofu Banh Mi is a vegetarian sandwich. The description does not explicitly state if it is vegan, but it contains marinated spicy tofu, pickled carrots, and cilantro.",
    "The Chicago Dog comes with yellow mustard, chopped onions, relish, tomato slices, and a pickle.",
    "Yes, the healthy meal options that do not contain meat are the Quinoa Salad, Lentil Soup, and the Buddha Bowl.",
]

async def process_question_async(question: str, rag_pipeline, llm: RateLimitedLLM):
    """Legacy async function - use process_question_async_with_backoff instead."""
    return await process_question_async_with_backoff(question, rag_pipeline, llm)

async def run_questions_with_progress(questions, rag_pipeline, llm: RateLimitedLLM):
    """Run all questions with progress tracking and rate limiting."""
    from tqdm import tqdm

    results = []

    # Create progress bar
    pbar = tqdm(total=len(questions), desc="Processing Questions")

    # Process questions one by one to respect rate limits
    for question in questions:
        try:
            result = await process_question_async_with_backoff(question, rag_pipeline, llm)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to process question '{question}': {e}")
            results.append({
                "question": question,
                "contexts": ["Error retrieving context"],
                "answer": "Error generating answer"
            })

        pbar.update(1)

    pbar.close()
    return results

def augment_dataset_with_backoff(questions, rag_pipeline, llm: RateLimitedLLM):
    """Augments the dataset with proper rate limiting and backoff."""

    # Run the async function
    results = asyncio.run(run_questions_with_progress(questions, rag_pipeline, llm))

    # Extract contexts and answers
    contexts = []
    answers = []
    for result in results:
        contexts.append(result["contexts"])
        answers.append(result["answer"])

    return contexts, answers

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run RAG evaluation with flexible rate limiting and model options")

    # Rate limiting options
    parser.add_argument("--rpm", type=int, default=30,
                       help="Requests per minute limit (default: 30)")
    parser.add_argument("--tpm", type=int, default=10000,
                       help="Tokens per minute limit (default: 10000)")

    # Model and API options
    parser.add_argument("--model", type=str, default="moonshotai/kimi-k2-instruct",
                       help="Model name (default: moonshotai/kimi-k2-instruct for Groq)")
    parser.add_argument("--openai_api_key", type=str, default=None,
                       help="OpenAI API key (if not provided, uses Groq)")
    parser.add_argument("--openai_base_url", type=str, default=None,
                       help="OpenAI base URL for API compatible services")

    return parser.parse_args()

def create_llm(args):
    """Create LLM based on provided arguments."""
    if args.openai_api_key:
        # Use OpenAI compatible API
        llm_kwargs = {
            "model": args.model,
            "temperature": 0.1,
            "api_key": args.openai_api_key,
            "max_tokens": 500
        }
        if args.openai_base_url:
            llm_kwargs["base_url"] = args.openai_base_url

        llm = ChatOpenAI(**llm_kwargs)
        print(f"Using OpenAI compatible API with model: {args.model}")
        if args.openai_base_url:
            print(f"Base URL: {args.openai_base_url}")
    else:
        # Use Groq (default behavior)
        llm = ChatGroq(
            model=args.model,
            temperature=0.1,
            api_key=os.getenv("GROQ_API_KEY"),
            max_tokens=500
        )
        print(f"Using Groq API with model: {args.model}")

    return llm

def main():
    """Main function to run the RAG evaluation with rate limiting."""
    args = parse_arguments()

    print(f"Rate limits - RPM: {args.rpm}, TPM: {args.tpm}")

    # Initialize a single rate limiter for the entire run
    rate_limiter = TokenRateLimiter(max_requests_per_minute=args.rpm, max_tokens_per_minute=args.tpm)

    print("Initializing RAG pipeline...")
    try:
        rag_pipeline = get_rag_pipeline()
        print("RAG pipeline initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize RAG pipeline: {e}")
        return

    print("Initializing and wrapping Generator LLM...")
    try:
        base_llm = create_llm(args)
        # Wrap the base LLM with our rate limiter
        generator_llm = RateLimitedLLM(base_llm, rate_limiter)
        print("Generator LLM initialized and wrapped successfully.")
    except Exception as e:
        print(f"Failed to initialize LLM: {e}")
        return

    print("Augmenting dataset with rate limiting...")
    try:
        # Pass the wrapped, rate-limited LLM instance
        contexts, answers = augment_dataset_with_backoff(
            eval_questions,
            rag_pipeline,
            generator_llm
        )
    except Exception as e:
        print(f"Error during dataset augmentation: {e}")
        return

    # Create samples using v2 schema
    samples = []
    for question, answer, context, reference in zip(eval_questions, answers, contexts, ground_truths):
        sample = SingleTurnSample(
            user_input=question,
            response=answer,
            retrieved_contexts=context,
            reference=reference,
        )
        samples.append(sample)

    dataset = EvaluationDataset(samples=samples)
    print(f"Dataset created with {len(dataset)} samples.")

    print("Starting RAGAS evaluation...")
    try:
        # The generator_llm is already rate-limited. We just need to wrap it for Ragas.
        ragas_llm = LangchainLLMWrapper(generator_llm)
        ragas_embeddings = LangchainEmbeddingsWrapper(rag_pipeline.embeddings)

        print(f"🔧 Using rate-limited RAGAS evaluation (RPM: {args.rpm}, TPM: {args.tpm})")
        print(f"📊 Total requests so far: {generator_llm.total_requests}, Total tokens: {generator_llm.total_tokens}")

        metrics = [
            ContextRelevance(llm=ragas_llm),
            ContextPrecision(llm=ragas_llm),
            Faithfulness(llm=ragas_llm),
            AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings),
            ContextRecall(llm=ragas_llm),
        ]

        result = evaluate(
            dataset=dataset,
            metrics=metrics,
            raise_exceptions=False,
            show_progress=True
        )

        print("Evaluation complete!")
        print("Results:")
        print(result)

        # Save results
        df = result.to_pandas()
        output_dir = project_root / 'evaluations' / 'RAG'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / 'rag_evaluation_results.csv'
        df.to_csv(output_path, index=False)
        print(f"Results saved to {output_path}")

        # Print summary statistics
        print("Summary Statistics:")
        metric_columns = ['nv_context_relevance', 'context_precision', 'faithfulness', 'answer_relevancy', 'context_recall']
        for metric_name in metric_columns:
            if metric_name in df.columns:
                mean_score = df[metric_name].mean()
                print(f"{metric_name}: {mean_score:.4f}")

    except Exception as e:
        print(f"Error during evaluation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()