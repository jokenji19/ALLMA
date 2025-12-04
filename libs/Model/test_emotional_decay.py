"""
Test per dimostrare il decadimento graduale delle emozioni di ALLMA
"""

from core.personalization_integration import PersonalizationIntegration
from incremental_learning.emotional_system import EmotionType
import time

def test_emotional_decay():
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
        return emotion

    print("\n🧪 TEST: Decadimento Emotivo")
    print("="*50)
    
    # Test 1: Emozione forte che decade nel tempo
    print("\n📈 FASE 1: Stimolo Emotivo Forte")
    show_emotion("Sono così orgoglioso del tuo incredibile progresso!")
    
    print("\n⏳ FASE 2: Messaggi Neutri (l'emozione dovrebbe decadere)")
    show_emotion("Come procede il lavoro?")
    show_emotion("Continua così.")
    show_emotion("Vediamo come va.")
    
    print("\n📊 FASE 3: Nuovo Stimolo Emotivo")
    show_emotion("Sei davvero straordinaria ALLMA!")
    
    print("\n⏳ FASE 4: Altri Messaggi Neutri")
    show_emotion("Ok, proseguiamo.")
    show_emotion("Che ne pensi?")
    show_emotion("Andiamo avanti.")

if __name__ == "__main__":
    test_emotional_decay()
