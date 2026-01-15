"""
Beta test di ALLMA per un mese intero di interazioni quotidiane.
Simula conversazioni giornaliere di 3 ore con progressione di complessità.
"""

from core.personalization_integration import PersonalizationIntegration
from datetime import datetime, timedelta
import random
import time

class BetaTest:
    def __init__(self):
        self.integration = PersonalizationIntegration()
        self.start_date = datetime(2025, 1, 1)  # Inizia dal 1° gennaio 2025
        self.current_day = 1
        self.total_days = 30
        
        # Temi di conversazione per diversi livelli di complessità
        self.basic_topics = [
            "saluti_base", "routine_quotidiana", "preferenze_base",
            "hobby_semplici", "tempo_meteo", "stati_emotivi"
        ]
        
        self.intermediate_topics = [
            "problemi_lavoro", "apprendimento_coding", "gestione_progetti",
            "relazioni_personali", "obiettivi_personali", "interessi_culturali"
        ]
        
        self.advanced_topics = [
            "debugging_complesso", "architettura_software", "machine_learning",
            "filosofia_tecnologia", "etica_AI", "innovazione_tech"
        ]
        
        # Attività quotidiane per simulare routine
        self.daily_activities = [
            "programmare", "leggere", "esercizio", "meditare", "studiare",
            "lavorare", "rilassarsi", "socializzare"
        ]
        
        # Stati emotivi per simulare variazioni
        self.emotional_states = [
            "felice", "frustrato", "soddisfatto", "preoccupato", "entusiasta",
            "stanco", "motivato", "curioso"
        ]

    def get_time_context(self, hour):
        """Genera il contesto temporale per una data ora"""
        time_of_day = "morning" if 5 <= hour < 12 else \
                      "afternoon" if 12 <= hour < 17 else \
                      "evening" if 17 <= hour < 22 else "night"
        
        return {
            'time_of_day': time_of_day,
            'current_time': f"{hour:02d}:00"
        }

    def simulate_basic_conversation(self, hour):
        """Simula una conversazione base"""
        context = self.get_time_context(hour)
        topic = random.choice(self.basic_topics)
        activity = random.choice(self.daily_activities)
        emotion = random.choice(self.emotional_states)
        
        conversations = [
            (f"👤 Utente: Buongiorno ALLMA, come stai oggi?",
             f"🤖 ALLMA: Ciao! Sto bene, grazie. Vedo che sono le {context['current_time']}. Come posso aiutarti?"),
            
            (f"👤 Utente: Oggi mi sento {emotion}",
             f"🤖 ALLMA: Capisco che ti senti {emotion}. Vuoi parlarne? Sono qui per ascoltarti."),
            
            (f"👤 Utente: Sto per iniziare a {activity}",
             f"🤖 ALLMA: È un ottimo momento per {activity}! Ti aiuta sempre a iniziare bene la giornata. Hai bisogno di suggerimenti?"),
            
            (f"👤 Utente: Parliamo di {topic}?",
             f"🤖 ALLMA: Certo! {topic} è un argomento interessante. Cosa ti piacerebbe sapere in particolare?")
        ]
        
        print(f"\n[Conversazione Base - {context['time_of_day']} {context['current_time']}]")
        for user_msg, allma_msg in conversations:
            print(f"\n{user_msg}")
            print(f"{allma_msg}")
            self.integration.process_interaction(user_msg, context)
            self.integration.process_interaction(allma_msg, context)

    def simulate_intermediate_conversation(self, hour):
        """Simula una conversazione di media complessità"""
        context = self.get_time_context(hour)
        topic = random.choice(self.intermediate_topics)
        activity = random.choice(self.daily_activities)
        
        conversations = [
            (f"👤 Utente: Ho un problema con {topic}, puoi aiutarmi?",
             f"🤖 ALLMA: Certamente! Raccontami di più del tuo problema con {topic}. Che difficoltà stai incontrando?"),
            
            (f"👤 Utente: Non riesco a capire come procedere con {activity} in questo contesto",
             f"🤖 ALLMA: Capisco la tua frustrazione. Analizziamo insieme il processo di {activity} passo per passo. Qual è il punto che ti blocca?"),
            
            (f"👤 Utente: Ho provato diverse soluzioni ma niente sembra funzionare",
             f"🤖 ALLMA: Ok, facciamo un passo indietro. Quali soluzioni hai già provato? Questo mi aiuterà a suggerirti approcci alternativi."),
            
            (f"👤 Utente: Come posso migliorare in questo campo?",
             f"🤖 ALLMA: Basandomi sulla nostra conversazione, ti suggerisco di: 1) Pratica regolare 2) Documentazione 3) Progetti pratici. Vuoi che approfondiamo uno di questi aspetti?")
        ]
        
        print(f"\n[Conversazione Intermedia - {context['time_of_day']} {context['current_time']}]")
        for user_msg, allma_msg in conversations:
            print(f"\n{user_msg}")
            print(f"{allma_msg}")
            self.integration.process_interaction(user_msg, context)
            self.integration.process_interaction(allma_msg, context)

    def simulate_advanced_conversation(self, hour):
        """Simula una conversazione complessa"""
        context = self.get_time_context(hour)
        topic = random.choice(self.advanced_topics)
        
        conversations = [
            (f"👤 Utente: Vorrei approfondire {topic}, ho letto diverse teorie interessanti",
             f"🤖 ALLMA: Eccellente scelta! {topic} è un campo affascinante. Quali teorie hai esplorato? Possiamo analizzarle insieme e vedere come si collegano tra loro."),
            
            (f"👤 Utente: Mi interessa capire l'impatto di {topic} sul futuro della tecnologia",
             f"🤖 ALLMA: È una domanda complessa e stimolante. {topic} sta influenzando profondamente lo sviluppo tecnologico. Consideriamo alcuni scenari chiave..."),
            
            (f"👤 Utente: Come si integra questo con altri concetti avanzati?",
             f"🤖 ALLMA: Ottima domanda! Vedo diverse connessioni interessanti. Per esempio, {topic} si collega strettamente con altri concetti dell'informatica avanzata. Vuoi che esploriamo queste connessioni?"),
            
            (f"👤 Utente: Quali sono le implicazioni pratiche di queste teorie?",
             f"🤖 ALLMA: Le implicazioni sono molteplici. Nel contesto pratico, queste teorie influenzano: 1) Architetture software 2) Processi di sviluppo 3) Paradigmi di programmazione. Su quale aspetto vorresti concentrarti?")
        ]
        
        print(f"\n[Conversazione Avanzata - {context['time_of_day']} {context['current_time']}]")
        for user_msg, allma_msg in conversations:
            print(f"\n{user_msg}")
            print(f"{allma_msg}")
            self.integration.process_interaction(user_msg, context)
            self.integration.process_interaction(allma_msg, context)

    def simulate_day(self, day):
        """Simula un intero giorno di interazioni"""
        print(f"\n{'='*50}")
        print(f" Giorno {day} - {self.start_date.strftime('%Y-%m-%d')}")
        print(f"{'='*50}")
        
        # Mattina (2-3 interazioni)
        morning_hours = random.sample(range(8, 12), 2)
        for hour in morning_hours:
            print(f"\n>> Sessione delle {hour}:00")
            self.simulate_basic_conversation(hour)
        
        # Pomeriggio (2-3 interazioni più complesse)
        afternoon_hours = random.sample(range(13, 17), 2)
        for hour in afternoon_hours:
            print(f"\n>> Sessione delle {hour}:00")
            self.simulate_intermediate_conversation(hour)
        
        # Sera (1-2 interazioni avanzate)
        evening_hours = random.sample(range(18, 22), 2)
        for hour in evening_hours:
            print(f"\n>> Sessione delle {hour}:00")
            self.simulate_advanced_conversation(hour)
        
        # Analisi giornaliera
        print("\nStatistiche Giornaliere:")
        print(f"- Interazioni: {self.integration.daily_stats['interaction_count']}")
        print(f"- Topics: {list(self.integration.daily_stats['topics_discussed'])}")
        print(f"- Attività: {list(self.integration.user_preferences['common_activities'])}")
        
        self.start_date += timedelta(days=1)

    def print_stats(self, title):
        """Stampa le statistiche in modo formattato"""
        print(f"\n{'='*50}")
        print(f" {title}")
        print(f"{'='*50}")
        
        print("\nPreferenze Utente:")
        print("- Morning Routine:", self.integration.user_preferences['morning_routine'])
        print("- Topics Preferiti:", list(self.integration.user_preferences['favorite_topics']))
        print("- Attività Comuni:", list(self.integration.user_preferences['common_activities']))
        print("- Pattern Emotivi per Ora:", {
            hour: len(patterns) 
            for hour, patterns in self.integration.user_preferences['emotional_patterns'].items()
        })
        
        print("\nStatistiche di Apprendimento:")
        print("- Interazioni Totali:", self.integration.daily_stats['interaction_count'])
        print("- Topics Discussi:", list(self.integration.daily_stats['topics_discussed']))
        print("- Attività Menzionate:", list(self.integration.daily_stats['activities_mentioned']))

    def run_beta(self):
        """Esegue il beta test completo"""
        print("\n🤖 Iniziando Beta Test di ALLMA - 30 giorni")
        print("Simulazione di interazioni quotidiane intensive\n")
        
        for day in range(1, self.total_days + 1):
            self.simulate_day(day)
            
            # Ogni 7 giorni, mostra statistiche settimanali
            if day % 7 == 0:
                self.print_stats(f"Analisi Settimanale - Settimana {day // 7}")
        
        # Statistiche finali
        self.print_stats("Risultati Beta Test - 30 Giorni")

if __name__ == "__main__":
    beta = BetaTest()
    beta.run_beta()
