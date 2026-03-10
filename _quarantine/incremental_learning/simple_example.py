from language_system import LanguageSystem
from performance_optimizer import PerformanceOptimizer
from resource_adapter import ResourceAdapter
from memory_manager import MemoryManager
import time
import json

class SimpleAssistant:
    def __init__(self):
        # Inizializzazione dei sistemi di ottimizzazione
        self.language_system = LanguageSystem()
        self.performance_optimizer = PerformanceOptimizer()
        self.resource_adapter = ResourceAdapter()
        self.memory_manager = MemoryManager()
        self.session_start = time.time()

    def process_request(self, request: str) -> dict:
        """Processa una richiesta e mostra come i vari sistemi interagiscono"""
        
        # 1. Verifica e ottimizza le performance
        perf_profile = self.performance_optimizer.adapt_performance()
        print(f"\nModalità Performance: {perf_profile['mode']}")
        print(f"Configurazione: {json.dumps(perf_profile, indent=2)}")
        
        # 2. Adatta le risorse
        resources = self.resource_adapter.adapt_resources()
        print(f"\nAllocazione Risorse:")
        print(f"- Memoria Max: {resources.max_memory_usage}GB")
        print(f"- Priorità CPU: {resources.cpu_priority}")
        print(f"- Quota Storage: {resources.storage_quota}GB")
        
        # 3. Memorizza la richiesta
        request_data = {
            "request": request,
            "timestamp": time.time(),
            "performance_mode": perf_profile['mode']
        }
        item_id = self.memory_manager.store_item(request_data, "request")
        
        # 4. Genera risposta nella lingua corrente
        response = self.language_system.get_response("greeting")
        
        # 5. Ottieni statistiche memoria
        memory_stats = self.memory_manager.get_memory_stats()
        print(f"\nStatistiche Memoria:")
        print(json.dumps(memory_stats, indent=2))
        
        return {
            "response": response,
            "performance_mode": perf_profile['mode'],
            "memory_usage": memory_stats['memory_usage']
        }

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
    """Esempio di utilizzo pratico del sistema ottimizzato"""
    assistant = SimpleAssistant()
    
    print("=== Sistema Inizializzato ===")
    print(json.dumps(assistant.get_system_status(), indent=2))
    
    # Esempio 1: Prima richiesta
    print("\n=== Esempio 1: Prima Richiesta ===")
    result = assistant.process_request("Ciao! Come stai oggi?")
    print(f"\nRisposta: {result['response']}")
    
    # Simula carico di sistema
    print("\n=== Simulazione Carico di Sistema ===")
    for i in range(5):
        request = f"Richiesta di test numero {i+1}"
        result = assistant.process_request(request)
        time.sleep(0.5)  # Piccola pausa tra le richieste
    
    # Mostra stato finale
    print("\n=== Stato Finale del Sistema ===")
    print(json.dumps(assistant.get_system_status(), indent=2))

if __name__ == "__main__":
    main()
