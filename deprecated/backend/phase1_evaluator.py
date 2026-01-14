"""
Evaluation Harness for Phase 1 Advanced RAG Implementation
Tests and benchmarks the enhanced query understanding and retrieval system
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

from loguru import logger
from semantic_intent_classifier import get_intent_classifier
from query_expansion import get_query_expander
from rag_pipeline import get_rag_pipeline
import pandas as pd


@dataclass
class EvaluationResult:
    """Results from a single evaluation run"""
    query: str
    intent_result: Dict[str, Any]
    expansion_result: Optional[Dict[str, Any]]
    retrieval_results: List[Dict[str, Any]]
    context_generated: str
    response_time_ms: float
    retrieval_strategy: str
    success: bool
    error: Optional[str] = None


@dataclass
class EvaluationMetrics:
    """Aggregated evaluation metrics"""
    total_queries: int
    success_rate: float
    avg_response_time_ms: float
    intent_accuracy: float
    retrieval_coverage: float
    strategy_distribution: Dict[str, int]
    confidence_distribution: Dict[str, int]


class Phase1Evaluator:
    """Evaluation harness for Phase 1 implementation"""
    
    def __init__(self):
        self.intent_classifier = None
        self.query_expander = None
        self.rag_pipeline = None
        self.evaluation_data = []
        
        # Test queries organized by intent
        self.test_queries = {
            "menu_inquiry": [
                "what vegetarian options do you have",
                "show me the pizza menu",
                "what salads are available",
                "tell me about your breakfast options",
                "what beverages do you offer"
            ],
            "price_inquiry": [
                "how much does the pizza cost",
                "what's the price of the burger",
                "how expensive is the wine",
                "what does the salad cost",
                "pricing for appetizers"
            ],
            "ingredient_inquiry": [
                "does the pizza contain gluten",
                "what's in the veggie burger",
                "are there nuts in the salad",
                "is the soup vegan",
                "what ingredients are in the sandwich"
            ],
            "dietary_inquiry": [
                "what gluten-free options are available",
                "do you have vegan dishes",
                "what about low-calorie meals",
                "any keto-friendly items",
                "vegetarian protein options"
            ],
            "order_placement": [
                "I want to order pizza",
                "get me the chicken sandwich",
                "I'll have the soup",
                "add a salad to my order",
                "order me some appetizers"
            ],
            "general_assistance": [
                "can you help me choose",
                "what do you recommend",
                "I'm not sure what to get",
                "help me decide",
                "what's popular"
            ]
        }
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all system components"""
        try:
            logger.info("Initializing evaluation components...")
            
            # Initialize components
            self.intent_classifier = get_intent_classifier()
            self.query_expander = get_query_expander()
            self.rag_pipeline = get_rag_pipeline()
            
            logger.info("All evaluation components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize evaluation components: {e}")
            raise
    
    def run_comprehensive_evaluation(self) -> EvaluationMetrics:
        """Run comprehensive evaluation across all test queries"""
        logger.info("Starting comprehensive Phase 1 evaluation...")
        
        all_results = []
        start_time = time.time()
        
        for intent, queries in self.test_queries.items():
            logger.info(f"Evaluating {intent} queries...")
            
            for query in queries:
                try:
                    result = self._evaluate_single_query(query, expected_intent=intent)
                    all_results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error evaluating query '{query}': {e}")
                    all_results.append(EvaluationResult(
                        query=query,
                        intent_result={},
                        expansion_result=None,
                        retrieval_results=[],
                        context_generated="",
                        response_time_ms=0.0,
                        retrieval_strategy="error",
                        success=False,
                        error=str(e)
                    ))
        
        total_time = time.time() - start_time
        logger.info(f"Comprehensive evaluation completed in {total_time:.2f}s")
        
        # Calculate metrics
        metrics = self._calculate_metrics(all_results)
        
        # Save detailed results
        self._save_evaluation_results(all_results, metrics)
        
        return metrics
    
    def _evaluate_single_query(self, query: str, expected_intent: Optional[str] = None) -> EvaluationResult:
        """Evaluate a single query through the complete pipeline"""
        start_time = time.time()
        
        try:
            # 1. Intent Classification
            intent_result = self.intent_classifier.classify_intent(
                query, 
                return_confidence=True, 
                include_retrieval_metadata=True
            )
            
            # 2. Query Expansion (if supported)
            expansion_result = None
            retrieval_metadata = intent_result.get("retrieval_metadata")
            
            if retrieval_metadata and retrieval_metadata.get("supports_expansion", False):
                expansion = self.query_expander.expand_query(query, retrieval_metadata)
                expansion_result = asdict(expansion)
            
            # 3. Enhanced Retrieval
            retrieval_results = self.rag_pipeline.retrieve_with_strategy(
                query, 
                retrieval_metadata, 
                k=5
            )
            
            # 4. Context Generation
            context = self.rag_pipeline.get_enhanced_context(
                query, 
                retrieval_metadata, 
                k=5
            )
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine success
            success = (
                len(retrieval_results) > 0 and
                len(context.strip()) > 0 and
                intent_result.get("confidence", 0) > 0.3
            )
            
            # Check intent accuracy if expected intent provided
            if expected_intent:
                predicted_intent = intent_result.get("intent", "")
                intent_accurate = predicted_intent == expected_intent
                if not intent_accurate:
                    logger.warning(f"Intent mismatch for '{query}': expected {expected_intent}, got {predicted_intent}")
            
            return EvaluationResult(
                query=query,
                intent_result=intent_result,
                expansion_result=expansion_result,
                retrieval_results=retrieval_results,
                context_generated=context,
                response_time_ms=response_time,
                retrieval_strategy=retrieval_metadata.get("retrieval_strategy", "basic") if retrieval_metadata else "basic",
                success=success
            )
            
        except Exception as e:
            logger.error(f"Error in single query evaluation: {e}")
            response_time = (time.time() - start_time) * 1000
            
            return EvaluationResult(
                query=query,
                intent_result={},
                expansion_result=None,
                retrieval_results=[],
                context_generated="",
                response_time_ms=response_time,
                retrieval_strategy="error",
                success=False,
                error=str(e)
            )
    
    def _calculate_metrics(self, results: List[EvaluationResult]) -> EvaluationMetrics:
        """Calculate aggregated evaluation metrics"""
        total_queries = len(results)
        successful_results = [r for r in results if r.success]
        
        # Success rate
        success_rate = len(successful_results) / total_queries if total_queries > 0 else 0.0
        
        # Average response time
        avg_response_time = sum(r.response_time_ms for r in results) / total_queries if total_queries > 0 else 0.0
        
        # Intent accuracy (approximate - based on non-fallback classifications)
        intent_accurate = len([r for r in results if r.intent_result.get("confidence_level") not in ["very_low", "fallback"]])
        intent_accuracy = intent_accurate / total_queries if total_queries > 0 else 0.0
        
        # Retrieval coverage (queries that got relevant results)
        retrieval_coverage = len([r for r in results if len(r.retrieval_results) > 0]) / total_queries if total_queries > 0 else 0.0
        
        # Strategy distribution
        strategy_distribution = {}
        for result in results:
            strategy = result.retrieval_strategy
            strategy_distribution[strategy] = strategy_distribution.get(strategy, 0) + 1
        
        # Confidence distribution
        confidence_distribution = {}
        for result in results:
            confidence_level = result.intent_result.get("confidence_level", "unknown")
            confidence_distribution[confidence_level] = confidence_distribution.get(confidence_level, 0) + 1
        
        return EvaluationMetrics(
            total_queries=total_queries,
            success_rate=success_rate,
            avg_response_time_ms=avg_response_time,
            intent_accuracy=intent_accuracy,
            retrieval_coverage=retrieval_coverage,
            strategy_distribution=strategy_distribution,
            confidence_distribution=confidence_distribution
        )
    
    def _save_evaluation_results(self, results: List[EvaluationResult], metrics: EvaluationMetrics):
        """Save evaluation results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = Path("evaluation_results")
        results_dir.mkdir(exist_ok=True)
        
        # Save detailed results
        detailed_results = []
        for result in results:
            detailed_results.append({
                "query": result.query,
                "intent": result.intent_result.get("intent", ""),
                "confidence": result.intent_result.get("confidence", 0.0),
                "confidence_level": result.intent_result.get("confidence_level", ""),
                "retrieval_strategy": result.retrieval_strategy,
                "num_retrieval_results": len(result.retrieval_results),
                "context_length": len(result.context_generated),
                "response_time_ms": result.response_time_ms,
                "success": result.success,
                "error": result.error,
                "expansion_used": result.expansion_result is not None
            })
        
        # Save as CSV
        df = pd.DataFrame(detailed_results)
        csv_path = results_dir / f"detailed_results_{timestamp}.csv"
        df.to_csv(csv_path, index=False)
        
        # Save metrics as JSON
        metrics_path = results_dir / f"metrics_{timestamp}.json"
        with open(metrics_path, 'w') as f:
            json.dump(asdict(metrics), f, indent=2)
        
        # Save full results as JSON for debugging
        full_results_path = results_dir / f"full_results_{timestamp}.json"
        with open(full_results_path, 'w') as f:
            json.dump([asdict(r) for r in results], f, indent=2, default=str)
        
        logger.info(f"Evaluation results saved to {results_dir}")
        logger.info(f"CSV: {csv_path}")
        logger.info(f"Metrics: {metrics_path}")
    
    def run_performance_benchmark(self, num_iterations: int = 50) -> Dict[str, float]:
        """Run performance benchmark with repeated queries"""
        logger.info(f"Running performance benchmark with {num_iterations} iterations...")
        
        # Select a representative query from each intent
        benchmark_queries = [
            "what vegetarian options do you have",
            "how much does the pizza cost", 
            "does the salad contain nuts",
            "I want to order food",
            "what do you recommend"
        ]
        
        timing_results = {}
        
        for query in benchmark_queries:
            times = []
            
            for _ in range(num_iterations):
                start_time = time.time()
                try:
                    result = self._evaluate_single_query(query)
                    end_time = time.time()
                    times.append((end_time - start_time) * 1000)  # Convert to ms
                except:
                    continue  # Skip failed iterations
            
            if times:
                timing_results[query] = {
                    "avg_ms": sum(times) / len(times),
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "p95_ms": sorted(times)[int(0.95 * len(times))]
                }
        
        logger.info("Performance benchmark completed")
        return timing_results
    
    def print_evaluation_summary(self, metrics: EvaluationMetrics):
        """Print a formatted summary of evaluation results"""
        print("\n" + "="*60)
        print("PHASE 1 ADVANCED RAG EVALUATION SUMMARY")
        print("="*60)
        
        print(f"\nOverall Performance:")
        print(f"  Total Queries: {metrics.total_queries}")
        print(f"  Success Rate: {metrics.success_rate:.1%}")
        print(f"  Average Response Time: {metrics.avg_response_time_ms:.1f}ms")
        print(f"  Intent Accuracy: {metrics.intent_accuracy:.1%}")
        print(f"  Retrieval Coverage: {metrics.retrieval_coverage:.1%}")
        
        print(f"\nRetrieval Strategy Distribution:")
        for strategy, count in metrics.strategy_distribution.items():
            percentage = count / metrics.total_queries * 100
            print(f"  {strategy}: {count} queries ({percentage:.1f}%)")
        
        print(f"\nConfidence Level Distribution:")
        for level, count in metrics.confidence_distribution.items():
            percentage = count / metrics.total_queries * 100
            print(f"  {level}: {count} queries ({percentage:.1f}%)")
        
        print("\n" + "="*60)


def run_phase1_evaluation():
    """Main function to run Phase 1 evaluation"""
    evaluator = Phase1Evaluator()
    
    # Run comprehensive evaluation
    metrics = evaluator.run_comprehensive_evaluation()
    
    # Print summary
    evaluator.print_evaluation_summary(metrics)
    
    # Run performance benchmark
    logger.info("\nRunning performance benchmark...")
    perf_results = evaluator.run_performance_benchmark(num_iterations=10)
    
    print(f"\nPerformance Benchmark Results:")
    for query, timings in perf_results.items():
        print(f"  '{query[:30]}...': {timings['avg_ms']:.1f}ms avg (p95: {timings['p95_ms']:.1f}ms)")
    
    return metrics, perf_results


if __name__ == "__main__":
    run_phase1_evaluation()