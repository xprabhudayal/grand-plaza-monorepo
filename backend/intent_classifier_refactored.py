"""
Refactored Semantic Intent Classifier
Fixes critical bugs and reduces complexity:
- Fixed ChromaDB score conversion bug
- Uses unified configuration system
- Dependency injection instead of singleton
- Simplified LangSmith tracing
"""

import os
import numpy as np
from typing import Dict, List, Optional, Any
from sentence_transformers import SentenceTransformer
from loguru import logger
from datetime import datetime

from rag_config import get_rag_config, RAGConfig
from chroma_manager import get_db_manager, ChromaDBManager, chroma_distance_to_similarity
from intent_training_data import (
    get_intent_examples, 
    get_intent_descriptions, 
    get_intent_priorities,
    get_all_intents
)


class SentenceTransformerWrapper:
    """Wrapper to make SentenceTransformer compatible with LangChain embeddings interface"""
    
    def __init__(self, model: SentenceTransformer):
        self.model = model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents"""
        embeddings = self.model.encode(texts)
        return embeddings.tolist()
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query"""
        embedding = self.model.encode([text])[0]
        return embedding.tolist()


class RefactoredIntentClassifier:
    """Production-ready intent classifier with unified architecture"""
    
    def __init__(self, config: Optional[RAGConfig] = None, db_manager: Optional[ChromaDBManager] = None):
        """Initialize with dependency injection"""
        self.config = config or get_rag_config()
        self.db_manager = db_manager or get_db_manager()
        
        # Initialize models and data
        self.model = None
        self.intent_vectorstore = None
        
        # Training data
        self.intent_examples = get_intent_examples()
        self.intent_descriptions = get_intent_descriptions()
        self.confidence_thresholds = self.config.get_confidence_thresholds()
        self.intent_priorities = get_intent_priorities()
        
        # Performance tracking
        self.stats = {
            "total_classifications": 0,
            "high_confidence_count": 0,
            "medium_confidence_count": 0,
            "low_confidence_count": 0,
            "fallback_count": 0,
            "average_classification_time": 0.0
        }
        
        # Initialize the classifier
        self._initialize_model()
        self._initialize_intent_vectorstore()
    
    def _initialize_model(self):
        """Initialize the sentence transformer model"""
        try:
            self.model = SentenceTransformer(self.config.intent_model_name)
            logger.info(f"Initialized semantic intent classifier: {self.config.intent_model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize intent classification model: {e}")
            raise
    
    def _initialize_intent_vectorstore(self):
        """Initialize or load ChromaDB vectorstore for intent embeddings"""
        try:
            collection_name = "intent_embeddings"
            
            # Check if intent embeddings already exist
            if self.db_manager.collection_exists(collection_name):
                self.intent_vectorstore = self.db_manager.get_collection(collection_name)
                logger.info(f"Loaded existing intent embeddings from ChromaDB")
            else:
                logger.info("No existing intent embeddings found, generating new ones...")
                self._generate_and_store_intent_embeddings()
                
        except Exception as e:
            logger.error(f"Failed to initialize intent vectorstore: {e}")
            raise
    
    def _generate_and_store_intent_embeddings(self):
        """Generate and store intent embeddings in ChromaDB"""
        logger.info("Generating intent embeddings for ChromaDB storage...")
        
        documents = []
        for intent, examples in self.intent_examples.items():
            description = self.intent_descriptions.get(intent, "")
            
            # Create comprehensive texts for each intent
            for i, example in enumerate(examples):
                # Combine example with description for richer representation
                combined_text = f"{example} {description}" if description else example
                
                from langchain.schema import Document
                doc = Document(
                    page_content=combined_text,
                    metadata={
                        "intent": intent,
                        "example_index": i,
                        "priority": self.intent_priorities.get(intent, 1),
                        "description": description,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                documents.append(doc)
        
        # Create collection with documents
        self.intent_vectorstore = self.db_manager.create_collection_with_documents(
            "intent_embeddings", 
            documents
        )
        
        logger.info(f"Generated and stored {len(documents)} intent embeddings in ChromaDB")
    
    def classify_intent(self, text: str, return_confidence: bool = True, include_retrieval_metadata: bool = False) -> Dict[str, Any]:
        """
        Classify intent using ChromaDB semantic similarity search
        
        Args:
            text: Input text to classify
            return_confidence: Whether to return confidence scores
            include_retrieval_metadata: Whether to include retrieval strategy metadata
            
        Returns:
            Dictionary with intent classification results and optional retrieval metadata
        """
        start_time = datetime.now()
        
        try:
            if not text or not text.strip():
                return self._create_classification_result("general_assistance", 0.5, "empty_input")
            
            # Search for similar intent examples using ChromaDB
            search_results = self.intent_vectorstore.similarity_search_with_score(
                query=text.strip(),
                k=self.config.intent_retrieval_k
            )
            
            if not search_results:
                return self._create_classification_result("general_assistance", 0.0, "no_matches")
            
            # Aggregate scores by intent - FIXED SCORE CONVERSION
            intent_scores = {}
            for doc, distance in search_results:
                intent = doc.metadata["intent"]
                # FIXED: Convert ChromaDB distance to similarity correctly
                similarity = chroma_distance_to_similarity(distance)
                
                if intent not in intent_scores:
                    intent_scores[intent] = []
                intent_scores[intent].append(similarity)
            
            # Calculate average similarity for each intent
            intent_confidences = {}
            for intent, scores in intent_scores.items():
                intent_confidences[intent] = np.mean(scores)
            
            # Get best match
            best_intent = max(intent_confidences, key=intent_confidences.get)
            confidence = intent_confidences[best_intent]
            
            # Determine confidence level
            confidence_level = self._get_confidence_level(confidence)
            
            # Handle low confidence cases
            if confidence_level == "very_low":
                best_intent = self._get_fallback_intent(intent_confidences)
                confidence_level = "fallback"
                self.stats["fallback_count"] += 1
            else:
                self.stats[f"{confidence_level}_confidence_count"] += 1
            
            # Update statistics
            self._update_stats(start_time)
            
            result = self._create_classification_result(
                best_intent, confidence, confidence_level, intent_confidences if return_confidence else None
            )
            
            # Add retrieval metadata if requested
            if include_retrieval_metadata:
                result["retrieval_metadata"] = self._generate_retrieval_metadata(best_intent, confidence, confidence_level)
            
            logger.debug(f"Intent classified: '{best_intent}' (confidence: {confidence:.3f})")
            return result
            
        except Exception as e:
            logger.error(f"Error in intent classification: {e}")
            return self._create_classification_result("general_assistance", 0.0, "error")
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Determine confidence level from confidence score"""
        if confidence >= self.confidence_thresholds["high_confidence"]:
            return "high"
        elif confidence >= self.confidence_thresholds["medium_confidence"]:
            return "medium"
        elif confidence >= self.confidence_thresholds["low_confidence"]:
            return "low"
        else:
            return "very_low"
    
    def _get_fallback_intent(self, similarities: Dict[str, float]) -> str:
        """Get fallback intent based on priorities when confidence is very low"""
        # Sort intents by priority (higher = more important)
        sorted_by_priority = sorted(
            similarities.items(),
            key=lambda x: (self.intent_priorities.get(x[0], 0), x[1]),
            reverse=True
        )
        
        return sorted_by_priority[0][0]
    
    def _create_classification_result(self, 
                                    intent: str, 
                                    confidence: float, 
                                    confidence_level: str,
                                    all_similarities: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Create standardized classification result"""
        result = {
            "intent": intent,
            "confidence": confidence,
            "confidence_level": confidence_level,
            "priority": self.intent_priorities.get(intent, 1),
            "timestamp": datetime.now().isoformat()
        }
        
        if all_similarities:
            # Add top 3 alternative intents
            sorted_similarities = sorted(all_similarities.items(), key=lambda x: x[1], reverse=True)
            result["alternatives"] = [
                {"intent": intent, "confidence": conf} 
                for intent, conf in sorted_similarities[1:4]  # Skip the top one (already selected)
            ]
        
        return result
    
    def _generate_retrieval_metadata(self, intent: str, confidence: float, confidence_level: str) -> Dict[str, Any]:
        """Generate retrieval strategy metadata based on intent classification"""
        
        # Intent-specific retrieval strategies using configuration
        retrieval_strategies = {
            "menu_inquiry": {
                "chunk_size": self.config.retrieval_specialized_chunk_size,
                "retrieval_strategy": "factual_lookup",
                "context_window": "small"
            },
            "price_inquiry": {
                "chunk_size": 150,  # Very precise for price information
                "retrieval_strategy": "factual_lookup", 
                "context_window": "small"
            },
            "ingredient_inquiry": {
                "chunk_size": 180,  # Small chunks for ingredient details
                "retrieval_strategy": "factual_lookup",
                "context_window": "small"
            },
            "order_placement": {
                "chunk_size": self.config.retrieval_hybrid_chunk_size,
                "retrieval_strategy": "procedural",
                "context_window": "medium"
            },
            "order_modification": {
                "chunk_size": self.config.retrieval_hybrid_chunk_size,
                "retrieval_strategy": "procedural",
                "context_window": "medium"
            },
            "dietary_inquiry": {
                "chunk_size": 400,  # Larger context for comparative analysis
                "retrieval_strategy": "comparative_analysis",
                "context_window": "large"
            },
            "general_assistance": {
                "chunk_size": 350,  # Hierarchical retrieval for conceptual explanations
                "retrieval_strategy": "conceptual_explanation",
                "context_window": "large"
            }
        }
        
        # Get strategy for this intent or use default
        strategy = retrieval_strategies.get(intent, retrieval_strategies["general_assistance"])
        
        # Get retrieval weight from configuration based on confidence level
        retrieval_weights = self.config.get_retrieval_weights()
        weight = retrieval_weights.get(confidence_level, retrieval_weights["medium"])
        
        # Determine retrieval approach based on confidence
        if confidence_level in ["high", "medium"]:
            approach = "confidence_based"
        else:
            approach = "exploratory"
        
        return {
            "intent": intent,
            "confidence": confidence,
            "confidence_level": confidence_level,
            "retrieval_approach": approach,
            "chunk_size": strategy["chunk_size"],
            "retrieval_strategy": strategy["retrieval_strategy"],
            "rerank_weight": weight,
            "context_window": strategy["context_window"],
            "supports_expansion": confidence > 0.6,  # Enable query expansion for confident classifications
            "supports_step_back": intent in ["dietary_inquiry", "general_assistance"] and confidence > 0.5
        }
    
    def _update_stats(self, start_time: datetime):
        """Update classification statistics"""
        self.stats["total_classifications"] += 1
        classification_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Update average classification time
        total_time = (self.stats["average_classification_time"] * 
                     (self.stats["total_classifications"] - 1) + classification_time)
        self.stats["average_classification_time"] = (
            total_time / self.stats["total_classifications"]
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get classification statistics"""
        stats = self.stats.copy()
        
        total = stats["total_classifications"]
        if total > 0:
            stats["high_confidence_rate"] = stats["high_confidence_count"] / total
            stats["medium_confidence_rate"] = stats["medium_confidence_count"] / total
            stats["low_confidence_rate"] = stats["low_confidence_count"] / total
            stats["fallback_rate"] = stats["fallback_count"] / total
        
        stats["total_intents"] = len(self.intent_examples)
        stats["model_name"] = self.config.intent_model_name
        stats["configuration"] = self.config.get_confidence_thresholds()
        
        return stats
    
    def batch_classify(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Classify multiple texts efficiently"""
        if not texts:
            return []
        
        start_time = datetime.now()
        results = []
        
        try:
            for text in texts:
                result = self.classify_intent(text, return_confidence=False)
                results.append(result)
            
            batch_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"Batch classified {len(texts)} texts in {batch_time:.2f}ms ({batch_time/len(texts):.2f}ms per text)")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch classification: {e}")
            return [self._create_classification_result("general_assistance", 0.0, "error") for _ in texts]


class IntentClassifierManager:
    """
    Manager class for Intent Classifier with dependency injection
    Replaces global singleton pattern
    """
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or get_rag_config()
        self._classifier: Optional[RefactoredIntentClassifier] = None
    
    def get_classifier(self) -> RefactoredIntentClassifier:
        """Get or create intent classifier instance"""
        if self._classifier is None:
            self._classifier = RefactoredIntentClassifier(self.config)
        return self._classifier
    
    def reload_classifier(self):
        """Reload classifier with fresh configuration"""
        self.config = get_rag_config()
        self._classifier = None
        logger.info("Intent classifier reloaded")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get classifier statistics"""
        if self._classifier:
            return self._classifier.get_statistics()
        else:
            return {"status": "not_initialized"}


# Factory functions for easy access
def create_intent_classifier(config: Optional[RAGConfig] = None) -> RefactoredIntentClassifier:
    """Factory function to create intent classifier"""
    return RefactoredIntentClassifier(config)


def create_intent_manager(config: Optional[RAGConfig] = None) -> IntentClassifierManager:
    """Factory function to create intent classifier manager"""
    return IntentClassifierManager(config)


if __name__ == "__main__":
    # Test the refactored intent classifier
    print("Testing Refactored Intent Classifier:")
    print("=" * 50)
    
    # Create classifier manager
    manager = create_intent_manager()
    classifier = manager.get_classifier()
    
    # Test classification
    test_cases = [
        "I want to order pizza",
        "what vegetarian options do you have",
        "how much does the burger cost",
        "does this contain nuts"
    ]
    
    for text in test_cases:
        result = classifier.classify_intent(text, include_retrieval_metadata=True)
        print(f"Text: '{text}'")
        print(f"Intent: {result['intent']} (confidence: {result['confidence']:.3f})")
        print(f"Level: {result['confidence_level']}")
        print("-" * 30)
    
    # Show statistics
    stats = manager.get_stats()
    print(f"\\nTotal classifications: {stats.get('total_classifications', 0)}")
    print(f"Average time: {stats.get('average_classification_time', 0):.2f}ms")