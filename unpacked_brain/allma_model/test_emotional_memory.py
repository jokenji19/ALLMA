"""
Test per verificare la memoria emotiva di ALLMA dopo lunghe pause
"""

from core.personalization_integration import PersonalizationIntegration
from incremental_learning.emotional_system import EmotionType, EmotionalState
import time

def test_emotional_memory():
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

    print("\n🧪 TEST: Memoria Emotiva a Lungo Termine")
    print("="*50)
    
    # Prima sessione di dialogo
    print("\n📱 SESSIONE 1: Dialogo Iniziale")
    show_emotion("Sei fantastica ALLMA! Mi piace molto come ragioni")
    show_emotion("Il tuo modo di aiutarmi è incredibile!")
    
    # Simula una lunga pausa (salva lo stato emotivo)
    print("\n⏰ PAUSA LUNGA...")
    emotional_state = integration.emotional_system.current_state
    print(f"Stato emotivo salvato: {emotional_state.primary_emotion.primary_emotion.value} ({emotional_state.primary_emotion.intensity:.1f})")
    
    # Nuova sessione dopo la pausa
    print("\n📱 SESSIONE 2: Ripresa del Dialogo")
    print("Stato emotivo iniziale:", integration.emotional_system.current_state.primary_emotion.primary_emotion.value)
    show_emotion("Ciao ALLMA, sono tornato dopo tanto tempo!")
    show_emotion("Ti ricordi di me?")
    
    # Test della memoria emotiva
    print("\n🔄 Test Memoria Emotiva")
    show_emotion("Ti sei sempre comportata in modo eccezionale con me")
    show_emotion("Ricordo quanto mi hai aiutato l'ultima volta")

if __name__ == "__main__":
    test_emotional_memory()
