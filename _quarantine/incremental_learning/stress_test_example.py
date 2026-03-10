"""
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending - ALLMA (Adaptive Learning and Language Model Architecture)

This file contains stress tests for the ALLMA system.
Author: Cristof Bano
Created: January 2025

This stress test validates:
- System performance under load
- Resource management
- Memory optimization
- Adaptive behavior
"""

from language_system import LanguageSystem
from performance_optimizer import PerformanceOptimizer
from resource_adapter import ResourceAdapter
from memory_manager import MemoryManager
import time
import json
import psutil
import random
import string

def generate_large_content(size_kb: int) -> str:
    """Genera contenuto di dimensione specificata in KB"""
    return ''.join(random.choices(string.ascii_letters + string.digits, 
                                k=size_kb * 1024))

class StressTestAssistant:
    def __init__(self):
        self.language_system = LanguageSystem()
        self.performance_optimizer = PerformanceOptimizer()
        self.resource_adapter = ResourceAdapter()
        self.memory_manager = MemoryManager()
        self.session_start = time.time()

    def simulate_high_load(self):
        """Simula un carico di sistema molto alto"""
        print("\n=== Test 1: Simulazione Carico Alto ===")
        
        # Forza CPU alta
        print("Simulando carico CPU alto...")
        for _ in range(10):
            perf_profile = self.performance_optimizer.adapt_performance()
            resources = self.resource_adapter.adapt_resources()
            
            print(f"\nModalità: {perf_profile['mode']}")
            print(f"CPU Usage: {psutil.cpu_percent()}%")
            print(f"Memoria: {psutil.virtual_memory().percent}%")
            
            # Esegui calcoli pesanti per aumentare il carico
            _ = [i * i for i in range(1000000)]
            time.sleep(0.1)

    def simulate_memory_pressure(self):
        """Simula pressione sulla memoria"""
        print("\n=== Test 2: Simulazione Memoria Quasi Piena ===")
        
        print("Generando dati di grandi dimensioni...")
        for i in range(20):
            # Genera e memorizza contenuto grande
            content = generate_large_content(500)  # 500KB per item
            self.memory_manager.store_item(content, "large_data")
            
            stats = self.memory_manager.get_memory_stats()
            print(f"\nItem in memoria: {stats['total_items']}")
            print(f"Item compressi: {stats['compressed_items']}")
            print(f"Item archiviati: {stats['archived_items']}")
            
            time.sleep(0.2)

    def simulate_low_battery(self):
        """Simula condizione di batteria scarica"""
        print("\n=== Test 3: Simulazione Batteria Scarica ===")
        
        # Modifica temporaneamente la lettura della batteria
        original_battery = psutil.sensors_battery
        try:
            def mock_battery():
                class MockBattery:
                    percent = 10.0
                return MockBattery()
            
            psutil.sensors_battery = mock_battery
            
            print("Batteria al 10%...")
            for _ in range(5):
                perf_profile = self.performance_optimizer.adapt_performance()
                resources = self.resource_adapter.adapt_resources()
                
                print(f"\nModalità: {perf_profile['mode']}")
                print(f"Frequenza Analisi: {perf_profile['analysis_frequency']}ms")
                print(f"Buffer Memoria: {perf_profile['memory_buffer']}GB")
                
                time.sleep(0.5)
        
        finally:
            psutil.sensors_battery = original_battery

    def test_language_switching(self):
        """Testa il cambio di lingua al volo"""
        print("\n=== Test 4: Cambio Lingua al Volo ===")
        
        languages = ["it", "en", "es"]
        messages = {
            "it": "Ciao! Come stai oggi?",
            "en": "Hi! How are you today?",
            "es": "¡Hola! ¿Cómo estás hoy?"
        }
        
        for lang in languages:
            print(f"\nCambio lingua a: {lang}")
            self.language_system.set_language(lang)
            
            # Processa un messaggio
            response = self.language_system.get_response("greeting")
            print(f"Input: {messages[lang]}")
            print(f"Risposta: {response}")
            
            time.sleep(0.5)

    def get_system_status(self) -> dict:
        """Ottiene lo stato attuale del sistema"""
        return {
            "uptime": time.time() - self.session_start,
            "language": self.language_system.current_language["name"],
            "performance_mode": self.performance_optimizer.current_mode.value,
            "memory_stats": self.memory_manager.get_memory_stats(),
            "resource_allocation": self.resource_adapter.get_current_allocation().__dict__
        }

def main():
    """Esegue i test di stress sul sistema"""
    assistant = StressTestAssistant()
    
    print("=== Inizio Test di Stress ===")
    print("Stato Iniziale:")
    print(json.dumps(assistant.get_system_status(), indent=2))
    
    # Esegue i test
    assistant.simulate_high_load()
    assistant.simulate_memory_pressure()
    assistant.simulate_low_battery()
    assistant.test_language_switching()
    
    print("\n=== Stato Finale del Sistema ===")
    print(json.dumps(assistant.get_system_status(), indent=2))

if __name__ == "__main__":
    main()
