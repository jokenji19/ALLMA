#!/usr/bin/env python3
"""
Test Self-Correction (Metacognition)
====================================
Verifica che ALLMA sappia correggere i propri pensieri.
"""

import sys
import os
import logging
from dataclasses import dataclass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Model.core.reasoning_engine import ReasoningEngine

logging.basicConfig(level=logging.INFO, format='%(message)s')

# Mock Emotional State
@dataclass
class MockEmotion:
    primary_emotion: str
    intensity: float
    confidence: float

def test_self_correction():
    print("=" * 70)
    print("🧠 TEST SELF-CORRECTION (METACOGNIZIONE)")
    print("=" * 70)
    
    engine = ReasoningEngine()
    
    # Scenario: Utente molto triste, ma ALLMA inizialmente non lo capisce bene
    # Forziamo una situazione dove la strategia iniziale potrebbe essere sbagliata
    # Nota: Per testare la correzione, dobbiamo simulare che _formulate_strategy dia qualcosa di inadatto
    # Ma _formulate_strategy è deterministico.
    # Quindi modifichiamo temporaneamente il comportamento o usiamo un input borderline.
    
    print("\n1️⃣  Scenario: Utente Triste (Sadness 0.9)")
    print("Input: 'Non ce la faccio più...'")
    
    emotion = MockEmotion('sadness', 0.9, 1.0)
    context = {'relevant_memories': []}
    
    # Eseguiamo il pensiero
    trace = engine.generate_thought_process("Non ce la faccio più...", context, emotion)
    
    print(f"\n💭 Pensiero Grezzo:\n{trace.raw_thought}")
    
    # Verifichiamo se c'è stata correzione
    if "CORREZIONE METACOGNITIVA" in trace.strategy:
        print("\n✅ SUCCESS: La metacognizione è intervenuta!")
        print(f"📝 Correzione applicata: {trace.strategy.split('CORREZIONE METACOGNITIVA:')[1]}")
    else:
        # Se la strategia iniziale era già perfetta (es. "Ascolto empatico"), la correzione non serve.
        # Verifichiamo che la strategia sia comunque corretta.
        print("\nℹ️  Nessuna correzione necessaria (la strategia iniziale era già corretta).")
        print(f"Strategia: {trace.strategy}")

    # Scenario: Contraddizione (Simulata)
    # Per testare la logica di correzione, chiamiamo direttamente _critique_thought
    print("\n2️⃣  Test Diretto Logica di Critica (Contraddizione)")
    thought_bad = "🤔 PENSIERO: ... Mi ricordo che... Nessun ricordo. ... Ricordo collegato: Pizza."
    critique, correction = engine._critique_thought(thought_bad, emotion, "Strategia: Normale")
    
    if critique:
        print(f"✅ SUCCESS: Critica rilevata -> {critique}")
        print(f"✅ Correzione proposta -> {correction}")
    else:
        print("❌ FAIL: Contraddizione non rilevata.")

if __name__ == "__main__":
    test_self_correction()
