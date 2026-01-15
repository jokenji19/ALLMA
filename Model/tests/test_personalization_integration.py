import unittest
from datetime import datetime
from core.personalization_integration import PersonalizationIntegration

class TestPersonalizationIntegration(unittest.TestCase):
    def setUp(self):
        """Inizializza il sistema per ogni test"""
        self.integration = PersonalizationIntegration()
        
    def test_process_interaction_with_cognitive(self):
        """Testa che il sistema processi correttamente un'interazione usando il processore cognitivo"""
        # Input di test
        test_input = "Mi sento molto felice oggi perché ho imparato qualcosa di nuovo"
        test_context = {
            'time_of_day': 'morning',
            'current_time': '09:00'
        }
        
        # Processa l'interazione
        result = self.integration.process_interaction(test_input, test_context)
        
        # Verifica che il risultato contenga i campi attesi
        self.assertIn('understanding', result)
        self.assertIn('cognitive_analysis', result['understanding'])
        
        # Verifica che il processore cognitivo abbia analizzato l'input
        cognitive_result = result['understanding']['cognitive_analysis']
        self.assertIn('understanding_level', cognitive_result)
        self.assertIn('concepts', cognitive_result)
        
        # Verifica che il sistema abbia identificato concetti nell'input
        self.assertTrue(len(cognitive_result['concepts']) > 0)
        
    def test_emotional_memory_integration(self):
        """Testa l'integrazione con il sistema di memoria emotiva"""
        # Input di test con contenuto emotivo
        test_input = "Sono entusiasta di questo nuovo progetto!"
        test_context = {
            'time_of_day': 'morning',
            'current_time': '10:00'
        }
        
        # Processa l'interazione
        result = self.integration.process_interaction(test_input, test_context)
        
        # Verifica che il sistema abbia registrato l'emozione
        self.assertIn('memory', result)
        self.assertIsNotNone(result['memory']['memory_node_id'])
        
    def test_user_preferences_update(self):
        """Testa l'aggiornamento delle preferenze utente"""
        # Input di test con attività e topic
        test_input = "Mi piace programmare al mattino mentre bevo il caffè"
        test_context = {
            'time_of_day': 'morning',
            'current_time': '08:00'
        }
        
        # Processa l'interazione
        self.integration.process_interaction(test_input, test_context)
        
        # Verifica che le preferenze siano state aggiornate
        self.assertTrue(len(self.integration.user_preferences['morning_routine']) > 0)
        self.assertTrue(len(self.integration.user_preferences['favorite_topics']) > 0)

    def test_relationship_level_calculation(self):
        """Testa il calcolo del livello della relazione"""
        # Simula alcune interazioni
        interactions = [
            {
                'input': 'Mi fido di te, vorrei un consiglio su un problema personale',
                'context': {'mood': 'positive'},
                'day': '2025-01-20'
            },
            {
                'input': 'Grazie per avermi aiutato, mi sento meglio',
                'context': {'mood': 'positive'},
                'day': '2025-01-21'
            }
        ]
        self.integration.interaction_history = interactions
        
        # Calcola il livello della relazione
        relationship = self.integration._calculate_relationship_level()
        
        # Verifica i campi attesi
        self.assertIn('level', relationship)
        self.assertIn('progress', relationship)
        self.assertIn('next_milestone', relationship)
        self.assertIn('total_score', relationship)
        
        # Verifica che il progresso sia un valore tra 0 e 1
        self.assertGreaterEqual(relationship['progress'], 0.0)
        self.assertLessEqual(relationship['progress'], 1.0)
        
    def test_conversation_depth_calculation(self):
        """Testa il calcolo della profondità della conversazione"""
        # Simula una conversazione profonda
        deep_interaction = {
            'input': 'Mi preoccupa il futuro e vorrei capire come raggiungere i miei obiettivi. Cosa ne pensi?',
            'context': {'mood': 'concerned'}
        }
        self.integration.interaction_history = [deep_interaction]
        
        # Calcola la profondità
        depth = self.integration._calculate_conversation_depth()
        
        # Verifica che la profondità sia maggiore di 0 per una conversazione profonda
        self.assertGreater(depth, 0.0)
        
        # Simula una conversazione superficiale
        shallow_interaction = {
            'input': 'Che tempo fa oggi?',
            'context': {'mood': 'neutral'}
        }
        self.integration.interaction_history = [shallow_interaction]
        
        # Calcola la profondità
        depth = self.integration._calculate_conversation_depth()
        
        # Verifica che la profondità sia minore per una conversazione superficiale
        self.assertLess(depth, 0.5)
        
    def test_emotional_connection_calculation(self):
        """Testa il calcolo della connessione emotiva"""
        # Simula interazioni con diverse emozioni
        emotional_interactions = [
            {'context': {'mood': 'positive'}},
            {'context': {'mood': 'tired'}},
            {'context': {'mood': 'neutral'}}
        ]
        self.integration.interaction_history = emotional_interactions
        
        # Calcola la connessione emotiva
        connection = self.integration._calculate_emotional_connection()
        
        # Verifica che il punteggio sia tra 0 e 1
        self.assertGreaterEqual(connection, 0.0)
        self.assertLessEqual(connection, 1.0)
        
    def test_trust_indicators_calculation(self):
        """Testa il calcolo degli indicatori di fiducia"""
        # Simula interazioni con indicatori di fiducia
        trust_interactions = [
            {'input': 'Ti confido che ho un problema difficile da risolvere'},
            {'input': 'Grazie per avermi aiutato, apprezzo molto il tuo supporto'}
        ]
        self.integration.interaction_history = trust_interactions
        
        # Calcola gli indicatori di fiducia
        trust = self.integration._calculate_trust_indicators()
        
        # Verifica che il punteggio sia positivo per interazioni con fiducia
        self.assertGreater(trust, 0.0)
        
    def test_communication_style_adaptation(self):
        """Testa l'adattamento dello stile di comunicazione"""
        # Testa diversi livelli di relazione
        levels = ['initial', 'basic_trust', 'friendly', 'established', 'close', 'deep_connection']
        
        for level in levels:
            style = self.integration._adapt_communication_style(level)
            
            # Verifica i campi attesi per ogni stile
            self.assertIn('formality', style)
            self.assertIn('personal_info', style)
            self.assertIn('emotional_expression', style)
            self.assertIn('conversation_depth', style)
            self.assertIn('humor_level', style)
            
    def test_pattern_analysis(self):
        """Testa l'analisi dei pattern nelle interazioni"""
        # Simula alcune interazioni con pattern
        self.integration.user_preferences['interaction_times'] = ['09:00', '09:30', '09:00']
        self.integration.daily_stats['mood_progression'] = ['positive', 'positive', 'tired']
        self.integration.user_preferences['morning_routine'] = ['caffè', 'programmare', 'caffè']
        self.integration.daily_stats['topics_discussed'] = {'programmazione', 'AI'}
        
        # Analizza i pattern
        patterns = self.integration._analyze_patterns()
        
        # Verifica i campi attesi
        self.assertIn('preferred_time', patterns)
        self.assertIn('mood_trend', patterns)
        self.assertIn('routine_consistency', patterns)
        self.assertIn('favorite_activities', patterns)
        self.assertIn('common_topics', patterns)
        
        # Verifica che il tempo preferito sia quello più frequente
        self.assertEqual(patterns['preferred_time'], '09:00')
        
    def test_importance_calculation(self):
        """Testa il calcolo dell'importanza delle memorie"""
        # Test con pattern e stato emotivo
        patterns = ['programming', 'learning']
        emotional_state = {'valence': 0.8}
        confidence = 0.9
        
        importance = self.integration._calculate_importance(patterns, emotional_state, confidence)
        
        # Verifica che l'importanza sia tra 0 e 1
        self.assertGreaterEqual(importance, 0.0)
        self.assertLessEqual(importance, 1.0)
        
        # Test senza pattern
        importance_no_patterns = self.integration._calculate_importance([], emotional_state, confidence)
        
        # Verifica che l'importanza sia minore senza pattern
        self.assertLess(importance_no_patterns, importance)

if __name__ == '__main__':
    unittest.main()
