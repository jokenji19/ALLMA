from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
import numpy as np
from datetime import datetime

from .curiosity_system import EmotionalCuriosity
from .pattern_recognition_system import PatternRecognitionSystem, Pattern
from .contextual_learning_system import ContextualLearningSystem, Context
from .meta_learning_system import MetaLearningSystem

@dataclass
class LearningResult:
    """Risultato del processo di apprendimento"""
    unknown_concepts: Set[str]
    learned_patterns: List[Pattern]
    context: Context
    confidence: float
    emotional_state: Dict[str, float]
    questions_generated: List[str]

class IntegratedLearningSystem:
    """Sistema integrato per l'apprendimento incrementale che coordina tutti i sottosistemi"""
    
    def __init__(self):
        self.curiosity_system = EmotionalCuriosity()
        self.pattern_recognition = PatternRecognitionSystem()
        self.contextual_learning = ContextualLearningSystem()
        self.meta_learning = MetaLearningSystem()
        
        # Stato interno
        self.current_context: Optional[Context] = None
        self.unknown_concepts: Set[str] = set()
        self.learning_history: List[Dict] = []
        
    def process_input(self, 
                     input_text: str, 
                     context: Dict[str, Any] = None) -> LearningResult:
        """
        Processa un input attraverso tutti i sistemi integrati
        
        Args:
            input_text: Testo da processare
            context: Contesto aggiuntivo (opzionale)
            
        Returns:
            LearningResult con i risultati dell'elaborazione
        """
        # 1. Analisi del contesto
        self.current_context = self.contextual_learning.process_input(
            input_text, 
            context
        )
        
        # 2. Identificazione concetti sconosciuti
        unknown_concepts = self.identify_unknown_concepts(input_text)
        
        # 3. Riconoscimento pattern
        patterns = self.pattern_recognition.analyze_pattern(
            input_text,
            self.current_context.__dict__
        )
        
        # 4. Aggiornamento curiosità
        self.curiosity_system.update(unknown_concepts, patterns)
        
        # 5. Generazione domande per l'apprendimento
        questions = self.generate_learning_questions(unknown_concepts)
        
        # 6. Meta-learning per ottimizzazione
        self.meta_learning.update_learning_strategy(
            unknown_concepts=unknown_concepts,
            patterns_found=patterns,
            context=self.current_context,
            emotional_state=self.curiosity_system.__dict__
        )
        
        # 7. Preparazione risultato
        result = LearningResult(
            unknown_concepts=unknown_concepts,
            learned_patterns=patterns,
            context=self.current_context,
            confidence=self.calculate_confidence(patterns),
            emotional_state=self.curiosity_system.__dict__,
            questions_generated=questions
        )
        
        # 8. Aggiornamento storia apprendimento
        self.update_learning_history(result)
        
        return result
    
    def identify_unknown_concepts(self, text: str) -> Set[str]:
        """Identifica concetti sconosciuti nel testo"""
        # Usa il sistema di curiosità per identificare concetti sconosciuti
        concepts = set()
        # TODO: Implementare logica di identificazione concetti
        return concepts
    
    def generate_learning_questions(self, unknown_concepts: Set[str]) -> List[str]:
        """Genera domande per approfondire i concetti sconosciuti"""
        questions = []
        for concept in unknown_concepts:
            # Genera domande basate sul contesto e sul concetto
            context_info = self.current_context.__dict__ if self.current_context else {}
            question = self.meta_learning.generate_question(concept, context_info)
            questions.append(question)
        return questions
    
    def learn_from_explanation(self, 
                             concept: str, 
                             explanation: str) -> bool:
        """
        Apprende da una spiegazione fornita
        
        Args:
            concept: Concetto da apprendere
            explanation: Spiegazione fornita
            
        Returns:
            True se l'apprendimento è avvenuto con successo
        """
        # 1. Analisi del pattern nella spiegazione
        pattern = self.pattern_recognition.analyze_pattern(
            explanation,
            {"concept": concept}
        )
        
        # 2. Aggiornamento contesto
        self.contextual_learning.learn(
            explanation,
            {
                "topic": concept,
                "subtopics": set(),
                "entities": {concept},
                "sentiment": 0.0,
                "timestamp": datetime.now(),
                "user_state": {},
                "previous_contexts": [],
                "confidence": 0.8
            }
        )
        
        # 3. Rimozione dai concetti sconosciuti
        if concept in self.unknown_concepts:
            self.unknown_concepts.remove(concept)
        
        # 4. Aggiornamento meta-learning
        self.meta_learning.update_concept_knowledge(
            concept,
            explanation,
            pattern
        )
        
        return True
    
    def calculate_confidence(self, patterns: List[Pattern]) -> float:
        """Calcola la confidenza complessiva del sistema"""
        if not patterns:
            return 0.0
        
        confidences = [p.confidence for p in patterns]
        return np.mean(confidences)
    
    def update_learning_history(self, result: LearningResult):
        """Aggiorna la storia dell'apprendimento"""
        history_entry = {
            "timestamp": datetime.now(),
            "unknown_concepts": list(result.unknown_concepts),
            "patterns_found": len(result.learned_patterns),
            "confidence": result.confidence,
            "emotional_state": result.emotional_state,
            "context": result.context.__dict__
        }
        self.learning_history.append(history_entry)
        
        # Mantiene solo gli ultimi 1000 record
        if len(self.learning_history) > 1000:
            self.learning_history = self.learning_history[-1000:]
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Ottiene statistiche sull'apprendimento"""
        if not self.learning_history:
            return {}
            
        total_concepts = sum(len(h["unknown_concepts"]) for h in self.learning_history)
        avg_confidence = np.mean([h["confidence"] for h in self.learning_history])
        
        return {
            "total_interactions": len(self.learning_history),
            "total_concepts_encountered": total_concepts,
            "average_confidence": avg_confidence,
            "current_unknown_concepts": len(self.unknown_concepts),
            "emotional_state": self.curiosity_system.__dict__
        }
