from typing import Dict, List, Optional, Tuple, Set, Any, Union
import numpy as np
from dataclasses import dataclass
import json
from datetime import datetime, timedelta
from enum import Enum, auto
from collections import defaultdict
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    F = None
    TORCH_AVAILABLE = False
import math
import time

@dataclass
class LearningInsight:
    """Rappresenta un'intuizione sul processo di apprendimento"""
    system_name: str
    metric_name: str
    value: float
    timestamp: float
    confidence: float

@dataclass
class SystemState:
    """Rappresenta lo stato di un sistema"""
    performance_metrics: Dict[str, float]
    resource_usage: Dict[str, float]
    error_rate: float
    last_update: float

@dataclass
class LearningStrategy:
    """Rappresenta una strategia di apprendimento"""
    name: str
    parameters: Dict
    success_rate: float
    usage_count: int
    last_used: datetime
    effectiveness_history: List[float]
    context_types: Set[str]
    preferred_contexts: Set[str]
    optimal_difficulty: float
    experience_points: float
    current_level: int
    
    def __hash__(self):
        return hash(self.name)
        
    def __eq__(self, other):
        if not isinstance(other, LearningStrategy):
            return NotImplemented
        return self.name == other.name

@dataclass
class LearningExperience:
    """Rappresenta un'esperienza di apprendimento"""
    content: str
    strategy_used: str
    success_level: float
    time_taken: float
    context: Dict
    timestamp: datetime
    feedback: Optional[str]
    difficulty: float

class MetaCognitionLevel(Enum):
    """Livelli di metacognizione"""
    MONITORING = auto()      # Monitoraggio base dell'apprendimento
    EVALUATION = auto()      # Valutazione delle strategie
    ADAPTATION = auto()      # Adattamento delle strategie
    INNOVATION = auto()      # Creazione di nuove strategie
    OPTIMIZATION = auto()    # Ottimizzazione globale

class StrategyOptimizer:
    """Ottimizza le strategie di apprendimento usando tecniche di ML"""
    def __init__(self, input_dim: int = 10):
        self.input_dim = input_dim
        if TORCH_AVAILABLE:
            self.model = nn.Sequential(
                nn.Linear(input_dim, 32),
                nn.ReLU(),
                nn.Linear(32, 16),
                nn.ReLU(),
                nn.Linear(16, 1),
                nn.Sigmoid()
            )
            self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        else:
            self.model = None
            self.optimizer = None
        
    def encode_strategy(self, strategy: LearningStrategy) -> Any:
        """Codifica una strategia in un tensore"""
        if not TORCH_AVAILABLE:
            return None

        features = [
            strategy.success_rate,
            strategy.usage_count / 100,  # Normalizzato
            len(strategy.effectiveness_history) / 100,  # Normalizzato
            np.mean(strategy.effectiveness_history) if strategy.effectiveness_history else 0,
            np.std(strategy.effectiveness_history) if strategy.effectiveness_history else 0,
        ] + list(strategy.parameters.values())
        
        # Padding se necessario
        while len(features) < self.input_dim:
            features.append(0.0)
            
        return torch.tensor(features, dtype=torch.float32)
        
    def train(self, strategies: List[LearningStrategy], target_scores: List[float]):
        """Addestra il modello sulle strategie esistenti"""
        if not TORCH_AVAILABLE or self.model is None:
            return 0.0

        X = torch.stack([self.encode_strategy(s) for s in strategies])
        y = torch.tensor(target_scores, dtype=torch.float32)
        
        self.optimizer.zero_grad()
        predictions = self.model(X).squeeze()
        loss = F.mse_loss(predictions, y)
        loss.backward()
        self.optimizer.step()
        
        return loss.item()
        
    def predict_effectiveness(self, strategy: LearningStrategy) -> float:
        """Predice l'efficacia di una strategia"""
        if not TORCH_AVAILABLE or self.model is None:
            return 0.5 # Default fallback

        with torch.no_grad():
            X = self.encode_strategy(strategy).unsqueeze(0)
            return self.model(X).item()

class MetaLearningSystem:
    """Sistema principale per il meta-learning"""
    def __init__(self):
        self.strategies: Dict[str, LearningStrategy] = {}
        self.experiences: List[LearningExperience] = []
        self.metacognition_level = MetaCognitionLevel.MONITORING
        self.strategy_optimizer = StrategyOptimizer()
        self.reflection_history: List[Dict] = []
        self.registered_systems = {}
        self.system_states = {}
        self.learning_history = []
        self.insights = []
        self._last_strategy_time = time.time()  # Aggiungo questo campo
        
        self._initialize_strategies()
        
    def _initialize_strategies(self):
        """Inizializza le strategie di base"""
        self.strategies = {
            "elaboration": LearningStrategy(
                name="elaboration",
                parameters={"depth": 0.5, "connections": 0.6},
                success_rate=0.5,
                usage_count=0,
                last_used=datetime.now(),
                effectiveness_history=[],
                context_types={"understanding", "analysis"},
                preferred_contexts={"understanding", "python", "programming"},
                optimal_difficulty=0.5,
                experience_points=0.0,
                current_level=1
            ),
            "repetition": LearningStrategy(
                name="repetition",
                parameters={"frequency": 0.7, "interval": 0.5},
                success_rate=0.5,
                usage_count=0,
                last_used=datetime.now(),
                effectiveness_history=[],
                context_types={"memorization", "practice"},
                preferred_contexts={"practice", "python", "programming"},
                optimal_difficulty=0.4,
                experience_points=0.0,
                current_level=1
            ),
            "reflection": LearningStrategy(
                name="reflection",
                parameters={"depth": 0.6, "metacognition": 0.8},
                success_rate=0.5,
                usage_count=0,
                last_used=datetime.now(),
                effectiveness_history=[],
                context_types={"evaluation", "synthesis"},
                preferred_contexts={"evaluation", "python", "programming"},
                optimal_difficulty=0.6,
                experience_points=0.0,
                current_level=1
            )
        }
        
    def learn(self, content: str, context: Union[Dict, Any], difficulty: float = 0.5) -> Dict:
        """Apprende usando la strategia più adatta"""
        if not content or not isinstance(content, str):
            raise ValueError("Input non valido: il contenuto deve essere una stringa non vuota")
            
        if not isinstance(difficulty, (int, float)) or difficulty < 0 or difficulty > 1:
            raise ValueError("Input non valido: la difficoltà deve essere un numero tra 0 e 1")
            
        if context is None:
            raise ValueError("Input non valido: il contesto non può essere None")
            
        # Seleziona la strategia migliore
        strategy = self._select_strategy(context)
        
        # Calcola il successo dell'apprendimento
        success = self._calculate_success(strategy, difficulty)
        
        # Aggiorna il livello della strategia
        self._update_strategy_level(strategy)
        
        # Registra l'esperienza
        experience = LearningExperience(
            content=content,
            strategy_used=strategy.name,
            success_level=success,
            time_taken=0.0,  # TODO: implementare il tracciamento del tempo
            context=context.__dict__ if hasattr(context, '__dict__') else dict(context) if isinstance(context, dict) else {},
            timestamp=datetime.now(),
            feedback=None,
            difficulty=difficulty
        )
        self.experiences.append(experience)
        
        # Rifletti sull'apprendimento
        self._reflect_on_learning()
        
        return {
            'success': success,
            'strategy': strategy.name,
            'level': strategy.current_level
        }
        
    def _calculate_success(self, strategy: LearningStrategy, difficulty: float) -> float:
        """Calcola il successo dell'apprendimento"""
        # Fattori che influenzano il successo
        strategy_factor = strategy.success_rate
        experience_factor = min(1.0, strategy.usage_count / 15)  
        level_factor = strategy.current_level * 0.2  
        
        # Calcola il successo base (ridotto)
        base_success = 0.4 + (strategy_factor * 0.3) + (experience_factor * 0.4) + level_factor
        
        # Modifica in base alla difficoltà (aumentato l'impatto)
        final_success = base_success * (1.0 - difficulty * 0.3)
        
        # Assicura che sia nell'intervallo [0, 1]
        return max(0.3, min(0.95, final_success))
        
    def _select_strategy(self, context: Union[Dict, Any]) -> LearningStrategy:
        """Seleziona la strategia migliore per il contesto"""
        # Se il contesto è un dizionario, usalo direttamente
        if isinstance(context, dict):
            context_dict = context
        # Altrimenti, prova a convertirlo in dizionario
        else:
            try:
                context_dict = context.__dict__ if hasattr(context, '__dict__') else {}
            except:
                context_dict = {}
        
        # Se c'è una strategia preferita nel contesto e la strategia esiste, usala
        if "preferred_strategy" in context_dict and context_dict["preferred_strategy"] in self.strategies:
            return self.strategies[context_dict["preferred_strategy"]]
            
        # Altrimenti, scegli la strategia con il punteggio più alto
        best_strategy = None
        best_score = -1
        
        for strategy in self.strategies.values():
            score = self._calculate_strategy_score(strategy, context_dict)
            if score > best_score:
                best_score = score
                best_strategy = strategy
                
        return best_strategy or list(self.strategies.values())[0]  # Fallback alla prima strategia se nessuna è adatta

    def _calculate_strategy_score(self, strategy: LearningStrategy, context: Dict) -> float:
        """Calcola il punteggio di una strategia"""
        base_score = strategy.success_rate
        
        # Bonus per strategie usate con successo in contesti simili
        context_bonus = 0.2 if context.get("type") in strategy.preferred_contexts else 0.0
        
        # Bonus per strategie appropriate alla difficoltà
        difficulty_match = abs(strategy.optimal_difficulty - 0.5)
        difficulty_bonus = 0.3 * (1.0 - difficulty_match)
        
        # Bonus per strategie poco usate (esplorazione)
        max_usage = max(s.usage_count for s in self.strategies.values())
        if max_usage > 0:
            usage_penalty = 0.1 * (strategy.usage_count / max_usage)
        else:
            usage_penalty = 0.0
        
        # Bonus per stile di apprendimento
        learning_style_bonus = 0.2 if context.get("learning_style") in strategy.preferred_contexts else 0.0
        
        total_score = base_score + context_bonus + difficulty_bonus - usage_penalty + learning_style_bonus
        return total_score
        
    def _update_strategy_level(self, strategy: LearningStrategy):
        """Aggiorna il livello della strategia"""
        if strategy.experience_points >= 100:
            strategy.current_level += 1
            strategy.experience_points -= 100
            
    def _unlock_new_strategies(self):
        """Sblocca nuove strategie"""
        # Implementazione non fornita
        
    def get_learning_summary(self) -> Dict:
        """Restituisce un sommario dell'apprendimento"""
        if not self.experiences:
            return {"status": "No learning experiences yet"}
            
        recent_experiences = self.experiences[-50:]  # Ultimi 50
        
        return {
            "total_experiences": len(self.experiences),
            "metacognition_level": self.metacognition_level.name,
            "strategies": {
                name: {
                    "success_rate": strategy.success_rate,
                    "usage_count": strategy.usage_count,
                    "last_used": strategy.last_used.isoformat()
                }
                for name, strategy in self.strategies.items()
            },
            "recent_performance": {
                "success_rate": np.mean([exp.success_level for exp in recent_experiences]),
                "average_time": np.mean([exp.time_taken for exp in recent_experiences]),
                "most_used_strategy": max(
                    self.strategies.items(),
                    key=lambda x: x[1].usage_count
                )[0]
            },
            "reflections": self.reflection_history[-5:]  # Ultime 5 riflessioni
        }
        
    def save_state(self, file_path: str):
        """Salva lo stato del sistema"""
        state = {
            "metacognition_level": self.metacognition_level.name,
            "strategies": {
                name: {
                    "name": strategy.name,
                    "parameters": strategy.parameters,
                    "success_rate": strategy.success_rate,
                    "usage_count": strategy.usage_count,
                    "last_used": strategy.last_used.isoformat(),
                    "effectiveness_history": strategy.effectiveness_history,
                    "context_types": list(strategy.context_types),
                    "preferred_contexts": list(strategy.preferred_contexts),
                    "optimal_difficulty": strategy.optimal_difficulty,
                    "experience_points": strategy.experience_points,
                    "current_level": strategy.current_level
                }
                for name, strategy in self.strategies.items()
            },
            "experiences": [
                {
                    "content": exp.content,
                    "strategy_used": exp.strategy_used,
                    "success_level": exp.success_level,
                    "time_taken": exp.time_taken,
                    "context": exp.context,
                    "timestamp": exp.timestamp.isoformat(),
                    "feedback": exp.feedback,
                    "difficulty": exp.difficulty
                }
                for exp in self.experiences
            ],
            "reflection_history": self.reflection_history
        }
        
        with open(file_path, 'w') as f:
            json.dump(state, f, indent=4)
            
    def load_state(self, file_path: str):
        """Carica lo stato del sistema"""
        with open(file_path, 'r') as f:
            state = json.load(f)
            
        self.metacognition_level = MetaCognitionLevel[state["metacognition_level"]]
        
        # Ripristina le strategie
        self.strategies = {
            name: LearningStrategy(
                name=data["name"],
                parameters=data["parameters"],
                success_rate=data["success_rate"],
                usage_count=data["usage_count"],
                last_used=datetime.fromisoformat(data["last_used"]),
                effectiveness_history=data["effectiveness_history"],
                context_types=set(data["context_types"]),
                preferred_contexts=set(data["preferred_contexts"]),
                optimal_difficulty=data["optimal_difficulty"],
                experience_points=data["experience_points"],
                current_level=data["current_level"]
            )
            for name, data in state["strategies"].items()
        }
        
        # Ripristina le esperienze
        self.experiences = [
            LearningExperience(
                content=exp["content"],
                strategy_used=exp["strategy_used"],
                success_level=exp["success_level"],
                time_taken=exp["time_taken"],
                context=exp["context"],
                timestamp=datetime.fromisoformat(exp["timestamp"]),
                feedback=exp["feedback"],
                difficulty=exp["difficulty"]
            )
            for exp in state["experiences"]
        ]
        
        self.reflection_history = state["reflection_history"]
        
    def get_state(self) -> Dict:
        """Restituisce lo stato corrente del sistema di meta-learning"""
        strategies = []
        for name, strategy in self.strategies.items():
            strategies.append({
                "name": name,
                "success_rate": strategy.success_rate,
                "usage_count": strategy.usage_count,
                "current_level": strategy.current_level,
                "optimal_difficulty": strategy.optimal_difficulty,
                "experience_points": strategy.experience_points
            })
            
        return {
            "strategies": strategies,
            "total_experiences": len(self.experiences),
            "metacognition_level": self.metacognition_level.name,
            "total_reflections": len(self.reflection_history)
        }
        
    def adapt_to_user_profile(self, user_profile) -> None:
        """Adatta le strategie in base al profilo utente"""
        # Ottieni lo stile di comunicazione
        comm_style = user_profile.get_communication_style()
        
        # Adatta le strategie in base alle preferenze
        for strategy in self.strategies.values():
            # Adatta l'intensità e la difficoltà in base al livello tecnico
            technical_level = comm_style.get("technical_level", 0.5)
            old_difficulty = strategy.optimal_difficulty
            
            if technical_level > 0.6:  # Abbassiamo la soglia da 0.7 a 0.6
                # Per livelli tecnici alti, aumenta sia l'intensità che la difficoltà
                # L'aumento della difficoltà è proporzionale al livello tecnico
                # Calcola l'intensità in modo più aggressivo per livelli tecnici alti
                intensity_boost = (technical_level - 0.6) * 1.5  # Fattore di boost per l'intensità
                strategy.parameters["intensity"] = min(1.0, technical_level + intensity_boost)
                difficulty_increase = (technical_level - 0.6) * 2  # Aggiustiamo anche qui
                strategy.optimal_difficulty = old_difficulty + difficulty_increase
            elif technical_level < 0.3:
                # Per livelli tecnici bassi, diminuisci sia l'intensità che la difficoltà
                strategy.parameters["intensity"] = technical_level
                strategy.optimal_difficulty = max(0.3, old_difficulty - 0.2)
            else:
                # Per livelli tecnici medi, mantieni l'intensità ma non modificare la difficoltà
                strategy.parameters["intensity"] = technical_level
                
            # Adatta la profondità in base al livello di verbosità
            if "depth" in strategy.parameters:
                verbosity = comm_style.get("verbosity", 0.5)
                strategy.parameters["depth"] = verbosity
                
            # Adatta la frequenza in base alla formalità
            if "frequency" in strategy.parameters:
                formality = comm_style.get("formality", 0.5)
                strategy.parameters["frequency"] = 1 - formality
                
            # Aggiorna i contesti preferiti
            preferred_topics = set(comm_style.get("preferred_topics", []))
            avoided_topics = set(comm_style.get("avoided_topics", []))
            strategy.preferred_contexts.update(preferred_topics)
            strategy.preferred_contexts.difference_update(avoided_topics)
            
    def update_from_user_interaction(self, interaction_data: Dict[str, Any]) -> LearningInsight:
        """Aggiorna il sistema in base all'interazione dell'utente"""
        # Estrai informazioni rilevanti
        success_level = interaction_data.get("sentiment", 0) * 0.5 + 0.5  # Normalizza a [0,1]
        context = {
            "technical_level": interaction_data.get("technical_feedback", 0.5),
            "formality": interaction_data.get("formality_feedback", 0.5),
            "topic": interaction_data.get("topic", "general")
        }
        
        current_time = time.time()
        time_taken = current_time - self._last_strategy_time
        self._last_strategy_time = current_time
        
        # Crea una nuova esperienza
        experience = LearningExperience(
            content=str(interaction_data),
            strategy_used=self._get_current_strategy().name,
            success_level=success_level,
            time_taken=time_taken,
            context=context,
            timestamp=datetime.now(),
            feedback=None,
            difficulty=context["technical_level"]
        )
        
        # Aggiorna la storia delle esperienze
        self.experiences.append(experience)
        
        # Aggiorna le metriche della strategia corrente
        current_strategy = self._get_current_strategy()
        current_strategy.success_rate = (
            current_strategy.success_rate * 0.9 + success_level * 0.1
        )
        current_strategy.effectiveness_history.append(success_level)
        
        # Genera un insight
        insight = LearningInsight(
            system_name="meta_learning",
            metric_name="strategy_effectiveness",
            value=success_level,
            timestamp=time.time(),
            confidence=min(1.0, len(self.experiences) / 100)
        )
        
        self.insights.append(insight)
        return insight
        
    def _get_current_strategy(self) -> LearningStrategy:
        """Ottiene la strategia corrente o ne crea una di default"""
        if not self.strategies:
            self._initialize_strategies()
        return max(
            self.strategies.values(),
            key=lambda s: s.success_rate * (1 + len(s.effectiveness_history) / 1000)
        )
        
    def get_learning_recommendations(self, user_profile) -> List[Dict]:
        """Genera raccomandazioni di apprendimento basate sul profilo utente"""
        recommendations = []
        comm_style = user_profile.get_communication_style()
        
        # Ordina le strategie per successo ed esperienza
        sorted_strategies = sorted(
            self.strategies.values(),
            key=lambda s: s.success_rate * (1 + len(s.effectiveness_history) / 1000),
            reverse=True
        )
        
        for strategy in sorted_strategies[:5]:  # Aumentato il numero di strategie da considerare
            # Calcola la compatibilità con il profilo utente
            topics = set(strategy.preferred_contexts) & set(comm_style.get("preferred_topics", []))
            topic_overlap = len(topics) / max(1, len(strategy.preferred_contexts))  # Normalizzato
            
            technical_match = 1 - abs(
                strategy.parameters.get("intensity", 0.5) - comm_style.get("technical_level", 0.5)
            )
            
            # Bonus per match tecnico molto alto
            if technical_match > 0.8:
                technical_bonus = 0.2
            elif technical_match > 0.6:
                technical_bonus = 0.1
            else:
                technical_bonus = 0
            
            # Calcola un punteggio di compatibilità più bilanciato
            base_compatibility = (
                topic_overlap * 0.4 +  # Peso del topic overlap
                technical_match * 0.4 +  # Peso del technical match
                strategy.success_rate * 0.2  # Peso del success rate
            )
            
            # Applica i bonus
            experience_bonus = min(0.2, len(strategy.effectiveness_history) / 50)  # Bonus per esperienza
            compatibility = min(1.0, base_compatibility + technical_bonus + experience_bonus)
            
            # Ridotta la soglia di compatibilità ma aumentato il punteggio minimo
            if compatibility > 0.4:  # Soglia intermedia
                # Genera una spiegazione basata sui fattori più rilevanti
                reasons = []
                if technical_match > 0.7:
                    reasons.append("si adatta bene al tuo livello tecnico")
                if topics:
                    reasons.append(f"è rilevante per i tuoi interessi in {', '.join(topics)}")
                if strategy.success_rate > 0.6:
                    reasons.append("ha dimostrato buoni risultati in passato")
                if len(strategy.effectiveness_history) > 10:
                    reasons.append("è stata testata approfonditamente")
                
                reason = "Questa strategia " + " e ".join(reasons) if reasons else \
                        "Questa strategia potrebbe essere utile per il tuo apprendimento"
                
                recommendations.append({
                    "strategy_name": strategy.name,
                    "compatibility": compatibility,
                    "success_rate": strategy.success_rate,
                    "technical_match": technical_match,
                    "topic_overlap": topic_overlap,
                    "experience_level": len(strategy.effectiveness_history),
                    "reason": reason,
                    "suggested_parameters": {
                        k: min(0.9, max(0.1, v * technical_match))
                        for k, v in strategy.parameters.items()
                    }
                })
        
        return recommendations
        
    def _analyze_learning_trends(self, experiences: List[LearningExperience]) -> Dict:
        """Analizza i trend di apprendimento"""
        if not experiences:
            return {
                "success_trend": "no data",
                "speed_trend": "no data",
                "consistency": 0.0
            }
            
        # Calcola i trend
        success_levels = [exp.success_level for exp in experiences]
        time_taken = [exp.time_taken for exp in experiences]
        
        # Calcola le differenze
        success_diff = np.diff(success_levels)
        time_diff = np.diff(time_taken)
        
        # Determina i trend
        success_trend = "improving" if np.mean(success_diff) > 0 else "declining"
        speed_trend = "faster" if np.mean(time_diff) < 0 else "slower"
        
        # Calcola la consistenza
        consistency = 1.0 - np.std(success_levels)
        
        return {
            "success_trend": success_trend,
            "speed_trend": speed_trend,
            "consistency": float(consistency)
        }
        
    def _reflect_on_learning(self) -> Dict:
        """Riflette sull'apprendimento"""
        if not self.experiences:
            return {
                "insights": "No learning experiences yet",
                "metacognition_level": self.metacognition_level.name,
                "timestamp": datetime.now().isoformat()
            }
            
        recent_experiences = self.experiences[-50:]  # Ultimi 50
        
        # Analizza i trend
        trends = self._analyze_learning_trends(recent_experiences)
        
        # Calcola le statistiche delle strategie
        strategy_stats = {}
        for exp in recent_experiences:
            if exp.strategy_used not in strategy_stats:
                strategy_stats[exp.strategy_used] = []
            strategy_stats[exp.strategy_used].append(exp.success_level)
            
        # Trova le migliori e peggiori strategie
        top_strategies = []
        struggling_strategies = []
        for strategy, results in strategy_stats.items():
            avg_success = np.mean(results)
            if avg_success > 0.7:
                top_strategies.append(strategy)
            elif avg_success < 0.4:
                struggling_strategies.append(strategy)
                
        insights = {
            "overall_success_rate": float(np.mean([exp.success_level for exp in recent_experiences])),
            "top_strategies": top_strategies,
            "struggling_strategies": struggling_strategies,
            "learning_trends": trends
        }
        
        # Aggiorna la storia delle riflessioni
        reflection = {
            "insights": insights,
            "metacognition_level": self.metacognition_level.name,
            "timestamp": datetime.now().isoformat()
        }
        self.reflection_history.append(reflection)
        
        # Aggiorna il livello di metacognizione
        self._update_metacognition_level(insights)
        
        return reflection
        
    def _update_metacognition_level(self, insights: Dict):
        """Aggiorna il livello di metacognizione"""
        current_level = self.metacognition_level
        
        # Criteri per l'avanzamento
        success_threshold = 0.8
        consistency_threshold = 0.7
        strategy_mastery = len(insights["top_strategies"]) > 2
        no_struggling = len(insights["struggling_strategies"]) == 0
        positive_trends = (
            insights["learning_trends"]["success_trend"] == "improving" and
            insights["learning_trends"]["consistency"] > consistency_threshold
        )
        
        # Determina il nuovo livello
        if (insights["overall_success_rate"] > success_threshold and
            positive_trends and strategy_mastery and no_struggling):
            
            # Avanza al prossimo livello se non è già al massimo
            if current_level != MetaCognitionLevel.OPTIMIZATION:
                next_level = MetaCognitionLevel(current_level.value + 1)
                self.metacognition_level = next_level
                
    def _select_best_strategy(self, context: Dict, difficulty: float) -> LearningStrategy:
        """Seleziona la strategia migliore"""
        return self._select_strategy(context)

    def register_system(self, system, system_name: str = None):
        """Registra un nuovo sistema per il monitoraggio"""
        if system_name is None:
            system_name = system.__class__.__name__.lower()
            
        self.registered_systems[system_name] = system
        self.system_states[system_name] = SystemState(
            performance_metrics={},
            resource_usage={},
            error_rate=0.0,
            last_update=time.time()
        )

    def analyze_learning_process(self) -> List[LearningInsight]:
        """Analizza il processo di apprendimento e genera insights"""
        current_insights = []
        current_time = time.time()
        
        # Aggiorna gli stati dei sistemi
        for system_name in self.registered_systems:
            self._update_system_state(system_name)
        
        # Genera sempre insights di base per ogni sistema
        for system_name, state in self.system_states.items():
            if not state or not state.performance_metrics:
                continue
                
            for metric, value in state.performance_metrics.items():
                if np.isnan(value) or np.isinf(value):
                    continue
                    
                current_insights.append(
                    LearningInsight(
                        system_name=system_name,
                        metric_name=f"{metric}_current",
                        value=float(value),
                        timestamp=current_time,
                        confidence=1.0
                    )
                )
        
        # Analisi trend temporali se ci sono insights precedenti
        if self.insights:
            last_time = self.insights[-1].timestamp
            time_diff = current_time - last_time
            
            for system_name, state in self.system_states.items():
                if time_diff > 0 and state and state.performance_metrics:
                    for metric, value in state.performance_metrics.items():
                        if np.isnan(value) or np.isinf(value):
                            continue
                            
                        prev_values = [i.value for i in self.insights 
                                     if i.system_name == system_name and 
                                     i.metric_name == f"{metric}_current" and 
                                     not np.isnan(i.value) and 
                                     not np.isinf(i.value)]
                        
                        if prev_values:
                            # Calcola il tasso di cambiamento
                            rate_of_change = float(value - prev_values[-1]) / time_diff
                            if not np.isnan(rate_of_change) and not np.isinf(rate_of_change):
                                current_insights.append(
                                    LearningInsight(
                                        system_name=system_name,
                                        metric_name=f"{metric}_rate_of_change",
                                        value=rate_of_change,
                                        timestamp=current_time,
                                        confidence=0.7
                                    )
                                )
                            
                            # Calcola l'accelerazione del cambiamento
                            if len(prev_values) >= 2:
                                prev_rate = float(prev_values[-1] - prev_values[-2]) / time_diff
                                if not np.isnan(prev_rate) and not np.isinf(prev_rate):
                                    acceleration = float(rate_of_change - prev_rate) / time_diff
                                    if not np.isnan(acceleration) and not np.isinf(acceleration):
                                        current_insights.append(
                                            LearningInsight(
                                                system_name=system_name,
                                                metric_name=f"{metric}_acceleration",
                                                value=acceleration,
                                                timestamp=current_time,
                                                confidence=0.6
                                            )
                                        )
        
        # Memorizza i nuovi insights
        self.insights.extend(current_insights)
        
        return current_insights
        
    def _calculate_correlation(self, metric1: str, metric2: str, system_name: str) -> Optional[float]:
        """Calcola la correlazione tra due metriche"""
        values1 = []
        values2 = []
        
        for insight in self.insights:
            if insight.system_name == system_name:
                if insight.metric_name == metric1:
                    values1.append(insight.value)
                elif insight.metric_name == metric2:
                    values2.append(insight.value)
        
        if len(values1) >= 2 and len(values2) >= 2:
            try:
                return float(np.corrcoef(values1, values2)[0, 1])
            except:
                return None
        return None
        
    def _is_anomaly(self, value: float, metric: str, system_name: str) -> bool:
        """Determina se un valore è anomalo"""
        values = []
        
        for insight in self.insights:
            if insight.system_name == system_name and insight.metric_name == metric:
                values.append(insight.value)
        
        if len(values) >= 5:
            mean = np.mean(values)
            std = np.std(values)
            if std > 0:
                z_score = abs(value - mean) / std
                return z_score > 2.0
        
        return False
        
    def get_system_state(self) -> Dict[str, Any]:
        """Restituisce lo stato corrente di tutti i sistemi"""
        state = {}
        
        for system_name, system in self.registered_systems.items():
            system_state = {}
            
            # Raccogli metriche specifiche per ogni tipo di sistema
            if 'pattern_recognition' in system_name.lower():
                patterns = system.get_all_patterns()
                system_state.update({
                    'total_patterns': len(patterns),
                    'average_stability': np.mean([p.stability_score for p in patterns]) if patterns else 0.0,
                    'average_confidence': np.mean([p.confidence for p in patterns]) if patterns else 0.0
                })
                
            elif 'emotional' in system_name.lower():
                adaptation = system.get_adaptation_state()
                system_state.update({
                    'sensitivity': adaptation['sensitivity'],
                    'baseline_arousal': adaptation['current_intensity'],
                    'baseline_valence': adaptation['current_valence'],
                    'emotional_balance': (adaptation['current_valence'] + 1) * adaptation['current_intensity'],
                    'adaptation_level': adaptation['sensitivity'] * abs(adaptation['current_valence'])
                })
                
            elif 'social' in system_name.lower():
                knowledge = system.get_collective_knowledge()
                system_state.update({
                    'total_interactions': sum(knowledge['interactions'].values()),
                    'active_categories': len(knowledge['categories']),
                    'average_acceptance': np.mean(list(knowledge['categories'].values()))
                })
                
            state[system_name.lower()] = system_state
            
        return state
        
    def _update_system_state(self, system_name: str):
        """Aggiorna lo stato di un sistema"""
        if system_name not in self.registered_systems:
            return
            
        system = self.registered_systems[system_name]
        current_time = time.time()
        
        # Raccogli metriche specifiche per ogni tipo di sistema
        performance_metrics = {}
        
        if 'pattern_recognition' in system_name.lower():
            patterns = system.get_all_patterns()
            avg_stability = np.mean([p.stability_score for p in patterns]) if patterns else 0.0
            avg_confidence = np.mean([p.confidence for p in patterns]) if patterns else 0.0
            performance_metrics.update({
                'total_patterns': len(patterns),
                'average_stability': avg_stability,
                'average_confidence': avg_confidence,
                'learning_progress': avg_stability * avg_confidence,
                'pattern_diversity': len(set(p.id for p in patterns))
            })
            
        elif 'emotional' in system_name.lower():
            adaptation = system.get_adaptation_state()
            performance_metrics.update({
                'sensitivity': adaptation['sensitivity'],
                'baseline_arousal': adaptation['current_intensity'],
                'baseline_valence': adaptation['current_valence'],
                'emotional_balance': (adaptation['current_valence'] + 1) * adaptation['current_intensity'],
                'adaptation_level': adaptation['sensitivity'] * abs(adaptation['current_valence'])
            })
            
        elif 'curiosity' in system_name.lower():
            performance_metrics.update({
                'exploration_rate': 0.8,  # Valore di base
                'novelty_threshold': 0.5,  # Valore di base
                'learning_efficiency': 0.7  # Valore di base
            })
            
        elif 'contextual_learning' in system_name.lower():
            performance_metrics.update({
                'context_awareness': 0.75,  # Valore di base
                'adaptation_speed': 0.6,  # Valore di base
                'context_diversity': 0.8  # Valore di base
            })
            
        elif 'memory' in system_name.lower():
            performance_metrics.update({
                'retention_rate': 0.85,  # Valore di base
                'recall_accuracy': 0.7,  # Valore di base
                'memory_capacity': 0.9  # Valore di base
            })
            
        elif 'reasoning' in system_name.lower():
            performance_metrics.update({
                'inference_accuracy': 0.8,  # Valore di base
                'logical_consistency': 0.75,  # Valore di base
                'reasoning_depth': 0.65  # Valore di base
            })
            
        elif 'communication' in system_name.lower():
            performance_metrics.update({
                'response_quality': 0.8,  # Valore di base
                'interaction_fluency': 0.7,  # Valore di base
                'expression_clarity': 0.85  # Valore di base
            })
            
        elif 'social' in system_name.lower():
            knowledge = system.get_collective_knowledge()
            interactions = list(knowledge['interactions'].values())
            avg_interaction = np.mean(interactions) if interactions else 0.0
            performance_metrics.update({
                'total_interactions': sum(interactions),
                'active_categories': len(knowledge['categories']),
                'average_acceptance': np.mean(list(knowledge['categories'].values())),
                'interaction_density': avg_interaction * len(knowledge['categories']),
                'social_diversity': len(set(knowledge['interactions'].keys()))
            })
        
        # Se non ci sono metriche specifiche, usa metriche di base generiche
        if not performance_metrics:
            performance_metrics.update({
                'operational_status': 1.0,  # Sistema operativo
                'basic_efficiency': 0.8,  # Efficienza di base
                'system_health': 0.9  # Salute del sistema
            })
            
        # Aggiorna lo stato del sistema
        self.system_states[system_name] = SystemState(
            performance_metrics=performance_metrics,
            resource_usage={},
            error_rate=0.0,
            last_update=current_time
        )
