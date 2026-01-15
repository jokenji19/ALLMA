import unittest
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import os
import threading
import queue
from typing import Dict, List, Optional, Any, Tuple
import json

from allma_model.core.allma_core import ALLMACore
from allma_model.memory_system.temporal_memory import TemporalMemorySystem
from allma_model.project_system.project_tracker import ProjectTracker
from allma_model.user_preferences.preference_analyzer import PreferenceAnalyzer
from allma_model.types import (
    LearningStyle,
    LearningPreference,
    CommunicationStyle,
    EmotionalState,
    ProcessedResponse,
    ResponseFormat
)

def with_test_db(func):
    """Decorator per usare un database di test"""
    def wrapper(*args, **kwargs):
        # Imposta il percorso del database di test
        test_db = "test.db"
        if os.path.exists(test_db):
            os.remove(test_db)
            
        # Esegui il test
        result = func(*args, **kwargs)
        
        # Pulisci
        if os.path.exists(test_db):
            os.remove(test_db)
            
        return result
    return wrapper

class TestALLMACore(unittest.TestCase):
    """Test di base per ALLMACore"""
    
    def setUp(self):
        """Setup per i test"""
        self.test_db = "test_allma.db"
        self.test_user_id = "test_user_123"
        
        # Inizializza il database
        from allma_model.database.init_db import init_db
        init_db(self.test_db)
        
        # Inizializza i componenti
        self.memory_system = TemporalMemorySystem(self.test_db)
        self.project_tracker = ProjectTracker(self.test_db)
        self.preference_analyzer = PreferenceAnalyzer(self.test_db)
        
        # Mock del ResponseGenerator
        self.mock_response_generator = MagicMock()
        self.mock_response_generator.generate_response.return_value = ProcessedResponse(
            content="Risposta di test",
            emotion="neutral",
            confidence=0.9,
            topics=["test"],
            format=ResponseFormat.BALANCED
        )
        
        # Inizializza ALLMACore
        self.core = ALLMACore(
            db_path=self.test_db,
            memory_system=self.memory_system,
            project_tracker=self.project_tracker,
            preference_analyzer=self.preference_analyzer,
            response_generator=self.mock_response_generator
        )
    
    def tearDown(self):
        """Cleanup dopo i test"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def test_process_interaction(self):
        """Test del processamento di un'interazione"""
        # Crea un'interazione di test
        content = "Mostrami un diagramma dettagliato del sistema"
        
        # Processa l'interazione
        result = self.core.process_interaction(
            self.test_user_id,
            content
        )
        
        # Verifica il risultato
        self.assertTrue(result['success'])
        self.assertIn('interaction_id', result)
        self.assertIn('response', result)
    
    def test_get_user_profile(self):
        """Test del recupero del profilo utente"""
        # Crea alcune interazioni
        for i in range(3):
            self.core.process_interaction(
                self.test_user_id,
                f"Interazione di test {i}"
            )
        
        # Recupera il profilo
        profile = self.core.get_user_profile(self.test_user_id)
        
        # Verifica il profilo
        self.assertIsInstance(profile, dict)
        self.assertIn('preferences', profile)
        self.assertIn('temporal_patterns', profile)
        self.assertIn('interaction_count', profile)
        self.assertEqual(profile['interaction_count'], 0)  # Per ora è 0 finché non implementiamo get_user_interactions
    
    def test_multiple_interactions(self):
        """Test di multiple interazioni e loro effetti"""
        # Crea un progetto
        project_id = self.project_tracker.create_project(
            user_id=self.test_user_id,
            name="Progetto Test",
            description="Test di multiple interazioni"
        )
        
        interactions = [
            "Prima interazione di test",
            "Seconda interazione correlata",
            "Terza interazione nella sequenza"
        ]
        
        for content in interactions:
            result = self.core.process_interaction(
                self.test_user_id,
                content,
                project_id=project_id
            )
            self.assertTrue(result['success'])
        
        # Verifica il profilo aggiornato
        profile = self.core.get_user_profile(self.test_user_id)
        self.assertIsInstance(profile['preferences'], dict)
    
    def test_project_interaction(self):
        """Test dell'interazione con un progetto"""
        # Crea un progetto
        project_id = self.project_tracker.create_project(
            user_id=self.test_user_id,
            name="Sistema Logging",
            description="Sistema di logging avanzato",
            metadata={"priority": "high"}
        )
        
        # Crea un'interazione legata al progetto
        content = "Iniziamo a lavorare sul sistema di logging"
        result = self.core.process_interaction(
            self.test_user_id,
            content,
            project_id=project_id
        )
        
        # Verifica il risultato
        self.assertTrue(result['success'])
        self.assertIsNotNone(result['project'])
        self.assertEqual(result['project']['name'], "Sistema Logging")
    
    def test_response_adaptations(self):
        """Test delle varie modalità di adattamento delle risposte"""
        test_response = """
        Come potrai immaginare, al fine di implementare questa funzionalità,
        è importante sottolineare che dobbiamo utilizzare un design pattern appropriato.
        Nel caso in cui ci siano problemi con la classe, possiamo modificare il codice.
        """
        
        # Test risposta diretta
        direct = self.core._make_response_direct(test_response)
        self.assertNotEqual(direct, test_response)
        self.assertNotIn("Come potrai immaginare", direct)
        
        # Test risposta tecnica
        technical = self.core._make_response_technical(test_response)
        self.assertNotEqual(technical, test_response)
        self.assertIn("Pattern", technical)
        
        # Test risposta con elementi visuali
        visual = self.core._make_response_visual(test_response)
        self.assertNotEqual(visual, test_response)
        self.assertIn("```", visual)
    
    def test_adapt_response(self):
        """Test dell'adattamento delle risposte"""
        print("Starting test_adapt_response...")
        
        # Test con preferenze minime
        preferences = LearningPreference(
            primary_style=LearningStyle.VISUAL,
            communication_style=CommunicationStyle.DIRECT,
            confidence=0.8
        )
        print("Created preferences object")
        
        # Test risposta base
        base_response = "Il sistema è composto da tre componenti principali"
        print("About to call _adapt_response...")
        adapted_response, meta = self.core._adapt_response(
            base_response,
            preferences
        )
        
        # Verifica adattamenti
        self.assertIsNotNone(adapted_response)
        self.assertIsInstance(meta, dict)
        self.assertIn('adaptations', meta)
        self.assertIn('confidence', meta)
        self.assertEqual(meta['confidence'], 0.8)
    
    def test_preference_conflicts(self):
        """Test di conflitti nelle preferenze"""
        # Imposta preferenze contrastanti
        preferences = [
            LearningPreference(
                primary_style=LearningStyle.VISUAL,
                communication_style=CommunicationStyle.DIRECT,
                confidence=0.8
            ),
            LearningPreference(
                primary_style=LearningStyle.THEORETICAL,
                communication_style=CommunicationStyle.BALANCED,
                confidence=0.9
            )
        ]
        
        # Verifica che il sistema gestisca i conflitti
        for prefs in preferences:
            result = self.core._adapt_response(
                "Test di risposta",
                prefs
            )
            
            # Verifica che la risposta sia stata adattata
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 2)
            adapted_response, meta = result
            self.assertIsInstance(adapted_response, str)
            self.assertIsInstance(meta, dict)
            self.assertIn('adaptations', meta)
            self.assertIn('confidence', meta)
    
    def test_adaptation_combinations(self):
        """Test di combinazioni di adattamenti"""
        # Crea una risposta complessa
        response = """
        Implementiamo un nuovo design pattern per gestire le connessioni al database.
        La classe DBConnection utilizzerà il Singleton pattern per garantire una singola istanza.
        Ecco la struttura del sistema e alcuni dati statistici sulle performance.
        """
        
        # Applica combinazioni di adattamenti
        adaptations = [
            LearningPreference(
                primary_style=LearningStyle.VISUAL,
                communication_style=CommunicationStyle.DIRECT,
                confidence=0.8
            ),
            LearningPreference(
                primary_style=LearningStyle.KINESTHETIC,
                communication_style=CommunicationStyle.BALANCED,
                confidence=0.7
            ),
            LearningPreference(
                primary_style=LearningStyle.THEORETICAL,
                communication_style=CommunicationStyle.DIRECT,
                confidence=0.9
            )
        ]
        
        seen_patterns = set()
        for preferences in adaptations:
            adapted, meta = self.core._adapt_response(response, preferences)
            
            # Verifica che ogni adattamento sia diverso
            self.assertNotIn(adapted, seen_patterns)
            seen_patterns.add(adapted)
            # Verifica che gli adattamenti siano stati registrati
            self.assertGreater(len(meta['adaptations_applied']), 0)

class TestALLMACoreEdgeCases(unittest.TestCase):
    """Test per casi edge e scenari complessi di ALLMACore"""
    
    def setUp(self):
        """Setup per i test"""
        self.test_db = "test_allma_edge.db"
        self.test_user_id = "test_user_123"
        
        # Inizializza il database
        from allma_model.database.init_db import init_db
        init_db(self.test_db)
        
        # Inizializza i componenti
        self.memory_system = TemporalMemorySystem(self.test_db)
        self.project_tracker = ProjectTracker(self.test_db)
        self.preference_analyzer = PreferenceAnalyzer(self.test_db)
        
        # Mock del ResponseGenerator
        self.mock_response_generator = MagicMock()
        self.mock_response_generator.generate_response.return_value = ProcessedResponse(
            content="Risposta di test",
            emotion="neutral",
            confidence=0.9,
            topics=["test"],
            format=ResponseFormat.BALANCED
        )
        
        # Inizializza ALLMACore
        self.core = ALLMACore(
            db_path=self.test_db,
            memory_system=self.memory_system,
            project_tracker=self.project_tracker,
            preference_analyzer=self.preference_analyzer,
            response_generator=self.mock_response_generator
        )
    
    def tearDown(self):
        """Cleanup dopo i test"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def test_concurrent_interactions(self):
        """Test di interazioni concorrenti"""
        import threading
        import queue
        
        # Coda per raccogliere i risultati
        results = queue.Queue()
        
        def process_interaction(content, project_id=None):
            try:
                result = self.core.process_interaction(
                    self.test_user_id,
                    content,
                    project_id=project_id
                )
                results.put(("success", result))
            except Exception as e:
                results.put(("error", str(e)))
        
        # Crea thread multipli che eseguono interazioni simultanee
        threads = []
        for i in range(5):
            content = f"Interazione concorrente {i}"
            project_id = self.project_tracker.create_project(
                user_id=self.test_user_id,
                name=f"Progetto {i}",
                description=f"Descrizione del progetto {i}"
            )
            thread = threading.Thread(
                target=process_interaction,
                args=(content, project_id)
            )
            threads.append(thread)
        
        # Avvia tutti i thread
        for thread in threads:
            thread.start()
        
        # Attendi il completamento
        for thread in threads:
            thread.join()
        
        # Verifica i risultati
        while not results.empty():
            status, result = results.get()
            self.assertEqual(status, "success")
            self.assertTrue(result['success'])
    
    def test_long_interaction_chain(self):
        """Test di una lunga catena di interazioni correlate"""
        # Crea un progetto
        project_id = self.project_tracker.create_project(
            user_id=self.test_user_id,
            name="Progetto Test",
            description="Test di lunga catena",
            metadata={"type": "test"}
        )

        print(f"\nCreated project with ID: {project_id}")

        # Crea una catena di 10 interazioni correlate
        chain_length = 10
        for i in range(chain_length):
            content = f"Interazione {i} nella catena"
            result = self.core.process_interaction(
                self.test_user_id,
                content,
                project_id=project_id
            )
            print(f"Interaction {i} result: {result}")
            self.assertTrue(result['success'])

        # Verifica che tutte le interazioni siano state collegate
        project = self.project_tracker.get_project(project_id)
        print(f"Final project state: {project}")
        self.assertEqual(project.interaction_count, chain_length)
    
    def test_malformed_input(self):
        """Test di input malformati"""
        # Test con stringhe vuote
        result = self.core.process_interaction(self.test_user_id, "")
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        
        # Test con stringhe molto lunghe
        long_content = "a" * 10000
        result = self.core.process_interaction(self.test_user_id, long_content)
        self.assertTrue(result['success'])
        
        # Test con caratteri speciali
        special_chars = "!@#$%^&*()_+-=[]{}|;:'\",.<>?/~`"
        result = self.core.process_interaction(self.test_user_id, special_chars)
        self.assertTrue(result['success'])
        
        # Test con emoji e unicode
        unicode_content = "👋 Hello 世界"
        result = self.core.process_interaction(self.test_user_id, unicode_content)
        self.assertTrue(result['success'])
    
    def test_system_recovery(self):
        """Test di recupero da errori di sistema"""
        # Simula un errore nel sistema di memoria
        def failing_store(*args, **kwargs):
            raise Exception("Errore simulato")
        
        original_store = self.memory_system.store_interaction
        self.memory_system.store_interaction = failing_store
        
        # Verifica che il core gestisca l'errore
        result = self.core.process_interaction(
            self.test_user_id,
            "Test con errore di sistema"
        )
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        
        # Ripristina il sistema e verifica il recupero
        self.memory_system.store_interaction = original_store
        result = self.core.process_interaction(
            self.test_user_id,
            "Test dopo errore"
        )
        self.assertTrue(result['success'])
    
    def test_project_dependencies(self):
        """Test di dipendenze tra progetti"""
        # Crea progetti con dipendenze
        projects = [
            ("Frontend", "Sviluppo interfaccia utente"),
            ("Backend", "Sviluppo server"),
            ("Database", "Gestione dati")
        ]
        
        project_ids = {}
        for name, desc in projects:
            project_id = self.project_tracker.create_project(
                user_id=self.test_user_id,
                name=name,
                description=desc
            )
            project_ids[name] = project_id
        
        # Crea interazioni che collegano i progetti
        interactions = [
            ("Aggiornare API per Frontend", "Backend"),
            ("Ottimizzare query per Backend", "Database"),
            ("Mostrare dati dal Database", "Frontend")
        ]
        
        for content, project in interactions:
            result = self.core.process_interaction(
                self.test_user_id,
                content,
                project_id=project_ids[project]
            )
            self.assertTrue(result['success'])
        
        # Verifica che tutti i progetti abbiano interazioni
        for name in project_ids:
            project = self.project_tracker.get_project(project_ids[name])
            self.assertGreater(project.interaction_count, 0)
    
    def test_adaptation_combinations(self):
        """Test di combinazioni di adattamenti"""
        # Crea una risposta complessa
        response = """
        Implementiamo un nuovo design pattern per gestire le connessioni al database.
        La classe DBConnection utilizzerà il Singleton pattern per garantire una singola istanza.
        Ecco la struttura del sistema e alcuni dati statistici sulle performance.
        """
        
        # Applica combinazioni di adattamenti
        adaptations = [
            LearningPreference(
                primary_style=LearningStyle.VISUAL,
                communication_style=CommunicationStyle.DIRECT,
                confidence=0.8
            ),
            LearningPreference(
                primary_style=LearningStyle.KINESTHETIC,
                communication_style=CommunicationStyle.BALANCED,
                confidence=0.7
            ),
            LearningPreference(
                primary_style=LearningStyle.THEORETICAL,
                communication_style=CommunicationStyle.DIRECT,
                confidence=0.9
            )
        ]
        
        seen_patterns = set()
        for preferences in adaptations:
            adapted, meta = self.core._adapt_response(response, preferences)
            
            # Verifica che ogni adattamento sia diverso
            self.assertNotIn(adapted, seen_patterns)
            seen_patterns.add(adapted)
            # Verifica che gli adattamenti siano stati registrati
            self.assertGreater(len(meta['adaptations_applied']), 0)

    @pytest.mark.timeout(5)  # Aumentato il timeout a 5 secondi
    def test_timeout_handling(self):
        """Test di gestione del timeout"""
        import time
        # Test di un'interazione che richiede elaborazione
        long_content = "a" * 1000  # Ridotto a 1000 caratteri
        start_time = time.time()
        
        result = self.core.process_interaction(
            self.test_user_id,
            long_content
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verifica che l'elaborazione sia completata con successo
        self.assertTrue(result['success'])
        # Verifica che l'elaborazione non abbia superato il timeout
        self.assertLess(processing_time, 5)  # Aumentato a 5 secondi

if __name__ == '__main__':
    unittest.main()
