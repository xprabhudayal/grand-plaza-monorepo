"""
RAG Pipeline for Hotel Menu System
Handles both CSV and PDF document processing with ChromaDB
"""

import os
import pandas as pd
from typing import List, Dict, Any, Optional
from pathlib import Path
import pypdf
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_mistralai import MistralAIEmbeddings
from langchain.schema import Document
from loguru import logger
import re

class MenuRAGPipeline:
    """RAG Pipeline for menu information retrieval"""
    
    def __init__(self, 
                 persist_directory: str = "./chroma_db",
                 collection_name: str = "hotel_menu"):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embeddings = None
        self.vectorstore = None
        self.documents = []
        
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
            
            # Create comprehensive text for each item
            content = f"""
            Category: {current_section}
            Item: {item_name}
            Description: {description}
            Type: {veg_status}
            Calories: {calories}
            Price: {price}
            
            This {item_name} is a {veg_status.lower()} item from our {current_section.lower()} menu.
            {description}
            It contains {calories} calories and costs {price}.
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
                # Pattern for menu items in table format
                table_pattern = r'([A-Za-z\s]+?)\s+\$?(\d+\.?\d*)\s+([\w\s,.-]+)'
                
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

        if Path(self.persist_directory).exists():
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
    
    def retrieve(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant menu information"""
        if not self.vectorstore:
            raise ValueError("Vectorstore not initialized")
        
        # Perform similarity search
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        
        # Format results
        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "relevance_score": score
            })
        
        return formatted_results
    
    def get_context_for_query(self, query: str, k: int = 3) -> str:
        """Get formatted context for LLM from query"""
        results = self.retrieve(query, k)
        
        if not results:
            return "No relevant menu information found."
        
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
            document_path = os.getenv("RAG_DOCUMENT_PATH", "/Users/prada/Desktop/coding/PYTHON/voice_ai_concierge/backend/RAG_DOCS/menu-items.csv")
            _rag_pipeline.load_documents(document_path)
        
        _rag_pipeline.create_vectorstore()
        logger.info("RAG pipeline initialized successfully")

    return _rag_pipeline