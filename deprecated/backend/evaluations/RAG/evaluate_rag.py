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
        """Blocks until a request can be made, then reserves a slot atomically."""
        while True:
            with self.lock:
                self._reset_if_minute_passed()

                reason = ""
                if self.requests_this_minute >= self.rpm_limit:
                    reason = f"RPM limit reached ({self.requests_this_minute}/{self.rpm_limit})"
                elif self.tokens_this_minute + estimated_tokens > self.tpm_limit:
                    reason = f"TPM limit would be exceeded ({self.tokens_this_minute + estimated_tokens}/{self.tpm_limit})"

                if not reason:
                    # Atomically reserve the slot
                    self.requests_this_minute += 1
                    self.tokens_this_minute += estimated_tokens
                    now_str = datetime.now().strftime('%H:%M:%S')
                    print(f"[{now_str}] Slot acquired - RPM: {self.requests_this_minute}/{self.rpm_limit}, TPM: {self.tokens_this_minute}/{self.tpm_limit} (estimated)")
                    return estimated_tokens  # Return the reserved token amount

            now = datetime.now()
            wait_time = 30 - (now - self.minute_start).total_seconds()
            print(f"🚫 Rate limit hit: {reason}. Waiting {max(1, wait_time):.1f}s for reset...")
            time.sleep(max(1, wait_time))

    async def await_for_slot(self, estimated_tokens: int):
        """Asynchronously waits until a request can be made, then reserves a slot atomically."""
        while True:
            with self.lock:
                self._reset_if_minute_passed()

                reason = ""
                if self.requests_this_minute >= self.rpm_limit:
                    reason = f"RPM limit reached ({self.requests_this_minute}/{self.rpm_limit})"
                elif self.tokens_this_minute + estimated_tokens > self.tpm_limit:
                    reason = f"TPM limit would be exceeded ({self.tokens_this_minute + estimated_tokens}/{self.tpm_limit})"

                if not reason:
                    # Atomically reserve the slot
                    self.requests_this_minute += 1
                    self.tokens_this_minute += estimated_tokens
                    now_str = datetime.now().strftime('%H:%M:%S')
                    print(f"[{now_str}] Slot acquired - RPM: {self.requests_this_minute}/{self.rpm_limit}, TPM: {self.tokens_this_minute}/{self.tpm_limit} (estimated)")
                    return estimated_tokens  # Return the reserved token amount

            now = datetime.now()
            wait_time = 30 - (now - self.minute_start).total_seconds()
            print(f"🚫 Rate limit hit: {reason}. Waiting {max(1, wait_time):.1f}s for reset...")
            await asyncio.sleep(max(1, wait_time))

    def update_token_count(self, actual_tokens: int, reserved_tokens: int):
        """Updates the token count with the actual value after a request is completed."""
        with self.lock:
            # Adjust for the difference between actual and reserved tokens
            token_diff = actual_tokens - reserved_tokens
            self.tokens_this_minute = max(0, self.tokens_this_minute + token_diff)
            now = datetime.now().strftime('%H:%M:%S')
            print(f"[{now}] Token count updated - RPM: {self.requests_this_minute}/{self.rpm_limit}, TPM: {self.tokens_this_minute}/{self.tpm_limit} (actual: {actual_tokens}, reserved: {reserved_tokens})")

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

        reserved_tokens = self.limiter.wait_for_slot(estimated_total_tokens)

        result = self.base_llm.invoke(messages, **kwargs)

        actual_tokens = estimated_total_tokens
        try:
            if hasattr(result, 'response_metadata') and 'token_usage' in result.response_metadata:
                token_usage = result.response_metadata['token_usage']
                if isinstance(token_usage, dict):
                    actual_tokens = token_usage.get('total_tokens', estimated_total_tokens)
                elif hasattr(token_usage, 'total_tokens'):
                    actual_tokens = token_usage.total_tokens
            elif hasattr(result, 'usage_metadata'):
                # Handle different API response formats
                usage = result.usage_metadata
                if hasattr(usage, 'total_token_count'):
                    actual_tokens = usage.total_token_count
                elif hasattr(usage, 'total_tokens'):
                    actual_tokens = usage.total_tokens
        except (AttributeError, KeyError, TypeError) as e:
            logger.warning(f"Could not extract actual token usage, using estimate: {e}")

        self.limiter.update_token_count(actual_tokens, reserved_tokens)
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

        reserved_tokens = await self.limiter.await_for_slot(estimated_total_tokens)

        result = await self.base_llm.ainvoke(messages, **kwargs)

        actual_tokens = estimated_total_tokens
        try:
            if hasattr(result, 'response_metadata') and 'token_usage' in result.response_metadata:
                token_usage = result.response_metadata['token_usage']
                if isinstance(token_usage, dict):
                    actual_tokens = token_usage.get('total_tokens', estimated_total_tokens)
                elif hasattr(token_usage, 'total_tokens'):
                    actual_tokens = token_usage.total_tokens
            elif hasattr(result, 'usage_metadata'):
                # Handle different API response formats
                usage = result.usage_metadata
                if hasattr(usage, 'total_token_count'):
                    actual_tokens = usage.total_token_count
                elif hasattr(usage, 'total_tokens'):
                    actual_tokens = usage.total_tokens
        except (AttributeError, KeyError, TypeError) as e:
            logger.warning(f"Could not extract actual token usage, using estimate: {e}")

        self.limiter.update_token_count(actual_tokens, reserved_tokens)
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
        # Log the specific error type for better debugging
        error_msg = str(e).lower()
        is_rate_limit = any(phrase in error_msg for phrase in [
            'rate limit', 'too many requests', 'quota exceeded', 'tpm', 'rpm'
        ])
        
        if is_rate_limit:
            logger.error(f"Rate limit error processing question '{question}': {e}")
        else:
            logger.error(f"Error processing question '{question}': {e}")
            
        return {
            "question": question,
            "contexts": ["No context retrieved" if "retrieve" in error_msg else "Error retrieving context"],
            "answer": "Rate limit exceeded, please retry" if is_rate_limit else "Error generating answer"
        }

# Comprehensive Ground Truth Q&A for Restaurant Menu RAG Evaluation
MENU_GROUND_TRUTH = {
    # PRICING QUESTIONS
    "What's the price of Margherita pizza?": "$12.50",
    "How much does BBQ Chicken pizza cost?": "$15.50", 
    "What's the cost of Hawaiian pizza?": "$14.50",
    "How much is Pepperoni pizza?": "$14.00",
    "What's the price of Veggie Supreme pizza?": "$13.50",
    "How much does Classic Lemonade cost?": "$4.00",
    "What's the price of Green Smoothie?": "$6.00",
    "How much is the Iced Mocha?": "$5.50",
    "What does Mango Lassi cost?": "$5.00",
    "How much is Sparkling Water?": "$3.00",
    "What's the price of Classic Club sandwich?": "$13.00",
    "How much does Caprese Panini cost?": "$11.50",
    "What's the cost of Philly Cheesesteak?": "$14.50",
    "How much is Spicy Tofu Banh Mi?": "$12.00",
    "What's the price of Tuna Melt?": "$12.50",
    "How much does The Classic hotdog cost?": "$8.00",
    "What's the price of Chicago Dog?": "$9.50",
    "How much is Chili Cheese Dog?": "$10.50",
    "What does Veggie Dog cost?": "$9.00",
    "How much is Sonoran Dog?": "$11.00",
    "What's the price of Quinoa Salad?": "$12.50",
    "How much does Grilled Salmon cost?": "$18.00",
    "What's the cost of Chicken & Veggie Skewers?": "$15.00",
    "How much is Lentil Soup?": "$9.00",
    "What's the price of Buddha Bowl?": "$13.50",

    # DIETARY RESTRICTIONS
    "Is Margherita pizza vegetarian?": "Yes, Margherita pizza is vegetarian.",
    "Is BBQ Chicken pizza vegetarian?": "No, BBQ Chicken pizza is non-vegetarian.",
    "Is Hawaiian pizza veg or non-veg?": "Hawaiian pizza is non-vegetarian.",
    "Is Pepperoni pizza vegetarian?": "No, Pepperoni pizza is non-vegetarian.", 
    "Is Veggie Supreme vegetarian?": "Yes, Veggie Supreme pizza is vegetarian.",
    "Are all beverages vegetarian?": "Yes, all beverages on the menu are vegetarian.",
    "Is Classic Club sandwich vegetarian?": "No, Classic Club sandwich is non-vegetarian.",
    "Is Caprese Panini veg or non-veg?": "Caprese Panini is vegetarian.",
    "Is Philly Cheesesteak vegetarian?": "No, Philly Cheesesteak is non-vegetarian.",
    "Is Spicy Tofu Banh Mi vegetarian?": "Yes, Spicy Tofu Banh Mi is vegetarian.",
    "Is Tuna Melt veg or non-veg?": "Tuna Melt is non-vegetarian.",
    "Is The Classic hotdog vegetarian?": "No, The Classic hotdog is non-vegetarian.",
    "Is Chicago Dog vegetarian?": "No, Chicago Dog is non-vegetarian.",
    "Is Veggie Dog vegetarian?": "Yes, Veggie Dog is vegetarian.",
    "Is Sonoran Dog veg or non-veg?": "Sonoran Dog is non-vegetarian.",
    "Are all healthy meals vegetarian?": "No, Grilled Salmon and Chicken & Veggie Skewers are non-vegetarian. Quinoa Salad, Lentil Soup, and Buddha Bowl are vegetarian.",

    # CALORIE INFORMATION
    "How many calories in Margherita pizza?": "720 kcal",
    "What's the calorie count for BBQ Chicken pizza?": "980 kcal",
    "How many calories does Hawaiian pizza have?": "890 kcal",
    "What's the calorie content of Pepperoni pizza?": "950 kcal",
    "How many calories in Veggie Supreme?": "810 kcal",
    "What's the calorie count for Classic Lemonade?": "150 kcal",
    "How many calories in Green Smoothie?": "280 kcal",
    "What's the calorie content of Iced Mocha?": "350 kcal",
    "How many calories does Mango Lassi have?": "320 kcal",
    "What's the calorie count for Sparkling Water?": "0 kcal",
    "How many calories in Classic Club sandwich?": "850 kcal",
    "What's the calorie content of Caprese Panini?": "650 kcal",
    "How many calories does Philly Cheesesteak have?": "990 kcal",
    "What's the calorie count for Spicy Tofu Banh Mi?": "580 kcal",
    "How many calories in Tuna Melt?": "750 kcal",
    "What's the calorie content of The Classic hotdog?": "450 kcal",
    "How many calories does Chicago Dog have?": "550 kcal",
    "What's the calorie count for Chili Cheese Dog?": "680 kcal",
    "How many calories in Veggie Dog?": "400 kcal",
    "What's the calorie content of Sonoran Dog?": "620 kcal",
    "How many calories does Quinoa Salad have?": "450 kcal",
    "What's the calorie count for Grilled Salmon?": "550 kcal",
    "How many calories in Chicken & Veggie Skewers?": "480 kcal",
    "What's the calorie content of Lentil Soup?": "350 kcal",
    "How many calories does Buddha Bowl have?": "520 kcal",

    # INGREDIENT/DESCRIPTION QUESTIONS
    "What ingredients are in Margherita pizza?": "Fresh mozzarella, tomato sauce, and basil on a thin crust.",
    "What's in BBQ Chicken pizza?": "Tangy BBQ sauce base, grilled chicken strips, red onions, and cilantro.",
    "What are the toppings on Hawaiian pizza?": "Ham, pineapple chunks, and a cheesy base.",
    "What's in Pepperoni pizza?": "Generous layers of spicy pepperoni and mozzarella cheese.",
    "What ingredients are in Veggie Supreme?": "Bell peppers, onions, olives, mushrooms, and mozzarella cheese.",
    "What's in Classic Lemonade?": "Freshly squeezed lemon juice, sweetened to perfection. Served chilled.",
    "What ingredients are in Green Smoothie?": "A healthy mix of spinach, banana, mango, and almond milk.",
    "What's in Iced Mocha?": "A rich blend of espresso, chocolate syrup, and cold milk, topped with whipped cream.",
    "What ingredients are in Mango Lassi?": "Traditional Indian yogurt-based drink blended with sweet mango pulp.",
    "What's in Sparkling Water?": "Chilled carbonated mineral water with a slice of lime.",
    "What ingredients are in Classic Club?": "Turkey, bacon, lettuce, tomato, and mayonnaise in a triple-decker sandwich.",
    "What's in Caprese Panini?": "Fresh mozzarella, tomatoes, basil pesto, and balsamic glaze in a toasted panini.",
    "What ingredients are in Philly Cheesesteak?": "Thinly sliced steak, melted provolone cheese, and grilled onions in a hoagie roll.",
    "What's in Spicy Tofu Banh Mi?": "Vietnamese-style sandwich with marinated spicy tofu, pickled carrots, and cilantro.",
    "What ingredients are in Tuna Melt?": "Tuna salad and melted cheddar cheese on toasted rye bread.",
    "What's in The Classic hotdog?": "All-beef hotdog in a soft bun, topped with ketchup and mustard.",
    "What ingredients are in Chicago Dog?": "All-beef hotdog with yellow mustard, chopped onions, relish, tomato slices, and a pickle.",
    "What's in Chili Cheese Dog?": "A hotdog smothered in beef chili and topped with melted cheddar cheese.",
    "What ingredients are in Veggie Dog?": "Plant-based sausage in a whole wheat bun with your choice of toppings.",
    "What's in Sonoran Dog?": "Bacon-wrapped hotdog topped with pinto beans, onions, tomatoes, and mayonnaise.",
    "What ingredients are in Quinoa Salad?": "Quinoa, chickpeas, cucumber, tomatoes, and a lemon-tahini dressing.",
    "What's in Grilled Salmon?": "Grilled salmon fillet served with a side of steamed asparagus and brown rice.",
    "What ingredients are in Chicken & Veggie Skewers?": "Marinated chicken and mixed vegetable skewers, grilled and served with a yogurt dip.",
    "What's in Lentil Soup?": "Red lentils, carrots, celery, and spices.",
    "What ingredients are in Buddha Bowl?": "Roasted sweet potatoes, black beans, avocado, and mixed greens.",

    # CATEGORY/SECTION QUESTIONS
    "What pizzas do you have?": "Margherita ($12.50), Pepperoni ($14.00), BBQ Chicken ($15.50), Veggie Supreme ($13.50), and Hawaiian ($14.50).",
    "What beverages are available?": "Classic Lemonade ($4.00), Iced Mocha ($5.50), Green Smoothie ($6.00), Mango Lassi ($5.00), and Sparkling Water ($3.00).",
    "What sandwiches do you offer?": "Classic Club ($13.00), Caprese Panini ($11.50), Philly Cheesesteak ($14.50), Spicy Tofu Banh Mi ($12.00), and Tuna Melt ($12.50).",
    "What hotdogs are on the menu?": "The Classic ($8.00), Chicago Dog ($9.50), Chili Cheese Dog ($10.50), Veggie Dog ($9.00), and Sonoran Dog ($11.00).",
    "What healthy meal options do you have?": "Quinoa Salad ($12.50), Grilled Salmon ($18.00), Chicken & Veggie Skewers ($15.00), Lentil Soup ($9.00), and Buddha Bowl ($13.50).",

    # COMPARATIVE QUESTIONS
    "What's the most expensive item on the menu?": "Grilled Salmon at $18.00.",
    "What's the cheapest item available?": "Sparkling Water at $3.00.",
    "Which pizza has the most calories?": "BBQ Chicken pizza with 980 kcal.",
    "What's the lowest calorie beverage?": "Sparkling Water with 0 kcal.",
    "Which hotdog is the most expensive?": "Sonoran Dog at $11.00.",
    "What's the cheapest pizza?": "Margherita pizza at $12.50.",
    "Which healthy meal has the least calories?": "Lentil Soup with 350 kcal.",
    "What's the most expensive sandwich?": "Philly Cheesesteak at $14.50.",

    # AVAILABILITY/EXISTENCE QUESTIONS
    "Do you have gluten-free options?": "Based on the menu provided, we have Veggie Dog served in a whole wheat bun, but specific gluten-free options are not explicitly listed.",
    "Do you serve vegan food?": "Yes, we have several vegetarian options that may be vegan, including Green Smoothie, Sparkling Water, Veggie Dog, Spicy Tofu Banh Mi, Quinoa Salad, Lentil Soup, and Buddha Bowl.",
    "Is there any seafood on the menu?": "Yes, we have Grilled Salmon ($18.00) and Tuna Melt ($12.50).",
    "Do you have any soups?": "Yes, we have Lentil Soup for $9.00.",
    "Are there any breakfast items?": "The menu doesn't specifically list breakfast items, but we have various sandwiches and beverages that could be enjoyed any time.",

    # SPECIFIC DETAIL QUESTIONS
    "What type of bread is the Tuna Melt served on?": "Toasted rye bread.",
    "What kind of bun comes with Veggie Dog?": "Whole wheat bun.",
    "What type of milk is used in Green Smoothie?": "Almond milk.",
    "What cheese is on Philly Cheesesteak?": "Melted provolone cheese.",
    "What dressing comes with Quinoa Salad?": "Lemon-tahini dressing.",
}

# Select a diverse subset for evaluation (you can adjust this list)
eval_questions = [
    "What's the price of Margherita pizza?",
    "How much does BBQ Chicken pizza cost?",
    "Is Veggie Supreme vegetarian?",
    "How many calories in Classic Club sandwich?",
    "What ingredients are in Chicago Dog?",
    "What beverages are available?",
    "What's the most expensive item on the menu?",
    "Do you serve vegan food?",
    "What ingredients are in Quinoa Salad?",
    "Which pizza has the most calories?",
    "What type of bread is the Tuna Melt served on?",
    "What healthy meal options do you have?",
    "How much is Sparkling Water?",
    "Is Hawaiian pizza veg or non-veg?",
    "How many calories in Green Smoothie?",
    "What's in Spicy Tofu Banh Mi?",
    "What's the cheapest pizza?",
    "What's the calorie count for Grilled Salmon?",
    "What's in Classic Lemonade?",
    "Which hotdog is the most expensive?",
]

# Extract ground truths for selected questions
ground_truths = [MENU_GROUND_TRUTH[q] for q in eval_questions]

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

    # Generator Model options
    parser.add_argument("--model", type=str, default="moonshotai/kimi-k2-instruct",
                       help="Generator model name (default: moonshotai/kimi-k2-instruct for Groq)")
    parser.add_argument("--openai_api_key", type=str, default=None,
                       help="OpenAI API key (if not provided, uses Groq)")
    parser.add_argument("--openai_base_url", type=str, default=None,
                       help="OpenAI base URL for API compatible services")

    # Evaluator Model options (separate from generator)
    parser.add_argument("--evaluator_model", type=str, default=None,
                       help="Separate evaluator model (default: same as generator)")
    parser.add_argument("--evaluator_openai_key", type=str, default=None,
                       help="Separate OpenAI API key for evaluator")
    parser.add_argument("--evaluator_base_url", type=str, default=None,
                       help="Separate base URL for evaluator model")

    # Evaluation configuration
    parser.add_argument("--skip_context_recall", action="store_true",
                       help="Skip context_recall metric (doesn't need ground truth)")
    parser.add_argument("--metrics", type=str, nargs="+", 
                       choices=["context_relevance", "context_precision", "faithfulness", "answer_relevancy", "context_recall"],
                       default=["context_relevance", "context_precision", "faithfulness", "answer_relevancy", "context_recall"],
                       help="Select specific metrics to run")

    return parser.parse_args()

def create_llm(args, for_evaluator=False):
    """Create LLM based on provided arguments."""
    if for_evaluator:
        # Use evaluator-specific settings if provided
        model = args.evaluator_model or args.model
        api_key = args.evaluator_openai_key or args.openai_api_key
        base_url = args.evaluator_base_url or args.openai_base_url
        llm_type = "Evaluator"
    else:
        # Use generator settings
        model = args.model
        api_key = args.openai_api_key
        base_url = args.openai_base_url
        llm_type = "Generator"

    if api_key:
        # Use OpenAI compatible API
        llm_kwargs = {
            "model": model,
            "temperature": 0.1,
            "api_key": api_key,
            "max_tokens": 500
        }
        if base_url:
            llm_kwargs["base_url"] = base_url

        llm = ChatOpenAI(**llm_kwargs)
        print(f"{llm_type} - Using OpenAI compatible API with model: {model}")
        if base_url:
            print(f"{llm_type} - Base URL: {base_url}")
    else:
        # Use Groq (default behavior)
        llm = ChatGroq(
            model=model,
            temperature=0.1,
            api_key=os.getenv("GROQ_API_KEY"),
            max_tokens=500
        )
        print(f"{llm_type} - Using Groq API with model: {model}")

    return llm

def main():
    """Main function to run the RAG evaluation with rate limiting."""
    args = parse_arguments()

    print(f"Rate limits - RPM: {args.rpm}, TPM: {args.tpm}")
    print(f"Selected metrics: {', '.join(args.metrics)}")

    # Initialize rate limiter for generator
    generator_limiter = TokenRateLimiter(max_requests_per_minute=args.rpm, max_tokens_per_minute=args.tpm)
    
    # Initialize separate rate limiter for evaluator (if different model)
    if args.evaluator_model or args.evaluator_openai_key:
        evaluator_limiter = TokenRateLimiter(max_requests_per_minute=args.rpm, max_tokens_per_minute=args.tpm)
        print("🔧 Using separate evaluator model - eliminates self-evaluation bias!")
    else:
        evaluator_limiter = generator_limiter
        print("⚠️  Using same model for generation and evaluation - potential self-evaluation bias")

    print("Initializing RAG pipeline...")
    try:
        rag_pipeline = get_rag_pipeline()
        print("RAG pipeline initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize RAG pipeline: {e}")
        return

    print("Initializing Generator LLM...")
    try:
        base_generator_llm = create_llm(args, for_evaluator=False)
        generator_llm = RateLimitedLLM(base_generator_llm, generator_limiter)
        print("Generator LLM initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Generator LLM: {e}")
        return

    print("Initializing Evaluator LLM...")
    try:
        base_evaluator_llm = create_llm(args, for_evaluator=True)
        evaluator_llm = RateLimitedLLM(base_evaluator_llm, evaluator_limiter)
        print("Evaluator LLM initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Evaluator LLM: {e}")
        return

    print("Augmenting dataset with rate limiting...")
    try:
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
        # Use the separate evaluator LLM for RAGAS metrics
        ragas_llm = LangchainLLMWrapper(evaluator_llm)
        ragas_embeddings = LangchainEmbeddingsWrapper(rag_pipeline.embeddings)

        print(f"🔧 Generator: {args.model}, Evaluator: {args.evaluator_model or args.model}")
        print(f"📊 Generator stats - Requests: {generator_llm.total_requests}, Tokens: {generator_llm.total_tokens}")
        print(f"📊 Evaluator stats - Requests: {evaluator_llm.total_requests}, Tokens: {evaluator_llm.total_tokens}")

        # Configure metrics based on arguments
        metrics = []
        metric_map = {
            "context_relevance": ContextRelevance(llm=ragas_llm),
            "context_precision": ContextPrecision(llm=ragas_llm),
            "faithfulness": Faithfulness(llm=ragas_llm),
            "answer_relevancy": AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings),
            "context_recall": ContextRecall(llm=ragas_llm),
        }

        for metric_name in args.metrics:
            if args.skip_context_recall and metric_name == "context_recall":
                print("⏭️  Skipping context_recall metric as requested")
                continue
            metrics.append(metric_map[metric_name])
            print(f"✅ Added {metric_name} metric")

        if not metrics:
            print("❌ No metrics selected for evaluation!")
            return

        result = evaluate(
            dataset=dataset,
            metrics=metrics,
            raise_exceptions=False,
            show_progress=True
        )

        print("Evaluation complete!")
        print("Results:")
        print(result)

        # Save results with timestamp
        df = result.to_pandas()
        output_dir = project_root / 'evaluations' / 'RAG'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        generator_model_safe = args.model.replace("/", "_")
        evaluator_model_safe = (args.evaluator_model or args.model).replace("/", "_")
        output_path = output_dir / f'rag_eval_{generator_model_safe}_vs_{evaluator_model_safe}_{timestamp}.csv'
        
        df.to_csv(output_path, index=False)
        print(f"Results saved to {output_path}")

        # Print summary statistics
        print("\n=== EVALUATION SUMMARY ===")
        print(f"📋 Ground Truth Questions: {len(eval_questions)}")
        print(f"🎯 Hardcoded Ground Truth: ✅ (Eliminates LLM judge bias)")
        print(f"🤖 Generator Model: {args.model}")
        print(f"⚖️  Evaluator Model: {args.evaluator_model or args.model}")
        
        metric_columns = {
            'context_relevance': 'Context Relevance',
            'nv_context_relevance': 'Context Relevance', 
            'context_precision': 'Context Precision',
            'faithfulness': 'Faithfulness',
            'answer_relevancy': 'Answer Relevancy',
            'context_recall': 'Context Recall'
        }
        
        print(f"\n📊 METRIC SCORES:")
        for col_name, display_name in metric_columns.items():
            if col_name in df.columns:
                mean_score = df[col_name].mean()
                print(f"   {display_name}: {mean_score:.4f}")

        # Token usage summary
        total_generator_tokens = generator_llm.total_tokens
        total_evaluator_tokens = evaluator_llm.total_tokens
        print(f"\n💰 TOKEN USAGE:")
        print(f"   Generator: {total_generator_tokens:,} tokens")
        print(f"   Evaluator: {total_evaluator_tokens:,} tokens") 
        print(f"   Total: {total_generator_tokens + total_evaluator_tokens:,} tokens")

    except Exception as e:
        print(f"Error during evaluation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()