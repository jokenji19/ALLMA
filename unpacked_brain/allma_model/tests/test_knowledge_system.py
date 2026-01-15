"""Test del sistema di memoria per la conoscenza"""

import unittest
import tempfile
import os
import sqlite3
import json
from allma_model.memory_system.knowledge_memory import KnowledgeMemory

class TestKnowledgeSystem(unittest.TestCase):
    def setUp(self):
        """Setup per i test"""
        # Crea un file temporaneo per il database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        
        # Inizializza il sistema di memoria
        self.knowledge_memory = KnowledgeMemory(self.db_path)
        
        # Crea esplicitamente la tabella
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        
    def tearDown(self):
        """Cleanup dopo i test"""
        # Rimuovi il file temporaneo
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
        
    def test_knowledge_storage(self):
        """Test della memorizzazione della conoscenza"""
        # Test memorizzazione base
        content = "Python is a programming language"
        metadata = {"topic": "programming"}
        self.knowledge_memory.store_knowledge(content, metadata)
        
        # Verifica che la conoscenza sia stata memorizzata
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT content, metadata FROM knowledge")
            row = cursor.fetchone()
            
            self.assertEqual(row[0], content)
            self.assertEqual(json.loads(row[1]), metadata)
            
    def test_knowledge_retrieval(self):
        """Test del recupero della conoscenza"""
        # Memorizza diverse conoscenze
        knowledge_items = [
            {
                "content": "Python is great for AI",
                "metadata": {"topic": "programming", "subtopic": "AI"}
            },
            {
                "content": "TensorFlow is a machine learning framework",
                "metadata": {"topic": "AI", "subtopic": "frameworks"}
            },
            {
                "content": "Neural networks need training data",
                "metadata": {"topic": "AI", "subtopic": "neural_networks"}
            }
        ]
        
        for item in knowledge_items:
            self.knowledge_memory.store_knowledge(
                item["content"],
                item["metadata"]
            )
            
        # Test recupero per parole chiave
        results = self.knowledge_memory.get_knowledge_for_text("AI framework")
        self.assertTrue(any("TensorFlow" in result for result in results))
        self.assertTrue(any("framework" in result for result in results))
        
    def test_knowledge_update(self):
        """Test dell'aggiornamento della conoscenza"""
        # Memorizza conoscenza iniziale
        content = "ALLMA version 1.0"
        metadata = {"topic": "version"}
        self.knowledge_memory.store_knowledge(content, metadata)
        
        # Verifica che la conoscenza sia stata memorizzata
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT content FROM knowledge WHERE content = ?", (content,))
            self.assertIsNotNone(cursor.fetchone())
            
    def test_knowledge_integration(self):
        """Test dell'integrazione della conoscenza nelle risposte"""
        # Memorizza conoscenza
        self.knowledge_memory.store_knowledge(
            "ALLMA uses SQLite for data storage",
            {"topic": "architecture"}
        )
        
        # Cerca conoscenza correlata
        results = self.knowledge_memory.get_knowledge_for_text("database storage")
        self.assertTrue(any("SQLite" in result for result in results))
        
    def test_knowledge_search(self):
        """Test della ricerca della conoscenza"""
        # Memorizza conoscenze di test
        test_items = [
            ("Python basics", {"topic": "programming"}),
            ("Advanced Python", {"topic": "programming"}),
            ("Python in AI", {"topic": "AI"}),
            ("Database design", {"topic": "database"}),
            ("SQL queries", {"topic": "database"})
        ]
        
        for content, metadata in test_items:
            self.knowledge_memory.store_knowledge(content, metadata)
            
        # Test ricerca per topic
        results = self.knowledge_memory.get_knowledge_for_text("database")
        self.assertEqual(len(results), 2)
        
        # Verifica che i risultati abbiano il topic "database"
        metadata_list = [self.knowledge_memory.get_metadata(result) for result in results]
        self.assertTrue(all(metadata["topic"] == "database" for metadata in metadata_list))
        
    def test_knowledge_metadata(self):
        """Test della gestione dei metadati della conoscenza"""
        # Test con metadati complessi
        content = "Machine learning requires data"
        metadata = {
            "topic": "AI",
            "subtopics": ["machine_learning", "data_science"],
            "difficulty": "intermediate",
            "tags": ["ML", "data", "training"]
        }
        
        self.knowledge_memory.store_knowledge(content, metadata)
        
        # Verifica che i metadati siano stati salvati correttamente
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT metadata FROM knowledge WHERE content = ?", (content,))
            row = cursor.fetchone()
            saved_metadata = json.loads(row[0])
            
            self.assertEqual(saved_metadata, metadata)
            
    def test_knowledge_response_generation(self):
        """Test della generazione di risposte basate sulla conoscenza"""
        # Memorizza conoscenze correlate
        self.knowledge_memory.store_knowledge(
            "TensorFlow is good for deep learning",
            {"topic": "AI", "subtopic": "frameworks"}
        )
        self.knowledge_memory.store_knowledge(
            "PyTorch is popular in research",
            {"topic": "AI", "subtopic": "frameworks"}
        )
        
        # Test generazione risposta
        results = self.knowledge_memory.get_knowledge_for_text("deep learning frameworks")
        self.assertTrue(any("TensorFlow" in result for result in results))
        self.assertTrue(any("PyTorch" in result for result in results))

if __name__ == '__main__':
    unittest.main()
