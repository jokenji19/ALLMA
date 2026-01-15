"""
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending - ALLMA (Adaptive Learning and Language Model Architecture)

This file implements the Perception System of ALLMA.
Author: Cristof Bano
Created: January 2025

This file contains proprietary and patent-pending technologies including:
- Multi-modal input processing
- Context recognition systems
- Pattern matching algorithms
- Sensory integration methods
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
from collections import defaultdict
import re
from queue import PriorityQueue

class InputType(Enum):
    TEXT = "text"
    PATTERN = "pattern"
    CONCEPT = "concept"
    RELATION = "relation"
    CONTEXT = "context"

class AttentionLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class PatternType(Enum):
    """Tipi di pattern riconoscibili"""
    SEQUENTIAL = "sequential"
    STRUCTURAL = "structural"
    TEMPORAL = "temporal"
    SEMANTIC = "semantic"

@dataclass
class Pattern:
    """Rappresenta un pattern riconosciuto"""
    pattern_type: PatternType
    elements: List[Any]
    confidence: float = 0.0
    frequency: int = 1
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Percept:
    """Rappresenta un percetto elaborato dal sistema"""
    input_type: InputType
    content: Any
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    patterns: List[Pattern] = field(default_factory=list)
    attention_level: AttentionLevel = AttentionLevel.LOW
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkingMemoryItem:
    """Rappresenta un elemento nella memoria di lavoro"""
    content: Any
    priority: float
    timestamp: datetime = field(default_factory=datetime.now)
    ttl: int = 100  # Time To Live in cicli di elaborazione
    
    def __lt__(self, other):
        # Implementa il confronto per la PriorityQueue
        return self.priority < other.priority

class PerceptionSystem:
    """Sistema di percezione per l'elaborazione degli input e il riconoscimento di pattern"""
    
    def __init__(self, working_memory_size: int = 10):
        self.working_memory: PriorityQueue = PriorityQueue(maxsize=working_memory_size)
        self.patterns: Dict[PatternType, List[Pattern]] = defaultdict(list)
        self.attention_focus: Dict[str, float] = defaultdict(float)
        self.context: Dict[str, Any] = {}
        self.long_term_patterns: Set[Tuple] = set()
        
    def process_input(self, input_data: Any, input_type: InputType) -> Percept:
        """Elabora l'input e genera un percetto"""
        # Analizza l'input
        if input_type == InputType.TEXT:
            patterns = self._analyze_text_patterns(input_data)
            confidence = self._calculate_text_confidence(input_data)
        else:
            patterns = []
            confidence = 0.5
            
        # Crea il percetto
        percept = Percept(
            input_type=input_type,
            content=input_data,
            confidence=confidence,
            patterns=patterns
        )
        
        # Aggiorna la memoria di lavoro
        self._update_working_memory(percept)
        
        return percept
        
    def _analyze_text_patterns(self, text: str) -> List[Pattern]:
        """Analizza il testo per trovare pattern"""
        patterns = []
        
        # Pattern sequenziali (ripetizioni)
        words = text.lower().split()
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
            if word_freq[word] > 1:
                patterns.append(Pattern(
                    pattern_type=PatternType.SEQUENTIAL,
                    elements=[word],
                    frequency=word_freq[word],
                    confidence=0.8
                ))
                
        # Pattern strutturali (frasi simili)
        memory_items = []
        while not self.working_memory.empty():
            item = self.working_memory.get()
            memory_items.append(item)
            if isinstance(item.content, str):
                similarity = self._calculate_text_similarity(text, item.content)
                if similarity > 0.5:
                    patterns.append(Pattern(
                        pattern_type=PatternType.STRUCTURAL,
                        elements=[text, item.content],
                        confidence=similarity
                    ))
        
        # Rimetti gli item nella working memory
        for item in memory_items:
            self.working_memory.put(item)
                        
        # Pattern semantici (parole chiave)
        keywords = {
            "errore": ["bug", "crash", "exception", "fail"],
            "performance": ["lento", "veloce", "ottimizzazione", "memoria"],
            "soluzione": ["fix", "risolto", "corretto", "implementato"]
        }
        
        for category, words in keywords.items():
            matches = [w for w in words if w in text.lower()]
            if matches:
                patterns.append(Pattern(
                    pattern_type=PatternType.SEMANTIC,
                    elements=[category] + matches,
                    confidence=len(matches) / len(words)
                ))
                
        return patterns
        
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calcola la similarità tra due testi"""
        # Implementazione semplificata usando parole comuni
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return 0.0
            
        return len(intersection) / len(union)
        
    def _calculate_text_confidence(self, text: str) -> float:
        """Calcola la confidenza per l'input testuale"""
        # Fattori che influenzano la confidenza
        factors = {
            "length": min(len(text.split()) / 20, 1.0),  # Lunghezza ottimale ~20 parole
            "clarity": 0.8 if any(char in text for char in ".,!?") else 0.5,  # Punteggiatura
            "structure": 0.9 if len(text.split()) > 3 else 0.6  # Struttura minima
        }
        
        return sum(factors.values()) / len(factors)
        
    def update_attention(self, focus_points: Dict[str, float]) -> None:
        """Aggiorna i punti di focus dell'attenzione"""
        # Resetta i focus precedenti
        self.attention_focus.clear()
        
        # Normalizza i pesi dell'attenzione
        total_weight = sum(focus_points.values())
        if total_weight > 0:
            self.attention_focus.update({
                k: v/total_weight
                for k, v in focus_points.items()
            })
            
    def get_attention_level(self, item: Any) -> AttentionLevel:
        """Determina il livello di attenzione per un item"""
        if isinstance(item, str):
            weight = self.attention_focus.get(item, 0.0)
        else:
            weight = sum(self.attention_focus.get(str(attr), 0.0) 
                        for attr in dir(item) if not attr.startswith('_'))
                        
        if weight > 0.6:  # Soglia per HIGH
            return AttentionLevel.HIGH
        elif weight > 0.3:  # Soglia per MEDIUM
            return AttentionLevel.MEDIUM
        else:
            return AttentionLevel.LOW
            
    def recognize_pattern(self, elements: List[Any], pattern_type: PatternType) -> Optional[Pattern]:
        """Riconosce un pattern negli elementi dati"""
        # Cerca pattern esistenti
        for pattern in self.patterns[pattern_type]:
            if self._match_pattern(pattern.elements, elements):
                pattern.frequency += 1
                pattern.last_seen = datetime.now()
                pattern.confidence = min(1.0, pattern.confidence + 0.1)
                return pattern
                
        # Crea un nuovo pattern
        new_pattern = Pattern(
            pattern_type=pattern_type,
            elements=elements,
            frequency=1,
            confidence=0.1
        )
        self.patterns[pattern_type].append(new_pattern)
        return new_pattern
        
    def integrate_context(self, context_data: Dict[str, Any]) -> None:
        """Integra nuove informazioni contestuali"""
        self.context.update(context_data)
        
        # Aggiorna le priorità nella memoria di lavoro
        self._reprioritize_working_memory()
        
    def get_working_memory_snapshot(self) -> List[WorkingMemoryItem]:
        """Ottiene uno snapshot della memoria di lavoro"""
        items = []
        temp_queue = PriorityQueue(maxsize=self.working_memory.maxsize)
        
        # Estrai e reinserisci gli elementi
        while not self.working_memory.empty():
            item = self.working_memory.get()
            items.append(item)
            temp_queue.put(item)
            
        # Ripristina la coda originale
        self.working_memory = temp_queue
        
        # Ordina gli item per priorità (decrescente)
        return sorted(items, key=lambda x: x.priority, reverse=True)
        
    def _preprocess_input(self, input_data: Any, input_type: InputType) -> Any:
        """Pre-processa l'input in base al tipo"""
        if input_type == InputType.TEXT:
            return self._preprocess_text(input_data)
        elif input_type == InputType.PATTERN:
            return self._preprocess_pattern(input_data)
        elif input_type == InputType.CONCEPT:
            return self._preprocess_concept(input_data)
        else:
            return input_data
            
    def _preprocess_text(self, text: str) -> str:
        """Pre-processa input testuali"""
        # Normalizza il testo
        text = text.lower().strip()
        # Rimuovi punteggiatura non necessaria
        text = re.sub(r'[^\w\s]', '', text)
        return text
        
    def _preprocess_pattern(self, pattern: Any) -> Any:
        """Pre-processa pattern"""
        if isinstance(pattern, (list, tuple)):
            return tuple(sorted(pattern))
        return pattern
        
    def _preprocess_concept(self, concept: Any) -> Any:
        """Pre-processa concetti"""
        if isinstance(concept, dict):
            return frozenset(concept.items())
        return concept
        
    def _evaluate_confidence(self, input_data: Any, input_type: InputType) -> float:
        """Valuta la confidenza dell'input"""
        if input_type == InputType.TEXT:
            # Valuta la qualità del testo
            if not input_data:
                return 0.0
            # Penalizza testi troppo corti o troppo lunghi
            length = len(input_data)
            if length < 3:
                return 0.3
            elif length > 1000:
                return 0.7
            return 0.9
        elif input_type == InputType.PATTERN:
            # Valuta la forza del pattern
            if isinstance(input_data, (list, tuple)):
                return min(1.0, len(input_data) * 0.2)
            return 0.5
        else:
            return 1.0
            
    def _update_working_memory(self, percept: Percept) -> None:
        """Aggiorna la memoria di lavoro"""
        # Calcola la priorità
        priority = self._calculate_priority(percept)
        
        # Crea l'item della memoria di lavoro
        memory_item = WorkingMemoryItem(
            content=percept,
            priority=priority
        )
        
        # Se la memoria è piena, rimuovi l'elemento meno prioritario
        if self.working_memory.full():
            self.working_memory.get()
            
        # Aggiungi il nuovo item
        self.working_memory.put(memory_item)
        
    def _calculate_priority(self, percept: Percept) -> float:
        """Calcola la priorità di un percept"""
        # Considera il decadimento temporale
        age = (datetime.now() - percept.timestamp).total_seconds()
        temporal_decay = max(0.0, 1.0 - (age / 3600))  # Decade in un'ora
        
        base_priority = percept.confidence * temporal_decay
        
        # Aumenta la priorità se l'elemento è nel focus dell'attenzione
        attention_boost = sum(
            weight for key, weight in self.attention_focus.items()
            if str(key).lower() in str(percept.content).lower()
        )
        
        # Considera il contesto
        context_relevance = self._evaluate_context_relevance(percept)
        
        # Calcola la priorità finale
        priority = (
            base_priority * 0.4 +  # 40% base priority
            attention_boost * 0.4 +  # 40% attention
            context_relevance * 0.2  # 20% context
        )
        
        return min(1.0, max(0.0, priority))  # Normalizza tra 0 e 1
        
    def _evaluate_context_relevance(self, percept: Percept) -> float:
        """Valuta la rilevanza rispetto al contesto corrente"""
        if not self.context:
            return 0.0
            
        relevance = 0.0
        percept_str = str(percept.content).lower()
        
        # Cerca corrispondenze con il contesto
        for key, value in self.context.items():
            if str(key).lower() in percept_str or str(value).lower() in percept_str:
                relevance += 0.2
                
        return min(1.0, relevance)
        
    def _detect_patterns(self, percept: Percept) -> None:
        """Rileva pattern nell'input corrente"""
        # Ottieni gli elementi recenti dalla memoria di lavoro
        recent_items = self.get_working_memory_snapshot()
        
        if recent_items:
            # Cerca pattern sequenziali
            self._detect_sequential_patterns(recent_items)
            
            # Cerca pattern strutturali
            self._detect_structural_patterns(recent_items)
            
            # Cerca pattern temporali
            self._detect_temporal_patterns(recent_items)
            
            # Cerca pattern semantici
            self._detect_semantic_patterns(recent_items)
            
    def _detect_sequential_patterns(self, items: List[WorkingMemoryItem]) -> None:
        """Rileva pattern sequenziali"""
        if len(items) < 2:
            return
            
        # Estrai le sequenze di contenuti
        sequence = [item.content for item in items]
        self.recognize_pattern(sequence, PatternType.SEQUENTIAL)
        
    def _detect_structural_patterns(self, items: List[WorkingMemoryItem]) -> None:
        """Rileva pattern strutturali"""
        for item in items:
            if hasattr(item.content, '__dict__'):
                structure = tuple(sorted(item.content.__dict__.keys()))
                self.recognize_pattern([structure], PatternType.STRUCTURAL)
                
    def _detect_temporal_patterns(self, items: List[WorkingMemoryItem]) -> None:
        """Rileva pattern temporali"""
        if len(items) < 2:
            return
            
        # Calcola gli intervalli temporali
        intervals = []
        for i in range(1, len(items)):
            interval = (items[i].timestamp - items[i-1].timestamp).total_seconds()
            intervals.append(interval)
            
        self.recognize_pattern(intervals, PatternType.TEMPORAL)
        
    def _detect_semantic_patterns(self, items: List[WorkingMemoryItem]) -> None:
        """Rileva pattern semantici"""
        # Estrai concetti e relazioni
        concepts = []
        for item in items:
            if item.content.input_type == InputType.CONCEPT:
                concepts.append(item.content.content)
                
        if concepts:
            self.recognize_pattern(concepts, PatternType.SEMANTIC)
            
    def _match_pattern(self, pattern_elements: List[Any], elements: List[Any]) -> bool:
        """Verifica se due pattern corrispondono"""
        if len(pattern_elements) != len(elements):
            return False
            
        return all(self._elements_match(p, e) for p, e in zip(pattern_elements, elements))
        
    def _elements_match(self, element1: Any, element2: Any) -> bool:
        """Verifica se due elementi corrispondono"""
        if isinstance(element1, (int, float)) and isinstance(element2, (int, float)):
            # Per numeri, considera una tolleranza
            return abs(element1 - element2) < 0.001
        return element1 == element2
        
    def _reprioritize_working_memory(self) -> None:
        """Ricalcola le priorità nella memoria di lavoro"""
        items = self.get_working_memory_snapshot()
        
        # Svuota la memoria
        self.working_memory = PriorityQueue(maxsize=self.working_memory.maxsize)
        
        # Reinserisci gli elementi con priorità aggiornate
        for item in items:
            if isinstance(item.content, Percept):
                priority = self._calculate_priority(item.content)
                item.priority = priority
                self.working_memory.put(item)
