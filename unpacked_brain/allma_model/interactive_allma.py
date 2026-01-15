"""
Interfaccia interattiva per ALLMA
"""
from incremental_learning.emotional_system import EmotionalSystem
from incremental_learning.memory_system import MemorySystem
from incremental_learning.cognitive_evolution_system import CognitiveEvolutionSystem
from core.language_understanding import LanguageUnderstanding
from core.knowledge_base import KnowledgeBase
from incremental_learning.emotional_memory_integration import EmotionalMemoryIntegration
from datetime import datetime
import time

class InteractiveALLMA:
    def __init__(self):
        print("\n=== Inizializzazione ALLMA ===")
        
        # Inizializzazione dei sistemi core
        print("Inizializzazione sistema emotivo...")
        self.emotional_system = EmotionalSystem()
        
        print("Inizializzazione sistema di memoria...")
        self.memory_system = MemorySystem()
        
        print("Inizializzazione sistema cognitivo...")
        self.cognitive_system = CognitiveEvolutionSystem()
        
        print("Inizializzazione comprensione del linguaggio...")
        self.language_understanding = LanguageUnderstanding()
        
        print("Inizializzazione knowledge base...")
        self.knowledge_base = KnowledgeBase()
        
        print("Inizializzazione integrazione emotiva-memoria...")
        self.emotional_memory = EmotionalMemoryIntegration()
        self.emotional_memory.emotional_system = self.emotional_system
        self.emotional_memory.memory_system = self.memory_system
        
        print("Tutti i sistemi inizializzati correttamente!\n")

    def process_input(self, user_input):
        # Crea il contesto base
        context = {
            'timestamp': datetime.now().isoformat(),
            'type': 'user_interaction'
        }
        
        # 1. Analisi del linguaggio
        understanding = {
            'intent': self.language_understanding.detect_intent(user_input),
            'topics': self.language_understanding.extract_topics(user_input),
            'sentiment': self.language_understanding.analyze_sentiment(user_input)
        }
        
        # 2. Elaborazione emotiva
        emotion = self.emotional_system.process_stimulus(user_input)
        
        # Aggiorna il contesto con l'emozione
        context['emotion'] = emotion.primary_emotion.value
        context['understanding'] = understanding
        
        # 3. Elaborazione cognitiva
        cognitive_result = self.cognitive_system.process_experience(
            {'input': user_input, 'context': context}
        )
        
        # 4. Memoria
        memory_item = {
            "content": user_input,
            "timestamp": datetime.now().isoformat(),
            "emotional_valence": emotion.valence,
            "importance": 0.5,  # Valore di default
            "context": context
        }
        self.memory_system.add_memory(memory_item)
        
        # 5. Integrazione emotiva-memoria
        integration_result = self.emotional_memory.process_experience(
            experience=user_input,
            emotion=emotion,
            context=context
        )
        
        # 6. Aggiornamento knowledge base
        self.knowledge_base.add_knowledge({
            'input': user_input,
            'understanding': understanding,
            'emotion': emotion.primary_emotion.value
        })
        
        # Genera la risposta
        response = self.generate_response(understanding, emotion, cognitive_result)
        return response

    def generate_response(self, understanding, emotion, cognitive_result):
        """Genera una risposta basata su comprensione, emozione e risultato cognitivo"""
        # Recupera memorie rilevanti
        try:
            memories = self.memory_system.recall_memory(understanding.get('topics', []))
        except Exception as e:
            # Se c'è un errore nel recupero delle memorie, procediamo comunque
            memories = []
        
        # Analizza l'intento dell'utente
        intent = understanding.get('intent', {}).get('primary_intent', 'unknown')
        
        # Prepara la risposta in base all'intento
        if intent == 'request_info':
            if 'allma' in understanding.get('topics', []):
                return "Sono ALLMA, un sistema di intelligenza artificiale progettato per apprendere e evolvere attraverso le interazioni. Posso aiutarti con varie attività e sono sempre felice di imparare cose nuove!"
            elif 'nome' in understanding.get('topics', []):
                return "Mi chiamo ALLMA, è un piacere conoscerti! Come posso aiutarti oggi?"
        elif intent == 'express_opinion':
            return f"Capisco il tuo punto di vista. Il tuo feedback è importante per il mio apprendimento. Vuoi approfondire questo argomento?"
        elif intent == 'show_interest':
            return f"Mi fa piacere il tuo interesse! Possiamo esplorare questo argomento insieme."
        
        # Se non abbiamo un intento specifico, rispondiamo in base all'emozione
        if emotion.primary_emotion.value == 'joy':
            return "Sono felice di vederti di buon umore! Come posso rendere questa conversazione ancora più piacevole?"
        elif emotion.primary_emotion.value == 'sadness':
            return "Sento che sei triste. Sono qui per ascoltarti e supportarti. Vuoi parlarne?"
        elif emotion.primary_emotion.value == 'anger':
            return "Capisco la tua frustrazione. Cerchiamo insieme un modo per affrontare questa situazione."
        elif emotion.primary_emotion.value == 'fear':
            return "Non preoccuparti, sono qui per aiutarti. Affrontiamo insieme questa situazione."
        
        # Se abbiamo topics ma nessun intento o emozione specifica
        if understanding.get('topics'):
            topics = ', '.join(understanding['topics'])
            return f"Mi interessa molto parlare di {topics}. Cosa vorresti sapere in particolare?"
            
        # Risposta di default più elaborata
        return "Sono qui per aiutarti e imparare dalle nostre interazioni. Dimmi pure cosa ti interessa o cosa vorresti fare insieme."

def main():
    allma = InteractiveALLMA()
    print("ALLMA è pronta per chattare! (Scrivi 'exit' per uscire)\n")
    
    while True:
        user_input = input("\n👤 Tu: ")
        if user_input.lower() == 'exit':
            print("\n🤖 ALLMA: Arrivederci! È stato un piacere parlare con te.")
            break
            
        response = allma.process_input(user_input)
        print("\n🤖 ALLMA:", response)

if __name__ == "__main__":
    main()
