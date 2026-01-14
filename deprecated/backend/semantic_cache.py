"""
Semantic Caching Layer for RAG Pipeline
Caches results based on semantic similarity using ChromaDB for unified storage
"""

import os
import hashlib
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
from langchain_community.vectorstores import Chroma
from langchain_mistralai import MistralAIEmbeddings
from loguru import logger


class ChromaSemanticCache:
    """Semantic caching system using ChromaDB for unified storage"""
    
    def __init__(self, 
                 chroma_dir: str = "./chroma_db",
                 similarity_threshold: float = 0.95,
                 max_cache_size: int = 1000,
                 cache_ttl_hours: int = 24):
        """
        Initialize semantic cache with ChromaDB
        
        Args:
            chroma_dir: ChromaDB directory (shared with RAG pipeline)
            similarity_threshold: Minimum similarity score to consider a cache hit
            max_cache_size: Maximum number of cached items
            cache_ttl_hours: Time to live for cached items in hours
        """
        self.chroma_dir = Path(chroma_dir)
        self.similarity_threshold = similarity_threshold
        self.max_cache_size = max_cache_size
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        
        # Use shared ChromaDB instance
        self.cache_vectorstore = None
        self._initialize_cache_vectorstore()
    
    def _get_shared_embeddings(self):
        """Get shared Mistral embeddings to reuse existing connection"""
        try:
            return MistralAIEmbeddings(
                api_key=os.getenv("MISTRAL_API_KEY"),
                model="mistral-embed"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Mistral embeddings for cache: {e}")
            raise
    
    def _initialize_cache_vectorstore(self):
        """Initialize ChromaDB vectorstore for semantic caching"""
        try:
            embeddings = self._get_shared_embeddings()
            collection_name = "semantic_query_cache"
            
            # Initialize ChromaDB with cache-specific collection
            self.cache_vectorstore = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=str(self.chroma_dir)
            )
            
            existing_count = self.cache_vectorstore._collection.count()
            logger.info(f"Initialized semantic cache with {existing_count} existing entries in ChromaDB")
            
        except Exception as e:
            logger.error(f"Failed to initialize cache vectorstore: {e}")
            raise
    
    def _generate_cache_id(self, query: str) -> str:
        """Generate a unique cache ID for the query"""
        return f"cache_{hashlib.md5(query.lower().strip().encode()).hexdigest()}"
    
    def _is_expired(self, timestamp_str: str) -> bool:
        """Check if cached entry is expired"""
        try:
            cache_time = datetime.fromisoformat(timestamp_str)
            return datetime.now() - cache_time > self.cache_ttl
        except:
            return True  # Treat invalid timestamps as expired
    
    def get_cached_result(self, query: str) -> Optional[str]:
        """
        Get cached result for a query using semantic similarity
        
        Args:
            query: The query to search cache for
            
        Returns:
            Cached result if found with sufficient similarity, None otherwise
        """
        if not query or not query.strip():
            return None
        
        try:
            # Search for similar cached queries
            search_results = self.cache_vectorstore.similarity_search_with_score(
                query=query.strip(),
                k=5  # Check top 5 most similar
            )
            
            for doc, distance in search_results:
                # Convert distance to similarity (ChromaDB returns distance)
                similarity = 1.0 / (1.0 + distance) if distance > 0 else 1.0
                
                # Check similarity threshold
                if similarity >= self.similarity_threshold:
                    # Check if entry is expired
                    timestamp = doc.metadata.get("timestamp", "")
                    if not self._is_expired(timestamp):
                        cached_result = doc.metadata.get("result", "")
                        logger.debug(f"Cache hit: similarity={similarity:.3f}, query='{query[:50]}...'")
                        return cached_result
                    else:
                        # Remove expired entry
                        self._remove_expired_entry(doc.metadata.get("cache_id", ""))
            
            logger.debug(f"Cache miss for query: '{query[:50]}...'")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None
    
    def cache_result(self, query: str, result: str):
        """
        Cache a query result using ChromaDB
        
        Args:
            query: The original query
            result: The result to cache
        """
        if not query or not result:
            return
        
        try:
            cache_id = self._generate_cache_id(query)
            current_time = datetime.now().isoformat()
            
            # Check if we need to clean up old entries
            current_count = self.cache_vectorstore._collection.count()
            if current_count >= self.max_cache_size:
                self._cleanup_old_entries()
            
            # Add to ChromaDB
            self.cache_vectorstore.add_texts(
                texts=[query],  # Store query as the searchable text
                metadatas=[{
                    "cache_id": cache_id,
                    "result": result,
                    "timestamp": current_time,
                    "query_hash": hashlib.md5(query.encode()).hexdigest()
                }],
                ids=[cache_id]
            )
            
            # Persist the database
            self.cache_vectorstore.persist()
            logger.debug(f"Cached result for query: '{query[:50]}...'")
            
        except Exception as e:
            logger.error(f"Error caching result: {e}")
    
    def _remove_expired_entry(self, cache_id: str):
        """Remove an expired entry from the cache"""
        try:
            if cache_id:
                self.cache_vectorstore.delete([cache_id])
                self.cache_vectorstore.persist()
                logger.debug(f"Removed expired cache entry: {cache_id}")
        except Exception as e:
            logger.warning(f"Error removing expired entry: {e}")
    
    def _cleanup_old_entries(self):
        """Clean up old entries when cache is full"""
        try:
            # Get all documents to find oldest ones
            all_docs = self.cache_vectorstore.get()
            if not all_docs or not all_docs['metadatas']:
                return
            
            # Sort by timestamp and remove oldest 20%
            docs_with_time = []
            for i, metadata in enumerate(all_docs['metadatas']):
                timestamp_str = metadata.get('timestamp', '')
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    docs_with_time.append((all_docs['ids'][i], timestamp))
                except:
                    # Add invalid timestamps as very old
                    docs_with_time.append((all_docs['ids'][i], datetime.min))
            
            # Sort by timestamp (oldest first)
            docs_with_time.sort(key=lambda x: x[1])
            
            # Remove oldest 20% entries
            num_to_remove = max(1, len(docs_with_time) // 5)
            ids_to_remove = [doc_id for doc_id, _ in docs_with_time[:num_to_remove]]
            
            self.cache_vectorstore.delete(ids_to_remove)
            self.cache_vectorstore.persist()
            
            logger.info(f"Cleaned up {num_to_remove} old cache entries")
            
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            total_entries = self.cache_vectorstore._collection.count()
            
            # Count expired entries
            all_docs = self.cache_vectorstore.get()
            expired_count = 0
            if all_docs and all_docs['metadatas']:
                for metadata in all_docs['metadatas']:
                    timestamp_str = metadata.get('timestamp', '')
                    if self._is_expired(timestamp_str):
                        expired_count += 1
            
            return {
                "total_entries": total_entries,
                "expired_entries": expired_count,
                "active_entries": total_entries - expired_count,
                "max_cache_size": self.max_cache_size,
                "similarity_threshold": self.similarity_threshold,
                "cache_ttl_hours": self.cache_ttl.total_seconds() / 3600
            }
            
        except Exception as e:
            logger.error(f"Error getting cache statistics: {e}")
            return {"error": str(e)}
    
    def clear_cache(self):
        """Clear all cached entries"""
        try:
            # Delete the entire collection
            collection_name = "semantic_query_cache"
            self.cache_vectorstore.delete_collection()
            
            # Reinitialize
            self._initialize_cache_vectorstore()
            
            logger.info("Semantic cache cleared successfully")
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")


class NoOpSemanticCache:
    """No-op semantic cache for when caching is disabled"""
    
    def get_cached_result(self, query: str) -> Optional[str]:
        return None
    
    def cache_result(self, query: str, result: str):
        pass
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        return {"status": "disabled"}
    
    def clear_cache(self):
        pass


# Global cache instance
_semantic_cache = None

def get_semantic_cache() -> ChromaSemanticCache:
    """Get or create the semantic cache singleton"""
    global _semantic_cache
    if _semantic_cache is None:
        cache_enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
        if cache_enabled:
            _semantic_cache = ChromaSemanticCache()
        else:
            # Return a no-op cache if disabled
            _semantic_cache = NoOpSemanticCache()
    
    return _semantic_cache


def clear_semantic_cache():
    """Clear the semantic cache"""
    cache = get_semantic_cache()
    cache.clear_cache()


def get_cache_stats() -> Dict[str, Any]:
    """Get semantic cache statistics"""
    cache = get_semantic_cache()
    return cache.get_cache_statistics()


# Test function for validation
def test_semantic_cache():
    """Test the semantic cache functionality"""
    cache = get_semantic_cache()
    
    print("Testing Semantic Cache (ChromaDB):")
    print("=" * 40)
    
    # Test caching
    test_queries = [
        ("What pizza options do you have?", "We have Margherita, Pepperoni, and Veggie Supreme pizzas."),
        ("Show me vegetarian food", "Our vegetarian options include Veggie Supreme Pizza and Quinoa Salad."),
        ("What drinks are available?", "We offer sodas, juices, coffee, and specialty cocktails.")
    ]
    
    # Cache some results
    for query, result in test_queries:
        cache.cache_result(query, result)
        print(f"Cached: '{query}' -> '{result[:30]}...'")
    
    print("\n" + "-" * 30)
    
    # Test retrieval with similar queries
    similar_queries = [
        "What pizza do you serve?",  # Should hit "What pizza options do you have?"
        "Do you have vegetarian meals?",  # Should hit "Show me vegetarian food" 
        "What beverages do you offer?"  # Should hit "What drinks are available?"
    ]
    
    for query in similar_queries:
        result = cache.get_cached_result(query)
        if result:
            print(f"Cache HIT: '{query}' -> '{result[:30]}...'")
        else:
            print(f"Cache MISS: '{query}'")
    
    # Show statistics
    stats = cache.get_cache_statistics()
    print(f"\nCache Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    test_semantic_cache()