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

def test_auto_confidence_boost():
    print("=== TEST FEEDBACK AUTOMATICO - EVOLUZIONE CONFIDENZA ===")
    
    # 1. Inizializzazione
    print("\n1. Inizializzazione Core...")
    allma = ALLMACore(mobile_mode=True)
    allma.start_conversation("test_user_boost")
    
    test_topic = "python"
    known_answer = "Python è un linguaggio di programmazione interpretato e ad alto livello."
    test_query = "Cos'è Python?"
    
    # 2. Inietta conoscenza con confidenza MEDIA
    print(f"\n2. Inietto conoscenza con confidenza MEDIUM sul topic '{test_topic}'...")
    unit = LearningUnit(
        topic=test_topic,
        content=known_answer,
        source="test_boost",
        confidence=ConfidenceLevel.MEDIUM,  # 2 = MEDIUM
        timestamp=datetime.now()
    )
    allma.incremental_learner.add_learning_unit(unit)
    
    # Verifica stato iniziale
    state = allma.incremental_learner.get_knowledge_state(test_topic)
    print(f"Stato iniziale: Confidenza = {state.confidence.name} ({state.confidence.value})")
    
    # 3. Simula 3 risposte indipendenti
    print("\n3. Simulo 3 risposte indipendenti per triggerare l'evoluzione...")
    for i in range(1, 4):
        print(f"\n--- Risposta {i}/3 ---")
        # Chiama record_success direttamente (simuliamo che ALLMA abbia risposto)
        boosted = allma.incremental_learner.record_success(test_topic, threshold=3)
        current_state = allma.incremental_learner.get_knowledge_state(test_topic)
        print(f"Successo registrato. Confidenza: {current_state.confidence.name} ({current_state.confidence.value})")
        
        if boosted:
            print(f"✅ EVOLUZIONE TRIGGERED! Confidenza aumentata.")
    
    # 4. Verifica finale
    final_state = allma.incremental_learner.get_knowledge_state(test_topic)
    print(f"\n4. Stato finale:")
    print(f"Confidenza: {final_state.confidence.name} ({final_state.confidence.value})")
    
    if final_state.confidence == ConfidenceLevel.HIGH:
        print("\n✅ TEST PASSATO: La confidenza è aumentata automaticamente a HIGH!")
    else:
        print(f"\n❌ TEST FALLITO: Confidenza finale = {final_state.confidence.name} (atteso: HIGH)")

if __name__ == "__main__":
    test_auto_confidence_boost()
