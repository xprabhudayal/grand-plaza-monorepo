"""
Production-Ready RAG System Integration
Combines all refactored components into a unified, scalable system

Key Improvements:
✅ Single ChromaDB connection manager (no resource leaks)
✅ Unified configuration system (.env driven)
✅ Fixed ChromaDB score conversion bugs
✅ Simplified retrieval strategies (2 instead of 4)
✅ Dependency injection (no global singletons)
✅ Minimal LangSmith tracing (only main phases)
✅ Production-ready error handling
✅ Comprehensive logging and monitoring
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
from langsmith import traceable

# Import refactored components
from rag_config import get_rag_config, RAGConfig
from chroma_manager import get_db_manager
from rag_pipeline_refactored import create_rag_manager, RAGPipelineManager
from intent_classifier_refactored import create_intent_manager, IntentClassifierManager
from query_expansion_simplified import get_query_expander


class ProductionRAGSystem:
    """
    Production-ready RAG system with unified architecture
    
    This system replaces the over-engineered original with:
    - Single database connection manager
    - Configuration-driven parameters
    - Simplified retrieval strategies
    - Fixed critical bugs
    - Production-ready error handling
    """
    
    def __init__(self, config: Optional[RAGConfig] = None):
        """Initialize with unified configuration"""
        self.config = config or get_rag_config()
        
        # Initialize core components with dependency injection
        self.rag_manager = create_rag_manager(self.config)
        self.intent_manager = create_intent_manager(self.config)
        self.query_expander = get_query_expander()
        
        # System state
        self._initialized = False
        self._stats = {
            "system_start_time": datetime.now().isoformat(),
            "total_queries_processed": 0,
            "successful_retrievals": 0,
            "failed_retrievals": 0,
            "average_response_time_ms": 0.0
        }
        
        logger.info("ProductionRAGSystem initialized with unified architecture")
    
    def initialize(self):
        """Initialize the entire RAG system"""
        if self._initialized:
            logger.info("System already initialized")
            return
        
        try:
            # Initialize RAG pipeline
            rag_pipeline = self.rag_manager.get_pipeline()
            
            # Initialize intent classifier  
            intent_classifier = self.intent_manager.get_classifier()
            
            self._initialized = True
            logger.info("ProductionRAGSystem initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ProductionRAGSystem: {e}")
            raise
    
    @traceable(name="production_rag_query", tags=["production", "rag", "main"])
    def process_query(self, query: str, include_debug_info: bool = False) -> Dict[str, Any]:
        """
        Main query processing method - simplified LangSmith tracing
        
        Args:
            query: User query string
            include_debug_info: Whether to include debug information in response
            
        Returns:
            Dictionary with context, metadata, and optional debug info
        """
        start_time = datetime.now()
        
        if not self._initialized:
            self.initialize()
        
        try:
            # Step 1: Intent Classification
            intent_classifier = self.intent_manager.get_classifier()
            intent_result = intent_classifier.classify_intent(
                query, 
                return_confidence=True,
                include_retrieval_metadata=True
            )
            
            # Step 2: Query Processing (optional expansion handled internally)
            rag_pipeline = self.rag_manager.get_pipeline()
            retrieval_metadata = intent_result.get("retrieval_metadata")
            
            # Step 3: Context Retrieval
            context = rag_pipeline.get_context_for_query(query, retrieval_metadata)
            retrieved_docs = rag_pipeline.retrieve(query, retrieval_metadata)
            
            # Step 4: Prepare Response
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update statistics
            self._update_stats(response_time_ms, success=True)
            
            response = {
                "context": context,
                "intent": intent_result["intent"],
                "confidence": intent_result["confidence"],
                "confidence_level": intent_result["confidence_level"],
                "documents_retrieved": len(retrieved_docs),
                "response_time_ms": response_time_ms,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add debug information if requested
            if include_debug_info:
                response["debug_info"] = {
                    "intent_result": intent_result,
                    "retrieval_metadata": retrieval_metadata,
                    "retrieved_documents": retrieved_docs[:3],  # First 3 for debugging
                    "system_config": {
                        "retrieval_k": self.config.retrieval_k,
                        "chunk_size": self.config.chunk_size,
                        "confidence_thresholds": self.config.get_confidence_thresholds()
                    }
                }
            
            logger.info(f"Query processed successfully: {intent_result['intent']} ({response_time_ms:.2f}ms)")
            return response
            
        except Exception as e:
            error_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            self._update_stats(error_time_ms, success=False)
            
            logger.error(f"Error processing query '{query}': {e}")
            
            return {
                "context": "I apologize, but I'm having trouble processing your request right now.",
                "intent": "error",
                "confidence": 0.0,
                "confidence_level": "error",
                "documents_retrieved": 0,
                "response_time_ms": error_time_ms,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_quick_context(self, query: str) -> str:
        """
        Quick context retrieval without full processing
        Useful for simple queries where intent classification is not needed
        """
        try:
            if not self._initialized:
                self.initialize()
            
            rag_pipeline = self.rag_manager.get_pipeline()
            return rag_pipeline.get_context_for_query(query)
            
        except Exception as e:
            logger.error(f"Error in quick context retrieval: {e}")
            return "I'm unable to find relevant information at the moment."
    
    def batch_process_queries(self, queries: List[str]) -> List[Dict[str, Any]]:
        """Process multiple queries efficiently"""
        if not queries:
            return []
        
        start_time = datetime.now()
        results = []
        
        try:
            for query in queries:
                result = self.process_query(query)
                results.append(result)
            
            batch_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"Batch processed {len(queries)} queries in {batch_time:.2f}ms")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            return [{"error": str(e)} for _ in queries]
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health and statistics"""
        try:
            health = {
                "status": "healthy" if self._initialized else "not_initialized",
                "timestamp": datetime.now().isoformat(),
                "system_stats": self._stats.copy(),
                "component_stats": {}
            }
            
            # Get component statistics
            if self._initialized:
                health["component_stats"] = {
                    "rag_pipeline": self.rag_manager.get_stats(),
                    "intent_classifier": self.intent_manager.get_stats(),
                    "database": get_db_manager().get_all_stats()
                }
            
            # Calculate health metrics
            total_queries = self._stats["total_queries_processed"]
            if total_queries > 0:
                success_rate = self._stats["successful_retrievals"] / total_queries
                health["success_rate"] = success_rate
                health["health_score"] = min(success_rate * 100, 100)
            else:
                health["success_rate"] = 1.0
                health["health_score"] = 100
            
            return health
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _update_stats(self, response_time_ms: float, success: bool):
        """Update system statistics"""
        self._stats["total_queries_processed"] += 1
        
        if success:
            self._stats["successful_retrievals"] += 1
        else:
            self._stats["failed_retrievals"] += 1
        
        # Update average response time
        total_time = (self._stats["average_response_time_ms"] * 
                     (self._stats["total_queries_processed"] - 1) + response_time_ms)
        self._stats["average_response_time_ms"] = (
            total_time / self._stats["total_queries_processed"]
        )
    
    def reload_system(self):
        """Reload the entire system with fresh configuration"""
        logger.info("Reloading ProductionRAGSystem...")
        
        # Reload configuration
        from rag_config import reload_config
        reload_config()
        self.config = get_rag_config()
        
        # Reload components
        self.rag_manager.reload_pipeline()
        self.intent_manager.reload_classifier()
        
        # Reset initialization status
        self._initialized = False
        
        logger.info("ProductionRAGSystem reloaded successfully")
    
    def cleanup(self):
        """Cleanup system resources"""
        try:
            # Cleanup database connections
            get_db_manager().cleanup()
            
            # Reset state
            self._initialized = False
            
            logger.info("ProductionRAGSystem cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Factory function for easy access
def create_production_rag_system(config: Optional[RAGConfig] = None) -> ProductionRAGSystem:
    """
    Factory function to create a production-ready RAG system
    
    Args:
        config: Optional configuration, will use environment-based config if not provided
        
    Returns:
        ProductionRAGSystem instance ready for use
    """
    return ProductionRAGSystem(config)


# Main interface function
def process_query_production(query: str, debug: bool = False) -> Dict[str, Any]:
    """
    Main interface function for query processing in production
    
    Args:
        query: User query string
        debug: Whether to include debug information
        
    Returns:
        Processed query result with context and metadata
    """
    system = create_production_rag_system()
    return system.process_query(query, include_debug_info=debug)


if __name__ == "__main__":
    # Test the production RAG system
    print("🚀 Testing Production RAG System")
    print("=" * 60)
    
    # Create system
    system = create_production_rag_system()
    
    # Test queries
    test_queries = [
        "What vegetarian pizza options do you have?",
        "How much does the BBQ chicken pizza cost?",
        "Does the quinoa salad contain nuts?",
        "I want to order room service"
    ]
    
    print("Processing test queries...")
    for i, query in enumerate(test_queries, 1):
        print(f"\\n{i}. Query: '{query}'")
        
        result = system.process_query(query)
        
        print(f"   Intent: {result['intent']}")
        print(f"   Confidence: {result['confidence']:.3f} ({result['confidence_level']})")
        print(f"   Documents: {result['documents_retrieved']}")
        print(f"   Time: {result['response_time_ms']:.1f}ms")
        print(f"   Context: {result['context'][:100]}...")
    
    # Show system health
    print(f"\\n📊 System Health:")
    health = system.get_system_health()
    print(f"   Status: {health['status']}")
    print(f"   Success Rate: {health.get('success_rate', 0):.1%}")
    print(f"   Total Queries: {health['system_stats']['total_queries_processed']}")
    print(f"   Avg Response Time: {health['system_stats']['average_response_time_ms']:.1f}ms")
    
    # Cleanup
    system.cleanup()
    print("\\n✅ Production RAG System test completed!")