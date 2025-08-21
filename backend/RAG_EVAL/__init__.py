"""
RAG Evaluation Suite for Hotel Menu System
Complete modular evaluation framework for testing RAG pipeline performance
"""

from .rag_evaluator import RAGEvaluator
from .metrics import RAGMetrics
from .test_data import TestDataGenerator
from .edge_case_tests import EdgeCaseTestSuite
from .performance_monitor import PerformanceMonitor

__version__ = "1.0.0"
__all__ = [
    "RAGEvaluator",
    "RAGMetrics", 
    "TestDataGenerator",
    "EdgeCaseTestSuite",
    "PerformanceMonitor"
]