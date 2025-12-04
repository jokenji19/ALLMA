"""
Sistema di profiling per ALLMA con gestione ottimizzata della memoria
"""
import cProfile
import pstats
import time
from typing import Dict, Any, Optional, List
import logging
from functools import wraps
from datetime import datetime
import gc
import psutil
import os
import weakref
from collections import deque

class MemoryTracker:
    def __init__(self, max_history: int = 100):
        self.memory_history = deque(maxlen=max_history)
        self.peak_memory = 0
        self.threshold_warning = 0.75  # 75% del massimo
        self.threshold_critical = 0.90  # 90% del massimo
        
    def update(self, current_memory: float):
        """Aggiorna il tracciamento della memoria"""
        self.memory_history.append(current_memory)
        self.peak_memory = max(self.peak_memory, current_memory)
        
    def get_trend(self) -> float:
        """Calcola il trend di utilizzo della memoria"""
        if len(self.memory_history) < 2:
            return 0.0
        return (self.memory_history[-1] - self.memory_history[0]) / len(self.memory_history)
        
    def should_optimize(self) -> bool:
        """Determina se è necessaria un'ottimizzazione"""
        if not self.memory_history:
            return False
        current = self.memory_history[-1]
        return (current / self.peak_memory) > self.threshold_warning

class PerformanceProfiler:
    def __init__(self):
        self.profiler = cProfile.Profile()
        self.metrics = {}
        self._start_time = None
        self._start_memory = None
        self.logger = logging.getLogger(__name__)
        self.memory_tracker = MemoryTracker()
        self._cached_objects = weakref.WeakSet()
        self.memory_threshold = 0.75  # 75% della RAM totale
        
    def start_profiling(self):
        """Inizia il profiling"""
        self.profiler.enable()
        self._optimize_memory_usage()
        
    def stop_profiling(self) -> pstats.Stats:
        """Ferma il profiling e restituisce le statistiche"""
        self.profiler.disable()
        stats = pstats.Stats(self.profiler)
        stats.sort_stats('cumulative')
        self._cleanup_memory()
        return stats
        
    def _optimize_memory_usage(self):
        """Ottimizza l'uso della memoria quando necessario"""
        if self.memory_tracker.should_optimize():
            self._cleanup_memory()
            if self._get_memory_percentage() > self.memory_threshold:
                self._emergency_memory_cleanup()
                
    def _cleanup_memory(self):
        """Pulizia normale della memoria"""
        gc.collect()
        self._cached_objects.clear()
        
    def _emergency_memory_cleanup(self):
        """Pulizia di emergenza della memoria"""
        for _ in range(3):  # Pulizia aggressiva
            gc.collect()
        self.metrics = {k: v for k, v in self.metrics.items() 
                       if time.time() - v.get('last_access', 0) < 3600}
        
    def _get_memory_percentage(self) -> float:
        """Ottiene la percentuale di memoria utilizzata"""
        process = psutil.Process(os.getpid())
        return process.memory_percent()
        
    def profile_operation(self, operation_type: str):
        """Decorator per profilare operazioni specifiche"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                start_memory = self._get_memory_usage()
                
                try:
                    self._optimize_memory_usage()  # Check prima dell'operazione
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    memory_used = self._get_memory_usage() - start_memory
                    
                    if operation_type not in self.metrics:
                        self.metrics[operation_type] = {
                            'times': [],
                            'memory_usage': [],
                            'count': 0,
                            'last_access': time.time()
                        }
                    metric = self.metrics[operation_type]
                    metric['times'].append(execution_time)
                    metric['memory_usage'].append(memory_used)
                    metric['count'] += 1
                    metric['last_access'] = time.time()
                    
                    self.memory_tracker.update(self._get_memory_usage())
                    
                    if execution_time > 1.0:
                        self.logger.warning(
                            f"Operazione lenta rilevata: {func.__name__} "
                            f"({execution_time:.2f}s)"
                        )
                        
                    return result
                except Exception as e:
                    self.logger.error(f"Errore durante {func.__name__}: {str(e)}")
                    raise
                finally:
                    if self.memory_tracker.should_optimize():
                        self._optimize_memory_usage()
                    
            return wrapper
        return decorator
        
    def _get_memory_usage(self) -> float:
        """Ottiene l'uso corrente della memoria"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024  # MB
        
    def analyze_performance(self) -> Dict[str, Any]:
        """Analizza le metriche di performance raccolte"""
        self._optimize_memory_usage()  # Ottimizza prima dell'analisi
        analysis = {}
        
        for operation_type, metric in self.metrics.items():
            if metric['count'] > 0:
                analysis[operation_type] = {
                    'avg_time': sum(metric['times']) / metric['count'],
                    'max_time': max(metric['times']),
                    'avg_memory': sum(metric['memory_usage']) / metric['count'],
                    'max_memory': max(metric['memory_usage']),
                    'count': metric['count'],
                    'memory_trend': self.memory_tracker.get_trend()
                }
            
        return analysis
        
    def generate_report(self) -> str:
        """Genera un report dettagliato delle performance"""
        self._optimize_memory_usage()  # Ottimizza prima di generare il report
        analysis = self.analyze_performance()
        
        report = ["=== Report Performance ALLMA ===\n"]
        report.append(f"Memoria di picco: {self.memory_tracker.peak_memory:.2f}MB")
        report.append(f"Trend memoria: {self.memory_tracker.get_trend():.2f}MB/op\n")
        
        for operation_type, metrics in analysis.items():
            report.append(f"\n{operation_type.upper()}:")
            report.append(f"- Tempo medio di esecuzione: {metrics['avg_time']:.3f}s")
            report.append(f"- Tempo massimo di esecuzione: {metrics['max_time']:.3f}s")
            report.append(f"- Uso medio memoria: {metrics['avg_memory']:.2f}MB")
            report.append(f"- Uso massimo memoria: {metrics['max_memory']:.2f}MB")
            report.append(f"- Operazioni totali: {metrics['count']}")
            
        return "\n".join(report)

    def profile(self, operation_name):
        """Context manager per profilare operazioni"""
        return ProfilerContext(self, operation_name)
        
    def _start_operation(self, operation_name):
        """Inizia a tracciare un'operazione"""
        self._optimize_memory_usage()
        if operation_name not in self.metrics:
            self.metrics[operation_name] = {
                'times': [],
                'memory_usage': [],
                'count': 0,
                'last_access': time.time()
            }
        self._start_time = time.time()
        self._start_memory = self._get_memory_usage()
        
    def _end_operation(self, operation_name):
        """Termina il tracciamento di un'operazione"""
        end_time = time.time()
        end_memory = self._get_memory_usage()
        
        duration = end_time - self._start_time
        memory_used = end_memory - self._start_memory
        
        metric = self.metrics[operation_name]
        metric['times'].append(duration)
        metric['memory_usage'].append(memory_used)
        metric['count'] += 1
        metric['last_access'] = time.time()
        
        self.memory_tracker.update(end_memory)
        self._optimize_memory_usage()
        
    def get_statistics(self):
        """Restituisce le statistiche di performance"""
        self._optimize_memory_usage()
        stats = {}
        for operation, metric in self.metrics.items():
            if metric['count'] > 0:
                stats[operation] = {
                    'avg_time': sum(metric['times']) / metric['count'],
                    'max_time': max(metric['times']),
                    'avg_memory': sum(metric['memory_usage']) / metric['count'],
                    'max_memory': max(metric['memory_usage']),
                    'count': metric['count'],
                    'memory_trend': self.memory_tracker.get_trend()
                }
        return stats

class ProfilerContext:
    def __init__(self, profiler, operation_name):
        self.profiler = profiler
        self.operation_name = operation_name
        
    def __enter__(self):
        self.profiler._start_operation(self.operation_name)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.profiler._end_operation(self.operation_name)
