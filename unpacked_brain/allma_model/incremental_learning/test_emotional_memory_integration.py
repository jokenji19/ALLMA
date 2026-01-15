import unittest
from datetime import datetime
from allma_model.incremental_learning.emotional_memory_integration import EmotionalMemoryIntegration

class TestEmotionalMemoryIntegration(unittest.TestCase):
    def setUp(self):
        self.integration = EmotionalMemoryIntegration()
        
    def test_process_input(self):
        """Testa l'elaborazione dell'input attraverso entrambi i sistemi"""
        input_text = "Sono molto felice di imparare cose nuove!"
        context = {'is_novel': True}
        
        # Processa l'input
        emotional_state, memories = self.integration.process_input(input_text, context)
        
        # Verifica lo stato emotivo
        self.assertGreater(emotional_state.pleasure, 0.5)
        
        # Verifica che l'esperienza sia stata memorizzata
        self.assertTrue(any(input_text in m.content for m in memories['episodic']))
        
    def test_emotional_memory_influence(self):
        """Testa l'influenza delle memorie sullo stato emotivo"""
        # Prima esperienza positiva
        self.integration.process_input(
            "Ho fatto una bellissima scoperta!",
            {'is_significant': True}
        )
        
        # Seconda esperienza correlata
        emotional_state, memories = self.integration.process_input(
            "Sto facendo nuove scoperte"
        )
        
        # La memoria della prima esperienza dovrebbe influenzare positivamente
        # lo stato emotivo della seconda
        self.assertGreater(emotional_state.pleasure, 0)
        
    def test_response_generation(self):
        """Testa la generazione di risposte"""
        # Memorizza un'esperienza
        self.integration.process_input(
            "I gatti sono animali affettuosi",
            {'is_significant': True}
        )
        
        # Genera una risposta a un input correlato
        response = self.integration.generate_response("Mi piacciono i gatti")
        
        # La risposta dovrebbe contenere riferimenti alla memoria precedente
        self.assertIn("ricorda", response.lower())
        self.assertIn("gatti", response.lower())
        
    def test_context_enrichment(self):
        """Testa l'arricchimento del contesto"""
        input_text = "Sono estremamente entusiasta!"
        context = {'location': 'casa'}
        
        emotional_state, memories = self.integration.process_input(input_text, context)
        
        # Verifica che il contesto sia stato arricchito
        memory = memories['episodic'][0]
        self.assertIn('emotional_state', memory.context)
        self.assertIn('timestamp', memory.context)
        self.assertIn('is_significant', memory.context)
        
    def test_state_persistence(self):
        """Testa il salvataggio e caricamento dello stato integrato"""
        # Crea alcune esperienze
        self.integration.process_input(
            "Oggi è una bellissima giornata!",
            {'is_significant': True}
        )
        self.integration.process_input(
            "Ho imparato molte cose interessanti",
            {'is_novel': True}
        )
        
        # Salva lo stato
        self.integration.save_state("test_integration")
        
        # Crea una nuova istanza e carica lo stato
        new_integration = EmotionalMemoryIntegration()
        new_integration.load_state("test_integration")
        
        # Verifica che lo stato sia stato preservato
        response = new_integration.generate_response("Com'è stata la giornata?")
        self.assertIn("bellissima", response.lower())
        
    def test_emotional_response_adaptation(self):
        """Testa l'adattamento emotivo delle risposte"""
        # Input positivo
        response_positive = self.integration.generate_response(
            "Sono davvero felice oggi!",
            {'is_significant': True}
        )
        
        # La risposta dovrebbe riflettere l'emozione positiva
        self.assertIn("content", response_positive.lower())
        
        # Input negativo
        response_negative = self.integration.generate_response(
            "Mi sento molto triste",
            {'is_significant': True}
        )
        
        # La risposta dovrebbe riflettere l'emozione negativa
        self.assertIn("triste", response_negative.lower())
        
    def test_memory_integration(self):
        """Testa l'integrazione tra memoria episodica e semantica"""
        # Aggiunge conoscenza semantica
        self.integration.process_input(
            "Il gatto è un mammifero domestico",
            {'is_significant': True}
        )
        
        # Aggiunge un'esperienza episodica
        self.integration.process_input(
            "Ho accarezzato un gatto molto affettuoso",
            {'is_novel': True}
        )
        
        # Genera una risposta che dovrebbe integrare entrambi i tipi di memoria
        response = self.integration.generate_response("Parlami dei gatti")
        
        # La risposta dovrebbe contenere sia informazioni semantiche che episodiche
        self.assertTrue(
            ("mammifero" in response.lower() and "accarezzato" in response.lower()) or
            ("domestico" in response.lower() and "affettuoso" in response.lower())
        )

if __name__ == '__main__':
    unittest.main()
