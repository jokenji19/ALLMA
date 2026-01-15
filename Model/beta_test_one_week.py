"""
Test di integrazione per una settimana di interazione con ALLMA.
Simula una settimana intera con pattern diversi per ogni giorno.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
import unittest
import random

from core.personalization_integration import PersonalizationIntegration
from core.advanced_memory_system import AdvancedMemorySystem
from incremental_learning.emotional_system import EmotionalSystem
from incremental_learning.cognitive_foundations import CognitiveProcessor

class OneWeekIntegrationTest(unittest.TestCase):
    def setUp(self):
        """Inizializza i sistemi per il test"""
        self.allma = PersonalizationIntegration()
        self.simulated_start_time = datetime.now().replace(
            hour=0, minute=0, second=0
        ) - timedelta(days=datetime.now().weekday())  # Inizia da lunedì
        
        # Pattern giornalieri (interazioni per ora)
        self.daily_patterns = {
            "monday": {"morning": 15, "afternoon": 20, "evening": 10, "night": 5},    # Giorno lavorativo intenso
            "tuesday": {"morning": 15, "afternoon": 20, "evening": 10, "night": 5},   # Giorno lavorativo intenso
            "wednesday": {"morning": 12, "afternoon": 15, "evening": 8, "night": 5},  # Giorno medio
            "thursday": {"morning": 15, "afternoon": 20, "evening": 10, "night": 5},  # Giorno lavorativo intenso
            "friday": {"morning": 12, "afternoon": 15, "evening": 12, "night": 8},    # Serata sociale
            "saturday": {"morning": 8, "afternoon": 12, "evening": 15, "night": 10},  # Weekend attivo
            "sunday": {"morning": 5, "afternoon": 10, "evening": 8, "night": 5}       # Giorno di riposo
        }
        
        # Scenari specifici per ogni giorno
        self.weekly_scenarios = {
            "monday": [
                {
                    "type": "planning",
                    "input": "Pianifichiamo gli obiettivi della settimana",
                    "verify": "week_planning"
                },
                {
                    "type": "work",
                    "input": "Iniziamo con il primo progetto della settimana",
                    "verify": "work_focus"
                }
            ],
            "tuesday": [
                {
                    "type": "learning",
                    "input": "Studiamo qualcosa di nuovo oggi",
                    "verify": "learning_progress"
                },
                {
                    "type": "work",
                    "input": "Continuiamo con il progetto di ieri",
                    "verify": "work_continuity"
                }
            ],
            "wednesday": [
                {
                    "type": "review",
                    "input": "Facciamo il punto della situazione a metà settimana",
                    "verify": "mid_week_review"
                },
                {
                    "type": "emotional",
                    "input": "Come sta procedendo la settimana?",
                    "verify": "emotional_check"
                }
            ],
            "thursday": [
                {
                    "type": "work",
                    "input": "Cerchiamo di completare i task principali",
                    "verify": "task_completion"
                },
                {
                    "type": "learning",
                    "input": "Approfondiamo un argomento interessante",
                    "verify": "deep_learning"
                }
            ],
            "friday": [
                {
                    "type": "review",
                    "input": "Rivediamo i risultati della settimana",
                    "verify": "week_review"
                },
                {
                    "type": "social",
                    "input": "Parliamo di piani per il weekend",
                    "verify": "social_planning"
                }
            ],
            "saturday": [
                {
                    "type": "leisure",
                    "input": "Che attività rilassante facciamo oggi?",
                    "verify": "leisure_activity"
                },
                {
                    "type": "creative",
                    "input": "Esploriamo qualche idea creativa",
                    "verify": "creative_exploration"
                }
            ],
            "sunday": [
                {
                    "type": "reflection",
                    "input": "Riflettiamo sulla settimana passata",
                    "verify": "week_reflection"
                },
                {
                    "type": "planning",
                    "input": "Prepariamoci per la prossima settimana",
                    "verify": "next_week_prep"
                }
            ]
        }
        
        # Metriche settimanali
        self.metrics = {
            "daily_interactions": {str(i): 0 for i in range(7)},  # 0=Lunedì
            "daily_response_times": {str(i): [] for i in range(7)},
            "activity_types": {
                "work": 0,
                "learning": 0,
                "social": 0,
                "leisure": 0,
                "planning": 0,
                "review": 0,
                "emotional": 0,
                "creative": 0,
                "reflection": 0
            },
            "memory_stats": {
                "short_term_recalls": 0,
                "long_term_recalls": 0,
                "new_memories": 0
            },
            "emotional_stats": {
                "positive_emotions": 0,
                "negative_emotions": 0,
                "neutral_emotions": 0
            }
        }

    def _get_day_name(self, day_index: int) -> str:
        """Converte l'indice del giorno nel nome"""
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        return days[day_index]

    def _get_time_period(self, hour: int) -> str:
        """Determina il periodo del giorno"""
        if 0 <= hour < 6:
            return "night"
        elif 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        else:
            return "evening"

    def test_one_week_interaction(self):
        """Simula una settimana di interazione"""
        print("\nInizio simulazione test di una settimana...")
        
        for day in range(7):
            day_name = self._get_day_name(day)
            print(f"\n=== {day_name.upper()} ===")
            
            # Simula ogni ora del giorno
            for hour in range(24):
                period = self._get_time_period(hour)
                interactions_this_hour = self.daily_patterns[day_name][period]
                
                print(f"\nOra {hour:02d}:00 - Periodo: {period}")
                
                for i in range(interactions_this_hour):
                    # Calcola il tempo simulato
                    simulated_time = self.simulated_start_time + timedelta(days=day, hours=hour, minutes=random.randint(0, 59))
                    
                    # Seleziona uno scenario appropriato
                    scenario = random.choice(self.weekly_scenarios[day_name])
                    
                    # Registra il tempo di inizio
                    start_time = time.time()
                    
                    # Processa l'input
                    response = self.allma.process_interaction(
                        scenario["input"],
                        context={
                            "test_type": scenario["type"],
                            "simulated_time": simulated_time,
                            "day": day_name,
                            "period": period
                        }
                    )
                    
                    # Registra il tempo di risposta
                    response_time = time.time() - start_time
                    self.metrics["daily_response_times"][str(day)].append(response_time)
                    
                    # Aggiorna le metriche
                    self._update_metrics(scenario, response, day)
                    
                # Analisi oraria
                self._analyze_hourly_results(day, hour, interactions_this_hour)
            
            # Analisi giornaliera
            self._analyze_daily_results(day)
        
        # Analisi settimanale finale
        self._analyze_weekly_results()

    def _update_metrics(self, scenario: Dict[str, Any], response: Dict[str, Any], day: int):
        """Aggiorna le metriche del test"""
        # Incrementa contatore interazioni giornaliere
        self.metrics["daily_interactions"][str(day)] += 1
        
        # Aggiorna contatori per tipo di attività
        self.metrics["activity_types"][scenario["type"]] += 1
        
        # Analizza la risposta per memoria ed emozioni
        if "memory" in response:
            if "short_term" in response["memory"]:
                self.metrics["memory_stats"]["short_term_recalls"] += 1
            if "long_term" in response["memory"]:
                self.metrics["memory_stats"]["long_term_recalls"] += 1
            
        if "understanding" in response and "emotion" in response["understanding"]:
            emotion = response["understanding"]["emotion"]
            if emotion["valence"] > 0.6:
                self.metrics["emotional_stats"]["positive_emotions"] += 1
            elif emotion["valence"] < 0.4:
                self.metrics["emotional_stats"]["negative_emotions"] += 1
            else:
                self.metrics["emotional_stats"]["neutral_emotions"] += 1

    def _analyze_hourly_results(self, day: int, hour: int, interactions: int):
        """Analizza i risultati dell'ora"""
        print(f"Interazioni nell'ora: {interactions}")

    def _analyze_daily_results(self, day: int):
        """Analizza i risultati del giorno"""
        day_name = self._get_day_name(day)
        total_interactions = self.metrics["daily_interactions"][str(day)]
        avg_response_time = sum(self.metrics["daily_response_times"][str(day)]) / len(self.metrics["daily_response_times"][str(day)])
        
        print(f"\nRiepilogo {day_name.upper()}:")
        print(f"Totale interazioni: {total_interactions}")
        print(f"Tempo medio di risposta: {avg_response_time:.3f}s")

    def _analyze_weekly_results(self):
        """Analizza e stampa i risultati finali della settimana"""
        print("\n=== RISULTATI SETTIMANALI ===")
        
        # Statistiche generali
        total_interactions = sum(self.metrics["daily_interactions"].values())
        avg_daily_interactions = total_interactions / 7
        
        print(f"Totale interazioni: {total_interactions}")
        print(f"Media interazioni giornaliere: {avg_daily_interactions:.1f}")
        
        # Statistiche per tipo di attività
        print("\nDistribuzione attività:")
        for activity, count in self.metrics["activity_types"].items():
            percentage = (count / total_interactions) * 100
            print(f"{activity}: {count} ({percentage:.1f}%)")
        
        # Statistiche memoria
        print("\nStatistiche memoria:")
        print(f"Richiami memoria breve termine: {self.metrics['memory_stats']['short_term_recalls']}")
        print(f"Richiami memoria lungo termine: {self.metrics['memory_stats']['long_term_recalls']}")
        
        # Statistiche emotive
        print("\nStatistiche emotive:")
        total_emotions = sum(self.metrics["emotional_stats"].values())
        for emotion, count in self.metrics["emotional_stats"].items():
            percentage = (count / total_emotions) * 100 if total_emotions > 0 else 0
            print(f"{emotion}: {count} ({percentage:.1f}%)")
        
        # Verifiche finali
        self.assertGreater(total_interactions, 500, "Numero totale di interazioni troppo basso")
        self.assertGreater(self.metrics["memory_stats"]["short_term_recalls"], 0, "Nessun richiamo memoria a breve termine")
        self.assertGreater(self.metrics["memory_stats"]["long_term_recalls"], 0, "Nessun richiamo memoria a lungo termine")
        
        # Verifica bilanciamento attività
        for activity, count in self.metrics["activity_types"].items():
            self.assertGreater(count, 0, f"Nessuna attività di tipo {activity}")

if __name__ == "__main__":
    unittest.main()
