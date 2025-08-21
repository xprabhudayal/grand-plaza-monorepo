"""
RAG Performance Monitor
Production-focused performance monitoring and metrics collection
"""

import time
import psutil
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading
import statistics
from loguru import logger
import json
from pathlib import Path

@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""
    response_times: List[float] = field(default_factory=list)
    memory_usage: List[float] = field(default_factory=list)
    cpu_usage: List[float] = field(default_factory=list)
    token_counts: List[int] = field(default_factory=list)
    error_count: int = 0
    timeout_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_requests: int = 0
    
    def add_response_time(self, time_ms: float):
        """Add response time measurement"""
        self.response_times.append(time_ms)
        self.total_requests += 1
    
    def add_error(self):
        """Record an error"""
        self.error_count += 1
        self.total_requests += 1
    
    def add_timeout(self):
        """Record a timeout"""
        self.timeout_count += 1
        self.total_requests += 1
    
    def add_cache_hit(self):
        """Record cache hit"""
        self.cache_hits += 1
    
    def add_cache_miss(self):
        """Record cache miss"""
        self.cache_misses += 1
    
    def get_latency_percentiles(self) -> Dict[str, float]:
        """Calculate latency percentiles"""
        if not self.response_times:
            return {}
        
        sorted_times = sorted(self.response_times)
        return {
            'p50': statistics.median(sorted_times),
            'p90': sorted_times[int(0.9 * len(sorted_times))],
            'p95': sorted_times[int(0.95 * len(sorted_times))],
            'p99': sorted_times[int(0.99 * len(sorted_times))],
            'mean': statistics.mean(sorted_times),
            'min': min(sorted_times),
            'max': max(sorted_times)
        }
    
    def get_error_rates(self) -> Dict[str, float]:
        """Calculate error rates"""
        if self.total_requests == 0:
            return {'error_rate': 0.0, 'timeout_rate': 0.0}
        
        return {
            'error_rate': self.error_count / self.total_requests,
            'timeout_rate': self.timeout_count / self.total_requests,
            'success_rate': 1.0 - ((self.error_count + self.timeout_count) / self.total_requests)
        }
    
    def get_cache_stats(self) -> Dict[str, float]:
        """Calculate cache statistics"""
        total_cache_requests = self.cache_hits + self.cache_misses
        if total_cache_requests == 0:
            return {'hit_rate': 0.0, 'miss_rate': 0.0}
        
        return {
            'hit_rate': self.cache_hits / total_cache_requests,
            'miss_rate': self.cache_misses / total_cache_requests,
            'total_requests': total_cache_requests
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get complete metrics summary"""
        return {
            'latency': self.get_latency_percentiles(),
            'error_rates': self.get_error_rates(),
            'cache_stats': self.get_cache_stats(),
            'resource_usage': {
                'avg_memory_mb': statistics.mean(self.memory_usage) if self.memory_usage else 0,
                'max_memory_mb': max(self.memory_usage) if self.memory_usage else 0,
                'avg_cpu_percent': statistics.mean(self.cpu_usage) if self.cpu_usage else 0,
                'max_cpu_percent': max(self.cpu_usage) if self.cpu_usage else 0
            },
            'token_usage': {
                'total_tokens': sum(self.token_counts),
                'avg_tokens_per_request': statistics.mean(self.token_counts) if self.token_counts else 0,
                'max_tokens': max(self.token_counts) if self.token_counts else 0
            },
            'total_requests': self.total_requests
        }

class PerformanceMonitor:
    """Monitor RAG pipeline performance in production scenarios"""
    
    def __init__(self, collect_system_metrics: bool = True):
        self.metrics = PerformanceMetrics()
        self.collect_system_metrics = collect_system_metrics
        self._monitoring = False
        self._monitor_thread = None
        self._start_time = None
        
    def start_monitoring(self):
        """Start background monitoring"""
        self._monitoring = True
        self._start_time = time.time()
        
        if self.collect_system_metrics:
            self._monitor_thread = threading.Thread(target=self._system_monitor, daemon=True)
            self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)
    
    def _system_monitor(self):
        """Background system monitoring"""
        while self._monitoring:
            try:
                # Collect memory usage
                memory_mb = psutil.virtual_memory().used / 1024 / 1024
                self.metrics.memory_usage.append(memory_mb)
                
                # Collect CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.metrics.cpu_usage.append(cpu_percent)
                
            except Exception as e:
                logger.warning(f"System monitoring error: {e}")
            
            time.sleep(1)
    
    @contextmanager
    def track_request(self):
        """Context manager to track individual request performance"""
        start_time = time.perf_counter()
        try:
            yield
            # Success - record response time
            response_time_ms = (time.perf_counter() - start_time) * 1000
            self.metrics.add_response_time(response_time_ms)
            
        except TimeoutError:
            self.metrics.add_timeout()
            raise
        except Exception:
            self.metrics.add_error()
            raise
    
    def record_token_usage(self, token_count: int):
        """Record token usage for a request"""
        self.metrics.token_counts.append(token_count)
    
    def record_cache_hit(self):
        """Record cache hit"""
        self.metrics.add_cache_hit()
    
    def record_cache_miss(self):
        """Record cache miss"""
        self.metrics.add_cache_miss()
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        summary = self.metrics.get_summary()
        
        if self._start_time:
            summary['monitoring_duration_seconds'] = time.time() - self._start_time
        
        return summary
    
    def save_metrics(self, output_path: str):
        """Save metrics to file"""
        metrics_data = self.get_current_metrics()
        with open(output_path, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        logger.info(f"Saved performance metrics to {output_path}")
    
    def check_production_thresholds(self, thresholds: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Check if current metrics meet production thresholds"""
        issues = []
        current = self.get_current_metrics()
        
        # Check latency thresholds
        latency = current.get('latency', {})
        if latency.get('p95', 0) > thresholds.get('max_p95_latency_ms', 500):
            issues.append(f"P95 latency too high: {latency.get('p95', 0):.1f}ms")
        
        if latency.get('p99', 0) > thresholds.get('max_p99_latency_ms', 1000):
            issues.append(f"P99 latency too high: {latency.get('p99', 0):.1f}ms")
        
        # Check error rates
        error_rates = current.get('error_rates', {})
        if error_rates.get('error_rate', 0) > thresholds.get('max_error_rate', 0.01):
            issues.append(f"Error rate too high: {error_rates.get('error_rate', 0):.2%}")
        
        # Check resource usage
        resource_usage = current.get('resource_usage', {})
        if resource_usage.get('max_memory_mb', 0) > thresholds.get('max_memory_mb', 1024):
            issues.append(f"Memory usage too high: {resource_usage.get('max_memory_mb', 0):.1f}MB")
        
        return len(issues) == 0, issues

class LoadTester:
    """Load testing utilities for RAG pipeline"""
    
    def __init__(self, rag_pipeline_func: Callable, monitor: PerformanceMonitor):
        self.rag_pipeline = rag_pipeline_func
        self.monitor = monitor
    
    async def run_concurrent_load_test(self, queries: List[str], concurrent_users: int, duration_seconds: int) -> Dict[str, Any]:
        """Run concurrent load test"""
        logger.info(f"Starting load test: {concurrent_users} users, {duration_seconds}s duration")
        
        self.monitor.start_monitoring()
        start_time = time.time()
        tasks = []
        
        async def worker():
            """Worker coroutine"""
            while time.time() - start_time < duration_seconds:
                query = queries[int(time.time()) % len(queries)]  # Rotate queries
                
                with self.monitor.track_request():
                    try:
                        result = await asyncio.to_thread(self.rag_pipeline, query)
                        # Simulate token counting
                        token_count = len(str(result).split()) * 1.3  # Rough estimate
                        self.monitor.record_token_usage(int(token_count))
                        
                    except Exception as e:
                        logger.error(f"Query failed: {e}")
                
                await asyncio.sleep(0.1)  # Brief pause between requests
        
        # Start concurrent workers
        for _ in range(concurrent_users):
            task = asyncio.create_task(worker())
            tasks.append(task)
        
        # Wait for completion
        await asyncio.sleep(duration_seconds)
        
        # Cancel remaining tasks
        for task in tasks:
            task.cancel()
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self.monitor.stop_monitoring()
        
        results = self.monitor.get_current_metrics()
        results['test_config'] = {
            'concurrent_users': concurrent_users,
            'duration_seconds': duration_seconds,
            'queries_used': len(queries)
        }
        
        logger.info(f"Load test completed: {results['total_requests']} requests")
        return results
    
    def run_cache_performance_test(self, queries: List[str], warmup_queries: int = 50) -> Dict[str, Any]:
        """Test cache performance impact"""
        logger.info("Running cache performance test")
        
        # Cold cache test
        cold_times = []
        for i, query in enumerate(queries[:warmup_queries]):
            with self.monitor.track_request():
                self.rag_pipeline(query)
                self.monitor.record_cache_miss()
            
            if i < len(self.monitor.metrics.response_times):
                cold_times.append(self.monitor.metrics.response_times[i])
        
        # Warm cache test (repeat same queries)
        warm_times = []
        start_idx = len(self.monitor.metrics.response_times)
        
        for query in queries[:warmup_queries]:
            with self.monitor.track_request():
                self.rag_pipeline(query)
                self.monitor.record_cache_hit()
        
        warm_times = self.monitor.metrics.response_times[start_idx:]
        
        return {
            'cold_cache': {
                'mean_latency_ms': statistics.mean(cold_times) if cold_times else 0,
                'median_latency_ms': statistics.median(cold_times) if cold_times else 0
            },
            'warm_cache': {
                'mean_latency_ms': statistics.mean(warm_times) if warm_times else 0,
                'median_latency_ms': statistics.median(warm_times) if warm_times else 0
            },
            'cache_improvement': {
                'latency_reduction_percent': (
                    (statistics.mean(cold_times) - statistics.mean(warm_times)) / statistics.mean(cold_times) * 100
                    if cold_times and warm_times else 0
                )
            }
        }

class AlertManager:
    """Manage performance alerts and notifications"""
    
    def __init__(self, thresholds: Dict[str, Any]):
        self.thresholds = thresholds
        self.alerts = []
    
    def check_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for alert conditions"""
        new_alerts = []
        
        # Latency alerts
        latency = metrics.get('latency', {})
        if latency.get('p95', 0) > self.thresholds.get('p95_latency_ms', 500):
            new_alerts.append({
                'type': 'latency_p95',
                'severity': 'warning',
                'message': f"P95 latency high: {latency.get('p95', 0):.1f}ms",
                'timestamp': time.time()
            })
        
        if latency.get('p99', 0) > self.thresholds.get('p99_latency_ms', 1000):
            new_alerts.append({
                'type': 'latency_p99',
                'severity': 'critical',
                'message': f"P99 latency critical: {latency.get('p99', 0):.1f}ms",
                'timestamp': time.time()
            })
        
        # Error rate alerts
        error_rates = metrics.get('error_rates', {})
        if error_rates.get('error_rate', 0) > self.thresholds.get('error_rate', 0.01):
            new_alerts.append({
                'type': 'error_rate',
                'severity': 'critical',
                'message': f"Error rate high: {error_rates.get('error_rate', 0):.2%}",
                'timestamp': time.time()
            })
        
        self.alerts.extend(new_alerts)
        return new_alerts
    
    def get_active_alerts(self, max_age_seconds: int = 300) -> List[Dict[str, Any]]:
        """Get alerts within time window"""
        current_time = time.time()
        return [
            alert for alert in self.alerts 
            if current_time - alert['timestamp'] <= max_age_seconds
        ]