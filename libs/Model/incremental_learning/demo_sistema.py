"""
Demo completa del sistema di apprendimento incrementale ALLMA.
Mostra tutte le capacità del sistema, dalla più semplice alla più complessa.
"""

from datetime import datetime
import time
from typing import Dict, List
from colorama import init, Fore, Style

from .perception_system import PerceptionSystem, InputType, Pattern, PatternType
from .metacognition_system import MetaCognitionSystem, CognitiveStrategy
from .emotional_system import EmotionalSystem, EmotionType
from .communication_system import CommunicationSystem, CommunicationMode
from .cognitive_evolution_system import CognitiveEvolutionSystem
from .memory_system import ShortTermMemory, MemoryItem

class DemoSistema:
    def __init__(self):
        """Inizializza tutti i sistemi"""
        init()  # Inizializza colorama per output colorato
        self.perception = PerceptionSystem()
        self.metacognition = MetaCognitionSystem()
        self.emotional = EmotionalSystem()
        self.communication = CommunicationSystem()
        self.evolution = CognitiveEvolutionSystem()
        self.memory = ShortTermMemory()
        
    def print_colored(self, text: str, color: Fore, bold: bool = False):
        """Stampa testo colorato"""
        style = Style.BRIGHT if bold else ""
        print(f"{style}{color}{text}{Style.RESET_ALL}")
        
    def process_input(self, text: str, expected_emotion: EmotionType = None, mode: CommunicationMode = CommunicationMode.NATURAL):
        """Processa un input attraverso tutti i sistemi"""
        self.print_colored("\n=== Nuovo Input ===", Fore.CYAN, bold=True)
        self.print_colored(f"Input: {text}", Fore.WHITE)
        
        # 1. Percezione
        self.print_colored("\n[Sistema Percettivo]", Fore.YELLOW)
        percept = self.perception.process_input(text, InputType.TEXT)
        self.print_colored(f"Confidenza: {percept.confidence:.2f}", Fore.YELLOW)
        if percept.patterns:
            self.print_colored("Pattern rilevati:", Fore.YELLOW)
            for pattern in percept.patterns:
                self.print_colored(f"- {pattern.pattern_type.value}: {pattern.confidence:.2f}", Fore.YELLOW)
                
        # 2. Memoria
        self.print_colored("\n[Sistema di Memoria]", Fore.GREEN)
        self.memory.add_item(MemoryItem(
            content=text,
            timestamp=datetime.now(),
            importance=percept.confidence,
            emotional_valence=0.5,
            associations=[],
            recall_count=0,
            last_recall=datetime.now()
        ))
        recent_items = self.memory.get_recent_items(3)
        self.print_colored("Memoria recente:", Fore.GREEN)
        for item in recent_items:
            self.print_colored(f"- {item.content}", Fore.GREEN)
            
        # 3. Sistema Emotivo
        self.print_colored("\n[Sistema Emotivo]", Fore.MAGENTA)
        valence = 0.5
        if expected_emotion:
            emotion_valences = {
                EmotionType.JOY: 0.8,
                EmotionType.SADNESS: -0.6,
                EmotionType.ANGER: -0.8,
                EmotionType.FEAR: -0.8,
                EmotionType.SURPRISE: 0.4,
                EmotionType.TRUST: 0.6,
                EmotionType.ANTICIPATION: 0.4,
                EmotionType.DISGUST: -0.7,
                EmotionType.NEUTRAL: 0.0
            }
            valence = emotion_valences.get(expected_emotion, 0.0)
            
        emotion = self.emotional.process_stimulus(text, valence=valence)
        self.print_colored(f"Emozione: {emotion.primary_emotion.value}", Fore.MAGENTA)
        self.print_colored(f"Intensità: {emotion.intensity:.2f}", Fore.MAGENTA)
        self.print_colored(f"Valenza: {emotion.valence:.2f}", Fore.MAGENTA)
        
        # 4. Sistema Metacognitivo
        self.print_colored("\n[Sistema Metacognitivo]", Fore.BLUE)
        self.metacognition.reflect_on_learning("demo", emotion.intensity, percept.confidence)
        strategy = self.metacognition.plan_learning_strategy("demo")
        understanding = self.metacognition.get_understanding_level("demo")
        self.print_colored(f"Strategia: {strategy.name if hasattr(strategy, 'name') else strategy}", Fore.BLUE)
        self.print_colored(f"Comprensione: {understanding:.2f}", Fore.BLUE)
        
        # 5. Sistema di Comunicazione
        self.print_colored("\n[Sistema di Comunicazione]", Fore.RED)
        response = self.communication.generate_response(
            input_text=text,
            emotion=emotion,
            mode=mode
        )
        self.print_colored(f"Risposta: {response.content}", Fore.RED)
        self.print_colored(f"Stile: {response.style.value}", Fore.RED)
        
        # 6. Evoluzione Cognitiva
        self.print_colored("\n[Sistema di Evoluzione Cognitiva]", Fore.CYAN)
        evolution_result = self.evolution.process_experience({
            "input": text,
            "percept": percept,
            "emotion": emotion,
            "response": response
        })
        self.print_colored(f"Livello Cognitivo: {evolution_result:.2f}", Fore.CYAN)
        
        # Pausa per leggibilità
        time.sleep(1)
        
def main():
    """Esegue la demo completa"""
    demo = DemoSistema()
    
    # 1. Input semplice
    demo.process_input(
        "Ciao! Come stai?",
        expected_emotion=EmotionType.JOY,
        mode=CommunicationMode.NATURAL
    )
    
    # 2. Domanda tecnica
    demo.process_input(
        "Puoi spiegarmi come funziona l'algoritmo di gradient descent?",
        expected_emotion=EmotionType.ANTICIPATION,
        mode=CommunicationMode.TECHNICAL
    )
    
    # 3. Espressione di frustrazione
    demo.process_input(
        "Non riesco a capire questo concetto, è troppo difficile!",
        expected_emotion=EmotionType.SADNESS,
        mode=CommunicationMode.EMPATHETIC
    )
    
    # 4. Momento di comprensione
    demo.process_input(
        "Ah! Ora ho capito! È come cercare il punto più basso di una valle!",
        expected_emotion=EmotionType.JOY,
        mode=CommunicationMode.NATURAL
    )
    
    # 5. Riflessione profonda
    demo.process_input(
        "Mi chiedo se possiamo applicare questo concetto ad altri problemi di ottimizzazione...",
        expected_emotion=EmotionType.ANTICIPATION,
        mode=CommunicationMode.TECHNICAL
    )
    
    # 6. Input complesso con pattern
    demo.process_input(
        "Ho notato che quando aumentiamo il learning rate, il modello converge più velocemente ma rischia di overshooting. " + 
        "D'altra parte, con un learning rate troppo basso, la convergenza è più stabile ma molto più lenta. " +
        "Forse potremmo implementare un learning rate adattivo?",
        expected_emotion=EmotionType.TRUST,
        mode=CommunicationMode.TECHNICAL
    )

if __name__ == "__main__":
    main()
