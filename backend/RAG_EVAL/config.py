"""
RAG Evaluation Configuration Module
Production-focused configuration for RAG pipeline evaluation
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
import json
from loguru import logger

@dataclass
class EvaluationConfig:
    """Configuration for RAG evaluation runs"""
    
    # Core settings
    pipeline_path: str = "../rag_pipeline.py"
    menu_data_path: str = "../RAG_DOCS/menu-items.csv"
    chroma_db_path: str = "../chroma_db"
    
    # Evaluation parameters
    retrieval_k: int = 3
    batch_size: int = 10
    max_workers: int = 4
    
    # Production metrics thresholds
    min_faithfulness_score: float = 0.7
    min_relevancy_score: float = 0.75
    min_precision_at_3: float = 0.8
    min_recall_at_5: float = 0.7
    max_latency_ms: int = 500
    
    # Test configuration
    run_basic_tests: bool = True
    run_edge_cases: bool = True
    run_stress_tests: bool = True
    run_performance_tests: bool = True
    
    # Output settings
    output_dir: str = "./evaluation_results"
    save_detailed_results: bool = True
    generate_report: bool = True
    
    # Model configuration
    mistral_api_key: Optional[str] = field(default_factory=lambda: os.getenv("MISTRAL_API_KEY"))
    model_name: str = "mistral-medium"
    temperature: float = 0.1
    max_tokens: int = 500
    
    # Performance monitoring
    track_memory_usage: bool = True
    track_response_time: bool = True
    track_token_usage: bool = True
    
    # Failure handling
    retry_on_failure: bool = True
    max_retries: int = 3
    retry_delay_seconds: int = 2
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            k: v for k, v in self.__dict__.items() 
            if not k.startswith('_') and v is not None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvaluationConfig':
        """Create config from dictionary"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_path: str) -> 'EvaluationConfig':
        """Load config from JSON file"""
        with open(json_path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def save_json(self, json_path: str):
        """Save config to JSON file"""
        with open(json_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def validate(self) -> List[str]:
        """Validate configuration settings"""
        errors = []
        
        # Check paths exist
        if not Path(self.menu_data_path).exists():
            errors.append(f"Menu data path not found: {self.menu_data_path}")
        
        # Check API key
        if not self.mistral_api_key:
            errors.append("MISTRAL_API_KEY not set")
        
        # Check thresholds
        if not 0 <= self.min_faithfulness_score <= 1:
            errors.append("min_faithfulness_score must be between 0 and 1")
        
        if not 0 <= self.min_relevancy_score <= 1:
            errors.append("min_relevancy_score must be between 0 and 1")
        
        if self.batch_size <= 0:
            errors.append("batch_size must be positive")
        
        if self.max_workers <= 0:
            errors.append("max_workers must be positive")
        
        return errors

@dataclass
class ProductionMetrics:
    """Production-critical metrics configuration"""
    
    # Response quality metrics
    faithfulness_weight: float = 0.3
    relevancy_weight: float = 0.3
    precision_weight: float = 0.2
    recall_weight: float = 0.2
    
    # Performance metrics
    latency_p50_threshold_ms: int = 200
    latency_p95_threshold_ms: int = 500
    latency_p99_threshold_ms: int = 1000
    
    # Error rate thresholds
    max_error_rate: float = 0.01  # 1%
    max_timeout_rate: float = 0.005  # 0.5%
    
    # Token usage limits
    avg_tokens_per_query: int = 150
    max_tokens_per_query: int = 500
    
    # Cache performance
    min_cache_hit_rate: float = 0.6
    
    def calculate_composite_score(self, metrics: Dict[str, float]) -> float:
        """Calculate weighted composite score"""
        score = 0.0
        score += metrics.get('faithfulness', 0) * self.faithfulness_weight
        score += metrics.get('relevancy', 0) * self.relevancy_weight
        score += metrics.get('precision', 0) * self.precision_weight
        score += metrics.get('recall', 0) * self.recall_weight
        return score
    
    def is_production_ready(self, metrics: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Check if metrics meet production standards"""
        issues = []
        
        # Check quality metrics
        if metrics.get('faithfulness', 0) < 0.7:
            issues.append(f"Faithfulness below threshold: {metrics.get('faithfulness', 0):.2f} < 0.7")
        
        if metrics.get('relevancy', 0) < 0.75:
            issues.append(f"Relevancy below threshold: {metrics.get('relevancy', 0):.2f} < 0.75")
        
        # Check performance metrics
        if metrics.get('latency_p95', float('inf')) > self.latency_p95_threshold_ms:
            issues.append(f"P95 latency too high: {metrics.get('latency_p95', 0)}ms")
        
        if metrics.get('error_rate', 1.0) > self.max_error_rate:
            issues.append(f"Error rate too high: {metrics.get('error_rate', 0):.2%}")
        
        return len(issues) == 0, issues

class TestScenarios:
    """Define production test scenarios"""
    
    @staticmethod
    def get_production_scenarios() -> Dict[str, Dict[str, Any]]:
        """Get production-critical test scenarios"""
        return {
            'high_traffic': {
                'description': 'Simulate high concurrent requests',
                'concurrent_requests': 50,
                'duration_seconds': 60,
                'expected_success_rate': 0.99
            },
            'cache_warmup': {
                'description': 'Test with cold vs warm cache',
                'queries_per_test': 100,
                'measure_cache_impact': True
            },
            'edge_cases': {
                'description': 'Handle malformed and edge case inputs',
                'include_empty_queries': True,
                'include_special_chars': True,
                'include_long_queries': True,
                'expected_graceful_handling': True
            },
            'multilingual': {
                'description': 'Test non-English queries',
                'languages': ['es', 'fr', 'de'],
                'expected_fallback_behavior': True
            },
            'resource_limits': {
                'description': 'Test under resource constraints',
                'memory_limit_mb': 512,
                'cpu_limit_percent': 50,
                'expected_degradation': 'graceful'
            }
        }
    
    @staticmethod
    def get_critical_queries() -> List[Dict[str, str]]:
        """Get queries that must work in production"""
        return [
            {
                'query': 'What vegetarian options do you have?',
                'category': 'dietary_restriction',
                'priority': 'critical'
            },
            {
                'query': 'Show me items under $15',
                'category': 'price_filter',
                'priority': 'critical'
            },
            {
                'query': 'What breakfast items are available?',
                'category': 'category_search',
                'priority': 'critical'
            },
            {
                'query': 'Does the chicken sandwich contain nuts?',
                'category': 'allergen_check',
                'priority': 'critical'
            },
            {
                'query': 'What\'s the price of the Caesar Salad?',
                'category': 'price_inquiry',
                'priority': 'high'
            }
        ]

def load_production_config() -> EvaluationConfig:
    """Load production evaluation configuration"""
    config = EvaluationConfig()
    
    # Override with environment variables if present
    if os.getenv('RAG_EVAL_CONFIG'):
        config_path = os.getenv('RAG_EVAL_CONFIG')
        if Path(config_path).exists():
            config = EvaluationConfig.from_json(config_path)
            logger.info(f"Loaded config from {config_path}")
    
    # Validate configuration
    errors = config.validate()
    if errors:
        logger.warning(f"Configuration validation warnings: {errors}")
    
    return config

def get_production_metrics() -> ProductionMetrics:
    """Get production metrics configuration"""
    return ProductionMetrics()