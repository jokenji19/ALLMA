"""Test del sistema di adattamento emotivo"""

import unittest
from datetime import datetime
from Model.incremental_learning.emotional_adaptation_system import EmotionalAdaptationSystem, EmotionalState, EmotionalResponse

class TestEmotionalAdaptationSystem(unittest.TestCase):
    """Test suite per il sistema di adattamento emotivo"""
    
    def setUp(self):
        """Setup per i test"""
        self.system = EmotionalAdaptationSystem(
            learning_rate=0.1,
            adaptation_threshold=0.7
        )
        
    def test_process_emotion_new_stimulus(self):
        """Verifica l'elaborazione di un nuovo stimolo emotivo"""
        # Crea uno stato emotivo iniziale
        initial_state = EmotionalState(
            valence=0.8,    # Molto positivo
            arousal=0.7,    # Abbastanza attivato
            dominance=0.4,  # Controllo moderato
            context={"situation": 1.0}
        )
        
        # Processa l'emozione
        response_state = self.system.process_emotion(
            "new_stimulus",
            initial_state,
            {"situation": 1.0}
        )
        
        # Verifica che la risposta sia moderata rispetto allo stato iniziale
        self.assertLess(response_state.valence, initial_state.valence)
        self.assertLess(response_state.arousal, initial_state.arousal)
        self.assertGreater(response_state.dominance, initial_state.dominance)
        
    def test_emotional_adaptation(self):
        """Verifica l'adattamento emotivo nel tempo"""
        stimulus_id = "test_stimulus"
        
        # Stato iniziale
        initial_state = EmotionalState(
            valence=0.9,
            arousal=0.8,
            dominance=0.3,
            context={"situation": 1.0}
        )
        
        # Prima risposta
        response_state1 = self.system.process_emotion(
            stimulus_id,
            initial_state,
            {"situation": 1.0}
        )
        
        # Aggiorna il sistema con un'efficacia alta
        self.system.update_adaptation(
            stimulus_id,
            initial_state,
            response_state1,
            effectiveness=0.9
        )
        
        # Secondo stimolo simile
        similar_state = EmotionalState(
            valence=0.85,
            arousal=0.75,
            dominance=0.35,
            context={"situation": 1.0}
        )
        
        # Seconda risposta
        response_state2 = self.system.process_emotion(
            stimulus_id,
            similar_state,
            {"situation": 1.0}
        )
        
        # Verifica che la seconda risposta sia influenzata dalla prima
        self.assertNotEqual(
            response_state1.valence,
            response_state2.valence,
            "La risposta dovrebbe essere adattata"
        )
        
    def test_context_influence(self):
        """Verifica l'influenza del contesto sull'adattamento"""
        stimulus_id = "context_test"
        
        # Stato con contesto A (situazione molto positiva)
        state_a = EmotionalState(
            valence=0.5,
            arousal=0.5,
            dominance=0.5,
            context={
                "location_home": 1.0,
                "time_morning": 1.0,
                "social_family": 1.0
            }
        )
        
        # Stato con contesto B (situazione stressante)
        state_b = EmotionalState(
            valence=0.5,
            arousal=0.5,
            dominance=0.5,
            context={
                "location_work": 1.0,
                "time_late": 1.0,
                "social_strangers": 1.0
            }
        )
        
        # Processa entrambi gli stati
        response_a = self.system.process_emotion(
            stimulus_id,
            state_a,
            state_a.context
        )
        
        # Aggiorna con alta efficacia per il contesto A
        self.system.update_adaptation(
            stimulus_id,
            state_a,
            response_a,
            effectiveness=0.9
        )
        
        response_b = self.system.process_emotion(
            stimulus_id,
            state_b,
            state_b.context
        )
        
        # Verifica che le risposte siano diverse a causa del contesto
        self.assertNotEqual(
            response_a.valence,
            response_b.valence,
            "Le risposte dovrebbero essere diverse in contesti diversi"
        )
        
        # Verifica che il contesto positivo produca una risposta più positiva
        self.assertGreater(
            response_a.valence,
            response_b.valence,
            "Il contesto positivo dovrebbe produrre una valenza più alta"
        )
        
    def test_adaptation_level(self):
        """Verifica il calcolo del livello di adattamento"""
        # Crea stati per il test
        initial_state = EmotionalState(
            valence=0.0,
            arousal=0.5,
            dominance=0.5,
            context={}
        )
        
        response_state = EmotionalState(
            valence=0.5,
            arousal=0.7,
            dominance=0.6,
            context={}
        )
        
        # Crea una risposta emotiva
        response = EmotionalResponse(
            stimulus_id="test",
            initial_state=initial_state,
            response_state=response_state,
            effectiveness=0.8,
            adaptation_level=0.0  # Sarà calcolato dal sistema
        )
        
        # Calcola il livello di adattamento
        adaptation_level = self.system._compute_adaptation_level(
            initial_state,
            response_state,
            0.8
        )
        
        # Verifica che il livello sia ragionevole
        self.assertGreater(adaptation_level, 0.0)
        self.assertLess(adaptation_level, 1.0)
        
    def test_state_similarity(self):
        """Verifica il calcolo della similarità tra stati emotivi"""
        # Crea due stati simili
        state1 = EmotionalState(
            valence=0.5,
            arousal=0.5,
            dominance=0.5,
            context={"factor": 1.0}
        )
        
        state2 = EmotionalState(
            valence=0.6,
            arousal=0.5,
            dominance=0.5,
            context={"factor": 0.9}
        )
        
        # Calcola la similarità
        similarity = self.system._compute_state_similarity(state1, state2)
        
        # Verifica che stati simili abbiano alta similarità
        self.assertGreater(
            similarity,
            0.8,
            "Stati simili dovrebbero avere alta similarità"
        )
        
        # Crea uno stato molto diverso
        state3 = EmotionalState(
            valence=-0.5,
            arousal=0.1,
            dominance=0.9,
            context={"factor": 0.1}
        )
        
        # Calcola la similarità con lo stato diverso
        similarity = self.system._compute_state_similarity(state1, state3)
        
        # Verifica che stati diversi abbiano bassa similarità
        self.assertLess(
            similarity,
            0.5,
            "Stati diversi dovrebbero avere bassa similarità"
        )

if __name__ == '__main__':
    unittest.main()
