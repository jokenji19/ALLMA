import unittest
from datetime import datetime
from .creativity_system import (
    CreativitySystem, Idea, Problem, CreativeApproach
)

class TestCreativitySystem(unittest.TestCase):
    def setUp(self):
        self.creativity_system = CreativitySystem()
        # Popola la knowledge base con dati di test
        self.creativity_system.add_to_knowledge_base("concetti", [
            "automobile", "bicicletta", "smartphone", "libro"
        ])
        self.creativity_system.add_to_knowledge_base("pattern", [
            "mobilità", "comunicazione", "apprendimento"
        ])
        self.creativity_system.add_to_knowledge_base("analogie", [
            "automobile come cavallo meccanico",
            "smartphone come cervello esterno"
        ])
        self.creativity_system.add_to_knowledge_base("metafore", [
            "il tempo è denaro",
            "la conoscenza è potere"
        ])
        
    def test_knowledge_base(self):
        """Testa la gestione della base di conoscenza"""
        # Test aggiunta elementi
        result = self.creativity_system.add_to_knowledge_base("concetti", ["computer"])
        self.assertTrue(result)
        self.assertIn("computer", self.creativity_system.knowledge_base["concetti"])
        
        # Test categoria non valida
        result = self.creativity_system.add_to_knowledge_base("invalid", ["test"])
        self.assertFalse(result)
        
        # Test duplicati
        initial_len = len(self.creativity_system.knowledge_base["concetti"])
        self.creativity_system.add_to_knowledge_base("concetti", ["automobile"])
        self.assertEqual(len(self.creativity_system.knowledge_base["concetti"]), initial_len)
        
    def test_idea_generation(self):
        """Testa la generazione di idee"""
        context = {"concetto": "trasporto", "ambiente": "urbano"}
        
        # Test generazione con approccio specifico
        idea = self.creativity_system.generate_idea(context, CreativeApproach.ANALOGIA)
        self.assertIsInstance(idea, Idea)
        self.assertEqual(idea.approach, CreativeApproach.ANALOGIA)
        self.assertTrue(idea.description)
        self.assertTrue(idea.components)
        
        # Test generazione con approccio casuale
        idea = self.creativity_system.generate_idea(context)
        self.assertIsInstance(idea, Idea)
        self.assertIn(idea.approach, CreativeApproach)
        
        # Verifica che l'idea sia stata memorizzata
        self.assertIn(idea.id, self.creativity_system.ideas)
        
    def test_idea_evaluation(self):
        """Testa la valutazione delle idee"""
        context = {"concetto": "mobilità"}
        idea = self.creativity_system.generate_idea(context)
        
        # Verifica che il punteggio sia nel range corretto
        self.assertGreaterEqual(idea.score, 0.0)
        self.assertLessEqual(idea.score, 1.0)
        
        # Genera più idee e verifica che abbiano punteggi diversi
        ideas = [
            self.creativity_system.generate_idea(context)
            for _ in range(3)
        ]
        scores = [idea.score for idea in ideas]
        self.assertTrue(any(s != scores[0] for s in scores[1:]))
        
    def test_problem_solving(self):
        """Testa la risoluzione creativa dei problemi"""
        problem = Problem(
            id="P1",
            description="Come migliorare la mobilità urbana",
            constraints=["sostenibile", "economico"],
            context={"ambiente": "città", "scala": "locale"}
        )
        
        # Genera soluzioni
        solutions = self.creativity_system.solve_problem(problem, num_solutions=3)
        
        # Verifica il numero di soluzioni
        self.assertEqual(len(solutions), 3)
        
        # Verifica che le soluzioni siano ordinate per punteggio
        for i in range(len(solutions) - 1):
            self.assertGreaterEqual(
                solutions[i].score,
                solutions[i + 1].score
            )
            
        # Verifica che il problema sia stato memorizzato
        self.assertIn(problem.id, self.creativity_system.problems)
        
    def test_idea_refinement(self):
        """Testa il raffinamento delle idee"""
        # Crea un'idea iniziale
        original_idea = self.creativity_system.generate_idea({"concetto": "trasporto"})
        
        # Raffina l'idea
        refined_idea = self.creativity_system.refine_idea(original_idea.id)
        
        # Verifica il raffinamento
        self.assertIsNotNone(refined_idea)
        self.assertNotEqual(refined_idea.id, original_idea.id)
        self.assertIn(original_idea.id, refined_idea.inspirations)
        
        # Test con ID non valido
        self.assertIsNone(self.creativity_system.refine_idea("invalid_id"))
        
    def test_idea_combination(self):
        """Testa la combinazione di idee"""
        # Crea alcune idee
        idea1 = self.creativity_system.generate_idea({"concetto": "automobile"})
        idea2 = self.creativity_system.generate_idea({"concetto": "smartphone"})
        
        # Combina le idee
        combined_idea = self.creativity_system.combine_ideas([idea1.id, idea2.id])
        
        # Verifica la combinazione
        self.assertIsNotNone(combined_idea)
        self.assertEqual(combined_idea.approach, CreativeApproach.COMBINAZIONE)
        self.assertTrue(set(idea1.components).intersection(set(combined_idea.components)))
        self.assertTrue(set(idea2.components).intersection(set(combined_idea.components)))
        
        # Test con ID non validi
        self.assertIsNone(self.creativity_system.combine_ideas(["invalid_id"]))
        
    def test_analogies(self):
        """Testa la ricerca di analogie"""
        # Cerca analogie per un concetto
        analogies = self.creativity_system.find_analogies("automobile")
        self.assertTrue(analogies)
        self.assertIn("automobile come cavallo meccanico", analogies)
        
        # Test similarità
        similarity = self.creativity_system._calculate_similarity("auto", "automobile")
        self.assertGreater(similarity, 0)
        
    def test_random_combinations(self):
        """Testa la generazione di combinazioni casuali"""
        elements = ["a", "b", "c", "d"]
        
        # Genera combinazioni
        combinations = self.creativity_system.generate_random_combinations(elements, 3)
        
        # Verifica il numero di combinazioni
        self.assertEqual(len(combinations), 3)
        
        # Verifica che ogni combinazione sia valida
        for combo in combinations:
            self.assertTrue(all(elem in elements for elem in combo))
            self.assertTrue(2 <= len(combo) <= 4)
            
        # Test con input non validi
        self.assertEqual(len(self.creativity_system.generate_random_combinations([], 3)), 0)
        self.assertEqual(len(self.creativity_system.generate_random_combinations(elements, 0)), 0)

if __name__ == '__main__':
    unittest.main()
