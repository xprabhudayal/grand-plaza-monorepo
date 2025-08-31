"""
Unified Database Manager for ChromaDB
Manages all ChromaDB connections and collections in one place
"""

import os
from typing import Dict, Optional, Any, List
from pathlib import Path
from langchain_community.vectorstores import Chroma
from langchain_mistralai import MistralAIEmbeddings
from loguru import logger
from rag_config import get_rag_config


class ChromaDBManager:
    """Centralized ChromaDB manager for all collections"""
    
    def __init__(self, config=None):
        self.config = config or get_rag_config()
        self._embeddings = None
        self._collections: Dict[str, Chroma] = {}
        self._initialized = False
        
    def _get_embeddings(self):
        """Get shared embeddings instance"""
        if self._embeddings is None:
            api_key = os.getenv("MISTRAL_API_KEY")
            if not api_key:
                raise ValueError("MISTRAL_API_KEY not found in environment variables")
            
            self._embeddings = MistralAIEmbeddings(
                model="mistral-embed",
                mistral_api_key=api_key
            )
            logger.info("Initialized shared Mistral embeddings")
        
        return self._embeddings
    
    def initialize(self):
        """Initialize the database manager"""
        if self._initialized:
            return
            
        # Ensure database directory exists
        db_path = Path(self.config.chroma_db_path)
        db_path.mkdir(parents=True, exist_ok=True)
        
        self._initialized = True
        logger.info(f"ChromaDB manager initialized with path: {self.config.chroma_db_path}")
    
    def get_collection(self, collection_name: str) -> Chroma:
        """Get or create a ChromaDB collection"""
        if not self._initialized:
            self.initialize()
            
        if collection_name in self._collections:
            return self._collections[collection_name]
        
        try:
            embeddings = self._get_embeddings()
            
            vectorstore = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=self.config.chroma_db_path
            )
            
            self._collections[collection_name] = vectorstore
            logger.info(f"Initialized ChromaDB collection: {collection_name}")
            
            return vectorstore
            
        except Exception as e:
            logger.error(f"Failed to initialize collection {collection_name}: {e}")
            raise
    
    def create_collection_with_documents(self, collection_name: str, documents: List[Any]) -> Chroma:
        """Create a new collection with documents"""
        if not self._initialized:
            self.initialize()
            
        try:
            embeddings = self._get_embeddings()
            
            vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=embeddings,
                persist_directory=self.config.chroma_db_path,
                collection_name=collection_name
            )
            
            self._collections[collection_name] = vectorstore
            logger.info(f"Created ChromaDB collection {collection_name} with {len(documents)} documents")
            
            return vectorstore
            
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise
    
    def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists"""
        if not self._initialized:
            self.initialize()
            
        try:
            vectorstore = self.get_collection(collection_name)
            return vectorstore._collection.count() > 0
        except:
            return False
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics for a collection"""
        try:
            vectorstore = self.get_collection(collection_name)
            count = vectorstore._collection.count()
            
            return {
                "collection_name": collection_name,
                "document_count": count,
                "status": "active" if count > 0 else "empty"
            }
        except Exception as e:
            return {
                "collection_name": collection_name,
                "document_count": 0,
                "status": "error",
                "error": str(e)
            }
    
    def delete_collection(self, collection_name: str):
        """Delete a collection"""
        try:
            if collection_name in self._collections:
                self._collections[collection_name].delete_collection()
                del self._collections[collection_name]
                logger.info(f"Deleted collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
    
    def list_collections(self) -> List[str]:
        """List all active collections"""
        return list(self._collections.keys())
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all collections"""
        stats = {
            "total_collections": len(self._collections),
            "database_path": self.config.chroma_db_path,
            "collections": {}
        }
        
        for collection_name in self._collections.keys():
            stats["collections"][collection_name] = self.get_collection_stats(collection_name)
        
        return stats
    
    def cleanup(self):
        """Cleanup all connections"""
        self._collections.clear()
        self._embeddings = None
        self._initialized = False
        logger.info("ChromaDB manager cleanup completed")


# Utility functions for distance/similarity conversion
def chroma_distance_to_similarity(distance: float, max_distance: float = 2.0) -> float:
    """
    Convert ChromaDB distance to similarity score
    ChromaDB returns distance (0 = perfect match), we need similarity (1 = perfect match)
    """
    return max(0.0, 1.0 - (distance / max_distance))


def chroma_similarity_to_distance(similarity: float, max_distance: float = 2.0) -> float:
    """Convert similarity score to ChromaDB distance"""
    return max_distance * (1.0 - similarity)


# Global manager instance
_db_manager = None

def get_db_manager() -> ChromaDBManager:
    """Get the global database manager"""
    global _db_manager
    if _db_manager is None:
        _db_manager = ChromaDBManager()
        _db_manager.initialize()
    return _db_manager


def get_collection(collection_name: str) -> Chroma:
    """Convenience function to get a collection"""
    return get_db_manager().get_collection(collection_name)


def create_collection_with_docs(collection_name: str, documents: List[Any]) -> Chroma:
    """Convenience function to create collection with documents"""
    return get_db_manager().create_collection_with_documents(collection_name, documents)


if __name__ == "__main__":
    # Test the database manager
    manager = get_db_manager()
    print("Database Manager initialized")
    print("=" * 40)
    
    stats = manager.get_all_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")