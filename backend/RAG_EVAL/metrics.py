"""
Comprehensive RAG Metrics Module
Implements all standard and custom metrics for hotel menu RAG evaluation
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
import re
import json
from collections import Counter
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer
import asyncio
from loguru import logger

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

@dataclass
class EvaluationResult:
    """Container for evaluation results"""
    metric_name: str
    score: float
    details: Dict[str, Any]
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class RAGTestCase:
    """Test case for RAG evaluation"""
    query: str
    retrieved_contexts: List[str]
    generated_answer: str
    ground_truth: Optional[str] = None
    expected_contexts: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class BaseMetric(ABC):
    """Abstract base class for all RAG metrics"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def compute(self, test_case: RAGTestCase) -> EvaluationResult:
        """Compute metric for a single test case"""
        pass
    
    @abstractmethod
    def aggregate(self, results: List[EvaluationResult]) -> EvaluationResult:
        """Aggregate results across multiple test cases"""
        pass

class RetrievalMetrics:
    """Metrics for evaluating retrieval quality"""
    
    @staticmethod
    def precision_at_k(retrieved_docs: List[str], relevant_docs: List[str], k: int) -> float:
        """Calculate Precision@K"""
        if not retrieved_docs or k <= 0:
            return 0.0
        
        retrieved_k = retrieved_docs[:k]
        relevant_retrieved = sum(1 for doc in retrieved_k if doc in relevant_docs)
        return relevant_retrieved / min(k, len(retrieved_k))
    
    @staticmethod
    def recall_at_k(retrieved_docs: List[str], relevant_docs: List[str], k: int) -> float:
        """Calculate Recall@K"""
        if not relevant_docs or k <= 0:
            return 0.0
        
        retrieved_k = retrieved_docs[:k]
        relevant_retrieved = sum(1 for doc in retrieved_k if doc in relevant_docs)
        return relevant_retrieved / len(relevant_docs)
    
    @staticmethod
    def f1_at_k(retrieved_docs: List[str], relevant_docs: List[str], k: int) -> float:
        """Calculate F1@K"""
        precision = RetrievalMetrics.precision_at_k(retrieved_docs, relevant_docs, k)
        recall = RetrievalMetrics.recall_at_k(retrieved_docs, relevant_docs, k)
        
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)
    
    @staticmethod
    def mean_reciprocal_rank(retrieved_docs: List[str], relevant_docs: List[str]) -> float:
        """Calculate Mean Reciprocal Rank"""
        for i, doc in enumerate(retrieved_docs):
            if doc in relevant_docs:
                return 1.0 / (i + 1)
        return 0.0
    
    @staticmethod
    def normalized_dcg_at_k(retrieved_docs: List[str], relevant_docs: List[str], k: int) -> float:
        """Calculate Normalized Discounted Cumulative Gain@K"""
        if not relevant_docs or k <= 0:
            return 0.0
        
        # Calculate DCG
        dcg = 0.0
        for i, doc in enumerate(retrieved_docs[:k]):
            relevance = 1 if doc in relevant_docs else 0
            dcg += relevance / np.log2(i + 2)
        
        # Calculate IDCG (ideal DCG)
        ideal_order = [1] * min(len(relevant_docs), k) + [0] * max(0, k - len(relevant_docs))
        idcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(ideal_order))
        
        return dcg / idcg if idcg > 0 else 0.0

class GenerationMetrics:
    """Metrics for evaluating generation quality"""
    
    def __init__(self):
        self.sentence_model = None
        self.rouge_scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    
    def _get_sentence_model(self):
        """Lazy load sentence transformer model"""
        if self.sentence_model is None:
            try:
                self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                logger.warning(f"Could not load sentence transformer: {e}")
                self.sentence_model = None
        return self.sentence_model
    
    def semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity using sentence embeddings"""
        model = self._get_sentence_model()
        if model is None:
            return self._simple_similarity(text1, text2)
        
        try:
            embeddings = model.encode([text1, text2])
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity)
        except Exception as e:
            logger.warning(f"Semantic similarity calculation failed: {e}")
            return self._simple_similarity(text1, text2)
    
    def _simple_similarity(self, text1: str, text2: str) -> float:
        """Simple word overlap similarity as fallback"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        return len(words1.intersection(words2)) / len(words1.union(words2))
    
    def bleu_score(self, generated: str, reference: str) -> float:
        """Calculate BLEU score"""
        try:
            generated_tokens = generated.lower().split()
            reference_tokens = [reference.lower().split()]
            
            smoothing = SmoothingFunction().method1
            score = sentence_bleu(reference_tokens, generated_tokens, smoothing_function=smoothing)
            return float(score)
        except Exception as e:
            logger.warning(f"BLEU score calculation failed: {e}")
            return 0.0
    
    def rouge_scores(self, generated: str, reference: str) -> Dict[str, float]:
        """Calculate ROUGE scores"""
        try:
            scores = self.rouge_scorer.score(reference, generated)
            return {
                'rouge1': scores['rouge1'].fmeasure,
                'rouge2': scores['rouge2'].fmeasure,
                'rougeL': scores['rougeL'].fmeasure
            }
        except Exception as e:
            logger.warning(f"ROUGE score calculation failed: {e}")
            return {'rouge1': 0.0, 'rouge2': 0.0, 'rougeL': 0.0}

class FaithfulnessMetric(BaseMetric):
    """Measures if generated answer is faithful to retrieved context"""
    
    def __init__(self):
        super().__init__("faithfulness")
        self.generation_metrics = GenerationMetrics()
    
    def compute(self, test_case: RAGTestCase) -> EvaluationResult:
        """Compute faithfulness score"""
        if not test_case.retrieved_contexts or not test_case.generated_answer:
            return EvaluationResult(
                metric_name=self.name,
                score=0.0,
                details={"error": "Missing contexts or answer"},
                timestamp=pd.Timestamp.now().isoformat()
            )
        
        # Extract claims from generated answer
        answer_claims = self._extract_claims(test_case.generated_answer)
        if not answer_claims:
            return EvaluationResult(
                metric_name=self.name,
                score=1.0,  # No claims to verify
                details={"claims_count": 0, "verified_claims": 0},
                timestamp=pd.Timestamp.now().isoformat()
            )
        
        # Check each claim against contexts
        verified_claims = 0
        context_text = " ".join(test_case.retrieved_contexts)
        
        for claim in answer_claims:
            if self._verify_claim(claim, context_text):
                verified_claims += 1
        
        score = verified_claims / len(answer_claims)
        
        return EvaluationResult(
            metric_name=self.name,
            score=score,
            details={
                "claims_count": len(answer_claims),
                "verified_claims": verified_claims,
                "claims": answer_claims
            },
            timestamp=pd.Timestamp.now().isoformat()
        )
    
    def _extract_claims(self, text: str) -> List[str]:
        """Extract factual claims from text"""
        # Split by sentences and filter out questions/greetings
        sentences = re.split(r'[.!?]+', text)
        claims = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and not sentence.endswith('?') and len(sentence) > 10:
                # Filter out greetings and meta-statements
                if not any(phrase in sentence.lower() for phrase in [
                    'hello', 'hi there', 'how can i help', 'welcome', 'thank you',
                    'i am', 'i can help', 'let me know', 'please feel free'
                ]):
                    claims.append(sentence)
        
        return claims
    
    def _verify_claim(self, claim: str, context: str) -> bool:
        """Verify if a claim is supported by context"""
        # Simple keyword-based verification
        claim_words = set(claim.lower().split())
        context_words = set(context.lower().split())
        
        # Check for factual elements (prices, names, descriptions)
        factual_overlap = len(claim_words.intersection(context_words))
        return factual_overlap / len(claim_words) > 0.3  # 30% word overlap threshold
    
    def aggregate(self, results: List[EvaluationResult]) -> EvaluationResult:
        """Aggregate faithfulness scores"""
        if not results:
            return EvaluationResult(
                metric_name=f"{self.name}_aggregated",
                score=0.0,
                details={"count": 0},
                timestamp=pd.Timestamp.now().isoformat()
            )
        
        scores = [r.score for r in results]
        return EvaluationResult(
            metric_name=f"{self.name}_aggregated",
            score=np.mean(scores),
            details={
                "count": len(scores),
                "mean": np.mean(scores),
                "std": np.std(scores),
                "min": np.min(scores),
                "max": np.max(scores)
            },
            timestamp=pd.Timestamp.now().isoformat()
        )

class AnswerRelevancyMetric(BaseMetric):
    """Measures how relevant the answer is to the query"""
    
    def __init__(self):
        super().__init__("answer_relevancy")
        self.generation_metrics = GenerationMetrics()
    
    def compute(self, test_case: RAGTestCase) -> EvaluationResult:
        """Compute answer relevancy score"""
        if not test_case.query or not test_case.generated_answer:
            return EvaluationResult(
                metric_name=self.name,
                score=0.0,
                details={"error": "Missing query or answer"},
                timestamp=pd.Timestamp.now().isoformat()
            )
        
        # Calculate semantic similarity between query and answer
        similarity = self.generation_metrics.semantic_similarity(
            test_case.query, test_case.generated_answer
        )
        
        # Check for direct relevance indicators
        relevance_boost = self._calculate_relevance_boost(
            test_case.query, test_case.generated_answer
        )
        
        # Combine scores
        score = min(1.0, similarity + relevance_boost)
        
        return EvaluationResult(
            metric_name=self.name,
            score=score,
            details={
                "semantic_similarity": similarity,
                "relevance_boost": relevance_boost,
                "query_length": len(test_case.query.split()),
                "answer_length": len(test_case.generated_answer.split())
            },
            timestamp=pd.Timestamp.now().isoformat()
        )
    
    def _calculate_relevance_boost(self, query: str, answer: str) -> float:
        """Calculate relevance boost based on query-answer alignment"""
        query_lower = query.lower()
        answer_lower = answer.lower()
        
        boost = 0.0
        
        # Check for direct question answering
        if '?' in query and any(word in answer_lower for word in ['yes', 'no', 'available', 'costs', 'includes']):
            boost += 0.1
        
        # Check for menu-specific terms
        menu_terms = ['menu', 'dish', 'price', 'ingredient', 'calorie', 'vegetarian', 'available']
        if any(term in query_lower for term in menu_terms):
            if any(term in answer_lower for term in menu_terms):
                boost += 0.1
        
        return min(0.3, boost)  # Cap boost at 0.3
    
    def aggregate(self, results: List[EvaluationResult]) -> EvaluationResult:
        """Aggregate relevancy scores"""
        if not results:
            return EvaluationResult(
                metric_name=f"{self.name}_aggregated",
                score=0.0,
                details={"count": 0},
                timestamp=pd.Timestamp.now().isoformat()
            )
        
        scores = [r.score for r in results]
        return EvaluationResult(
            metric_name=f"{self.name}_aggregated",
            score=np.mean(scores),
            details={
                "count": len(scores),
                "mean": np.mean(scores),
                "std": np.std(scores),
                "min": np.min(scores),
                "max": np.max(scores)
            },
            timestamp=pd.Timestamp.now().isoformat()
        )

class ContextualPrecisionMetric(BaseMetric):
    """Measures precision of retrieved context"""
    
    def __init__(self):
        super().__init__("contextual_precision")
    
    def compute(self, test_case: RAGTestCase) -> EvaluationResult:
        """Compute contextual precision"""
        if not test_case.retrieved_contexts or not test_case.expected_contexts:
            return EvaluationResult(
                metric_name=self.name,
                score=0.0,
                details={"error": "Missing retrieved or expected contexts"},
                timestamp=pd.Timestamp.now().isoformat()
            )
        
        # Calculate precision at different k values
        k_values = [1, 3, 5, len(test_case.retrieved_contexts)]
        precision_scores = {}
        
        for k in k_values:
            if k <= len(test_case.retrieved_contexts):
                precision = RetrievalMetrics.precision_at_k(
                    test_case.retrieved_contexts, 
                    test_case.expected_contexts, 
                    k
                )
                precision_scores[f"precision@{k}"] = precision
        
        # Use precision@3 as main score
        main_score = precision_scores.get("precision@3", 0.0)
        
        return EvaluationResult(
            metric_name=self.name,
            score=main_score,
            details=precision_scores,
            timestamp=pd.Timestamp.now().isoformat()
        )
    
    def aggregate(self, results: List[EvaluationResult]) -> EvaluationResult:
        """Aggregate precision scores"""
        if not results:
            return EvaluationResult(
                metric_name=f"{self.name}_aggregated",
                score=0.0,
                details={"count": 0},
                timestamp=pd.Timestamp.now().isoformat()
            )
        
        scores = [r.score for r in results]
        all_details = {}
        
        # Aggregate all precision@k scores
        for result in results:
            for key, value in result.details.items():
                if key not in all_details:
                    all_details[key] = []
                all_details[key].append(value)
        
        aggregated_details = {
            key: np.mean(values) for key, values in all_details.items()
        }
        aggregated_details["count"] = len(scores)
        
        return EvaluationResult(
            metric_name=f"{self.name}_aggregated",
            score=np.mean(scores),
            details=aggregated_details,
            timestamp=pd.Timestamp.now().isoformat()
        )

class ContextualRecallMetric(BaseMetric):
    """Measures recall of retrieved context"""
    
    def __init__(self):
        super().__init__("contextual_recall")
    
    def compute(self, test_case: RAGTestCase) -> EvaluationResult:
        """Compute contextual recall"""
        if not test_case.retrieved_contexts or not test_case.expected_contexts:
            return EvaluationResult(
                metric_name=self.name,
                score=0.0,
                details={"error": "Missing retrieved or expected contexts"},
                timestamp=pd.Timestamp.now().isoformat()
            )
        
        # Calculate recall at different k values
        k_values = [1, 3, 5, len(test_case.retrieved_contexts)]
        recall_scores = {}
        
        for k in k_values:
            if k <= len(test_case.retrieved_contexts):
                recall = RetrievalMetrics.recall_at_k(
                    test_case.retrieved_contexts,
                    test_case.expected_contexts,
                    k
                )
                recall_scores[f"recall@{k}"] = recall
        
        # Use recall@5 as main score
        main_score = recall_scores.get("recall@5", 0.0)
        
        return EvaluationResult(
            metric_name=self.name,
            score=main_score,
            details=recall_scores,
            timestamp=pd.Timestamp.now().isoformat()
        )
    
    def aggregate(self, results: List[EvaluationResult]) -> EvaluationResult:
        """Aggregate recall scores"""
        if not results:
            return EvaluationResult(
                metric_name=f"{self.name}_aggregated",
                score=0.0,
                details={"count": 0},
                timestamp=pd.Timestamp.now().isoformat()
            )
        
        scores = [r.score for r in results]
        all_details = {}
        
        # Aggregate all recall@k scores
        for result in results:
            for key, value in result.details.items():
                if key not in all_details:
                    all_details[key] = []
                all_details[key].append(value)
        
        aggregated_details = {
            key: np.mean(values) for key, values in all_details.items()
        }
        aggregated_details["count"] = len(scores)
        
        return EvaluationResult(
            metric_name=f"{self.name}_aggregated",
            score=np.mean(scores),
            details=aggregated_details,
            timestamp=pd.Timestamp.now().isoformat()
        )

class MenuSpecificMetrics:
    """Hotel menu specific evaluation metrics"""
    
    @staticmethod
    def price_accuracy(generated_answer: str, expected_price: str) -> float:
        """Check if price mentioned in answer matches expected price"""
        # Extract prices from generated answer
        price_pattern = r'\$?(\d+\.?\d*)'
        generated_prices = re.findall(price_pattern, generated_answer)
        
        if not generated_prices:
            return 0.0
        
        expected_price_clean = re.sub(r'[^\d.]', '', expected_price)
        
        for price in generated_prices:
            if abs(float(price) - float(expected_price_clean)) < 0.01:
                return 1.0
        
        return 0.0
    
    @staticmethod
    def category_correctness(query: str, generated_answer: str, expected_category: str) -> float:
        """Check if answer mentions correct menu category"""
        answer_lower = generated_answer.lower()
        expected_lower = expected_category.lower()
        
        # Direct mention
        if expected_lower in answer_lower:
            return 1.0
        
        # Synonym mapping
        category_synonyms = {
            'breakfast': ['morning', 'brunch'],
            'appetizer': ['starter', 'small plate'],
            'main course': ['entree', 'main dish', 'dinner'],
            'dessert': ['sweet', 'after dinner'],
            'beverage': ['drink', 'liquid']
        }
        
        synonyms = category_synonyms.get(expected_lower, [])
        if any(syn in answer_lower for syn in synonyms):
            return 0.8
        
        return 0.0
    
    @staticmethod
    def ingredient_completeness(generated_answer: str, expected_ingredients: List[str]) -> float:
        """Check how many expected ingredients are mentioned"""
        if not expected_ingredients:
            return 1.0
        
        answer_lower = generated_answer.lower()
        mentioned_ingredients = sum(1 for ing in expected_ingredients if ing.lower() in answer_lower)
        
        return mentioned_ingredients / len(expected_ingredients)

class RAGMetrics:
    """Main metrics orchestrator for RAG evaluation"""
    
    def __init__(self):
        self.metrics = {
            'faithfulness': FaithfulnessMetric(),
            'answer_relevancy': AnswerRelevancyMetric(),
            'contextual_precision': ContextualPrecisionMetric(),
            'contextual_recall': ContextualRecallMetric()
        }
        self.generation_metrics = GenerationMetrics()
    
    def evaluate_single(self, test_case: RAGTestCase, metrics_to_run: Optional[List[str]] = None) -> Dict[str, EvaluationResult]:
        """Evaluate a single test case"""
        if metrics_to_run is None:
            metrics_to_run = list(self.metrics.keys())
        
        results = {}
        
        for metric_name in metrics_to_run:
            if metric_name in self.metrics:
                try:
                    result = self.metrics[metric_name].compute(test_case)
                    results[metric_name] = result
                except Exception as e:
                    logger.error(f"Error computing {metric_name}: {e}")
                    results[metric_name] = EvaluationResult(
                        metric_name=metric_name,
                        score=0.0,
                        details={"error": str(e)},
                        timestamp=pd.Timestamp.now().isoformat()
                    )
        
        return results
    
    def evaluate_batch(self, test_cases: List[RAGTestCase], metrics_to_run: Optional[List[str]] = None) -> Dict[str, List[EvaluationResult]]:
        """Evaluate multiple test cases"""
        all_results = {metric: [] for metric in (metrics_to_run or self.metrics.keys())}
        
        for test_case in test_cases:
            single_results = self.evaluate_single(test_case, metrics_to_run)
            for metric_name, result in single_results.items():
                all_results[metric_name].append(result)
        
        return all_results
    
    def aggregate_results(self, batch_results: Dict[str, List[EvaluationResult]]) -> Dict[str, EvaluationResult]:
        """Aggregate batch evaluation results"""
        aggregated = {}
        
        for metric_name, results in batch_results.items():
            if metric_name in self.metrics:
                aggregated[metric_name] = self.metrics[metric_name].aggregate(results)
        
        return aggregated
    
    def compute_custom_metrics(self, test_case: RAGTestCase) -> Dict[str, float]:
        """Compute hotel-specific custom metrics"""
        custom_scores = {}
        
        # Add custom metrics based on metadata
        if test_case.metadata:
            expected_price = test_case.metadata.get('expected_price')
            if expected_price:
                custom_scores['price_accuracy'] = MenuSpecificMetrics.price_accuracy(
                    test_case.generated_answer, expected_price
                )
            
            expected_category = test_case.metadata.get('expected_category')
            if expected_category:
                custom_scores['category_correctness'] = MenuSpecificMetrics.category_correctness(
                    test_case.query, test_case.generated_answer, expected_category
                )
            
            expected_ingredients = test_case.metadata.get('expected_ingredients')
            if expected_ingredients:
                custom_scores['ingredient_completeness'] = MenuSpecificMetrics.ingredient_completeness(
                    test_case.generated_answer, expected_ingredients
                )
        
        return custom_scores