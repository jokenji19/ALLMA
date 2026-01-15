from language_system import LanguageSystem
from performance_optimizer import PerformanceOptimizer
from resource_adapter import ResourceAdapter
from memory_manager import MemoryManager
import time
import json

class RealWorldExamples:
    def __init__(self):
        # Inizializza i sistemi core
        self.language_system = LanguageSystem()
        self.performance_optimizer = PerformanceOptimizer()
        self.resource_adapter = ResourceAdapter()
        self.memory_manager = MemoryManager()

    def show_personal_assistant_capabilities(self):
        """Esempio 1: Capacità di Assistente Personale"""
        print("\n=== Esempio 1: Assistente Personale ===")
        print("Scenario: Gestione agenda e preferenze personali")
        
        # Memorizza preferenze utente
        preferences = {
            "morning_meetings": True,
            "lunch_time": "13:00",
            "exercise_time": "17:00",
            "language": "it",
            "notification_style": "minimal"
        }
        
        # Adatta le risorse per l'elaborazione
        perf_mode = self.performance_optimizer.adapt_performance()
        print(f"\nModalità Operativa: {perf_mode['mode']}")
        print(f"Configurazione Performance:")
        print(f"- Frequenza analisi: {perf_mode['analysis_frequency']}ms")
        print(f"- Task concorrenti: {perf_mode['max_concurrent_tasks']}")
        
        # Memorizza e recupera dati
        pref_id = self.memory_manager.store_item(preferences, "user_preferences")
        stored_prefs = self.memory_manager.retrieve_item(pref_id)
        
        print("\nPreferenze Utente Elaborate:")
        print(f"- Riunioni preferite: Mattina")
        print(f"- Pausa pranzo: {stored_prefs['lunch_time']}")
        print(f"- Esercizio: {stored_prefs['exercise_time']}")

    def show_adaptive_learning(self):
        """Esempio 2: Apprendimento Adattivo"""
        print("\n=== Esempio 2: Apprendimento Adattivo ===")
        print("Scenario: Adattamento alle abitudini dell'utente")
        
        # Simula pattern di utilizzo
        usage_patterns = [
            {"time": "09:00", "activity": "email", "duration": 30},
            {"time": "11:00", "activity": "meeting", "duration": 60},
            {"time": "14:00", "activity": "focus_work", "duration": 120},
        ]
        
        # Adatta risorse in base al pattern
        for pattern in usage_patterns:
            self.memory_manager.store_item(pattern, "usage_pattern")
            resources = self.resource_adapter.adapt_resources()
            
            print(f"\nAttività: {pattern['activity']}")
            print(f"Allocazione Risorse:")
            print(f"- CPU Priority: {resources.cpu_priority}")
            print(f"- Memory Buffer: {resources.max_memory_usage}GB")
            print(f"- Batch Size: {resources.batch_size}")

    def show_language_processing(self):
        """Esempio 3: Elaborazione Linguistica"""
        print("\n=== Esempio 3: Elaborazione Linguistica ===")
        print("Scenario: Adattamento a diverse lingue")
        
        messages = {
            "it": "Come posso aiutarti oggi?",
            "en": "How can I help you today?",
            "es": "¿Cómo puedo ayudarte hoy?"
        }
        
        for lang_code in messages.keys():
            self.language_system.set_language(lang_code)
            response = self.language_system.get_response("greeting")
            print(f"\nLingua: {self.language_system.current_language['name']}")
            print(f"Input: {messages[lang_code]}")
            print(f"Risposta: {response}")

    def show_resource_management(self):
        """Esempio 4: Gestione Risorse"""
        print("\n=== Esempio 4: Gestione Risorse ===")
        print("Scenario: Adattamento a diverse condizioni del dispositivo")
        
        # Simula diversi stati del dispositivo
        device_states = [
            {"cpu": 80, "memory": 75, "battery": 100},  # Alto carico
            {"cpu": 30, "memory": 40, "battery": 50},   # Carico medio
            {"cpu": 90, "memory": 85, "battery": 15}    # Critico
        ]
        
        for state in device_states:
            print(f"\nStato Dispositivo:")
            print(f"- CPU: {state['cpu']}%")
            print(f"- Memoria: {state['memory']}%")
            print(f"- Batteria: {state['battery']}%")
            
            perf_mode = self.performance_optimizer.adapt_performance()
            resources = self.resource_adapter.adapt_resources()
            
            print(f"Risposta del Sistema:")
            print(f"- Modalità: {perf_mode['mode']}")
            print(f"- Allocazione CPU: Priority {resources.cpu_priority}")
            print(f"- Buffer Memoria: {resources.max_memory_usage}GB")

def main():
    """Esegue gli esempi del mondo reale"""
    examples = RealWorldExamples()
    
    # Mostra le capacità in scenari reali
    examples.show_personal_assistant_capabilities()
    examples.show_adaptive_learning()
    examples.show_language_processing()
    examples.show_resource_management()

if __name__ == "__main__":
    main()
