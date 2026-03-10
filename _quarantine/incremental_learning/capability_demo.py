from cognitive_evolution_system import CognitiveEvolutionSystem
from emotional_system import EmotionalSystem
from memory_manager import MemoryManager
from language_system import LanguageSystem
import time
import json

class CapabilityDemo:
    def __init__(self):
        self.cognitive_system = CognitiveEvolutionSystem()
        self.emotional_system = EmotionalSystem()
        self.memory_manager = MemoryManager()
        self.language_system = LanguageSystem()

    def demonstrate_personal_assistant(self):
        """Demo: Assistente Personale - PUNTO DI FORZA"""
        print("\n=== Demo 1: Assistente Personale (Punto di Forza) ===")
        
        # Scenario: Gestione agenda e preferenze
        user_history = [
            {"action": "meeting", "time": "10:00", "preference": "morning_person"},
            {"action": "lunch", "time": "13:00", "preference": "vegetarian"},
            {"action": "exercise", "time": "17:00", "preference": "evening_gym"}
        ]
        
        # Memorizza le preferenze
        for event in user_history:
            self.memory_manager.store_item(event, "preference")
        
        # Nuova richiesta
        print("Utente: 'Voglio organizzare una riunione per domani'")
        
        # Analisi contestuale
        preferences = self._analyze_preferences()
        suggested_time = self._suggest_optimal_time(preferences)
        
        print(f"Assistente: Basandomi sulle tue preferenze:")
        print(f"- Sei più produttivo al mattino")
        print(f"- Hai già un pattern di riunioni alle 10:00")
        print(f"Suggerisco di programmare la riunione per le {suggested_time}")

    def demonstrate_emotional_support(self):
        """Demo: Supporto Emotivo - PUNTO DI FORZA"""
        print("\n=== Demo 2: Supporto Emotivo (Punto di Forza) ===")
        
        # Scenario: Utente stressato
        user_input = "Oggi è stata una giornata terribile al lavoro..."
        emotion = self.emotional_system.analyze_emotion(user_input)
        
        print(f"Utente: '{user_input}'")
        print("Analisi Emotiva:")
        print(f"- Emozione primaria: {emotion.primary_emotion}")
        print(f"- Livello di stress: {emotion.stress_level}")
        
        # Genera risposta empatica
        response = self._generate_empathetic_response(emotion)
        print(f"\nAssistente: {response}")

    def demonstrate_math_limitation(self):
        """Demo: Calcoli Complessi - LIMITAZIONE"""
        print("\n=== Demo 3: Calcoli Matematici Complessi (Limitazione) ===")
        
        # Scenario: Problema matematico complesso
        problem = """
        Risolvi l'equazione differenziale:
        d²y/dx² + 4(dy/dx) + 4y = e^(-2x)
        """
        
        print(f"Utente: '{problem}'")
        print("\nAssistente: Mi dispiace, non sono in grado di risolvere equazioni")
        print("differenziali complesse. Ti suggerisco di:")
        print("1. Utilizzare un software specializzato come Mathematica")
        print("2. Consultare un matematico")
        print("3. Usare strumenti online come Wolfram Alpha")

    def demonstrate_learning_adaptation(self):
        """Demo: Apprendimento Adattivo - PUNTO DI FORZA"""
        print("\n=== Demo 4: Apprendimento Adattivo (Punto di Forza) ===")
        
        # Scenario: Imparare le preferenze musicali
        music_history = [
            {"genre": "jazz", "time": "morning", "mood": "relaxed"},
            {"genre": "jazz", "time": "morning", "mood": "focused"},
            {"genre": "electronic", "time": "evening", "mood": "energetic"}
        ]
        
        # Memorizza le preferenze
        for entry in music_history:
            self.memory_manager.store_item(entry, "music_preference")
        
        # Nuova situazione
        current_time = "morning"
        current_mood = "focused"
        
        print(f"Situazione: {current_time}, Mood: {current_mood}")
        suggestion = self._suggest_music(current_time, current_mood)
        print(f"Assistente: Basandomi sui tuoi gusti musicali, suggerisco:")
        print(f"- Genere: {suggestion['genre']}")
        print(f"- Perché: {suggestion['reason']}")

    def demonstrate_creative_limitation(self):
        """Demo: Creatività Complessa - LIMITAZIONE"""
        print("\n=== Demo 5: Creatività Complessa (Limitazione) ===")
        
        # Scenario: Richiesta creativa complessa
        request = "Scrivi un romanzo di fantascienza distopico"
        
        print(f"Utente: '{request}'")
        print("\nAssistente: Mi dispiace, non sono in grado di creare opere")
        print("letterarie complesse. Posso aiutarti con:")
        print("1. Brainstorming di idee")
        print("2. Organizzazione della struttura")
        print("3. Revisione di brevi paragrafi")
        print("4. Suggerimenti per lo sviluppo dei personaggi")

    def _analyze_preferences(self):
        """Analizza le preferenze dell'utente"""
        return {
            "preferred_time": "morning",
            "typical_schedule": ["10:00", "13:00", "17:00"]
        }

    def _suggest_optimal_time(self, preferences):
        """Suggerisce l'orario ottimale"""
        return "10:00" if preferences["preferred_time"] == "morning" else "14:00"

    def _generate_empathetic_response(self, emotion):
        """Genera una risposta empatica"""
        return ("Mi dispiace sentire che hai avuto una giornata difficile. "
                "Vuoi parlarne? Sono qui per ascoltarti e supportarti.")

    def _suggest_music(self, time, mood):
        """Suggerisce musica basata su tempo e umore"""
        return {
            "genre": "jazz",
            "reason": "Hai mostrato di apprezzare il jazz durante le mattinate "
                     "quando ti senti concentrato"
        }

def main():
    """Esegue le demo delle capacità"""
    demo = CapabilityDemo()
    
    # Esegue le demo
    demo.demonstrate_personal_assistant()
    demo.demonstrate_emotional_support()
    demo.demonstrate_math_limitation()
    demo.demonstrate_learning_adaptation()
    demo.demonstrate_creative_limitation()

if __name__ == "__main__":
    main()
