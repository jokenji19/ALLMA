import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from typing import Dict, List, Any
from core.nlp_processor import NLPProcessor
from core.language_understanding import LanguageUnderstanding
from core.personalization_integration import PersonalizationIntegration

def print_separator(title: str = ""):
    """Stampa un separatore con titolo opzionale"""
    print("\n" + "="*50)
    if title:
        print(f" {title} ")
        print("="*50)

def test_nlp_understanding():
    """Test del sistema NLP e comprensione del linguaggio"""
    print_separator("Test Sistema NLP e Comprensione")
    
    # Inizializza i componenti
    nlp = NLPProcessor()
    understanding = LanguageUnderstanding()
    integration = PersonalizationIntegration()
    
    # Test 1: Analisi Base del Testo
    print_separator("Fase 1: Analisi Base del Testo")
    
    test_text = "Mi piacerebbe sapere di più sulla storia di Roma antica, specialmente il periodo di Augusto."
    
    print("\n👤 Input:", test_text)
    
    # Analisi NLP
    tokens = nlp.tokenize(test_text)
    pos_tags = nlp.pos_tag(tokens)
    entities = nlp.extract_entities(test_text)
    
    print("\n📊 Analisi NLP:")
    print(f"  Tokens: {tokens[:5]}...")
    print(f"  POS Tags: {pos_tags[:5]}...")
    print(f"  Entità: {entities}")
    
    # Test 2: Comprensione Semantica
    print_separator("Fase 2: Comprensione Semantica")
    
    intent = understanding.detect_intent(test_text)
    topics = understanding.extract_topics(test_text)
    sentiment = understanding.analyze_sentiment(test_text)
    
    print("\n🧠 Comprensione Semantica:")
    print(f"  Intent: {intent}")
    print(f"  Topics: {topics}")
    print(f"  Sentiment: {sentiment}")
    
    # Test 3: Gestione del Contesto
    print_separator("Fase 3: Gestione del Contesto")
    
    context = {
        'previous_topic': 'storia',
        'user_interests': ['storia antica', 'archeologia'],
        'conversation_history': ['Parliamo di storia antica']
    }
    
    follow_up = "E cosa ne pensi del suo successore Tiberio?"
    
    print("\n👤 Follow-up:", follow_up)
    
    resolved_reference = understanding.resolve_references(follow_up, context)
    enhanced_understanding = understanding.enhance_with_context(follow_up, context)
    
    print("\n🔍 Analisi Contestuale:")
    print(f"  Riferimenti Risolti: {resolved_reference}")
    print(f"  Comprensione Arricchita: {enhanced_understanding}")
    
    # Test 4: Integrazione con il Sistema di Personalizzazione
    print_separator("Fase 4: Integrazione con Personalizzazione")
    
    personalized_response = integration.process_interaction(
        follow_up,
        {
            'nlp_analysis': {'tokens': tokens, 'entities': entities},
            'semantic_understanding': {'intent': intent, 'topics': topics},
            'context': context
        }
    )
    
    print("\n🤖 Risposta Personalizzata:")
    print(f"  {personalized_response.get('response', 'Nessuna risposta generata')}")
    print(f"  Confidenza: {personalized_response.get('confidence', 0):.2f}")
    
    # Statistiche Finali
    print_separator("Statistiche Finali")
    
    print("\n📈 Performance del Sistema:")
    print(f"  Accuratezza NLP: {nlp.get_accuracy():.2f}")
    print(f"  Precisione Semantica: {understanding.get_precision():.2f}")
    print(f"  Recall Contestuale: {understanding.get_recall():.2f}")

if __name__ == "__main__":
    test_nlp_understanding()
