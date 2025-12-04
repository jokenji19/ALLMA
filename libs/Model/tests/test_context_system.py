"""
Test del sistema contestuale
"""

import unittest
from datetime import datetime
import numpy as np
from Model.incremental_learning.communication_system import (
    ConceptLink,
    ConceptNetwork,
    ContextTracker,
    DialogContext,
    Message,
    CommunicationMode
)

class TestContextSystem(unittest.TestCase):
    def setUp(self):
        self.context_tracker = ContextTracker()
        self.concept_network = ConceptNetwork()
        
    def test_concept_network(self):
        # Test aggiunta concetti
        self.concept_network.add_concept("gatto", {"felino", "animale", "domestico"})
        self.concept_network.add_concept("cane", {"canide", "animale", "domestico"})
        
        # Test aggiunta link
        link = ConceptLink("gatto", "cane", "correlazione")
        self.concept_network.add_link(link)
        
        # Test ricerca concetti correlati
        related = self.concept_network.get_related_concepts("gatto")
        self.assertIn("cane", related)
        
        # Test percorso tra concetti
        path = self.concept_network.find_path("gatto", "cane")
        self.assertEqual(len(path), 1)
        self.assertEqual(path[0].source, "gatto")
        self.assertEqual(path[0].target, "cane")
        
    def test_context_tracking(self):
        # Test aggiornamento contesto
        context = {
            "topic": "animali",
            "entities": ["gatto", "cane"]
        }
        self.context_tracker.update_context(context)
        
        # Test estrazione concetti
        self.assertIn("animali", self.context_tracker.active_concepts)
        self.assertIn("gatto", self.context_tracker.active_concepts)
        self.assertIn("cane", self.context_tracker.active_concepts)
        
        # Test riepilogo contesto
        summary = self.context_tracker.get_context_summary()
        self.assertEqual(summary["current_context"], context)
        self.assertEqual(len(summary["active_concepts"]), 3)
        
        # Test ricerca contesto rilevante
        query = "parlami degli animali"  # Modificato per matchare il topic
        relevant = self.context_tracker.find_relevant_context(query)
        self.assertIn("topic", relevant)
        self.assertEqual(relevant["topic"], "animali")
        
    def test_context_history(self):
        # Test storia del contesto
        context1 = {"topic": "animali", "entities": ["gatto"]}
        context2 = {"topic": "cibo", "entities": ["pesce"]}
        
        self.context_tracker.update_context(context1)
        self.context_tracker.update_context(context2)
        
        # Verifica che il contesto precedente sia stato salvato
        self.assertEqual(len(self.context_tracker.context_history), 1)
        self.assertEqual(self.context_tracker.context_history[0], context1)
        
        # Verifica contesto corrente
        self.assertEqual(self.context_tracker.current_context, context2)
        
    def test_concept_similarity(self):
        # Test similarità tra concetti usando vettori normalizzati
        v1 = np.array([1.0, 0.5, 0.3])
        v2 = np.array([0.8, 0.6, 0.4])
        
        # Normalizza i vettori
        v1 = v1 / np.linalg.norm(v1)
        v2 = v2 / np.linalg.norm(v2)
        
        self.concept_network.update_concept_embedding("gatto", v1)
        self.concept_network.update_concept_embedding("cane", v2)
        
        similarity = self.concept_network.get_concept_similarity("gatto", "cane")
        self.assertGreater(similarity, 0.9)  # Alta similarità attesa
        
    def test_strongest_relations(self):
        # Test relazioni più forti
        self.concept_network.add_concept("gatto", {"felino"})
        self.concept_network.add_concept("cane", {"canide"})
        self.concept_network.add_concept("pesce", {"acquatico"})
        
        link1 = ConceptLink("gatto", "cane", "correlazione", weight=0.8)
        link2 = ConceptLink("gatto", "pesce", "correlazione", weight=0.3)
        
        self.concept_network.add_link(link1)
        self.concept_network.add_link(link2)
        
        strongest = self.concept_network.get_strongest_relations("gatto")
        self.assertEqual(len(strongest), 2)
        self.assertEqual(strongest[0][0], "cane")  # Prima relazione più forte
        self.assertEqual(strongest[0][1], 0.8)
        
if __name__ == '__main__':
    unittest.main()
