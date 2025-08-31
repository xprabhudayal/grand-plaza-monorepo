"""
Simplified Retrieval Engine
Reduces complexity from 4 strategies to 2: Confidence-based and Exploratory
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from langchain.schema import Document
from loguru import logger
from langsmith import traceable

from rag_config import get_rag_config
from chroma_manager import get_db_manager, chroma_distance_to_similarity


class SimplifiedRetrievalEngine:
    """Simplified retrieval engine with 2 strategies instead of 4"""
    
    def __init__(self, config=None):
        self.config = config or get_rag_config()
        self.db_manager = get_db_manager()
        self._vectorstore = None
        self._query_expander = None
        
    def _get_vectorstore(self):
        """Get the main vectorstore"""
        if self._vectorstore is None:
            self._vectorstore = self.db_manager.get_collection("hotel_menu")
        return self._vectorstore
    
    def _get_query_expander(self):
        """Get query expander (lazy loading to avoid circular import)"""
        if self._query_expander is None:
            try:
                from query_expansion_simplified import get_query_expander
                self._query_expander = get_query_expander()
            except ImportError:
                logger.warning("Query expander not available")
                self._query_expander = None
        return self._query_expander
    
    @traceable(name="simplified_retrieve", tags=["rag", "retrieval"])
    def retrieve(self, query: str, retrieval_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Main retrieval method with simplified strategy selection
        
        Args:
            query: User query
            retrieval_metadata: Optional metadata from intent classification
            
        Returns:
            List of retrieved documents with metadata
        """
        start_time = datetime.now()
        
        if not query or not query.strip():
            return []
        
        try:
            vectorstore = self._get_vectorstore()
            
            # Determine strategy based on confidence
            confidence = retrieval_metadata.get("confidence", 0.5) if retrieval_metadata else 0.5
            
            if confidence >= self.config.intent_medium_confidence:
                # High/Medium confidence: Use confidence-based retrieval
                results = self._confidence_based_retrieval(query, retrieval_metadata, vectorstore)
            else:
                # Low confidence: Use exploratory retrieval
                results = self._exploratory_retrieval(query, retrieval_metadata, vectorstore)
            
            # Add timing metadata
            retrieval_time = (datetime.now() - start_time).total_seconds() * 1000
            for result in results:
                result["retrieval_time_ms"] = retrieval_time
                result["strategy_used"] = "confidence_based" if confidence >= self.config.intent_medium_confidence else "exploratory"
            
            logger.debug(f"Retrieved {len(results)} documents in {retrieval_time:.2f}ms")
            return results
            
        except Exception as e:
            logger.error(f"Error in retrieval: {e}")
            return []
    
    def _confidence_based_retrieval(self, query: str, metadata: Optional[Dict[str, Any]], vectorstore) -> List[Dict[str, Any]]:
        """
        High/Medium confidence retrieval: Focused and precise
        """
        confidence = metadata.get("confidence", 0.7) if metadata else 0.7
        
        # Determine parameters based on confidence level
        if confidence >= self.config.intent_high_confidence:
            k = self.config.retrieval_k
            chunk_size = self.config.retrieval_specialized_chunk_size
            weight = self.config.retrieval_high_confidence_weight
        else:
            k = self.config.retrieval_k + 1
            chunk_size = self.config.retrieval_hybrid_chunk_size
            weight = self.config.retrieval_medium_confidence_weight
        
        # Perform similarity search
        search_results = vectorstore.similarity_search_with_score(query.strip(), k=k)
        
        formatted_results = []
        for doc, distance in search_results:
            similarity = chroma_distance_to_similarity(distance)
            
            # Apply confidence-based weight adjustment
            adjusted_score = similarity * weight
            
            formatted_results.append({
                "content": doc.page_content[:chunk_size] if chunk_size else doc.page_content,
                "metadata": doc.metadata,
                "relevance_score": adjusted_score,
                "original_similarity": similarity,
                "confidence_weight": weight,
                "chunk_size_used": chunk_size
            })
        
        return formatted_results
    
    def _exploratory_retrieval(self, query: str, metadata: Optional[Dict[str, Any]], vectorstore) -> List[Dict[str, Any]]:
        """
        Low confidence retrieval: Broader exploration with query expansion
        """
        all_results = []
        
        # 1. Basic similarity search
        basic_results = vectorstore.similarity_search_with_score(
            query.strip(), 
            k=self.config.retrieval_k
        )
        
        # 2. Try query expansion if available
        expander = self._get_query_expander()
        if expander and metadata:
            try:
                expansion = expander.expand_query(query, metadata)
                
                # Use expanded queries
                for expanded_query in expansion.reformulated_queries[:2]:  # Limit to 2
                    expanded_results = vectorstore.similarity_search_with_score(
                        expanded_query, 
                        k=2
                    )
                    all_results.extend(expanded_results)
            except Exception as e:
                logger.warning(f"Query expansion failed: {e}")
        
        # Combine basic results
        all_results.extend(basic_results)
        
        # Remove duplicates and diversify
        unique_results = self._diversify_results(all_results, self.config.retrieval_k + 2)
        
        # Format results
        formatted_results = []
        for doc, distance in unique_results:
            similarity = chroma_distance_to_similarity(distance)
            
            # Apply low confidence weight
            adjusted_score = similarity * self.config.retrieval_low_confidence_weight
            
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "relevance_score": adjusted_score,
                "original_similarity": similarity,
                "confidence_weight": self.config.retrieval_low_confidence_weight
            })
        
        return formatted_results
    
    def _diversify_results(self, results: List[Tuple], target_count: int) -> List[Tuple]:
        """Remove duplicate and similar results"""
        if not results:
            return []
        
        # Sort by relevance (distance - lower is better)
        results.sort(key=lambda x: x[1])
        
        diversified = []
        seen_content = set()
        
        for doc, distance in results:
            # Simple content similarity check
            content_snippet = doc.page_content[:100].lower()
            content_words = set(content_snippet.split())
            
            # Check for significant overlap with existing results
            is_similar = False
            for seen_words in seen_content:
                overlap = len(content_words.intersection(seen_words))
                if overlap > len(content_words) * 0.7:  # 70% overlap threshold
                    is_similar = True
                    break
            
            if not is_similar:
                seen_content.add(content_words)
                diversified.append((doc, distance))
                
                if len(diversified) >= target_count:
                    break
        
        return diversified
    
    def get_context_for_query(self, query: str, retrieval_metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Get formatted context string for LLM
        
        Args:
            query: User query
            retrieval_metadata: Optional metadata from intent classification
            
        Returns:
            Formatted context string
        """
        results = self.retrieve(query, retrieval_metadata)
        
        if not results:
            return "No relevant information found."
        
        # Format based on retrieval strategy
        strategy = retrieval_metadata.get("retrieval_strategy", "factual_lookup") if retrieval_metadata else "factual_lookup"
        
        if strategy == "factual_lookup":
            context = "Here is the relevant information:\n\n"
            for i, result in enumerate(results, 1):
                context += f"{i}. {result['content']}\n\n"
        
        elif strategy == "comparative_analysis":
            context = "Comparative information:\n\n"
            for result in results:
                category = result.get('metadata', {}).get('category', 'General')
                context += f"**{category}**: {result['content']}\n\n"
        
        else:  # Default comprehensive format
            context = "Available information:\n\n"
            for i, result in enumerate(results, 1):
                context += f"• {result['content']}\n"
            context += "\n"
        
        return context.strip()


# Global retrieval engine instance  
_retrieval_engine = None

def get_retrieval_engine() -> SimplifiedRetrievalEngine:
    """Get the global retrieval engine"""
    global _retrieval_engine
    if _retrieval_engine is None:
        _retrieval_engine = SimplifiedRetrievalEngine()
    return _retrieval_engine


def retrieve_for_query(query: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Convenience function for retrieval"""
    engine = get_retrieval_engine()
    return engine.retrieve(query, metadata)


def get_context_for_query(query: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Convenience function for context generation"""
    engine = get_retrieval_engine()
    return engine.get_context_for_query(query, metadata)


if __name__ == "__main__":
    # Test the simplified retrieval engine
    engine = get_retrieval_engine()
    
    test_query = "What vegetarian options do you have?"
    test_metadata = {"confidence": 0.8, "retrieval_strategy": "factual_lookup"}
    
    print("Testing Simplified Retrieval Engine:")
    print("=" * 50)
    print(f"Query: {test_query}")
    
    results = engine.retrieve(test_query, test_metadata)
    print(f"Retrieved {len(results)} results")
    
    context = engine.get_context_for_query(test_query, test_metadata)
    print(f"Context length: {len(context)} characters")