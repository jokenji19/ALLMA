"""Test per il sistema di memoria conversazionale."""

import unittest
from datetime import datetime, timedelta
from allma_model.memory_system.conversational_memory import ConversationalMemory

class TestConversationalMemory(unittest.TestCase):
    """Test per ConversationalMemory."""
    
    def setUp(self):
        """Setup per i test."""
        self.memory = ConversationalMemory()
        self.test_user = "test_user_123"
        
    def test_store_conversation(self):
        """Test della memorizzazione conversazioni."""
        content = "Questo è un test di conversazione"
        metadata = {"topic": "test", "priority": "high"}
        
        # Test memorizzazione base
        conv_id = self.memory.store_conversation(
            self.test_user,
            content,
            metadata
        )
        
        self.assertIsNotNone(conv_id)
        self.assertTrue(conv_id.startswith(self.test_user))
        
        # Verifica che la conversazione sia stata memorizzata
        conversations = self.memory.conversations[self.test_user]
        self.assertEqual(len(conversations), 1)
        self.assertEqual(conversations[0].content, content)
        self.assertEqual(conversations[0].metadata, metadata)
        
    def test_retrieve_relevant_context(self):
        """Test del recupero contesto rilevante."""
        # Memorizza alcune conversazioni
        contents = [
            "Python è un linguaggio di programmazione",
            "I gatti sono animali domestici",
            "JavaScript è usato nel web",
            "I cani sono fedeli amici"
        ]
        
        for content in contents:
            self.memory.store_conversation(self.test_user, content)
            
        # Test recupero contesto
        results = self.memory.retrieve_relevant_context(
            "Parliamo di programmazione",
            self.test_user
        )
        
        self.assertTrue(len(results) > 0)
        # Il primo risultato dovrebbe essere sulla programmazione
        self.assertIn("programmazione", results[0][1].content.lower())
        
    def test_get_conversation_history(self):
        """Test del recupero storia conversazioni."""
        # Memorizza conversazioni con timestamp diversi
        now = datetime.now()
        
        conversations = [
            ("Conv 1", now - timedelta(days=2)),
            ("Conv 2", now - timedelta(days=1)),
            ("Conv 3", now)
        ]
        
        conv_ids = []
        for content, timestamp in conversations:
            conv_id = self.memory.store_conversation(self.test_user, content)
            conv_ids.append(conv_id)
            # Aggiorna il timestamp manualmente per il test
            conv = self.memory.conversations[self.test_user][-1]
            conv.timestamp = timestamp
            
        # Test recupero senza filtri
        history = self.memory.get_conversation_history(conv_ids[-1])
        self.assertEqual(len(history), 1)
        
        # Test recupero con filtro temporale
        history = self.memory.get_conversation_history(
            conv_ids[-1],
            start_time=now - timedelta(days=1)
        )
        self.assertEqual(len(history), 1)
        
    def test_analyze_conversation_patterns(self):
        """Test dell'analisi pattern conversazioni."""
        # Memorizza conversazioni per analisi
        contents = [
            "Python è fantastico per il machine learning",
            "Adoro programmare in Python",
            "Il deep learning è interessante",
            "Python ha molte librerie utili"
        ]
        
        for content in contents:
            self.memory.store_conversation(self.test_user, content)
            
        patterns = self.memory.analyze_conversation_patterns(self.test_user)
        
        self.assertEqual(patterns['total_conversations'], 4)
        self.assertTrue(patterns['avg_length'] > 0)
        self.assertTrue(len(patterns['common_topics']) > 0)
        self.assertTrue(len(patterns['time_patterns']) > 0)
        
    def test_clear_old_conversations(self):
        """Test della pulizia conversazioni vecchie."""
        # Memorizza conversazioni con date diverse
        now = datetime.now()
        old_date = now - timedelta(days=10)
        
        conversations = [
            ("Conv vecchia 1", old_date - timedelta(days=1)),
            ("Conv vecchia 2", old_date - timedelta(days=2)),
            ("Conv nuova 1", now - timedelta(days=1)),
            ("Conv nuova 2", now)
        ]
        
        for content, timestamp in conversations:
            conv_id = self.memory.store_conversation(self.test_user, content)
            # Aggiorna il timestamp manualmente per il test
            conv = self.memory.conversations[self.test_user][-1]
            conv.timestamp = timestamp
            
        # Rimuovi conversazioni vecchie
        removed = self.memory.clear_old_conversations(
            self.test_user,
            old_date
        )
        
        self.assertEqual(removed, 2)
        self.assertEqual(
            len(self.memory.conversations[self.test_user]),
            2
        )
        
    def test_edge_cases(self):
        """Test dei casi limite."""
        # Test con contenuto vuoto
        conv_id = self.memory.store_conversation(self.test_user, "")
        self.assertIsNotNone(conv_id)
        
        # Test con metadata None
        conv_id = self.memory.store_conversation(
            self.test_user,
            "Test",
            None
        )
        self.assertIsNotNone(conv_id)
        
        # Test recupero contesto con topic vuoto
        results = self.memory.retrieve_relevant_context("")
        self.assertEqual(len(results), 0)
        
        # Test analisi pattern per utente inesistente
        patterns = self.memory.analyze_conversation_patterns("nonexistent")
        self.assertEqual(patterns['total_conversations'], 0)
        
        # Test pulizia per utente inesistente
        removed = self.memory.clear_old_conversations(
            "nonexistent",
            datetime.now()
        )
        self.assertEqual(removed, 0)

if __name__ == '__main__':
    unittest.main()
