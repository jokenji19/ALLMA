import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import time
from core.personalization_integration import PersonalizationIntegration

def print_section(title):
    print("\n" + "=" * 50)
    print(title)
    print("=" * 50 + "\n")

def print_user(message):
    print(f"👤 Utente: {message}")

def print_allma(message):
    print(f"\n🤖 ALLMA: {message}\n")

def print_memory_state(result):
    print("\n📖 Stato della Memoria:")
    
    if result['memory']['immediate']:
        print("\n🔹 Memoria Immediata:")
        for memory in result['memory']['immediate']:
            print(f"  - {memory}")
    
    if result['memory']['short_term']:
        print("\n🔸 Memoria a Breve Termine:")
        for memory in result['memory']['short_term']:
            print(f"  - {memory}")
    
    if result['memory']['long_term']:
        print("\n💎 Memoria a Lungo Termine:")
        for memory in result['memory']['long_term']:
            print(f"  - {memory}")
    
    stats = result['memory']['memory_stats']
    print(f"\n📊 Statistiche:")
    print(f"  Memorie Immediate: {stats['immediate_count']}")
    print(f"  Memorie a Lungo Termine: {stats['long_term_count']}")
    print(f"  Totale Nodi: {stats['total_nodes']}")
    print(f"  Salute Sistema: {stats['memory_health']:.2f}")
    print(f"  Intensità Emotiva Media: {stats['avg_emotional_intensity']:.2f}")

def test_advanced_memory():
    print_section("Test Sistema di Memoria Avanzato")
    integration = PersonalizationIntegration()
    
    # Fase 1: Creazione Memorie Immediate
    print_section("Fase 1: Creazione Memorie Immediate")
    
    # Prima interazione sulla storia
    print_user("Mi piacerebbe parlare di storia antica, specialmente dell'Impero Romano")
    result = integration.process_interaction(
        "Mi piacerebbe parlare di storia antica, specialmente dell'Impero Romano",
        {'topic': 'storia', 'subject': 'impero_romano'}
    )
    print_allma(result['understanding']['allma_result'].get('response',
        "L'Impero Romano è un argomento affascinante! Da dove vorresti iniziare?"))
    print_memory_state(result)
    
    # Seconda interazione sulla storia
    print_user("Mi interessa particolarmente il periodo di Augusto")
    result = integration.process_interaction(
        "Mi interessa particolarmente il periodo di Augusto",
        {'topic': 'storia', 'subject': 'augusto'}
    )
    print_allma(result['understanding']['allma_result'].get('response',
        "Augusto fu il primo imperatore romano e trasformò la Repubblica in Impero!"))
    print_memory_state(result)
    
    # Cambio argomento
    print_user("Sai, mi piace anche molto l'arte rinascimentale")
    result = integration.process_interaction(
        "Sai, mi piace anche molto l'arte rinascimentale",
        {'topic': 'arte', 'period': 'rinascimento'}
    )
    print_allma(result['understanding']['allma_result'].get('response',
        "Il Rinascimento è stato un periodo straordinario per l'arte. "
        "Interessante come sia stato influenzato anche dalla riscoperta dell'arte romana!"))
    print_memory_state(result)
    
    # Fase 2: Verifica delle connessioni
    print_section("Fase 2: Verifica delle Connessioni")
    
    # Verifica che ci siano connessioni tra i nodi
    memory_stats = integration.memory_system.get_memory_stats()
    assert memory_stats['total_nodes'] > 0
    assert memory_stats['connections_made'] > 0
    
    # Verifica la salute del sistema
    assert memory_stats['memory_health'] > 0.5
    assert memory_stats['avg_emotional_intensity'] > 0
    
    # Fase 3: Collegamenti Tematici
    print_section("Fase 3: Collegamenti Tematici")
    
    # Interazione che collega storia e arte
    print_user("C'è una connessione interessante tra l'arte romana e quella rinascimentale")
    result = integration.process_interaction(
        "C'è una connessione interessante tra l'arte romana e quella rinascimentale",
        {'topics': ['storia', 'arte'], 'connection': True}
    )
    print_allma(result['understanding']['allma_result'].get('response',
        "Esatto! Gli artisti rinascimentali furono fortemente influenzati "
        "dall'arte romana classica. Questo collegamento è evidente nelle loro opere."))
    print_memory_state(result)
    
    # Fase 4: Evoluzione delle Preferenze
    print_section("Fase 4: Evoluzione delle Preferenze")
    
    # Mostra come ALLMA tiene traccia dell'evoluzione degli interessi
    print_user("Ultimamente mi sto appassionando sempre più all'arte che alla storia")
    result = integration.process_interaction(
        "Ultimamente mi sto appassionando sempre più all'arte che alla storia",
        {'topic': 'preferences', 'shift': 'art_focus'}
    )
    print_allma(result['understanding']['allma_result'].get('response',
        "Ho notato questo tuo crescente interesse per l'arte! "
        "È affascinante vedere come i tuoi interessi si evolvono."))
    print_memory_state(result)

if __name__ == "__main__":
    test_advanced_memory()
