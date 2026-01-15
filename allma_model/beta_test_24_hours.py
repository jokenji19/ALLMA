"""
Test di integrazione per 24 ore di interazione con ALLMA.
Simula un giorno intero di interazioni con variazioni basate sull'ora.
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

class TwentyFourHoursIntegrationTest(unittest.TestCase):
    def setUp(self):
        """Inizializza i sistemi per il test"""
        self.allma = PersonalizationIntegration()
        self.simulated_start_time = datetime.now().replace(hour=0, minute=0, second=0)
        
        # Una interazione ogni 5 minuti in media (più frequenti di giorno, meno di notte)
        self.interactions_per_hour = {
            "night": 6,    # Una ogni 10 minuti (00:00-06:00)
            "morning": 20,  # Una ogni 3 minuti (06:00-12:00)
            "afternoon": 15,# Una ogni 4 minuti (12:00-18:00)
            "evening": 12   # Una ogni 5 minuti (18:00-00:00)
        }
        
        # Scenari di test per diverse ore del giorno
        self.time_based_scenarios = {
            "morning": [
                {
                    "type": "routine",
                    "input": "Buongiorno! Come iniziamo questa giornata?",
                    "expected_context": "morning_routine"
                },
                {
                    "type": "planning",
                    "input": "Quali sono i piani per oggi?",
                    "verify": "day_planning"
                }
            ],
            "afternoon": [
                {
                    "type": "activity",
                    "input": "Come procede il lavoro oggi?",
                    "verify": "work_context"
                },
                {
                    "type": "learning",
                    "input": "Studiamo qualcosa di nuovo insieme",
                    "verify": "learning_mode"
                }
            ],
            "evening": [
                {
                    "type": "reflection",
                    "input": "Cosa abbiamo imparato oggi?",
                    "verify": "day_reflection"
                },
                {
                    "type": "emotional",
                    "input": "Come ti senti dopo questa giornata?",
                    "verify": "emotional_state"
                }
            ],
            "night": [
                {
                    "type": "consolidation",
                    "input": "Facciamo un ripasso di oggi prima di riposare",
                    "verify": "memory_consolidation"
                }
            ]
        }
        
        # Metriche di test
        self.metrics = {
            "total_interactions": 0,
            "emotional_responses": 0,
            "memory_recalls": 0,
            "context_switches": 0,
            "response_times": [],
            "hourly_stats": {str(i).zfill(2): {"interactions": 0, "avg_response_time": 0.0} for i in range(24)},
            "routine_completions": 0,
            "learning_sessions": 0,
            "memory_consolidations": 0
        }

    def _get_time_period(self, hour: int) -> str:
        """Determina il periodo del giorno in base all'ora"""
        if 0 <= hour < 6:
            return "night"
        elif 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        else:
            return "evening"

    def _get_scenarios_for_hour(self, hour: int) -> List[Dict]:
        """Restituisce gli scenari appropriati per l'ora del giorno"""
        period = self._get_time_period(hour)
        return self.time_based_scenarios[period]

    def test_24_hours_interaction(self):
        """Simula 24 ore di interazione"""
        print("\nInizio simulazione test di 24 ore...")
        
        for hour in range(24):
            period = self._get_time_period(hour)
            interactions_this_hour = self.interactions_per_hour[period]
            
            print(f"\nOra {hour:02d}:00 - Periodo: {period}")
            
            for i in range(interactions_this_hour):
                # Calcola il tempo simulato
                simulated_time = self.simulated_start_time + timedelta(hours=hour, minutes=random.randint(0, 59))
                
                # Seleziona uno scenario appropriato per l'ora
                scenario = random.choice(self._get_scenarios_for_hour(hour))
                
                # Registra il tempo di inizio
                start_time = time.time()
                
                # Processa l'input
                response = self.allma.process_interaction(
                    scenario["input"],
                    context={
                        "test_type": scenario["type"],
                        "simulated_time": simulated_time,
                        "hour": hour,
                        "period": period
                    }
                )
                
                # Registra il tempo di risposta
                response_time = time.time() - start_time
                self.metrics["response_times"].append(response_time)
                
                # Aggiorna le metriche
                self._update_metrics(scenario, hour, response_time)
                
                # Verifica la risposta
                self._verify_response(scenario, response, hour)
            
            # Analisi oraria
            self._analyze_hourly_results(hour)
        
        # Analisi finale
        self._analyze_final_results()

    def _verify_response(self, scenario: Dict[str, Any], response: Dict[str, Any], hour: int):
        """Verifica la correttezza della risposta"""
        self.assertIn("understanding", response)
        
        if scenario["type"] == "routine":
            self.assertIn("personalization", response)
            self.assertIn("user_preferences", response["personalization"])
            
        elif scenario["type"] == "emotional":
            self.assertIn("emotion", response["understanding"])
            
        elif scenario["type"] == "consolidation":
            self.assertIn("memory", response)
            self.metrics["memory_consolidations"] += 1
            
        elif scenario["type"] == "learning":
            self.assertIn("cognitive_analysis", response["understanding"])

    def _update_metrics(self, scenario: Dict[str, Any], hour: int, response_time: float):
        """Aggiorna le metriche del test"""
        hour_key = str(hour).zfill(2)
        
        self.metrics["total_interactions"] += 1
        self.metrics["hourly_stats"][hour_key]["interactions"] += 1
        self.metrics["hourly_stats"][hour_key]["avg_response_time"] = (
            (self.metrics["hourly_stats"][hour_key]["avg_response_time"] * 
             (self.metrics["hourly_stats"][hour_key]["interactions"] - 1) +
             response_time) / self.metrics["hourly_stats"][hour_key]["interactions"]
        )
        
        if scenario["type"] == "emotional":
            self.metrics["emotional_responses"] += 1
        elif scenario["type"] == "learning":
            self.metrics["learning_sessions"] += 1
        elif scenario["type"] == "routine":
            self.metrics["routine_completions"] += 1

    def _analyze_hourly_results(self, hour: int):
        """Analizza i risultati dell'ora corrente"""
        hour_key = str(hour).zfill(2)
        stats = self.metrics["hourly_stats"][hour_key]
        
        print(f"\nStatistiche ora {hour:02d}:00:")
        print(f"Interazioni: {stats['interactions']}")
        print(f"Tempo medio di risposta: {stats['avg_response_time']:.3f}s")

    def _analyze_final_results(self):
        """Analizza e stampa i risultati finali del test"""
        print("\nRisultati finali del test di 24 ore:")
        print(f"Totale interazioni: {self.metrics['total_interactions']}")
        print(f"Routine completate: {self.metrics['routine_completions']}")
        print(f"Sessioni di apprendimento: {self.metrics['learning_sessions']}")
        print(f"Consolidamenti memoria: {self.metrics['memory_consolidations']}")
        print(f"Risposte emotive: {self.metrics['emotional_responses']}")
        
        avg_response_time = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
        print(f"Tempo medio di risposta globale: {avg_response_time:.3f}s")
        
        # Verifiche finali
        self.assertGreater(self.metrics["total_interactions"], 300)
        self.assertGreater(self.metrics["routine_completions"], 0)
        self.assertGreater(self.metrics["learning_sessions"], 0)
        self.assertGreater(self.metrics["memory_consolidations"], 0)
        self.assertLess(avg_response_time, 2.0, "Tempo medio di risposta troppo alto")

if __name__ == "__main__":
    unittest.main()
