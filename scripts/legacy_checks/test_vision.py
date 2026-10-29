#!/usr/bin/env python3
"""
Test Vision System
==================
Verifica che ALLMA possa "vedere" e integrare il contesto visivo.
"""

import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Model.core.allma_core import ALLMACore

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_vision():
    print("=" * 70)
    print("👁️ TEST VISION SYSTEM (VISTA)")
    print("=" * 70)
    
    allma = ALLMACore(mobile_mode=True)
    
    # Scenario: Utente manda foto del frigo vuoto
    print("\n1️⃣  Scenario: Foto Frigo Vuoto")
    image_path = "/path/to/frigo_vuoto.jpg" # Il nome file attiva il mock
    user_msg = "Cosa dovrei cucinare?"
    
    print(f"📸 Immagine: {image_path}")
    print(f"💬 Messaggio: {user_msg}")
    
    # Processiamo
    # Nota: process_visual_input chiama process_message, che usa il ReasoningEngine
    # Vedremo nei log se il pensiero include l'analisi visiva
    
    response = allma.process_visual_input("test_user", image_path, user_msg)
    
    # Verifica output (simulato, dato che non abbiamo LLM attivo nel test rapido, ma vediamo i log)
    # Se il sistema funziona, il ReasoningEngine avrà ricevuto il contesto visivo.
    
    print("\n✅ Ciclo completato.")
    print("Controlla i log sopra per vedere se 'Analisi visiva' appare nel pensiero.")

if __name__ == "__main__":
    test_vision()
