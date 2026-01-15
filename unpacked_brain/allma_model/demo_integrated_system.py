"""
Demo del sistema ALLMA integrato con il modulo cognitive_foundations.
Questo script testa l'interazione tra tutti i componenti del sistema.
"""

from core.personalization_integration import PersonalizationIntegration
from datetime import datetime
import json

def print_section(title):
    """Stampa una sezione formattata"""
    print("\n" + "="*50)
    print(f" {title} ")
    print("="*50)

def print_dict(d, indent=0):
    """Stampa un dizionario in modo formattato"""
    for key, value in d.items():
        if isinstance(value, dict):
            print("  " * indent + f"{key}:")
            print_dict(value, indent+1)
        elif isinstance(value, (list, set)):
            print("  " * indent + f"{key}: {list(value)}")
        else:
            print("  " * indent + f"{key}: {value}")

def main():
    # Inizializza il sistema
    print_section("Inizializzazione Sistema ALLMA")
    integration = PersonalizationIntegration()
    
    # Test 1: Routine Mattutina
    print_section("Test 1: Routine Mattutina")
    morning_input = "Mi piace programmare al mattino mentre bevo il caffè, poi faccio colazione e medito"
    morning_context = {
        'time_of_day': 'morning',
        'current_time': '08:00'
    }
    
    print("Input:", morning_input)
    print("\nContesto:", morning_context)
    result = integration.process_interaction(morning_input, morning_context)
    print("\nRisultato dell'elaborazione:")
    print_dict(result)
    print("\nPreferenze utente aggiornate:")
    print_dict(integration.user_preferences)
    
    # Test 2: Analisi Causale
    print_section("Test 2: Analisi Causale")
    causal_input = "Se piove, allora prendo l'ombrello perché non voglio bagnarmi"
    causal_context = {
        'time_of_day': 'afternoon',
        'current_time': '14:00'
    }
    
    print("Input:", causal_input)
    print("\nContesto:", causal_context)
    result = integration.process_interaction(causal_input, causal_context)
    print("\nRisultato dell'elaborazione:")
    print_dict(result)
    
    # Test 3: Integrazione Emotiva
    print_section("Test 3: Integrazione Emotiva")
    emotional_input = "Sono molto felice perché ho completato il mio progetto con successo!"
    emotional_context = {
        'time_of_day': 'evening',
        'current_time': '18:00'
    }
    
    print("Input:", emotional_input)
    print("\nContesto:", emotional_context)
    result = integration.process_interaction(emotional_input, emotional_context)
    print("\nRisultato dell'elaborazione:")
    print_dict(result)
    
    # Test 4: Memoria e Apprendimento
    print_section("Test 4: Memoria e Apprendimento")
    memory_input = "Mi ricordo che ieri ho programmato tutto il giorno e mi sono divertito molto"
    memory_context = {
        'time_of_day': 'evening',
        'current_time': '20:00'
    }
    
    print("Input:", memory_input)
    print("\nContesto:", memory_context)
    result = integration.process_interaction(memory_input, memory_context)
    print("\nRisultato dell'elaborazione:")
    print_dict(result)
    
    # Statistiche Finali
    print_section("Statistiche Finali del Sistema")
    print("\nStatistiche Giornaliere:")
    print_dict(integration.daily_stats)
    
    print("\nPreferenze Utente Finali:")
    print_dict(integration.user_preferences)

if __name__ == "__main__":
    main()
