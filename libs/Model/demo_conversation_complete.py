"""
Demo del sistema conversazionale completo
"""
import sys
from typing import Dict, Any, List

from Model.incremental_learning.pattern_recognition_system import PatternRecognitionSystem
from Model.incremental_learning.intent_recognition_system import IntentRecognitionSystem
from Model.incremental_learning.response_generation_system import ResponseGenerator
from Model.incremental_learning.emotional_system import EmotionalSystem
from Model.incremental_learning.dynamic_response_system import DynamicResponseSystem
from Model.incremental_learning.user_profile import UserProfile

class IntegratedDemo:
    """Demo del sistema integrato che combina tutti i componenti"""
    
    def __init__(self):
        """Inizializza il sistema demo integrato"""
        self.emotional_system = EmotionalSystem()
        self.response_generator = ResponseGenerator()
        self.pattern_recognizer = PatternRecognitionSystem()
        self.intent_recognizer = IntentRecognitionSystem()
        self.dynamic_response = DynamicResponseSystem(
            templates_file="Model/incremental_learning/response_templates.json"
        )
        self.user_profile = UserProfile("demo_user")
        self.conversation_history = []
        self.debug = '--debug' in sys.argv
        
    def process_user_input(self, text: str) -> str:
        """Processa l'input dell'utente e genera una risposta appropriata"""
        try:
            # Riconosci l'intento
            intent_category, confidence, subject = self.intent_recognizer.recognize_intent(text)
            
            # Analizza l'emozione
            emotion = self.emotional_system.analyze_emotion(text)
            
            # Riconosci pattern e topic
            pattern = self.pattern_recognizer.learn_pattern(text)
            
            # Prepara il contesto
            context = {
                "emotion": emotion.name.lower(),
                "technical_level": self.user_profile.get_technical_level(),
                "topics": pattern.topic if pattern else None,
                "is_error": False
            }
            
            # Ottieni una risposta appropriata
            response_text, is_learned = self.dynamic_response.get_response(
                intent_category, context
            )
            
            # Aggiorna il profilo utente
            self.user_profile.update_from_interaction(text, emotion, pattern)
            
            # Debug info
            if self.debug:
                print(f"Intent: {intent_category} ({confidence:.2f})")
                if subject:
                    print(f"Subject: {subject}")
                print(f"Emotional State: {emotion}")
                if pattern and pattern.topic:
                    print(f"Detected Topics: {pattern.topic}")
                print(f"Pattern: {pattern}")
                print(f"Learned Response: {'Yes' if is_learned else 'No'}")
                print("-" * 50)
            
            return response_text
            
        except Exception as e:
            print(f"Mi dispiace, ho avuto un problema nel processare la tua richiesta: {str(e)}")
            return "Proviamo di nuovo!"

def run_demo():
    """Esegue il demo del sistema integrato"""
    print("=== Demo Sistema Integrato ALLMA ===\n")
    demo = IntegratedDemo()
    
    print("Benvenuto! Puoi parlarmi di qualsiasi cosa. Scrivi 'exit' per terminare.\n")
    
    while True:
        try:
            # Ottieni input dall'utente
            user_input = input("Tu: ").strip()
            
            # Controlla se l'utente vuole uscire
            if user_input.lower() == 'exit':
                print("\nGrazie per aver conversato con me! A presto!")
                break
                
            # Processa l'input e mostra la risposta
            result = demo.process_user_input(user_input)
            
            # Mostra la risposta
            print(f"ALLMA: {result}")
            
        except KeyboardInterrupt:
            print("\nConversazione interrotta. Arrivederci!")
            break
            
if __name__ == "__main__":
    run_demo()
