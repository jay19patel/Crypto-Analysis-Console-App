"""
Performance optimization utilities for the trading system
"""

import asyncio
import functools
import logging
import time
import threading
from collections import defaultdict, deque
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from dataclasses import dataclass
import weakref
import gc
import psutil
import sys

# Type hints
F = TypeVar('F', bound=Callable[..., Any])


@dataclass
class PerformanceMetrics:
    """Performance metrics container"""
    avg_execution_time: float
    min_execution_time: float
    max_execution_time: float
    total_calls: int
    total_time: float
    calls_per_second: float
    memory_usage_mb: float
    cpu_usage_percent: float


class PerformanceMonitor:
    """Performance monitoring and optimization utilities"""
    
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self.call_counts: Dict[str, int] = defaultdict(int)
        self.start_times: Dict[str, float] = {}
        self.lock = threading.RLock()
        self.logger = logging.getLogger("performance_monitor")
        
    def record_execution_time(self, function_name: str, execution_time: float):
        """Record execution time for a function"""
        with self.lock:
            self.metrics[function_name].append(execution_time)
            self.call_counts[function_name] += 1
    
    def get_metrics(self, function_name: str) -> Optional[PerformanceMetrics]:
        """Get performance metrics for a function"""
        with self.lock:
            if function_name not in self.metrics or not self.metrics[function_name]:
                return None
            
            times = list(self.metrics[function_name])
            total_calls = self.call_counts[function_name]
            total_time = sum(times)
            
            # Get system metrics
            try:
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
            except:
                memory_mb = 0.0
                cpu_percent = 0.0
            
            return PerformanceMetrics(
                avg_execution_time=total_time / len(times),
                min_execution_time=min(times),
                max_execution_time=max(times),
                total_calls=total_calls,
                total_time=total_time,
                calls_per_second=total_calls / total_time if total_time > 0 else 0,
                memory_usage_mb=memory_mb,
                cpu_usage_percent=cpu_percent
            )
    
    def get_all_metrics(self) -> Dict[str, PerformanceMetrics]:
        """Get metrics for all monitored functions"""
        with self.lock:
            return {
                name: self.get_metrics(name)
                for name in self.metrics.keys()
                if self.get_metrics(name) is not None
            }
    
    def reset_metrics(self, function_name: Optional[str] = None):
        """Reset metrics for a specific function or all functions"""
        with self.lock:
            if function_name:
                if function_name in self.metrics:
                    self.metrics[function_name].clear()
                    self.call_counts[function_name] = 0
            else:
                self.metrics.clear()
                self.call_counts.clear()


# Global performance monitor instance
_performance_monitor = PerformanceMonitor()


def performance_monitor(func_name: Optional[str] = None):
    """Decorator to monitor function performance"""
    def decorator(func: F) -> F:
        name = func_name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                _performance_monitor.record_execution_time(name, execution_time)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                _performance_monitor.record_execution_time(name, execution_time)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class LRUCache:
    """Thread-safe LRU cache implementation"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: Dict[Any, Any] = {}
        self.access_order = deque()
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: Any, default: Any = None) -> Any:
        """Get item from cache"""
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.access_order.remove(key)
                self.access_order.append(key)
                self.hits += 1
                return self.cache[key]
            else:
                self.misses += 1
                return default
    
    def put(self, key: Any, value: Any):
        """Put item in cache"""
        with self.lock:
            if key in self.cache:
                # Update existing
                self.cache[key] = value
                self.access_order.remove(key)
                self.access_order.append(key)
            else:
                # Add new
                if len(self.cache) >= self.max_size:
                    # Remove least recently used
                    lru_key = self.access_order.popleft()
                    del self.cache[lru_key]
                
                self.cache[key] = value
                self.access_order.append(key)
    
    def remove(self, key: Any) -> bool:
        """Remove item from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.access_order.remove(key)
                return True
            return False
    
    def clear(self):
        """Clear all cache"""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
            self.hits = 0
            self.misses = 0
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)
    
    def hit_rate(self) -> float:
        """Get cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def stats(self) -> Dict[str, Union[int, float]]:
        """Get cache statistics"""
        return {
            "size": self.size(),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate()
        }


def cached(max_size: int = 1000, ttl: Optional[int] = None):
    """Decorator for caching function results with optional TTL"""
    def decorator(func: F) -> F:
        cache = LRUCache(max_size)
        ttl_cache = {} if ttl else None
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = str(args) + str(sorted(kwargs.items()))
            
            # Check TTL if enabled
            if ttl_cache is not None:
                current_time = time.time()
                if key in ttl_cache and current_time - ttl_cache[key] > ttl:
                    cache.remove(key)
                    del ttl_cache[key]
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.put(key, result)
            
            if ttl_cache is not None:
                ttl_cache[key] = time.time()
            
            return result
        
        # Add cache management methods
        wrapper.cache_clear = cache.clear
        wrapper.cache_stats = cache.stats
        wrapper.cache_size = cache.size
        
        return wrapper
    
    return decorator


class MemoryOptimizer:
    """Memory optimization utilities"""
    
    def __init__(self):
        self.logger = logging.getLogger("memory_optimizer")
        self.weak_refs: Dict[str, weakref.ref] = {}
        self.last_gc_time = time.time()
        self.gc_threshold = 300  # 5 minutes
    
    @staticmethod
    def get_memory_usage() -> Dict[str, float]:
        """Get current memory usage statistics"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size
                "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size
                "percent": process.memory_percent(),
                "available_mb": psutil.virtual_memory().available / 1024 / 1024,
                "total_mb": psutil.virtual_memory().total / 1024 / 1024
            }
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def force_garbage_collection() -> Dict[str, int]:
        """Force garbage collection and return statistics"""
        before_count = len(gc.get_objects())
        
        # Collect garbage
        collected = []
        for generation in range(3):
            collected.append(gc.collect(generation))
        
        after_count = len(gc.get_objects())
        
        return {
            "objects_before": before_count,
            "objects_after": after_count,
            "objects_collected": before_count - after_count,
            "generation_0": collected[0],
            "generation_1": collected[1],
            "generation_2": collected[2]
        }
    
    def periodic_cleanup(self) -> bool:
        """Perform periodic memory cleanup"""
        current_time = time.time()
        
        if current_time - self.last_gc_time > self.gc_threshold:
            try:
                gc_stats = self.force_garbage_collection()
                self.last_gc_time = current_time
                
                if gc_stats["objects_collected"] > 0:
                    self.logger.debug(f"Garbage collection: {gc_stats}")
                
                return True
            except Exception as e:
                self.logger.error(f"Error during garbage collection: {e}")
                return False
        
        return False
    
    def register_weak_reference(self, name: str, obj: Any):
        """Register weak reference for monitoring"""
        def cleanup_callback(ref):
            if name in self.weak_refs:
                del self.weak_refs[name]
        
        self.weak_refs[name] = weakref.ref(obj, cleanup_callback)
    
    def get_alive_references(self) -> Dict[str, bool]:
        """Get status of registered weak references"""
        return {
            name: ref() is not None
            for name, ref in self.weak_refs.items()
        }


class AsyncResourcePool:
    """Async resource pool for managing connections and objects"""
    
    def __init__(self, factory: Callable, max_size: int = 10, timeout: float = 30.0):
        self.factory = factory
        self.max_size = max_size
        self.timeout = timeout
        self._pool = asyncio.Queue(maxsize=max_size)
        self._created = 0
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger("resource_pool")
    
    async def acquire(self) -> Any:
        """Acquire resource from pool"""
        try:
            # Try to get from pool with timeout
            resource = await asyncio.wait_for(
                self._pool.get(),
                timeout=1.0  # Short timeout for pool check
            )
            return resource
        except asyncio.TimeoutError:
            # Pool is empty, create new resource if under limit
            async with self._lock:
                if self._created < self.max_size:
                    resource = await self.factory()
                    self._created += 1
                    self.logger.debug(f"Created new resource ({self._created}/{self.max_size})")
                    return resource
                else:
                    # Wait for resource to become available
                    resource = await asyncio.wait_for(
                        self._pool.get(),
                        timeout=self.timeout
                    )
                    return resource
    
    async def release(self, resource: Any):
        """Release resource back to pool"""
        try:
            await self._pool.put(resource)
        except asyncio.QueueFull:
            # Pool is full, discard resource
            self.logger.warning("Resource pool full, discarding resource")
    
    async def close_all(self):
        """Close all resources in pool"""
        while not self._pool.empty():
            try:
                resource = await self._pool.get()
                if hasattr(resource, 'close'):
                    await resource.close()
                elif hasattr(resource, 'disconnect'):
                    await resource.disconnect()
            except Exception as e:
                self.logger.error(f"Error closing resource: {e}")
        
        self._created = 0
    
    def stats(self) -> Dict[str, int]:
        """Get pool statistics"""
        return {
            "pool_size": self._pool.qsize(),
            "max_size": self.max_size,
            "created": self._created,
            "available": self._pool.qsize()
        }


class RateLimiter:
    """Thread-safe rate limiter using sliding window"""
    
    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
        self.lock = threading.RLock()
    
    def is_allowed(self) -> bool:
        """Check if call is allowed under rate limit"""
        with self.lock:
            current_time = time.time()
            
            # Remove old calls outside the window
            while self.calls and current_time - self.calls[0] > self.time_window:
                self.calls.popleft()
            
            # Check if we can make another call
            if len(self.calls) < self.max_calls:
                self.calls.append(current_time)
                return True
            
            return False
    
    def wait_time(self) -> float:
        """Get time to wait before next call is allowed"""
        with self.lock:
            if not self.calls:
                return 0.0
            
            current_time = time.time()
            oldest_call = self.calls[0]
            
            if len(self.calls) < self.max_calls:
                return 0.0
            
            return max(0.0, self.time_window - (current_time - oldest_call))
    
    async def acquire(self):
        """Async acquire - wait until call is allowed"""
        while not self.is_allowed():
            wait_time = self.wait_time()
            if wait_time > 0:
                await asyncio.sleep(min(wait_time, 0.1))  # Check every 100ms
    
    def reset(self):
        """Reset rate limiter"""
        with self.lock:
            self.calls.clear()


# Global instances
memory_optimizer = MemoryOptimizer()


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    return _performance_monitor


def get_memory_optimizer() -> MemoryOptimizer:
    """Get global memory optimizer instance"""
    return memory_optimizer


def optimize_pandas_memory(df):
    """Optimize pandas DataFrame memory usage"""
    try:
        import pandas as pd
        
        # Optimize numeric columns
        for col in df.select_dtypes(include=['int64']).columns:
            df[col] = pd.to_numeric(df[col], downcast='integer')
        
        for col in df.select_dtypes(include=['float64']).columns:
            df[col] = pd.to_numeric(df[col], downcast='float')
        
        # Optimize object columns to category if beneficial
        for col in df.select_dtypes(include=['object']).columns:
            if df[col].nunique() / len(df) < 0.5:  # If less than 50% unique values
                df[col] = df[col].astype('category')
        
        return df
    except ImportError:
        return df


@performance_monitor("system_health_check")
def get_system_health() -> Dict[str, Any]:
    """Get comprehensive system health information"""
    try:
        # CPU information
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory information
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk information
        disk = psutil.disk_usage('/')
        
        # Process information
        process = psutil.Process()
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
                "load_avg": getattr(psutil, 'getloadavg', lambda: (0, 0, 0))()
            },
            "memory": {
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "used_gb": memory.used / (1024**3),
                "percent": memory.percent
            },
            "swap": {
                "total_gb": swap.total / (1024**3),
                "used_gb": swap.used / (1024**3),
                "percent": swap.percent
            },
            "disk": {
                "total_gb": disk.total / (1024**3),
                "free_gb": disk.free / (1024**3),
                "used_gb": disk.used / (1024**3),
                "percent": (disk.used / disk.total) * 100
            },
            "process": {
                "cpu_percent": process.cpu_percent(),
                "memory_mb": process.memory_info().rss / (1024**2),
                "memory_percent": process.memory_percent(),
                "num_threads": process.num_threads(),
                "num_fds": getattr(process, 'num_fds', lambda: 0)()  # Unix only
            },
            "python": {
                "version": sys.version,
                "gc_counts": gc.get_count(),
                "gc_stats": gc.get_stats() if hasattr(gc, 'get_stats') else []
            }
        }
    except Exception as e:
        return {"error": str(e)}