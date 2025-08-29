# Enhanced RAG Pipeline for Hotel Menu System with Multi-Strategy Support
# Handles both CSV and PDF document processing with ChromaDB
# Enhanced with LangSmith tracing, evaluation capabilities, and advanced retrieval strategies

import os
import pandas as pd
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import pypdf
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_mistralai import MistralAIEmbeddings
from langchain.schema import Document
from loguru import logger
import re
from datetime import datetime
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# LangSmith Integration
from langsmith import traceable, Client

# Import query expansion
from query_expansion import get_query_expander, ExpansionResult

os.environ["LANGSMITH_PROJECT"] = "voice-ai-concierge"

RAG_PIPELINE_DIR = Path(__file__).resolve().parent

class MenuRAGPipeline:
    """Enhanced RAG Pipeline with multi-strategy retrieval support"""
    
    def __init__(self, 
                 persist_directory: str = str(RAG_PIPELINE_DIR / "chroma_db"),
                 collection_name: str = "hotel_menu"):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embeddings = None
        self.vectorstore = None
        self.documents = []
        
        # Initialize LangSmith client for RAG tracking
        self.langsmith_client = Client(
            api_key=os.getenv("LANGSMITH_API_KEY"),
        )
        
        # Initialize query expander
        self.query_expander = None
        
    def initialize_embeddings(self, api_key: Optional[str] = None):
        """Initialize Mistral embeddings"""
        if not api_key:
            api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY not found in environment variables")
        
        self.embeddings = MistralAIEmbeddings(
            model="mistral-embed",
            mistral_api_key=api_key
        )
        logger.info("Initialized Mistral embeddings")
        
        # Initialize query expander
        try:
            self.query_expander = get_query_expander()
            logger.info("Initialized query expander")
        except Exception as e:
            logger.warning(f"Could not initialize query expander: {e}")
            self.query_expander = None
        
    def load_csv_menu(self, csv_path: str) -> List[Document]:
        """Load and process CSV menu file"""
        logger.info(f"Loading CSV menu from {csv_path}")
        df = pd.read_csv(csv_path)
        
        documents = []
        current_section = ""
        
        for _, row in df.iterrows():
            # Update section if present
            if pd.notna(row.get('Section', '')) and row['Section']:
                current_section = row['Section']
            
            # Create document for each menu item
            item_name = row.get('Item Name', '')
            description = row.get('Description', '')
            veg_status = row.get('Veg/Non-Veg', '')
            calories = row.get('Calories (kcal)', '')
            price = row.get('Price (USD)', '')
            
            # Create concise text for each item (avoid repetition)
            content = f"""
            Category: {current_section}
            Item: {item_name}
            Description: {description}
            Type: {veg_status}
            Calories: {calories}
            Price: {price}
            """
            
            # Create metadata for filtering
            metadata = {
                "category": current_section,
                "item_name": item_name,
                "type": veg_status,
                "price": price,
                "calories": calories,
                "source": "menu_csv"
            }
            
            documents.append(Document(page_content=content.strip(), metadata=metadata))
        
        logger.info(f"Loaded {len(documents)} items from CSV")
        return documents
    
    def load_pdf_menu(self, pdf_path: str) -> List[Document]:
        """Load and process PDF menu file with table extraction"""
        logger.info(f"Loading PDF menu from {pdf_path}")
        documents = []
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                
                full_text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    full_text += f"\nPage {page_num + 1}:\n{text}\n"
                
                # Extract table data using regex patterns
                # Pattern for menu items in table format (currently not used but kept for future enhancement)
                # table_pattern = r'([A-Za-z\s]+?)\s+\$?(\d+\.?\d*)\s+([\w\s,.-]+)'
                
                # Split text into sections if identifiable
                sections = re.split(r'\n(?=[A-Z][A-Za-z\s]+:)', full_text)
                
                current_category = "General"
                for section in sections:
                    lines = section.strip().split('\n')
                    
                    # Check if first line is a category header
                    if lines and ':' in lines[0]:
                        current_category = lines[0].split(':')[0].strip()
                        lines = lines[1:]
                    
                    # Process each line for menu items
                    for line in lines:
                        if '$' in line or re.search(r'\d+\.?\d*', line):
                            # Try to extract item details
                            parts = line.split()
                            if len(parts) >= 2:
                                # Simple extraction logic
                                item_text = line.strip()
                                
                                content = f"""
                                Category: {current_category}
                                Menu Item: {item_text}
                                This item is from the {current_category} section of our menu.
                                """
                                
                                metadata = {
                                    "category": current_category,
                                    "source": "menu_pdf",
                                    "page": page_num + 1
                                }
                                
                                documents.append(Document(
                                    page_content=content.strip(),
                                    metadata=metadata
                                ))
                
                # Also add the full text as chunks for general queries
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=200,
                    chunk_overlap=10
                )
                
                chunks = text_splitter.split_text(full_text)
                for i, chunk in enumerate(chunks):
                    documents.append(Document(
                        page_content=chunk,
                        metadata={
                            "source": "menu_pdf_chunk",
                            "chunk_id": i
                        }
                    ))
                
        except Exception as e:
            logger.error(f"Error loading PDF: {e}")
            raise
        
        logger.info(f"Loaded {len(documents)} documents from PDF")
        return documents
    
    def load_documents(self, document_path: str):
        """Load documents from CSV or PDF"""
        path = Path(document_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {document_path}")
        
        if path.suffix.lower() == '.csv':
            self.documents = self.load_csv_menu(document_path)
        elif path.suffix.lower() == '.pdf':
            self.documents = self.load_pdf_menu(document_path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
        
        logger.info(f"Loaded {len(self.documents)} documents total")
    
    def create_vectorstore(self):
        """Create or load ChromaDB vectorstore"""
        if not self.embeddings:
            raise ValueError("Embeddings not initialized. Call initialize_embeddings first.")

        db_path = Path(self.persist_directory)
        if db_path.exists() and any(db_path.iterdir()):
            logger.info(f"Loading existing vectorstore from {self.persist_directory}...")
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
            logger.info("Existing vectorstore loaded.")
        else:
            if not self.documents:
                raise ValueError("No documents loaded to create a new vectorstore.")

            logger.info("Creating new vectorstore...")
            self.vectorstore = Chroma.from_documents(
                documents=self.documents,
                embedding=self.embeddings,
                persist_directory=self.persist_directory,
                collection_name=self.collection_name
            )
            logger.info(f"New vectorstore created with {len(self.documents)} documents.")
    
    @traceable(
        name="rag_retrieve",
        metadata={"pipeline": "menu_rag", "component": "retrieval"},
        tags=["rag", "retrieval", "menu", "vectorstore"]
    )
    def retrieve(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant menu information with comprehensive tracking"""
        start_time = datetime.now()
        
        if not self.vectorstore:
            raise ValueError("Vectorstore not initialized")
        
        try:
            # Perform similarity search
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            
            # Calculate retrieval time
            retrieval_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Format results
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_score": score
                })
            
            # Retrieval metrics tracked via @traceable decorator metadata
            logger.info(f"Retrieved {len(formatted_results)} docs in {retrieval_time:.2f}ms")
            
            return formatted_results
            
        except Exception as e:
            # Track retrieval errors
            error_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Error tracking via logs (log_metrics not available in LangSmith API)
            logger.error(f"RAG retrieval error: {type(e).__name__} after {error_time:.2f}ms")
            
            logger.error(f"Error in RAG retrieval: {e}")
            raise
    
    @traceable(
        name="multi_strategy_retrieve",
        metadata={"pipeline": "menu_rag", "component": "multi_strategy_retrieval"},
        tags=["rag", "retrieval", "multi_strategy", "advanced"]
    )
    def retrieve_with_strategy(self, query: str, retrieval_metadata: Optional[Dict[str, Any]] = None, k: int = 5) -> List[Dict[str, Any]]:
        """
        Advanced retrieval using multiple strategies based on intent metadata
        
        Args:
            query: Original user query
            retrieval_metadata: Metadata from intent classification
            k: Number of documents to retrieve
            
        Returns:
            List of retrieved documents with enhanced metadata
        """
        start_time = datetime.now()
        
        if not self.vectorstore:
            raise ValueError("Vectorstore not initialized")
        
        try:
            # Default to basic retrieval if no metadata
            if not retrieval_metadata:
                return self.retrieve(query, k)
            
            retrieval_approach = retrieval_metadata.get("retrieval_approach", "specialized")
            retrieval_strategy = retrieval_metadata.get("retrieval_strategy", "factual_lookup")
            
            # Choose retrieval strategy
            if retrieval_approach == "specialized":
                results = self._specialized_retrieval(query, retrieval_metadata, k)
            elif retrieval_approach == "hybrid":
                results = self._hybrid_retrieval(query, retrieval_metadata, k)
            elif retrieval_approach == "multi_strategy":
                results = self._multi_strategy_retrieval(query, retrieval_metadata, k)
            else:
                results = self.retrieve(query, k)
            
            # Add strategy metadata to results
            for result in results:
                result["retrieval_strategy"] = retrieval_strategy
                result["retrieval_approach"] = retrieval_approach
            
            retrieval_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"Multi-strategy retrieval ({retrieval_approach}) completed in {retrieval_time:.2f}ms")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in multi-strategy retrieval: {e}")
            # Fallback to basic retrieval
            return self.retrieve(query, k)
    
    def _specialized_retrieval(self, query: str, metadata: Dict[str, Any], k: int) -> List[Dict[str, Any]]:
        """High-confidence specialized retrieval for specific intents"""
        chunk_size = metadata.get("chunk_size", 200)
        rerank_weight = metadata.get("rerank_weight", 0.8)
        
        # Use smaller chunk size for precise retrieval
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        
        formatted_results = []
        for doc, score in results:
            # Apply rerank weighting
            adjusted_score = score * rerank_weight
            
            formatted_results.append({
                "content": doc.page_content[:chunk_size],  # Limit chunk size
                "metadata": doc.metadata,
                "relevance_score": adjusted_score,
                "chunk_size_used": chunk_size
            })
        
        return formatted_results
    
    def _hybrid_retrieval(self, query: str, metadata: Dict[str, Any], k: int) -> List[Dict[str, Any]]:
        """Medium-confidence hybrid retrieval combining multiple approaches"""
        results = []
        
        # Primary retrieval
        primary_results = self.vectorstore.similarity_search_with_score(query, k=k//2 + 1)
        
        # Query expansion if available
        if self.query_expander and metadata.get("supports_expansion", False):
            try:
                expansion = self.query_expander.expand_query(query, metadata)
                
                # Additional retrieval with expanded terms
                for expanded_query in expansion.reformulated_queries[:2]:
                    expanded_results = self.vectorstore.similarity_search_with_score(expanded_query, k=2)
                    primary_results.extend(expanded_results)
                
            except Exception as e:
                logger.warning(f"Query expansion failed in hybrid retrieval: {e}")
        
        # Remove duplicates and format
        seen_content = set()
        for doc, score in primary_results:
            content_hash = hash(doc.page_content[:100])
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_score": score * metadata.get("rerank_weight", 0.7)
                })
        
        return results[:k]
    
    def _multi_strategy_retrieval(self, query: str, metadata: Dict[str, Any], k: int) -> List[Dict[str, Any]]:
        """Low-confidence multi-strategy retrieval for broader coverage"""
        all_results = []
        
        # 1. Basic similarity search
        basic_results = self.vectorstore.similarity_search_with_score(query, k=k//3 + 1)
        
        # 2. Expanded query retrieval
        if self.query_expander:
            try:
                expansion = self.query_expander.expand_query(query, metadata)
                
                # Use reformulated queries
                for reformed_query in expansion.reformulated_queries[:3]:
                    expanded_results = self.vectorstore.similarity_search_with_score(reformed_query, k=2)
                    all_results.extend(expanded_results)
                
                # Use step-back query if available
                if expansion.step_back_query:
                    step_back_results = self.vectorstore.similarity_search_with_score(expansion.step_back_query, k=2)
                    all_results.extend(step_back_results)
                    
            except Exception as e:
                logger.warning(f"Query expansion failed in multi-strategy retrieval: {e}")
        
        # Combine all results
        all_results.extend(basic_results)
        
        # Remove duplicates and diversify
        unique_results = self._diversify_results(all_results, k)
        
        return unique_results
    
    def _diversify_results(self, results: List[tuple], target_count: int) -> List[Dict[str, Any]]:
        """Diversify results to avoid redundancy"""
        if not results:
            return []
        
        # Sort by relevance score
        results.sort(key=lambda x: x[1])
        
        diversified = []
        seen_content = set()
        
        for doc, score in results:
            # Simple content similarity check
            content_snippet = doc.page_content[:100].lower()
            
            # Check for significant overlap with existing results
            is_similar = False
            for seen in seen_content:
                if self._content_similarity(content_snippet, seen) > 0.7:
                    is_similar = True
                    break
            
            if not is_similar:
                seen_content.add(content_snippet)
                diversified.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_score": score
                })
                
                if len(diversified) >= target_count:
                    break
        
        return diversified
    
    def _content_similarity(self, content1: str, content2: str) -> float:
        """Calculate simple content similarity"""
        words1 = set(content1.split())
        words2 = set(content2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    @traceable(
        name="context_generation",
        metadata={"pipeline": "menu_rag", "component": "context_formatting"},
        tags=["rag", "context", "formatting", "llm_input"]
    )
    def get_context_for_query(self, query: str, k: int = 3) -> str:
        """Get formatted context for LLM from query with tracking"""
        start_time = datetime.now()
        
        try:
            results = self.retrieve(query, k)
            
            if not results:
                # Empty results tracked via logs
                logger.warning(f"No relevant results for query: {query}")
                return "No relevant menu information found."
            
            # Generate context
            context = "Here is the relevant menu information:\n\n"
            for i, result in enumerate(results, 1):
                context += f"{i}. {result['content']}\n\n"
            
            formatted_context = context.strip()
            
            # Calculate context generation time
            generation_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Context generation metrics tracked via @traceable decorator
            logger.info(f"Generated context with {len(results)} sections in {generation_time:.2f}ms")
            
            return formatted_context
            
        except Exception as e:
            # Track context generation errors
            error_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Context generation error tracking via logs
            logger.error(f"Context generation error: {type(e).__name__} after {error_time:.2f}ms")
            
            logger.error(f"Error in context generation: {e}")
            raise
    
    @traceable(
        name="enhanced_context_generation",
        metadata={"pipeline": "menu_rag", "component": "enhanced_context_formatting"},
        tags=["rag", "context", "multi_strategy", "enhanced"]
    )
    def get_enhanced_context(self, query: str, retrieval_metadata: Optional[Dict[str, Any]] = None, k: int = 5) -> str:
        """
        Get enhanced formatted context using multi-strategy retrieval
        
        Args:
            query: User query
            retrieval_metadata: Intent classification metadata
            k: Number of documents to retrieve
            
        Returns:
            Formatted context string optimized for the specific intent
        """
        start_time = datetime.now()
        
        try:
            # Use multi-strategy retrieval
            results = self.retrieve_with_strategy(query, retrieval_metadata, k)
            
            if not results:
                logger.warning(f"No relevant results for enhanced query: {query}")
                return "No relevant menu information found."
            
            # Format context based on retrieval strategy
            context_window = retrieval_metadata.get("context_window", "medium") if retrieval_metadata else "medium"
            retrieval_strategy = retrieval_metadata.get("retrieval_strategy", "factual_lookup") if retrieval_metadata else "factual_lookup"
            
            formatted_context = self._format_context_by_strategy(results, context_window, retrieval_strategy)
            
            generation_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"Generated enhanced context ({retrieval_strategy}) with {len(results)} sections in {generation_time:.2f}ms")
            
            return formatted_context
            
        except Exception as e:
            logger.error(f"Error in enhanced context generation: {e}")
            # Fallback to basic context generation
            return self.get_context_for_query(query, k)
    
    def _format_context_by_strategy(self, results: List[Dict[str, Any]], context_window: str, strategy: str) -> str:
        """Format context based on retrieval strategy and window size"""
        
        if strategy == "factual_lookup":
            # Concise, fact-focused formatting
            context = "Relevant menu information:\n\n"
            for i, result in enumerate(results, 1):
                content = result['content'][:200] if context_window == "small" else result['content']
                context += f"{i}. {content}\n\n"
                
        elif strategy == "procedural":
            # Step-by-step formatting for procedures
            context = "Step-by-step information:\n\n"
            for i, result in enumerate(results, 1):
                context += f"Step {i}: {result['content']}\n\n"
                
        elif strategy == "comparative_analysis":
            # Structured comparison formatting
            context = "Comparative menu information:\n\n"
            for i, result in enumerate(results, 1):
                metadata = result.get('metadata', {})
                category = metadata.get('category', 'General')
                context += f"{category} - {result['content']}\n\n"
                
        elif strategy == "conceptual_explanation":
            # Comprehensive explanatory formatting
            context = "Comprehensive menu information:\n\n"
            context += "Overview: " + results[0]['content'] + "\n\n"
            
            if len(results) > 1:
                context += "Additional details:\n"
                for i, result in enumerate(results[1:], 1):
                    context += f"• {result['content']}\n"
                context += "\n"
                
        else:
            # Default formatting
            context = "Here is the relevant menu information:\n\n"
            for i, result in enumerate(results, 1):
                context += f"{i}. {result['content']}\n\n"
        
        return context.strip()

# Initialize the RAG pipeline singleton
_rag_pipeline = None

def get_rag_pipeline() -> MenuRAGPipeline:
    """Get or create the RAG pipeline singleton"""
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = MenuRAGPipeline()
        _rag_pipeline.initialize_embeddings()

        # Only load documents if the vectorstore doesn't exist
        if not Path(_rag_pipeline.persist_directory).exists():
            logger.info("No existing vectorstore found. Loading documents to create a new one.")
            document_path = os.getenv("RAG_DOCUMENT_PATH")
            
            if not document_path:
                # Use relative path as fallback
                default_path = RAG_PIPELINE_DIR / "RAG_DOCS" / "menu-items.csv"
                if default_path.exists():
                    document_path = str(default_path)
                    logger.info(f"Using default document path: {document_path}")
                else:
                    raise FileNotFoundError(
                        "RAG_DOCUMENT_PATH environment variable not set and default path not found. "
                        f"Please set RAG_DOCUMENT_PATH or place menu-items.csv at {default_path}"
                    )
            
            _rag_pipeline.load_documents(document_path)
        
        _rag_pipeline.create_vectorstore()
        logger.info("RAG pipeline initialized successfully")

    return _rag_pipeline
