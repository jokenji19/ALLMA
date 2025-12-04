import unittest
from datetime import datetime, timedelta
from typing import Dict, List

from .perception_system import PerceptionSystem, InputType, Pattern, PatternType
from .metacognition_system import MetaCognitionSystem, CognitiveStrategy
from .emotional_system import EmotionalSystem, EmotionType
from .communication_system import CommunicationSystem, CommunicationMode
from .cognitive_evolution_system import CognitiveEvolutionSystem

class TestAdvancedScenarios(unittest.TestCase):
    def setUp(self):
        """Inizializza tutti i sistemi"""
        self.perception = PerceptionSystem()
        self.metacognition = MetaCognitionSystem()
        self.emotional = EmotionalSystem()
        self.communication = CommunicationSystem()
        self.evolution = CognitiveEvolutionSystem()
        
    def test_complex_learning_scenario(self):
        """Test di uno scenario di apprendimento complesso con multiple interazioni"""
        print("\n=== Test Scenario di Apprendimento Complesso ===")
        
        # Sequenza di input che simula un processo di apprendimento
        learning_sequence = [
            "Iniziamo a studiare gli algoritmi di machine learning",
            "Non capisco bene il concetto di gradient descent",
            "Ah, ora ho capito! È come scendere una collina cercando il punto più basso",
            "Questo esempio pratico mi ha davvero aiutato a comprendere",
            "Posso applicare questo concetto ad altri problemi di ottimizzazione"
        ]
        
        understanding_levels = []
        emotional_states = []
        cognitive_levels = []
        
        for input_text in learning_sequence:
            # Processo percettivo
            percept = self.perception.process_input(input_text, InputType.TEXT)
            print(f"\nInput: {input_text}")
            print(f"Confidenza Percettiva: {percept.confidence:.2f}")
            
            # Analisi metacognitiva
            self.metacognition.reflect_on_learning("machine_learning", 0.5, 0.7)
            strategy = self.metacognition.plan_learning_strategy("machine_learning")
            understanding_levels.append(
                self.metacognition.get_understanding_level("machine_learning")
            )
            print(f"Livello di Comprensione: {understanding_levels[-1]:.2f}")
            
            # Processo emotivo
            emotion = self.emotional.process_stimulus(input_text, valence=0.5)
            emotional_states.append(emotion)
            print(f"Emozione: {emotion.primary_emotion.value}")
            print(f"Intensità: {emotion.intensity:.2f}")
            
            # Generazione risposta
            response = self.communication.generate_response(
                input_text=input_text,
                emotion=emotion,
                mode=CommunicationMode.EMPATHETIC
            )
            print(f"Risposta: {response.content}")
            
            # Evoluzione cognitiva
            evolution_result = self.evolution.process_experience({
                "input": input_text,
                "percept": percept,
                "emotion": emotion,
                "response": response
            })
            cognitive_levels.append(evolution_result)
            print(f"Livello Cognitivo: {evolution_result:.2f}")
            
        # Verifica il progresso
        self.assertGreater(understanding_levels[-1], understanding_levels[0])
        self.assertGreater(cognitive_levels[-1], cognitive_levels[0])
        
    def test_emotional_adaptation(self):
        """Test dell'adattamento emotivo in risposta a diversi stimoli"""
        print("\n=== Test Adattamento Emotivo ===")
        
        # Sequenza di stimoli emotivi
        emotional_sequence = [
            ("Ho trovato un bug critico nel sistema", EmotionType.FEAR),
            ("Sto lavorando alla soluzione", EmotionType.ANTICIPATION),
            ("Ho identificato la causa del problema", EmotionType.JOY),
            ("La soluzione funziona!", EmotionType.JOY),
            ("Il sistema è più stabile di prima", EmotionType.TRUST)
        ]
        
        emotional_responses = []
        for stimulus, expected_emotion in emotional_sequence:
            # Processo emotivo
            emotion = self.emotional.process_stimulus(stimulus, valence=self._get_valence(expected_emotion))
            emotional_responses.append(emotion)
            
            print(f"\nStimolo: {stimulus}")
            print(f"Emozione Attesa: {expected_emotion.value}")
            print(f"Emozione Rilevata: {emotion.primary_emotion.value}")
            print(f"Intensità: {emotion.intensity:.2f}")
            print(f"Valenza: {emotion.valence:.2f}")
            
            # Verifica la coerenza emotiva
            self.assertEqual(emotion.primary_emotion, expected_emotion)
            
    def test_pattern_recognition(self):
        """Test del riconoscimento di pattern in una sequenza di input"""
        print("\n=== Test Riconoscimento Pattern ===")
        
        # Sequenza di input con pattern ricorrenti
        input_sequence = [
            "Il sistema mostra un errore di memoria",
            "L'errore si verifica dopo 1000 iterazioni",
            "Un altro processo mostra lo stesso errore di memoria",
            "Anche questo crash avviene dopo circa 1000 iterazioni",
            "Sembra esserci un pattern nei crash di memoria"
        ]
        
        patterns_found = []
        for input_text in input_sequence:
            # Processo percettivo
            percept = self.perception.process_input(input_text, InputType.TEXT)
            
            print(f"\nInput: {input_text}")
            print(f"Pattern rilevati: {len(percept.patterns)}")
            
            # Memorizza i pattern trovati
            patterns_found.extend(percept.patterns)
            
        # Verifica che siano stati trovati pattern significativi
        self.assertGreater(len(patterns_found), 0)
        
    def test_cognitive_transfer(self):
        """Test del trasferimento di conoscenze tra domini diversi"""
        print("\n=== Test Trasferimento Cognitivo ===")
        
        # Sequenza di apprendimento in domini diversi
        learning_sequence = [
            ("programming", "Ho imparato a usare gli array in Python", 0.8),
            ("programming", "Gli array sono strutture dati lineari", 0.7),
            ("math", "Le matrici sono array bidimensionali", 0.8),
            ("math", "Posso applicare le operazioni degli array alle matrici", 0.9),
            ("physics", "Le matrici sono utili per i calcoli di meccanica quantistica", 0.7)
        ]
        
        # Traccia la conoscenza iniziale per ogni dominio
        initial_knowledge = {}
        final_knowledge = {}
        
        for domain, input_text, effectiveness in learning_sequence:
            # Registra la conoscenza iniziale del dominio
            if domain not in initial_knowledge:
                initial_knowledge[domain] = self.metacognition.get_understanding_level(domain)
            
            # Processo di apprendimento
            self.metacognition.reflect_on_learning(domain, 1.0, effectiveness)
            
            # Evoluzione cognitiva
            evolution = self.evolution.process_experience({
                "input": input_text,
                "domain": domain,
                "effectiveness": effectiveness
            })
            
            # Aggiorna la conoscenza finale del dominio
            final_knowledge[domain] = self.metacognition.get_understanding_level(domain)
            
            print(f"\nDominio: {domain}")
            print(f"Input: {input_text}")
            print(f"Efficacia: {effectiveness:.2f}")
            print(f"Livello di Comprensione: {final_knowledge[domain]:.2f}")
            
        # Verifica il trasferimento di conoscenza tra domini correlati
        print("\nTrasferimento di conoscenza tra domini:")
        for domain in ["programming", "math", "physics"]:
            print(f"{domain}: {initial_knowledge[domain]:.2f} -> {final_knowledge[domain]:.2f}")
            self.assertGreater(final_knowledge[domain], initial_knowledge[domain],
                             f"Il dominio {domain} non mostra un incremento di conoscenza")
            
        # Verifica che la conoscenza si sia trasferita tra domini correlati
        self.assertGreater(final_knowledge["math"], initial_knowledge["math"],
                          "La conoscenza non si è trasferita da programming a math")
        self.assertGreater(final_knowledge["physics"], initial_knowledge["physics"],
                          "La conoscenza non si è trasferita da math a physics")
            
    def test_adaptive_communication(self):
        """Test dell'adattamento della comunicazione in base al contesto"""
        print("\n=== Test Comunicazione Adattiva ===")
        
        # Scenari di comunicazione con diversi contesti
        communication_scenarios = [
            {
                "input": "Come funziona questo algoritmo?",
                "emotion": EmotionType.ANTICIPATION,
                "mode": CommunicationMode.TECHNICAL
            },
            {
                "input": "Non riesco a risolvere questo bug...",
                "emotion": EmotionType.SADNESS,
                "mode": CommunicationMode.EMPATHETIC
            },
            {
                "input": "Ottimo lavoro sul refactoring!",
                "emotion": EmotionType.JOY,
                "mode": CommunicationMode.NATURAL
            }
        ]
        
        for scenario in communication_scenarios:
            # Processo emotivo
            emotion = self.emotional.process_stimulus(scenario["input"], valence=self._get_valence(scenario["emotion"]))
            
            # Generazione risposta
            response = self.communication.generate_response(
                input_text=scenario["input"],
                emotion=emotion,
                mode=scenario["mode"]
            )
            
            print(f"\nScenario: {scenario['input']}")
            print(f"Modalità: {scenario['mode'].value}")
            print(f"Emozione: {emotion.primary_emotion.value}")
            print(f"Risposta: {response.content}")
            
            # Verifica l'appropriatezza della risposta
            self.assertEqual(response.style, scenario["mode"])

    def _get_valence(self, emotion: EmotionType) -> float:
        """Mappa le emozioni a valori di valenza"""
        emotion_valences = {
            EmotionType.JOY: 0.8,
            EmotionType.SADNESS: -0.6,
            EmotionType.ANGER: -0.8,
            EmotionType.FEAR: -0.8,
            EmotionType.SURPRISE: 0.4,
            EmotionType.TRUST: 0.6,
            EmotionType.ANTICIPATION: 0.4,
            EmotionType.DISGUST: -0.7,
            EmotionType.NEUTRAL: 0.0
        }
        return emotion_valences.get(emotion, 0.0)

if __name__ == '__main__':
    unittest.main()
