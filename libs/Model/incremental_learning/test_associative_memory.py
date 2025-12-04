"""
Test del Sistema di Memoria Associativa
"""

import unittest
from datetime import datetime, timedelta
import time
from Model.incremental_learning.associative_memory_system import AssociativeMemorySystem

class TestAssociativeMemorySystem(unittest.TestCase):
    def setUp(self):
        self.memory = AssociativeMemorySystem()
        
    def test_memory_creation(self):
        """Verifica la creazione di nuove memorie"""
        # Crea una memoria con tag e contesto
        node = self.memory.create_memory(
            "Python",
            tags={"programming", "language"},
            context={"domain": "computer science"}
        )
        
        # Verifica che la memoria sia stata creata correttamente
        self.assertEqual(node.content, "Python")
        self.assertEqual(node.tags, {"programming", "language"})
        self.assertEqual(node.context["domain"], "computer science")
        self.assertGreater(node.strength, 0.9)  # Dovrebbe essere forte all'inizio
        
    def test_association_creation(self):
        """Verifica la creazione di associazioni tra memorie"""
        # Crea due memorie e le associa
        self.memory.create_memory("Python", tags={"programming"})
        self.memory.create_memory("JavaScript", tags={"programming"})
        
        assoc = self.memory.create_association(
            "Python",
            "JavaScript",
            type="similar_language",
            strength=0.7
        )
        
        # Verifica l'associazione
        self.assertEqual(assoc.type, "similar_language")
        self.assertEqual(assoc.strength, 0.7)
        self.assertEqual(self.memory.nodes[assoc.source_id].content, "Python")
        self.assertEqual(self.memory.nodes[assoc.target_id].content, "JavaScript")
        
    def test_memory_recall(self):
        """Verifica il recupero delle memorie"""
        # Crea una memoria
        self.memory.create_memory("Python", tags={"programming"})
        
        # Recupera la memoria
        node = self.memory.recall("Python")
        
        # Verifica il recupero
        self.assertIsNotNone(node)
        self.assertEqual(node.content, "Python")
        self.assertGreater(node.access_count, 0)
        
    def test_association_finding(self):
        """Verifica la ricerca di associazioni"""
        # Crea una rete di memorie associate
        self.memory.create_memory("Python", tags={"programming"})
        self.memory.create_memory("Django", tags={"framework"})
        self.memory.create_memory("Flask", tags={"framework"})
        
        self.memory.create_association("Python", "Django", strength=0.8)
        self.memory.create_association("Python", "Flask", strength=0.6)
        
        # Trova le associazioni
        associations = self.memory.find_associations("Python")
        
        # Verifica che le associazioni siano state trovate e ordinate
        self.assertEqual(len(associations), 2)
        self.assertEqual(self.memory.nodes[associations[0].target_id].content, "Django")  # Più forte
        self.assertEqual(self.memory.nodes[associations[1].target_id].content, "Flask")   # Più debole
        
    def test_tag_search(self):
        """Verifica la ricerca per tag"""
        # Crea memorie con tag
        self.memory.create_memory("Python", tags={"programming", "backend"})
        self.memory.create_memory("JavaScript", tags={"programming", "frontend"})
        self.memory.create_memory("HTML", tags={"frontend"})
        
        # Cerca per tag
        programming_nodes = self.memory.find_by_tags({"programming"})
        frontend_nodes = self.memory.find_by_tags({"frontend"})
        
        # Verifica i risultati
        self.assertEqual(len(programming_nodes), 2)
        self.assertEqual(len(frontend_nodes), 2)
        
    def test_context_search(self):
        """Verifica la ricerca per contesto"""
        # Crea memorie con contesto
        self.memory.create_memory(
            "Python",
            context={"domain": "backend"}
        )
        self.memory.create_memory(
            "JavaScript",
            context={"domain": "frontend"}
        )
        
        # Cerca per contesto
        backend_nodes = self.memory.find_by_context("domain", "backend")
        frontend_nodes = self.memory.find_by_context("domain", "frontend")
        
        # Verifica i risultati
        self.assertEqual(len(backend_nodes), 1)
        self.assertEqual(len(frontend_nodes), 1)
        self.assertEqual(backend_nodes[0].content, "Python")
        self.assertEqual(frontend_nodes[0].content, "JavaScript")
        
    def test_activation_spreading(self):
        """Verifica la diffusione dell'attivazione"""
        # Crea una rete di memorie interconnesse
        self.memory.create_memory("AI", tags={"technology"})
        self.memory.create_memory("Machine Learning", tags={"technology"})
        self.memory.create_memory("Neural Networks", tags={"technology"})
        
        self.memory.create_association("AI", "Machine Learning", strength=0.9)
        self.memory.create_association("Machine Learning", "Neural Networks", strength=0.8)
        
        # Attiva la diffusione da AI
        activated_nodes = self.memory.spread_activation("AI", depth=2)
        
        # Verifica la diffusione
        self.assertEqual(len(activated_nodes), 3)  # AI, ML, e NN
        self.assertEqual(activated_nodes[0][0].content, "AI")  # Nodo iniziale
        
    def test_memory_consolidation(self):
        """Verifica il consolidamento della memoria"""
        # Crea alcune memorie
        node_temp = self.memory.create_memory("Temporary")
        node_temp.strength = 0.2  # Imposta manualmente la forza
        
        node_imp = self.memory.create_memory("Important")
        node_imp.strength = 0.9  # Imposta manualmente la forza
        
        # Simula il passaggio del tempo
        future_time = datetime.now() + timedelta(days=7)  # Aumentiamo il tempo
        
        # Forza il decadimento
        node_temp.decay(future_time, decay_rate=1.0)  # Aumentiamo il tasso di decadimento
        node_imp.decay(future_time, decay_rate=0.1)
        
        # Consolida le memorie
        self.memory.consolidate_memories()
        
        # Verifica che le memorie deboli siano state dimenticate
        recalled_temp = self.memory.recall("Temporary", strengthen=False)  # Non rinforzare durante il recall
        recalled_imp = self.memory.recall("Important", strengthen=False)   # Non rinforzare durante il recall
        
        # La memoria temporanea dovrebbe essere molto debole o dimenticata
        if recalled_temp:
            self.assertLess(recalled_temp.strength, self.memory.forgetting_threshold)
            
        # La memoria importante dovrebbe essere ancora presente
        self.assertIsNotNone(recalled_imp)
        self.assertGreater(recalled_imp.strength, self.memory.forgetting_threshold)
        
    def test_memory_decay(self):
        """Verifica il decadimento naturale della memoria"""
        # Crea una memoria
        node = self.memory.create_memory("Decaying")
        initial_strength = node.strength
        
        # Simula il passaggio del tempo
        future_time = datetime.now() + timedelta(days=1)
        node.decay(future_time)
        
        # Verifica il decadimento
        self.assertLess(node.strength, initial_strength)

if __name__ == '__main__':
    unittest.main()
