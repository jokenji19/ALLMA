import unittest
import os
import sqlite3
from datetime import datetime
import json
from allma_model.project_system.project_tracker import ProjectTracker

class TestProjectTracker(unittest.TestCase):
    """Test del ProjectTracker"""
    
    def setUp(self):
        """Setup per i test"""
        self.test_db = "test_project.db"
        self.test_user_id = "test_user"
        self.tracker = ProjectTracker(self.test_db)
    
    def tearDown(self):
        """Cleanup dopo i test"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def test_create_project(self):
        """Test della creazione di un progetto"""
        # Test creazione base
        success = self.tracker.create_project(
            self.test_user_id,
            "Test Project",
            "A test project",
            {"priority": "high"}
        )
        self.assertTrue(success)
        
        # Verifica che il progetto sia stato creato
        with self.tracker._get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM projects WHERE name = ?",
                ("Test Project",)
            )
            project = cursor.fetchone()
            self.assertIsNotNone(project)
            self.assertEqual(project['name'], "Test Project")
            self.assertEqual(project['description'], "A test project")
            self.assertEqual(project['user_id'], self.test_user_id)
            metadata = json.loads(project['metadata'])
            self.assertEqual(metadata['priority'], "high")
    
    def test_get_project_summary(self):
        """Test del riepilogo del progetto"""
        # Crea un progetto con metadati
        metadata = {
            "priority": "high",
            "deadline": "2025-02-28",
            "tags": ["test", "demo"]
        }
        
        self.tracker.create_project(
            self.test_user_id,
            "Summary Test",
            "Testing project summary",
            metadata
        )
        
        # Recupera il progetto ID
        with self.tracker._get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM projects WHERE name = ?",
                ("Summary Test",)
            )
            project = cursor.fetchone()
            project_id = project['id']
        
        # Recupera il riepilogo
        summary = self.tracker.get_project_summary(project_id)
        
        # Verifica i dettagli
        self.assertIsNotNone(summary)
        self.assertEqual(summary['name'], "Summary Test")
        self.assertEqual(summary['description'], "Testing project summary")
        self.assertEqual(summary['user_id'], self.test_user_id)
        self.assertEqual(summary['interaction_count'], 0)
        self.assertEqual(summary['metadata']['priority'], "high")
        self.assertEqual(summary['metadata']['deadline'], "2025-02-28")
        self.assertEqual(summary['metadata']['tags'], ["test", "demo"])
    
    def test_link_interaction(self):
        """Test del collegamento delle interazioni"""
        # Crea un progetto
        self.tracker.create_project(
            self.test_user_id,
            "Link Test",
            "Testing interaction linking"
        )
        
        # Recupera il progetto ID
        with self.tracker._get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM projects WHERE name = ?",
                ("Link Test",)
            )
            project = cursor.fetchone()
            project_id = project['id']
        
        # Simula un'interazione
        with self.tracker._get_db_connection() as conn:
            cursor = conn.execute(
                """
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    context TEXT,
                    metadata TEXT
                )
                """
            )
            conn.execute(
                """
                INSERT INTO interactions
                (user_id, content, context, metadata)
                VALUES (?, ?, ?, ?)
                """,
                (
                    self.test_user_id,
                    "Test interaction",
                    "{}",
                    "{}"
                )
            )
            conn.commit()
            interaction_id = cursor.lastrowid
        
        # Collega l'interazione
        success = self.tracker.link_interaction(
            project_id,
            interaction_id,
            "test_interaction",
            {"confidence": 0.8}
        )
        self.assertTrue(success)
        
        # Verifica il collegamento
        with self.tracker._get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM project_interactions WHERE project_id = ?",
                (project_id,)
            )
            link = cursor.fetchone()
            self.assertIsNotNone(link)
            self.assertEqual(link['interaction_id'], interaction_id)
            self.assertEqual(link['interaction_type'], "test_interaction")
            metadata = json.loads(link['metadata'])
            self.assertEqual(metadata['confidence'], 0.8)
    
    def test_update_project_status(self):
        """Test dell'aggiornamento dello stato del progetto"""
        # Crea un progetto
        self.tracker.create_project(
            self.test_user_id,
            "Status Test",
            "Testing status updates"
        )
        
        # Recupera il progetto ID
        with self.tracker._get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM projects WHERE name = ?",
                ("Status Test",)
            )
            project = cursor.fetchone()
            project_id = project['id']
        
        # Aggiorna lo stato
        success = self.tracker.update_project_status(
            project_id,
            "paused"
        )
        self.assertTrue(success)
        
        # Verifica l'aggiornamento
        with self.tracker._get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT status FROM projects WHERE id = ?",
                (project_id,)
            )
            project = cursor.fetchone()
            self.assertEqual(project['status'], "paused")
    
    def test_error_handling(self):
        """Test della gestione degli errori"""
        # Test creazione progetto con nome duplicato
        self.tracker.create_project(
            self.test_user_id,
            "Duplicate Test",
            "Testing duplicate handling"
        )
        
        success = self.tracker.create_project(
            self.test_user_id,
            "Duplicate Test",
            "This should fail"
        )
        self.assertFalse(success)
        
        # Test link con progetto inesistente
        success = self.tracker.link_interaction(
            999,  # ID inesistente
            1,
            "test"
        )
        self.assertFalse(success)
        
        # Test aggiornamento stato con progetto inesistente
        success = self.tracker.update_project_status(
            999,  # ID inesistente
            "completed"
        )
        self.assertFalse(success)

    def test_timestamp_updates(self):
        """Test dell'aggiornamento dei timestamp"""
        # Crea un progetto
        self.tracker.create_project(
            self.test_user_id,
            "Timestamp Test",
            "Testing timestamp updates"
        )
        
        # Recupera il progetto e i timestamp iniziali
        with self.tracker._get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT id, created_at, updated_at, last_updated_at FROM projects WHERE name = ?",
                ("Timestamp Test",)
            )
            project = cursor.fetchone()
            project_id = project['id']
            initial_created_at = project['created_at']
            initial_updated_at = project['updated_at']
            initial_last_updated = project['last_updated_at']
        
        # Aspetta un momento per assicurarsi che i timestamp siano diversi
        import time
        time.sleep(1)
        
        # Simula un'interazione
        with self.tracker._get_db_connection() as conn:
            cursor = conn.execute(
                """
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    context TEXT,
                    metadata TEXT
                )
                """
            )
            conn.execute(
                """
                INSERT INTO interactions
                (user_id, content, context, metadata)
                VALUES (?, ?, ?, ?)
                """,
                (
                    self.test_user_id,
                    "Test interaction",
                    "{}",
                    "{}"
                )
            )
            conn.commit()
            interaction_id = cursor.lastrowid
        
        # Collega l'interazione
        self.tracker.link_interaction(
            project_id,
            interaction_id,
            "test_interaction",
            {"confidence": 0.8}
        )
        
        # Verifica i timestamp dopo l'interazione
        with self.tracker._get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT created_at, updated_at, last_updated_at FROM projects WHERE id = ?",
                (project_id,)
            )
            project = cursor.fetchone()
            
            # created_at non dovrebbe cambiare
            self.assertEqual(project['created_at'], initial_created_at)
            
            # updated_at e last_updated dovrebbero essere stati aggiornati
            self.assertNotEqual(project['updated_at'], initial_updated_at)
            self.assertNotEqual(project['last_updated_at'], initial_last_updated)
            
            # updated_at e last_updated dovrebbero essere uguali tra loro
            self.assertEqual(project['updated_at'], project['last_updated_at'])

if __name__ == '__main__':
    unittest.main()
