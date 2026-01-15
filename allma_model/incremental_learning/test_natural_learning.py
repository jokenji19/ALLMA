import unittest
from typing import Dict, List
from incremental_learning.metacognition_system import MetaCognitionSystem
from incremental_learning.emotional_system import EmotionalSystem
from incremental_learning.perception_system import PerceptionSystem
from incremental_learning.cognitive_evolution_system import CognitiveEvolutionSystem

class TestNaturalLearning(unittest.TestCase):
    """Test del processo di apprendimento naturale del sistema"""

    def setUp(self):
        """Inizializza i sistemi per il test"""
        self.metacognition = MetaCognitionSystem()
        self.emotional = EmotionalSystem()
        self.perception = PerceptionSystem()
        self.evolution = CognitiveEvolutionSystem()

    def test_natural_learning_progression(self):
        """Test della progressione naturale dell'apprendimento"""
        print("\n=== Test Progressione Naturale dell'Apprendimento ===\n")

        # Sequenza di esperienze di apprendimento
        learning_sequence = [
            # Fase 1: Osservazione iniziale
            {
                "input": "Osserva attentamente questa nuova situazione",
                "effectiveness": 0.7,
                "expected_ability": "perception"
            },
            # Fase 2: Memorizzazione
            {
                "input": "Memorizza ciò che hai osservato",
                "effectiveness": 0.8,
                "expected_ability": "memory"
            },
            # Fase 3: Apprendimento
            {
                "input": "Studia il pattern che hai identificato",
                "effectiveness": 0.9,
                "expected_ability": "learning"
            },
            # Fase 4: Ragionamento
            {
                "input": "Analizza le relazioni tra i diversi elementi",
                "effectiveness": 0.7,
                "expected_ability": "reasoning"
            },
            # Fase 5: Creatività
            {
                "input": "Immagina nuove possibili connessioni",
                "effectiveness": 0.6,
                "expected_ability": "creativity"
            },
            # Fase 6: Problem Solving
            {
                "input": "Risolvi questo problema usando ciò che hai imparato",
                "effectiveness": 0.8,
                "expected_ability": "problem_solving"
            }
        ]

        # Traccia l'evoluzione delle capacità
        ability_progression = {ability: [] for ability in self.evolution.cognitive_abilities}

        # Processa ogni esperienza
        for i, experience in enumerate(learning_sequence, 1):
            print(f"\nFase {i}: {experience['input']}")
            print(f"Efficacia attesa: {experience['effectiveness']:.2f}")

            # Verifica che l'abilità identificata sia corretta
            identified_ability = self.evolution._get_ability_category(experience)
            self.assertEqual(identified_ability, experience['expected_ability'],
                           f"L'abilità identificata ({identified_ability}) non corrisponde a quella attesa ({experience['expected_ability']})")
            print(f"Abilità stimolata: {identified_ability}")

            # Processa l'esperienza
            result = self.evolution.process_experience(experience)
            print(f"Risultato: {result:.3f}")

            # Traccia i livelli di tutte le abilità
            for ability, level in self.evolution.cognitive_abilities.items():
                ability_progression[ability].append(level)
                print(f"{ability}: {level:.3f}")

        # Verifica che ci sia stato un miglioramento generale
        for ability, progression in ability_progression.items():
            print(f"\nProgressione {ability}: {[f'{x:.3f}' for x in progression]}")
            self.assertGreater(progression[-1], progression[0],
                             f"Nessun miglioramento rilevato per {ability}")

        # Verifica il trasferimento di apprendimento
        for ability, levels in ability_progression.items():
            # Verifica che ci sia stato un incremento anche nelle fasi in cui l'abilità non era direttamente stimolata
            non_target_phases = [i for i, exp in enumerate(learning_sequence) if exp['expected_ability'] != ability]
            if non_target_phases:
                for phase in non_target_phases:
                    if phase > 0:  # Salta la prima fase
                        self.assertGreaterEqual(levels[phase], levels[phase-1],
                                              f"Diminuzione inattesa in {ability} durante la fase {phase+1}")

    def test_learning_rate_decay(self):
        """Test della diminuzione del tasso di apprendimento con l'aumentare dell'expertise"""
        print("\n=== Test Decadimento del Tasso di Apprendimento ===\n")

        # Ripeti la stessa esperienza più volte
        experience = {
            "input": "Studia questo concetto in profondità",
            "effectiveness": 0.9
        }

        improvements = []
        current_level = 0.0

        for i in range(5):
            result = self.evolution.process_experience(experience)
            improvement = result - current_level
            improvements.append(improvement)
            current_level = result

            print(f"Iterazione {i+1}")
            print(f"Livello: {result:.3f}")
            print(f"Miglioramento: {improvement:.3f}")

        # Verifica che i miglioramenti successivi siano progressivamente minori
        for i in range(1, len(improvements)):
            self.assertLess(improvements[i], improvements[i-1],
                          "Il tasso di apprendimento non sta diminuendo come previsto")

    def test_cross_domain_transfer(self):
        """Test del trasferimento di apprendimento tra domini correlati"""
        print("\n=== Test Trasferimento tra Domini ===\n")

        # Sequenza di apprendimento che stimola capacità correlate
        sequence = [
            {
                "input": "Osserva attentamente questo pattern",
                "effectiveness": 0.8,
                "primary": "perception",
                "related": ["memory", "learning"]
            },
            {
                "input": "Memorizza ciò che hai osservato",
                "effectiveness": 0.8,
                "primary": "memory",
                "related": ["learning", "reasoning"]
            }
        ]

        for i, experience in enumerate(sequence, 1):
            print(f"\nEsperienza {i}: {experience['input']}")
            
            # Livelli prima dell'esperienza
            before_levels = self.evolution.cognitive_abilities.copy()
            
            # Processa l'esperienza
            result = self.evolution.process_experience(experience)
            
            print(f"Abilità primaria ({experience['primary']}): {result:.3f}")
            
            # Verifica il trasferimento alle abilità correlate
            for related_ability in experience['related']:
                improvement = self.evolution.cognitive_abilities[related_ability] - before_levels[related_ability]
                print(f"Trasferimento a {related_ability}: {improvement:.3f}")
                self.assertGreater(improvement, 0,
                                 f"Nessun trasferimento rilevato verso {related_ability}")

if __name__ == '__main__':
    unittest.main()
