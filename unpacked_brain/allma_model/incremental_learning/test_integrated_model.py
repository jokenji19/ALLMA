import unittest
from datetime import datetime
from typing import Dict, Any

from .perception_system import PerceptionSystem, InputType
from .metacognition_system import MetaCognitionSystem, CognitiveStrategy
from .emotional_system import EmotionalSystem, EmotionType
from .communication_system import CommunicationSystem, CommunicationMode
from .cognitive_evolution_system import CognitiveEvolutionSystem

class TestIntegratedModel(unittest.TestCase):
    def setUp(self):
        """Inizializza tutti i sistemi"""
        self.perception = PerceptionSystem()
        self.metacognition = MetaCognitionSystem()
        self.emotional = EmotionalSystem()
        self.communication = CommunicationSystem()
        self.evolution = CognitiveEvolutionSystem()
        
    def test_process_text_input(self):
        """Test dell'elaborazione di input testuale"""
        # Input di test
        test_input = "Sono felice di imparare cose nuove sulla programmazione"
        
        # 1. Processo percettivo
        percept = self.perception.process_input(test_input, InputType.TEXT)
        self.assertIsNotNone(percept)
        print("\n=== Test Processo Percettivo ===")
        print(f"Confidenza: {percept.confidence:.2f}")
        print(f"Pattern rilevati: {len(percept.patterns)}")
        
        # 2. Analisi metacognitiva
        process_data = {
            "complexity": 0.6,
            "accuracy": 0.8,
            "consistency": 0.7,
            "completeness": 0.9,
            "speed": 0.8,
            "resource_usage": 0.4
        }
        insight = self.metacognition.monitor_cognitive_process(process_data)
        print("\n=== Test Analisi Metacognitiva ===")
        print(f"Strategia selezionata: {insight.strategy.value}")
        print(f"Confidenza: {insight.confidence:.2f}")
        print(f"Efficacia: {insight.effectiveness:.2f}")
        
        # 3. Risposta emotiva
        emotion = self.emotional.process_stimulus(test_input)
        print("\n=== Test Risposta Emotiva ===")
        print(f"Emozione dominante: {emotion.primary_emotion.value}")
        print(f"Intensità: {emotion.intensity:.2f}")
        print(f"Valenza: {emotion.valence:.2f}")
        
        # 4. Generazione risposta
        response = self.communication.generate_response(
            input_text=test_input,
            emotion=emotion,
            mode=CommunicationMode.NATURAL
        )
        print("\n=== Test Generazione Risposta ===")
        print(f"Risposta: {response.content}")
        print(f"Stile: {response.style}")
        
        # 5. Evoluzione cognitiva
        evolution_data = {
            "input": test_input,
            "percept": percept,
            "insight": insight,
            "emotion": emotion,
            "response": response
        }
        evolution = self.evolution.process_experience(evolution_data)
        print("\n=== Test Evoluzione Cognitiva ===")
        print(f"Abilità migliorate: {evolution.improved_abilities}")
        print(f"Nuove connessioni: {evolution.new_connections}")
        
    def test_learning_scenario(self):
        """Test di uno scenario di apprendimento completo"""
        print("\n=== Test Scenario di Apprendimento ===")
        
        # 1. Fase iniziale di apprendimento
        topic = "Python Programming"
        self.metacognition.reflect_on_learning(topic, time_spent=1.0, outcome=0.6)
        
        # 2. Pianificazione strategia
        plan = self.metacognition.plan_learning_strategy(topic)
        print("\nPiano di Apprendimento:")
        print(f"Topic: {plan['topic']}")
        print(f"Gap di comprensione: {plan['understanding_gap']:.2f}")
        print(f"Efficienza temporale: {plan['time_efficiency']:.2f}")
        print(f"Strategie raccomandate: {[s.value for s in plan['recommended_strategies']]}")
        
        # 3. Applicazione della strategia
        test_input = "Sto imparando le classi e gli oggetti in Python"
        process_data = {
            "complexity": 0.7,
            "accuracy": 0.8,
            "consistency": 0.8,
            "completeness": 0.7,
            "speed": 0.6,
            "resource_usage": 0.5
        }
        
        # Processo percettivo
        percept = self.perception.process_input(test_input, InputType.TEXT)
        
        # Analisi metacognitiva
        insight = self.metacognition.monitor_cognitive_process(process_data)
        
        # Risposta emotiva
        emotion = self.emotional.process_stimulus(test_input)
        
        print("\nStato Emotivo durante l'Apprendimento:")
        print(f"Emozione: {emotion.primary_emotion.value}")
        print(f"Intensità: {emotion.intensity:.2f}")
        
        # 4. Valutazione del progresso
        self.metacognition.reflect_on_learning(topic, time_spent=1.0, outcome=0.8)
        progress = self.metacognition.learning_progress[topic]
        
        print("\nProgresso dell'Apprendimento:")
        print(f"Livello di comprensione: {progress.understanding_level:.2f}")
        print(f"Tempo totale: {progress.time_spent:.1f} ore")
        print(f"Numero di sessioni: {len(progress.outcomes)}")
        
    def test_emotional_response(self):
        """Test delle risposte emotive in diversi scenari"""
        print("\n=== Test Risposte Emotive ===")
        
        scenarios = [
            "Ho risolto un bug complesso!",
            "Non riesco a capire questo errore...",
            "Il codice funziona perfettamente",
            "Il sistema continua a crashare"
        ]
        
        for scenario in scenarios:
            emotion = self.emotional.process_stimulus(scenario)
            response = self.communication.generate_response(
                input_text=scenario,
                emotion=emotion,
                mode=CommunicationMode.EMPATHETIC
            )
            
            print(f"\nScenario: {scenario}")
            print(f"Emozione: {emotion.primary_emotion.value}")
            print(f"Intensità: {emotion.intensity:.2f}")
            print(f"Risposta: {response.content}")
            
    def test_cognitive_evolution(self):
        """Test dell'evoluzione cognitiva nel tempo"""
        print("\n=== Test Evoluzione Cognitiva ===")
        
        # Simula una serie di esperienze
        experiences = [
            "Sto imparando un nuovo linguaggio di programmazione",
            "Ho implementato un algoritmo complesso",
            "Sto debuggando un errore difficile",
            "Ho ottimizzato il codice con successo"
        ]
        
        for exp in experiences:
            # Processo l'esperienza attraverso tutti i sistemi
            percept = self.perception.process_input(exp, InputType.TEXT)
            
            process_data = {
                "complexity": 0.7,
                "accuracy": 0.8,
                "consistency": 0.8,
                "completeness": 0.7,
                "speed": 0.6,
                "resource_usage": 0.5
            }
            insight = self.metacognition.monitor_cognitive_process(process_data)
            
            emotion = self.emotional.process_stimulus(exp)
            
            response = self.communication.generate_response(
                input_text=exp,
                emotion=emotion,
                mode=CommunicationMode.NATURAL
            )
            
            evolution_data = {
                "input": exp,
                "percept": percept,
                "insight": insight,
                "emotion": emotion,
                "response": response
            }
            
            evolution = self.evolution.process_experience(evolution_data)
            
            print(f"\nEsperienza: {exp}")
            print(f"Abilità migliorate: {evolution.improved_abilities}")
            print(f"Nuove connessioni: {evolution.new_connections}")
            print(f"Livello cognitivo: {evolution.cognitive_level:.2f}")

if __name__ == '__main__':
    unittest.main()
