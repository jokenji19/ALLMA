"""
Test del sistema di riconoscimento pattern
"""
from incremental_learning.pattern_recognition_system import PatternRecognitionSystem

def test_pattern_recognition():
    # Inizializza il sistema
    pattern_system = PatternRecognitionSystem()
    
    # Test 1: Riconoscimento topic tecnologia
    text_tech = "Mi piace programmare e sviluppare software usando l'intelligenza artificiale"
    pattern = pattern_system.learn_pattern(text_tech)
    print("\nTest 1 - Topic Tecnologia:")
    print(f"Testo: {text_tech}")
    print(f"Pattern rilevato: {pattern}")
    assert pattern.topic == "tecnologia", "Errore nel riconoscimento topic tecnologia"
    
    # Test 2: Analisi sentiment
    text_emotion = "Sono molto felice di imparare cose nuove!"
    v, a, d = pattern_system.analyze_sentiment(text_emotion)
    print("\nTest 2 - Analisi Sentiment:")
    print(f"Testo: {text_emotion}")
    print(f"VAD scores: Valence={v:.2f}, Arousal={a:.2f}, Dominance={d:.2f}")
    assert v > 0.5, "Errore nell'analisi della valence positiva"
    
    # Test 3: Estrazione temi
    texts = [
        "Mi piace programmare in Python",
        "L'intelligenza artificiale è interessante",
        "Sto imparando nuove tecnologie"
    ]
    themes = pattern_system.analyze_themes(texts)
    print("\nTest 3 - Analisi Temi:")
    print(f"Testi: {texts}")
    print("Temi principali:")
    for theme in themes[:3]:
        print(f"- {theme.text} (confidence: {theme.confidence:.2f})")
    assert len(themes) > 0, "Errore nell'estrazione dei temi"
    
    # Test 4: Calcolo similarità
    text1 = "Mi piace la programmazione"
    text2 = "Amo sviluppare software"
    pattern1 = pattern_system.learn_pattern(text1)
    pattern2 = pattern_system.learn_pattern(text2)
    similarity = pattern_system.calculate_pattern_similarity(pattern1, pattern2)
    print("\nTest 4 - Similarità Pattern:")
    print(f"Testo 1: {text1}")
    print(f"Testo 2: {text2}")
    print(f"Similarità: {similarity:.2f}")
    
    print("\nTutti i test completati con successo!")
    
if __name__ == "__main__":
    test_pattern_recognition()
