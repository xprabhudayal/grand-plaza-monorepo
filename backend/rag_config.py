"""
Unified Configuration System for RAG Pipeline
Centralizes all configuration using environment variables
"""

import os
from dataclasses import dataclass
from typing import Dict, Any
from pathlib import Path


@dataclass
class RAGConfig:
    """Centralized configuration for the entire RAG system"""
    
    # RAG Pipeline Configuration
    chunk_size: int = 200
    chunk_overlap: int = 10
    retrieval_k: int = 5
    similarity_threshold: float = 0.85
    chroma_db_path: str = "./chroma_db"
    
    # Intent Classification Configuration
    intent_model_name: str = "all-MiniLM-L6-v2"
    intent_high_confidence: float = 0.80
    intent_medium_confidence: float = 0.65
    intent_low_confidence: float = 0.50
    intent_retrieval_k: int = 5
    
    # Query Expansion Configuration
    query_expansion_max_terms: int = 5
    query_expansion_max_reformulations: int = 4
    query_expansion_semantic_k: int = 3
    
    # Retrieval Strategy Configuration
    retrieval_high_confidence_weight: float = 0.8
    retrieval_medium_confidence_weight: float = 0.7
    retrieval_low_confidence_weight: float = 0.3
    retrieval_specialized_chunk_size: int = 200
    retrieval_hybrid_chunk_size: int = 300
    
    # Cache Configuration
    cache_enabled: bool = True
    cache_similarity_threshold: float = 0.95
    cache_max_size: int = 1000
    cache_ttl_hours: int = 24
    
    @classmethod
    def from_env(cls) -> 'RAGConfig':
        """Create configuration from environment variables"""
        return cls(
            # RAG Pipeline
            chunk_size=int(os.getenv("RAG_CHUNK_SIZE", "200")),
            chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "10")),
            retrieval_k=int(os.getenv("RAG_RETRIEVAL_K", "5")),
            similarity_threshold=float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.85")),
            chroma_db_path=os.getenv("RAG_CHROMA_DB_PATH", "./chroma_db"),
            
            # Intent Classification
            intent_model_name=os.getenv("INTENT_MODEL_NAME", "all-MiniLM-L6-v2"),
            intent_high_confidence=float(os.getenv("INTENT_HIGH_CONFIDENCE", "0.80")),
            intent_medium_confidence=float(os.getenv("INTENT_MEDIUM_CONFIDENCE", "0.65")),
            intent_low_confidence=float(os.getenv("INTENT_LOW_CONFIDENCE", "0.50")),
            intent_retrieval_k=int(os.getenv("INTENT_RETRIEVAL_K", "5")),
            
            # Query Expansion
            query_expansion_max_terms=int(os.getenv("QUERY_EXPANSION_MAX_TERMS", "5")),
            query_expansion_max_reformulations=int(os.getenv("QUERY_EXPANSION_MAX_REFORMULATIONS", "4")),
            query_expansion_semantic_k=int(os.getenv("QUERY_EXPANSION_SEMANTIC_K", "3")),
            
            # Retrieval Strategy
            retrieval_high_confidence_weight=float(os.getenv("RETRIEVAL_HIGH_CONFIDENCE_WEIGHT", "0.8")),
            retrieval_medium_confidence_weight=float(os.getenv("RETRIEVAL_MEDIUM_CONFIDENCE_WEIGHT", "0.7")),
            retrieval_low_confidence_weight=float(os.getenv("RETRIEVAL_LOW_CONFIDENCE_WEIGHT", "0.3")),
            retrieval_specialized_chunk_size=int(os.getenv("RETRIEVAL_SPECIALIZED_CHUNK_SIZE", "200")),
            retrieval_hybrid_chunk_size=int(os.getenv("RETRIEVAL_HYBRID_CHUNK_SIZE", "300")),
            
            # Cache
            cache_enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            cache_similarity_threshold=float(os.getenv("CACHE_SIMILARITY_THRESHOLD", "0.95")),
            cache_max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
            cache_ttl_hours=int(os.getenv("CACHE_TTL_HOURS", "24"))
        )
    
    def get_confidence_thresholds(self) -> Dict[str, float]:
        """Get confidence thresholds as dictionary"""
        return {
            "high_confidence": self.intent_high_confidence,
            "medium_confidence": self.intent_medium_confidence,
            "low_confidence": self.intent_low_confidence
        }
    
    def get_retrieval_weights(self) -> Dict[str, float]:
        """Get retrieval weights as dictionary"""
        return {
            "high": self.retrieval_high_confidence_weight,
            "medium": self.retrieval_medium_confidence_weight,
            "low": self.retrieval_low_confidence_weight
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "retrieval_k": self.retrieval_k,
            "similarity_threshold": self.similarity_threshold,
            "chroma_db_path": self.chroma_db_path,
            "intent_model_name": self.intent_model_name,
            "confidence_thresholds": self.get_confidence_thresholds(),
            "retrieval_weights": self.get_retrieval_weights(),
            "cache_enabled": self.cache_enabled,
            "cache_settings": {
                "similarity_threshold": self.cache_similarity_threshold,
                "max_size": self.cache_max_size,
                "ttl_hours": self.cache_ttl_hours
            }
        }


# Global configuration instance
_config = None

def get_rag_config() -> RAGConfig:
    """Get the global RAG configuration"""
    global _config
    if _config is None:
        _config = RAGConfig.from_env()
    return _config


def reload_config():
    """Reload configuration from environment"""
    global _config
    _config = RAGConfig.from_env()


# Utility functions for easy access
def get_config_value(key: str, default=None):
    """Get a specific configuration value"""
    config = get_rag_config()
    return getattr(config, key, default)


if __name__ == "__main__":
    # Test configuration loading
    config = get_rag_config()
    print("RAG Configuration loaded:")
    print("=" * 40)
    for key, value in config.to_dict().items():
        print(f"{key}: {value}")