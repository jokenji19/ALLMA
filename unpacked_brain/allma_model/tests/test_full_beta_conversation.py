import unittest
import time
from typing import Dict, List, Any
from ..core.nlp_processor import NLPProcessor
from ..core.information_extractor import InformationExtractor
from ..core.knowledge_memory import KnowledgeMemory
from ..core.personality import Personality
from ..core.context_understanding import ContextUnderstandingSystem
from ..core.document_processor import DocumentProcessor
from ..core.response_generator import ResponseGenerator

class TestFullBetaConversation(unittest.TestCase):
    """Test completo del sistema ALLMA con conversazioni"""
    
    def setUp(self):
        """Inizializza tutti i componenti necessari per i test"""
        self.nlp = NLPProcessor()
        self.extractor = InformationExtractor()
        self.knowledge = KnowledgeMemory(nlp=self.nlp)
        self.personality = Personality()
        self.context = ContextUnderstandingSystem()
        self.doc_processor = DocumentProcessor()
        self.response_generator = ResponseGenerator(
            context_system=self.context,
            knowledge_memory=self.knowledge,
            personality=self.personality
        )
        
        # Aggiungi conoscenza di base sulle reti neurali
        self.knowledge.add_concept(
            concept="reti neurali",
            description="Le reti neurali sono modelli computazionali ispirati al funzionamento del cervello umano. "
                       "Sono composte da neuroni artificiali, organizzate in strati e hanno capacità di apprendimento automatico. "
                       "Vengono utilizzate per riconoscimento immagini, elaborazione linguaggio naturale e previsioni."
        )
        
        self.knowledge.add_concept(
            concept="deep learning",
            description="Il deep learning è una branca del machine learning basata su reti neurali profonde. "
                       "È parte del machine learning e utilizza reti neurali per l'apprendimento."
        )
        
    def simulate_conversation(self, conversation: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Simula una conversazione tra l'utente e ALLMA
        
        Args:
            conversation: Lista di messaggi dell'utente
            
        Returns:
            List[Dict[str, Any]]: Lista di messaggi con emozioni, contesto e confidenza
        """
        history = []
        
        for message in conversation:
            # Analizza il messaggio
            emotions = self.nlp.analyze_emotion(message['text'])
            context = self.context.get_current_context()
            
            # Aggiorna il contesto
            self.context.update_context(message['text'])
            
            # Integra la conoscenza
            confidence = self.knowledge.integrate_knowledge(message['text'], context)
            
            # Trova l'emozione dominante
            dominant_emotion = max(
                (e for e in emotions.items() if e[0] != 'sentiment'),
                key=lambda x: x[1]
            )[0]
            
            # Genera risposta contestuale
            response = self.response_generator.generate_contextual_response(
                message['text'],
                {
                    'current_topic': self.context.get_current_topic(),
                    'user_knowledge_level': context.get('knowledge_level', 'base'),
                    'current_emotion': dominant_emotion
                },
                history
            )
            
            # Registra il messaggio nella storia
            history.append({
                'text': message['text'],
                'response': response,
                'emotion': dominant_emotion,
                'context': context,
                'confidence': confidence,
                'emotions': emotions,
                'topic': self.context.get_current_topic()
            })
            
            # Aggiorna la personalità
            self.personality.update_personality(message['text'], emotions)
            
        return history
        
    def test_1_initial_learning_conversation(self):
        """Verifica la capacità di apprendimento iniziale attraverso una conversazione"""
        conversation = [
            {
                'text': "Ciao ALLMA, come stai?"
            },
            {
                'text': "Puoi spiegarmi cosa sono le reti neurali?"
            }
        ]
        
        history = self.simulate_conversation(conversation)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['emotion'], 'neutral')
        self.assertGreater(history[1]['confidence'], 0)
        self.assertIn('reti neurali', history[1]['response'].lower())
        
    def test_2_emotional_response_conversation(self):
        """Verifica l'integrazione delle risposte emotive attraverso una conversazione"""
        conversation = [
            {
                'text': "Sono molto felice di imparare con te!"
            },
            {
                'text': "Mi piace molto come mi aiuti a capire le cose."
            }
        ]
        
        history = self.simulate_conversation(conversation)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[1]['emotion'], 'joy')
        self.assertTrue(any(end in history[1]['response'] for end in [
            "È affascinante, vero?",
            "Che ne pensi?",
            "Ti piacerebbe saperne di più?",
            "È davvero interessante!",
            "Continua pure a farmi domande!"
        ]))
        
    def test_3_context_awareness_conversation(self):
        """Verifica la consapevolezza del contesto attraverso una conversazione"""
        conversation = [
            {
                'text': "Come funziona il deep learning?"
            },
            {
                'text': "Mi puoi fare un esempio pratico?"
            }
        ]
        
        history = self.simulate_conversation(conversation)
        context = history[-1]['context']
        self.assertIn('deep_learning', str(context))
        
    def test_4_knowledge_integration_conversation(self):
        """Verifica l'integrazione della conoscenza attraverso una conversazione"""
        conversation = [
            {
                'text': """
                Il machine learning è una branca dell'intelligenza artificiale
                che permette ai computer di imparare dai dati.
                """
            }
        ]
        
        history = self.simulate_conversation(conversation)
        self.assertGreater(
            history[0]['confidence'],
            0.0,
            "La confidenza dovrebbe essere maggiore di 0"
        )
        
    def test_5_personality_evolution_conversation(self):
        """Verifica l'evoluzione della personalità attraverso una conversazione"""
        conversation = [
            {
                'text': "Mi piace molto parlare con te!"
            },
            {
                'text': "Sei molto brava a spiegare le cose."
            }
        ]
        
        history = self.simulate_conversation(conversation)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[1]['emotion'], 'joy')
        
    def test_6_full_interaction_cycle_conversation(self):
        """Verifica un ciclo completo di interazione attraverso una conversazione"""
        conversation = [
            {
                'text': "Ho una domanda sul machine learning"
            },
            {
                'text': "Come funziona l'apprendimento supervisionato?"
            },
            {
                'text': "Grazie, ora ho capito meglio!"
            }
        ]
        
        history = self.simulate_conversation(conversation)
        context = history[-1]['context']
        self.assertIn('machine_learning', str(context))
        
    def test_7_long_term_learning_conversation(self):
        """Verifica l'apprendimento a lungo termine attraverso una conversazione"""
        conversation1 = [
            {
                'text': "Parliamo di deep learning"
            },
            {
                'text': "Come funzionano le reti neurali?"
            }
        ]
        
        conversation2 = [
            {
                'text': "Mi ricordo che abbiamo parlato di reti neurali"
            },
            {
                'text': "Puoi approfondire il discorso?"
            }
        ]
        
        # Prima conversazione per stabilire conoscenza iniziale
        history1 = self.simulate_conversation(conversation1)
        
        # Seconda conversazione per verificare memoria a lungo termine
        history2 = self.simulate_conversation(conversation2)
        
        # Verifica che la confidenza media sia alta
        confidences = [msg['confidence'] for msg in history2]
        average_confidence = sum(confidences) / len(confidences)
        self.assertGreaterEqual(average_confidence, 0.7)
        
        # Verifica che le risposte siano diverse e contestualizzate
        self.assertNotEqual(history1[1]['response'], history2[1]['response'])
        self.assertIn('approfondire', history2[1]['response'].lower())
        
if __name__ == '__main__':
    unittest.main()
