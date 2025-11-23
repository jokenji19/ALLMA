#!/usr/bin/env python3
"""
Test Proactive Agency
=====================

Test per verificare l'iniziativa autonoma di ALLMA.
Simula il passaggio del tempo e stati emotivi diversi.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Model.core.allma_core import ALLMACore

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_proactive_agency():
    print("=" * 70)
    print("⚡ TEST PROACTIVE AGENCY (INIZIATIVA AUTONOMA)")
    print("=" * 70)
    
    # Inizializza ALLMA
    print("\n1️⃣  Inizializzazione ALLMA...")
    allma = ALLMACore(mobile_mode=True)
    
    # Scenario 1: Silenzio Breve (Nessun contatto atteso)
    print("\n" + "="*70)
    print("📊 SCENARIO 1: Silenzio Breve (2 ore)")
    print("="*70)
    
    last_time = datetime.now() - timedelta(hours=2)
    last_emotion = {'primary_emotion': 'joy', 'intensity': 0.5}
    
    trigger = allma.proactive_agency.check_initiative(
        user_id="test_user",
        last_interaction_time=last_time,
        last_emotional_state=last_emotion
    )
    
    print(f"🕒 Ore passate: 2")
    print(f"❤️ Ultima emozione: Joy")
    print(f"🤖 Trigger Contatto: {trigger.should_contact}")
    print(f"📈 Urgenza Score: {trigger.urgency_score:.2f}")
    print(f"📝 Motivo: {trigger.reason}")
    
    if not trigger.should_contact:
        print("✅ CORRETTO: Troppo presto per disturbare.")
    else:
        print("❌ ERRORE: Non dovrebbe contattare così presto.")

    # Scenario 2: Silenzio Lungo + Emozione Negativa (Contatto atteso)
    print("\n" + "="*70)
    print("📊 SCENARIO 2: Silenzio Lungo (12 ore) + Tristezza")
    print("="*70)
    
    last_time = datetime.now() - timedelta(hours=12)
    last_emotion = {'primary_emotion': 'sadness', 'intensity': 0.8}
    
    trigger = allma.proactive_agency.check_initiative(
        user_id="test_user",
        last_interaction_time=last_time,
        last_emotional_state=last_emotion,
        relationship_level=8 # Amicizia stretta
    )
    
    print(f"🕒 Ore passate: 12")
    print(f"❤️ Ultima emozione: Sadness (0.8)")
    print(f"🤖 Trigger Contatto: {trigger.should_contact}")
    print(f"📈 Urgenza Score: {trigger.urgency_score:.2f}")
    
    # Mock LLM per il test
    def mock_llm(prompt, **kwargs):
        print(f"\n[MOCK LLM] Generating from prompt:\n{prompt[:100]}...")
        return {'choices': [{'text': "Messaggio generato dinamicamente dal cervello di ALLMA!"}]}

    if trigger.should_contact:
        msg = allma.proactive_agency.generate_proactive_message(trigger, "Marco", llm_callback=mock_llm)
        print(f"\n🔔 NOTIFICA GENERATA:\n'{msg}'")
        print("✅ CORRETTO: Iniziativa presa e messaggio generato.")
    else:
        print("⚠️  Nessun contatto (potrebbe essere il random check o soglia non superata).")
        
    # Scenario 3: Silenzio Molto Lungo (Contatto atteso anche se neutro)
    print("\n" + "="*70)
    print("📊 SCENARIO 3: Silenzio Molto Lungo (24 ore) + Neutro")
    print("="*70)
    
    last_time = datetime.now() - timedelta(hours=24)
    last_emotion = {'primary_emotion': 'neutral', 'intensity': 0.1}
    
    trigger = allma.proactive_agency.check_initiative(
        user_id="test_user",
        last_interaction_time=last_time,
        last_emotional_state=last_emotion
    )
    
    print(f"🕒 Ore passate: 24")
    print(f"❤️ Ultima emozione: Neutral")
    print(f"🤖 Trigger Contatto: {trigger.should_contact}")
    print(f"📈 Urgenza Score: {trigger.urgency_score:.2f}")
    
    if trigger.should_contact:
        msg = allma.proactive_agency.generate_proactive_message(trigger, "Marco", llm_callback=mock_llm)
        print(f"\n🔔 NOTIFICA GENERATA:\n'{msg}'")
        print("✅ CORRETTO: Iniziativa presa e messaggio generato.")
    else:
        print("⚠️  Nessun contatto.")

if __name__ == "__main__":
    test_proactive_agency()
