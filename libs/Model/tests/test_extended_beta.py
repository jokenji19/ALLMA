import unittest
from datetime import datetime, timedelta
import random
import json
import time
from typing import List, Dict
from Model.core.personality_coalescence import CoalescenceProcessor, EmotionalState, EmotionalResponse
from Model.core.nlp_processor import NLPProcessor
from Model.core.user_profile import UserProfile
from Model.core.knowledge_memory import KnowledgeMemory
from Model.core.learning_feedback import FeedbackType

class TestExtendedBeta(unittest.TestCase):
    def setUp(self):
        """Inizializza i componenti necessari per il test"""
        self.processor = CoalescenceProcessor()
        self.nlp = NLPProcessor()
        self.user_profile = UserProfile()
        self.knowledge = KnowledgeMemory(nlp=self.nlp)
        
        # Carica scenari di conversazione predefiniti
        self.conversation_scenarios = {
            'technical': [
                ("Come funziona il deep learning?", "learning_inquiry"),
                ("Quali sono i vantaggi del transfer learning?", "technical_question"),
                ("Mi spieghi la differenza tra supervised e unsupervised learning?", "technical_question"),
                ("Come gestisci la memoria a lungo termine?", "technical_question")
            ],
            'personal': [
                ("Come ti senti oggi?", "emotional_inquiry"),
                ("Qual è la tua opinione sulla coscienza artificiale?", "philosophical"),
                ("Ti piace imparare cose nuove?", "personal_question"),
                ("Come gestisci le emozioni?", "emotional_inquiry")
            ],
            'project': [
                ("Possiamo lavorare insieme su un progetto di ML?", "project_proposal"),
                ("Come possiamo migliorare questo algoritmo?", "technical_collaboration"),
                ("Hai suggerimenti per ottimizzare il codice?", "code_review"),
                ("Che ne pensi di questo approccio?", "feedback_request")
            ],
            'creative': [
                ("Inventiamo una storia insieme?", "creative_collaboration"),
                ("Come visualizzi i concetti astratti?", "conceptual_inquiry"),
                ("Puoi aiutarmi a brainstormare delle idee?", "ideation"),
                ("Che ne pensi dell'arte generativa?", "opinion_request")
            ]
        }
        
        # Definisci diversi profili utente per la simulazione
        self.user_profiles = [
            {"name": "Erik", "interests": ["AI", "deep learning", "robotica"], "style": "technical"},
            {"name": "Maria", "interests": ["arte", "creatività", "design"], "style": "creative"},
            {"name": "Luca", "interests": ["progetti", "sviluppo", "innovazione"], "style": "project"},
            {"name": "Sofia", "interests": ["filosofia", "etica", "psicologia"], "style": "personal"}
        ]
        
        # Definisci i concetti iniziali da insegnare ad ALLMA
        self.initial_concepts = {
            'deep_learning': {
                'description': """Il deep learning è un sottoinsieme del machine learning basato su reti neurali artificiali con multiple layer.
                               Le reti profonde possono apprendere gerarchie di feature sempre più astratte dai dati.""",
                'examples': ['Riconoscimento immagini con CNN', 'Traduzione automatica con Transformer'],
                'related': {'machine_learning', 'neural_networks', 'AI'}
            },
            'transfer_learning': {
                'description': """Il transfer learning è una tecnica che permette di riutilizzare un modello addestrato su un task 
                               come punto di partenza per un nuovo task correlato.""",
                'examples': ['Uso di ImageNet per classificazione custom', 'Fine-tuning di BERT'],
                'related': {'deep_learning', 'machine_learning', 'model_adaptation'}
            },
            'supervised_learning': {
                'description': """Nel supervised learning, il modello viene addestrato su dati etichettati, 
                               imparando a mappare input a output noti.""",
                'examples': ['Classificazione email spam/non-spam', 'Previsione prezzi case'],
                'related': {'machine_learning', 'training_data', 'labels'}
            }
        }
        
        # Scenari di conversazione per la fase di training
        self.training_scenarios = {
            'concept_explanation': [
                ("Lascia che ti spieghi come funziona il deep learning...", "learning_input"),
                ("Il transfer learning è una tecnica molto utile che...", "learning_input"),
                ("La differenza tra supervised e unsupervised learning è...", "learning_input")
            ],
            'concept_verification': [
                ("Puoi spiegarmi cosa hai capito del deep learning?", "learning_verification"),
                ("Come funziona il transfer learning secondo te?", "learning_verification"),
                ("Qual è la differenza tra supervised e unsupervised learning?", "learning_verification")
            ],
            'concept_application': [
                ("Come possiamo usare il deep learning per questo problema?", "learning_application"),
                ("Questo sarebbe un buon caso per il transfer learning?", "learning_application"),
                ("Quale approccio di learning useresti qui?", "learning_application")
            ]
        }
        
    def _initial_training_phase(self) -> None:
        """Fase iniziale di training dove gli utenti insegnano i concetti ad ALLMA"""
        print("\n=== Fase di Training Iniziale ===\n")
        
        for concept, info in self.initial_concepts.items():
            # Simula l'insegnamento del concetto
            print(f"\nInsegnamento del concetto: {concept}")
            
            # Imposta una confidenza iniziale più alta
            self.knowledge.learn_concept(
                concept=concept,
                description=info['description'],
                source="Erik",  # assumiamo che Erik sia l'esperto tecnico
                examples=info['examples'],
                related_concepts=info['related']
            )
            
            # Verifica la comprensione
            knowledge = self.knowledge.get_concept_knowledge(concept)
            print(f"Confidenza iniziale: {knowledge['confidence']:.2f}")
            
            # Simula più verifiche del concetto con alta probabilità di successo
            for _ in range(5):  # Aumentato il numero di verifiche
                success = random.random() < 0.9  # 90% di successo nelle verifiche
                self.knowledge.verify_concept(concept, success)
                
                # Aggiungi feedback positivo dopo ogni verifica riuscita
                if success:
                    self.knowledge.add_feedback(
                        concept=concept,
                        feedback_type=FeedbackType.VALIDATION,
                        content=f"Ottima comprensione di {concept}",
                        source="Erik",
                        context={'type': 'verification', 'quality': 'high'}
                    )
                
            # Aggiungi esempi pratici per rafforzare l'apprendimento
            for example in info['examples']:
                self.knowledge.add_feedback(
                    concept=concept,
                    feedback_type=FeedbackType.EXPANSION,
                    content=f"Esempio pratico di {concept}: {example}",
                    source="Erik",
                    context={'type': 'example', 'quality': 'high'}
                )
            
            # Mostra la confidenza finale
            knowledge = self.knowledge.get_concept_knowledge(concept)
            print(f"Confidenza dopo le verifiche: {knowledge['confidence']:.2f}")
            
        # Stampa statistiche di apprendimento
        stats = self.knowledge.get_learning_statistics()
        print("\nStatistiche di apprendimento:")
        print(f"Totale concetti appresi: {stats['total_concepts']}")
        print(f"Confidenza media: {stats['average_confidence']:.2f}")
        
    def _generate_daily_conversations(self, day: int, num_conversations: int) -> List[Dict]:
        """Genera conversazioni casuali per un giorno, utilizzando la conoscenza acquisita"""
        conversations = []
        
        for i in range(num_conversations):
            # Seleziona un profilo utente casuale
            user = random.choice(self.user_profiles)
            
            # Crea la conversazione
            conversation = {
                'day': day,
                'conversation_id': f"conv_{day}_{i}",
                'user': user['name'],
                'timestamp': time.time(),
                'messages': []
            }
            
            # Genera 3-7 scambi per conversazione
            num_exchanges = random.randint(3, 7)
            
            # Seleziona un concetto principale per la conversazione
            main_concept = random.choice(list(self.initial_concepts.keys()))
            knowledge = self.knowledge.get_concept_knowledge(main_concept)
            
            for j in range(num_exchanges):
                if j == 0:
                    # Prima interazione sulla comprensione del concetto
                    user_msg = f"Cosa ne pensi di {main_concept}?"
                    msg_type = "concept_discussion"
                else:
                    # Interazioni successive più specifiche
                    if random.random() < 0.3:
                        # 30% di probabilità di esplorare concetti correlati
                        related = self.knowledge.get_related_concepts(main_concept)
                        if related:
                            related_concept = random.choice(related)
                            user_msg = f"Come si collega {main_concept} a {related_concept}?"
                            msg_type = "concept_relationship"
                        else:
                            user_msg = f"Puoi farmi un esempio pratico di {main_concept}?"
                            msg_type = "example_request"
                    else:
                        # Altrimenti, approfondisci il concetto corrente
                        if knowledge['examples']:
                            example = random.choice(knowledge['examples'])
                            user_msg = f"Puoi spiegarmi meglio questo esempio: {example}?"
                            msg_type = "example_explanation"
                        else:
                            user_msg = f"Puoi farmi un esempio pratico di {main_concept}?"
                            msg_type = "example_request"
                
                # Crea il contesto del messaggio
                context = {
                    'type': msg_type,
                    'timestamp': time.time(),
                    'user_profile': user,
                    'concept': main_concept,
                    'conversation_history': len(conversation['messages'])
                }
                
                # Genera la risposta di ALLMA utilizzando la conoscenza acquisita
                if knowledge and knowledge['confidence'] > 0.5:
                    response_content = self._generate_knowledgeable_response(
                        main_concept, msg_type, knowledge, context
                    )
                    
                    # Aggiungi feedback positivo per rinforzare l'apprendimento
                    if random.random() < 0.8:  # 80% di probabilità di feedback positivo
                        self.knowledge.add_feedback(
                            concept=main_concept,
                            feedback_type=FeedbackType.VALIDATION,
                            content=f"Ottima spiegazione di {main_concept}",
                            source=user['name'],
                            context={'type': 'conversation', 'response_quality': 'high'}
                        )
                else:
                    # Se la confidenza è bassa, ALLMA chiede aiuto
                    response_content = (
                        f"Sto ancora imparando su {main_concept}. "
                        "Potresti aiutarmi a capire meglio condividendo la tua esperienza?"
                    )
                    
                    # L'utente fornisce nuove informazioni
                    if main_concept in self.initial_concepts:
                        info = self.initial_concepts[main_concept]
                        
                        # Aggiungi feedback espansivo
                        self.knowledge.add_feedback(
                            concept=main_concept,
                            feedback_type=FeedbackType.EXPANSION,
                            content=info['description'],
                            source=user['name'],
                            context={
                                'type': 'teaching',
                                'examples': info['examples'],
                                'related_concepts': info['related']
                            }
                        )
                        
                        # Aggiungi anche un feedback di validazione
                        if random.random() < 0.7:  # 70% di probabilità di feedback positivo
                            self.knowledge.add_feedback(
                                concept=main_concept,
                                feedback_type=FeedbackType.VALIDATION,
                                content=f"Buona comprensione di base di {main_concept}",
                                source=user['name'],
                                context={'type': 'validation', 'quality': 'good'}
                            )
                
                # Analizza il sentiment e genera la risposta
                sentiment = self.nlp.analyze_sentiment(user_msg)
                response = {
                    'content': response_content,
                    'emotional_state': EmotionalState.CURIOSITY.value,
                    'confidence': knowledge['confidence'] if knowledge else 0.0
                }
                
                # Aggiungi lo scambio alla conversazione
                conversation['messages'].append({
                    'user_message': user_msg,
                    'allma_response': response['content'],
                    'sentiment': sentiment,
                    'emotional_state': response.get('emotional_state'),
                    'context': context,
                    'confidence': response['confidence']
                })
                
            conversations.append(conversation)
            
        return conversations
        
    def _generate_knowledgeable_response(self, concept: str, msg_type: str, 
                                       knowledge: Dict, context: Dict) -> str:
        """Genera una risposta basata sulla conoscenza acquisita"""
        if msg_type == "concept_discussion":
            return (
                f"{knowledge['description']}\n\n"
                f"Posso farti alcuni esempi: {', '.join(knowledge['examples'][:2])}"
            )
        elif msg_type == "concept_relationship":
            related = knowledge['related_concepts']
            if related:
                concepts_desc = [
                    self.knowledge.get_concept_knowledge(rel)['description'][:100] + "..."
                    for rel in related[:2]
                    if self.knowledge.get_concept_knowledge(rel)
                ]
                return (
                    f"{concept} è collegato a diversi concetti. "
                    f"In particolare: {'. '.join(concepts_desc)}"
                )
            return f"Sto ancora esplorando le connessioni tra {concept} e altri concetti."
        elif msg_type == "example_explanation":
            return (
                f"Questo esempio illustra un aspetto importante di {concept}. "
                f"{knowledge['description']}\n\n"
                "Posso spiegarti altri aspetti se sei interessato."
            )
        else:
            return (
                f"Basandomi sulla mia comprensione di {concept}, "
                f"posso dirti che {knowledge['description'][:150]}... "
                "Vuoi che approfondisca qualche aspetto specifico?"
            )
        
    def _save_conversations(self, conversations: List[Dict], filename: str):
        """Salva le conversazioni su file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, indent=4, ensure_ascii=False)
            
    def _analyze_conversations(self, conversations: List[Dict]) -> Dict:
        """Analizza le conversazioni per statistiche e metriche"""
        stats = {
            'total_conversations': len(conversations),
            'total_messages': 0,
            'sentiment_distribution': {'positive': 0, 'negative': 0, 'neutral': 0},
            'topic_distribution': {},
            'user_engagement': {},
            'avg_conversation_length': 0
        }
        
        for conv in conversations:
            stats['total_messages'] += len(conv['messages'])
            stats['user_engagement'][conv['user']] = stats['user_engagement'].get(conv['user'], 0) + 1
            
            for msg in conv['messages']:
                # Analizza sentiment
                if msg['sentiment']['compound'] > 0.05:
                    stats['sentiment_distribution']['positive'] += 1
                elif msg['sentiment']['compound'] < -0.05:
                    stats['sentiment_distribution']['negative'] += 1
                else:
                    stats['sentiment_distribution']['neutral'] += 1
                    
                # Analizza topic
                context_type = msg['context']['type']
                stats['topic_distribution'][context_type] = stats['topic_distribution'].get(context_type, 0) + 1
                
        stats['avg_conversation_length'] = stats['total_messages'] / stats['total_conversations']
        
        return stats
        
    def test_one_month_beta(self):
        """Esegue un test beta di un mese con fase di training iniziale"""
        print("\n=== Inizio Test Beta di Un Mese ===\n")
        
        # Fase 1: Training iniziale
        self._initial_training_phase()
        
        # Fase 2: Conversazioni giornaliere
        all_conversations = []
        start_date = datetime(2025, 1, 22)  # Data corrente
        
        for day in range(30):  # Un mese di test
            current_date = start_date + timedelta(days=day)
            print(f"\nGiorno {day + 1}: {current_date.strftime('%Y-%m-%d')}")
            
            # Genera un numero casuale di conversazioni (minimo 20)
            num_conversations = random.randint(20, 30)
            
            # Genera le conversazioni del giorno
            daily_conversations = self._generate_daily_conversations(day + 1, num_conversations)
            all_conversations.extend(daily_conversations)
            
            print(f"Generate {num_conversations} conversazioni")
            
            # Mostra alcuni esempi di conversazione
            sample_conv = random.choice(daily_conversations)
            print(f"\nEsempio di conversazione con {sample_conv['user']}:")
            for msg in sample_conv['messages'][:2]:  # Mostra solo i primi 2 scambi per brevità
                print(f"Utente: {msg['user_message']}")
                print(f"ALLMA: {msg['allma_response']}")
                print(f"Confidenza: {msg['confidence']:.2f}\n")
                
        # Salva tutte le conversazioni
        self._save_conversations(all_conversations, 'beta_test_conversations.json')
        
        # Analizza i risultati
        stats = self._analyze_conversations(all_conversations)
        
        print("\n=== Statistiche del Test Beta ===")
        print(f"Totale conversazioni: {stats['total_conversations']}")
        print(f"Totale messaggi: {stats['total_messages']}")
        print(f"Media messaggi per conversazione: {stats['avg_conversation_length']:.2f}")
        print("\nDistribuzione sentiment:")
        for sentiment, count in stats['sentiment_distribution'].items():
            print(f"- {sentiment}: {count}")
        print("\nDistribuzione topic:")
        for topic, count in stats['topic_distribution'].items():
            print(f"- {topic}: {count}")
        print("\nEngagement utenti:")
        for user, count in stats['user_engagement'].items():
            print(f"- {user}: {count} conversazioni")
            
        # Statistiche finali di apprendimento
        final_stats = self.knowledge.get_learning_statistics()
        print("\n=== Statistiche Finali di Apprendimento ===")
        print(f"Totale concetti: {final_stats['total_concepts']}")
        print(f"Confidenza media: {final_stats['average_confidence']:.2f}")
        print("Verifiche:")
        for stat, value in final_stats['verification_stats'].items():
            print(f"- {stat}: {value:.2f}")
            
        print("\n=== Fine Test Beta ===")
        
        # Verifica che il test abbia soddisfatto i requisiti minimi
        self.assertGreaterEqual(len(all_conversations), 600)  # Minimo 20 conversazioni * 30 giorni
        self.assertGreater(stats['avg_conversation_length'], 3)  # Media messaggi per conversazione
        self.assertGreaterEqual(round(final_stats['average_confidence'], 6), 0.7)  # Buona confidenza sui concetti
        
if __name__ == '__main__':
    unittest.main()
