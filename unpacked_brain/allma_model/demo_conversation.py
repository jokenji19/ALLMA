"""
Demo di una conversazione naturale con il sistema ALLMA.
"""

from core.personalization_integration import PersonalizationIntegration
from datetime import datetime
import time

def print_allma(text):
    """Stampa una risposta di ALLMA"""
    print("\n🤖 ALLMA:", text)
    time.sleep(1)  # Simula un tempo di risposta naturale

def print_user(text):
    """Stampa un input dell'utente"""
    print("\n👤 Utente:", text)
    time.sleep(0.5)

def print_section(title):
    """Stampa una sezione formattata"""
    print("\n" + "="*50)
    print(f" {title} ")
    print("="*50)

def simulate_conversation():
    # Inizializza il sistema
    integration = PersonalizationIntegration()
    
    print_section("Conversazione di Esempio con ALLMA")
    
    # Mattina - Prima interazione
    context = {'time_of_day': 'morning', 'current_time': '08:30'}
    
    print_user("Buongiorno! Mi sono appena svegliato e sto per iniziare la mia giornata.")
    result = integration.process_interaction(
        "Buongiorno! Mi sono appena svegliato e sto per iniziare la mia giornata.",
        context
    )
    print_allma("Buongiorno! Come preferisci iniziare la tua giornata?")
    
    print_user("Di solito mi piace fare colazione mentre leggo le notizie, poi programmo un po' e faccio esercizio.")
    result = integration.process_interaction(
        "Di solito mi piace fare colazione mentre leggo le notizie, poi programmo un po' e faccio esercizio.",
        context
    )
    print_allma("Ho notato che hai una routine mattutina ben strutturata! "
                "Ti piace combinare attività rilassanti come la colazione e la lettura "
                "con attività più impegnative come la programmazione e l'esercizio fisico.")
    
    # Pomeriggio - Problema da risolvere
    context = {'time_of_day': 'afternoon', 'current_time': '14:30'}
    
    print_user("Oggi ho un problema con il mio codice perché quando eseguo il test, ricevo sempre un errore.")
    result = integration.process_interaction(
        "Oggi ho un problema con il mio codice perché quando eseguo il test, ricevo sempre un errore.",
        context
    )
    print_allma("Capisco la tua frustrazione. Quando incontri errori nei test, "
                "è utile procedere step by step. Puoi dirmi di più sull'errore specifico?")
    
    print_user("Sì, quando eseguo il test, il sistema dice che la variabile non è definita, ma sono sicuro di averla inizializzata.")
    result = integration.process_interaction(
        "Sì, quando eseguo il test, il sistema dice che la variabile non è definita, ma sono sicuro di averla inizializzata.",
        context
    )
    print_allma("Questo è un classico problema di scope delle variabili. "
                "Se il test non riesce a vedere la variabile, potrebbe essere perché: "
                "1) La variabile è definita in un altro scope "
                "2) L'inizializzazione avviene dopo l'uso "
                "3) C'è un problema di importazione. "
                "Vuoi che analizziamo insieme il codice?")
    
    # Sera - Riflessione
    context = {'time_of_day': 'evening', 'current_time': '19:00'}
    
    print_user("Sono molto soddisfatto perché oggi ho risolto quel bug che mi dava problemi!")
    result = integration.process_interaction(
        "Sono molto soddisfatto perché oggi ho risolto quel bug che mi dava problemi!",
        context
    )
    print_allma("Mi fa piacere sentire che sei riuscito a risolvere il problema! "
                "Ho notato che il tuo stato emotivo è molto positivo. "
                "Risolvere i bug può essere davvero gratificante, vero?")
    
    print_user("Sì, infatti! Ho imparato che devo sempre controllare lo scope delle variabili quando lavoro con i test.")
    result = integration.process_interaction(
        "Sì, infatti! Ho imparato che devo sempre controllare lo scope delle variabili quando lavoro con i test.",
        context
    )
    print_allma("È un'ottima lezione appresa! Ho memorizzato questa esperienza "
                "e noto che hai fatto un importante collegamento causale tra il debugging "
                "e il concetto di scope delle variabili. "
                "Questo tipo di comprensione aiuta a prevenire problemi simili in futuro.")
    
    # Statistiche finali
    print_section("Analisi della Conversazione")
    print("\nPreferenze Utente Sviluppate:")
    print("- Routine Mattutina:", integration.user_preferences['morning_routine'])
    print("- Attività Comuni:", list(integration.user_preferences['common_activities']))
    print("- Orari di Interazione:", integration.user_preferences['interaction_times'])
    
    print("\nStatistiche di Apprendimento:")
    print("- Numero di Interazioni:", integration.daily_stats['interaction_count'])
    print("- Topics Discussi:", list(integration.daily_stats['topics_discussed']))

if __name__ == "__main__":
    simulate_conversation()
