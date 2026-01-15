import unittest
from .personality_system import PersonalitySystem
import json
import os

class TestPersonalitySystem(unittest.TestCase):
    def setUp(self):
        self.personality = PersonalitySystem()
        
    def test_initial_traits(self):
        """Verifica che i tratti iniziali siano impostati correttamente"""
        traits = self.personality.traits
        self.assertEqual(len(traits), 7)  # 7 tratti principali
        for trait in traits.values():
            self.assertEqual(trait.value, 0.5)  # Valore iniziale
            self.assertTrue(0 <= trait.flexibility <= 1)  # Flessibilità valida
            
    def test_process_interaction(self):
        """Verifica che le interazioni influenzino la personalità"""
        # Simula un'interazione positiva con apprendimento
        changes = self.personality.process_interaction(
            "Mi piace molto imparare cose nuove e interessanti!",
            {"valence": 0.8, "emotion": "joy", "intensity": 0.8},
            {"success": True}
        )
        
        # Verifica che ci siano stati cambiamenti
        self.assertTrue(any(changes.values()))
        # Verifica che openness sia aumentata
        self.assertTrue(changes.get("openness", 0) > 0)
        
    def test_personality_influence(self):
        """Verifica l'influenza della personalità sui vari sistemi"""
        influence = self.personality.get_personality_influence("emotional")
        self.assertTrue(0 <= influence <= 1)
        
    def test_personality_persistence(self):
        """Verifica il salvataggio e caricamento della personalità"""
        # Modifica alcuni tratti
        self.personality.traits["openness"].value = 0.8
        self.personality.traits["extraversion"].value = 0.3
        
        # Salva lo stato
        test_file = "test_personality_state.json"
        self.personality.save_personality_state(test_file)
        
        # Crea una nuova istanza e carica lo stato
        new_personality = PersonalitySystem()
        new_personality.load_personality_state(test_file)
        
        # Verifica che i tratti siano stati preservati
        self.assertEqual(
            new_personality.traits["openness"].value,
            self.personality.traits["openness"].value
        )
        self.assertEqual(
            new_personality.traits["extraversion"].value,
            self.personality.traits["extraversion"].value
        )
        
        # Pulisci il file di test
        os.remove(test_file)
        
    def test_personality_summary(self):
        """Verifica il sommario della personalità"""
        summary = self.personality.get_personality_summary()
        self.assertEqual(len(summary), 7)  # 7 tratti principali
        for trait_info in summary.values():
            self.assertIn("value", trait_info)
            self.assertIn("description", trait_info)
            
    def test_interaction_influence(self):
        """Verifica il calcolo dell'influenza delle interazioni"""
        influences = self.personality._calculate_interaction_influence(
            "Voglio organizzare meglio il mio tempo per imparare cose nuove",
            {"valence": 0.9},
            {"success": True}
        )
        
        # Verifica che conscientiousness e openness siano influenzate positivamente
        self.assertTrue(influences["conscientiousness"] > 0)
        self.assertTrue(influences["openness"] > 0)

    def test_values_influence(self):
        """Verifica l'influenza dei valori personali"""
        # Modifica un valore personale e la flessibilità del tratto
        self.personality.values["growth"] = 1.0  # Massima importanza alla crescita
        self.personality.traits["openness"].flexibility = 0.5  # Aumenta la flessibilità
        
        # Processa un'interazione legata alla crescita
        changes = self.personality.process_interaction(
            "Voglio imparare e crescere sempre di più",
            {"valence": 0.9, "emotion": "joy", "intensity": 0.8},
            {"success": True}
        )
        
        # Verifica che openness sia aumentata
        self.assertGreater(changes["openness"], 0.05)  # Ridotto il valore atteso
        
    def test_environmental_adaptation(self):
        """Verifica l'adattamento all'ambiente"""
        # Simula un ambiente ad alto stress
        self.personality.adapt_to_environment({
            "complexity": 0.8,
            "social_pressure": 0.9,
            "time_pressure": 0.7
        })
        
        # Verifica che emotional_stability e conscientiousness siano aumentate
        self.assertGreater(
            self.personality.traits["emotional_stability"].value,
            0.5
        )
        self.assertGreater(
            self.personality.traits["conscientiousness"].value,
            0.5
        )
        
    def test_emotional_tendency(self):
        """Verifica il calcolo delle tendenze emotive"""
        # Imposta alcuni tratti a valori specifici
        self.personality.traits["extraversion"].value = 0.8
        self.personality.traits["emotional_stability"].value = 0.3
        
        tendencies = self.personality.get_emotional_tendency()
        
        # Verifica che le tendenze riflettano i tratti
        self.assertGreater(tendencies["emotional_intensity"], 0.5)  # Alta intensità emotiva
        self.assertLess(tendencies["recovery_speed"], 0.5)  # Bassa velocità di recupero
        
    def test_personality_evolution(self):
        """Verifica l'evoluzione della personalità nel tempo"""
        # Simula una serie di interazioni positive
        for _ in range(5):
            self.personality.process_interaction(
                "Questa è un'esperienza molto positiva",
                {"valence": 0.9, "emotion": "joy", "intensity": 0.7},
                {"success": True}
            )
            
        # Verifica che ci sia stata un'evoluzione positiva
        self.assertGreater(self.personality.internal_state["positive_interactions"], 0)
        self.assertGreater(self.personality.internal_state["learning_achievements"], 0)
        
        # Verifica che la storia della personalità sia stata registrata
        self.assertEqual(len(self.personality.personality_history), 5)

if __name__ == '__main__':
    unittest.main()
