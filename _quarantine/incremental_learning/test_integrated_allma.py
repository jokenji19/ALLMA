"""
Test del sistema ALLMA integrato.
"""

import unittest
from .integrated_allma import IntegratedALLMA

class TestIntegratedALLMA(unittest.TestCase):
    def setUp(self):
        """Inizializza il sistema integrato per i test"""
        self.allma = IntegratedALLMA()
        
    def test_basic_learning_sequence(self):
        """Testa una sequenza di apprendimento base"""
        
        # Primo input semplice
        result1 = self.allma.process_input("Il gatto è sopra il tavolo")
        self.assertIn("concepts", result1)
        self.assertIn("relations", result1)
        self.assertIn("confidence", result1)
        
        # Verifica che il sistema abbia riconosciuto concetti spaziali
        concepts = result1["concepts"]
        self.assertTrue(any("sopra" in str(c) for c in concepts))
        
        # Input con relazione causale
        result2 = self.allma.process_input("Se piove, quindi il gatto entra in casa")
        
        # Verifica la comprensione causale
        relations = result2["relations"]
        self.assertTrue(any("implicazione" in str(r) for r in relations))
        
        # Verifica che il livello di apprendimento sia aumentato
        state = self.allma.get_current_state()
        self.assertTrue(state.learning_level > 0)
        
    def test_emotional_integration(self):
        """Testa l'integrazione con il sistema emotivo"""
        
        # Input con contenuto emotivo
        result = self.allma.process_input("Sono molto felice di vedere il gatto giocare")
        
        # Verifica la presenza di analisi emotiva
        self.assertIn("emotional_context", result)
        emotional = result["emotional_context"]
        self.assertGreater(emotional["valence"], 0)  # Emozione positiva
        
    def test_memory_integration(self):
        """Testa l'integrazione con il sistema di memoria"""
        
        # Prima esperienza
        self.allma.process_input("Il gatto beve il latte")
        
        # Seconda esperienza correlata
        result = self.allma.process_input("Il gatto ha sete")
        
        # Verifica che il sistema abbia fatto connessioni dalla memoria
        self.assertIn("memory_context", result)
        self.assertTrue(len(result["memory_context"]) > 0)
        
    def test_complex_understanding(self):
        """Testa la comprensione di input complessi"""
        
        # Sequenza di input correlati
        inputs = [
            "Quando il sole splende, i fiori sbocciano",
            "I fiori hanno bisogno di acqua per crescere",
            "Se piove, quindi i fiori ricevono acqua"
        ]
        
        results = []
        for input_text in inputs:
            result = self.allma.process_input(input_text)
            results.append(result)
            
        # Verifica che la confidenza aumenti con input correlati
        confidences = [r["confidence"] for r in results]
        self.assertTrue(confidences[-1] > confidences[0])
        
        # Verifica che il sistema abbia creato relazioni tra i concetti
        final_state = self.allma.get_current_state()
        self.assertTrue(len(final_state.cognitive_state["active_relations"]) > 0)
        
    def test_learning_progression(self):
        """Testa la progressione dell'apprendimento"""
        
        # Serie di input di complessità crescente
        inputs = [
            "Il cane corre",  # Semplice
            "Il cane corre perché vede un gatto",  # Causale
            "Se il cane vede un gatto, quindi abbaia e corre, perché vuole giocare"  # Complesso
        ]
        
        learning_levels = []
        for input_text in inputs:
            self.allma.process_input(input_text)
            state = self.allma.get_current_state()
            learning_levels.append(state.learning_level)
            
        # Verifica che il livello di apprendimento sia aumentato
        self.assertTrue(learning_levels[-1] > learning_levels[0])
        
        # Verifica la spiegazione del sistema
        explanation = self.allma.explain_understanding()
        self.assertIsInstance(explanation, str)
        self.assertTrue(len(explanation) > 0)
        
if __name__ == '__main__':
    unittest.main()
