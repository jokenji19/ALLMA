"""
Demo interattiva del sistema di apprendimento incrementale ALLMA.
Simula una conversazione reale con un nuovo utente, mostrando tutte le capacità del sistema.
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

class DemoInterattiva:
    def __init__(self):
        """Inizializza il sistema"""
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
        
    def print_system_status(self):
        """Mostra lo stato attuale del sistema"""
        self.print_colored("\n=== Stato del Sistema ===", Fore.CYAN, bold=True)
        
        # Memoria
        recent_items = self.memory.get_recent_items(3)
        if recent_items:
            self.print_colored("\n📚 Memoria Recente:", Fore.GREEN)
            for item in recent_items:
                self.print_colored(f"- {item.content}", Fore.GREEN)
                
        # Stato Emotivo
        self.print_colored("\n❤️ Stato Emotivo:", Fore.MAGENTA)
        emotion = self.emotional.current_state
        self.print_colored(f"Emozione: {emotion}", Fore.MAGENTA)
        
        # Livello Cognitivo
        self.print_colored("\n🧠 Livello Cognitivo:", Fore.BLUE)
        cognitive_level = self.evolution.cognitive_abilities.get("general", 0.0)
        self.print_colored(f"Livello: {cognitive_level:.2f}", Fore.BLUE)
        
    def process_user_input(self, text: str):
        """Processa l'input dell'utente e mostra la risposta del sistema"""
        self.print_colored("\n=== Input Utente ===", Fore.CYAN, bold=True)
        self.print_colored(f"👤 {text}", Fore.WHITE)
        
        # 1. Percezione
        self.print_colored("\n🔍 Analisi Percettiva:", Fore.YELLOW)
        percept = self.perception.process_input(text, InputType.TEXT)
        self.print_colored(f"Confidenza: {percept.confidence:.2f}", Fore.YELLOW)
        if percept.patterns:
            self.print_colored("Pattern rilevati:", Fore.YELLOW)
            for pattern in percept.patterns:
                self.print_colored(f"- {pattern.pattern_type.value}: {pattern.confidence:.2f}", Fore.YELLOW)
                
        # 2. Analisi Emotiva
        self.print_colored("\n❤️ Analisi Emotiva:", Fore.MAGENTA)
        emotion = self.emotional.process_stimulus(text)
        self.print_colored(f"Emozione Primaria: {emotion.primary_emotion.value}", Fore.MAGENTA)
        self.print_colored(f"Intensità: {emotion.intensity:.2f}", Fore.MAGENTA)
        
        # 3. Memoria
        self.print_colored("\n📚 Memorizzazione:", Fore.GREEN)
        self.memory.add_item(MemoryItem(
            content=text,
            timestamp=datetime.now(),
            importance=percept.confidence,
            emotional_valence=emotion.valence,
            associations=[],
            recall_count=0,
            last_recall=datetime.now()
        ))
        self.print_colored("Input memorizzato con successo", Fore.GREEN)
        
        # 4. Metacognizione
        self.print_colored("\n🤔 Analisi Metacognitiva:", Fore.BLUE)
        self.metacognition.reflect_on_learning("conversation", emotion.intensity, percept.confidence)
        strategy = self.metacognition.plan_learning_strategy("conversation")
        understanding = self.metacognition.get_understanding_level("conversation")
        self.print_colored(f"Livello di Comprensione: {understanding:.2f}", Fore.BLUE)
        
        # 5. Risposta
        self.print_colored("\n💬 Generazione Risposta:", Fore.RED)
        mode = CommunicationMode.EMPATHETIC if emotion.intensity > 0.6 else CommunicationMode.NATURAL
        response = self.communication.generate_response(text, emotion, mode)
        self.print_colored(f"🤖 {response.content}", Fore.RED)
        
        # 6. Evoluzione
        evolution_result = self.evolution.process_experience({
            "input": text,
            "percept": percept,
            "emotion": emotion,
            "response": response
        })
        
        # Pausa per leggibilità
        time.sleep(1)
        
def main():
    """Esegue la demo interattiva"""
    demo = DemoInterattiva()
    
    # Introduzione
    demo.print_colored("\n=== ALLMA: Sistema di Apprendimento Incrementale ===", Fore.CYAN, bold=True)
    demo.print_colored("\nBenvenuto! Sono ALLMA, un sistema di apprendimento incrementale.", Fore.WHITE)
    demo.print_colored("Posso percepire, comprendere, memorizzare e imparare dalle nostre interazioni.", Fore.WHITE)
    demo.print_colored("\nProviamo a conversare! Ecco alcuni esempi di interazioni:", Fore.WHITE)
    
    # Demo progressiva
    conversations = [
        # 1. Saluto semplice
        "Ciao! Sono un nuovo utente e vorrei capire come funzioni.",
        
        # 2. Domanda sulle capacità
        "Quali sono le tue principali capacità di apprendimento?",
        
        # 3. Espressione emotiva
        "Sono davvero impressionato da come riesci a capire le emozioni!",
        
        # 4. Domanda tecnica
        "Mi spieghi come funziona il tuo sistema di memoria a breve termine?",
        
        # 5. Feedback con frustrazione
        "Non sono sicuro di aver capito bene come funziona la memoria...",
        
        # 6. Comprensione
        "Ah, ora ho capito! È come un sistema che organizza le informazioni per importanza e le collega tra loro!",
        
        # 7. Domanda complessa
        "Come gestisci l'integrazione tra il sistema emotivo e quello cognitivo? Ci sono dei pattern ricorrenti?",
        
        # 8. Riflessione metacognitiva
        "È interessante vedere come il tuo livello di comprensione si evolve durante la conversazione. Come funziona questo processo?",
        
        # 9. Input tecnico avanzato
        """Ho notato che il tuo sistema di apprendimento incrementale utilizza diversi sottosistemi che lavorano in parallelo:
        percezione, emozione, memoria, metacognizione e evoluzione cognitiva. 
        Questo approccio modulare permette una grande flessibilità e adattabilità."""
    ]
    
    # Processa ogni conversazione
    for i, text in enumerate(conversations, 1):
        demo.print_colored(f"\n=== Interazione {i}/{len(conversations)} ===", Fore.CYAN, bold=True)
        demo.process_user_input(text)
        demo.print_system_status()
        time.sleep(2)  # Pausa tra le interazioni
        
    # Conclusione
    demo.print_colored("\n=== Fine Demo ===", Fore.CYAN, bold=True)
    demo.print_colored("Questa demo ha mostrato le mie principali capacità:", Fore.WHITE)
    demo.print_colored("1. Percezione e analisi del testo", Fore.WHITE)
    demo.print_colored("2. Gestione delle emozioni", Fore.WHITE)
    demo.print_colored("3. Memoria a breve termine", Fore.WHITE)
    demo.print_colored("4. Metacognizione e apprendimento", Fore.WHITE)
    demo.print_colored("5. Comunicazione adattiva", Fore.WHITE)
    demo.print_colored("6. Evoluzione cognitiva", Fore.WHITE)

if __name__ == "__main__":
    main()
