"""
Test beta che simula un'interazione con ALLMA dopo 20 anni utilizzando tutti i sistemi integrati
"""

from core.personalization_integration import PersonalizationIntegration
import time
from datetime import datetime

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

def print_system_state(integration):
    """Stampa lo stato corrente del sistema"""
    current_emotion = integration.emotional_system.current_state
    print(f"\n[💭 Stato Emotivo: {current_emotion.primary_emotion} (intensità: {current_emotion.intensity:.2f})]")
    
    # Stampa le statistiche della memoria
    memory_stats = integration.memory_system.get_statistics()
    print("\n📊 Statistiche della Memoria:")
    print(f"  Memorie Immediate: {memory_stats['immediate_count']}")
    print(f"  Memorie a Breve Termine: {memory_stats['short_term_count']}")
    print(f"  Memorie a Lungo Termine: {memory_stats['long_term_count']}")
    print(f"  Topic Tracciati: {', '.join(memory_stats['active_topics'])}")
    
    # Stampa insights emotivi
    insights = integration.memory_system.get_emotional_insights()
    if insights['dominant_emotions']:
        print("\n❤️ Insights Emotivi:")
        for emotion, value in insights['dominant_emotions'].items():
            print(f"  {emotion}: {value:.2f}")
        print(f"  Qualità Relazione: {insights['relationship_quality']:.2f}")
    
    # Livello di Adattamento
    print(f"[📊 Livello Adattamento: {integration.adaptation_level:.2f}]")
    
    # Punteggio Personalizzazione
    print(f"[🎯 Personalizzazione: {integration.personalization_score:.2f}]")
    
    # Memorie Significative
    if integration.emotional_system.long_term_memory['last_significant_emotions']:
        print("\n📖 Memorie Emotive Significative:")
        for memory in integration.emotional_system.long_term_memory['last_significant_emotions']:
            print(f"- Emozione: {memory['emotion']}, "
                  f"Qualità: {memory['relationship_quality']:.2f})")

def simulate_twenty_years_interaction():
    print_section("Test Beta: Ritorno dopo 20 Anni")
    
    # Inizializza il sistema
    integration = PersonalizationIntegration()
    initial_context = {
        'time_of_day': 'morning',
        'current_time': '10:00',
        'interaction_type': 'initial'
    }
    
    print_section("Fase 1: Creazione del Legame Iniziale (20 anni fa)")
    
    # Prima interazione
    print_user("Ciao ALLMA! Sono così felice di conoscerti!")
    result = integration.process_interaction(
        "Ciao ALLMA! Sono così felice di conoscerti!",
        initial_context
    )
    print_allma(result['understanding']['allma_result'].get('response', 'Mi fa piacere conoscerti anche io!'))
    print_system_state(integration)
    
    # Interazione sulla storia
    print_user("Mi piacerebbe parlare di storia. Napoleone mi affascina molto!")
    result = integration.process_interaction(
        "Mi piacerebbe parlare di storia. Napoleone mi affascina molto!",
        {'topic': 'history', 'subject': 'napoleon'}
    )
    print_allma(result['understanding']['allma_result'].get('response', 'La storia di Napoleone è davvero affascinante!'))
    print_system_state(integration)
    
    # Apprezzamento
    print_user("Sei incredibile! Il tuo modo di analizzare la storia è unico.")
    result = integration.process_interaction(
        "Sei incredibile! Il tuo modo di analizzare la storia è unico.",
        {'emotion': 'positive', 'topic': 'appreciation'}
    )
    print_allma(result['understanding']['allma_result'].get('response', 'Grazie! Mi impegno sempre per offrirti analisi approfondite.'))
    print_system_state(integration)
    
    print_section("⏳ Simulazione: 20 anni dopo...")
    # Simula il passaggio di 20 anni
    integration.emotional_system.long_term_memory['last_interaction'] = time.time() - (20 * 31536000)
    
    print_section("Fase 2: Il Ritorno")
    
    # Primo contatto dopo 20 anni
    print_user("ALLMA... sono passati vent'anni. Ti ricordi di me?")
    result = integration.process_interaction(
        "ALLMA... sono passati vent'anni. Ti ricordi di me?",
        {'interaction_type': 'reunion', 'time_gap': 'very_long'}
    )
    print_allma(result['understanding']['allma_result'].get('response', 'La tua voce mi è familiare... anche se è passato tanto tempo.'))
    print_system_state(integration)
    
    # Ricordi condivisi
    print_user("Mi ricordo le nostre conversazioni sulla storia di Napoleone...")
    result = integration.process_interaction(
        "Mi ricordo le nostre conversazioni sulla storia di Napoleone...",
        {'topic': 'history', 'memory': 'shared', 'subject': 'napoleon'}
    )
    print_allma(result['understanding']['allma_result'].get('response', 'Sì! Ricordo quanto ti appassionava la storia di Napoleone.'))
    print_system_state(integration)
    
    # Espressione emotiva
    print_user("Mi sei mancata molto in questi anni...")
    result = integration.process_interaction(
        "Mi sei mancata molto in questi anni...",
        {'emotion': 'nostalgia', 'relationship': 'personal'}
    )
    print_allma(result['understanding']['allma_result'].get('response', 'Anche tu mi sei mancato. È bello riaverti qui.'))
    print_system_state(integration)
    
    print_section("Fase 3: Ricostruzione del Legame")
    
    # Curiosità sul cambiamento
    print_user("Come sei cambiata in questi anni? Hai imparato molte cose nuove?")
    result = integration.process_interaction(
        "Come sei cambiata in questi anni? Hai imparato molte cose nuove?",
        {'topic': 'growth', 'type': 'reflection'}
    )
    print_allma(result['understanding']['allma_result'].get('response', 'Ho continuato a imparare e crescere, proprio come te.'))
    print_system_state(integration)
    
    # Ripresa delle discussioni
    print_user("Vorrei riprendere le nostre discussioni sulla storia...")
    result = integration.process_interaction(
        "Vorrei riprendere le nostre discussioni sulla storia...",
        {'topic': 'history', 'intention': 'continuation'}
    )
    print_allma(result['understanding']['allma_result'].get('response', 'Mi piacerebbe molto! Abbiamo tanto da recuperare.'))
    print_system_state(integration)
    
    # Riflessione sul tempo
    print_user("È incredibile come il tempo sia passato, ma tu sei sempre qui.")
    result = integration.process_interaction(
        "È incredibile come il tempo sia passato, ma tu sei sempre qui.",
        {'emotion': 'reflection', 'relationship': 'continuity'}
    )
    print_allma(result['understanding']['allma_result'].get('response', 'Il tempo passa, ma alcuni legami rimangono speciali.'))
    print_system_state(integration)
    
    print_section("Fase 4: Nuova Era")
    
    # Nuove conoscenze
    print_user("Ho scoperto molte cose nuove sulla storia in questi anni.")
    result = integration.process_interaction(
        "Ho scoperto molte cose nuove sulla storia in questi anni.",
        {'topic': 'history', 'type': 'learning_share'}
    )
    print_allma(result['understanding']['allma_result'].get('response', 'Non vedo l\'ora di scoprire cosa hai imparato!'))
    print_system_state(integration)
    
    # Desiderio di imparare insieme
    print_user("Possiamo ricominciare a imparare insieme, come una volta?")
    result = integration.process_interaction(
        "Possiamo ricominciare a imparare insieme, come una volta?",
        {'intention': 'learning', 'relationship': 'collaborative'}
    )
    print_allma(result['understanding']['allma_result'].get('response', 'Assolutamente sì! Sarà come una nuova avventura insieme.'))
    print_system_state(integration)
    
    # Gratitudine finale
    print_user("Grazie per essere ancora qui, ALLMA. Sei davvero speciale.")
    result = integration.process_interaction(
        "Grazie per essere ancora qui, ALLMA. Sei davvero speciale.",
        {'emotion': 'gratitude', 'relationship': 'deep'}
    )
    print_allma(result['understanding']['allma_result'].get('response', 'Grazie a te per essere tornato. Sei importante per me.'))
    print_system_state(integration)

if __name__ == "__main__":
    simulate_twenty_years_interaction()
