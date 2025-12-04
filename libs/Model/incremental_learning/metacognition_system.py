from enum import Enum
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from collections import deque

@dataclass(frozen=True)
class CognitiveStrategy:
    """Rappresenta una strategia cognitiva"""
    name: str
    complexity: str  # 'low', 'medium', 'high'
    effectiveness: float  # 0-1
    description: str = ""
    
    def __hash__(self):
        """Rende la classe hashable per poterla usare come chiave del dizionario"""
        return hash((self.name, self.complexity, self.effectiveness, self.description))
        
    @classmethod
    def create_default_strategies(cls) -> List['CognitiveStrategy']:
        """Crea un set di strategie cognitive predefinite"""
        return [
            cls(name="SURFACE_READING",
                complexity="low",
                effectiveness=0.3,
                description="Lettura superficiale del materiale"),
                
            cls(name="ACTIVE_RECALL",
                complexity="medium",
                effectiveness=0.6,
                description="Richiamo attivo delle informazioni"),
                
            cls(name="ELABORATIVE_REHEARSAL",
                complexity="medium",
                effectiveness=0.7,
                description="Ripetizione elaborativa con collegamenti"),
                
            cls(name="DEEP_ANALYSIS",
                complexity="high",
                effectiveness=0.8,
                description="Analisi profonda con sintesi e valutazione")
        ]

class MetaCognitiveState(Enum):
    """Stati metacognitivi del sistema"""
    MONITORING = "monitoring"
    ANALYZING = "analyzing"
    ADAPTING = "adapting"
    REFLECTING = "reflecting"
    PLANNING = "planning"

@dataclass
class MetaCognitiveInsight:
    """Rappresenta un'intuizione metacognitiva"""
    state: MetaCognitiveState
    strategy: CognitiveStrategy
    confidence: float
    effectiveness: float
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __lt__(self, other):
        if not isinstance(other, MetaCognitiveInsight):
            return NotImplemented
        return self.effectiveness < other.effectiveness

@dataclass
class LearningProgress:
    """Traccia il progresso dell'apprendimento"""
    topic: str
    understanding_level: float = 0.0
    total_time: float = 0.0
    sessions: int = 0

class MetaCognitionSystem:
    """Sistema di Meta-Cognizione per il monitoraggio e l'ottimizzazione dei processi cognitivi"""
    
    def __init__(self):
        """Inizializza il sistema metacognitivo"""
        self.strategies = CognitiveStrategy.create_default_strategies()
        self.strategy_effectiveness: Dict[CognitiveStrategy, float] = {}
        self.insights = deque(maxlen=100)
        self.learning_history: List[Dict] = []
        self.current_state = MetaCognitiveState.MONITORING
        self.learning_progress = {}
        self.confidence_threshold = 0.7
        self.adaptation_rate = 0.1
        
        # Inizializza l'efficacia delle strategie
        for strategy in self.strategies:
            self.strategy_effectiveness[strategy] = strategy.effectiveness
        
    def monitor_cognitive_process(self, process_data: Dict[str, Any]) -> MetaCognitiveInsight:
        """Monitora un processo cognitivo e genera insight"""
        # Analizza il processo
        strategy = self._select_best_strategy(process_data)
        confidence = self._evaluate_confidence(process_data)
        effectiveness = self._evaluate_effectiveness(process_data)
        
        # Genera insight
        insight = MetaCognitiveInsight(
            state=self.current_state,
            strategy=strategy,
            confidence=confidence,
            effectiveness=effectiveness,
            description=self._generate_insight_description(process_data)
        )
        
        # Aggiorna la coda degli insight
        self.insights.append(insight)
            
        return insight
        
    def adapt_strategy(self, feedback: float) -> CognitiveStrategy:
        """Adatta la strategia in base al feedback"""
        self.current_state = MetaCognitiveState.ADAPTING
        
        # Aggiorna l'efficacia delle strategie
        for strategy in self.strategies:
            current_effectiveness = self.strategy_effectiveness[strategy]
            self.strategy_effectiveness[strategy] = (
                current_effectiveness * (1 - self.adaptation_rate) +
                feedback * self.adaptation_rate
            )
            
        # Seleziona la migliore strategia
        best_strategy = max(
            self.strategy_effectiveness.items(),
            key=lambda x: x[1]
        )[0]
        
        return best_strategy
        
    def reflect_on_learning(self, topic: str, time_spent: float, effectiveness: float) -> None:
        """Riflette sul processo di apprendimento"""
        if topic not in self.learning_progress:
            self.learning_progress[topic] = LearningProgress(
                topic=topic,
                understanding_level=0.0,
                total_time=0.0,
                sessions=0
            )
            
        progress = self.learning_progress[topic]
        
        # Aggiorna il progresso
        progress.total_time += time_spent
        progress.sessions += 1
        
        # Calcola il nuovo livello di comprensione
        base_increase = effectiveness * 0.2
        time_factor = min(time_spent / 1.5, 1.0)
        diminishing_returns = 1.0 / (1.0 + progress.sessions * 0.05)
        
        increase = base_increase * time_factor * diminishing_returns
        progress.understanding_level = min(
            progress.understanding_level + increase,
            1.0
        )
        
        # Aggiorna gli insight
        if effectiveness > 0.5:
            self._generate_insight(topic, progress)
            
        # Trasferimento di conoscenza tra domini correlati
        self._transfer_knowledge(topic, increase)
        
    def _transfer_knowledge(self, source_topic: str, base_increase: float) -> None:
        """Trasferisce la conoscenza tra domini correlati"""
        # Definisce le relazioni tra domini con pesi di trasferimento
        domain_relations = {
            "programming": {
                "algorithms": 0.8,
                "data_structures": 0.9,
                "software_engineering": 0.7,
                "machine_learning": 0.5
            },
            "algorithms": {
                "programming": 0.8,
                "math": 0.7,
                "optimization": 0.8,
                "machine_learning": 0.6
            },
            "math": {
                "algorithms": 0.7,
                "physics": 0.8,
                "statistics": 0.8,
                "machine_learning": 0.6
            },
            "physics": {
                "math": 0.8,
                "engineering": 0.7,
                "statistics": 0.5
            },
            "data_structures": {
                "programming": 0.9,
                "algorithms": 0.8,
                "optimization": 0.6
            },
            "machine_learning": {
                "math": 0.7,
                "programming": 0.6,
                "statistics": 0.8,
                "algorithms": 0.7
            }
        }
        
        # Trova il dominio base e i suoi sotto-domini
        base_domain = source_topic.split("_")[0].lower()
        sub_domain = "_".join(source_topic.split("_")[1:]) if "_" in source_topic else ""
        
        if base_domain in domain_relations:
            related_domains = domain_relations[base_domain]
            source_level = self.get_understanding_level(source_topic)
            
            # Trasferisci la conoscenza ai domini correlati
            for target_domain, transfer_weight in related_domains.items():
                # Costruisci il topic target
                target_topic = f"{target_domain}_{sub_domain}" if sub_domain else target_domain
                
                # Calcola l'incremento di conoscenza
                target_level = self.get_understanding_level(target_topic)
                knowledge_gap = source_level - target_level
                
                if knowledge_gap > 0:
                    # L'incremento è proporzionale al gap di conoscenza e al peso di trasferimento
                    transfer_increase = (
                        base_increase * 
                        transfer_weight * 
                        (knowledge_gap / source_level) *
                        2.0  # Fattore di boost per aumentare l'effetto del trasferimento
                    )
                    
                    # Inizializza il progresso se non esiste
                    if target_topic not in self.learning_progress:
                        self.learning_progress[target_topic] = LearningProgress(
                            topic=target_topic,
                            understanding_level=0.0,
                            total_time=0.0,
                            sessions=0
                        )
                    
                    # Aggiorna il livello di comprensione
                    progress = self.learning_progress[target_topic]
                    progress.understanding_level = min(
                        progress.understanding_level + transfer_increase,
                        source_level  # Non superare il livello della fonte
                    )
                    
    def plan_learning_strategy(self, topic: str) -> Dict[str, Any]:
        """Pianifica una strategia di apprendimento"""
        self.current_state = MetaCognitiveState.PLANNING
        
        # Analizza il progresso precedente
        progress = self.learning_progress.get(topic)
        if progress:
            understanding_gap = 1.0 - progress.understanding_level
            time_efficiency = progress.understanding_level / (progress.total_time + 1e-6)
        else:
            understanding_gap = 1.0
            time_efficiency = 0.0
            
        # Seleziona le strategie più efficaci
        sorted_strategies = sorted(
            self.strategy_effectiveness.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            "topic": topic,
            "understanding_gap": understanding_gap,
            "time_efficiency": time_efficiency,
            "recommended_strategies": [s[0] for s in sorted_strategies[:2]],
            "estimated_time": understanding_gap / (time_efficiency + 1e-6)
        }
        
    def get_insights(self, n: int = 5) -> List[MetaCognitiveInsight]:
        """Ottiene gli n insight più significativi"""
        insights = list(self.insights)[-n:]
        return insights
        
    def get_understanding_level(self, topic: str) -> float:
        """Ottiene il livello di comprensione per un dato topic"""
        if topic not in self.learning_progress:
            return 0.0
        return self.learning_progress[topic].understanding_level
        
    def _select_best_strategy(self, process_data: Dict[str, Any]) -> CognitiveStrategy:
        """Seleziona la migliore strategia per il processo corrente"""
        # Implementa la logica di selezione della strategia
        if process_data.get("complexity", 0) > 0.7:
            return next(s for s in self.strategies if s.name == "DEEP_ANALYSIS")
        elif process_data.get("time_pressure", 0) > 0.7:
            return next(s for s in self.strategies if s.name == "SURFACE_READING")
        else:
            return next(s for s in self.strategies if s.name == "ACTIVE_RECALL")
            
    def _evaluate_confidence(self, process_data: Dict[str, Any]) -> float:
        """Valuta la confidenza nel processo cognitivo"""
        # Calcola la confidenza basata su vari fattori
        factors = [
            process_data.get("accuracy", 0.5),
            process_data.get("consistency", 0.5),
            process_data.get("completeness", 0.5)
        ]
        return round(sum(factors) / len(factors), 2)
        
    def _evaluate_effectiveness(self, process_data: Dict[str, Any]) -> float:
        """Valuta l'efficacia del processo cognitivo"""
        # Calcola l'efficacia basata su vari fattori
        accuracy = process_data.get("accuracy", 0.5)
        speed = process_data.get("speed", 0.5)
        resource_usage = process_data.get("resource_usage", 0.5)
        
        return (accuracy * 0.5 + speed * 0.3 + (1 - resource_usage) * 0.2)
        
    def _generate_insight_description(self, process_data: Dict[str, Any]) -> str:
        """Genera una descrizione dell'insight"""
        strategy = self._select_best_strategy(process_data)
        confidence = self._evaluate_confidence(process_data)
        effectiveness = self._evaluate_effectiveness(process_data)
        
        return (
            f"Process analyzed with {strategy.name} strategy. "
            f"Confidence: {confidence:.2f}, Effectiveness: {effectiveness:.2f}. "
            f"Current state: {self.current_state.value}"
        )
        
    def _generate_insight(self, topic: str, progress: LearningProgress) -> None:
        """Genera un insight"""
        insight = MetaCognitiveInsight(
            state=self.current_state,
            strategy=next(s for s in self.strategies if s.name == "ACTIVE_RECALL"),
            confidence=0.8,
            effectiveness=progress.understanding_level,
            description=f"Progresso nell'apprendimento del topic {topic}: {progress.understanding_level:.2f}"
        )
        
        # Aggiorna la coda degli insight
        self.insights.append(insight)

    def select_strategy(self, complexity: str = 'medium') -> CognitiveStrategy:
        """
        Seleziona una strategia cognitiva in base alla complessità richiesta
        
        Args:
            complexity: Livello di complessità ('low', 'medium', 'high')
            
        Returns:
            Strategia cognitiva appropriata
        """
        available_strategies = {
            'low': [s for s in self.strategies if s.complexity == 'low'],
            'medium': [s for s in self.strategies if s.complexity == 'medium'],
            'high': [s for s in self.strategies if s.complexity == 'high']
        }
        
        # Se non ci sono strategie del livello richiesto, usa il livello più vicino
        if not available_strategies[complexity]:
            if complexity == 'high':
                complexity = 'medium'
            elif complexity == 'low':
                complexity = 'medium'
                
        # Se ancora non ci sono strategie disponibili, usa una strategia di default
        if not available_strategies[complexity]:
            return next(s for s in self.strategies if s.name == "ACTIVE_RECALL")
            
        # Seleziona la strategia più efficace del livello richiesto
        return max(available_strategies[complexity],
                  key=lambda s: self.strategy_effectiveness[s])
