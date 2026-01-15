"""
Sistema di Apprendimento Sociale
Gestisce l'apprendimento dalle interazioni sociali e l'adattamento del comportamento
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
import numpy as np
import numpy.typing as npt
import time

@dataclass
class SocialInteraction:
    """Rappresenta un'interazione sociale"""
    interaction_id: str
    agent_id: str  # ID dell'agente con cui si interagisce
    interaction_type: str  # Tipo di interazione (es. collaborazione, competizione)
    context: Dict[str, float]  # Contesto dell'interazione
    outcome: float  # Successo dell'interazione (-1 a 1)
    timestamp: datetime = field(default_factory=datetime.now)
    feedback: Dict[str, float] = field(default_factory=dict)  # Feedback ricevuto

@dataclass
class SocialBehavior:
    """Rappresenta un comportamento sociale"""
    behavior_id: str
    behavior_type: str  # Tipo di comportamento
    parameters: Dict[str, float]  # Parametri del comportamento
    success_rate: float = 0.0  # Tasso di successo (0 a 1)
    usage_count: int = 0
    last_used: datetime = field(default_factory=datetime.now)

@dataclass
class SocialFeedback:
    """Rappresenta il feedback sociale per un pattern"""
    acceptance_score: float
    consensus_level: float
    timestamp: float
    pattern_id: str

@dataclass
class CollectiveKnowledge:
    """Rappresenta la conoscenza collettiva del sistema"""
    patterns: Dict[str, List[Dict[str, float]]]
    categories: Dict[str, float]  # Categoria -> importanza
    interactions: Dict[str, int]  # Pattern ID -> numero di interazioni

@dataclass
class SocialContext:
    """Rappresenta il contesto sociale di un'interazione"""
    formality: float = 0.5  # Livello di formalità (0-1)
    engagement_level: float = 0.5  # Livello di coinvolgimento (0-1)
    social_distance: float = 0.5  # Distanza sociale (0-1)
    context_type: str = 'neutral'  # Tipo di contesto (formal, casual, neutral)
    relationship_type: str = 'neutral'  # Tipo di relazione (professional, personal, neutral)
    context: Dict[str, Any] = field(default_factory=dict)

class SocialLearningSystem:
    """Sistema di apprendimento sociale"""
    
    def __init__(self,
                 learning_rate: float = 0.1,
                 exploration_rate: float = 0.2,
                 memory_size: int = 1000):
        """
        Inizializza il sistema di apprendimento sociale
        
        Args:
            learning_rate: Tasso di apprendimento
            exploration_rate: Tasso di esplorazione di nuovi comportamenti
            memory_size: Dimensione massima della memoria delle interazioni
        """
        self.learning_rate = learning_rate
        self.exploration_rate = exploration_rate
        self.memory_size = memory_size
        
        # Memoria delle interazioni
        self.interactions: List[SocialInteraction] = []
        # Comportamenti conosciuti
        self.behaviors: Dict[str, SocialBehavior] = {}
        # Relazioni con altri agenti
        self.agent_relationships: Dict[str, float] = {}
        # Preferenze comportamentali per contesto
        self.context_preferences: Dict[str, Dict[str, float]] = {}
        
        # Conoscenza collettiva
        self.collective_knowledge = CollectiveKnowledge(
            patterns={},
            categories={},
            interactions={}
        )
        self.feedback_history = []
        self.learning_rate = 0.1
        
        self.interaction_history = []
        self.current_context = {}
        self.formality_level = 0.5
        self.social_distance = 0.5
        self.adaptation_level = 0.5
        
    def observe_interaction(self,
                          agent_id: str,
                          behavior: str,
                          context: Dict[str, float],
                          outcome: float) -> None:
        """
        Osserva un'interazione sociale e impara da essa
        
        Args:
            agent_id: ID dell'agente osservato
            behavior: Comportamento osservato
            context: Contesto dell'interazione
            outcome: Risultato dell'interazione (-1 a 1)
        """
        # Crea una nuova interazione
        interaction = SocialInteraction(
            interaction_id=f"obs_{len(self.interactions)}",
            agent_id=agent_id,
            interaction_type="observation",
            context=context.copy(),
            outcome=outcome
        )
        
        # Aggiorna la memoria delle interazioni
        self._update_interaction_memory(interaction)
        
        # Aggiorna il comportamento se non esiste
        if behavior not in self.behaviors:
            self.behaviors[behavior] = SocialBehavior(
                behavior_id=behavior,
                behavior_type="observed",
                parameters={}
            )
            
        # Aggiorna le statistiche del comportamento
        self._update_behavior_stats(behavior, outcome)
        
        # Aggiorna le preferenze contestuali
        self._update_context_preferences(behavior, context, outcome)
        
    def interact(self,
                agent_id: str,
                context: Dict[str, float]) -> Tuple[str, Dict[str, float]]:
        """
        Sceglie e genera un comportamento per un'interazione
        
        Args:
            agent_id: ID dell'agente con cui interagire
            context: Contesto dell'interazione
            
        Returns:
            Tupla (comportamento scelto, parametri)
        """
        # Decide se esplorare nuovi comportamenti
        if np.random.random() < self.exploration_rate:
            return self._explore_behavior(context)
            
        # Altrimenti usa il comportamento più adatto
        return self._select_best_behavior(agent_id, context)
        
    def receive_feedback(self,
                        interaction_id: str,
                        feedback: Dict[str, float]) -> None:
        """
        Riceve feedback su un'interazione
        
        Args:
            interaction_id: ID dell'interazione
            feedback: Feedback ricevuto
        """
        # Trova l'interazione
        for interaction in self.interactions:
            if interaction.interaction_id == interaction_id:
                # Aggiorna il feedback
                interaction.feedback.update(feedback)
                
                # Aggiorna la relazione con l'agente
                if "relationship" in feedback:
                    self._update_relationship(
                        interaction.agent_id,
                        feedback["relationship"]
                    )
                break
                
    def adapt_behavior(self,
                      behavior_id: str,
                      context: Dict[str, float],
                      feedback: Dict[str, float]) -> None:
        """
        Adatta un comportamento in base al feedback
        
        Args:
            behavior_id: ID del comportamento da adattare
            context: Contesto in cui è stato usato
            feedback: Feedback ricevuto
        """
        if behavior_id not in self.behaviors:
            return
            
        behavior = self.behaviors[behavior_id]
        
        # Calcola l'errore medio dal feedback
        error = np.mean(list(feedback.values()))
        
        # Adatta i parametri del comportamento
        for param, value in behavior.parameters.items():
            if param in feedback:
                # Aggiorna il parametro verso il feedback
                behavior.parameters[param] += (
                    self.learning_rate * (feedback[param] - value)
                )
                
        # Aggiorna le preferenze contestuali
        self._update_context_preferences(behavior_id, context, error)
        
    def evaluate_pattern(self, pattern) -> SocialFeedback:
        """Valuta un pattern dal punto di vista sociale"""
        # Estrai la categoria dal pattern
        category = pattern.category if hasattr(pattern, 'category') else 'default'
        
        # Ottieni i pattern della stessa categoria
        category_patterns = self._get_category_patterns(category)
        
        # Se non ci sono pattern precedenti, accetta il pattern
        if not category_patterns:
            feedback = SocialFeedback(
                acceptance_score=1.0,
                consensus_level=0.5,
                timestamp=time.time(),
                pattern_id=pattern.id if hasattr(pattern, 'id') else 'unknown'
            )
            self._update_collective_knowledge(pattern, feedback)
            return feedback
        
        # Calcola l'accettazione basata sulla stabilità e confidenza
        acceptance = (pattern.stability_score + pattern.confidence) / 2
        
        # Calcola il consenso basato sulla categoria
        similarities = []
        for other_pattern in category_patterns:
            similarity = self._calculate_similarity(
                pattern.features,
                other_pattern['features']
            )
            similarities.append(similarity)
        consensus = np.mean(similarities)
        
        # Crea il feedback
        feedback = SocialFeedback(
            acceptance_score=acceptance,
            consensus_level=consensus,
            timestamp=time.time(),
            pattern_id=pattern.id if hasattr(pattern, 'id') else 'unknown'
        )
        
        # Aggiorna la conoscenza collettiva
        self._update_collective_knowledge(pattern, feedback)
        
        return feedback
        
    def get_collective_knowledge(self) -> Dict[str, Any]:
        """Restituisce la conoscenza collettiva del sistema"""
        return {
            'total_patterns': len(self.collective_knowledge.patterns),
            'categories': self.collective_knowledge.categories,
            'interactions': self.collective_knowledge.interactions
        }
        
    def on_pattern_update(self, pattern):
        """Callback per gli aggiornamenti dei pattern"""
        self.evaluate_pattern(pattern)
        
    def _update_interaction_memory(self, interaction: SocialInteraction) -> None:
        """Aggiorna la memoria delle interazioni"""
        # Aggiungi la nuova interazione
        self.interactions.append(interaction)
        
        # Se la memoria supera il limite, mantieni solo le più recenti
        if len(self.interactions) > self.memory_size:
            self.interactions = self.interactions[-self.memory_size:]
            
    def _update_behavior_stats(self, behavior_id: str, outcome: float) -> None:
        """Aggiorna le statistiche di un comportamento"""
        behavior = self.behaviors[behavior_id]
        
        # Aggiorna il conteggio
        behavior.usage_count += 1
        
        # Aggiorna il tasso di successo con media mobile
        behavior.success_rate = (
            (behavior.success_rate * (behavior.usage_count - 1) + 
             max(0, outcome)) / behavior.usage_count
        )
        
        behavior.last_used = datetime.now()
        
    def _update_context_preferences(self,
                                  behavior_id: str,
                                  context: Dict[str, float],
                                  outcome: float) -> None:
        """Aggiorna le preferenze contestuali"""
        # Per ogni feature del contesto
        for feature, value in context.items():
            if feature not in self.context_preferences:
                self.context_preferences[feature] = {}
                
            if behavior_id not in self.context_preferences[feature]:
                self.context_preferences[feature][behavior_id] = 0.0
                
            # Aggiorna la preferenza
            current_pref = self.context_preferences[feature][behavior_id]
            self.context_preferences[feature][behavior_id] = (
                current_pref + self.learning_rate * (outcome - current_pref)
            )
            
    def _update_relationship(self, agent_id: str, feedback: float) -> None:
        """Aggiorna la relazione con un agente"""
        if agent_id not in self.agent_relationships:
            self.agent_relationships[agent_id] = 0.0
            
        current_rel = self.agent_relationships[agent_id]
        self.agent_relationships[agent_id] = (
            current_rel + self.learning_rate * (feedback - current_rel)
        )
        
    def _explore_behavior(self,
                         context: Dict[str, float]) -> Tuple[str, Dict[str, float]]:
        """Esplora un nuovo comportamento"""
        # Seleziona un comportamento casuale come base
        if self.behaviors:
            base_behavior = np.random.choice(list(self.behaviors.values()))
            behavior_id = f"exp_{base_behavior.behavior_id}"
            
            # Modifica leggermente i parametri
            parameters = {
                k: v + np.random.normal(0, 0.1)
                for k, v in base_behavior.parameters.items()
            }
        else:
            # Se non ci sono comportamenti, crea uno base
            behavior_id = "exp_base"
            parameters = {"intensity": 0.5, "duration": 0.5}
            
        return behavior_id, parameters
        
    def _select_best_behavior(self,
                            agent_id: str,
                            context: Dict[str, float]) -> Tuple[str, Dict[str, float]]:
        """Seleziona il comportamento migliore per il contesto"""
        if not self.behaviors:
            return self._explore_behavior(context)
            
        # Calcola i punteggi per ogni comportamento
        scores = {}
        for behavior_id, behavior in self.behaviors.items():
            # Base score from success rate
            score = behavior.success_rate
            
            # Add context preference
            context_score = 0.0
            context_count = 0
            for feature, value in context.items():
                if (feature in self.context_preferences and
                    behavior_id in self.context_preferences[feature]):
                    context_score += (
                        self.context_preferences[feature][behavior_id] * value
                    )
                    context_count += 1
                    
            if context_count > 0:
                score = 0.7 * score + 0.3 * (context_score / context_count)
                
            # Consider relationship with agent
            if agent_id in self.agent_relationships:
                score *= (1 + self.agent_relationships[agent_id])
                
            scores[behavior_id] = score
            
        # Select the best behavior
        best_behavior_id = max(scores.items(), key=lambda x: x[1])[0]
        return best_behavior_id, self.behaviors[best_behavior_id].parameters.copy()

    def _update_collective_knowledge(self, pattern, feedback: SocialFeedback):
        """Aggiorna la conoscenza collettiva con un nuovo pattern"""
        # Aggiorna il dizionario dei pattern
        if pattern.id not in self.collective_knowledge.patterns:
            self.collective_knowledge.patterns[pattern.id] = []
            
        self.collective_knowledge.patterns[pattern.id].append({
            'features': pattern.features,
            'acceptance': feedback.acceptance_score,
            'consensus': feedback.consensus_level,
            'timestamp': feedback.timestamp
        })
        
        # Aggiorna le statistiche della categoria
        if pattern.category not in self.collective_knowledge.categories:
            self.collective_knowledge.categories[pattern.category] = 0.5
            
        # Aggiorna l'importanza della categoria
        category_importance = self.collective_knowledge.categories[pattern.category]
        importance_update = (feedback.acceptance_score - category_importance) * self.learning_rate
        self.collective_knowledge.categories[pattern.category] = np.clip(
            category_importance + importance_update,
            0.0, 1.0
        )
        
        # Aggiorna il contatore delle interazioni
        if pattern.id not in self.collective_knowledge.interactions:
            self.collective_knowledge.interactions[pattern.id] = 0
        self.collective_knowledge.interactions[pattern.id] += 1
        
    def _get_category_patterns(self, category: str) -> List[Dict]:
        """Ottiene i pattern per una categoria"""
        patterns = []
        for pattern_id, pattern_data in self.collective_knowledge.patterns.items():
            if pattern_data and pattern_data[-1].get('category') == category:
                patterns.append(pattern_data[-1])
        return patterns
        
    def _calculate_similarity(self, features1, features2) -> float:
        """Calcola la similarità tra due set di features"""
        return 1.0 - np.mean(np.abs(np.array(features1) - np.array(features2)))

    def analyze_social_context(self, input_text: str, context: Dict[str, Any] = None) -> SocialContext:
        """Analizza il contesto sociale di un'interazione"""
        # Aggiorna il contesto
        if context:
            self.current_context.update(context)
            
        # Analizza la formalità
        formality = self._analyze_formality(input_text)
        
        # Analizza la distanza sociale
        social_distance = self._analyze_social_distance(input_text)
        
        # Aggiorna i livelli medi
        self.formality_level = (self.formality_level * 0.8 + formality * 0.2)
        self.social_distance = (self.social_distance * 0.8 + social_distance * 0.2)
        
        # Crea il contesto sociale
        social_context = SocialContext(
            formality=formality,
            engagement_level=0.5,
            social_distance=social_distance,
            context_type='neutral',
            relationship_type='neutral',
            context=self.current_context.copy()
        )
        
        # Aggiorna la storia delle interazioni
        self.interaction_history.append({
            'input': input_text,
            'context': social_context,
            'timestamp': time.time()
        })
        
        return social_context
        
    def generate_response(self, social_context: Dict[str, Any]) -> str:
        """Genera una risposta basata sul contesto sociale"""
        responses = {
            'formal': [
                "Sarò lieto di aiutarla.",
                "Mi dica pure come posso esserle utile.",
                "Sono a sua disposizione."
            ],
            'casual': [
                "Certo, dimmi pure!",
                "Sono qui per te!",
                "Come posso aiutarti?"
            ],
            'neutral': [
                "Come posso aiutarti?",
                "Sono qui per aiutare.",
                "Dimmi pure."
            ]
        }
        
        # Determina il livello di formalità
        formality = social_context.get('formality', 0.5)
        
        if formality > 0.7:
            style = 'formal'
        elif formality < 0.3:
            style = 'casual'
        else:
            style = 'neutral'
            
        # Seleziona una risposta casuale dallo stile appropriato
        import random
        response = random.choice(responses[style])
        
        return response

    def analyze_context(self, text, context):
        """Analizza il contesto sociale del testo"""
        # Analisi semplificata del contesto sociale
        formality_markers = {
            'formal': ['per favore', 'cortesemente', 'gentilmente', 'vorrei'],
            'informal': ['ehi', 'ciao', 'hey', 'bella']
        }
        
        text = text.lower()
        formality_score = 0.5  # default neutrale
        
        # Calcola il punteggio di formalità
        formal_count = sum(1 for marker in formality_markers['formal'] if marker in text)
        informal_count = sum(1 for marker in formality_markers['informal'] if marker in text)
        
        if formal_count > informal_count:
            formality_score = 0.8
        elif informal_count > formal_count:
            formality_score = 0.2
            
        # Aggiungi il punteggio al contesto
        context['formality'] = formality_score
        
        return context
        
    def update(self, social_context):
        """Aggiorna il sistema in base al contesto sociale"""
        self.adaptation_level += 0.1 if social_context.get('formality', 0.5) > 0.5 else -0.05
        self.adaptation_level = max(0, min(1, self.adaptation_level))
        
    def get_state(self):
        """Restituisce lo stato corrente del sistema"""
        if not self.interaction_history:
            return {
                'adaptation_level': self.adaptation_level,
                'interaction_count': 0,
                'avg_formality': 0.5,
                'avg_social_distance': 0.5
            }
            
        return {
            'adaptation_level': self.adaptation_level,
            'interaction_count': len(self.interaction_history),
            'avg_formality': sum(i['context'].formality for i in self.interaction_history) / len(self.interaction_history),
            'avg_social_distance': sum(i['context'].social_distance for i in self.interaction_history) / len(self.interaction_history)
        }

    def extract_social_triggers(self, text: str) -> List[str]:
        """Estrae i trigger sociali dal testo"""
        # Dizionario dei trigger sociali
        social_triggers = {
            'work_stress': {
                'words': {'deadline', 'pressione', 'carico', 'responsabilità'},
                'weight': 0.8
            },
            'social_anxiety': {
                'words': {'presentazione', 'pubblico', 'gruppo', 'giudizio'},
                'weight': 0.7
            },
            'team_dynamics': {
                'words': {'conflitto', 'collaborazione', 'feedback', 'ruolo'},
                'weight': 0.6
            },
            'personal_growth': {
                'words': {'obiettivo', 'sviluppo', 'miglioramento', 'crescita'},
                'weight': 0.5
            }
        }
        
        # Analizza il testo
        words = text.lower().split()
        triggers = []
        
        # Identifica i trigger presenti
        for trigger, data in social_triggers.items():
            if any(word in data['words'] for word in words):
                triggers.append(trigger)
                
        return triggers

    def _calculate_adaptation_level(self) -> float:
        """Calcola il livello di adattamento del sistema"""
        if not self.interaction_history:
            return 0.5
            
        # Calcola la consistenza delle interazioni
        formality_consistency = self._calculate_consistency([i['context'].formality for i in self.interaction_history])
        distance_consistency = self._calculate_consistency([i['context'].social_distance for i in self.interaction_history])
        
        # Calcola il progresso dell'apprendimento
        learning_progress = min(len(self.interaction_history) / 20, 1.0)
        
        # Combina i fattori
        adaptation = (formality_consistency + distance_consistency + learning_progress) / 3
        
        return min(max(adaptation, 0), 1)
        
    def _calculate_consistency(self, values: List[float]) -> float:
        """Calcola la consistenza di una serie di valori"""
        if len(values) < 2:
            return 0.5
            
        # Calcola la deviazione standard
        import numpy as np
        std = np.std(values)
        
        # Una bassa deviazione standard indica alta consistenza
        consistency = 1 - std
        
        return min(max(consistency, 0), 1)

    def update_social_model(self, input_text, emotional_state):
        """Aggiorna il modello sociale in base all'input e allo stato emotivo"""
        # Analizza il contesto sociale
        social_context = self.analyze_social_context(input_text)
        
        # Aggiorna il livello di adattamento
        self.adaptation_level = min(1.0, self.adaptation_level + 0.05)
        
        # Aggiorna il contesto con lo stato emotivo
        social_context.update({
            'emotional_state': emotional_state,
            'adaptation_level': self.adaptation_level
        })
        
        return social_context
        
    def analyze_social_context(self, text):
        """Analizza il contesto sociale del testo"""
        # Analisi semplificata del contesto sociale
        formality_markers = {
            'formal': ['per favore', 'grazie', 'cortesemente', 'gentilmente'],
            'informal': ['hey', 'ciao', 'ok', 'bello']
        }
        
        text = text.lower()
        
        # Calcola il livello di formalità
        formal_count = sum(1 for word in formality_markers['formal'] if word in text)
        informal_count = sum(1 for word in formality_markers['informal'] if word in text)
        
        formality = 0.8 if formal_count > informal_count else \
                   0.2 if informal_count > formal_count else 0.5
                   
        # Calcola la distanza sociale
        social_distance = 0.8 if formality > 0.6 else \
                         0.2 if formality < 0.4 else 0.5
        
        return {
            'formality': formality,
            'social_distance': social_distance,
            'interaction_type': 'formal' if formality > 0.6 else 'casual'
        }
