"""Test dell'integrazione dei sistemi ALLMA"""

import unittest
from datetime import datetime
import numpy as np
from typing import Dict, List

from Model.incremental_learning.cognitive_evolution_system import (
    CognitiveEvolutionSystem,
    CognitiveStage,
    CognitiveAbility
)
from Model.incremental_learning.meta_learning_system import (
    MetaLearningSystem,
    MetaCognitionLevel
)
from Model.incremental_learning.memory_system import EnhancedMemorySystem
from Model.incremental_learning.contextual_learning_system import ContextualLearningSystem
from Model.incremental_learning.personality_system import PersonalitySystem
from Model.incremental_learning.emotional_social_system import EmotionalSocialSystem

class TestSystemIntegration(unittest.TestCase):
    def setUp(self):
        """Inizializza tutti i sistemi"""
        self.cognitive = CognitiveEvolutionSystem()
        self.meta = MetaLearningSystem()
        self.memory = EnhancedMemorySystem()
        self.contextual = ContextualLearningSystem()
        self.personality = PersonalitySystem()
        self.emotional = EmotionalSocialSystem()
        
    def test_learning_cycle(self):
        """Test completo di un ciclo di apprendimento"""
        # 1. Configurazione del contesto di apprendimento
        context = {
            "type": "problem_solving",
            "domain": "mathematics",
            "complexity": 0.7,
            "valence": 0.6,
            "arousal": 0.4
        }
        
        # 2. Personalità influenza l'approccio
        personality_traits = self.personality.get_current_traits()
        self.assertTrue(len(personality_traits) > 0)
        
        # Modifica il contesto basato sulla personalità
        if personality_traits["openness"] > 0.7:
            context["approach"] = "exploratory"
        else:
            context["approach"] = "structured"
            
        # 3. Sistema Emotivo-Sociale processa
        emotional_state, _ = self.emotional.process_interaction(
            agent_id="test_agent",
            emotional_stimulus={"valence": context["valence"], "arousal": context["arousal"]},
            social_context={"interaction_type": "learning"}
        )
        self.assertTrue(hasattr(emotional_state, "valence"))
            
        # 4. Sistema Cognitivo gestisce l'abilità di base
        cognitive_success = self.cognitive.process_experience({
            "type": "pattern_recognition",
            "difficulty": 0.1,
            "context": context,
            "effectiveness": 0.8
        })
        self.assertGreater(cognitive_success, 0.1)
        
        # 5. Usa l'abilità di base più volte per aumentare l'esperienza
        for _ in range(5):
            cognitive_success = self.cognitive.process_experience({
                "type": "pattern_recognition",
                "difficulty": 0.1,
                "context": context,
                "effectiveness": 0.8
            })
            self.assertGreater(cognitive_success, 0.1)
            
        # 6. Ora prova un'abilità più avanzata
        cognitive_success = self.cognitive.process_experience({
            "type": "analytical_thinking",
            "difficulty": context["complexity"],
            "context": context,
            "effectiveness": 0.7
        })
        self.assertGreater(cognitive_success, 0.1)
        
        # 7. Sistema di Meta-Learning sceglie la strategia
        meta_result = self.meta.learn(
            content="Solving quadratic equations",
            context=context,
            difficulty=context["complexity"]
        )
        self.assertIn("success_level", meta_result)
        self.assertIn("strategy_used", meta_result)
        
        # 8. Sistema di Memoria memorizza l'esperienza
        memory_result = self.memory.process_experience(
            content="Quadratic equations require identifying a, b, and c coefficients",
            emotional_valence=emotional_state.valence,
            context=context
        )
        self.assertTrue(memory_result["stored"])
        
        # 9. Sistema Contestuale crea connessioni
        contextual_result = self.contextual.process_input(
            "Quadratic equations are related to parabolas",
            context
        )
        self.assertIn("connections", contextual_result)
        
        # Verifica l'integrazione completa
        self.verify_system_state()
        
    def test_adaptive_learning(self):
        """Test dell'adattamento del sistema all'apprendimento"""
        levels = [
            {"difficulty": 0.2, "name": "basic"},
            {"difficulty": 0.5, "name": "intermediate"},
            {"difficulty": 0.8, "name": "advanced"}
        ]
        
        results = []
        for level in levels:
            # Prova ogni livello più volte
            for _ in range(5):
                # Usa il sistema cognitivo
                cognitive_success = self.cognitive.process_experience({
                    "type": "analytical_thinking",
                    "difficulty": level["difficulty"],
                    "context": {"level": level["name"]},
                    "effectiveness": 0.7
                })
                
                # Usa il sistema di meta-learning
                meta_result = self.meta.learn(
                    content=f"Learning at {level['name']} level",
                    context={"level": level["name"]},
                    difficulty=level["difficulty"]
                )
                
                results.append({
                    "level": level["name"],
                    "cognitive_success": cognitive_success,
                    "meta_success": meta_result["success_level"]
                })
        
        # Verifica il progresso nell'apprendimento
        self.verify_learning_progress(results)
        
    def test_emotional_influence(self):
        """Test dell'influenza delle emozioni sull'apprendimento"""
        # Test con diverse emozioni
        emotions = [
            {"valence": 0.8, "arousal": 0.6},  # Gioia
            {"valence": 0.3, "arousal": 0.8},  # Ansia
            {"valence": 0.7, "arousal": 0.5}   # Interesse
        ]
        
        for emotion in emotions:
            # Imposta lo stato emotivo
            emotional_state, _ = self.emotional.process_interaction(
                agent_id="test_agent",
                emotional_stimulus=emotion,
                social_context={"interaction_type": "learning"}
            )
            
            # Verifica che lo stato emotivo sia stato processato
            self.assertTrue(hasattr(emotional_state, "valence"))
            
            # Usa un'abilità cognitiva
            cognitive_success = self.cognitive.process_experience({
                "type": "pattern_recognition",
                "difficulty": 0.3,
                "context": {"emotion": emotion},
                "effectiveness": 0.7
            })
            
            # Prova ad apprendere
            meta_result = self.meta.learn(
                content="Emotional learning test",
                context={"emotion": emotion},
                difficulty=0.3  # Difficoltà ridotta per favorire il successo
            )
            
            # Verifica l'impatto delle emozioni
            self.verify_emotional_impact(emotion, cognitive_success, meta_result)
            
    def test_memory_integration(self):
        """Test dell'integrazione della memoria"""
        # Sequenza di apprendimento
        sequence = [
            {
                "content": "Basic arithmetic operations",
                "type": "pattern_recognition",
                "difficulty": 0.2,
                "emotion": {"valence": 0.7, "arousal": 0.4}
            },
            {
                "content": "Algebraic expressions",
                "type": "analytical_thinking",
                "difficulty": 0.4,
                "emotion": {"valence": 0.6, "arousal": 0.5}
            },
            {
                "content": "Complex equations",
                "type": "problem_solving",
                "difficulty": 0.6,
                "emotion": {"valence": 0.5, "arousal": 0.6}
            }
        ]
        
        for item in sequence:
            # 1. Processa lo stato emotivo
            emotional_state, _ = self.emotional.process_interaction(
                agent_id="test_agent",
                emotional_stimulus=item["emotion"],
                social_context={"interaction_type": "learning"}
            )
            
            # 2. Sistema Cognitivo elabora
            cognitive_success = self.cognitive.process_experience({
                "type": item["type"],
                "difficulty": item["difficulty"],
                "context": {"content": item["content"]},
                "effectiveness": 0.7
            })
            
            # 3. Meta-Learning adatta la strategia
            meta_result = self.meta.learn(
                content=item["content"],
                context={"type": item["type"]},
                difficulty=item["difficulty"]
            )
            
            # 4. Memoria memorizza
            memory_result = self.memory.process_experience(
                content=item["content"],
                emotional_valence=emotional_state.valence,
                context={
                    "type": item["type"],
                    "difficulty": item["difficulty"]
                }
            )
            
            # 5. Sistema Contestuale crea connessioni
            contextual_result = self.contextual.process_input(
                item["content"],
                {"type": item["type"]}
            )
            
            # Verifica i risultati
            self.assertGreater(cognitive_success, 0.1)
            self.assertGreater(meta_result["success_level"], 0.3)
            self.assertTrue(memory_result["stored"])
            self.assertIn("connections", contextual_result)
            
    def test_cognitive_evolution(self):
        """Test dell'evoluzione cognitiva nel tempo"""
        # Simula un lungo periodo di apprendimento
        n_iterations = 20
        abilities = ["pattern_recognition", "analytical_thinking", "problem_solving"]
        difficulties = [0.2, 0.4, 0.6]
        
        results = []
        for i in range(n_iterations):
            # Alterna tra diverse abilità e difficoltà
            ability = abilities[i % len(abilities)]
            difficulty = difficulties[i % len(difficulties)]
            
            # 1. Sistema Cognitivo elabora
            cognitive_success = self.cognitive.process_experience({
                "type": ability,
                "difficulty": difficulty,
                "context": {"iteration": i},
                "effectiveness": 0.7
            })
            
            # 2. Meta-Learning adatta la strategia
            meta_result = self.meta.learn(
                content=f"Learning {ability}",
                context={"iteration": i},
                difficulty=difficulty
            )
            
            # 3. Memoria consolida l'esperienza
            memory_result = self.memory.process_experience(
                content=f"Practice {ability}",
                emotional_valence=0.6,  # Valenza emotiva positiva per l'apprendimento
                context={
                    "type": ability,
                    "difficulty": difficulty,
                    "iteration": i
                }
            )
            
            results.append({
                "iteration": i,
                "ability": ability,
                "difficulty": difficulty,
                "cognitive_success": cognitive_success,
                "meta_success": meta_result["success_level"]
            })
            
        # Verifica il progresso cognitivo
        self.verify_cognitive_progress(results)
        
    def verify_system_state(self):
        """Verifica lo stato generale del sistema"""
        # Verifica il sistema cognitivo
        cognitive_state = self.cognitive.get_state()
        self.assertTrue(cognitive_state["total_experiences"] > 0)
        self.assertGreater(cognitive_state["success_rate"], 0.1)
        
        # Verifica il sistema emotivo
        emotional_state = self.emotional.get_state()
        self.assertTrue(len(emotional_state["interactions"]) > 0)
        
        # Verifica il sistema di memoria
        memory_state = self.memory.get_state()
        self.assertTrue(memory_state["total_memories"] > 0)
        
        # Verifica il sistema di meta-learning
        meta_state = self.meta.get_state()
        self.assertTrue(len(meta_state["strategies"]) > 0)
        
        # Verifica il sistema contestuale
        contextual_state = self.contextual.get_state()
        self.assertTrue(len(contextual_state["contexts"]) > 0)
        
    def verify_learning_progress(self, results: List[Dict]):
        """Verifica il progresso nell'apprendimento"""
        # Calcola il tasso di successo per ogni metà dei tentativi
        cognitive_success = [r["cognitive_success"] for r in results]
        meta_success = [r["meta_success"] for r in results]
        
        # Verifica che il tasso di successo migliori nel tempo
        self.assertTrue(
            np.mean(cognitive_success[len(cognitive_success)//2:]) >
            np.mean(cognitive_success[:len(cognitive_success)//2])
        )
        
        # Verifica che il meta-learning migliori
        self.assertTrue(
            np.mean(meta_success[len(meta_success)//2:]) >
            np.mean(meta_success[:len(meta_success)//2])
        )
        
    def verify_emotional_impact(self, emotion: Dict, cognitive_result: float, meta_result: Dict):
        """Verifica l'impatto delle emozioni"""
        if emotion["valence"] > 0.7:
            self.assertGreater(cognitive_result, 0.1)
            self.assertGreater(meta_result["success_level"], 0.3)
            self.assertLess(meta_result["success_level"], 0.9)  # Non troppo alto
        elif emotion["valence"] < 0.4:
            self.assertLess(meta_result["success_level"], 0.8)
            self.assertGreater(meta_result["success_level"], 0.2)  # Non troppo basso
        else:
            self.assertGreater(cognitive_result, 0.1)
            self.assertGreater(meta_result["success_level"], 0.3)
            self.assertLess(meta_result["success_level"], 0.9)  # Non troppo alto
            
    def verify_memory_connections(self, sequence: int, memory_result: Dict, contextual_result: Dict):
        """Verifica le connessioni di memoria"""
        # Verifica che la memoria sia stata memorizzata
        self.assertTrue(memory_result["stored"])
        
        # Verifica che il numero di connessioni aumenti con la sequenza
        if sequence > 0:
            self.assertTrue(len(contextual_result["connections"]) > 0)
            
    def verify_cognitive_progress(self, results: List[Dict]):
        """Verifica il progresso cognitivo"""
        # Calcola il tasso di successo per ogni metà dei tentativi
        cognitive_success = [r["cognitive_success"] for r in results]
        meta_success = [r["meta_success"] for r in results]
        
        # Verifica che il tasso di successo migliori nel tempo
        self.assertTrue(
            np.mean(cognitive_success[len(cognitive_success)//2:]) >
            np.mean(cognitive_success[:len(cognitive_success)//2])
        )
        
        # Verifica che il meta-learning migliori
        self.assertTrue(
            np.mean(meta_success[len(meta_success)//2:]) >
            np.mean(meta_success[:len(meta_success)//2])
        )
        
if __name__ == '__main__':
    unittest.main()
