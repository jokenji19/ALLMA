"""
Demo interattiva del sistema ALLMA
"""

from curiosity_system import CuriosityDrive
from emotional_system import EmotionalSystem, EmotionType, Emotion
from subconscious_ethical_system import SubconsciousEthicalSystem, EthicalContext
from memory_system import MemorySystem
from datetime import datetime
import time

class ALLMADemo:
    def __init__(self):
        print("Inizializzazione dei sistemi ALLMA...")
        self.curiosity = CuriosityDrive()
        self.emotional = EmotionalSystem()
        self.ethical = SubconsciousEthicalSystem()
        self.memory = MemorySystem()
        print("Sistemi inizializzati con successo!\n")

    def process_input(self, user_input: str):
        """Processa l'input dell'utente attraverso tutti i sistemi"""
        print("\n=== Elaborazione dell'input ===")
        print(f"Input utente: '{user_input}'\n")

        # 1. Sistema Emotivo
        print("🫀 Analisi Emotiva:")
        emotion = self.emotional.process_emotion(
            name='anticipation',
            valence=0.6,
            context={"situation": "interaction"}
        )
        print(f"- Emozione rilevata: {emotion.primary_emotion.value}")
        print(f"- Intensità: {emotion.intensity:.2f}")
        print(f"- Valenza: {emotion.valence:.2f}\n")

        # 2. Sistema Etico
        print("🧠 Valutazione Etica:")
        ethical_context = EthicalContext(
            action_type="response",
            potential_impact=0.3,
            involved_entities=["user"],
            timestamp=datetime.now().timestamp(),
            context_data={"topic": "interaction"}
        )
        intuition = self.ethical.process_action(user_input, ethical_context)
        print(f"- Natura: {intuition.nature}")
        print(f"- Forza: {intuition.strength:.2f}")
        print(f"- Messaggio: {intuition.message}\n")

        # 3. Sistema di Curiosità
        print("🔍 Generazione Curiosità:")
        curiosity_response = self.curiosity.process_input(user_input)
        print("- Domande generate:")
        for question in curiosity_response['questions']:
            print(f"  • {question}")
        print()

        # 4. Sistema di Memoria
        print("💭 Memorizzazione Esperienza:")
        self.memory.process_experience(
            content=user_input,
            emotional_valence=emotion.valence,
            context={
                "emotion": emotion.primary_emotion.value,
                "ethical_nature": intuition.nature,
                "curiosity_questions": curiosity_response['questions']
            }
        )
        
        # Recupero memorie correlate
        memories = self.memory.recall_memory(user_input)
        if memories:
            print("- Memorie correlate trovate:")
            for mem in memories[:3]:  # Mostra solo le prime 3 memorie
                print(f"  • {mem.content[:100]}...")
        else:
            print("- Nessuna memoria correlata trovata")
        print()

        # Generazione risposta finale
        print("=== Risposta Finale ===")
        response = self._generate_response(
            user_input, emotion, intuition, 
            curiosity_response, memories
        )
        print(response)
        print("\n" + "="*50 + "\n")

    def _generate_response(self, user_input, emotion, intuition, 
                         curiosity_response, memories):
        """Genera una risposta basata su tutti gli input dei sistemi"""
        response_parts = []

        # Parte emotiva
        if emotion.valence > 0:
            response_parts.append(
                "Mi fa piacere parlare di questo argomento con te."
            )
        
        # Parte etica
        if intuition.nature == "supportive":
            response_parts.append(
                "Apprezzo il tuo approccio costruttivo a questo tema."
            )
        elif intuition.nature == "cautionary":
            response_parts.append(
                "Vorrei esplorare questo argomento con la giusta attenzione."
            )

        # Parte curiosità
        if curiosity_response['questions']:
            response_parts.append(
                f"Mi chiedo: {curiosity_response['questions'][0]}"
            )

        # Parte memoria
        if memories:
            response_parts.append(
                "Questo mi ricorda alcune esperienze precedenti che "
                "potrebbero essere rilevanti."
            )

        return " ".join(response_parts)

def main():
    demo = ALLMADemo()
    print("\nBenvenuto alla demo di ALLMA!")
    print("Scrivi 'exit' per uscire\n")

    while True:
        user_input = input("Tu: ")
        if user_input.lower() == 'exit':
            print("\nGrazie per aver testato ALLMA!")
            break
        
        demo.process_input(user_input)

if __name__ == "__main__":
    main()
