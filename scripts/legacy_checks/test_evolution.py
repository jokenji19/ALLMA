import sys
import os
import logging
from datetime import datetime

# Configura logging
logging.basicConfig(level=logging.INFO)

# Aggiungi la directory corrente al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Model.core.allma_core import ALLMACore
from Model.learning_system.incremental_learning import LearningUnit, ConfidenceLevel

def test_evolution():
    print("=== TEST SIMBIOSI EVOLUTIVA ===")
    
    # 1. Inizializzazione
    print("\n1. Inizializzazione Core...")
    allma = ALLMACore(mobile_mode=True)
    
    # Simuliamo che il modello sia caricato (o mockiamolo se necessario, ma qui vogliamo vedere il flusso)
    # Per il test, iniettiamo manualmente una conoscenza ad ALTA confidenza per simulare che abbia già imparato
    
    test_topic = "vita"
    test_query = "Qual è il senso della vita?"
    known_answer = "Il senso della vita è imparare ed evolversi costantemente."
    
    print(f"\n2. Fase 1: Ignoranza (Simulata)")
    # Verifichiamo che inizialmente NON sappia (o meglio, simuliamo il caso in cui sa)
    # In questo test specifico, voglio verificare che SE sa, NON usa Gemma.
    
    print(f"Iniettiamo conoscenza ad ALTA confidenza sul topic '{test_topic}'...")
    unit = LearningUnit(
        topic=test_topic,
        content=known_answer,
        source="test_evolution",
        confidence=ConfidenceLevel.HIGH, # 3 = HIGH
        timestamp=datetime.now()
    )
    allma.incremental_learner.add_learning_unit(unit)
    
    # DEBUG: Verifica diretta del learner
    print("\n--- DEBUG LEARNER ---")
    print(f"Topics in knowledge_base: {list(allma.incremental_learner.knowledge_base.keys())}")
    knowledge = allma.incremental_learner.find_related_knowledge(test_query, threshold=0.1) # Soglia bassissima per vedere cosa trova
    print(f"Knowledge found (threshold=0.1): {len(knowledge)}")
    for k in knowledge:
        print(f" - Topic: {k.topic}, Confidence: {k.confidence}, Content: {k.content[:50]}...")
    
    # Verifica diretta con get_knowledge_by_topic
    direct_knowledge = allma.incremental_learner.get_knowledge_by_topic(test_topic)
    print(f"\nDirect knowledge for topic '{test_topic}': {len(direct_knowledge)} items")
    for k in direct_knowledge:
        print(f" - Confidence: {k.get('confidence')}, Content: {k.get('content', '')[:50]}...")
    
    print("\n3. Fase 2: Test Indipendenza")
    print(f"Domanda Utente: '{test_query}'")
    
    # Start conversation
    allma.start_conversation("test_user_evo")
    
    # Process message
    # Se funziona, dovrebbe loggare "💡 ALLMA INDIPENDENTE" e NON chiamare Gemma
    response = allma.process_message(
        user_id="test_user_evo",
        conversation_id="test_chat_evo",
        message=test_query
    )
    
    print(f"\nRisposta Generata: {response.content}")
    print(f"Confidence: {response.confidence}")
    print(f"Knowledge Integrated: {response.knowledge_integrated}")
    
    if response.knowledge_integrated and response.confidence == 1.0:
        print("\n✅ TEST PASSATO: ALLMA ha risposto in modo INDIPENDENTE!")
        print(f"Risposta dalla memoria: {response.content[:100]}...")
    else:
        print("\n❌ TEST FALLITO: ALLMA ha usato Gemma o non ha trovato la memoria.")
        print(f"  - Knowledge Integrated: {response.knowledge_integrated}")
        print(f"  - Confidence: {response.confidence}")

if __name__ == "__main__":
    test_evolution()
