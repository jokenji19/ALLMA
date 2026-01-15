"""
Test del sistema di memoria avanzato
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending
"""

import unittest
from datetime import datetime, timedelta
from allma_model.incremental_learning.memory_system import EnhancedMemorySystem, MemoryItem

class TestMemorySystem(unittest.TestCase):
    def setUp(self):
        """Inizializza il sistema di memoria per i test"""
        self.memory = EnhancedMemorySystem()
        
    def test_working_memory(self):
        """Test della memoria di lavoro"""
        content = "Test memory item"
        self.memory.working_memory.add_item(
            MemoryItem(content=content,
                      timestamp=datetime.now(),
                      importance=0.8,
                      emotional_valence=0.6,
                      associations={"test"},
                      recall_count=0,
                      last_recall=datetime.now())
        )
        items = self.memory.working_memory.get_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].content, content)
        
    def test_short_term_memory(self):
        """Test della memoria a breve termine"""
        content = "Short term memory test"
        self.memory.short_term.add_item(
            MemoryItem(content=content,
                      timestamp=datetime.now(),
                      importance=0.7,
                      emotional_valence=0.5,
                      associations={"test", "short"},
                      recall_count=0,
                      last_recall=datetime.now())
        )
        items = self.memory.short_term.get_recent_items(1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].content, content)
        
    def test_long_term_memory(self):
        """Test della memoria a lungo termine"""
        content = "Long term memory test"
        item = MemoryItem(content=content,
                         timestamp=datetime.now(),
                         importance=0.9,
                         emotional_valence=0.8,
                         associations={"test", "long"},
                         recall_count=0,
                         last_recall=datetime.now())
        self.memory.long_term.add_item(item)
        strength = self.memory.long_term.get_memory_strength(item)
        self.assertGreater(strength, 0)
        
    def test_procedural_memory(self):
        """Test della memoria procedurale"""
        procedure_name = "test_procedure"
        steps = ["step1", "step2", "step3"]
        
        # Test aggiunta procedura
        self.memory.store_procedure(procedure_name, steps)
        proc = self.memory.get_procedure(procedure_name)
        self.assertIsNotNone(proc)
        self.assertEqual(proc['steps'], steps)
        
        # Test pratica procedura
        self.memory.practice_procedure(procedure_name, 0.8)
        mastery = self.memory.get_procedure_mastery(procedure_name)
        self.assertGreater(mastery, 0)
        
    def test_episodic_memory(self):
        """Test della memoria episodica"""
        content = "Ho imparato qualcosa di nuovo oggi"
        self.memory.episodic.add_memory(
            content=content,
            emotional_valence=0.8,
            context={'is_novel': True, 'is_significant': True}
        )
        
        # Verifica che la memoria sia stata aggiunta
        self.assertEqual(len(self.memory.episodic.memories), 1)
        memory = self.memory.episodic.memories[0]
        self.assertEqual(memory.content, content)
        self.assertGreater(memory.importance, 0.7)  # Alta importanza per novità ed emozione positiva
        
        # Test recupero memoria
        recalled = self.memory.episodic.recall("imparato", limit=1)
        self.assertEqual(len(recalled), 1)
        self.assertEqual(recalled[0].content, content)
        
    def test_semantic_memory(self):
        """Test della memoria semantica"""
        # Test aggiunta concetti
        self.memory.semantic.add_concept(
            "gatto",
            {"tipo": "mammifero", "habitat": "domestico"}
        )
        self.memory.semantic.add_relationship(
            "gatto", "è", "animale"
        )
        
        # Verifica concetti
        self.assertIn("gatto", self.memory.semantic.concepts)
        self.assertEqual(
            self.memory.semantic.concepts["gatto"]["tipo"],
            "mammifero"
        )
        
        # Verifica relazioni
        related = self.memory.semantic.get_related_concepts("gatto")
        self.assertIn("è", related)
        self.assertIn("animale", related["è"])
        
    def test_memory_integration(self):
        """Test dell'integrazione tra i diversi tipi di memoria"""
        # Memorizza un'esperienza
        self.memory.process_experience(
            "Test integrated memory",
            context={"type": "test"},
            emotional_valence=0.8
        )
        
        # Verifica che sia stata memorizzata
        state = self.memory.get_state()
        self.assertGreater(state["total_memories"], 0)
        
    def test_memory_persistence(self):
        """Test del salvataggio e caricamento della memoria"""
        # Aggiungi alcuni dati di test
        self.memory.process_experience(
            "Ho visto un gatto nero",
            emotional_valence=0.3
        )
        self.memory.semantic.add_concept(
            "gatto",
            {"colore": "nero"}
        )
        self.memory.store_procedure(
            "accarezzare_gatto",
            ["avvicinare la mano", "accarezzare delicatamente"]
        )
        
        # Salva lo stato
        filename = "test_memory.json"
        self.memory.save_to_file(filename)
        
        # Crea un nuovo sistema e carica lo stato
        new_system = EnhancedMemorySystem()
        new_system.load_from_file(filename)
        
        # Verifica che i dati siano stati preservati
        self.assertEqual(
            len(new_system.episodic.memories),
            len(self.memory.episodic.memories)
        )
        self.assertEqual(
            new_system.semantic.concepts["gatto"],
            self.memory.semantic.concepts["gatto"]
        )
        self.assertEqual(
            new_system.procedural.procedures["accarezzare_gatto"]["steps"],
            self.memory.procedural.procedures["accarezzare_gatto"]["steps"]
        )
        
    def test_memory_categorization(self):
        """Test della categorizzazione automatica delle memorie"""
        # Test memoria di apprendimento
        content = "Oggi sto imparando a programmare in Python"
        self.memory.episodic.add_memory(
            content=content,
            emotional_valence=0.6,
            context={'activity': 'studio'}
        )
        
        # Verifica le categorie
        memory = self.memory.episodic.memories[0]
        self.assertIn('apprendimento', memory.categories)
        self.assertIn('attività_studio', memory.categories)
        
        # Test memoria emotiva
        content = "Mi sento molto felice oggi"
        self.memory.episodic.add_memory(
            content=content,
            emotional_valence=0.9,
            context={'social': True}
        )
        
        # Verifica le categorie
        memory = self.memory.episodic.memories[1]
        self.assertIn('emozioni', memory.categories)
        self.assertIn('sociale', memory.categories)
        
    def test_memory_forgetting(self):
        """Test del meccanismo di oblio selettivo"""
        # Aggiungi una memoria vecchia
        old_date = datetime.now() - timedelta(days=30)
        memory = MemoryItem(
            content="Un vecchio ricordo",
            timestamp=old_date,
            emotional_valence=0.5,
            importance=0.5,
            associations=set(),
            recall_count=0,
            last_recall=old_date
        )
        self.memory.episodic.memories.append(memory)
        
        # Applica l'oblio
        self.memory.episodic.apply_forgetting()
        
        # Verifica che la forza sia diminuita
        self.assertLess(memory.strength, 1.0)
        
    def test_memory_consolidation(self):
        """Test del consolidamento della memoria"""
        # Aggiungi alcune memorie con forza variabile
        for i in range(5):
            memory = MemoryItem(
                content=f"Ricordo {i}",
                timestamp=datetime.now(),
                emotional_valence=0.5,
                importance=0.5,
                associations=set(),
                recall_count=0,
                last_recall=datetime.now(),
                strength=0.1 if i < 2 else 0.8
            )
            self.memory.episodic.memories.append(memory)
            
        # Forza il consolidamento
        self.memory.episodic.last_consolidation = datetime.now() - timedelta(hours=5)
        self.memory.episodic.consolidate()
        
        # Verifica che le memorie deboli siano state rimosse
        self.assertEqual(len(self.memory.episodic.memories), 3)
        for memory in self.memory.episodic.memories:
            self.assertGreater(memory.strength, 0.2)
            
    def test_contextual_recall(self):
        """Test del recupero contestuale migliorato"""
        # Aggiungi alcune memorie con contesti diversi
        contexts = [
            {'location': 'casa', 'activity': 'studio'},
            {'location': 'casa', 'activity': 'relax'},
            {'location': 'ufficio', 'activity': 'studio'}
        ]
        
        for i, context in enumerate(contexts):
            self.memory.episodic.add_memory(
                content=f"Ricordo {i+1} in {context['location']} durante {context['activity']}",
                emotional_valence=0.5,
                context=context
            )
            
        # Recupera memorie con contesto simile
        recalled = self.memory.episodic.recall(
            "ricordo",
            context={'location': 'casa', 'activity': 'studio'},
            limit=2
        )
        
        # Verifica che le memorie più rilevanti siano state recuperate
        self.assertEqual(len(recalled), 2)
        self.assertIn("casa", recalled[0].content.lower())
        self.assertIn("studio", recalled[0].content.lower())
        
    def test_memory_associations(self):
        """Test delle associazioni tra memorie"""
        # Aggiungi alcune memorie correlate
        memories = [
            ("Ho iniziato a studiare Python", 0.7, {'activity': 'studio'}),
            ("Sto studiando gli algoritmi in Python", 0.8, {'activity': 'studio'}),
            ("Mi sto rilassando al parco", 0.6, {'activity': 'relax'})
        ]
        
        for content, valence, context in memories:
            self.memory.episodic.add_memory(content, valence, context)
            
        # Test pattern recognition sulla seconda memoria
        memory = self.memory.episodic.memories[1]
        self.assertGreater(len(memory.patterns), 0)
        
        # Test associazioni
        associated = self.memory.episodic.get_associated_memories(1)
        self.assertGreater(len(associated), 0)
        
        # Verifica che le memorie più simili abbiano associazioni più forti
        self.assertGreater(associated[0][1], associated[-1][1])
        
    def test_memory_chains(self):
        """Test delle catene di memorie associate"""
        # Aggiungi alcune memorie correlate
        memories = [
            ("Ho iniziato a studiare Python", 0.7, {'activity': 'studio'}),
            ("Sto imparando gli algoritmi", 0.8, {'activity': 'studio'}),
            ("Mi piace programmare", 0.9, {'activity': 'studio'})
        ]
        
        for content, valence, context in memories:
            self.memory.episodic.add_memory(content, valence, context)
            
        # Trova catene di memorie
        chains = self.memory.episodic.find_memory_chains(1, max_depth=3)
        
        # Verifica che esistano catene
        self.assertGreater(len(chains), 0)
        
        # Verifica che le catene siano valide
        for chain in chains:
            self.assertGreater(len(chain), 1)  # Ogni catena dovrebbe avere almeno 2 memorie
            self.assertEqual(chain[0], self.memory.episodic.memories[1])  # La prima memoria dovrebbe essere quella di partenza
            
    def test_pattern_recognition(self):
        """Test del riconoscimento dei pattern"""
        # Aggiungi alcune memorie con pattern simili
        memories = [
            ("Oggi ho studiato Python", 0.7, {'activity': 'studio'}),
            ("Ieri ho studiato Java", 0.7, {'activity': 'studio'}),
            ("La settimana scorsa ho studiato C++", 0.7, {'activity': 'studio'})
        ]
        
        for content, valence, context in memories:
            self.memory.episodic.add_memory(content, valence, context)
            
        # Verifica che i pattern siano stati riconosciuti sulla seconda memoria
        memory = self.memory.episodic.memories[1]
        self.assertGreater(len(memory.patterns), 0)  # Dovrebbe trovare un pattern con le altre memorie

if __name__ == '__main__':
    unittest.main()
