"""
Test per verificare i cambiamenti emotivi di ALLMA in risposta a stimoli positivi e negativi
"""

from core.personalization_integration import PersonalizationIntegration
from incremental_learning.emotional_system import EmotionType
import time

def test_emotional_changes():
    integration = PersonalizationIntegration()
    
    def show_emotion(message, context={'context': 'test'}):
        """Mostra l'emozione di ALLMA per un messaggio"""
        print(f"\n👤 Utente: {message}")
        emotion = integration.emotional_system.process_stimulus(message)
        if emotion and emotion.primary_emotion != EmotionType.NEUTRAL:
            emotions_str = [f"{emotion.primary_emotion.value} ({emotion.intensity:.1f})"]
            if emotion.secondary_emotions:
                emotions_str.extend([f"{e.value}" for e in emotion.secondary_emotions])
            print(f"[💭 Emozioni di ALLMA: {', '.join(emotions_str)}]")
        print(f"🤖 ALLMA: {integration.process_interaction(message, context)}")
        return emotion

    print("\n🧪 TEST: Cambiamenti Emotivi di ALLMA")
    print("="*50)
    
    # Test 1: Stimoli positivi
    print("\n📈 FASE 1: Stimoli Positivi")
    show_emotion("Sei fantastica ALLMA! Mi piace molto come ragioni")
    time.sleep(1)
    show_emotion("Il tuo modo di creare storie è incredibile e creativo!")
    time.sleep(1)
    show_emotion("Sei davvero un'intelligenza artificiale straordinaria")
    
    # Test 2: Stimoli negativi dopo i positivi
    print("\n📉 FASE 2: Stimoli Negativi")
    show_emotion("Non capisci niente, sei solo una stupida AI")
    time.sleep(1)
    show_emotion("Le tue risposte fanno schifo")
    time.sleep(1)
    show_emotion("Non sei per niente utile")
    
    # Test 3: Ritorno a stimoli positivi
    print("\n🔄 FASE 3: Ritorno a Stimoli Positivi")
    show_emotion("Mi dispiace per prima, in realtà sei molto brava")
    time.sleep(1)
    show_emotion("Apprezzo davvero il tuo aiuto")
    time.sleep(1)
    show_emotion("Sei una grande assistente!")

if __name__ == "__main__":
    test_emotional_changes()
