"""
Test della modularità del sistema di memoria
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending

Questo test verifica che i componenti del sistema di memoria possano essere
utilizzati sia indipendentemente che in modo integrato.
"""

import unittest
from datetime import datetime, timedelta
from memory_system import (
    MemoryItem,
    WorkingMemory,
    ShortTermMemory,
    LongTermMemory,
    EpisodicMemory,
    SemanticMemory,
    ProceduralMemory,
    EnhancedMemorySystem
)

class TestMemoryModularity(unittest.TestCase):
    def setUp(self):
        """Inizializza i componenti di memoria individuali e il sistema integrato"""
        # Componenti individuali
        self.working = WorkingMemory()
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()
        
        # Sistema integrato
        self.integrated = EnhancedMemorySystem()
        
    def test_independent_working_memory(self):
        """Test del funzionamento indipendente della memoria di lavoro"""
        memory = MemoryItem(
            content="Test working memory",
            timestamp=datetime.now(),
            importance=0.8,
            emotional_valence=0.6,
            associations={"test"},
            recall_count=0,
            last_recall=datetime.now()
        )
        
        # Test diretto sulla memoria di lavoro
        self.working.add_item(memory)
        items = self.working.get_items()
        
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].content, "Test working memory")
        
    def test_independent_episodic_memory(self):
        """Test del funzionamento indipendente della memoria episodica"""
        # Test diretto sulla memoria episodica
        self.episodic.add_memory(
            "Ho imparato qualcosa di nuovo",
            emotional_valence=0.8,
            context={'is_novel': True}
        )
        
        recalled = self.episodic.recall("imparato", limit=1)
        self.assertEqual(len(recalled), 1)
        self.assertEqual(recalled[0].content, "Ho imparato qualcosa di nuovo")
        
    def test_independent_semantic_memory(self):
        """Test del funzionamento indipendente della memoria semantica"""
        # Test diretto sulla memoria semantica
        self.semantic.add_concept(
            "python",
            {"tipo": "linguaggio", "paradigma": "object-oriented"}
        )
        
        self.semantic.add_relationship("python", "è", "linguaggio")
        related = self.semantic.get_related_concepts("python")
        
        self.assertIn("è", related)
        self.assertIn("linguaggio", related["è"])
        
    def test_independent_procedural_memory(self):
        """Test del funzionamento indipendente della memoria procedurale"""
        # Test diretto sulla memoria procedurale
        steps = ["apri editor", "scrivi codice", "salva file"]
        self.procedural.add_procedure("programmare", steps)
        
        proc = self.procedural.get_procedure("programmare")
        self.assertEqual(proc['steps'], steps)
        
        self.procedural.practice_procedure("programmare", 0.9)
        mastery = self.procedural.get_mastery_level("programmare")
        self.assertGreater(mastery, 0)
        
    def test_memory_interaction(self):
        """Test dell'interazione tra diversi tipi di memoria"""
        # Crea una memoria che coinvolge più sistemi
        experience = "Ho imparato a programmare in Python oggi"
        
        # Memorizza nei sistemi individuali
        self.episodic.add_memory(
            experience,
            emotional_valence=0.8,
            context={'activity': 'studio'}
        )
        
        self.semantic.add_concept(
            "python",
            {"tipo": "linguaggio", "difficoltà": "media"}
        )
        
        self.procedural.add_procedure(
            "python_hello_world",
            ["apri editor", "scrivi print('Hello World')", "esegui"]
        )
        
        # Verifica che ogni sistema abbia la sua parte
        episodic_recall = self.episodic.recall("programmare")
        self.assertTrue(any("programmare" in m.content for m in episodic_recall))
        
        semantic_info = self.semantic.concepts.get("python")
        self.assertEqual(semantic_info["tipo"], "linguaggio")
        
        procedure = self.procedural.get_procedure("python_hello_world")
        self.assertEqual(len(procedure["steps"]), 3)
        
    def test_integrated_system(self):
        """Test del sistema integrato"""
        # Usa il sistema integrato per processare la stessa esperienza
        experience = "Ho imparato a programmare in Python oggi"
        
        self.integrated.process_experience(
            experience,
            emotional_valence=0.8,
            context={'activity': 'studio'}
        )
        
        # Memorizza una procedura correlata
        self.integrated.store_procedure(
            "python_hello_world",
            ["apri editor", "scrivi print('Hello World')", "esegui"]
        )
        
        # Verifica che il sistema integrato gestisca tutto correttamente
        results = self.integrated.recall_memory("python")
        
        # Dovrebbe trovare sia la memoria episodica che i concetti semantici
        self.assertTrue(results['episodic'])  # Memorie episodiche trovate
        self.assertTrue(results['semantic'])  # Concetti semantici trovati
        
        # Verifica che la procedura sia stata memorizzata
        procedure = self.integrated.get_procedure("python_hello_world")
        self.assertIsNotNone(procedure)
        
    def test_memory_persistence(self):
        """Test della persistenza indipendente e integrata"""
        # Test persistenza componente individuale
        self.episodic.add_memory(
            "Memoria di test",
            emotional_valence=0.7,
            context={'test': True}
        )
        
        # Verifica che la memoria persista nel componente
        recalled = self.episodic.recall("test")
        self.assertEqual(len(recalled), 1)
        
        # Test persistenza sistema integrato
        self.integrated.process_experience(
            "Test integrato",
            emotional_valence=0.7,
            context={'test': True}
        )
        
        # Verifica che la memoria persista nel sistema integrato
        results = self.integrated.recall_memory("test")
        self.assertTrue(results['episodic'])
        
    def test_cross_component_interaction(self):
        """Test dell'interazione tra componenti diversi"""
        # Crea una memoria che richiede più componenti
        self.integrated.process_experience(
            "Sto imparando una nuova tecnica di programmazione",
            emotional_valence=0.8,
            context={'activity': 'studio', 'is_novel': True}
        )
        
        # Aggiungi una procedura correlata
        self.integrated.store_procedure(
            "nuova_tecnica",
            ["studio teoria", "pratica", "applica"]
        )
        
        # Verifica che i componenti si influenzino a vicenda
        results = self.integrated.recall_memory("tecnica")
        
        # La memoria dovrebbe essere presente sia come esperienza che come concetto
        self.assertTrue(any("tecnica" in m.content for m in results['episodic']))
        self.assertTrue(results['semantic'])
        
        # La procedura dovrebbe essere accessibile
        procedure = self.integrated.get_procedure("nuova_tecnica")
        self.assertIsNotNone(procedure)
        
        # L'importanza della memoria dovrebbe essere influenzata dal contesto
        memory = results['episodic'][0]
        self.assertGreater(memory.importance, 0.7)  # Alta importanza per novità
        
if __name__ == '__main__':
    unittest.main()
