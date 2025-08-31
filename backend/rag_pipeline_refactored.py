"""
Refactored RAG Pipeline - Production Ready
Fixes all critical issues:
- Unified configuration system
- Single ChromaDB connection manager
- Simplified retrieval strategies (2 instead of 4)
- Fixed score conversion bugs
- Dependency injection instead of singletons
- Reduced LangSmith tracing complexity
"""

import os
import pandas as pd
from typing import List, Dict, Any, Optional
from pathlib import Path
import pypdf
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from loguru import logger
import re
from datetime import datetime
from langsmith import traceable

from rag_config import get_rag_config, RAGConfig
from chroma_manager import get_db_manager, ChromaDBManager, chroma_distance_to_similarity
from retrieval_engine import SimplifiedRetrievalEngine


class RefactoredRAGPipeline:
    """
    Production-ready RAG Pipeline with unified architecture
    """
    
    def __init__(self, config: Optional[RAGConfig] = None, db_manager: Optional[ChromaDBManager] = None):
        """Initialize with dependency injection"""
        self.config = config or get_rag_config()
        self.db_manager = db_manager or get_db_manager()
        
        # Core components
        self.retrieval_engine = SimplifiedRetrievalEngine(self.config)
        self.documents = []
        self._vectorstore = None
        
        logger.info("Initialized RefactoredRAGPipeline with unified configuration")
    
    def initialize_embeddings(self, api_key: Optional[str] = None):
        """Initialize embeddings (handled by ChromaDBManager)"""
        # This is now handled by the unified database manager
        self.db_manager.initialize()
        logger.info("Embeddings initialized via ChromaDBManager")
    
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
            
            # Create concise text for each item
            content = f\"\"\"Category: {current_section}
Item: {item_name}
Description: {description}
Type: {veg_status}
Calories: {calories}
Price: {price}

This {item_name} is a {veg_status.lower()} item from our {current_section.lower()} menu.
{description}
It contains {calories} calories and costs {price}.\"\"\"
            
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
        """Load and process PDF menu file with improved text extraction"""
        logger.info(f"Loading PDF menu from {pdf_path}")
        documents = []
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                
                full_text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    full_text += f"\\nPage {page_num + 1}:\\n{text}\\n"
                
                # Use configurable text splitter
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.config.chunk_size,
                    chunk_overlap=self.config.chunk_overlap
                )
                
                chunks = text_splitter.split_text(full_text)
                for i, chunk in enumerate(chunks):
                    documents.append(Document(
                        page_content=chunk,
                        metadata={
                            "source": "menu_pdf_chunk",
                            "chunk_id": i,
                            "total_chunks": len(chunks)
                        }
                    ))
                
        except Exception as e:
            logger.error(f"Error loading PDF: {e}")
            raise
        
        logger.info(f"Loaded {len(documents)} chunks from PDF")
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
    
    @traceable(name="rag_vectorstore_creation", tags=["rag", "setup"])
    def create_vectorstore(self):
        """Create or load ChromaDB vectorstore using unified manager"""
        collection_name = "hotel_menu"
        
        # Check if collection exists
        if self.db_manager.collection_exists(collection_name):
            logger.info(f"Loading existing vectorstore: {collection_name}")
            self._vectorstore = self.db_manager.get_collection(collection_name)
        else:
            if not self.documents:
                raise ValueError("No documents loaded to create a new vectorstore.")
            
            logger.info(f"Creating new vectorstore: {collection_name}")
            self._vectorstore = self.db_manager.create_collection_with_documents(
                collection_name, 
                self.documents
            )
        
        # Update retrieval engine vectorstore reference
        self.retrieval_engine._vectorstore = self._vectorstore
        
        logger.info("Vectorstore initialization completed")
    
    @traceable(name="rag_query_processing", tags=["rag", "query"])
    def retrieve(self, query: str, retrieval_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents using simplified retrieval engine
        
        Args:
            query: User query
            retrieval_metadata: Optional metadata from intent classification
            
        Returns:
            List of retrieved documents with metadata
        """
        if not self._vectorstore:
            raise ValueError("Vectorstore not initialized. Call create_vectorstore() first.")
        
        return self.retrieval_engine.retrieve(query, retrieval_metadata)
    
    @traceable(name="rag_context_generation", tags=["rag", "context"])
    def get_context_for_query(self, query: str, retrieval_metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate formatted context for LLM
        
        Args:
            query: User query
            retrieval_metadata: Optional metadata from intent classification
            
        Returns:
            Formatted context string
        """
        try:
            return self.retrieval_engine.get_context_for_query(query, retrieval_metadata)
        except Exception as e:
            logger.error(f"Error generating context: {e}")
            return "No relevant information could be retrieved."
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics"""
        try:
            db_stats = self.db_manager.get_all_stats()
            
            return {
                "pipeline_type": "RefactoredRAG",
                "configuration": self.config.to_dict(),
                "database_stats": db_stats,
                "documents_loaded": len(self.documents),
                "vectorstore_initialized": self._vectorstore is not None,
                "retrieval_engine_active": True,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting pipeline stats: {e}")
            return {"error": str(e)}


class RAGPipelineManager:
    """
    Manager class for RAG Pipeline with dependency injection
    Replaces global singleton pattern
    """
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or get_rag_config()
        self._pipeline: Optional[RefactoredRAGPipeline] = None
        
    def get_pipeline(self) -> RefactoredRAGPipeline:
        """Get or create RAG pipeline instance"""
        if self._pipeline is None:
            self._pipeline = RefactoredRAGPipeline(self.config)
            
            # Initialize the pipeline
            self._setup_pipeline()
            
        return self._pipeline
    
    def _setup_pipeline(self):
        """Setup the RAG pipeline with configuration"""
        pipeline = self._pipeline
        
        # Initialize embeddings
        pipeline.initialize_embeddings()
        
        # Load documents if needed
        if not self.config.chroma_db_path or not Path(self.config.chroma_db_path).exists():
            document_path = os.getenv("RAG_DOCUMENT_PATH")
            
            if not document_path:
                # Use relative path as fallback
                default_path = Path(__file__).parent / "RAG_DOCS" / "menu-items.csv"
                if default_path.exists():
                    document_path = str(default_path)
                    logger.info(f"Using default document path: {document_path}")
                else:
                    raise FileNotFoundError(
                        "RAG_DOCUMENT_PATH environment variable not set and default path not found. "
                        f"Please set RAG_DOCUMENT_PATH or place menu-items.csv at {default_path}"
                    )
            
            pipeline.load_documents(document_path)
        
        # Create vectorstore
        pipeline.create_vectorstore()
        
        logger.info("RAG pipeline setup completed successfully")
    
    def reload_pipeline(self):
        """Reload pipeline with fresh configuration"""
        self.config = get_rag_config()
        self._pipeline = None
        logger.info("RAG pipeline reloaded")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        if self._pipeline:
            return self._pipeline.get_pipeline_stats()
        else:
            return {"status": "not_initialized"}


# Factory functions for easy access
def create_rag_pipeline(config: Optional[RAGConfig] = None) -> RefactoredRAGPipeline:
    """Factory function to create RAG pipeline"""
    return RefactoredRAGPipeline(config)


def create_rag_manager(config: Optional[RAGConfig] = None) -> RAGPipelineManager:
    """Factory function to create RAG pipeline manager"""
    return RAGPipelineManager(config)


if __name__ == "__main__":
    # Test the refactored RAG pipeline
    print("Testing Refactored RAG Pipeline:")
    print("=" * 50)
    
    # Create pipeline manager
    manager = create_rag_manager()
    pipeline = manager.get_pipeline()
    
    # Test retrieval
    test_query = "What vegetarian options do you have?"
    test_metadata = {"confidence": 0.8, "retrieval_strategy": "factual_lookup"}
    
    context = pipeline.get_context_for_query(test_query, test_metadata)
    print(f"Context generated: {len(context)} characters")
    
    # Show stats
    stats = manager.get_stats()
    print("\\nPipeline Statistics:")
    print(f"Documents loaded: {stats.get('documents_loaded', 'N/A')}")
    print(f"Vectorstore initialized: {stats.get('vectorstore_initialized', 'N/A')}")
    print(f"Database collections: {len(stats.get('database_stats', {}).get('collections', {}))}")