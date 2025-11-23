#!/usr/bin/env python3
"""
ALLMA System Benchmark
======================
Misura le prestazioni (latenza e risorse) dei sottosistemi chiave.
"""

import time
import sys
import os
import psutil
import logging
from statistics import mean

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configura logging per non inquinare l'output
logging.basicConfig(level=logging.ERROR)

from Model.core.allma_core import ALLMACore

def measure_time(func, *args, **kwargs):
    start = time.time()
    result = func(*args, **kwargs)
    end = time.time()
    return (end - start) * 1000, result  # ms

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

def run_benchmark():
    print("=" * 60)
    print("🚀 ALLMA SYSTEM BENCHMARK")
    print("=" * 60)
    
    print(f"Initial Memory: {get_memory_usage():.2f} MB")
    
    # 1. Cold Start
    print("\n1️⃣  Cold Start (Inizializzazione)...")
    start_mem = get_memory_usage()
    t_init, allma = measure_time(ALLMACore, mobile_mode=True)
    end_mem = get_memory_usage()
    
    print(f"   ⏱️  Time: {t_init:.2f} ms")
    print(f"   💾 RAM Delta: +{end_mem - start_mem:.2f} MB")
    
    # 2. Emotion Analysis (Simulato tramite pipeline interna)
    print("\n2️⃣  Emotion Analysis Pipeline...")
    # Accediamo direttamente al metodo interno se possibile, o misuriamo via process_message
    # Per ora usiamo una chiamata fittizia per stimare
    t_emotion = 0.0
    # (Nota: la pipeline reale è caricata in ALLMACore, qui testiamo l'overhead)
    
    # 3. Reasoning Engine
    print("\n3️⃣  Reasoning Engine (Thought Generation)...")
    context = {'relevant_memories': [{'content': 'User likes Python'}]}
    emotion = type('obj', (object,), {'primary_emotion': 'joy', 'intensity': 0.8, 'confidence': 0.9})
    
    times = []
    for _ in range(10):
        t, _ = measure_time(allma.reasoning_engine.generate_thought_process, "Ciao, come stai?", context, emotion)
        times.append(t)
        
    print(f"   ⏱️  Avg Time: {mean(times):.2f} ms")
    print(f"   ⚡ Min/Max: {min(times):.2f} / {max(times):.2f} ms")
    
    # 4. Memory Retrieval
    print("\n4️⃣  Memory Retrieval (Vector/Keyword Search)...")
    # Popoliamo un po' la memoria
    interaction_data = {
        'content': "Mi piace la pizza",
        'context': {'source': 'benchmark'},
        'emotion': 'joy',
        'topics': ['food']
    }
    allma.memory_system.store_interaction("user_1", interaction_data)
    
    times = []
    for _ in range(10):
        t, _ = measure_time(allma.memory_system.get_relevant_context, "user_1", "food")
        times.append(t)
        
    print(f"   ⏱️  Avg Time: {mean(times):.2f} ms")
    
    # 5. Proactive Agency Check
    print("\n5️⃣  Proactive Agency Check...")
    from datetime import datetime, timedelta
    last_time = datetime.now() - timedelta(hours=12)
    last_emotion = {'primary_emotion': 'sadness', 'intensity': 0.8}
    
    times = []
    for _ in range(100): # Molto veloce, ne facciamo tanti
        t, _ = measure_time(allma.proactive_agency.check_initiative, "user_1", last_time, last_emotion)
        times.append(t)
        
    print(f"   ⏱️  Avg Time: {mean(times):.4f} ms")
    
    # 6. Full Cycle (Simulated without heavy LLM)
    print("\n6️⃣  Full Processing Cycle (No LLM)...")
    # Forziamo una risposta indipendente (knowledge) per testare la velocità del core
    allma.incremental_learner.add_knowledge("test_topic", "Risposta test", 1.0)
    
    t_full, response = measure_time(allma.process_message, "test_topic", "user_1")
    print(f"   ⏱️  Total Latency: {t_full:.2f} ms")
    
    print("\n" + "=" * 60)
    print(f"Final Memory Usage: {get_memory_usage():.2f} MB")
    print("=" * 60)

if __name__ == "__main__":
    run_benchmark()
