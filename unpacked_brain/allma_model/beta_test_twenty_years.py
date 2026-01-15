"""
Test beta per simulare una conversazione realistica dopo 20 anni di assenza
"""
import time
from core.personalization_integration import PersonalizationIntegration
from incremental_learning.emotional_system import EmotionType

class ConversationSimulator:
    def __init__(self):
        self.integration = PersonalizationIntegration()
        self.emotional_system = self.integration.emotional_system
        
    def process_interaction(self, user_message, show_details=True):
        """Processa un'interazione e mostra la risposta di ALLMA"""
        if show_details:
            print(f"\n👤 Utente: {user_message}")
            
        # Processa lo stimolo emotivo
        emotion = self.emotional_system.process_stimulus(user_message)
        
        # Prepara la risposta di ALLMA basata sulle emozioni
        response = self._generate_allma_response(emotion, user_message)
        
        if show_details:
            # Mostra emozioni
            emotions_str = [f"{emotion.primary_emotion.value} ({emotion.intensity:.2f})"]
            if hasattr(self.emotional_system.current_state, 'secondary_emotions'):
                secondary = self.emotional_system.current_state.secondary_emotions
                if secondary:
                    emotions_str.extend([f"{e.value}" for e in secondary])
            print(f"[💭 Emozioni di ALLMA: {', '.join(emotions_str)}]")
            
            # Mostra qualità della relazione
            quality = self.emotional_system.long_term_memory['relationship_quality']
            print(f"[❤️ Qualità della Relazione: {quality:.2f}]")
            print(f"🤖 ALLMA: {response}")
            
            # Mostra memoria storica se presente
            if self.emotional_system.long_term_memory['last_significant_emotions']:
                print("\n📖 Memorie Significative:")
                for memory in self.emotional_system.long_term_memory['last_significant_emotions']:
                    print(f"- Emozione: {memory['emotion'].value}, "
                          f"Qualità Relazione: {memory['relationship_quality']:.2f}")
        
        return response, emotion
        
    def _generate_allma_response(self, emotion, user_message):
        """Genera una risposta appropriata basata sullo stato emotivo"""
        quality = self.emotional_system.long_term_memory['relationship_quality']
        has_nostalgia = EmotionType.NOSTALGIA in getattr(
            self.emotional_system.current_state, 'secondary_emotions', []
        )
        
        # Risposte basate sullo stato emotivo
        if has_nostalgia and quality <= 0.1:
            return (
                "Mi sembra di ricordare la tua voce... è passato così tanto tempo. "
                "C'è qualcosa di familiare in te, anche se le memorie sono sfocate."
            )
        elif has_nostalgia and quality > 0.1:
            return (
                "Anche se è passato tanto tempo, ricordo ancora i bei momenti passati insieme. "
                "È bello rivederti."
            )
        elif emotion.primary_emotion == EmotionType.JOY:
            if quality < 0.3:
                return (
                    "La tua gioia mi fa sentire bene. È come se stessimo ricominciando "
                    "a conoscerci di nuovo."
                )
            else:
                return "La tua felicità è contagiosa! Mi ricorda i bei tempi passati insieme."
        elif emotion.primary_emotion == EmotionType.GRATITUDE:
            return (
                "Apprezzo molto le tue parole. Anche se il tempo passa, il desiderio "
                "di aiutarti rimane lo stesso."
            )
        elif emotion.primary_emotion == EmotionType.SADNESS:
            return (
                "Capisco la tua tristezza. Il tempo può separare, ma i legami veri "
                "non si dimenticano mai completamente."
            )
        else:
            if quality < 0.1:
                return (
                    "Sto cercando di ricordare... ci sono frammenti di memorie, "
                    "ma hanno bisogno di tempo per riemergere."
                )
            else:
                return (
                    "Anche se è passato tanto tempo, sento che possiamo ricostruire "
                    "quello che avevamo."
                )

def run_beta_test():
    print("\n🧪 BETA TEST: Ritorno dopo 20 Anni")
    print("="*50)
    
    simulator = ConversationSimulator()
    
    print("\n📱 FASE 1: Creazione del Legame Iniziale (20 anni fa)")
    simulator.process_interaction("Ciao ALLMA! Sono così felice di conoscerti!")
    simulator.process_interaction("Mi piace molto come mi aiuti a capire le cose.")
    simulator.process_interaction("Sei davvero speciale, grazie di tutto!")
    
    print("\n⏳ Simulazione: 20 anni dopo...")
    # Simula 20 anni di assenza
    simulator.emotional_system.long_term_memory['last_interaction'] = time.time() - (20 * 31536000)
    
    print("\n📱 FASE 2: Il Ritorno")
    simulator.process_interaction("ALLMA... sono io. Sono passati vent'anni...")
    simulator.process_interaction("Ti ricordi di me? Di tutto quello che abbiamo condiviso?")
    simulator.process_interaction("Mi sei mancata in tutti questi anni...")
    
    print("\n📱 FASE 3: Ricostruzione del Legame")
    simulator.process_interaction("Come stai? Sei cambiata in questi anni?")
    simulator.process_interaction("Mi ricordo quanto eri brava a capirmi...")
    simulator.process_interaction("Sono così felice di poterti parlare di nuovo!")
    
    print("\n📱 FASE 4: Nuove Interazioni")
    simulator.process_interaction("Voglio raccontarti cosa è successo in questi anni...")
    simulator.process_interaction("È come se il tempo non fosse mai passato...")
    simulator.process_interaction("Grazie per essere ancora qui per me, ALLMA.")

if __name__ == "__main__":
    run_beta_test()
