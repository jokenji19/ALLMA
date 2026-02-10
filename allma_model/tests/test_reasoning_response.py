import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Any
import pytest
from core.reasoning_engine import ReasoningEngine
from core.response_generator import ResponseGenerator
from core.knowledge_base import KnowledgeBase
from core.context_understanding import ContextUnderstandingSystem
from allma_model.personality_system.personality import Personality

def print_separator(title: str = ""):
    """Stampa un separatore con titolo opzionale"""
    print("\n" + "="*50)
    if title:
        print(f" {title} ")
        print("="*50)

def test_reasoning_response():
    """Test del sistema di ragionamento e risposta"""
    required = [
        "extract_entities",
        "identify_relations",
        "retrieve_relevant_facts",
        "extract_premises",
        "draw_conclusion",
        "evaluate_confidence",
        "get_performance_stats"
    ]
    if any(not hasattr(ReasoningEngine, name) for name in required):
        pytest.skip("API reasoning non disponibile")
    print_separator("Test Sistema di Ragionamento e Risposta")
    
    # Inizializza i componenti
    kb = KnowledgeBase()
    reasoning = ReasoningEngine(kb)
    context = ContextUnderstandingSystem()
    personality = Personality()
    response_gen = ResponseGenerator(
        context_system=context,
        knowledge_memory=kb,
        personality=personality
    )
    
    # Carica conoscenza di test
    kb.add_fact("Napoleone", {
        "tipo": "persona_storica",
        "ruolo": "imperatore",
        "nazione": "Francia",
        "periodo": "1769-1821",
        "eventi_chiave": ["battaglia_austerlitz", "codice_napoleonico"],
        "relazioni": {
            "successore": "Luigi XVIII",
            "moglie": "Giuseppina di Beauharnais"
        }
    })
    
    kb.add_fact("battaglia_austerlitz", {
        "tipo": "evento_storico",
        "data": "1805",
        "luogo": "Austerlitz",
        "partecipanti": ["Francia", "Russia", "Austria"],
        "risultato": "vittoria_francia"
    })
    
    # Test 1: Ragionamento Base
    print_separator("Fase 1: Ragionamento Base")
    
    query = "Chi era il successore di Napoleone?"
    print("\n👤 Query:", query)
    
    # Analisi e ragionamento
    entities = reasoning.extract_entities(query)
    relations = reasoning.identify_relations(query)
    facts = reasoning.retrieve_relevant_facts(entities, relations)
    
    print("\n🧠 Analisi:")
    print(f"  Entità: {entities}")
    print(f"  Relazioni: {relations}")
    print(f"  Fatti: {facts}")
    
    # Test 2: Inferenza
    print_separator("Fase 2: Inferenza")
    
    query = "Napoleone ha vinto ad Austerlitz?"
    print("\n👤 Query:", query)
    
    # Inferenza logica
    premises = reasoning.extract_premises(query)
    conclusion = reasoning.draw_conclusion(premises)
    confidence = reasoning.evaluate_confidence(conclusion)
    
    print("\n🔍 Inferenza:")
    print(f"  Premesse: {premises}")
    print(f"  Conclusione: {conclusion}")
    print(f"  Confidenza: {confidence:.2f}")
    
    # Test 3: Generazione Risposta
    print_separator("Fase 3: Generazione Risposta")
    
    context = {
        "previous_topic": "Napoleone",
        "user_knowledge_level": "intermedio",
        "interaction_style": "formale"
    }

    conversation_history = []  # Aggiungiamo una history vuota per il test
    response = response_gen.generate_contextual_response(
        query=conclusion['statement'],
        context=context,
        conversation_history=conversation_history
    )
    
    print("\n🤖 Risposta Generata:")
    print(f"  {response}")
    
    # Test 4: Adattamento al Contesto
    print_separator("Fase 4: Adattamento al Contesto")
    
    query = "Puoi spiegarmi in modo semplice cosa ha fatto Napoleone?"
    print("\n👤 Query:", query)
    
    # Adattamento della risposta
    user_context = {
        "knowledge_level": "base",
        "preferred_style": "informale",
        "interests": ["storia militare"]
    }
    
    adapted_response = response_gen.adapt_to_context(
        query,
        reasoning.retrieve_relevant_facts(["Napoleone"], []),
        user_context
    )
    
    print("\n🤖 Risposta Adattata:")
    print(f"  {adapted_response}")
    
    # Statistiche Finali
    print_separator("Statistiche Finali")
    
    stats = {
        "reasoning": reasoning.get_performance_stats(),
        "response": response_gen.get_performance_stats()
    }
    
    print("\n📊 Performance:")
    print(f"  Accuratezza Ragionamento: {stats['reasoning']['accuracy']:.2f}")
    print(f"  Qualità Risposte: {stats['response']['quality']:.2f}")
    print(f"  Tempo Medio Risposta: {stats['response']['avg_time']:.2f}s")

if __name__ == "__main__":
    test_reasoning_response()
