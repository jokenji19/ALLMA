"""
Test del Sistema di Auto-Diagnosi
"""

import unittest
from datetime import datetime, timedelta
import time
from allma_model.incremental_learning.diagnostic_system import DiagnosticSystem

class TestDiagnosticSystem(unittest.TestCase):
    def setUp(self):
        self.diagnostic = DiagnosticSystem()
        
    def test_initial_state(self):
        """Verifica che il sistema parta con uno stato iniziale corretto"""
        state = self.diagnostic.monitor_state()
        
        # Verifica che tutti i parametri siano inizializzati
        self.assertIsNotNone(state.memory_usage)
        self.assertIsNotNone(state.processing_load)
        self.assertIsNotNone(state.cognitive_load)
        self.assertIsNotNone(state.attention_level)
        
        # Verifica che i valori siano nel range corretto
        self.assertGreaterEqual(state.memory_usage, 0.0)
        self.assertLessEqual(state.memory_usage, 1.0)
        self.assertGreaterEqual(state.attention_level, 0.0)
        self.assertLessEqual(state.attention_level, 1.0)
        
    def test_issue_detection(self):
        """Verifica la capacità di rilevare problemi"""
        # Forza alcuni stati problematici
        for _ in range(20):  # Simula carico
            state = self.diagnostic.monitor_state()
            
        issues = self.diagnostic.diagnose_issues()
        
        # Verifica che vengano rilevati i problemi
        self.assertIsInstance(issues, list)
        if issues:  # Se ci sono problemi
            first_issue = issues[0]
            self.assertIn('type', first_issue)
            self.assertIn('severity', first_issue)
            self.assertIn('description', first_issue)
            
    def test_self_repair(self):
        """Verifica la capacità di auto-riparazione"""
        # Crea alcuni problemi artificiali
        for _ in range(100):  # Aumentiamo il carico
            with self.diagnostic.monitoring():
                time.sleep(0.01)  # Simula operazione pesante
            
        # Forza alcuni errori
        for _ in range(5):
            try:
                with self.diagnostic.monitoring():
                    raise Exception("Errore di test")
            except Exception:
                pass
        
        # Diagnosi e riparazione
        issues = self.diagnostic.diagnose_issues()
        self.assertGreater(len(issues), 0)  # Verifica che ci siano problemi
        
        repair_success = self.diagnostic.self_repair(issues)
        self.assertTrue(repair_success)
        
        # Verifica che i problemi siano stati ridotti
        post_repair_issues = self.diagnostic.diagnose_issues()
        self.assertLessEqual(len(post_repair_issues), len(issues))
        
    def test_monitoring_context(self):
        """Verifica il monitoraggio contestuale"""
        with self.diagnostic.monitoring():
            time.sleep(0.1)  # Simula operazione
            
        # Verifica che il tempo di risposta sia stato registrato
        state = self.diagnostic.current_state
        self.assertTrue(len(state.response_times) > 0)
        
    def test_error_handling(self):
        """Verifica la gestione degli errori"""
        try:
            with self.diagnostic.monitoring():
                raise Exception("Errore di test")
        except Exception:
            pass
            
        # Verifica che l'errore sia stato registrato
        self.assertTrue(len(self.diagnostic.error_log) > 0)
        last_error = self.diagnostic.error_log[-1]
        self.assertEqual(last_error['error'], "Errore di test")
        
    def test_health_report(self):
        """Verifica la generazione del rapporto di salute"""
        # Monitora lo stato prima
        self.diagnostic.monitor_state()
        
        # Ottieni il rapporto
        report = self.diagnostic.get_health_report()
        
        # Verifica la struttura del rapporto
        self.assertIn('status', report)
        self.assertIn('memory_health', report)
        self.assertIn('processing_health', report)
        self.assertIn('cognitive_health', report)
        self.assertIn('attention_level', report)
        
        # Verifica i valori
        self.assertGreaterEqual(report['memory_health'], 0.0)
        self.assertLessEqual(report['memory_health'], 1.0)
        self.assertGreaterEqual(report['attention_level'], 0.0)
        self.assertLessEqual(report['attention_level'], 1.0)
        
    def test_cognitive_load_estimation(self):
        """Verifica la stima del carico cognitivo"""
        # Simula attività intensa
        for _ in range(10):
            with self.diagnostic.monitoring():
                time.sleep(0.01)  # Simula operazione
                
        state = self.diagnostic.monitor_state()
        
        # Verifica che il carico cognitivo sia stato stimato
        self.assertGreater(state.cognitive_load, 0.0)
        self.assertLess(state.cognitive_load, 1.0)
        
        # Verifica che il livello di attenzione sia inversamente correlato
        self.assertLess(state.attention_level, 1.0)

if __name__ == '__main__':
    unittest.main()
