"""
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending - ALLMA (Adaptive Learning and Language Model Architecture)

This file provides practical examples of ALLMA system usage.
Author: Cristof Bano
Created: January 2025

This example demonstrates:
- System integration
- Real-world usage scenarios
- Performance optimization
- Resource adaptation
"""

from cognitive_evolution_system import CognitiveEvolutionSystem
from perception_system import PerceptionSystem
from emotional_system import EmotionalSystem
from language_system import LanguageSystem
from performance_optimizer import PerformanceOptimizer
from resource_adapter import ResourceAdapter
from memory_manager import MemoryManager
import time
import json

class IntelligentAssistant:
    def __init__(self):
        # Inizializzazione dei sistemi core
        self.cognitive_system = CognitiveEvolutionSystem()
        self.perception_system = PerceptionSystem()
        self.emotional_system = EmotionalSystem()
        
        # Inizializzazione dei sistemi di ottimizzazione
        self.language_system = LanguageSystem()
        self.performance_optimizer = PerformanceOptimizer()
        self.resource_adapter = ResourceAdapter()
        self.memory_manager = MemoryManager()
        
        # Stato dell'assistente
        self.context = {}
        self.session_start = time.time()

    def process_user_input(self, user_input: str, user_emotion: str = None) -> str:
        """Processa l'input dell'utente e genera una risposta appropriata"""
        # 1. Verifica risorse e ottimizza performance
        perf_profile = self.performance_optimizer.adapt_performance()
        resources = self.resource_adapter.adapt_resources()
        
        # 2. Analizza l'input e il contesto emotivo
        perception_result = self.perception_system.analyze_input(user_input)
        emotional_state = self.emotional_system.analyze_emotion(
            user_input, user_emotion if user_emotion else "neutral"
        )
        
        # 3. Recupera conoscenze rilevanti dalla memoria
        relevant_experiences = self._retrieve_relevant_experiences(user_input)
        
        # 4. Genera risposta cognitiva
        cognitive_response = self.cognitive_system.process_experience({
            "input": user_input,
            "perception": perception_result,
            "emotion": emotional_state,
            "context": self.context,
            "experiences": relevant_experiences
        })
        
        # 5. Formatta risposta nella lingua corrente
        response = self.language_system.format_response(
            cognitive_response["response"],
            cognitive_response["context"]
        )
        
        # 6. Memorizza l'interazione
        self._store_interaction(user_input, response, emotional_state)
        
        return response

    def _retrieve_relevant_experiences(self, query: str) -> list:
        """Recupera esperienze rilevanti dalla memoria"""
        # Genera un ID per la query
        query_hash = self.memory_manager.store_item(
            {"query": query, "timestamp": time.time()},
            category="query"
        )
        
        # Recupera esperienze simili
        experiences = []
        for item_id in self.memory_manager.active_memory.cache:
            item = self.memory_manager.retrieve_item(item_id)
            if item and isinstance(item, dict) and "query" in item:
                similarity = self.cognitive_system.calculate_similarity(
                    query, item["query"]
                )
                if similarity > 0.7:  # Soglia di similarità
                    experiences.append(item)
        
        return experiences

    def _store_interaction(self, user_input: str, response: str, emotion: dict):
        """Memorizza l'interazione per apprendimento futuro"""
        interaction_data = {
            "timestamp": time.time(),
            "user_input": user_input,
            "system_response": response,
            "emotional_context": emotion,
            "performance_mode": self.performance_optimizer.current_mode.value,
            "resource_state": self.resource_adapter.get_current_allocation().__dict__
        }
        
        self.memory_manager.store_item(
            interaction_data,
            category="interaction"
        )

    def get_system_status(self) -> dict:
        """Ottiene lo stato attuale del sistema"""
        return {
            "uptime": time.time() - self.session_start,
            "language": self.language_system.current_language["name"],
            "performance_mode": self.performance_optimizer.current_mode.value,
            "memory_stats": self.memory_manager.get_memory_stats(),
            "resource_allocation": self.resource_adapter.get_current_allocation().__dict__,
            "emotional_state": str(self.emotional_system.current_state)
        }

def main():
    """Esempio di utilizzo pratico del sistema"""
    assistant = IntelligentAssistant()
    
    print("=== Sistema Inizializzato ===")
    print(json.dumps(assistant.get_system_status(), indent=2))
    
    # Esempio 1: Richiesta semplice
    print("\n=== Esempio 1: Richiesta Semplice ===")
    response = assistant.process_user_input(
        "Ciao! Come stai oggi?",
        user_emotion="happy"
    )
    print(f"Utente (felice): Ciao! Come stai oggi?")
    print(f"Assistente: {response}")
    
    # Esempio 2: Richiesta tecnica
    print("\n=== Esempio 2: Richiesta Tecnica ===")
    response = assistant.process_user_input(
        "Puoi spiegarmi come funziona il machine learning?",
        user_emotion="curious"
    )
    print(f"Utente (curioso): Puoi spiegarmi come funziona il machine learning?")
    print(f"Assistente: {response}")
    
    # Esempio 3: Richiesta emotiva
    print("\n=== Esempio 3: Richiesta Emotiva ===")
    response = assistant.process_user_input(
        "Oggi mi sento un po' giù...",
        user_emotion="sad"
    )
    print(f"Utente (triste): Oggi mi sento un po' giù...")
    print(f"Assistente: {response}")
    
    # Mostra stato finale del sistema
    print("\n=== Stato Finale del Sistema ===")
    print(json.dumps(assistant.get_system_status(), indent=2))

if __name__ == "__main__":
    main()
