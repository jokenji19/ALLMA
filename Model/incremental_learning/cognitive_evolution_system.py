"""
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending - ALLMA (Adaptive Learning and Language Model Architecture)

This file implements the core Cognitive Evolution System of ALLMA.
Author: Cristof Bano
Created: January 2025

This file contains proprietary and patent-pending technologies including:
- Adaptive learning algorithms
- Dynamic knowledge acquisition
- Pattern recognition systems
- Memory optimization methods
"""

from typing import Dict, List, Optional, Tuple, Set, Any
import numpy as np
from dataclasses import dataclass
import json
from datetime import datetime, timedelta
from enum import Enum, auto
from collections import defaultdict
import math
import random
import logging

class CognitiveStage(Enum):
    """Stadi di sviluppo cognitivo"""
    BASIC = auto()           # Comprensione base e risposte semplici
    INTERMEDIATE = auto()    # Analisi più profonda e connessioni semplici
    ADVANCED = auto()        # Pensiero astratto e connessioni complesse
    EXPERT = auto()          # Metacognizione e apprendimento autonomo
    MASTER = auto()          # Innovazione e sintesi creativa

@dataclass
class CognitiveAbility:
    """Rappresenta una singola abilità cognitiva"""
    name: str
    description: str
    current_level: float  # 0.0 - 1.0
    stage_requirement: CognitiveStage
    dependencies: Set[str]  # Altre abilità necessarie
    experience_points: float
    last_used: datetime
    usage_count: int
    mastery_threshold: float = 0.8

class AbilityCategory(Enum):
    """Categorie di abilità cognitive"""
    PERCEPTION = "perception"
    ATTENTION = "attention"
    MEMORY = "memory"
    LANGUAGE = "language"
    REASONING = "reasoning"
    METACOGNITION = "metacognition"
    CREATIVITY = "creativity"
    SOCIAL = "social"
    EMOTIONAL = "emotional"
    LEARNING = "learning"

@dataclass
class EvolutionResult:
    """Rappresenta il risultato di un'evoluzione cognitiva"""
    improved_abilities: List[str]
    new_connections: List[str]
    cognitive_level: float

class CognitiveEvolutionSystem:
    """Sistema che simula l'evoluzione delle capacità cognitive attraverso l'esperienza"""
    
    def __init__(self):
        # Inizializza tutte le capacità a zero
        self.cognitive_abilities = {
            "perception": 0.0,
            "memory": 0.0,
            "learning": 0.0,
            "reasoning": 0.0,
            "creativity": 0.0,
            "problem_solving": 0.0
        }
        
        # Memoria delle esperienze per l'apprendimento incrementale
        self.experience_memory = []
        self.learning_threshold = 0.01  # Ridotta da 0.1 a 0.01
        self.logger = logging.getLogger(__name__)
        self.skills = {}
        self.knowledge = {}
        self.processed_experiences = []
        
    def _get_ability_category(self, experience: Dict) -> str:
        """Determina quale capacità cognitiva viene stimolata dall'esperienza"""
        # Analisi del contesto per determinare la capacità più rilevante
        context = experience.get("input", "").lower()
        
        # Parole chiave per ogni abilità, ordinate per specificità
        ability_keywords = {
            "problem_solving": ["risolvi questo", "risolvi il", "risolvere", "problema", "soluzione"],
            "memory": ["memorizza", "memorizzare", "ricorda", "ricordare", "memoria", "ripeti", "ripetere"],
            "perception": ["osserva", "osservare", "nota", "notare", "vedi", "vedere", "guarda", "guardare"],
            "learning": ["studia", "studiare", "impara", "imparare", "comprendi", "comprendere"],
            "reasoning": ["analizza", "analizzare", "ragiona", "ragionare", "deduci", "dedurre"],
            "creativity": ["immagina", "immaginare", "crea", "creare", "inventa", "inventare"]
        }
        
        # Cerca le parole chiave nel contesto
        for ability, keywords in ability_keywords.items():
            if any(word in context for word in keywords):
                return ability
        
        # Se non trova corrispondenze specifiche, usa l'apprendimento generale
        return "learning"
        
    def process_experience(self, experience: Dict, context: Dict = None) -> float:
        """Elabora una nuova esperienza e aggiorna il sistema cognitivo"""
        if context is None:
            context = {}
            
        # Calcola il livello cognitivo basato sull'esperienza
        cognitive_level = self._calculate_cognitive_level(experience)
        
        # Aggiorna il sistema con la nuova esperienza
        self.processed_experiences.append({
            'experience': experience,
            'context': context,
            'cognitive_level': cognitive_level,
            'timestamp': datetime.now().isoformat()
        })
        
        # Estrai concetti chiave dall'esperienza
        concepts = self._extract_concepts(experience)
        
        # Aggiorna la knowledge base con i nuovi concetti
        if hasattr(self, 'knowledge_base'):
            for concept in concepts:
                self.knowledge_base.add_knowledge({
                    'type': 'concept',
                    'content': concept,
                    'source': 'cognitive_system',
                    'confidence': cognitive_level,
                    'context': context
                })
        
        return cognitive_level
        
    def _extract_concepts(self, experience: Dict) -> List[str]:
        """Estrae concetti chiave dall'esperienza"""
        concepts = []
        
        # Estrai concetti dal testo se presente
        if 'text' in experience:
            # Parole chiave per concetti cognitivi
            cognitive_keywords = [
                'imparare', 'capire', 'analizzare', 'pensare',
                'ragionare', 'dedurre', 'concludere', 'ipotizzare'
            ]
            
            text = experience['text'].lower()
            concepts.extend([word for word in cognitive_keywords if word in text])
            
        # Aggiungi concetti dal contesto
        if 'topics' in experience:
            concepts.extend(experience['topics'])
            
        return list(set(concepts))  # Rimuovi duplicati
        
    def _calculate_cognitive_level(self, experience: Dict) -> float:
        """Calcola il livello cognitivo basato sull'esperienza"""
        # Determina quale capacità viene stimolata
        ability = self._get_ability_category(experience)
        
        # Calcola l'incremento in base all'esperienza
        increment = max(0.01, min(0.1, len(experience["input"].split()) / 100.0))
        
        # Aggiorna l'abilità
        current_level = self.cognitive_abilities[ability]
        new_level = min(1.0, current_level + increment)
        self.cognitive_abilities[ability] = new_level
        
        # Effetto di trasferimento dell'apprendimento
        for other_ability in self.cognitive_abilities:
            if other_ability != ability:
                transfer_rate = self._calculate_transfer_rate(ability, other_ability)
                self.cognitive_abilities[other_ability] = min(
                    1.0,
                    self.cognitive_abilities[other_ability] + (increment * transfer_rate)
                )
                
        # Restituisce il livello cognitivo medio
        return sum(self.cognitive_abilities.values()) / len(self.cognitive_abilities)
            
    def _calculate_transfer_rate(self, source_ability: str, target_ability: str) -> float:
        """Calcola il tasso di trasferimento tra due capacità cognitive"""
        # Definisce le relazioni naturali tra le capacità
        ability_relationships = {
            "perception": {"memory": 0.3, "learning": 0.2},
            "memory": {"learning": 0.3, "reasoning": 0.2},
            "learning": {"reasoning": 0.3, "problem_solving": 0.2},
            "reasoning": {"problem_solving": 0.3, "creativity": 0.2},
            "creativity": {"problem_solving": 0.3, "perception": 0.2},
            "problem_solving": {"reasoning": 0.3, "creativity": 0.2}
        }
        
        # Il trasferimento è più forte tra capacità naturalmente correlate
        if source_ability in ability_relationships and target_ability in ability_relationships[source_ability]:
            return ability_relationships[source_ability][target_ability]
        
        # Trasferimento minimo tra capacità non direttamente correlate
        return 0.1

    def get_state(self) -> Dict[str, float]:
        """Restituisce lo stato corrente del sistema cognitivo"""
        return {k: float(v) for k, v in self.cognitive_abilities.items()}
        
    def learn(self, domain: str, difficulty: float, success_rate: float) -> dict:
        """
        Apprende da una nuova esperienza in un dominio
        
        Args:
            domain: Dominio di apprendimento
            difficulty: Difficoltà dell'esperienza (0-1)
            success_rate: Tasso di successo nell'esperienza (0-1)
            
        Returns:
            Dizionario con i risultati dell'apprendimento
            
        Raises:
            ValueError: Se difficulty o success_rate non sono nell'intervallo [0,1]
        """
        # Validazione input
        if not 0.0 <= difficulty <= 1.0:
            raise ValueError("La difficoltà deve essere tra 0.0 e 1.0")
            
        if not 0.0 <= success_rate <= 1.0:
            raise ValueError("Il tasso di successo deve essere tra 0.0 e 1.0")
            
        # Inizializza il dominio se non esiste
        if domain not in self.knowledge:
            self.knowledge[domain] = {
                "difficulty": difficulty,
                "success_rate": success_rate,
                "experiences": 0,
                "last_update": datetime.now()
            }
            
        # Aggiorna le statistiche del dominio
        domain_stats = self.knowledge[domain]
        is_first_experience = domain_stats["experiences"] == 0
        domain_stats["experiences"] += 1
        
        # Aggiorna la difficoltà media
        if is_first_experience:
            domain_stats["difficulty"] = difficulty
        else:
            domain_stats["difficulty"] = (
                domain_stats["difficulty"] * 0.7 + 
                difficulty * 0.3
            )
        
        # Aggiorna il tasso di successo
        if is_first_experience:
            domain_stats["success_rate"] = success_rate
        else:
            domain_stats["success_rate"] = (
                domain_stats["success_rate"] * 0.7 +
                success_rate * 0.3
            )
        
        domain_stats["last_update"] = datetime.now()
        
        # Verifica se c'è stato un apprendimento significativo
        learning_occurred = (
            (domain_stats["experiences"] > 3 and domain_stats["success_rate"] > 0.6) or
            (domain_stats["success_rate"] >= 0.8 and difficulty >= 0.6)
        )
        
        return {
            "domain": domain,
            "learning_occurred": learning_occurred,
            "current_stats": domain_stats
        }

    def check_transfer(self, domain1: str, domain2: str) -> float:
        """
        Verifica il trasferimento di conoscenza tra due domini
        
        Args:
            domain1: Primo dominio
            domain2: Secondo dominio
            
        Returns:
            Valore del trasferimento (0-1)
        """
        # Definisci relazioni tra domini
        domain_relations = {
            "matematica": {"fisica": 0.8, "chimica": 0.6, "informatica": 0.7},
            "fisica": {"matematica": 0.8, "chimica": 0.7, "ingegneria": 0.6},
            "chimica": {"fisica": 0.7, "biologia": 0.6, "matematica": 0.6},
            "biologia": {"chimica": 0.6, "medicina": 0.7},
            "informatica": {"matematica": 0.7, "ingegneria": 0.6},
            "ingegneria": {"fisica": 0.6, "matematica": 0.6, "informatica": 0.6}
        }
        
        # Se entrambi i domini sono nel knowledge, usa la logica esistente
        if domain1 in self.knowledge and domain2 in self.knowledge:
            k1 = self.knowledge[domain1]
            k2 = self.knowledge[domain2]
            
            # Calcola similarità basata su difficoltà e tasso di successo
            difficulty_similarity = 1.0 - abs(k1["difficulty"] - k2["difficulty"])
            success_similarity = 1.0 - abs(k1["success_rate"] - k2["success_rate"])
            
            # Peso l'importanza delle esperienze
            exp_weight = min(k1["experiences"], k2["experiences"]) / max(k1["experiences"], k2["experiences"])
            
            # Calcola il punteggio base di trasferimento
            base_transfer = (difficulty_similarity * 0.4 + 
                           success_similarity * 0.4 + 
                           exp_weight * 0.2)
                       
            # Applica un bonus se entrambi i domini hanno avuto successo
            if k1["success_rate"] > 0.7 and k2["success_rate"] > 0.7:
                base_transfer *= 1.2
                
            # Applica un bonus se c'è stata molta pratica
            if k1["experiences"] > 5 and k2["experiences"] > 5:
                base_transfer *= 1.1
        
        # Se almeno uno dei domini è nel knowledge, usa la relazione semantica
        elif domain1 in self.knowledge or domain2 in self.knowledge:
            source_domain = domain1 if domain1 in self.knowledge else domain2
            target_domain = domain2 if domain1 in self.knowledge else domain1
            
            # Se esiste una relazione diretta tra i domini
            if source_domain in domain_relations and target_domain in domain_relations[source_domain]:
                base_transfer = domain_relations[source_domain][target_domain]
                
                # Applica un malus perché il dominio target non è stato esplorato
                base_transfer *= 0.8
            else:
                # Se non c'è una relazione diretta, usa un valore base basso
                base_transfer = 0.2
        
        # Se nessuno dei domini è nel knowledge, usa solo la relazione semantica
        else:
            # Se esiste una relazione diretta tra i domini
            if domain1 in domain_relations and domain2 in domain_relations[domain1]:
                base_transfer = domain_relations[domain1][domain2] * 0.6  # Malus più alto
            else:
                # Se non c'è una relazione diretta, usa un valore base molto basso
                base_transfer = 0.1
            
        return max(0.1, min(1.0, base_transfer))  # Garantisce un minimo di trasferimento

    def _update_skill_network(self, skill: str) -> None:
        # Aggiorna la rete di relazioni tra le abilità
        pass
        
    def _calculate_skill_similarity(self, target_skill: str, source_skill: str) -> float:
        # Calcola la similarità tra due abilità
        return 0.5  # Valore di default per la similarità
