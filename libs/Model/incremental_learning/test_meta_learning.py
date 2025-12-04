import unittest
from datetime import datetime
import os
import numpy as np
from Model.incremental_learning.meta_learning_system import (
    MetaLearningSystem,
    LearningStrategy,
    LearningExperience,
    MetaCognitionLevel,
    StrategyOptimizer
)

class TestMetaLearningSystem(unittest.TestCase):
    def setUp(self):
        self.system = MetaLearningSystem()
        
    def test_initial_state(self):
        """Verifica lo stato iniziale del sistema"""
        self.assertEqual(self.system.metacognition_level, MetaCognitionLevel.MONITORING)
        self.assertTrue(len(self.system.strategies) > 0)
        self.assertEqual(len(self.system.experiences), 0)
        
    def test_learning_process(self):
        """Verifica il processo di apprendimento"""
        result = self.system.learn(
            content="Test learning content",
            context={"type": "basic"},
            difficulty=0.5
        )
        
        self.assertIn("success_level", result)
        self.assertIn("strategy_used", result)
        self.assertIn("time_taken", result)
        self.assertTrue(0 <= result["success_level"] <= 1)
        
    def test_strategy_selection(self):
        """Verifica la selezione delle strategie"""
        strategy = self.system._select_best_strategy(
            context={"type": "basic"},
            difficulty=0.5
        )
        
        self.assertIsInstance(strategy, LearningStrategy)
        self.assertTrue(hasattr(strategy, "name"))
        self.assertTrue(hasattr(strategy, "success_rate"))
        
    def test_strategy_optimization(self):
        """Verifica l'ottimizzazione delle strategie"""
        optimizer = StrategyOptimizer()
        
        # Crea alcune strategie di test
        strategies = [
            LearningStrategy(
                name=f"test_strategy_{i}",
                parameters={"param1": 0.5, "param2": 0.7},
                success_rate=0.5 + i * 0.1,
                usage_count=10,
                last_used=datetime.now(),
                effectiveness_history=[0.5 + i * 0.1] * 5,
                context_types={"test"},
                preferred_contexts={"test"},
                optimal_difficulty=0.5,
                experience_points=0.0,
                current_level=1
            )
            for i in range(3)
        ]
        
        # Addestra l'ottimizzatore
        target_scores = [0.6, 0.7, 0.8]
        loss = optimizer.train(strategies, target_scores)
        
        self.assertIsInstance(loss, float)
        
    def test_reflection_process(self):
        """Verifica il processo di riflessione"""
        # Genera alcune esperienze
        for _ in range(10):
            self.system.learn(
                content=f"Test content {_}",
                context={"type": "basic"},
                difficulty=0.5
            )
            
        reflection = self.system._reflect_on_learning()
        
        self.assertIn("insights", reflection)
        self.assertIn("metacognition_level", reflection)
        self.assertIn("timestamp", reflection)
        
    def test_learning_trends(self):
        """Verifica l'analisi dei trend di apprendimento"""
        # Crea alcune esperienze con trend positivo
        experiences = [
            LearningExperience(
                content=f"Test {i}",
                strategy_used="test_strategy",
                success_level=0.5 + i * 0.05,  # Trend crescente
                time_taken=10.0 - i * 0.5,     # Trend decrescente (più veloce)
                context={"type": "test"},
                timestamp=datetime.now(),
                feedback=None,
                difficulty=0.5
            )
            for i in range(10)
        ]
        
        trends = self.system._analyze_learning_trends(experiences)
        
        self.assertIn("success_trend", trends)
        self.assertIn("speed_trend", trends)
        self.assertIn("consistency", trends)
        
    def test_metacognition_evolution(self):
        """Verifica l'evoluzione del livello di metacognizione"""
        # Simula performance eccellenti
        insights = {
            "overall_success_rate": 0.95,
            "top_strategies": ["strategy1", "strategy2", "strategy3"],
            "struggling_strategies": [],
            "learning_trends": {
                "success_trend": "improving",
                "speed_trend": "faster",
                "consistency": 0.9
            }
        }
        
        initial_level = self.system.metacognition_level
        self.system._update_metacognition_level(insights)
        
        # Verifica che il livello sia aumentato
        self.assertTrue(
            self.system.metacognition_level.value > initial_level.value,
            "Il livello di metacognizione dovrebbe aumentare con performance eccellenti"
        )
        
    def test_system_persistence(self):
        """Verifica il salvataggio e caricamento dello stato"""
        # Genera alcuni dati
        for _ in range(5):
            self.system.learn(
                content=f"Test content {_}",
                context={"type": "basic"},
                difficulty=0.5
            )
            
        # Salva lo stato
        test_file = "test_meta_learning_state.json"
        self.system.save_state(test_file)
        
        # Crea un nuovo sistema e carica lo stato
        new_system = MetaLearningSystem()
        new_system.load_state(test_file)
        
        # Verifica che lo stato sia stato preservato
        self.assertEqual(
            new_system.metacognition_level,
            self.system.metacognition_level
        )
        self.assertEqual(
            len(new_system.experiences),
            len(self.system.experiences)
        )
        
        # Pulisci
        os.remove(test_file)
        
    def test_learning_summary(self):
        """Verifica il sommario dell'apprendimento"""
        # Genera alcuni dati
        for _ in range(5):
            self.system.learn(
                content=f"Test content {_}",
                context={"type": "basic"},
                difficulty=0.5
            )
            
        summary = self.system.get_learning_summary()
        
        self.assertIn("total_experiences", summary)
        self.assertIn("metacognition_level", summary)
        self.assertIn("strategies", summary)
        self.assertIn("recent_performance", summary)
        self.assertIn("reflections", summary)
        
    def _show_learning_result(self, title: str, result: dict, content: str):
        """Mostra i risultati di un'esperienza di apprendimento"""
        print(f"\n=== {title} ===")
        print(f"Contenuto: {content}")
        print(f"Strategia: {result['strategy_used']}")
        print(f"Successo: {result['success_level']:.2f}")
        print(f"Tempo: {result['time_taken']:.1f} secondi")
        
    def test_practical_learning_examples(self):
        """Test con esempi pratici di apprendimento in diversi contesti"""
        
        # 1. Esempio: Imparare una nuova lingua (Italiano)
        language_result = self.system.learn(
            content="Ciao = Hello, Grazie = Thank you, Per favore = Please",
            context={
                "type": "language",
                "subject": "italian",
                "method": "vocabulary",
                "learning_style": "visual",
                "preferred_strategy": "repetition"  # Strategia forzata
            },
            difficulty=0.3
        )
        self._show_learning_result(
            "Esempio 1: Apprendimento Linguistico",
            language_result,
            "Vocabolario base italiano"
        )
        
        # 2. Esempio: Programmazione Python
        coding_result = self.system.learn(
            content="""
            def fibonacci(n):
                if n <= 1:
                    return n
                return fibonacci(n-1) + fibonacci(n-2)
            """,
            context={
                "type": "programming",
                "subject": "python",
                "concept": "recursion",
                "learning_style": "practical",
                "preferred_strategy": "practice"  # Strategia forzata
            },
            difficulty=0.7
        )
        self._show_learning_result(
            "Esempio 2: Programmazione",
            coding_result,
            "Funzione ricorsiva Fibonacci"
        )
        
        # 3. Esempio: Teoria musicale
        music_result = self.system.learn(
            content="La scala maggiore è composta da: Do Re Mi Fa Sol La Si Do",
            context={
                "type": "music",
                "subject": "theory",
                "concept": "scales",
                "learning_style": "auditory",
                "preferred_strategy": "elaboration"  # Strategia forzata
            },
            difficulty=0.5
        )
        self._show_learning_result(
            "Esempio 3: Teoria Musicale",
            music_result,
            "Scala maggiore"
        )
        
        # 4. Esempio di Problem Solving
        problem_result = self.system.learn(
            content="Per ottimizzare un algoritmo, analizza: 1) Complessità temporale, 2) Uso memoria, 3) Input/Output",
            context={
                "type": "problem_solving",
                "subject": "algorithms",
                "method": "analysis",
                "learning_style": "analytical",
                "preferred_strategy": "reflection"  # Strategia forzata
            },
            difficulty=0.8
        )
        self._show_learning_result(
            "Esempio 4: Problem Solving",
            problem_result,
            "Ottimizzazione algoritmi"
        )
        
        # 5. Esempio di Apprendimento motorio (Sport)
        sport_result = self.system.learn(
            content="Sequenza per il servizio nel tennis: 1) Posizione, 2) Lancio palla, 3) Rotazione, 4) Impatto",
            context={
                "type": "motor_learning",
                "subject": "tennis",
                "skill": "serve",
                "learning_style": "kinesthetic",
                "preferred_strategy": "practice"  # Strategia forzata
            },
            difficulty=0.6
        )
        self._show_learning_result(
            "Esempio 5: Apprendimento Motorio",
            sport_result,
            "Servizio nel tennis"
        )
        
        # Analisi delle strategie utilizzate
        strategies_used = {
            language_result['strategy_used'],
            coding_result['strategy_used'],
            music_result['strategy_used'],
            problem_result['strategy_used'],
            sport_result['strategy_used']
        }
        
        print("\n=== Analisi dell'Apprendimento ===")
        print(f"Numero di strategie diverse utilizzate: {len(strategies_used)}")
        print("Strategie:", ", ".join(strategies_used))
        
        # Calcola l'efficacia media per ogni tipo di contesto
        context_results = {
            "language": language_result['success_level'],
            "programming": coding_result['success_level'],
            "music": music_result['success_level'],
            "problem_solving": problem_result['success_level'],
            "motor_learning": sport_result['success_level']
        }
        
        print("\n=== Efficacia per Contesto ===")
        for context, success in sorted(context_results.items(), key=lambda x: x[1], reverse=True):
            print(f"{context}: {success:.2f} successo")
            
        # Analisi dettagliata per ogni contesto
        print("\n=== Analisi Dettagliata per Contesto ===")
        for context, result in [
            ("Linguistico", language_result),
            ("Programmazione", coding_result),
            ("Musicale", music_result),
            ("Problem Solving", problem_result),
            ("Motorio", sport_result)
        ]:
            print(f"\n{context}:")
            print(f"- Strategia: {result['strategy_used']}")
            print(f"- Successo: {result['success_level']:.2f}")
            print(f"- Tempo: {result['time_taken']:.1f} secondi")
            print(f"- Difficoltà: {result.get('difficulty', 'N/A')}")
        
        # Verifica che il sistema usi strategie appropriate
        self.assertTrue(len(strategies_used) >= 3,
                       "Il sistema dovrebbe usare almeno 3 strategie diverse")
        
        # Verifica che il successo medio sia accettabile
        avg_success = sum(context_results.values()) / len(context_results)
        self.assertTrue(avg_success > 0.5,
                       f"Il successo medio ({avg_success:.2f}) dovrebbe essere superiore a 0.5")
        
        # Mostra il sommario dell'apprendimento
        summary = self.system.get_learning_summary()
        print("\n=== Sommario Generale ===")
        print(f"Esperienze totali: {summary['total_experiences']}")
        print(f"Livello metacognitivo: {summary['metacognition_level']}")
        
        if 'recent_performance' in summary:
            perf = summary['recent_performance']
            print(f"\nPerformance recente:")
            print(f"- Tasso di successo medio: {perf['success_rate']:.2f}")
            print(f"- Tempo medio: {perf['average_time']:.1f} secondi")
            print(f"- Strategia più usata: {perf['most_used_strategy']}")
            
        # Analisi delle correlazioni
        print("\n=== Correlazioni ===")
        print("Difficoltà vs Successo:")
        difficulties = [0.3, 0.7, 0.5, 0.8, 0.6]
        successes = [r['success_level'] for r in [language_result, coding_result, music_result, problem_result, sport_result]]
        correlation = np.corrcoef(difficulties, successes)[0,1]
        print(f"Coefficiente di correlazione: {correlation:.2f}")
        
        # Suggerimenti per il miglioramento
        print("\n=== Suggerimenti per il Miglioramento ===")
        for context, result in context_results.items():
            if result < 0.6:
                print(f"- {context}: Considerare strategie alternative o più pratica")
            elif result < 0.7:
                print(f"- {context}: Buon risultato, ma c'è spazio per miglioramento")
            else:
                print(f"- {context}: Ottimo risultato, mantenere questa strategia")
                
    def test_learning_examples(self):
        """Test con esempi pratici di diverse strategie di apprendimento"""
        # 1. Esempio di apprendimento base con ripetizione
        basic_result = self.system.learn(
            content="2 + 2 = 4",
            context={"type": "basic", "subject": "math"},
            difficulty=0.2
        )
        self._show_learning_result(
            "Esempio 1: Apprendimento Base",
            basic_result,
            "Aritmetica semplice"
        )
        
        # 2. Esempio di apprendimento con elaborazione
        elaboration_result = self.system.learn(
            content="Le equazioni di secondo grado hanno la forma ax² + bx + c = 0",
            context={"type": "understanding", "subject": "algebra"},
            difficulty=0.6
        )
        self._show_learning_result(
            "Esempio 2: Apprendimento con Elaborazione",
            elaboration_result,
            "Equazioni di secondo grado"
        )
        
        # 3. Esempio di pratica attiva
        practice_result = self.system.learn(
            content="Risolvi: x² - 4x + 4 = 0",
            context={"type": "skill", "subject": "algebra"},
            difficulty=0.7
        )
        self._show_learning_result(
            "Esempio 3: Pratica Attiva",
            practice_result,
            "Risoluzione equazione"
        )
        
        # 4. Esempio di riflessione metacognitiva
        reflection_result = self.system.learn(
            content="Analizza i passaggi usati per risolvere l'equazione",
            context={"type": "metacognition", "subject": "algebra"},
            difficulty=0.8
        )
        self._show_learning_result(
            "Esempio 4: Riflessione Metacognitiva",
            reflection_result,
            "Analisi del processo"
        )
        
        # Verifica che le strategie siano diverse per contesti diversi
        strategies_used = {
            basic_result['strategy_used'],
            elaboration_result['strategy_used'],
            practice_result['strategy_used'],
            reflection_result['strategy_used']
        }
        self.assertTrue(len(strategies_used) > 1, 
                       "Il sistema dovrebbe usare strategie diverse per contesti diversi")
        
        # Verifica che il successo sia correlato alla difficoltà
        success_levels = [
            basic_result['success_level'],
            elaboration_result['success_level'],
            practice_result['success_level'],
            reflection_result['success_level']
        ]
        self.assertTrue(np.mean(success_levels) > 0.5,
                       "Il successo medio dovrebbe essere superiore al 50%")
        
        # Mostra il sommario dell'apprendimento
        summary = self.system.get_learning_summary()
        print("\n=== Sommario dell'Apprendimento ===")
        print(f"Esperienze totali: {summary['total_experiences']}")
        print(f"Livello metacognitivo: {summary['metacognition_level']}")
        
        if 'strategies' in summary and isinstance(summary['strategies'], dict):
            print("\nStrategie più efficaci:")
            # Ordina le strategie per tasso di successo
            sorted_strategies = sorted(
                [(name, data['success_rate']) for name, data in summary['strategies'].items()],
                key=lambda x: x[1],
                reverse=True
            )
            # Mostra le prime 3 strategie
            for name, success_rate in sorted_strategies[:3]:
                print(f"- {name}: {success_rate:.2f} successo")
                
    def test_progressive_learning(self):
        """Test dell'apprendimento progressivo che simula lo sviluppo cognitivo umano"""
        
        # Fase 1: Apprendimento Base (come un bambino che inizia a riconoscere pattern)
        print("\n=== Fase 1: Apprendimento Base ===")
        basic_results = []
        for i in range(5):
            result = self.system.learn(
                content=f"Pattern {i}: {'A' * (i+1)} -> {'B' * (i+1)}",
                context={
                    "type": "pattern_recognition",
                    "stage": "basic",
                    "complexity": i/5,
                    "learning_style": "discovery",
                    "emotional_state": "curious"
                },
                difficulty=0.2 + (i * 0.1)
            )
            basic_results.append(result)
            self._show_learning_result(
                f"Pattern Recognition {i+1}",
                result,
                f"Pattern di complessità {i+1}"
            )
            
        # Fase 2: Connessioni (come un cervello che crea collegamenti)
        print("\n=== Fase 2: Creazione Connessioni ===")
        connection_results = []
        patterns_learned = [f"Pattern {i}" for i in range(5)]
        for i in range(3):
            result = self.system.learn(
                content=f"Connessione: {patterns_learned[i]} si collega con {patterns_learned[i+1]}",
                context={
                    "type": "connection_making",
                    "stage": "intermediate",
                    "previous_knowledge": patterns_learned[:i+1],
                    "learning_style": "associative",
                    "emotional_state": "focused"
                },
                difficulty=0.4 + (i * 0.1)
            )
            connection_results.append(result)
            self._show_learning_result(
                f"Creazione Connessione {i+1}",
                result,
                f"Collegamento tra pattern {i+1} e {i+2}"
            )
            
        # Fase 3: Astrazione (come il cervello che sviluppa il pensiero astratto)
        print("\n=== Fase 3: Sviluppo Astrazione ===")
        abstraction_results = []
        for i in range(3):
            result = self.system.learn(
                content=f"Regola astratta {i}: Se vedi una sequenza crescente, predici il prossimo elemento",
                context={
                    "type": "abstraction",
                    "stage": "advanced",
                    "abstraction_level": i,
                    "learning_style": "conceptual",
                    "emotional_state": "analytical"
                },
                difficulty=0.6 + (i * 0.1)
            )
            abstraction_results.append(result)
            self._show_learning_result(
                f"Sviluppo Astrazione {i+1}",
                result,
                f"Regola astratta livello {i+1}"
            )
            
        # Fase 4: Applicazione Creativa (come il cervello che innova)
        print("\n=== Fase 4: Applicazione Creativa ===")
        creative_results = []
        for i in range(2):
            result = self.system.learn(
                content=f"Creazione nuovo pattern: Combina regole {i} e {i+1} per creare qualcosa di nuovo",
                context={
                    "type": "creative_synthesis",
                    "stage": "expert",
                    "creativity_level": i,
                    "learning_style": "experimental",
                    "emotional_state": "inspired"
                },
                difficulty=0.8 + (i * 0.1)
            )
            creative_results.append(result)
            self._show_learning_result(
                f"Sintesi Creativa {i+1}",
                result,
                f"Nuova creazione livello {i+1}"
            )
            
        # Analisi dell'evoluzione dell'apprendimento
        print("\n=== Analisi Evoluzione Apprendimento ===")
        
        # 1. Progressione del successo per fase
        phases = {
            "Base": basic_results,
            "Connessioni": connection_results,
            "Astrazione": abstraction_results,
            "Creativa": creative_results
        }
        
        for phase_name, results in phases.items():
            avg_success = np.mean([r['success_level'] for r in results])
            avg_time = np.mean([r['time_taken'] for r in results])
            print(f"\n{phase_name}:")
            print(f"- Successo medio: {avg_success:.2f}")
            print(f"- Tempo medio: {avg_time:.1f} secondi")
            
        # 2. Verifica dell'apprendimento incrementale
        all_results = basic_results + connection_results + abstraction_results + creative_results
        success_trend = [r['success_level'] for r in all_results]
        
        # Calcola la correlazione tra ordine di apprendimento e successo
        correlation = np.corrcoef(range(len(success_trend)), success_trend)[0,1]
        print(f"\nCorrelazione ordine-successo: {correlation:.2f}")
        
        # 3. Test delle ipotesi sull'apprendimento
        
        # H1: Il sistema migliora con l'esperienza
        early_success = np.mean([r['success_level'] for r in all_results[:5]])
        late_success = np.mean([r['success_level'] for r in all_results[-5:]])
        print(f"\nMiglioramento dall'inizio alla fine:")
        print(f"- Successo iniziale: {early_success:.2f}")
        print(f"- Successo finale: {late_success:.2f}")
        print(f"- Miglioramento: {(late_success - early_success) * 100:.1f}%")
        
        # H2: Il sistema mantiene un livello minimo di competenza
        min_success = min(r['success_level'] for r in all_results)
        self.assertTrue(min_success >= 0.4,
                       "Il sistema dovrebbe mantenere un livello minimo di competenza")
        
        # H3: Il sistema può gestire compiti più complessi con l'esperienza
        complexity_success = np.corrcoef(
            [i/len(all_results) for i in range(len(all_results))],
            [r['success_level'] for r in all_results]
        )[0,1]
        self.assertTrue(complexity_success > -0.5,
                       "Il sistema dovrebbe gestire la complessità crescente")
        
if __name__ == '__main__':
    unittest.main()
