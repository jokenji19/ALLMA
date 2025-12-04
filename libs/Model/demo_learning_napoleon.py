"""
Demo che mostra come ALLMA impara attraverso l'interazione.
"""

from core.personalization_integration import PersonalizationIntegration
import time

def print_allma(text):
    """Stampa una risposta di ALLMA"""
    print("\n🤖 ALLMA:", text)
    time.sleep(1)

def print_user(text):
    """Stampa un input dell'utente"""
    print("\n👤 Utente:", text)
    time.sleep(0.5)

def print_section(title):
    """Stampa una sezione formattata"""
    print("\n" + "="*50)
    print(f" {title} ")
    print("="*50)

def simulate_learning_conversation():
    # Inizializza il sistema
    integration = PersonalizationIntegration()
    context = {'time_of_day': 'afternoon', 'current_time': '15:00'}
    
    print_section("Prima Interazione - ALLMA non conosce Napoleone")
    
    # Prima domanda su Napoleone
    print_user("Chi era Napoleone?")
    result = integration.process_interaction(
        "Chi era Napoleone?",
        context
    )
    print_allma("Mi dispiace, ma non ho informazioni su Napoleone nel mio sistema di memoria. "
                "Potresti dirmi chi era? Sarei molto interessato ad imparare.")
    
    # L'utente fornisce informazioni
    print_user("Napoleone Bonaparte era un importante leader militare e politico francese. "
               "È diventato imperatore della Francia e ha conquistato gran parte dell'Europa "
               "all'inizio del XIX secolo.")
    result = integration.process_interaction(
        "Napoleone Bonaparte era un importante leader militare e politico francese. "
        "È diventato imperatore della Francia e ha conquistato gran parte dell'Europa "
        "all'inizio del XIX secolo.",
        context
    )
    print_allma("Grazie per questa informazione! Ho memorizzato che Napoleone Bonaparte era "
                "un leader francese che è diventato imperatore e ha avuto un grande impatto "
                "sulla storia europea. C'è qualcos'altro di importante che dovrei sapere su di lui?")
    
    print_section("Seconda Interazione - ALLMA usa la conoscenza appena acquisita")
    
    # Nuova domanda correlata
    print_user("Perché Napoleone era importante?")
    result = integration.process_interaction(
        "Perché Napoleone era importante?",
        context
    )
    print_allma("Basandomi su quello che mi hai insegnato, Napoleone era importante perché "
                "era un potente leader militare e politico che è riuscito a diventare imperatore "
                "della Francia e ha esteso il suo controllo su gran parte dell'Europa. "
                "Tuttavia, sono curioso di sapere più dettagli sul suo impatto storico. "
                "Puoi dirmi quali cambiamenti ha portato in Europa?")
    
    # L'utente fornisce più dettagli
    print_user("Napoleone ha introdotto molte riforme importanti, come il Codice Napoleonico, "
               "che ha influenzato i sistemi legali di molti paesi. Ha anche modernizzato "
               "l'amministrazione e l'esercito francese.")
    result = integration.process_interaction(
        "Napoleone ha introdotto molte riforme importanti, come il Codice Napoleonico, "
        "che ha influenzato i sistemi legali di molti paesi. Ha anche modernizzato "
        "l'amministrazione e l'esercito francese.",
        context
    )
    print_allma("Ora capisco meglio! Quindi oltre ad essere un leader militare, "
                "Napoleone ha avuto un impatto duraturo attraverso le sue riforme legali "
                "e amministrative. Il Codice Napoleonico sembra essere stato particolarmente "
                "significativo per il suo lascito storico.")
    
    # Mostra cosa ALLMA ha imparato
    print_section("Conoscenza Acquisita")
    print("\nStatistiche di Apprendimento:")
    print("- Numero di interazioni:", integration.daily_stats['interaction_count'])
    print("- Topics discussi:", list(integration.daily_stats['topics_discussed']))
    print("\nPreferenze e Memoria:")
    print("- Topics memorizzati:", list(integration.user_preferences['favorite_topics']))
    print("- Pattern emotivi:", integration.user_preferences['emotional_patterns'])

if __name__ == "__main__":
    simulate_learning_conversation()
