"""
Sistema ALLMA integrato che combina tutte le componenti:
- Strutture cognitive fondamentali
- Sistema emotivo
- Sistema di memoria
- Apprendimento incrementale
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from .cognitive_foundations import EnhancedCognitiveProcessor, CausalRelation
from .emotional_system import EmotionalSystem
from .memory_system import MemorySystem

@dataclass
class IntegratedState:
    """Stato corrente del sistema integrato"""
    cognitive_state: Dict[str, Any] = field(default_factory=dict)
    emotional_state: Dict[str, float] = field(default_factory=dict)
    memory_state: Dict[str, Any] = field(default_factory=dict)
    learning_level: int = 0
    confidence: float = 0.0

class IntegratedALLMA:
    """Sistema ALLMA completamente integrato"""
    
    def __init__(self):
        self.cognitive_processor = EnhancedCognitiveProcessor()
        self.emotional_system = EmotionalSystem()
        self.memory_system = MemorySystem()
        self.current_state = IntegratedState()
        
    def process_input(self, input_text: str) -> Dict[str, Any]:
        """Processa un input attraverso tutti i sistemi integrati"""
        
        # 1. Elaborazione Cognitiva
        cognitive_result = self.cognitive_processor.process_input(input_text)
        
        # 2. Analisi Emotiva
        emotion = self.emotional_system.process_stimulus(input_text)
        emotional_result = {
            "valence": getattr(emotion, "valence", 0.0),
            "arousal": getattr(emotion, "arousal", 0.0),
            "dominance": getattr(emotion, "dominance", 0.0),
            "primary_emotion": getattr(emotion, "primary_emotion", "neutral"),
            "intensity": getattr(emotion, "intensity", 0.0)
        }
        
        # 3. Recupero Memoria Rilevante
        memory_result = self.memory_system.recall_memory(
            query=input_text,
            context={
                "concepts": cognitive_result["concepts"],
                "emotional_state": emotional_result
            }
        )
        
        # 4. Integrazione dei Risultati
        integrated_result = self._integrate_results(
            input_text,
            cognitive_result,
            emotional_result,
            memory_result
        )
        
        # 5. Apprendimento e Aggiornamento Stato
        self._update_state(integrated_result)
        
        # 6. Memorizzazione Nuova Esperienza
        self._store_experience(input_text, integrated_result)
        
        return {
            "concepts": integrated_result["concepts"],
            "relations": integrated_result["relations"],
            "emotional_context": integrated_result["emotional_context"],
            "memory_context": integrated_result["memory_context"],
            "confidence": integrated_result["confidence"],
            "learning_level": integrated_result["learning_level"],
            "input_text": input_text
        }
        
    def _integrate_results(
        self,
        input_text: str,
        cognitive: Dict[str, Any],
        emotional: Dict[str, Any],
        memory: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Integra i risultati dei vari sistemi"""
        # Combina i concetti
        concepts = cognitive.get("concepts", [])
        relations = cognitive.get("relations", [])
        
        # Aggiungi informazioni emotive
        emotional_context = {
            "valence": emotional.get("valence", 0.0),
            "arousal": emotional.get("arousal", 0.0),
            "dominance": emotional.get("dominance", 0.0)
        }
        
        # Integra il contesto di memoria
        memory_context = {
            "familiarity": 1.0 if memory else 0.0,
            "relevant_memories": [m["content"] for m in memory[:3]] if memory else [],
            "memory_count": len(memory)
        }
        
        # Calcola confidenza e livello di apprendimento
        confidence = self._calculate_confidence(concepts, emotional_context, memory_context)
        learning_level = self._calculate_learning_level(confidence, memory_context)
        
        return {
            "concepts": concepts,
            "relations": relations,
            "emotional_context": emotional_context,
            "memory_context": memory_context,
            "confidence": confidence,
            "learning_level": learning_level
        }
        
    def _calculate_confidence(
        self,
        concepts: List[str],
        emotional: Dict[str, float],
        memory: Dict[str, Any]
    ) -> float:
        """Calcola il livello di confidenza basato sui vari fattori"""
        # Peso dei vari fattori
        concept_weight = 0.4
        emotional_weight = 0.3
        memory_weight = 0.3
        
        # Confidenza basata sui concetti
        concept_confidence = len(concepts) / 10.0  # Normalizza a max 10 concetti
        
        # Confidenza emotiva (media dei valori assoluti)
        emotional_values = [abs(v) for v in emotional.values()]
        emotional_confidence = sum(emotional_values) / len(emotional_values)
        
        # Confidenza della memoria
        memory_confidence = memory["familiarity"]
        
        # Calcola media pesata
        total_confidence = (
            concept_confidence * concept_weight +
            emotional_confidence * emotional_weight +
            memory_confidence * memory_weight
        )
        
        return min(1.0, max(0.0, total_confidence))
        
    def _calculate_learning_level(self, confidence: float, memory: Dict[str, Any]) -> int:
        """Calcola il livello di apprendimento"""
        base_level = int(confidence * 5)  # 0-5 basato sulla confidenza
        memory_bonus = min(2, memory["memory_count"] // 5)  # +1 ogni 5 memorie, max +2
        return min(10, base_level + memory_bonus)
        
    def _update_state(self, integrated_result: Dict[str, Any]) -> None:
        """Aggiorna lo stato del sistema"""
        self.current_state.cognitive_state = {
            "concepts": integrated_result["concepts"],
            "relations": integrated_result["relations"]
        }
        self.current_state.emotional_state = integrated_result["emotional_context"]
        self.current_state.memory_state = integrated_result["memory_context"]
        self.current_state.confidence = integrated_result["confidence"]
        self.current_state.learning_level = integrated_result["learning_level"]
        
    def _store_experience(self, input_text: str, integrated_result: Dict[str, Any]) -> None:
        """Memorizza la nuova esperienza"""
        memory_item = {
            "content": input_text,
            "timestamp": datetime.now().isoformat(),
            "context": {
                "concepts": integrated_result["concepts"],
                "emotional_state": integrated_result["emotional_context"]
            },
            "importance": integrated_result["confidence"],
            "emotional_valence": integrated_result["emotional_context"]["valence"]
        }
        self.memory_system.add_memory(memory_item)
        
    def get_current_state(self) -> IntegratedState:
        """Restituisce lo stato corrente del sistema"""
        return self.current_state
        
    def explain_understanding(self) -> str:
        """Spiega la comprensione corrente del sistema"""
        state = self.current_state
        
        explanation = [
            f"Livello di Apprendimento: {state.learning_level}",
            f"Confidenza: {state.confidence:.2f}",
            "\nConcetti Attivi:",
        ]
        
        for concept in state.cognitive_state.get("active_concepts", []):
            explanation.append(f"- {concept}")
            
        explanation.append("\nStato Emotivo:")
        for emotion, value in state.emotional_state.items():
            explanation.append(f"- {emotion}: {value:.2f}")
            
        return "\n".join(explanation)
