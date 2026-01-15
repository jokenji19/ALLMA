import unittest
from datetime import datetime
import time
from Model.core.personality_coalescence import CoalescenceProcessor, EmotionalState, EmotionalResponse
from Model.core.nlp_processor import NLPProcessor
from Model.core.user_profile import UserProfile

class TestInitialConversation(unittest.TestCase):
    def setUp(self):
        """Inizializza i componenti necessari per il test"""
        self.processor = CoalescenceProcessor()
        self.nlp = NLPProcessor()
        self.user_profile = UserProfile()
        
    def test_initial_conversation(self):
        """Simula una conversazione iniziale con ALLMA"""
        print("\n=== Test Conversazione Iniziale con ALLMA ===\n")
        
        # Prima interazione - Saluto
        user_input = "Ciao! Sono Erik, piacere di conoscerti."
        print(f"Utente: {user_input}")
        
        # Crea la goccia di esperienza
        droplet = self.processor.create_droplet(
            content=user_input,
            context={
                "type": "greeting",
                "timestamp": time.time(),
                "is_first_interaction": True
            }
        )
        
        # Analizza il sentiment
        sentiment = self.nlp.analyze_sentiment(user_input)
        print(f"Sentiment rilevato: {sentiment}")
        
        # Genera la risposta
        response = self.processor.generate_response({"content": user_input, "context": droplet.context})
        print(f"ALLMA: {response['content']}\n")
        
        # Seconda interazione - Domanda sugli interessi
        user_input = "Mi piace molto la tecnologia e l'intelligenza artificiale. Tu che interessi hai?"
        print(f"Utente: {user_input}")
        
        droplet = self.processor.create_droplet(
            content=user_input,
            context={
                "type": "interests_sharing",
                "timestamp": time.time(),
                "topics": ["tecnologia", "intelligenza artificiale"]
            }
        )
        
        sentiment = self.nlp.analyze_sentiment(user_input)
        print(f"Sentiment rilevato: {sentiment}")
        
        response = self.processor.generate_response({"content": user_input, "context": droplet.context})
        print(f"ALLMA: {response['content']}\n")
        
        # Terza interazione - Domanda sulla capacità di apprendimento
        user_input = "Come funziona il tuo processo di apprendimento?"
        print(f"Utente: {user_input}")
        
        droplet = self.processor.create_droplet(
            content=user_input,
            context={
                "type": "learning_inquiry",
                "timestamp": time.time(),
                "topic": "self_learning"
            }
        )
        
        sentiment = self.nlp.analyze_sentiment(user_input)
        print(f"Sentiment rilevato: {sentiment}")
        
        response = self.processor.generate_response({"content": user_input, "context": droplet.context})
        print(f"ALLMA: {response['content']}\n")
        
        # Verifica che le risposte siano appropriate
        self.assertIsNotNone(response)
        self.assertIn('content', response)
        self.assertIn('emotional_state', response)
        
        # Verifica che il profilo utente sia stato aggiornato
        user_data = self.user_profile.get_profile_data()
        self.assertIsNotNone(user_data)
        self.assertIn('interests', user_data)
        self.assertIn('interaction_history', user_data)
        
        print("=== Fine Test Conversazione Iniziale ===\n")

if __name__ == '__main__':
    unittest.main()
