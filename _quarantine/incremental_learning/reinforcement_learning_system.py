"""
Sistema di Apprendimento per Rinforzo
Simula la capacità del cervello umano di imparare dalle esperienze e dal feedback
"""

from typing import Dict, List, Tuple
import numpy as np
from datetime import datetime

class ReinforcementLearningSystem:
    def __init__(self):
        """
        Inizializza il sistema di apprendimento per rinforzo.
        Come un neonato, parte senza conoscenze ma con la capacità di imparare.
        """
        self.experiences = []  # Lista di esperienze passate
        self.action_values = {}  # Valori stimati delle azioni
        self.learning_rate = 0.1  # Tasso di apprendimento iniziale
        self.exploration_rate = 1.0  # Massima esplorazione iniziale
        self.min_exploration_rate = 0.01
        self.exploration_decay = 0.995
        
    def observe_outcome(self, state: str, action: str, reward: float, new_state: str):
        """
        Osserva il risultato di un'azione, come un bambino che impara dalle conseguenze
        """
        # Memorizza l'esperienza
        experience = {
            'state': state,
            'action': action,
            'reward': reward,
            'new_state': new_state,
            'timestamp': datetime.now()
        }
        self.experiences.append(experience)
        
        # Aggiorna i valori stimati delle azioni
        state_action_key = f"{state}:{action}"
        if state_action_key not in self.action_values:
            self.action_values[state_action_key] = 0.0
            
        # Apprendimento Q-learning semplificato
        current_value = self.action_values[state_action_key]
        self.action_values[state_action_key] = current_value + \
            self.learning_rate * (reward - current_value)
            
        # Adatta il tasso di esplorazione
        self.exploration_rate = max(
            self.min_exploration_rate,
            self.exploration_rate * self.exploration_decay
        )
        
    def choose_action(self, state: str, available_actions: List[str]) -> str:
        """
        Sceglie un'azione bilanciando esplorazione e sfruttamento,
        come un bambino che alterna tra provare cose nuove e ripetere ciò che funziona
        """
        if np.random.random() < self.exploration_rate:
            # Esplora - prova qualcosa di nuovo
            return np.random.choice(available_actions)
        
        # Sfrutta - usa l'esperienza passata
        action_values = []
        for action in available_actions:
            key = f"{state}:{action}"
            value = self.action_values.get(key, 0.0)
            action_values.append(value)
            
        # Sceglie l'azione con il valore più alto
        best_action_idx = np.argmax(action_values)
        return available_actions[best_action_idx]
        
    def reflect_on_experiences(self) -> Dict:
        """
        Riflette sulle esperienze passate per migliorare,
        come un umano che ripensa alla sua giornata
        """
        if not self.experiences:
            return {'insights': 'Nessuna esperienza su cui riflettere'}
            
        # Analizza le esperienze recenti
        recent_experiences = self.experiences[-10:]
        avg_reward = np.mean([exp['reward'] for exp in recent_experiences])
        
        # Identifica pattern di successo
        successful_actions = [
            exp['action'] for exp in recent_experiences 
            if exp['reward'] > avg_reward
        ]
        
        # Identifica aree di miglioramento
        improvement_needed = [
            exp['action'] for exp in recent_experiences 
            if exp['reward'] < avg_reward
        ]
        
        return {
            'avg_reward': avg_reward,
            'successful_actions': successful_actions,
            'improvement_needed': improvement_needed,
            'exploration_rate': self.exploration_rate
        }
        
    def adapt_learning_rate(self):
        """
        Adatta il tasso di apprendimento in base all'esperienza,
        come un umano che diventa più efficiente nell'imparare
        """
        if len(self.experiences) > 10:
            recent_rewards = [exp['reward'] for exp in self.experiences[-10:]]
            reward_variance = np.var(recent_rewards)
            
            # Se la varianza è alta, aumenta il learning rate per adattarsi più velocemente
            # Se è bassa, diminuisci per stabilizzare l'apprendimento
            if reward_variance > 0.5:
                self.learning_rate = min(0.5, self.learning_rate * 1.1)
            else:
                self.learning_rate = max(0.01, self.learning_rate * 0.95)
