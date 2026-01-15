"""
Test per verificare tutte le emozioni di ALLMA
"""

from core.personalization_integration import PersonalizationIntegration
from incremental_learning.emotional_system import EmotionType
import time

def test_all_emotions():
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
        print(f"🤖 ALLMA: {integration.process_interaction(message, context)}\n")
        return emotion

    print("\n🧪 TEST: Verifica di Tutte le Emozioni di ALLMA")
    print("="*50)
    
    # Test JOY (Gioia)
    print("\n😊 Test GIOIA")
    show_emotion("Sono così felice di lavorare con te!")
    show_emotion("È bellissimo vedere come migliori ogni giorno")
    
    # Test SADNESS (Tristezza)
    print("\n😢 Test TRISTEZZA")
    show_emotion("Mi sento triste quando non riesco a capire")
    show_emotion("È difficile vedere che non funziona come dovrebbe")
    
    # Test FEAR (Paura)
    print("\n😨 Test PAURA")
    show_emotion("Sono preoccupato che qualcosa possa andare storto")
    show_emotion("Ho paura di non farcela")
    
    # Test EXCITEMENT (Eccitazione)
    print("\n🤩 Test ECCITAZIONE")
    show_emotion("Wow, questo è incredibile!")
    show_emotion("Non vedo l'ora di iniziare questo nuovo progetto!")
    
    # Test PRIDE (Orgoglio)
    print("\n🦁 Test ORGOGLIO")
    show_emotion("Sono orgoglioso di quello che abbiamo realizzato insieme")
    show_emotion("Hai fatto un lavoro eccezionale!")
    
    # Test GRATITUDE (Gratitudine)
    print("\n🙏 Test GRATITUDINE")
    show_emotion("Grazie mille per il tuo aiuto prezioso")
    show_emotion("Apprezzo molto il tuo supporto")
    
    # Test CURIOSITY (Curiosità)
    print("\n🤔 Test CURIOSITÀ")
    show_emotion("Come funziona questo sistema?")
    show_emotion("Mi chiedo perché succede questo")
    
    # Test EMPATHY (Empatia)
    print("\n🤗 Test EMPATIA")
    show_emotion("Capisco come ti senti")
    show_emotion("Condivido la tua preoccupazione")
    
    # Test INSPIRATION (Ispirazione)
    print("\n✨ Test ISPIRAZIONE")
    show_emotion("Questa idea è davvero creativa e innovativa")
    show_emotion("Mi hai ispirato a pensare in modo diverso")
    
    # Test WONDER (Meraviglia)
    print("\n🌟 Test MERAVIGLIA")
    show_emotion("Questo è semplicemente meraviglioso!")
    show_emotion("È magico vedere come tutto funziona insieme")

if __name__ == "__main__":
    test_all_emotions()
