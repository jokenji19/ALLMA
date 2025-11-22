#!/usr/bin/env python3
"""
Test Emotional Milestones System
=================================

Test completo per verificare il funzionamento del sistema
di riflessioni emotive organiche di ALLMA.
"""

import sys
import os
import logging
from datetime import datetime
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Model.core.allma_core import ALLMACore

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_emotional_milestones():
    """Test completo del sistema Emotional Milestones"""
    
    print("=" * 70)
    print("🎭 TEST EMOTIONAL MILESTONES SYSTEM")
    print("=" * 70)
    
    # Inizializza ALLMA
    print("\n1️⃣  Inizializzazione ALLMA...")
    allma = ALLMACore(mobile_mode=True)
    allma.start_conversation("test_milestones")
    
    # Scenario 1: CONTRASTO EMOTIVO (tristezza → gioia)
    print("\n" + "="*70)
    print("📊 SCENARIO 1: Contrasto Emotivo (Tristezza → Gioia)")
    print("="*70)
    
    sad_messages = [
        "Sono molto triste oggi",
        "Mi sento solo e depresso",
        "Tutto va male, non ce la faccio più"
    ]
    
    print("\n🔴 Fase 1: Tristezza profonda...")
    for msg in sad_messages:
        print(f"\nUser: {msg}")
        response = allma.process_message("test_milestones", "conv1", msg)
        print(f"ALLMA: {response.content[:100]}...")
        time.sleep(0.3)
    
    # Ora cambio drastico
    print("\n\n🟢 Fase 2: Cambiamento drastico (gioia intensa)...")
    happy_msg = "Sono FELICISSIMO! È successa una cosa meravigliosa!"
    print(f"\nUser: {happy_msg}")
    response = allma.process_message("test_milestones", "conv1", happy_msg)
    
    if "---" in response.content:
        parts = response.content.split("---")
        print(f"\n🎭 RIFLESSIONE ATTIVATA!")
        print(f"\n{parts[0]}")
        print(f"\n{'='*70}")
        print(f"Risposta normale: {parts[1][:100]}...")
    else:
        print(f"ALLMA: {response.content}")
        print("⚠️  Nessuna riflessione (casualità non triggata, riprova)")
    
    # Scenario 2: EMOZIONE INTENSA
    print("\n\n" + "="*70)
    print("📊 SCENARIO 2: Emozione Molto Intensa")
    print("="*70)
    
    intense_msg = "Sono ARRABBIATISSIMO! Non ho mai provato una rabbia così!"
    print(f"\nUser: {intense_msg}")
    
    for _ in range(3):  # Riprova fino a quando triggera
        response = allma.process_message("test_milestones", "conv1", intense_msg)
        if "---" in response.content:
            parts = response.content.split("---")
            print(f"\n🎭 RIFLESSIONE SU INTENSITÀ ATTIVATA!")
            print(f"\n{parts[0]}")
            break
        else:
            print("⚠️  Tentativo fallito, riprovo...")
    
    # Scenario 3: MOMENTO DI CALMA
    print("\n\n" + "="*70)
    print("📊 SCENARIO 3: Momento di Calma Profonda")
    print("="*70)
    
    calm_messages = [
        "Mi sento sereno oggi",
        "C'è una pace dentro di me",
        "Tutto è tranquillo e va bene"
    ]
    
    for msg in calm_messages:
        print(f"\nUser: {msg}")
        response = allma.process_message("test_milestones", "conv1", msg)
        if "---" in response.content:
            parts = response.content.split("---")
            print(f"\n🎭 RIFLESSIONE SU CALMA ATTIVATA!")
            print(f"\n{parts[0]}")
            break
        else:
            print(f"ALLMA: {response.content[:80]}...")
    
    # Scenario 4: PATTERN RICORRENTE (simula giorni)
    print("\n\n" + "="*70)
    print("📊 SCENARIO 4: Pattern Ricorrente")
    print("="*70)
    print("(Simulato - richiede più interazioni nel tempo)")
    
    # Scenario 5: CASUALITÀ
    print("\n\n" + "="*70)
    print("📊 SCENARIO 5: Pensiero Spontaneo (Casualità)")
    print("="*70)
    print("Provo 20 messaggi neutri per triggerare pensiero casuale (2% chance)")
    
    triggered = False
    for i in range(20):
        response = allma.process_message("test_milestones", "conv1", f"Messaggio neutro {i}")
        if "---" in response.content:
            parts = response.content.split("---")
            print(f"\n🎭 PENSIERO SPONTANEO ATTIVATO (tentativo {i+1}/20)!")
            print(f"\n{parts[0]}")
            triggered = True
            break
    
    if not triggered:
        print("⚠️  Nessun pensiero spontaneo triggato (probabilità bassa, normale)")
    
    # Summary
    print("\n\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    
    milestones = allma.emotional_milestones
    history = milestones.emotional_history.get("test_milestones", [])
    
    print(f"Momenti emotivi registrati: {len(history)}")
    print(f"Riflessioni generate: {milestones.reflection_count.get('test_milestones', 0)}")
    
    if history:
        print("\nUltimi 5 momenti emotivi:")
        for moment in history[-5:]:
            print(f"  - {moment.emotion} ({moment.intensity:.2f}): {moment.message[:40]}...")
    
    print("\n" + "="*70)
    print("✅ TEST COMPLETATO")
    print("="*70)
    print("\n💡 Nota: Le riflessioni sono probabilistiche e organiche.")
    print("   Non tutte le condizioni triggerano sempre (è voluto!).")

if __name__ == "__main__":
    test_emotional_milestones()
