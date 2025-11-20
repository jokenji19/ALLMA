import unittest
from datetime import datetime
import os
from Model.user_preferences.preference_analyzer import (
    PreferenceAnalyzer,
    CommunicationStyle,
    LearningStyle
)

class TestPreferenceAnalyzer(unittest.TestCase):
    def setUp(self):
        """Setup per ogni test"""
        self.test_db = "test_preferences.db"
        self.analyzer = PreferenceAnalyzer(db_path=self.test_db)
        self.test_user_id = "test_user_123"
    
    def tearDown(self):
        """Pulizia dopo ogni test"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def test_analyze_communication_style(self):
        """Test dell'analisi dello stile di comunicazione"""
        # Test stile diretto
        interaction = {
            'content': 'Dammi una breve spiegazione di questo.',
            'context': {}
        }
        preferences = self.analyzer.analyze_interaction(self.test_user_id, interaction)
        self.assertIn('communication_style', preferences)
        self.assertEqual(
            preferences['communication_style']['style'],
            CommunicationStyle.DIRECT.value
        )
        
        # Test stile dettagliato
        interaction = {
            'content': 'Per favore, spiegami dettagliatamente come funziona questo sistema. '
                      'Vorrei capire tutti gli aspetti e i dettagli implementativi, '
                      'inclusi i casi edge e le possibili ottimizzazioni.',
            'context': {}
        }
        preferences = self.analyzer.analyze_interaction(self.test_user_id, interaction)
        self.assertIn('communication_style', preferences)
        self.assertEqual(
            preferences['communication_style']['style'],
            CommunicationStyle.DETAILED.value
        )
        
        # Test stile tecnico
        interaction = {
            'content': 'Quali sono le specifiche tecniche dell\'API? '
                      'Vorrei vedere la documentazione del framework.',
            'context': {}
        }
        preferences = self.analyzer.analyze_interaction(self.test_user_id, interaction)
        self.assertIn('communication_style', preferences)
        self.assertEqual(
            preferences['communication_style']['style'],
            CommunicationStyle.TECHNICAL.value
        )
    
    def test_analyze_learning_style(self):
        """Test dell'analisi dello stile di apprendimento"""
        # Test stile visuale
        interaction = {
            'content': 'Puoi mostrarmi un diagramma di come funziona? '
                      'Preferisco vedere un\'immagine.',
            'context': {}
        }
        preferences = self.analyzer.analyze_interaction(self.test_user_id, interaction)
        self.assertIn('learning_style', preferences)
        self.assertEqual(
            preferences['learning_style']['style'],
            LearningStyle.VISUAL.value
        )
        
        # Test stile pratico/cinestetico
        interaction = {
            'content': 'Fammi un esempio pratico. Come si fa nella pratica? '
                      'Voglio provare a implementarlo.',
            'context': {}
        }
        preferences = self.analyzer.analyze_interaction(self.test_user_id, interaction)
        self.assertIn('learning_style', preferences)
        self.assertEqual(
            preferences['learning_style']['style'],
            LearningStyle.KINESTHETIC.value
        )
        
        # Test stile teorico
        interaction = {
            'content': 'Qual è la teoria dietro questo concetto? '
                      'Spiegami i principi fondamentali.',
            'context': {}
        }
        preferences = self.analyzer.analyze_interaction(self.test_user_id, interaction)
        self.assertIn('learning_style', preferences)
        self.assertEqual(
            preferences['learning_style']['style'],
            LearningStyle.THEORETICAL.value
        )
    
    def test_store_and_retrieve_preferences(self):
        """Test del salvataggio e recupero delle preferenze"""
        # Crea alcune interazioni per generare preferenze
        interactions = [
            {
                'content': 'Dammi una breve spiegazione.',
                'context': {}
            },
            {
                'content': 'Mostrami un diagramma del sistema.',
                'context': {}
            }
        ]
        
        # Analizza le interazioni
        for interaction in interactions:
            self.analyzer.analyze_interaction(self.test_user_id, interaction)
        
        # Recupera le preferenze
        preferences = self.analyzer.get_user_preferences(self.test_user_id)
        
        # Verifica che le preferenze siano state salvate
        self.assertIn('communication_style', preferences)
        self.assertIn('learning_style', preferences)
        
        # Verifica i valori
        self.assertEqual(
            preferences['communication_style']['style'],
            CommunicationStyle.DIRECT.value
        )
        self.assertEqual(
            preferences['learning_style']['style'],
            LearningStyle.VISUAL.value
        )
    
    def test_preference_history(self):
        """Test della storia delle preferenze"""
        # Crea una serie di interazioni nel tempo
        interactions = [
            {
                'content': 'Dammi una breve spiegazione.',
                'context': {}
            },
            {
                'content': 'Spiegami dettagliatamente come funziona.',
                'context': {}
            },
            {
                'content': 'Mostrami la documentazione tecnica.',
                'context': {}
            }
        ]
        
        # Analizza le interazioni
        for interaction in interactions:
            self.analyzer.analyze_interaction(self.test_user_id, interaction)
        
        # Recupera la storia delle preferenze
        history = self.analyzer.get_preference_history(
            self.test_user_id,
            'communication_style'
        )
        
        # Verifica che ci siano entry nella storia
        self.assertGreater(len(history), 0)
        
        # Verifica che le entry abbiano i campi corretti
        for entry in history:
            self.assertIn('value', entry)
            self.assertIn('confidence', entry)
            self.assertIn('timestamp', entry)
    
    def test_confidence_levels(self):
        """Test dei livelli di confidenza"""
        # Test con interazione ambigua
        interaction = {
            'content': 'Ciao, come stai?',
            'context': {}
        }
        preferences = self.analyzer.analyze_interaction(self.test_user_id, interaction)
        
        # Non dovrebbe identificare preferenze con bassa confidenza
        self.assertEqual(len(preferences), 0)
        
        # Test con interazione chiara
        interaction = {
            'content': 'Mostrami un diagramma dettagliato del sistema. '
                      'Preferisco vedere le cose visivamente con immagini '
                      'e grafici che spieghino il funzionamento.',
            'context': {}
        }
        preferences = self.analyzer.analyze_interaction(self.test_user_id, interaction)
        
        # Dovrebbe identificare preferenze con alta confidenza
        self.assertIn('learning_style', preferences)
        self.assertGreaterEqual(preferences['learning_style']['confidence'], 0.5)

if __name__ == '__main__':
    unittest.main()
