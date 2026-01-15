"""
Demo interattiva del sistema di riconoscimento pattern
"""
from incremental_learning.pattern_recognition_system import PatternRecognitionSystem
from typing import List, Dict, Any
import time

class DemoObserver:
    def __init__(self):
        self.patterns = []
        
    def update(self, event_type: str, data: Dict[str, Any]):
        print(f"\nEvento ricevuto: {event_type}")
        if event_type == "pattern_updated":
            pattern = data["pattern"]
            self.patterns.append(pattern)
            print(f"Nuovo pattern rilevato: {pattern.text}")
            print(f"Topic: {pattern.topic}")
            print(f"Confidence: {pattern.confidence:.2f}")

def print_separator():
    print("\n" + "="*50 + "\n")

def run_demo():
    # Inizializza il sistema
    print("Inizializzazione del sistema di riconoscimento pattern...")
    system = PatternRecognitionSystem()
    
    # Registra l'observer
    observer = DemoObserver()
    system.register_observer(observer)
    
    while True:
        print_separator()
        print("Demo Interattiva - Sistema di Riconoscimento Pattern")
        print("\nOpzioni disponibili:")
        print("1. Analizza un testo")
        print("2. Analizza sentiment (VAD)")
        print("3. Confronta due testi")
        print("4. Analizza temi in più testi")
        print("5. Visualizza pattern appresi")
        print("6. Esci")
        
        choice = input("\nScegli un'opzione (1-6): ")
        
        if choice == "1":
            print_separator()
            text = input("Inserisci il testo da analizzare: ")
            pattern = system.learn_pattern(text)
            print("\nRisultati dell'analisi:")
            print(f"Topic rilevato: {pattern.topic}")
            print(f"Confidence: {pattern.confidence:.2f}")
            print("\nMetadati:")
            for key, value in pattern.metadata.items():
                if key != "embedding":
                    print(f"- {key}: {value}")
                    
        elif choice == "2":
            print_separator()
            text = input("Inserisci il testo per l'analisi emotiva: ")
            v, a, d = system.analyze_sentiment(text)
            print("\nAnalisi VAD (Valence, Arousal, Dominance):")
            print(f"Valence (positività): {v:.2f}")
            print(f"Arousal (intensità): {a:.2f}")
            print(f"Dominance (controllo): {d:.2f}")
            
            # Interpretazione
            print("\nInterpretazione:")
            if v > 0.6:
                print("- Sentiment positivo")
            elif v < 0.4:
                print("- Sentiment negativo")
            else:
                print("- Sentiment neutro")
                
            if a > 0.6:
                print("- Alta intensità emotiva")
            elif a < 0.4:
                print("- Bassa intensità emotiva")
            
        elif choice == "3":
            print_separator()
            print("Confronto tra due testi:")
            text1 = input("Inserisci il primo testo: ")
            text2 = input("Inserisci il secondo testo: ")
            
            pattern1 = system.learn_pattern(text1)
            pattern2 = system.learn_pattern(text2)
            
            similarity = system.calculate_pattern_similarity(pattern1, pattern2)
            print(f"\nSimilarità tra i testi: {similarity:.2f}")
            
            if similarity > 0.8:
                print("I testi sono molto simili")
            elif similarity > 0.5:
                print("I testi hanno alcune somiglianze")
            else:
                print("I testi sono abbastanza diversi")
                
        elif choice == "4":
            print_separator()
            print("Analisi temi in più testi")
            texts = []
            while True:
                text = input("Inserisci un testo (o premi invio per terminare): ")
                if not text:
                    break
                texts.append(text)
                
            if texts:
                themes = system.analyze_themes(texts)
                print("\nTemi principali identificati:")
                for i, theme in enumerate(themes[:5], 1):
                    print(f"\n{i}. Tema: {theme.text}")
                    print(f"   Confidence: {theme.confidence:.2f}")
                    if "features" in theme.metadata:
                        print("   Caratteristiche linguistiche:")
                        for feat_type, feats in theme.metadata["features"].items():
                            if feats:
                                print(f"   - {feat_type}: {', '.join(feats[:3])}...")
                
        elif choice == "5":
            print_separator()
            print("Pattern appresi finora:")
            for i, pattern in enumerate(observer.patterns, 1):
                print(f"\n{i}. Testo: {pattern.text}")
                print(f"   Topic: {pattern.topic}")
                print(f"   Confidence: {pattern.confidence:.2f}")
                if "sentiment" in pattern.metadata:
                    s = pattern.metadata["sentiment"]
                    print(f"   Sentiment (VAD): {s['valence']:.2f}, {s['arousal']:.2f}, {s['dominance']:.2f}")
                
        elif choice == "6":
            print_separator()
            print("Grazie per aver utilizzato la demo!")
            break
            
        else:
            print("\nOpzione non valida. Riprova.")
            
        time.sleep(1)  # Breve pausa per leggibilità

if __name__ == "__main__":
    run_demo()
