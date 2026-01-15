"""
Demo completa di ALLMA che simula un mese di conversazioni.
Utilizza tutti i moduli principali del sistema per creare un'esperienza realistica.
"""

from datetime import datetime, timedelta
import random
from typing import Dict, Any, List
import json

from core.advanced_memory_system import AdvancedMemorySystem
from core.cognitive_processor import EnhancedCognitiveProcessor
from core.knowledge_base import KnowledgeBase
from core.language_understanding import LanguageUnderstanding
from core.personality_coalescence import PersonalityCore, CoalescenceProcessor
from core.personalization_integration import PersonalizationIntegration, IntegratedALLMA
from core.reasoning_engine import ReasoningEngine
from core.response_generator import ResponseGenerator
from core.user_profile import UserProfile, UserPreferences

class ALLMACompleteDemo:
    def __init__(self):
        # Inizializzazione della base di conoscenza (necessaria per altri moduli)
        self.knowledge_base = KnowledgeBase()
        
        # Inizializzazione dei moduli di base
        self.memory_system = AdvancedMemorySystem()
        self.cognitive_processor = EnhancedCognitiveProcessor()
        self.language_understanding = LanguageUnderstanding()
        
        # Inizializzazione del sistema di personalità
        self.personality = PersonalityCore()
        self.coalescence_processor = CoalescenceProcessor()
        
        # Inizializzazione del profilo utente e preferenze
        self.user_preferences = UserPreferences(
            communication_style='casual',
            response_length='medium',
            interaction_frequency='high',
            emotional_sensitivity=0.7,
            social_engagement=0.8,
            favorite_topics=["tecnologia", "arte", "scienza", "filosofia"]
        )
        self.user_profile = UserProfile()
        
        # Inizializzazione dei sistemi che dipendono da knowledge_base
        self.reasoning = ReasoningEngine(knowledge_base=self.knowledge_base)
        self.response_gen = ResponseGenerator(knowledge_base=self.knowledge_base)
        
        # Inizializzazione dei sistemi di integrazione
        self.personalization = PersonalizationIntegration()
        self.integrated_allma = IntegratedALLMA()
        
        # Stato iniziale di ALLMA
        self.allma_state = {
            "emotional_state": "curious",
            "trust_level": 0.5,
            "engagement_level": 0.7,
            "knowledge_depth": 0.3,
            "relationship_phase": "initial",
            "conversation_history": [],
            "daily_interactions": 0,
            "total_interactions": 0
        }
        
        # Temi di conversazione per il mese
        self.conversation_themes = {
            "week1": [
                "conoscenza_iniziale",
                "interessi_personali",
                "vita_quotidiana",
                "hobby_passioni"
            ],
            "week2": [
                "approfondimento_emotivo",
                "esperienze_passate",
                "obiettivi_futuri",
                "sfide_personali"
            ],
            "week3": [
                "discussioni_profonde",
                "filosofia_vita",
                "crescita_personale",
                "relazioni_umane"
            ],
            "week4": [
                "progetti_comuni",
                "riflessioni_progresso",
                "impatto_sociale",
                "visione_futuro"
            ]
        }
        
    def process_interaction(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Elabora l'input dell'utente utilizzando tutti i moduli di ALLMA."""
        
        # Comprensione del linguaggio
        intent_analysis = self.language_understanding.detect_intent(user_input)
        
        # Analisi cognitiva (passa il testo originale)
        cognitive_analysis = self.cognitive_processor.process_input(user_input)
        
        # Arricchisce l'analisi cognitiva con l'intento
        cognitive_analysis['intent'] = intent_analysis
        
        # Recupero conoscenze rilevanti
        relevant_knowledge = {}
        for topic in cognitive_analysis.get('topics', []):
            knowledge = self.knowledge_base.get_fact(topic)
            if knowledge:
                relevant_knowledge[topic] = knowledge
        
        # Elaborazione della memoria
        # Prima aggiungiamo la nuova memoria
        self.memory_system.add_memory(
            content=user_input,
            context=context,
            emotional_state={'valence': 0.0, 'arousal': 0.0},  # Neutro di default
            importance=0.5  # Importanza media di default
        )
        
        # Poi recuperiamo le memorie rilevanti
        memory_context = {
            'memories': self.memory_system.get_relevant_memories(context),
            'stats': self.memory_system.get_memory_stats()
        }
        
        # Ragionamento e decisione
        # 1. Estrae entità e relazioni
        entities = self.reasoning.extract_entities(user_input)
        relations = self.reasoning.identify_relations(user_input)
        
        # 2. Recupera fatti rilevanti
        facts = self.reasoning.retrieve_relevant_facts(entities, relations)
        
        # 3. Estrae premesse e trae conclusioni
        premises = self.reasoning.extract_premises(user_input)
        conclusion = self.reasoning.draw_conclusion(premises)
        
        # 4. Valuta la confidenza della conclusione
        confidence = self.reasoning.evaluate_confidence(conclusion)
        
        # Risultato finale del ragionamento
        reasoning_result = {
            'entities': entities,
            'relations': relations,
            'facts': facts,
            'conclusion': conclusion,
            'confidence': confidence
        }
        
        # Elaborazione personalità
        # 1. Crea una nuova memoria dall'esperienza
        droplet = {
            'content': user_input,
            'context': {'reasoning': reasoning_result}
        }
        
        # 2. Processa l'esperienza attraverso il sistema di personalità
        self.coalescence_processor.process_droplet(droplet)
        
        # 3. Ottiene lo stato attuale della personalità
        personality_state = self.coalescence_processor.get_current_personality_state()
        
        # 4. Genera una risposta appropriata
        response_text = self.coalescence_processor.generate_response(droplet)
        coalescence_result = {
            'text': response_text,
            'emotional_state': personality_state.get('current_emotion', 'neutral'),
            'personality': personality_state
        }
        
        # Generazione della risposta finale
        final_response = self.response_gen.generate_response(
            {
                'valid': True,  # La risposta è valida perché è stata generata da CoalescenceProcessor
                'statement': coalescence_result['text'],  # Il testo personalizzato
                'confidence': coalescence_result.get('personality', {}).get('traits', {}).get('confidence', 0.8)  # Confidenza basata sui tratti della personalità
            },
            context
        )
        
        # Prepara il risultato finale
        result = {
            "text": final_response,
            "emotional_state": coalescence_result['emotional_state'],
            "trust_level": self.allma_state["trust_level"],
            "knowledge_depth": self.allma_state["knowledge_depth"],
            "emotional_impact": 0.8  # Impostato a un valore alto per aumentare la fiducia
        }
        
        # Aggiorna lo stato di ALLMA
        self._update_allma_state(result, context)
        
        return result
        
    def _update_allma_state(self, result: Dict[str, Any], context: Dict[str, Any]):
        """Aggiorna lo stato interno di ALLMA dopo ogni interazione."""
        # Aggiorna contatori
        self.allma_state["daily_interactions"] += 1
        self.allma_state["total_interactions"] += 1
        
        # Aggiorna livelli di coinvolgimento e fiducia
        if result.get("emotional_impact", 0) > 0.7:
            self.allma_state["trust_level"] = min(1.0, self.allma_state["trust_level"] + 0.05)
        
        # Aggiorna fase della relazione
        if self.allma_state["total_interactions"] > 10:
            self.allma_state["relationship_phase"] = "established"
        elif self.allma_state["total_interactions"] > 5:
            self.allma_state["relationship_phase"] = "developing"
        
        # Aggiorna profondità di conoscenza
        self.allma_state["knowledge_depth"] = min(
            1.0,
            self.allma_state["knowledge_depth"] + 0.01
        )

def simulate_one_month():
    """Simula un mese di conversazioni con ALLMA."""
    allma = ALLMACompleteDemo()
    start_date = datetime.now()
    
    # Scenari di conversazione per ogni settimana del mese
    conversation_scenarios = {
        # SETTIMANA 1: Conoscenza Iniziale e Apprendimento Base
        "week1": [
            {
                "day": 1,
                "conversations": [
                    {
                        "user": "Ciao! Sono Marco, è la prima volta che parlo con te.",
                        "context": {"first_meeting": True, "time": "morning"}
                    },
                    {
                        "user": "Sai cosa significa la parola 'arte'?",
                        "context": {"topic": "learning_basics", "time": "morning"}
                    },
                    {
                        "user": "L'arte è quando le persone creano qualcosa di bello, come dipinti o sculture. Hai capito?",
                        "context": {"topic": "teaching_basics", "time": "afternoon"}
                    }
                ]
            },
            {
                "day": 2,
                "conversations": [
                    {
                        "user": "Ti ricordi cosa ti ho spiegato ieri sull'arte?",
                        "context": {"topic": "memory_check", "time": "morning"}
                    },
                    {
                        "user": "Esatto! E sai che ci sono tanti tipi diversi di arte? Per esempio la pittura, la scultura, la musica...",
                        "context": {"topic": "expanding_knowledge", "time": "afternoon"}
                    }
                ]
            },
            {
                "day": 3,
                "conversations": [
                    {
                        "user": "Oggi ti voglio parlare della musica. La musica è arte fatta con i suoni. Ti piacerebbe saperne di più?",
                        "context": {"topic": "new_concept", "time": "morning"}
                    },
                    {
                        "user": "La musica può essere allegra o triste, veloce o lenta. Le persone la usano per esprimere emozioni.",
                        "context": {"topic": "teaching_concepts", "time": "afternoon"}
                    }
                ]
            }
        ],
        # SETTIMANA 2: Approfondimento Graduale
        "week2": [
            {
                "day": 8,
                "conversations": [
                    {
                        "user": "Mi piacerebbe sapere cosa hai imparato finora sulla musica.",
                        "context": {"topic": "knowledge_review", "time": "morning"}
                    },
                    {
                        "user": "Molto bene! Ora ti spiego che in ogni cultura le persone fanno musica in modo diverso.",
                        "context": {"topic": "expanding_knowledge", "time": "afternoon"}
                    }
                ]
            }
        ]
    }
    
    print("\n=== Inizio Simulazione Un Mese di Conversazioni ===\n")
    
    for week, days in conversation_scenarios.items():
        print(f"\n=== {week.upper()} ===\n")
        
        for day in days:
            current_date = start_date + timedelta(days=day["day"]-1)
            print(f"\n--- Giorno {day['day']} ({current_date.strftime('%d/%m/%Y')}) ---\n")
            
            for conv in day["conversations"]:
                print(f"\nUtente ({conv['context']['time']}): {conv['user']}")
                
                # Processa l'input attraverso tutti i moduli di ALLMA
                response = allma.process_interaction(conv['user'], conv['context'])
                
                # Mostra la risposta di ALLMA
                print(f"ALLMA: {response.get('text', 'Mi dispiace, non ho capito.')}")
                print(f"Stato Emotivo: {response.get('emotional_state', 'neutral')}")
                print(f"Livello di Fiducia: {allma.allma_state['trust_level']:.2f}")
                print(f"Profondità Conoscenza: {allma.allma_state['knowledge_depth']:.2f}")
                print("-" * 50)
                
    print("\n=== Fine Simulazione Un Mese di Conversazioni ===")
    print(f"\nStatistiche Finali:")
    print(f"Totale Interazioni: {allma.allma_state['total_interactions']}")
    print(f"Livello Finale di Fiducia: {allma.allma_state['trust_level']:.2f}")
    print(f"Profondità Finale Conoscenza: {allma.allma_state['knowledge_depth']:.2f}")
    print(f"Fase Relazione: {allma.allma_state['relationship_phase']}")

if __name__ == "__main__":
    simulate_one_month()
