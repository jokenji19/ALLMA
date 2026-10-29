import sys
import os
import logging

# Configura logging
logging.basicConfig(level=logging.INFO)

# Aggiungi la directory corrente al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Model.core.allma_core import ALLMACore

def test_symbiosis():
    print("=== TEST SIMBIOSI ALLMA + GEMMA ===")
    
    # 1. Inizializzazione
    print("\n1. Inizializzazione Core (Mobile Mode)...")
    try:
        allma = ALLMACore(mobile_mode=True)
        print("✅ Core inizializzato.")
    except Exception as e:
        print(f"❌ Errore inizializzazione: {e}")
        return

    # 2. Verifica Caricamento Modello
    print("\n2. Verifica Modello LLM...")
    # Forziamo un caricamento se non è avvenuto (avviene al primo messaggio solitamente, ma controlliamo l'attributo)
    # Simulo un messaggio per innescare il caricamento
    
    user_input = "Ciao, come ti senti oggi?"
    print(f"Input Utente: '{user_input}'")
    
    try:
        # Start conversation
        allma.start_conversation("test_user")
        
        # Process message
        response = allma.process_message(
            user_id="test_user",
            conversation_id="test_chat",
            message=user_input
        )
        
        print("\n3. Risposta Generata:")
        print(f"🤖 ALLMA: {response.content}")
        
        print("\n4. Analisi Simbiosi:")
        print(f"Emozione Rilevata: {response.emotion}")
        print(f"Confidence: {response.confidence}")
        
        # Verifica se è stato usato il fallback o il modello
        if hasattr(allma, '_llm') and allma._llm is not None:
            print("✅ Modello Gemma usato correttamente (LLM caricato).")
        else:
            print("⚠️ ATTENZIONE: Modello Gemma NON usato (Fallback attivo).")
            print("Possibili cause: llama-cpp-python non installato o modello non trovato.")

    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_symbiosis()
