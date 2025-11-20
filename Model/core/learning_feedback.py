"""
Gestisce il feedback e l'apprendimento incrementale di ALLMA
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum, auto
import time

class FeedbackType(str, Enum):
    """Tipi di feedback per l'apprendimento"""
    CREATE = 'create'        # Creazione di un nuovo concetto
    UPDATE = 'update'        # Aggiornamento di un concetto esistente
    VALIDATION = 'validate'  # Verifica positiva di un concetto
    ERROR = 'error'         # Errore o verifica negativa
    EXPANSION = 'expand'    # Espansione della conoscenza
    REINFORCEMENT = 'reinforce' # Rinforzo della conoscenza esistente
    CORRECTION = 'correct'   # Correzione di un concetto errato
    CONFUSION = 'confuse'   # Confusione nell'applicazione del concetto

@dataclass
class Feedback:
    """Rappresenta un feedback da un utente"""
    type: FeedbackType
    content: str
    source: str
    timestamp: float
    context: Dict
    confidence_impact: float  # Impatto sulla confidenza (-1.0 a 1.0)

class LearningManager:
    """Gestisce l'apprendimento incrementale basato sul feedback"""
    
    def __init__(self):
        self.feedback_history = []
        self.learning_rate = 0.2  # Tasso base di apprendimento
        self.confidence_threshold = 0.7  # Soglia per considerare un concetto ben appreso
        
    def process_feedback(self, feedback: Feedback, knowledge_node: Dict) -> Tuple[str, float]:
        """Processa il feedback e aggiorna la conoscenza"""
        
        # Calcola l'impatto sulla confidenza
        confidence_delta = self._calculate_confidence_impact(feedback, knowledge_node)
        
        # Genera una descrizione aggiornata basata sul feedback
        updated_description = self._update_description(
            feedback, 
            knowledge_node['description']
        )
        
        # Aggiorna la storia del feedback
        self.feedback_history.append({
            'timestamp': feedback.timestamp,
            'type': feedback.type.value,
            'source': feedback.source,
            'confidence_delta': confidence_delta,
            'context': feedback.context
        })
        
        return updated_description, confidence_delta
        
    def _calculate_confidence_impact(self, feedback: Feedback, 
                                   knowledge_node: Dict) -> float:
        """Calcola l'impatto del feedback sulla confidenza"""
        base_impact = feedback.confidence_impact
        
        # Fattori che influenzano l'impatto
        time_factor = self._calculate_time_factor(knowledge_node['age'])
        source_factor = self._calculate_source_reliability(feedback.source)
        context_factor = self._calculate_context_relevance(feedback.context)
        
        # Calcola l'impatto finale con boost per feedback positivo
        impact = base_impact * self.learning_rate * time_factor * source_factor * context_factor
        if base_impact > 0:  # Per feedback positivo
            impact *= 1.15  # Aumenta del 15% l'impatto positivo
        
        # Limita l'impatto in base alla confidenza attuale
        current_confidence = knowledge_node['confidence']
        if impact > 0:
            # Per feedback positivo, diminuisce l'impatto se la confidenza è già alta
            max_increase = self.confidence_threshold - current_confidence
            impact = min(impact * 1.1, max_increase)  # Aumenta del 10% il limite massimo
        else:
            # Per feedback negativo, mantiene sempre un minimo di confidenza
            min_confidence = 0.1
            impact = max(impact, min_confidence - current_confidence)
            
        return impact
        
    def _calculate_time_factor(self, concept_age: float) -> float:
        """Calcola il fattore tempo per l'apprendimento"""
        # Concetti più recenti sono più plastici
        hour = 3600  # secondi in un'ora
        if concept_age < hour:
            return 1.7  # Boost aumentato per concetti molto recenti
        elif concept_age < 24 * hour:
            return 1.4  # Boost moderato aumentato per concetti recenti
        else:
            return 1.2  # Leggero boost aumentato per concetti più vecchi
            
    def _calculate_source_reliability(self, source: str) -> float:
        """Calcola l'affidabilità della fonte del feedback"""
        # Implementazione base - potrebbe essere estesa con una vera valutazione
        expert_sources = {'Erik', 'Luca'}  # Fonti considerate esperte
        if source in expert_sources:
            return 1.3  # Maggior peso per feedback da esperti
        return 1.0
        
    def _calculate_context_relevance(self, context: Dict) -> float:
        """Calcola la rilevanza del contesto per il feedback"""
        # Analizza il contesto per determinare quanto è rilevante
        if context.get('type') == 'correction':
            return 1.5  # Correzioni hanno più peso
        elif context.get('type') == 'expansion':
            return 1.2  # Espansioni hanno peso moderato
        return 1.0
        
    def _update_description(self, feedback: Feedback, current_description: str) -> str:
        """Aggiorna la descrizione basata sul feedback"""
        if feedback.type == FeedbackType.CREATE:
            # Crea una nuova descrizione
            return feedback.content
            
        elif feedback.type == FeedbackType.UPDATE:
            # Aggiorna la descrizione esistente
            return f"{current_description}\n\nAggiornamento:\n{feedback.content}"
            
        elif feedback.type == FeedbackType.VALIDATION:
            # Verifica positiva, non modifica la descrizione
            return current_description
            
        elif feedback.type == FeedbackType.ERROR:
            # Errore o verifica negativa, non modifica la descrizione
            return current_description
            
        elif feedback.type == FeedbackType.EXPANSION:
            # Aggiunge nuove informazioni
            return f"{current_description}\n\nUlteriori dettagli:\n{feedback.content}"
            
        elif feedback.type == FeedbackType.REINFORCEMENT:
            # Rinforzo della conoscenza esistente, non modifica la descrizione
            return current_description
            
        return current_description
        
    def analyze_learning_progress(self) -> Dict:
        """Analizza il progresso dell'apprendimento"""
        if not self.feedback_history:
            return {
                'total_feedback': 0,
                'feedback_distribution': {},
                'average_confidence_impact': 0.0,
                'learning_effectiveness': 0.0
            }
            
        # Analizza la distribuzione del feedback
        feedback_counts = {}
        total_impact = 0.0
        positive_feedback = 0
        
        for feedback in self.feedback_history:
            feedback_type = feedback['type']
            feedback_counts[feedback_type] = feedback_counts.get(feedback_type, 0) + 1
            total_impact += feedback['confidence_delta']
            
            if feedback['confidence_delta'] > 0:
                positive_feedback += 1
                
        total_feedback = len(self.feedback_history)
        
        return {
            'total_feedback': total_feedback,
            'feedback_distribution': feedback_counts,
            'average_confidence_impact': total_impact / total_feedback,
            'learning_effectiveness': positive_feedback / total_feedback
        }
        
    def get_feedback_suggestions(self, knowledge_node: Dict) -> List[str]:
        """Genera suggerimenti per migliorare l'apprendimento"""
        suggestions = []
        
        # Verifica la completezza della conoscenza
        if not knowledge_node.get('examples'):
            suggestions.append("Richiedi esempi pratici per questo concetto")
            
        if not knowledge_node.get('related_concepts'):
            suggestions.append("Esplora le relazioni con altri concetti")
            
        # Verifica la confidenza
        if knowledge_node['confidence'] < self.confidence_threshold:
            if knowledge_node['verification_count'] < 3:
                suggestions.append("Richiedi più verifiche della comprensione")
            else:
                suggestions.append("Cerca feedback da fonti esperte")
                
        return suggestions
