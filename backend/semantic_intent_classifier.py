"""
Semantic Intent Classifier for Hotel Concierge Voice AI
Replaces keyword-based intent detection with semantic similarity-based classification
Now integrated with ChromaDB for unified caching architecture
"""

import os
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from loguru import logger
from datetime import datetime
from langchain_community.vectorstores import Chroma
from langchain_mistralai import MistralAIEmbeddings

from intent_training_data import (
    get_intent_examples, 
    get_intent_descriptions, 
    get_confidence_thresholds,
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


class SemanticIntentClassifier:
    """Semantic intent classifier using ChromaDB for unified caching"""
    
    def __init__(self, 
                 model_name: str = "all-MiniLM-L6-v2",
                 chroma_dir: str = "./chroma_db"):
        self.model_name = model_name
        self.chroma_dir = Path(chroma_dir)
        
        # Use shared embedding model from environment or default
        self.model = None
        self.intent_vectorstore = None
        
        # Training data
        self.intent_examples = get_intent_examples()
        self.intent_descriptions = get_intent_descriptions()
        self.confidence_thresholds = get_confidence_thresholds()
        self.intent_priorities = get_intent_priorities()
        
        # Performance tracking
        self.classification_stats = {
            "total_classifications": 0,
            "high_confidence_count": 0,
            "medium_confidence_count": 0,
            "low_confidence_count": 0,
            "fallback_count": 0,
            "average_classification_time": 0.0
        }
        
        # Initialize the classifier with shared ChromaDB
        self._initialize_model()
        self._initialize_intent_vectorstore()
    
    def _initialize_model(self):
        """Initialize the sentence transformer model"""
        try:
            # Use model from environment or default
            model_name = os.getenv("INTENT_MODEL_PATH", self.model_name)
            self.model = SentenceTransformer(model_name)
            logger.info(f"Initialized semantic intent classifier with model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize intent classification model: {e}")
            raise
    
    def _get_shared_embeddings(self):
        """Get shared Mistral embeddings to reuse ChromaDB connection"""
        try:
            return MistralAIEmbeddings(
                api_key=os.getenv("MISTRAL_API_KEY"),
                model="mistral-embed"
            )
        except Exception as e:
            logger.warning(f"Could not initialize Mistral embeddings, using SentenceTransformer: {e}")
            # Fallback wrapper for sentence transformers
            return SentenceTransformerWrapper(self.model)
    
    def _initialize_intent_vectorstore(self):
        """Initialize or load ChromaDB vectorstore for intent embeddings"""
        try:
            embeddings = self._get_shared_embeddings()
            collection_name = "intent_embeddings"
            
            # Initialize ChromaDB with intent-specific collection
            self.intent_vectorstore = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=str(self.chroma_dir)
            )
            
            # Check if intent embeddings already exist
            existing_docs = self.intent_vectorstore._collection.count()
            
            if existing_docs == 0:
                logger.info("No existing intent embeddings found, generating new ones...")
                self._generate_and_store_intent_embeddings()
            else:
                logger.info(f"Loaded {existing_docs} existing intent embeddings from ChromaDB")
                
        except Exception as e:
            logger.error(f"Failed to initialize intent vectorstore: {e}")
            raise
    
    def _generate_and_store_intent_embeddings(self):
        """Generate and store intent embeddings in ChromaDB"""
        logger.info("Generating intent embeddings for ChromaDB storage...")
        
        documents = []
        metadatas = []
        ids = []
        
        for intent, examples in self.intent_examples.items():
            description = self.intent_descriptions.get(intent, "")
            
            # Create comprehensive texts for each intent
            for i, example in enumerate(examples):
                # Combine example with description for richer representation
                combined_text = f"{example} {description}" if description else example
                
                documents.append(combined_text)
                metadatas.append({
                    "intent": intent,
                    "example_index": i,
                    "priority": self.intent_priorities.get(intent, 1),
                    "description": description,
                    "timestamp": datetime.now().isoformat()
                })
                ids.append(f"{intent}_{i}")
        
        # Store in ChromaDB
        self.intent_vectorstore.add_texts(
            texts=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        # Persist the database
        self.intent_vectorstore.persist()
        logger.info(f"Generated and stored {len(documents)} intent embeddings in ChromaDB")
    
    def classify_intent(self, text: str, return_confidence: bool = True) -> Dict[str, Any]:
        """
        Classify intent using ChromaDB semantic similarity search
        
        Args:
            text: Input text to classify
            return_confidence: Whether to return confidence scores
            
        Returns:
            Dictionary with intent classification results
        """
        start_time = datetime.now()
        
        try:
            if not text or not text.strip():
                return self._create_classification_result("general_assistance", 0.5, "empty_input")
            
            # Search for similar intent examples using ChromaDB
            search_results = self.intent_vectorstore.similarity_search_with_score(
                query=text.strip(),
                k=10  # Get more results to analyze intent distribution
            )
            
            if not search_results:
                return self._create_classification_result("general_assistance", 0.0, "no_matches")
            
            # Aggregate scores by intent
            intent_scores = {}
            for doc, score in search_results:
                intent = doc.metadata["intent"]
                # ChromaDB returns distance, convert to similarity (higher is better)
                similarity = 1.0 / (1.0 + score) if score > 0 else 1.0
                
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
                self.classification_stats["fallback_count"] += 1
            else:
                self.classification_stats[f"{confidence_level}_confidence_count"] += 1
            
            # Update statistics
            self.classification_stats["total_classifications"] += 1
            classification_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update average classification time
            total_time = (self.classification_stats["average_classification_time"] * 
                         (self.classification_stats["total_classifications"] - 1) + classification_time)
            self.classification_stats["average_classification_time"] = (
                total_time / self.classification_stats["total_classifications"]
            )
            
            result = self._create_classification_result(
                best_intent, confidence, confidence_level, intent_confidences if return_confidence else None
            )
            
            logger.debug(f"Intent classified: '{best_intent}' (confidence: {confidence:.3f}) in {classification_time:.2f}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in intent classification: {e}")
            return self._create_classification_result("general_assistance", 0.0, "error")
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Determine confidence level from confidence score"""
        thresholds = self.confidence_thresholds
        
        if confidence >= thresholds["high_confidence"]:
            return "high"
        elif confidence >= thresholds["medium_confidence"]:
            return "medium"
        elif confidence >= thresholds["low_confidence"]:
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
    
    def batch_classify(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Classify multiple texts efficiently using ChromaDB batch operations"""
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
    
    def get_intent_info(self, intent: str) -> Dict[str, Any]:
        """Get information about a specific intent"""
        if intent not in self.intent_examples:
            return {"error": "Intent not found"}
        
        return {
            "intent": intent,
            "description": self.intent_descriptions.get(intent, ""),
            "priority": self.intent_priorities.get(intent, 1),
            "example_count": len(self.intent_examples[intent]),
            "examples": self.intent_examples[intent][:5]  # Show first 5 examples
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get classification statistics"""
        stats = self.classification_stats.copy()
        
        total = stats["total_classifications"]
        if total > 0:
            stats["high_confidence_rate"] = stats["high_confidence_count"] / total
            stats["medium_confidence_rate"] = stats["medium_confidence_count"] / total
            stats["low_confidence_rate"] = stats["low_confidence_count"] / total
            stats["fallback_rate"] = stats["fallback_count"] / total
        
        # Update to use ChromaDB count instead of intent_embeddings dict
        stats["total_intents"] = len(self.intent_examples)
        stats["model_name"] = self.model_name
        
        return stats
    
    def update_training_data(self):
        """Reload training data and regenerate embeddings in ChromaDB"""
        logger.info("Updating intent classifier with new training data...")
        
        # Reload training data
        self.intent_examples = get_intent_examples()
        self.intent_descriptions = get_intent_descriptions()
        self.intent_priorities = get_intent_priorities()
        
        # Clear existing ChromaDB collection
        try:
            self.intent_vectorstore.delete_collection()
            logger.info("Cleared existing intent embeddings from ChromaDB")
        except Exception as e:
            logger.warning(f"Could not clear existing collection: {e}")
        
        # Regenerate embeddings in ChromaDB
        self._initialize_intent_vectorstore()
        
        logger.info("Intent classifier updated successfully with ChromaDB storage")
        
        if confidence >= thresholds["high_confidence"]:
            return "high"
        elif confidence >= thresholds["medium_confidence"]:
            return "medium"
        elif confidence >= thresholds["low_confidence"]:
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
    
    def batch_classify(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Classify multiple texts efficiently"""
        if not texts:
            return []
        
        start_time = datetime.now()
        
        try:
            # Generate embeddings for all texts at once (more efficient)
            text_embeddings = self.model.encode([text.strip() for text in texts])
            
            results = []
            for i, text in enumerate(texts):
                if not text.strip():
                    results.append(self._create_classification_result("general_assistance", 0.5, "empty_input"))
                    continue
                
                text_embedding = text_embeddings[i]
                
                # Calculate similarities
                similarities = {}
                for intent, intent_embedding in self.intent_embeddings.items():
                    similarity = cosine_similarity(
                        text_embedding.reshape(1, -1),
                        intent_embedding.reshape(1, -1)
                    )[0][0]
                    similarities[intent] = similarity
                
                # Get best match
                best_intent = max(similarities, key=similarities.get)
                confidence = similarities[best_intent]
                confidence_level = self._get_confidence_level(confidence)
                
                if confidence_level == "very_low":
                    best_intent = self._get_fallback_intent(similarities)
                    confidence_level = "fallback"
                
                results.append(self._create_classification_result(best_intent, confidence, confidence_level))
            
            batch_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"Batch classified {len(texts)} texts in {batch_time:.2f}ms ({batch_time/len(texts):.2f}ms per text)")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch classification: {e}")
            return [self._create_classification_result("general_assistance", 0.0, "error") for _ in texts]
    
    def get_intent_info(self, intent: str) -> Dict[str, Any]:
        """Get information about a specific intent"""
        if intent not in self.intent_examples:
            return {"error": "Intent not found"}
        
        return {
            "intent": intent,
            "description": self.intent_descriptions.get(intent, ""),
            "priority": self.intent_priorities.get(intent, 1),
            "example_count": len(self.intent_examples[intent]),
            "examples": self.intent_examples[intent][:5]  # Show first 5 examples
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get classification statistics"""
        stats = self.classification_stats.copy()
        
        total = stats["total_classifications"]
        if total > 0:
            stats["high_confidence_rate"] = stats["high_confidence_count"] / total
            stats["medium_confidence_rate"] = stats["medium_confidence_count"] / total
            stats["low_confidence_rate"] = stats["low_confidence_count"] / total
            stats["fallback_rate"] = stats["fallback_count"] / total
        
        stats["total_intents"] = len(self.intent_embeddings)
        stats["model_name"] = self.model_name
        
        return stats
    
    def update_training_data(self):
        """Reload training data and regenerate embeddings"""
        logger.info("Updating intent classifier with new training data...")
        
        # Reload training data
        self.intent_examples = get_intent_examples()
        self.intent_descriptions = get_intent_descriptions()
        self.intent_priorities = get_intent_priorities()
        
        # Regenerate embeddings
        self._generate_intent_embeddings()
        self._cache_embeddings()
        
        logger.info("Intent classifier updated successfully")


# Global classifier instance
_intent_classifier = None

def get_intent_classifier() -> SemanticIntentClassifier:
    """Get or create the intent classifier singleton"""
    global _intent_classifier
    if _intent_classifier is None:
        _intent_classifier = SemanticIntentClassifier()
    
    return _intent_classifier


def classify_user_intent(text: str) -> Dict[str, Any]:
    """Convenience function for intent classification"""
    classifier = get_intent_classifier()
    return classifier.classify_intent(text)


def get_classification_stats() -> Dict[str, Any]:
    """Get intent classification statistics"""
    classifier = get_intent_classifier()
    return classifier.get_statistics()


# Test function for validation
def test_intent_classifier():
    """Test the intent classifier with sample inputs"""
    classifier = get_intent_classifier()
    
    test_cases = [
        "I want to order pizza",
        "what vegetarian options do you have",
        "how much does the burger cost",
        "does this contain nuts",
        "my food is cold",
        "can you help me choose"
    ]
    
    print("Testing Intent Classifier:")
    print("=" * 50)
    
    for text in test_cases:
        result = classifier.classify_intent(text)
        print(f"Text: '{text}'")
        print(f"Intent: {result['intent']} (confidence: {result['confidence']:.3f})")
        print(f"Level: {result['confidence_level']}")
        print("-" * 30)
    
    print("\nClassifier Statistics:")
    stats = classifier.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    test_intent_classifier()
