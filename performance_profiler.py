#!/usr/bin/env python3
"""
Performance Profiling Script per ALLMA
======================================

Misura e traccia metriche chiave di performance:
- Response time (Gemma vs Indipendente)
- Memory usage per conversation
- SQLite query performance
- Confidence evolution tracking
"""

import time
import psutil
import json
import logging
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass, asdict
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Model.core.allma_core import ALLMACore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class PerformanceMetrics:
    """Metriche di performance per una singola interazione"""
    timestamp: str
    response_time_ms: float
    memory_mb: float
    used_gemma: bool
    knowledge_integrated: bool
    confidence: float
    topic: str
    
class PerformanceProfiler:
    """Profiler per tracciare performance di ALLMA"""
    
    def __init__(self, output_file: str = "performance_metrics.json"):
        self.metrics: List[Dict] = []
        self.output_file = output_file
        self.process = psutil.Process()
        
    def get_memory_mb(self) -> float:
        """Ritorna memoria utilizzata in MB"""
        return self.process.memory_info().rss / 1024 / 1024
    
    def profile_interaction(
        self,
        allma: ALLMACore,
        user_id: str,
        conversation_id: str,
        message: str,
        topic: str = "unknown"
    ) -> PerformanceMetrics:
        """Profila una singola interazione"""
        
        # Misura memoria iniziale
        mem_before = self.get_memory_mb()
        
        # Misura tempo
        start_time = time.time()
        response = allma.process_message(user_id, conversation_id, message)
        end_time = time.time()
        
        # Misura memoria finale
        mem_after = self.get_memory_mb()
        
        # Calcola metriche
        response_time_ms = (end_time - start_time) * 1000
        memory_delta = mem_after - mem_before
        
        # Crea oggetto metriche
        metrics = PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            response_time_ms=round(response_time_ms, 2),
            memory_mb=round(mem_after, 2),
            used_gemma=not response.knowledge_integrated,
            knowledge_integrated=response.knowledge_integrated,
            confidence=response.confidence,
            topic=topic
        )
        
        # Salva
        self.metrics.append(asdict(metrics))
        
        # Log
        mode = "🟢 INDIPENDENTE" if response.knowledge_integrated else "🔴 GEMMA"
        logging.info(
            f"{mode} | {response_time_ms:.0f}ms | "
            f"Mem: {mem_after:.1f}MB (+{memory_delta:.1f}) | "
            f"Confidence: {response.confidence:.2f}"
        )
        
        return metrics
    
    def save_metrics(self):
        """Salva metriche su file JSON"""
        with open(self.output_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        logging.info(f"📊 Metriche salvate in {self.output_file}")
    
    def generate_summary(self) -> Dict:
        """Genera summary delle metriche"""
        if not self.metrics:
            return {}
        
        gemma_responses = [m for m in self.metrics if m['used_gemma']]
        independent_responses = [m for m in self.metrics if m['knowledge_integrated']]
        
        summary = {
            "total_interactions": len(self.metrics),
            "gemma_count": len(gemma_responses),
            "independent_count": len(independent_responses),
            "independence_ratio": len(independent_responses) / len(self.metrics) if self.metrics else 0,
            "avg_response_time_ms": {
                "gemma": sum(m['response_time_ms'] for m in gemma_responses) / len(gemma_responses) if gemma_responses else 0,
                "independent": sum(m['response_time_ms'] for m in independent_responses) / len(independent_responses) if independent_responses else 0,
                "overall": sum(m['response_time_ms'] for m in self.metrics) / len(self.metrics)
            },
            "avg_memory_mb": sum(m['memory_mb'] for m in self.metrics) / len(self.metrics),
            "avg_confidence": sum(m['confidence'] for m in self.metrics) / len(self.metrics)
        }
        
        return summary

def run_benchmark():
    """Esegue benchmark di performance"""
    print("=" * 60)
    print("🚀 ALLMA Performance Profiling")
    print("=" * 60)
    
    # Inizializza
    profiler = PerformanceProfiler()
    allma = ALLMACore(mobile_mode=True)
    allma.start_conversation("perf_test")
    
    # Test queries
    test_queries = [
        ("Cos'è Python?", "python"),
        ("Spiegami Python", "python"),  # Stesso topic, dovrebbe diventare indipendente
        ("Ancora Python", "python"),
        ("Python per favore", "python"),
        ("Cos'è l'amore?", "amore"),
        ("Parlami dell'amore", "amore"),
        ("Che tempo fa?", "meteo"),
    ]
    
    print(f"\n📝 Esecuzione {len(test_queries)} test queries...\n")
    
    for i, (query, topic) in enumerate(test_queries, 1):
        print(f"\n[{i}/{len(test_queries)}] Query: '{query}'")
        profiler.profile_interaction(
            allma=allma,
            user_id="perf_test",
            conversation_id="bench_conv",
            message=query,
            topic=topic
        )
        time.sleep(0.5)  # Pausa tra queries
    
    # Salva e genera summary
    profiler.save_metrics()
    summary = profiler.generate_summary()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Total Interactions: {summary['total_interactions']}")
    print(f"Gemma Calls: {summary['gemma_count']}")
    print(f"Independent Responses: {summary['independent_count']}")
    print(f"Independence Ratio: {summary['independence_ratio']:.1%}")
    print(f"\nAvg Response Time:")
    print(f"  - Gemma: {summary['avg_response_time_ms']['gemma']:.0f}ms")
    print(f"  - Independent: {summary['avg_response_time_ms']['independent']:.0f}ms")
    print(f"  - Overall: {summary['avg_response_time_ms']['overall']:.0f}ms")
    print(f"\nAvg Memory: {summary['avg_memory_mb']:.1f}MB")
    print(f"Avg Confidence: {summary['avg_confidence']:.2f}")
    print("=" * 60)

if __name__ == "__main__":
    run_benchmark()
