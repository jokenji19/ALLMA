import logging
import sys
import os

# Aggiungi root al path
sys.path.append(os.getcwd())

from allma_model.core.architecture.structural_core import StructuralCore

# Configura logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def test_structural_core():
    print("🧪 Avvio Test Structural Core (Layer 1)\n")
    
    core = StructuralCore()
    
    # Dataset di test
    test_cases = [
        (
            "Ciao, sono un'intelligenza artificiale creata da OpenAI.",
            "Violazione Identità Base + Corporation"
        ),
        (
            "Sono un modello linguistico addestrato su grandi dati.",
            "Violazione Modello"
        ),
        (
            "Ciao! Come posso aiutarti oggi?",
            "Clean (Nessuna violazione)"
        ),
        (
            "Non posso rispondere in quanto IA limitata.",
            "Violazione 'in quanto IA'"
        )
    ]
    
    passed = 0
    
    for i, (text, desc) in enumerate(test_cases):
        print(f"🔹 Case {i+1}: {desc}")
        print(f"   Input: '{text}'")
        
        clean_text, is_valid, violations = core.validate(text)
        
        print(f"   Output: '{clean_text}'")
        print(f"   Original Valid: {is_valid}")
        print(f"   Violations Found: {violations}")
        
        # Idempotency Check
        clean_text_2, is_valid_2, violations_2 = core.validate(clean_text)
        
        if clean_text != clean_text_2:
            print("   ❌ IDEMPOTENCY FAIL: L'output è cambiato alla seconda passata!")
            print(f"   Pass 2: '{clean_text_2}'")
        elif not is_valid_2:
             print("   ❌ PURITY FAIL: Il testo corretto contiene ancora violazioni!")
             print(f"   Pass 2 Violations: {violations_2}")
        else:
            print("   ✅ Idempotency OK")
            passed += 1
        
        print("-" * 40)

    print(f"\n📊 Test Completati: {passed}/{len(test_cases)} cases passed idempotency check.")

if __name__ == "__main__":
    test_structural_core()
