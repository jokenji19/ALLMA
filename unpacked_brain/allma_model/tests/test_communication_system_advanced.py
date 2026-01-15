import unittest
from allma_model.incremental_learning.communication_system import (
    CommunicationSystem,
    CommunicationMode,
    Message,
    DialogContext,
    IntentType,
    SentimentType
)
from allma_model.incremental_learning.emotional_system import Emotion, EmotionType

class TestCommunicationSystemAdvanced(unittest.TestCase):
    def setUp(self):
        self.system = CommunicationSystem()
        
    def test_context_aware_response(self):
        """Test della generazione di risposte consapevoli del contesto"""
        context = self.system.create_context("test_topic", CommunicationMode.NATURAL)
        self.system.update_context(context, "Mi chiamo Mario")
        
        message = Message(
            content="Come mi chiamo?",
            intent=IntentType.QUESTION,
            sentiment=SentimentType.NEUTRAL,
            entities={"name": "Mario"},
            context=context
        )
        
        response = self.system._generate_base_response(message)
        self.assertIn("Mario", response)
        
    def test_emotional_response_adaptation(self):
        """Test dell'adattamento della risposta in base all'emozione"""
        input_text = "Non riesco a risolvere questo problema"
        emotion = Emotion(EmotionType.FRUSTRATION, 0.8, -0.6)
        
        response = self.system.generate_response(
            input_text=input_text,
            emotion=emotion,
            mode=CommunicationMode.EMPATHETIC
        )
        
        self.assertIsNotNone(response)
        self.assertIn("frustrazione", response.content.lower())
        
    def test_communication_style_switching(self):
        """Test del cambio di stile di comunicazione"""
        input_text = "Come funziona questo sistema?"
        emotion = Emotion(EmotionType.CURIOSITY, 0.7, 0.3)
        
        # Test risposta tecnica
        technical_response = self.system.generate_response(
            input_text=input_text,
            emotion=emotion,
            mode=CommunicationMode.TECHNICAL
        )
        
        # Test risposta empatica
        empathetic_response = self.system.generate_response(
            input_text=input_text,
            emotion=emotion,
            mode=CommunicationMode.EMPATHETIC
        )
        
        self.assertNotEqual(technical_response.content, empathetic_response.content)
        self.assertIn("Input analizzato", technical_response.content)
        self.assertIn("senti", empathetic_response.content.lower())
        
    def test_complex_dialog_flow(self):
        """Test di un flusso di dialogo complesso"""
        context = self.system.create_context("supporto_tecnico", CommunicationMode.NATURAL)
        
        # Prima interazione
        message1 = Message(
            content="Ho un problema con il sistema",
            intent=IntentType.STATEMENT,
            sentiment=SentimentType.NEGATIVE,
            entities={},
            context=context
        )
        response1 = self.system._generate_base_response(message1)
        self.assertIn("problema", response1.lower())
        
        # Aggiorna il contesto
        self.system.update_context(context, message1.content)
        
        # Seconda interazione
        message2 = Message(
            content="Puoi aiutarmi a risolverlo?",
            intent=IntentType.REQUEST,
            sentiment=SentimentType.NEUTRAL,
            entities={},
            context=context
        )
        response2 = self.system._generate_base_response(message2)
        self.assertTrue(
            any(word in response2.lower() for word in ["aiut", "risol", "cert"])
        )
        
    def test_sentiment_based_response(self):
        """Test della risposta basata sul sentiment"""
        # Test sentiment positivo
        message_pos = Message(
            content="Fantastico, funziona tutto!",
            intent=IntentType.STATEMENT,
            sentiment=SentimentType.POSITIVE,
            entities={},
            context=DialogContext("test", CommunicationMode.NATURAL)
        )
        response_pos = self.system._generate_base_response(message_pos)
        self.assertTrue(
            any(word in response_pos.lower() for word in ["bene", "content", "piac"])
        )
        
        # Test sentiment negativo
        message_neg = Message(
            content="Non funziona niente, che frustrazione",
            intent=IntentType.STATEMENT,
            sentiment=SentimentType.NEGATIVE,
            entities={},
            context=DialogContext("test", CommunicationMode.NATURAL)
        )
        response_neg = self.system._generate_base_response(message_neg)
        self.assertTrue(
            any(word in response_neg.lower() for word in ["dispiace", "aiut", "risol"])
        )

if __name__ == '__main__':
    unittest.main()
