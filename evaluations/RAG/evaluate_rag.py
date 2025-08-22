import os  
import sys  
from pathlib import Path  
import pandas as pd  
from dotenv import load_dotenv  
from ragas import evaluate, EvaluationDataset, SingleTurnSample  
from ragas.metrics import (  
    Faithfulness,  
    AnswerRelevancy,  
    ContextRecall,  
    ContextPrecision,  
    ContextRelevance  # Fixed: was context_relevancy  
)  
# Required wrappers for RAGAS  
from ragas.llms import LangchainLLMWrapper  
from ragas.embeddings import LangchainEmbeddingsWrapper  
from langchain_groq import ChatGroq  
from langchain.schema.runnable import RunnablePassthrough  
from langchain.prompts import PromptTemplate  
  
# Add backend to sys.path  
project_root = Path(__file__).resolve().parents[2]  
sys.path.append(str(project_root))  
  
# Load environment variables from the root .env file  
dotenv_path = project_root / 'backend' / '.env'  
if dotenv_path.exists():  
    load_dotenv(dotenv_path=dotenv_path)  
    print(f"Loaded .env file from {dotenv_path}")  
else:  
    print(f"Warning: .env file not found at {dotenv_path}")  
  
# Import the RAG pipeline  
try:  
    from backend.rag_pipeline import get_rag_pipeline  
except ImportError as e:  
    print(f"Error importing rag_pipeline: {e}")  
    sys.exit(1)  
  
# --- 1. Prepare Evaluation Dataset ---  
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
  
# --- 2. Augment Dataset with RAG Pipeline Output ---  
def augment_dataset(questions, rag_pipeline, llm):  
    """  
    Augments the dataset with context and answers from the RAG pipeline.  
    """  
    contexts = []  
    answers = []  
  
    # Define a simple prompt for the generator LLM  
    template = """Answer the question based only on the following context:  
{context}  
  
Question: {question}  
  
Answer:"""  
    prompt = PromptTemplate.from_template(template)  
  
    # Define the RAG chain  
    def get_context(inputs):  
        question = inputs["question"]  
        retrieved_docs = rag_pipeline.retrieve(question, k=3)  
        return "\n\n".join([doc['content'] for doc in retrieved_docs])  
  
    rag_chain = (  
        {  
            "context": lambda x: get_context(x),  
            "question": lambda x: x["question"]  
        }  
        | prompt  
        | llm  
    )  
  
    for q in questions:  
        try:  
            print(f"Processing question: {q}")  
              
            # Get context - ensure it's a list of strings as RAGAS expects  
            retrieved_docs = rag_pipeline.retrieve(q, k=3)  
            context_list = [doc['content'] for doc in retrieved_docs]  
            contexts.append(context_list)  
              
            # Get answer  
            response = rag_chain.invoke({"question": q})  
            answers.append(response.content)  
              
        except Exception as e:  
            print(f"Error processing question '{q}': {e}")  
            # Add placeholder values to maintain dataset consistency  
            contexts.append(["No context retrieved"])  
            answers.append("Error generating answer")  
  
    return contexts, answers  
  
# --- 3. Run Evaluation ---  
def main():  
    """  
    Main function to run the RAG evaluation.  
    """  
    print("Initializing RAG pipeline...")  
    try:  
        rag_pipeline = get_rag_pipeline()  
        print("RAG pipeline initialized successfully.")  
    except Exception as e:  
        print(f"Failed to initialize RAG pipeline: {e}")  
        print("Please ensure your MISTRAL_API_KEY is set in the .env file.")  
        return  
  
    print("Initializing Generator LLM with Groq...")  
    try:  
        generator_llm = ChatGroq(  
            model="qwen/qwen3-32b",  # Use a valid Groq model  
            temperature=0.1,  
            api_key=os.getenv("GROQ_API_KEY"),  
            max_tokens=500  
        )  
        print("Generator LLM (Groq) initialized successfully.")  
    except Exception as e:  
        print(f"Failed to initialize Groq LLM: {e}")  
        print("Please ensure your GROQ_API_KEY is set in the .env file.")  
        return  
  
    print("Augmenting dataset with RAG pipeline outputs...")  
    try:  
        contexts, answers = augment_dataset(eval_questions, rag_pipeline, generator_llm)  
    except Exception as e:  
        print(f"Error during dataset augmentation: {e}")  
        return  
  
    # Create samples using the new v2 schema  
    samples = []  
    for i, (question, answer, context, reference) in enumerate(zip(eval_questions, answers, contexts, ground_truths)):  
        sample = SingleTurnSample(  
            user_input=question,           # Changed from "question"  
            response=answer,               # Changed from "answer"  
            retrieved_contexts=context,    # Changed from "contexts"  
            reference=reference,           # Changed from "ground_truth"  
        )  
        samples.append(sample)  
      
    # Create EvaluationDataset using v2 schema  
    dataset = EvaluationDataset(samples=samples)  
    print(f"Dataset created with {len(dataset)} samples.")  
  
    print("Starting RAGAS evaluation...")  
    try:  
        # Wrap LLM and Embeddings for Ragas  
        ragas_llm = LangchainLLMWrapper(generator_llm)  
        ragas_embeddings = LangchainEmbeddingsWrapper(rag_pipeline.embeddings)  
  
        # Initialize metrics using class instances with evaluator LLM  
        metrics = [  
            ContextRelevance(llm=ragas_llm),      # Fixed metric name  
            ContextPrecision(llm=ragas_llm),  
            Faithfulness(llm=ragas_llm),  
            AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings),  
            ContextRecall(llm=ragas_llm),  
        ]  
          
        # Run the evaluation  
        result = evaluate(  
            dataset=dataset,  
            metrics=metrics,  
            raise_exceptions=False,  
            show_progress=True  
        )  
          
        print("Evaluation complete!")  
        print("Results:")  
        print(result)  
  
        # Convert to DataFrame and save  
        df = result.to_pandas()  
          
        # Create output directory if it doesn't exist  
        output_dir = project_root / 'evaluations' / 'RAG'  
        output_dir.mkdir(parents=True, exist_ok=True)  
          
        output_path = output_dir / 'rag_evaluation_results.csv'  
        df.to_csv(output_path, index=False)  
        print(f"Results saved to {output_path}")  
          
        # Print summary statistics - updated metric names  
        print("\nSummary Statistics:")  
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