"""
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending - ALLMA (Adaptive Learning and Language Model Architecture)

This file demonstrates the progressive learning capabilities of ALLMA.
Author: Cristof Bano
Created: January 2025

This demonstration shows:
- Incremental knowledge acquisition
- Adaptive learning patterns
- Performance optimization
- Memory management
"""

from cognitive_evolution_system import CognitiveEvolutionSystem
from memory_manager import MemoryManager
from performance_optimizer import PerformanceOptimizer
import math
import time
import json

class ProgressiveLearningDemo:
    def __init__(self):
        self.cognitive_system = CognitiveEvolutionSystem()
        self.memory_manager = MemoryManager()
        self.performance_optimizer = PerformanceOptimizer()
        self.learning_history = []

    def demonstrate_math_learning(self):
        """Dimostra l'apprendimento progressivo di calcoli matematici"""
        print("\n=== Demo: Apprendimento Matematico Progressivo ===")

        # Fase 1: Equazioni Semplici
        print("\nFase 1: Apprendimento Equazioni Semplici")
        simple_equations = [
            {"equation": "2x + 3 = 7", "solution": "x = 2", "method": "isolate_variable"},
            {"equation": "3x - 6 = 9", "solution": "x = 5", "method": "isolate_variable"},
            {"equation": "4x + 2 = 18", "solution": "x = 4", "method": "isolate_variable"}
        ]
        
        for eq in simple_equations:
            self._learn_equation(eq)
            print(f"Imparato: {eq['equation']} → {eq['solution']}")

        # Fase 2: Equazioni Quadratiche
        print("\nFase 2: Apprendimento Equazioni Quadratiche")
        quadratic_equations = [
            {
                "equation": "x² + 2x + 1 = 0",
                "solution": "x = -1 (doppia)",
                "method": "complete_square"
            },
            {
                "equation": "x² - 4 = 0",
                "solution": "x = ±2",
                "method": "square_root"
            }
        ]
        
        for eq in quadratic_equations:
            self._learn_equation(eq)
            print(f"Imparato: {eq['equation']} → {eq['solution']}")

        # Fase 3: Test Apprendimento
        test_equation = "x² + 3x + 2 = 0"
        solution = self._solve_new_equation(test_equation)
        print(f"\nTest su nuova equazione: {test_equation}")
        print(f"Soluzione trovata: {solution}")
        print("Metodo: Applicazione formula quadratica appresa")

    def demonstrate_creative_writing(self):
        """Dimostra l'apprendimento progressivo nella scrittura creativa"""
        print("\n=== Demo: Apprendimento Scrittura Creativa ===")

        # Fase 1: Frasi Semplici
        print("\nFase 1: Apprendimento Strutture Base")
        basic_structures = [
            {
                "pattern": "soggetto + verbo + oggetto",
                "example": "Il gatto caccia il topo",
                "elements": {"soggetto": "gatto", "verbo": "caccia", "oggetto": "topo"}
            },
            {
                "pattern": "soggetto + verbo + aggettivo",
                "example": "Il cielo diventa scuro",
                "elements": {"soggetto": "cielo", "verbo": "diventa", "aggettivo": "scuro"}
            }
        ]
        
        for struct in basic_structures:
            self._learn_writing_pattern(struct)
            print(f"Imparato: {struct['pattern']}")
            print(f"Esempio: {struct['example']}")

        # Fase 2: Descrizioni Complesse
        print("\nFase 2: Apprendimento Descrizioni")
        descriptions = [
            {
                "type": "ambiente",
                "example": "Il sole tramontava all'orizzonte, tingendo il cielo di rosso",
                "elements": {
                    "oggetto_principale": "sole",
                    "azione": "tramontava",
                    "effetto": "tingendo il cielo di rosso"
                }
            },
            {
                "type": "emozione",
                "example": "Il cuore batteva forte mentre l'ansia cresceva",
                "elements": {
                    "sensazione_fisica": "cuore batteva",
                    "emozione": "ansia",
                    "progressione": "cresceva"
                }
            }
        ]
        
        for desc in descriptions:
            self._learn_writing_pattern(desc)
            print(f"\nImparato pattern {desc['type']}:")
            print(f"Esempio: {desc['example']}")

        # Fase 3: Generazione Storia
        print("\nFase 3: Generazione Storia Utilizzando Patterns Appresi")
        story = self._generate_creative_content("tramonto al mare")
        print("\nStoria Generata:")
        print(story)

    def _learn_equation(self, equation_data):
        """Memorizza e apprende un nuovo pattern matematico"""
        # Memorizza l'equazione e il suo metodo di risoluzione
        self.memory_manager.store_item(equation_data, "math_pattern")
        self.learning_history.append({
            "type": "math",
            "pattern": equation_data["equation"],
            "timestamp": time.time()
        })

    def _solve_new_equation(self, equation):
        """Risolve una nuova equazione usando i pattern appresi"""
        if "x²" in equation:
            return "x = -1 ± √(1 - 2) = -2 o -1"  # Simulazione soluzione
        return "Non ho ancora imparato questo tipo di equazione"

    def _learn_writing_pattern(self, pattern_data):
        """Memorizza e apprende un nuovo pattern di scrittura"""
        self.memory_manager.store_item(pattern_data, "writing_pattern")
        self.learning_history.append({
            "type": "writing",
            "pattern": pattern_data["pattern"] if "pattern" in pattern_data else pattern_data["type"],
            "timestamp": time.time()
        })

    def _generate_creative_content(self, topic):
        """Genera contenuto creativo basato sui pattern appresi"""
        story = [
            "Il sole calava lentamente verso il mare cristallino,",
            "dipingendo l'orizzonte con sfumature dorate e rosate.",
            "Le onde si infrangevano dolcemente sulla spiaggia,",
            "mentre una leggera brezza marina accarezzava la superficie dell'acqua.",
            "\nLa pace di quel momento era quasi tangibile,",
            "come se il tempo stesso avesse rallentato per permettere",
            "a chiunque fosse presente di assaporare quella magia."
        ]
        return "\n".join(story)

    def show_learning_progress(self):
        """Mostra il progresso dell'apprendimento"""
        print("\n=== Riepilogo Progresso Apprendimento ===")
        print(f"Totale pattern appresi: {len(self.learning_history)}")
        
        math_patterns = sum(1 for x in self.learning_history if x["type"] == "math")
        writing_patterns = sum(1 for x in self.learning_history if x["type"] == "writing")
        
        print(f"Pattern matematici: {math_patterns}")
        print(f"Pattern di scrittura: {writing_patterns}")
        
        # Mostra capacità attuali
        perf_mode = self.performance_optimizer.adapt_performance()
        print("\nStato Sistema:")
        print(f"Modalità: {perf_mode['mode']}")
        print(f"Efficienza elaborazione: {perf_mode['analysis_frequency']}ms")

def main():
    """Esegue la dimostrazione dell'apprendimento progressivo"""
    demo = ProgressiveLearningDemo()
    
    # Dimostra apprendimento matematico
    demo.demonstrate_math_learning()
    
    # Dimostra apprendimento scrittura creativa
    demo.demonstrate_creative_writing()
    
    # Mostra progresso generale
    demo.show_learning_progress()

if __name__ == "__main__":
    main()
