"""
RAG Evaluator - Main Orchestrator for Production RAG Evaluation
Comprehensive evaluation system focused on production requirements
"""

import asyncio
import sys
import os
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import pandas as pd
import json
from loguru import logger

# Add parent directory to path to import rag_pipeline
sys.path.append(str(Path(__file__).parent.parent))

from rag_pipeline import get_rag_pipeline, MenuRAGPipeline
from .config import EvaluationConfig, ProductionMetrics, load_production_config
from .metrics import RAGMetrics, RAGTestCase, EvaluationResult
from .test_data import TestDataGenerator
from .performance_monitor import PerformanceMonitor, LoadTester
from .edge_case_tests import EdgeCaseTestSuite

@dataclass
class EvaluationResults:
    """Container for complete evaluation results"""
    quality_metrics: Dict[str, EvaluationResult]
    performance_metrics: Dict[str, Any]
    edge_case_results: Dict[str, Any]
    production_readiness: Dict[str, Any]
    test_summary: Dict[str, Any]
    timestamp: str
    config: EvaluationConfig

class RAGEvaluator:
    """Main RAG evaluation orchestrator for production systems"""
    
    def __init__(self, config: Optional[EvaluationConfig] = None):
        self.config = config or load_production_config()
        self.rag_pipeline = None
        self.rag_metrics = RAGMetrics()
        self.performance_monitor = PerformanceMonitor()
        self.test_data_generator = None
        self.edge_case_suite = None
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize evaluation components"""
        logger.info("Initializing RAG evaluator components...")
        
        try:
            # Initialize RAG pipeline
            self.rag_pipeline = get_rag_pipeline()
            logger.info("RAG pipeline initialized successfully")
            
            # Initialize test data generator
            self.test_data_generator = TestDataGenerator(self.config.menu_data_path)
            
            # Initialize edge case test suite
            self.edge_case_suite = EdgeCaseTestSuite(self.rag_pipeline)
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    def run_quality_evaluation(self, test_cases: List[RAGTestCase]) -> Dict[str, EvaluationResult]:
        """Run comprehensive quality evaluation"""
        logger.info(f"Running quality evaluation on {len(test_cases)} test cases")
        
        # Execute queries through RAG pipeline
        for test_case in test_cases:
            try:
                with self.performance_monitor.track_request():
                    # Get retrieved contexts
                    retrieved_results = self.rag_pipeline.retrieve(test_case.query, k=self.config.retrieval_k)
                    test_case.retrieved_contexts = [result['content'] for result in retrieved_results]
                    
                    # Generate answer (simulate LLM response)
                    context = self.rag_pipeline.get_context_for_query(test_case.query, k=self.config.retrieval_k)
                    test_case.generated_answer = self._simulate_llm_response(test_case.query, context)
                    
                    # Record token usage (estimated)
                    token_count = len(test_case.generated_answer.split()) + len(context.split())
                    self.performance_monitor.record_token_usage(token_count)
                    
            except Exception as e:
                logger.error(f"Failed to process query '{test_case.query}': {e}")
                test_case.retrieved_contexts = []
                test_case.generated_answer = f"Error: {str(e)}"
        
        # Evaluate test cases
        batch_results = self.rag_metrics.evaluate_batch(test_cases)
        aggregated_results = self.rag_metrics.aggregate_results(batch_results)
        
        logger.info("Quality evaluation completed")
        return aggregated_results
    
    def run_performance_evaluation(self, test_queries: List[str]) -> Dict[str, Any]:
        """Run performance-focused evaluation"""
        logger.info("Running performance evaluation...")
        
        # Basic performance test
        self.performance_monitor.start_monitoring()
        
        for query in test_queries[:20]:  # Sample for performance testing
            with self.performance_monitor.track_request():
                try:
                    self.rag_pipeline.retrieve(query, k=self.config.retrieval_k)
                except Exception:
                    pass  # Errors already tracked by monitor
        
        self.performance_monitor.stop_monitoring()
        
        # Load testing (if configured)
        load_test_results = {}
        if self.config.run_stress_tests and len(test_queries) > 10:
            load_tester = LoadTester(
                lambda q: self.rag_pipeline.retrieve(q, k=self.config.retrieval_k),
                self.performance_monitor
            )
            
            try:
                load_test_results = asyncio.run(
                    load_tester.run_concurrent_load_test(
                        test_queries[:10], 
                        concurrent_users=5, 
                        duration_seconds=30
                    )
                )
            except Exception as e:
                logger.warning(f"Load test failed: {e}")
                load_test_results = {"error": str(e)}
        
        performance_results = self.performance_monitor.get_current_metrics()
        performance_results['load_test'] = load_test_results
        
        logger.info("Performance evaluation completed")
        return performance_results
    
    def run_edge_case_evaluation(self) -> Dict[str, Any]:
        """Run edge case evaluation"""
        logger.info("Running edge case evaluation...")
        
        edge_case_results = {
            'robustness_score': 0.0,
            'error_handling_score': 0.0,
            'graceful_degradation_score': 0.0,
            'test_results': {}
        }
        
        try:
            # Test empty/malformed queries
            empty_query_results = self.edge_case_suite.test_empty_queries()
            edge_case_results['test_results']['empty_queries'] = empty_query_results
            
            # Test error handling
            error_handling_results = self.edge_case_suite.test_error_handling()
            edge_case_results['test_results']['error_handling'] = error_handling_results
            
            # Test robustness
            robustness_results = self.edge_case_suite.test_robustness()
            edge_case_results['test_results']['robustness'] = robustness_results
            
            # Calculate aggregate scores
            edge_case_results['robustness_score'] = robustness_results.get('avg_score', 0.0)
            edge_case_results['error_handling_score'] = error_handling_results.get('avg_score', 0.0)
            edge_case_results['graceful_degradation_score'] = (
                edge_case_results['robustness_score'] + edge_case_results['error_handling_score']
            ) / 2
            
        except Exception as e:
            logger.error(f"Edge case evaluation failed: {e}")
            edge_case_results['error'] = str(e)
        
        logger.info("Edge case evaluation completed")
        return edge_case_results
    
    def assess_production_readiness(self, quality_results: Dict[str, EvaluationResult], 
                                   performance_results: Dict[str, Any]) -> Dict[str, Any]:
        """Assess if RAG system is production ready"""
        logger.info("Assessing production readiness...")
        
        production_metrics = ProductionMetrics()
        issues = []
        passed_checks = []
        
        # Check quality metrics
        faithfulness_score = quality_results.get('faithfulness_aggregated', EvaluationResult('', 0.0, {}, '')).score
        relevancy_score = quality_results.get('answer_relevancy_aggregated', EvaluationResult('', 0.0, {}, '')).score
        precision_score = quality_results.get('contextual_precision_aggregated', EvaluationResult('', 0.0, {}, '')).score
        
        if faithfulness_score < self.config.min_faithfulness_score:
            issues.append(f"Faithfulness below threshold: {faithfulness_score:.3f} < {self.config.min_faithfulness_score}")
        else:
            passed_checks.append(f"Faithfulness: {faithfulness_score:.3f}")
        
        if relevancy_score < self.config.min_relevancy_score:
            issues.append(f"Relevancy below threshold: {relevancy_score:.3f} < {self.config.min_relevancy_score}")
        else:
            passed_checks.append(f"Relevancy: {relevancy_score:.3f}")
        
        if precision_score < self.config.min_precision_at_3:
            issues.append(f"Precision@3 below threshold: {precision_score:.3f} < {self.config.min_precision_at_3}")
        else:
            passed_checks.append(f"Precision@3: {precision_score:.3f}")
        
        # Check performance metrics
        latency_data = performance_results.get('latency', {})
        p95_latency = latency_data.get('p95', 0)
        
        if p95_latency > self.config.max_latency_ms:
            issues.append(f"P95 latency too high: {p95_latency:.1f}ms > {self.config.max_latency_ms}ms")
        else:
            passed_checks.append(f"P95 latency: {p95_latency:.1f}ms")
        
        # Check error rates
        error_rates = performance_results.get('error_rates', {})
        error_rate = error_rates.get('error_rate', 0)
        
        if error_rate > production_metrics.max_error_rate:
            issues.append(f"Error rate too high: {error_rate:.2%} > {production_metrics.max_error_rate:.2%}")
        else:
            passed_checks.append(f"Error rate: {error_rate:.2%}")
        
        # Calculate composite score
        composite_score = production_metrics.calculate_composite_score({
            'faithfulness': faithfulness_score,
            'relevancy': relevancy_score,
            'precision': precision_score,
            'recall': quality_results.get('contextual_recall_aggregated', EvaluationResult('', 0.0, {}, '')).score
        })
        
        is_production_ready = len(issues) == 0 and composite_score >= 0.7
        
        readiness_assessment = {
            'is_production_ready': is_production_ready,
            'composite_score': composite_score,
            'issues': issues,
            'passed_checks': passed_checks,
            'recommendation': self._get_production_recommendation(is_production_ready, composite_score, issues)
        }
        
        logger.info(f"Production readiness: {'READY' if is_production_ready else 'NOT READY'}")
        return readiness_assessment
    
    def run_complete_evaluation(self) -> EvaluationResults:
        """Run complete evaluation suite"""
        logger.info("Starting complete RAG evaluation suite...")
        start_time = time.time()
        
        # Generate test data
        logger.info("Generating test data...")
        test_suite = self.test_data_generator.generate_complete_test_suite()
        
        # Combine all test cases for quality evaluation
        all_test_cases = []
        for category, cases in test_suite.items():
            all_test_cases.extend(cases[:10])  # Limit for efficiency
        
        # Run evaluations
        quality_results = self.run_quality_evaluation(all_test_cases)
        
        test_queries = [case.query for case in all_test_cases]
        performance_results = self.run_performance_evaluation(test_queries)
        
        edge_case_results = self.run_edge_case_evaluation()
        
        production_readiness = self.assess_production_readiness(quality_results, performance_results)
        
        # Create test summary
        test_summary = {
            'total_test_cases': len(all_test_cases),
            'test_categories': list(test_suite.keys()),
            'evaluation_duration_seconds': time.time() - start_time,
            'rag_pipeline_config': {
                'retrieval_k': self.config.retrieval_k,
                'model_name': self.config.model_name,
                'temperature': self.config.temperature
            }
        }
        
        results = EvaluationResults(
            quality_metrics=quality_results,
            performance_metrics=performance_results,
            edge_case_results=edge_case_results,
            production_readiness=production_readiness,
            test_summary=test_summary,
            timestamp=pd.Timestamp.now().isoformat(),
            config=self.config
        )
        
        logger.info(f"Complete evaluation finished in {test_summary['evaluation_duration_seconds']:.1f}s")
        return results
    
    def save_results(self, results: EvaluationResults, output_dir: Optional[str] = None):
        """Save evaluation results"""
        output_path = Path(output_dir or self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results
        results_file = output_path / f"rag_evaluation_{timestamp}.json"
        
        # Convert results to serializable format
        serializable_results = {
            'quality_metrics': {k: self._evaluation_result_to_dict(v) for k, v in results.quality_metrics.items()},
            'performance_metrics': results.performance_metrics,
            'edge_case_results': results.edge_case_results,
            'production_readiness': results.production_readiness,
            'test_summary': results.test_summary,
            'timestamp': results.timestamp,
            'config': results.config.to_dict()
        }
        
        with open(results_file, 'w') as f:
            json.dump(serializable_results, f, indent=2, default=str)
        
        logger.info(f"Detailed results saved to {results_file}")
        
        # Generate summary report
        if self.config.generate_report:
            report_file = output_path / f"rag_evaluation_report_{timestamp}.md"
            self._generate_markdown_report(results, report_file)
            logger.info(f"Summary report saved to {report_file}")
    
    def _simulate_llm_response(self, query: str, context: str) -> str:
        """Simulate LLM response for testing (replace with actual LLM call in production)"""
        # Simple simulation - extract relevant info from context
        if not context or "No relevant menu information found" in context:
            return "I don't have information about that menu item."
        
        # Extract first relevant piece of information
        lines = context.split('\n')
        relevant_lines = [line for line in lines if line.strip() and not line.startswith('Here is')]
        
        if relevant_lines:
            return f"Based on our menu, {relevant_lines[0]}"
        else:
            return "I can help you with our menu items."
    
    def _get_production_recommendation(self, is_ready: bool, score: float, issues: List[str]) -> str:
        """Generate production deployment recommendation"""
        if is_ready and score >= 0.8:
            return "DEPLOY: System meets all production requirements and shows excellent performance."
        elif is_ready:
            return "DEPLOY WITH MONITORING: System meets minimum requirements but monitor closely."
        elif score >= 0.6:
            return f"FIX ISSUES FIRST: Address {len(issues)} critical issues before deployment."
        else:
            return "SIGNIFICANT IMPROVEMENTS NEEDED: System requires major improvements before production use."
    
    def _evaluation_result_to_dict(self, result: EvaluationResult) -> Dict[str, Any]:
        """Convert EvaluationResult to dictionary"""
        return {
            'metric_name': result.metric_name,
            'score': result.score,
            'details': result.details,
            'timestamp': result.timestamp,
            'metadata': result.metadata
        }
    
    def _generate_markdown_report(self, results: EvaluationResults, output_file: Path):
        """Generate markdown evaluation report"""
        report = f"""# RAG Pipeline Evaluation Report

Generated: {results.timestamp}

## Executive Summary

**Production Readiness:** {'✅ READY' if results.production_readiness['is_production_ready'] else '❌ NOT READY'}

**Composite Score:** {results.production_readiness['composite_score']:.3f}/1.0

**Recommendation:** {results.production_readiness['recommendation']}

## Quality Metrics

"""
        
        for metric_name, result in results.quality_metrics.items():
            report += f"- **{metric_name.replace('_', ' ').title()}:** {result.score:.3f}\n"
        
        report += f"""

## Performance Metrics

"""
        
        latency = results.performance_metrics.get('latency', {})
        if latency:
            report += f"- **P50 Latency:** {latency.get('p50', 0):.1f}ms\n"
            report += f"- **P95 Latency:** {latency.get('p95', 0):.1f}ms\n"
            report += f"- **P99 Latency:** {latency.get('p99', 0):.1f}ms\n"
        
        error_rates = results.performance_metrics.get('error_rates', {})
        if error_rates:
            report += f"- **Error Rate:** {error_rates.get('error_rate', 0):.2%}\n"
            report += f"- **Success Rate:** {error_rates.get('success_rate', 0):.2%}\n"
        
        report += f"""

## Edge Cases & Robustness

- **Robustness Score:** {results.edge_case_results.get('robustness_score', 0):.3f}
- **Error Handling Score:** {results.edge_case_results.get('error_handling_score', 0):.3f}
- **Graceful Degradation:** {results.edge_case_results.get('graceful_degradation_score', 0):.3f}

## Issues Found

"""
        
        for issue in results.production_readiness['issues']:
            report += f"- ❌ {issue}\n"
        
        if not results.production_readiness['issues']:
            report += "- ✅ No critical issues found\n"
        
        report += f"""

## Passed Checks

"""
        
        for check in results.production_readiness['passed_checks']:
            report += f"- ✅ {check}\n"
        
        report += f"""

## Test Summary

- **Total Test Cases:** {results.test_summary['total_test_cases']}
- **Evaluation Duration:** {results.test_summary['evaluation_duration_seconds']:.1f}s
- **Test Categories:** {', '.join(results.test_summary['test_categories'])}

## Configuration

- **Retrieval K:** {results.test_summary['rag_pipeline_config']['retrieval_k']}
- **Model:** {results.test_summary['rag_pipeline_config']['model_name']}
- **Temperature:** {results.test_summary['rag_pipeline_config']['temperature']}

---
*Report generated by RAG Evaluation Suite*
"""
        
        with open(output_file, 'w') as f:
            f.write(report)