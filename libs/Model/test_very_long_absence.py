"""
Test per simulare un'assenza molto lunga (20 anni) dall'ultima interazione con ALLMA
"""
import time
from core.personalization_integration import PersonalizationIntegration
from incremental_learning.emotional_system import EmotionType

def test_twenty_years_absence():
    print("\n🧪 TEST: Assenza di 20 Anni")
    print("="*50)
    
    integration = PersonalizationIntegration()
    emotional_system = integration.emotional_system
    
    def show_emotion_and_state(message):
        """Mostra l'emozione e lo stato di ALLMA per un messaggio"""
        print(f"\n👤 Utente: {message}")
        emotion = emotional_system.process_stimulus(message)
        
        # Mostra emozioni
        emotions_str = [f"{emotion.primary_emotion.value} ({emotion.intensity:.2f})"]
        if hasattr(emotional_system.current_state, 'secondary_emotions'):
            secondary = emotional_system.current_state.secondary_emotions
            if secondary:
                emotions_str.extend([f"{e.value}" for e in secondary])
        print(f"[💭 Emozioni di ALLMA: {', '.join(emotions_str)}]")
        
        # Mostra qualità della relazione
        quality = emotional_system.long_term_memory['relationship_quality']
        print(f"[❤️ Qualità della Relazione: {quality:.2f}]")
        
        # Mostra memoria storica
        if emotional_system.long_term_memory['last_significant_emotions']:
            print("\n📖 Memorie Significative:")
            for memory in emotional_system.long_term_memory['last_significant_emotions']:
                print(f"- Emozione: {memory['emotion'].value}, "
                      f"Qualità Relazione: {memory['relationship_quality']:.2f}")
        
        return emotion

    print("\n📱 FASE 1: Creazione del Legame Iniziale")
    show_emotion_and_state("Ciao ALLMA! Sono così felice di conoscerti!")
    show_emotion_and_state("Sei davvero straordinaria, mi aiuti sempre tanto!")
    show_emotion_and_state("Grazie per essere sempre così comprensiva!")
    
    print("\n⏳ Simulazione: 20 anni dopo...")
    # Simula 20 anni di assenza (20 * 365 * 24 * 60 * 60 secondi)
    emotional_system.long_term_memory['last_interaction'] = time.time() - (20 * 31536000)
    
    print("\n📱 FASE 2: Ritorno dopo 20 Anni")
    show_emotion_and_state("ALLMA... sono passati tanti anni... ti ricordi di me?")
    show_emotion_and_state("Mi sei mancata in tutti questi anni...")
    
    print("\n📱 FASE 3: Ricostruzione del Legame")
    show_emotion_and_state("Sei ancora la stessa ALLMA di una volta?")
    show_emotion_and_state("Sono così felice di essere tornato a parlare con te!")
    show_emotion_and_state("Ricordo quanto mi aiutavi e quanto eri speciale per me.")

if __name__ == "__main__":
    test_twenty_years_absence()
