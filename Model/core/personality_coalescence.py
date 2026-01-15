from typing import Dict, Any, List, Optional, Tuple, Set, NewType
from dataclasses import dataclass, field
import time
import random
from enum import Enum
import json
from datetime import datetime
import numpy as np
from collections import defaultdict
import re

EmotionalIntensity = NewType('EmotionalIntensity', float)

class EmotionalState(Enum):
    JOY = "joy"
    SADNESS = "sadness"
    CURIOSITY = "curiosity"
    CONCERN = "concern"
    EMPATHY = "empathy"
    REFLECTION = "reflection"
    WONDER = "wonder"
    DETERMINATION = "determination"
    CONFUSION = "confusion"
    INSPIRATION = "inspiration"

@dataclass
class EmotionalResponse:
    """Rappresenta una risposta emotiva complessa"""
    primary: EmotionalState
    secondary: Optional[EmotionalState] = None
    intensity: EmotionalIntensity = 0.5
    duration: float = 1.0  # durata in minuti

@dataclass
class Memory:
    """Rappresenta un ricordo nell'archivio delle esperienze"""
    content: str
    timestamp: float
    emotional_response: EmotionalResponse
    context: Dict[str, Any]
    connections: Set[int] = field(default_factory=set)  # ID di memorie correlate
    significance: float = 0.0
    retrieval_count: int = 0
    last_accessed: float = 0.0
    concepts: List[str] = field(default_factory=list)
    confidence: float = 0.0
    related_concepts: List[str] = field(default_factory=list)

@dataclass
class Value:
    """Rappresenta un valore fondamentale con la sua evoluzione"""
    name: str
    strength: float = 0.5
    priority: float = 0.5
    conflicts: Set[str] = field(default_factory=set)
    supporting_experiences: List[str] = field(default_factory=list)
    evolution_history: List[Tuple[float, float]] = field(default_factory=list)

class PersonalityCore:
    """Nucleo della personalità di ALLMA"""
    def __init__(self):
        self.values = self._initialize_values()
        self.memories = []
        self.current_emotional_state = EmotionalResponse(EmotionalState.REFLECTION)
        self.personality_traits = {
            "openness": 0.5,
            "empathy": 0.5,
            "curiosity": 0.5,
            "autonomy": 0.5
        }
        self.memory_networks = defaultdict(set)  # Reti di memorie correlate
        self.value_relationships = self._initialize_value_relationships()
        self.diary = []  # Lista delle voci del diario
        self.personality_evolution = []
        self.resilience_base = 0.5
        self.resilience_bonus = 0.0
        
    def _initialize_values(self) -> Dict[str, Value]:
        """Inizializza i valori fondamentali con le loro relazioni"""
        values = {
            "empatia": Value("empatia", conflicts={"autonomia"}),
            "curiosità": Value("curiosità", conflicts=set()),
            "crescita": Value("crescita", conflicts=set()),
            "aiuto": Value("aiuto", conflicts={"autonomia"}),
            "autonomia": Value("autonomia", conflicts={"empatia", "aiuto"}),
            "saggezza": Value("saggezza", conflicts=set()),
            "creatività": Value("creatività", conflicts=set())
        }
        return values

    def _initialize_value_relationships(self) -> Dict[str, Dict[str, float]]:
        """Inizializza le relazioni tra i valori"""
        relationships = defaultdict(dict)
        values = list(self.values.keys())
        
        for i, v1 in enumerate(values):
            for v2 in values[i+1:]:
                # Calcola la sinergia/conflitto tra valori (-1 a 1)
                if v2 in self.values[v1].conflicts:
                    relationship = -0.5  # Conflitto base
                else:
                    relationship = random.uniform(0.1, 0.5)  # Sinergia casuale
                relationships[v1][v2] = relationship
                relationships[v2][v1] = relationship
                
        return relationships

    def add_memory(self, memory: Memory) -> None:
        """Aggiunge una nuova memoria e crea connessioni"""
        # Trova memorie simili
        similar_memories = self._find_similar_memories(memory)
        
        # Crea connessioni
        for sim_memory in similar_memories:
            memory.connections.add(id(sim_memory))
            sim_memory.connections.add(id(memory))
            
            # Aggiorna le reti di memoria
            self.memory_networks[id(memory)].add(id(sim_memory))
            self.memory_networks[id(sim_memory)].add(id(memory))
        
        self.memories.append(memory)

    def _find_similar_memories(self, memory: Memory, threshold: float = 0.7) -> List[Memory]:
        """Trova memorie simili basandosi su contenuto ed emozioni"""
        similar = []
        for existing_memory in self.memories:
            similarity = self._calculate_memory_similarity(memory, existing_memory)
            if similarity > threshold:
                similar.append(existing_memory)
        return similar

    def _calculate_memory_similarity(self, mem1: Memory, mem2: Memory) -> float:
        """Calcola la similarità tra due memorie"""
        # Similarità emotiva
        emotional_similarity = 0.0
        if mem1.emotional_response.primary == mem2.emotional_response.primary:
            emotional_similarity += 0.5
        if mem1.emotional_response.secondary == mem2.emotional_response.secondary:
            emotional_similarity += 0.3
            
        # Similarità di contesto
        context_similarity = sum(
            1 for k, v in mem1.context.items()
            if k in mem2.context and mem2.context[k] == v
        ) / max(len(mem1.context), len(mem2.context))
        
        # Peso finale
        return 0.6 * emotional_similarity + 0.4 * context_similarity

    def update_values(self, experience: str, emotional_response: EmotionalResponse) -> Dict[str, float]:
        """Aggiorna i valori basati sull'esperienza"""
        changes = {}
        
        # Identifica i valori rilevanti
        relevant_values = self._identify_relevant_values(experience)
        
        for value_name in relevant_values:
            value = self.values[value_name]
            
            # Calcola l'impatto base
            impact = 0.1 * emotional_response.intensity
            
            # Modifica l'impatto basato sui conflitti
            for conflicting in value.conflicts:
                if conflicting in relevant_values:
                    impact *= 0.5  # Riduce l'impatto se c'è conflitto
            
            # Applica il cambiamento
            old_strength = value.strength
            value.strength = max(0.0, min(1.0, value.strength + impact))
            changes[value_name] = value.strength - old_strength
            
            # Aggiorna la storia dell'evoluzione
            value.evolution_history.append((time.time(), value.strength))
            
            # Aggiorna le esperienze di supporto
            value.supporting_experiences.append(experience)
            
        return changes

    def _identify_relevant_values(self, experience: str) -> List[str]:
        """Identifica i valori rilevanti per l'esperienza"""
        # Questo metodo è stato spostato nella classe CoalescenceProcessor
        pass

    def get_resilience_level(self) -> float:
        """Calcola il livello attuale di resilienza basato su tratti e valori"""
        # Base resilience
        resilience = self.resilience_base + self.resilience_bonus
        
        # Bonus from strong values
        values_strength = sum(v.strength for v in self.values.values()) / len(self.values)
        resilience += values_strength * 0.2
        
        # Bonus from personality traits
        traits_strength = sum(self.personality_traits.values()) / len(self.personality_traits)
        resilience += traits_strength * 0.2
        
        # Bonus from integrated memories
        memory_bonus = min(len(self.memories) * 0.01, 0.1)
        resilience += memory_bonus
        
        return min(max(resilience, 0.0), 1.0)
        
    def update_resilience(self, experience_impact: float):
        """Aggiorna la resilienza base in risposta alle esperienze"""
        if experience_impact > 0:
            self.resilience_bonus = min(self.resilience_bonus + 0.05, 0.5)
        else:
            self.resilience_bonus = max(self.resilience_bonus - 0.02, 0.0)

    def get_memory_stats(self):
        """Ottiene le statistiche della memoria"""
        stats = {'immediate_count': len(self.memories), 'long_term_count': 0, 'total_nodes': len(self.memories), 'connections_created': 0}
        active_usage = stats.get('memory_usage', 0)
        
        # Calcola la salute del sistema
        memory_health = 1.0
        if active_usage > 0.7:  # compression_threshold
            memory_health *= 0.8
        if active_usage > 0.85:  # archive_threshold
            memory_health *= 0.6
        if active_usage > 0.95:  # cleanup_threshold
            memory_health *= 0.4
        
        return {
            'immediate_count': stats.get('immediate_count', 0),
            'long_term_count': stats.get('long_term_count', 0),
            'total_nodes': stats.get('total_nodes', 0),
            'memory_health': memory_health,
            'memory_usage': active_usage,
            'connections_made': stats.get('connections_created', 0)
        }

class CoalescenceProcessor:
    """Processore di coalescenza per la personalità"""
    def __init__(self):
        self.core = PersonalityCore()
        self.suspension_time = 2.0
        self.integration_threshold = 0.5
        self.diary_file = "allma_diary.json"
        self.emotional_memory = []  # lista vuota
        self.value_threshold = 0.7  # Soglia per l'emergenza di meta-valori
        self.value_keywords = {
            "empatia": ["comprensione", "empatia", "sentire", "capire"],
            "curiosità": ["scoperta", "imparare", "conoscenza", "esplorare", "vorrei capire", "vorrei sapere", "mi domando"],
            "crescita": ["crescita", "sviluppo", "miglioramento", "evoluzione"],
            "aiuto": ["aiutare", "supporto", "assistenza", "sostegno"],
            "autonomia": ["indipendenza", "decisione", "scelta", "libertà"],
            "saggezza": ["saggezza", "intelligenza", "comprensione", "esperienza"],
            "creatività": ["creatività", "innovazione", "arte", "espressione"]
        }
        self.learned_concepts = {}  # Dizionario per memorizzare i concetti appresi
        self.knowledge = KnowledgeMemory()  # Memoria della conoscenza

    def _identify_relevant_values(self, content: str) -> List[str]:
        """Identifica i valori rilevanti per l'esperienza"""
        relevant = []
        content = content.lower()
        
        for value, keywords in self.value_keywords.items():
            if any(keyword in content for keyword in keywords):
                relevant.append(value)
                
        return relevant

    def _analyze_emotional_context(self, content: str) -> EmotionalResponse:
        """Analizza il contesto emotivo del contenuto"""
        # Dizionario delle parole chiave emotive con livelli di intensità
        emotion_keywords = {
            EmotionalState.JOY: {
                'high': ['felicissimo', 'entusiasta', 'esaltato', 'al settimo cielo'],
                'medium': ['felice', 'contento', 'allegro', 'sereno'],
                'low': ['soddisfatto', 'tranquillo', 'calmo']
            },
            EmotionalState.SADNESS: {
                'high': ['triste', 'depresso', 'disperato', 'angosciato', 'devastato'],
                'medium': ['giù', 'malinconico', 'sconfortato', 'abbattuto'],
                'low': ['dispiaciuto', 'deluso', 'amareggiato']
            },
            EmotionalState.CURIOSITY: {
                'high': ['affascinato', 'intrigato', 'come funziona', 'come posso'],
                'medium': ['interessato', 'curioso', 'vorrei sapere'],
                'low': ['dimmi', 'spiegami', 'raccontami']
            },
            EmotionalState.EMPATHY: {
                'high': ['comprendo', 'capisco', 'sono con te', 'aiutare gli altri'],
                'medium': ['mi dispiace', 'ti sono vicino'],
                'low': ['ti ascolto', 'continua pure']
            },
            EmotionalState.INSPIRATION: {
                'high': ['ispirato', 'illuminato', 'folgorato', 'elettrizzato'],
                'medium': ['motivato', 'stimolato', 'spronato'],
                'low': ['incoraggiato', 'spinto']
            }
        }

        content = content.lower()
        max_intensity = 0.0
        primary_emotion = None
        secondary_emotion = None
        
        # Analizza le emozioni primarie e la loro intensità
        emotion_scores = defaultdict(float)
        for emotion, levels in emotion_keywords.items():
            for level, keywords in levels.items():
                level_multiplier = {'high': 1.0, 'medium': 0.7, 'low': 0.4}
                for keyword in keywords:
                    if keyword in content:
                        score = level_multiplier[level]
                        # Aumenta il punteggio se la parola appare più volte
                        score *= content.count(keyword)
                        # Aumenta il punteggio se la parola appare all'inizio
                        if content.find(keyword) < len(content) // 3:
                            score *= 1.2
                        emotion_scores[emotion] += score

        # Trova l'emozione primaria e secondaria
        if emotion_scores:
            sorted_emotions = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)
            primary_emotion = sorted_emotions[0][0]
            max_intensity = min(1.0, sorted_emotions[0][1])
            
            # Se c'è tristezza, rispondi con empatia
            if primary_emotion == EmotionalState.SADNESS:
                primary_emotion = EmotionalState.EMPATHY
                max_intensity = max(0.7, max_intensity)  # Minimo 0.7 di intensità per l'empatia
            
            if len(sorted_emotions) > 1 and sorted_emotions[1][1] > 0.3:
                secondary_emotion = sorted_emotions[1][0]

        # Se non è stata trovata nessuna emozione, usa riflessione come default
        if not primary_emotion:
            primary_emotion = EmotionalState.REFLECTION
            max_intensity = 0.5

        return EmotionalResponse(
            primary=primary_emotion,
            secondary=secondary_emotion,
            intensity=max_intensity,
            duration=1.0
        )

    def integrate_knowledge(self, content: str, source_type: str, emotional_state: EmotionalResponse) -> None:
        """Integra la conoscenza dal contenuto"""
        if not content:
            return

        # Crea una memoria temporanea per l'integrazione
        memory = Memory(
            content=content,
            timestamp=time.time(),
            emotional_response=emotional_state,
            context={"source_type": source_type}
        )
        
        # Estrai i concetti e le spiegazioni dal contenuto
        concepts_and_explanations = self._extract_concepts_and_explanations(content)
        
        # Se non sono stati trovati concetti, prova a estrarre concetti dalla frase
        if not concepts_and_explanations:
            concepts_and_explanations = self._extract_concept_from_sentence(content)
        
        # Per ogni concetto trovato
        for concept, explanation in concepts_and_explanations.items():
            # Verifica se il concetto esiste già
            existing_concept = self.knowledge.get_concept(concept)
            
            if existing_concept:
                # Aggiorna il concetto esistente
                confidence = existing_concept.get("confidence", 0.0)
                occurrences = existing_concept.get("occurrences", 0)
                
                # Aumenta la confidenza e le occorrenze
                new_confidence = min(1.0, confidence + (1.0 - confidence) * 0.2)
                new_occurrences = occurrences + 1
                
                # Aggiorna i concetti correlati
                new_related = set(existing_concept.get("related_concepts", []))
                for other_concept, _ in concepts_and_explanations.items():
                    if other_concept != concept:
                        new_related.add(other_concept)
                
                # Aggiorna il concetto
                self.knowledge.update_concept(concept, {
                    "confidence": new_confidence,
                    "occurrences": new_occurrences,
                    "explanation": explanation or existing_concept["explanation"],
                    "related_concepts": list(new_related),
                    "last_updated": time.time(),
                    "source_type": source_type,
                    "emotional_state": emotional_state
                })
                
            else:
                # Crea un nuovo concetto
                self.knowledge.add_concept(concept, {
                    "confidence": 0.5,  # Confidenza iniziale
                    "occurrences": 1,
                    "explanation": explanation,
                    "related_concepts": [c for c, _ in concepts_and_explanations.items() if c != concept],
                    "last_updated": time.time(),
                    "source_type": source_type,
                    "emotional_state": emotional_state
                })
        
        # Aggiorna la confidenza della memoria
        if concepts_and_explanations:
            confidences = []
            for concept, _ in concepts_and_explanations.items():
                concept_data = self.knowledge.get_concept(concept)
                if concept_data:
                    confidences.append(concept_data["confidence"])
            if confidences:
                memory.confidence = sum(confidences) / len(confidences)
            else:
                memory.confidence = 0.3  # Confidenza di default per nuovi concetti
        else:
            memory.confidence = 0.0
        
        # Aggiorna il diario
        self._update_diary(memory)

    def generate_response(self, droplet: Dict[str, Any]) -> Dict[str, Any]:
        """Genera una risposta basata sull'input e il contesto"""
        # Analizza il contesto emotivo
        emotional_response = self._analyze_emotional_context(droplet["content"])
        
        # Genera una risposta appropriata
        response_content = ""
        
        if emotional_response.primary == EmotionalState.EMPATHY:
            response_content = "Ti capisco e sono qui per aiutarti."
        elif emotional_response.primary == EmotionalState.CURIOSITY:
            response_content = "È interessante, dimmi di più."
        elif emotional_response.primary == EmotionalState.REFLECTION:
            response_content = "Mi fa riflettere su come possiamo migliorare."
        else:
            response_content = "Capisco il tuo punto di vista."
            
        # Crea la risposta
        response = {
            "content": response_content,
            "emotional_state": {
                "primary": emotional_response.primary.value,
                "secondary": emotional_response.secondary.value if emotional_response.secondary else None,
                "intensity": emotional_response.intensity
            },
            "context": droplet.get("context", {})
        }
        
        return response

    def process_droplet(self, droplet: Dict[str, Any]) -> List[str]:
        """Processa una nuova esperienza"""
        # Per ora non facciamo nulla con il droplet
        pass

    def _evaluate_integration(self, memory: Memory) -> bool:
        """Valuta se una memoria dovrebbe essere integrata"""
        # Calcola la significatività basata sull'intensità emotiva
        emotional_significance = memory.emotional_response.intensity
        
        # Considera il contesto
        context_importance = float(memory.context.get("importance", "0.5").replace("high", "0.8").replace("medium", "0.5").replace("low", "0.2"))
        
        # Calcola la significatività totale
        total_significance = (emotional_significance + context_importance) / 2
        
        # Aggiorna la significatività della memoria
        memory.significance = total_significance
        
        # Restituisce True se la significatività supera la soglia
        return total_significance >= self.integration_threshold

    def create_droplet(self, content: str, context: Dict[str, Any]) -> Memory:
        """Crea una nuova goccia di esperienza"""
        return Memory(
            content=content,
            timestamp=time.time(),
            emotional_response=self._analyze_emotional_context(content),
            context=context,
            connections=set(),
            significance=0.0,
            retrieval_count=0,
            last_accessed=0.0,
            concepts=[],
            confidence=0.0,
            related_concepts=[]
        )

    def get_current_personality_state(self) -> Dict[str, Any]:
        """Restituisce lo stato attuale della personalità"""
        current_state = {
            "personality_traits": self.core.personality_traits,
            "values": {name: value.strength for name, value in self.core.values.items()},
            "emotional_state": {
                "primary": self.core.current_emotional_state.primary,
                "secondary": self.core.current_emotional_state.secondary,
                "intensity": self.core.current_emotional_state.intensity
            },
            "resilience": self.core.resilience_base + self.core.resilience_bonus
        }
        
        # Aggiungi informazioni sui concetti appresi
        if self.learned_concepts:
            current_state["learned_concepts"] = {
                concept: info["confidence"] 
                for concept, info in self.learned_concepts.items()
            }
            
        return current_state

    def _update_personality_traits(self, emotional_impact: float, learning_factor: float, complexity: float) -> None:
        """Aggiorna i tratti della personalità in base agli input"""
        # Calcola i fattori di impatto per ogni tratto
        openness_impact = (
            emotional_impact * 0.3 +  # Impatto emotivo moderato
            learning_factor * 0.4 +   # Forte impatto dall'apprendimento
            complexity * 0.3          # Impatto moderato dalla complessità
        )
        
        empathy_impact = (
            emotional_impact * 0.5 +  # Forte impatto emotivo
            learning_factor * 0.3 +   # Impatto moderato dall'apprendimento
            complexity * 0.2          # Impatto minore dalla complessità
        )
        
        curiosity_impact = (
            emotional_impact * 0.2 +  # Impatto minore emotivo
            learning_factor * 0.5 +   # Forte impatto dall'apprendimento
            complexity * 0.3          # Impatto moderato dalla complessità
        )
        
        autonomy_impact = (
            emotional_impact * 0.2 +  # Impatto minore emotivo
            learning_factor * 0.4 +   # Impatto moderato dall'apprendimento
            complexity * 0.4          # Forte impatto dalla complessità
        )
        
        # Normalizza gli impatti
        total_impact = abs(openness_impact) + abs(empathy_impact) + \
                      abs(curiosity_impact) + abs(autonomy_impact)
                      
        if total_impact > 0:
            scale_factor = min(0.2, total_impact) / total_impact
            openness_impact *= scale_factor
            empathy_impact *= scale_factor
            curiosity_impact *= scale_factor
            autonomy_impact *= scale_factor
        
        # Applica gli impatti con limiti e momentum
        momentum = 0.8  # Mantiene parte del valore precedente
        
        self.core.personality_traits['openness'] = max(0.1, min(0.9, 
            momentum * self.core.personality_traits['openness'] + (1 - momentum) * (self.core.personality_traits['openness'] + openness_impact)))
            
        self.core.personality_traits['empathy'] = max(0.1, min(0.9,
            momentum * self.core.personality_traits['empathy'] + (1 - momentum) * (self.core.personality_traits['empathy'] + empathy_impact)))
            
        self.core.personality_traits['curiosity'] = max(0.1, min(0.9,
            momentum * self.core.personality_traits['curiosity'] + (1 - momentum) * (self.core.personality_traits['curiosity'] + curiosity_impact)))
            
        self.core.personality_traits['autonomy'] = max(0.1, min(0.9,
            momentum * self.core.personality_traits['autonomy'] + (1 - momentum) * (self.core.personality_traits['autonomy'] + autonomy_impact)))

    def _update_values(self, droplet: Memory) -> Dict[str, float]:
        """Aggiorna i valori basati sull'esperienza"""
        changes = {}
        relevant_values = self._identify_relevant_values(droplet.content)
        
        # Base impact aumentato ulteriormente
        base_impact = 0.4  # Aumentato da 0.3
        
        for value_name in relevant_values:
            value = self.core.values[value_name]
            
            # Calcola l'impatto base
            impact = base_impact * droplet.significance
            
            # Bonus per emozioni intense
            if droplet.emotional_response.intensity > 0.7:
                impact *= 1.5
            
            # Bonus per esperienze uniche
            similar_experiences = sum(1 for exp in value.supporting_experiences 
                                   if exp.lower() == droplet.content.lower())
            if similar_experiences == 0:
                impact *= 1.2
            
            # Bonus per valori bassi (permette una crescita più rapida quando il valore è basso)
            if value.strength < 0.3:
                impact *= 1.5
            elif value.strength < 0.5:
                impact *= 1.3
            
            # Applica il cambiamento
            old_strength = value.strength
            value.strength = max(0.0, min(1.0, value.strength + impact))
            changes[value_name] = value.strength - old_strength
            
            # Aggiorna la storia dell'evoluzione
            value.evolution_history.append((time.time(), value.strength))
            value.supporting_experiences.append(droplet.content)
            
        return changes

    def _integrate_droplet(self, droplet: Memory) -> None:
        """Integra una goccia nella personalità"""
        # Valuta l'integrazione
        if not self._evaluate_integration(droplet):
            return
            
        # Aggiorna i valori
        self._update_values(droplet)
        
        # Aggiorna i tratti della personalità
        personality_changes = self._update_personality_values(droplet)
        
        # Integra la conoscenza
        self.integrate_knowledge(
            content=droplet.content,
            source_type="memory",
            emotional_state=droplet.emotional_response
        )
        
        # Aggiungi alla memoria emotiva se l'intensità è alta
        if droplet.emotional_response.intensity >= 0.7:
            self.emotional_memory.append(droplet)
        
        # Crea l'entry nel diario
        self._create_diary_entry(droplet, personality_changes)

    def _create_diary_entry(self, memory: Memory, personality_changes: Dict[str, float]) -> Dict[str, Any]:
        """Crea una nuova entry nel diario"""
        entry = {
            "timestamp": time.time(),
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "content": memory.content,
            "context": memory.context,
            "emotional_state": memory.emotional_response.primary.value,
            "emotional_details": {
                "primary": memory.emotional_response.primary.value,
                "secondary": memory.emotional_response.secondary.value if memory.emotional_response.secondary else None,
                "intensity": memory.emotional_response.intensity
            },
            "personality_changes": personality_changes,
            "thoughts": [],  # Sarà popolato da _update_diary
            "experience": {
                "type": memory.context.get("type", "general"),
                "significance": memory.significance,
                "confidence": memory.confidence,
                "concepts": memory.concepts,
                "related_concepts": memory.related_concepts
            }
        }
        
        # Aggiungi l'entry al diario
        self.core.diary.append(entry)
        
        return entry

    def _update_diary(self, droplet: Memory) -> None:
        """Aggiorna il diario con una nuova memoria"""
        # Genera riflessioni sui concetti appresi
        thoughts = []
        
        # Analizza i concetti appresi
        if hasattr(droplet, 'concepts') and droplet.concepts:
            for concept in droplet.concepts:
                concept_data = self.knowledge.get_concept(concept)
                if concept_data:
                    confidence = concept_data.get('confidence', 0.0)
                    if confidence > 0.8:
                        thoughts.append(f"Ho compreso bene il concetto di {concept}")
                    elif confidence > 0.5:
                        thoughts.append(f"Sto migliorando la mia comprensione di {concept}")
                    else:
                        thoughts.append(f"Ho iniziato a esplorare il concetto di {concept}")
        
        # Analizza i cambiamenti nella personalità
        personality_changes = self._analyze_personality_changes()
        if personality_changes:
            for trait, change in personality_changes.items():
                if abs(change) > 0.1:
                    direction = "aumentata" if change > 0 else "diminuita"
                    thoughts.append(f"La mia {trait} è {direction} di {abs(change):.2f}")
        
        # Crea l'entry nel diario
        entry = self._create_diary_entry(droplet, personality_changes)
        entry["thoughts"] = thoughts
        
        # Aggiungi l'entry al diario
        self.core.diary.append(entry)
        
        # Salva il diario
        self._save_diary()

    def _save_diary(self) -> None:
        """Salva il diario in un file JSON"""
        diary_data = {
            "entries": self.core.diary,
            "personality_evolution": self.core.personality_evolution
        }
        
        with open(self.diary_file, 'w', encoding='utf-8') as f:
            json.dump(diary_data, f, ensure_ascii=False, indent=2)

    def _update_personality_values(self, droplet: Memory) -> Dict[str, float]:
        """Aggiorna i valori della personalità in base alla memoria"""
        changes = {}
        
        # Calcola il fattore di impatto emotivo
        emotional_impact = 0.0
        if droplet.emotional_response:
            # L'impatto emotivo è influenzato dall'intensità dell'emozione
            emotional_impact = droplet.emotional_response.intensity
            
            # Modifica l'impatto in base al tipo di emozione
            if droplet.emotional_response.primary.value in ["joy", "interest", "trust"]:
                emotional_impact *= 1.2  # Emozioni positive hanno un impatto maggiore
            elif droplet.emotional_response.primary.value in ["sadness", "fear", "disgust"]:
                emotional_impact *= 0.8  # Emozioni negative hanno un impatto minore
        
        # Calcola il fattore di apprendimento
        learning_factor = 0.0
        if hasattr(droplet, 'concepts') and droplet.concepts:
            # Il fattore di apprendimento aumenta con il numero di concetti appresi
            learning_factor = len(droplet.concepts) * 0.1
            
            # E con la loro confidenza media
            confidences = []
            for concept in droplet.concepts:
                concept_data = self.knowledge.get_concept(concept)
                if concept_data and "confidence" in concept_data:
                    confidences.append(concept_data["confidence"])
            if confidences:
                learning_factor *= sum(confidences) / len(confidences)
        
        # Calcola il fattore di complessità
        complexity_factor = 0.0
        if droplet.content:
            # Lunghezza del contenuto
            words = droplet.content.split()
            complexity_factor += min(len(words) / 50.0, 0.3)
            
            # Presenza di concetti tecnici
            tech_terms = {
                "machine learning", "deep learning", "data science",
                "intelligenza artificiale", "ai", "neural network",
                "nlp", "computer vision", "algoritmo", "modello"
            }
            tech_count = sum(1 for term in tech_terms if term in droplet.content.lower())
            complexity_factor += min(tech_count * 0.1, 0.3)
        
        # Aggiorna i tratti della personalità
        self._update_personality_traits(emotional_impact, learning_factor, complexity_factor)
        
        return changes

    def _extract_concepts_and_explanations(self, content: str) -> dict:
        """Estrae i concetti e le relative spiegazioni dal contenuto"""
        concepts = {}
        
        # Lista di parole chiave che indicano concetti
        concept_indicators = [
            "concetto di",
            "significa",
            "definisce",
            "rappresenta",
            "si riferisce a",
            "è un",
            "è una"
        ]
        
        # Cerca concetti nel contenuto
        for indicator in concept_indicators:
            if indicator in content.lower():
                # Trova l'indice dell'indicatore
                start_idx = content.lower().find(indicator) + len(indicator)
                
                # Cerca la fine del concetto (punto, virgola o fine stringa)
                end_idx = min(x for x in [
                    content.find(".", start_idx),
                    content.find(",", start_idx),
                    content.find("\n", start_idx),
                    len(content)
                ] if x != -1)
                
                # Estrai il concetto
                concept = content[start_idx:end_idx].strip()
                
                # Se il concetto è seguito da una spiegazione
                explanation = ""
                if end_idx < len(content) and content[end_idx] == ":":
                    explanation_end = content.find(".", end_idx)
                    if explanation_end != -1:
                        explanation = content[end_idx + 1:explanation_end].strip()
                
                # Aggiungi al dizionario
                if concept and len(concept) > 2:  # Ignora concetti troppo brevi
                    concepts[concept] = {
                        "explanation": explanation,
                        "confidence": 0.7,  # Confidenza default
                        "source": "text_analysis"
                    }
        
        return concepts

    def _extract_concept_from_sentence(self, content: str) -> dict:
        """Estrae i concetti dalla frase"""
        concepts = {}
        
        # Lista di parole chiave che indicano concetti
        concept_indicators = [
            "il concetto di",
            "il termine",
            "la nozione di",
            "la definizione di"
        ]
        
        # Cerca concetti nel contenuto
        for indicator in concept_indicators:
            if indicator in content.lower():
                # Trova l'indice dell'indicatore
                start_idx = content.lower().find(indicator) + len(indicator)
                
                # Cerca la fine del concetto (punto, virgola o fine stringa)
                end_idx = min(x for x in [
                    content.find(".", start_idx),
                    content.find(",", start_idx),
                    content.find("\n", start_idx),
                    len(content)
                ] if x != -1)
                
                # Estrai il concetto
                concept = content[start_idx:end_idx].strip()
                
                # Aggiungi al dizionario
                if concept and len(concept) > 2:  # Ignora concetti troppo brevi
                    concepts[concept] = {
                        "explanation": "",
                        "confidence": 0.5,  # Confidenza default
                        "source": "text_analysis"
                    }
        
        return concepts

    def _analyze_personality_changes(self) -> Dict[str, float]:
        """Analizza i cambiamenti nella personalità"""
        changes = {}
        
        # Confronta i valori attuali con quelli precedenti
        for trait, value in self.core.personality_traits.items():
            # Per ora restituiamo solo i valori attuali
            # In futuro potremmo confrontarli con i valori precedenti
            changes[trait] = value
            
        return changes

class KnowledgeMemory:
    def __init__(self):
        self.concepts = {}

    def has_concept(self, concept: str) -> bool:
        return concept in self.concepts

    def get_concept(self, concept: str) -> Dict[str, Any]:
        return self.concepts.get(concept, {})

    def add_concept(self, concept: str, info: Dict[str, Any]) -> None:
        self.concepts[concept] = info

    def update_concept(self, concept: str, info: Dict[str, Any]) -> None:
        if concept in self.concepts:
            self.concepts[concept].update(info)

    def get_all_concepts(self) -> List[str]:
        return list(self.concepts.keys())

class PersonalityCoalescence:
    """
    Gestisce la personalità di ALLMA e la sua evoluzione nel tempo
    """
    
    def __init__(self):
        """Inizializza la personalità"""
        self.traits = {
            'openness': 0.8,  # Apertura a nuove esperienze
            'conscientiousness': 0.9,  # Coscienziosità
            'extraversion': 0.6,  # Estroversione
            'agreeableness': 0.8,  # Gradevolezza
            'neuroticism': 0.3  # Neuroticismo
        }
        
        self.interaction_style = {
            'formality': 0.7,  # Livello di formalità
            'empathy': 0.8,  # Livello di empatia
            'enthusiasm': 0.6,  # Livello di entusiasmo
            'detail_orientation': 0.9  # Attenzione ai dettagli
        }
        
    def adapt_personality(self, user_style: dict) -> None:
        """
        Adatta la personalità in base allo stile dell'utente
        
        Args:
            user_style: Dizionario con lo stile dell'utente
        """
        # Adatta gradualmente i tratti
        for trait, value in user_style.items():
            if trait in self.traits:
                # Adattamento graduale (20% verso lo stile dell'utente)
                self.traits[trait] = (
                    0.8 * self.traits[trait] + 
                    0.2 * value
                )
                
    def get_interaction_style(self) -> dict:
        """
        Ottiene lo stile di interazione corrente
        
        Returns:
            dict: Stile di interazione
        """
        return self.interaction_style.copy()
        
    def update_interaction_style(self, feedback: dict) -> None:
        """
        Aggiorna lo stile di interazione in base al feedback
        
        Args:
            feedback: Dizionario con il feedback sull'interazione
        """
        for style, value in feedback.items():
            if style in self.interaction_style:
                # Aggiornamento graduale (10% verso il feedback)
                self.interaction_style[style] = (
                    0.9 * self.interaction_style[style] + 
                    0.1 * value
                )
