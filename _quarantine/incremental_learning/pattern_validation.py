"""
Sistema di validazione per il pattern recognition
"""

from typing import List, Dict, Any, Optional
import numpy as np
from dataclasses import dataclass
import time

@dataclass
class ValidationResult:
    """Risultato della validazione di un pattern"""
    is_valid: bool
    confidence: float
    error_messages: List[str]
    validation_score: float
    validation_time: float

class PatternValidator:
    """
    Sistema di validazione per i pattern
    Implementa controlli di coerenza e validità
    """
    
    def __init__(self, 
                 min_features_similarity: float = 0.7,
                 min_stability_score: float = 0.5,
                 min_confidence: float = 0.3,
                 max_validation_time: float = 1.0):
        """
        Inizializza il validatore
        
        Args:
            min_features_similarity: Similarità minima tra features
            min_stability_score: Punteggio minimo di stabilità
            min_confidence: Confidenza minima richiesta
            max_validation_time: Tempo massimo per la validazione in secondi
        """
        self.min_features_similarity = min_features_similarity
        self.min_stability_score = min_stability_score
        self.min_confidence = min_confidence
        self.max_validation_time = max_validation_time
        
    def validate_pattern(self, pattern: Any, context: Dict[str, Any]) -> ValidationResult:
        """
        Valida un pattern nel suo contesto
        
        Args:
            pattern: Pattern da validare
            context: Contesto di validazione (altri pattern, configurazione, etc.)
            
        Returns:
            Risultato della validazione
        """
        start_time = time.time()
        errors = []
        
        # Validazione base del pattern
        if not self._validate_pattern_structure(pattern):
            errors.append("Struttura del pattern non valida")
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                error_messages=errors,
                validation_score=0.0,
                validation_time=time.time() - start_time
            )
            
        # Validazione delle features
        if not self._validate_features(pattern.features):
            errors.append("Features non valide")
            
        # Validazione della stabilità
        if pattern.stability_score < self.min_stability_score:
            errors.append(f"Stabilità troppo bassa: {pattern.stability_score:.2f}")
            
        # Validazione della confidenza
        if pattern.confidence < self.min_confidence:
            errors.append(f"Confidenza troppo bassa: {pattern.confidence:.2f}")
            
        # Validazione del contesto
        context_score = self._validate_context(pattern, context)
        if context_score < self.min_features_similarity:
            errors.append(f"Pattern non coerente con il contesto: {context_score:.2f}")
            
        # Calcolo del punteggio finale
        validation_score = self._calculate_validation_score(
            pattern,
            context_score,
            len(errors)
        )
        
        # Controllo del tempo di validazione
        validation_time = time.time() - start_time
        if validation_time > self.max_validation_time:
            errors.append(f"Validazione troppo lenta: {validation_time:.2f}s")
            
        return ValidationResult(
            is_valid=len(errors) == 0,
            confidence=max(0.0, 1.0 - len(errors) * 0.2),
            error_messages=errors,
            validation_score=validation_score,
            validation_time=validation_time
        )
        
    def _validate_pattern_structure(self, pattern: Any) -> bool:
        """
        Valida la struttura base di un pattern
        
        Args:
            pattern: Pattern da validare
            
        Returns:
            True se la struttura è valida
        """
        required_attrs = [
            'features',
            'category',
            'stability_score',
            'confidence',
            'related_patterns'
        ]
        
        return all(hasattr(pattern, attr) for attr in required_attrs)
        
    def _validate_features(self, features: np.ndarray) -> bool:
        """
        Valida le features di un pattern
        
        Args:
            features: Features da validare
            
        Returns:
            True se le features sono valide
        """
        if not isinstance(features, np.ndarray):
            return False
            
        if features.size == 0:
            return False
            
        if not np.isfinite(features).all():
            return False
            
        return True
        
    def _validate_context(self, pattern: Any, context: Dict[str, Any]) -> float:
        """
        Valida un pattern nel suo contesto
        
        Args:
            pattern: Pattern da validare
            context: Contesto di validazione
            
        Returns:
            Punteggio di coerenza con il contesto
        """
        if 'patterns' not in context:
            return 1.0
            
        similarities = []
        for other in context['patterns']:
            if other.category == pattern.category:
                sim = self._calculate_similarity(pattern.features, other.features)
                similarities.append(sim)
                
        return np.mean(similarities) if similarities else 1.0
        
    def _calculate_validation_score(self,
                                  pattern: Any,
                                  context_score: float,
                                  num_errors: int) -> float:
        """
        Calcola il punteggio finale di validazione
        
        Args:
            pattern: Pattern validato
            context_score: Punteggio di coerenza con il contesto
            num_errors: Numero di errori trovati
            
        Returns:
            Punteggio di validazione
        """
        base_score = 1.0
        
        # Penalità per errori
        error_penalty = num_errors * 0.2
        
        # Bonus per stabilità
        stability_bonus = pattern.stability_score * 0.3
        
        # Bonus per confidenza
        confidence_bonus = pattern.confidence * 0.3
        
        # Bonus per coerenza con il contesto
        context_bonus = context_score * 0.4
        
        final_score = (base_score 
                      - error_penalty 
                      + stability_bonus 
                      + confidence_bonus 
                      + context_bonus)
                      
        return max(0.0, min(1.0, final_score))
        
    def _calculate_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """
        Calcola la similarità tra due set di features
        
        Args:
            features1: Primo set di features
            features2: Secondo set di features
            
        Returns:
            Similarità tra le features
        """
        if features1.shape != features2.shape:
            return 0.0
            
        distance = np.linalg.norm(features1 - features2)
        similarity = np.exp(-distance)
        
        return similarity
