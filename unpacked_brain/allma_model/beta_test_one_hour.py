"""
Test di integrazione per una conversazione di un'ora con ALLMA.
Simula un'ora di interazione senza attendere realmente quel tempo.
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

class OneHourIntegrationTest(unittest.TestCase):
    def setUp(self):
        """Inizializza i sistemi per il test"""
        self.allma = PersonalizationIntegration()
        self.simulated_start_time = datetime.now()
        self.interactions_count = 120  # Una interazione ogni 30 secondi simulati
        
        # Scenari di test predefiniti
        self.test_scenarios = [
            {
                "type": "emotional",
                "input": "Sono molto felice oggi, mi sento pieno di energia!",
                "expected_emotion": "joy"
            },
            {
                "type": "memory",
                "input": "Ti ricordi cosa ti ho detto all'inizio della conversazione?",
                "verify": "short_term_recall"
            },
            {
                "type": "cognitive",
                "input": "Qual è la tua opinione sul machine learning?",
                "verify": "coherent_response"
            },
            {
                "type": "context_switch",
                "input": "Cambiamo argomento, parliamo di arte",
                "verify": "context_adaptation"
            }
        ]
        
        # Metriche di test
        self.metrics = {
            "emotional_responses": 0,
            "memory_recalls": 0,
            "context_switches": 0,
            "total_interactions": 0,
            "response_times": []
        }

    def test_one_hour_interaction(self):
        """Simula un'ora di interazione"""
        print("\nInizio simulazione test di un'ora...")
        
        for i in range(self.interactions_count):
            # Seleziona uno scenario casuale
            scenario = random.choice(self.test_scenarios)
            
            # Registra il tempo di inizio
            start_time = time.time()
            
            print(f"\nInterazione {i+1}:")
            print(f"Utente: {scenario['input']}")
            
            # Processa l'input
            response = self.allma.process_interaction(
                scenario["input"],
                context={
                    "test_type": scenario["type"],
                    "simulated_time": self.simulated_start_time + timedelta(seconds=30*i)
                }
            )
            
            # Mostra la risposta di ALLMA
            if "understanding" in response and "allma_result" in response["understanding"]:
                print(f"ALLMA: {response['understanding']['allma_result']['response']}")
            else:
                print("ALLMA: ", response)
            
            # Registra il tempo di risposta
            response_time = time.time() - start_time
            self.metrics["response_times"].append(response_time)
            
            # Verifica la risposta
            self._verify_response(scenario, response)
            
            # Aggiorna le metriche
            self.metrics["total_interactions"] += 1
            self._update_metrics(scenario["type"])
            
            # Breve pausa per leggibilità dell'output
            if i < self.interactions_count - 1:
                print("-" * 50)
            
        # Analisi finale
        self._analyze_results()

    def _verify_response(self, scenario: Dict[str, Any], response: Dict[str, Any]):
        """Verifica la correttezza della risposta"""
        if scenario["type"] == "emotional":
            self.assertIn("understanding", response)
            self.assertIn("emotion", response["understanding"])
            if "expected_emotion" in scenario:
                self.assertEqual(
                    response["understanding"]["emotion"]["primary_emotion"],
                    scenario["expected_emotion"]
                )
                
        elif scenario["type"] == "memory":
            self.assertIn("memory", response)
            if scenario["verify"] == "short_term_recall":
                self.assertIn("short_term", response["memory"])
                
        elif scenario["type"] == "cognitive":
            self.assertIn("understanding", response)
            self.assertIn("cognitive_analysis", response["understanding"])
            if scenario["verify"] == "coherent_response":
                self.assertGreater(
                    response["understanding"]["cognitive_analysis"]["understanding_level"],
                    0.0
                )
                
        elif scenario["type"] == "context_switch":
            self.assertIn("understanding", response)
            self.assertIn("allma_result", response["understanding"])
            if scenario["verify"] == "context_adaptation":
                self.assertIn("concepts", response["understanding"]["allma_result"])

    def _update_metrics(self, scenario_type: str):
        """Aggiorna le metriche del test"""
        if scenario_type == "emotional":
            self.metrics["emotional_responses"] += 1
        elif scenario_type == "memory":
            self.metrics["memory_recalls"] += 1
        elif scenario_type == "context_switch":
            self.metrics["context_switches"] += 1

    def _analyze_results(self):
        """Analizza e stampa i risultati del test"""
        print("\nRisultati della simulazione di un'ora:")
        print(f"Totale interazioni: {self.metrics['total_interactions']}")
        print(f"Risposte emotive: {self.metrics['emotional_responses']}")
        print(f"Richiami memoria: {self.metrics['memory_recalls']}")
        print(f"Cambi contesto: {self.metrics['context_switches']}")
        print(f"Tempo medio di risposta: {sum(self.metrics['response_times'])/len(self.metrics['response_times']):.2f}s")
        
        # Verifica finale
        self.assertTrue(self.metrics["total_interactions"] > 0)
        self.assertTrue(self.metrics["emotional_responses"] > 0)
        self.assertTrue(self.metrics["memory_recalls"] > 0)
        self.assertTrue(self.metrics["context_switches"] > 0)
        
        avg_response_time = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
        self.assertLess(avg_response_time, 2.0, "Tempo medio di risposta troppo alto")

if __name__ == "__main__":
    unittest.main()
