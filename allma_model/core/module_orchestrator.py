"""
Module Orchestrator - Sistema di Gestione Moduli Intelligente

Coordina l'esecuzione di tutti i moduli ALLMA in modo efficiente,
rispettando budget di performance per deployment mobile.
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import time
import logging
from enum import IntEnum

logger = logging.getLogger(__name__)


class ModulePriority(IntEnum):
    """Priorità moduli (più alto = più importante)"""
    CRITICAL = 10  # Sempre eseguito
    HIGH = 8
    MEDIUM = 5
    LOW = 3
    OPTIONAL = 1


@dataclass
class ModuleConfig:
    """Configurazione singolo modulo"""
    name: str
    instance: Any
    priority: ModulePriority
    cost_ms: int  # Tempo stimato esecuzione
    enabled: bool = True
    success_count: int = 0
    failure_count: int = 0
    avg_exec_time: float = 0.0


class ModuleOrchestrator:
    """
    Orchestratore intelligente per moduli ALLMA.
    
    Gestisce:
    - Esecuzione basata su priorità
    - Budget performance
    - Enable/disable dinamico
    - Metriche performance
    """
    
    def __init__(self, performance_budget_ms: int = 500):
        """
        Args:
            performance_budget_ms: Tempo massimo per esecuzione moduli (default 500ms)
        """
        self.performance_budget = performance_budget_ms
        self.modules: Dict[str, ModuleConfig] = {}
        self.execution_history: List[Dict[str, Any]] = []
        
        logger.info(f"ModuleOrchestrator initialized with {performance_budget_ms}ms budget")
    
    def register_module(
        self,
        name: str,
        instance: Any,
        priority: ModulePriority,
        cost_ms: int,
        enabled: bool = True
    ) -> None:
        """
        Registra un modulo nell'orchestratore.
        
        Args:
            name: Nome identificativo modulo
            instance: Istanza del modulo
            priority: Priorità esecuzione (ModulePriority enum)
            cost_ms: Costo stimato in millisecondi
            enabled: Se abilitato all'avvio
        """
        config = ModuleConfig(
            name=name,
            instance=instance,
            priority=priority,
            cost_ms=cost_ms,
            enabled=enabled
        )
        
        self.modules[name] = config
        logger.info(f"Registered module '{name}' (priority={priority}, cost={cost_ms}ms)")
    
    def enable_module(self, name: str) -> bool:
        """Abilita un modulo"""
        if name in self.modules:
            self.modules[name].enabled = True
            logger.info(f"Module '{name}' enabled")
            return True
        return False
    
    def disable_module(self, name: str) -> bool:
        """Disabilita un modulo (kill switch)"""
        if name in self.modules:
            self.modules[name].enabled = False
            logger.warning(f"Module '{name}' disabled")
            return True
        return False
    
    def process(
        self,
        user_input: str,
        context: Dict[str, Any],
        intent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Esegue moduli rilevanti rispettando budget performance.
        
        Args:
            user_input: Input utente
            context: Contesto conversazione
            intent: Intent rilevato (opzionale, per filtering)
        
        Returns:
            Risultati aggregati da tutti i moduli
        """
        start_time = time.time()
        
        # Filtra moduli abilitati e ordinali per priorità
        active_modules = [
            m for m in self.modules.values()
            if m.enabled and self._is_relevant(m, intent, context)
        ]
        active_modules.sort(key=lambda x: x.priority, reverse=True)
        
        results = {}
        time_used_ms = 0
        executed_count = 0
        
        for module in active_modules:
            # Budget check
            if time_used_ms + module.cost_ms > self.performance_budget:
                logger.debug(
                    f"Budget exceeded, skipping module '{module.name}' "
                    f"(used {time_used_ms}ms / {self.performance_budget}ms)"
                )
                break
            
            # Esecuzione modulo
            try:
                module_start = time.time()
                
                # Chiama metodo 'process' del modulo se esiste
                if hasattr(module.instance, 'process'):
                    result = module.instance.process(user_input, context)
                elif hasattr(module.instance, 'analyze'):
                    result = module.instance.analyze(user_input, context)
                else:
                    logger.warning(f"Module '{module.name}' has no process/analyze method")
                    continue
                
                module_time_ms = (time.time() - module_start) * 1000
                
                # Update stats
                module.success_count += 1
                module.avg_exec_time = (
                    (module.avg_exec_time * (module.success_count - 1) + module_time_ms)
                    / module.success_count
                )
                
                results[module.name] = result
                time_used_ms += module_time_ms
                executed_count += 1
                
                logger.debug(
                    f"Module '{module.name}' executed in {module_time_ms:.1f}ms"
                )
                
            except Exception as e:
                module.failure_count += 1
                logger.error(f"Module '{module.name}' failed: {e}", exc_info=True)
                
                # Auto-disable se troppi fallimenti
                if module.failure_count > 5:
                    self.disable_module(module.name)
                    logger.error(f"Module '{module.name}' auto-disabled (too many failures)")
        
        total_time_ms = (time.time() - start_time) * 1000
        
        # Log performance
        self.execution_history.append({
            'timestamp': time.time(),
            'executed': executed_count,
            'total_time_ms': total_time_ms,
            'budget_used_pct': (time_used_ms / self.performance_budget) * 100
        })
        
        logger.info(
            f"Orchestrator executed {executed_count} modules in {total_time_ms:.1f}ms "
            f"({time_used_ms:.0f}/{self.performance_budget}ms budget)"
        )
        
        return self.coalescence(results)
    
    def _is_relevant(self, module: ModuleConfig, intent: Optional[str], context: Dict[str, Any] = {}) -> bool:
        """
        Determina se un modulo è rilevante per l'intent corrente.
        
        Future enhancement: intent-based filtering
        Per ora ritorna sempre True (esegui tutti i moduli abilitati)
        """
        if module.priority == ModulePriority.CRITICAL:
            return True
            
        # Cognitive Tracker is always relevant for monitoring
        if module.name == 'cognitive_tracker':
            return True
            
        # Default to True if no intent provided (conservative fallback)
        if not intent:
            return True
            
        # Intent-based filtering
        if module.name == 'emotional_adaptation':
            emotional_intents = {'joy', 'sadness', 'anger', 'fear', 'surprise', 'emotional'}
            # Also check context for high intensity
            intensity = context.get('emotional_intensity', 0.0)
            return (intent in emotional_intents) or (intensity > 0.6)
            
        if module.name == 'curiosity_system':
            curiosity_intents = {'question', 'learning', 'unknown', 'confused', 'curiosity'}
            return intent in curiosity_intents
            
        if module.name == 'meta_learner':
            learning_intents = {'learning', 'study', 'analyze', 'explain', 'practice'}
            return intent in learning_intents
            
        if module.name == 'creativity_enhancer':
            creative_intents = {'creative', 'story', 'generate', 'write', 'imagine'}
            return intent in creative_intents
            
        # Default for other modules
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Statistiche performance moduli"""
        return {
            'modules': {
                name: {
                    'enabled': m.enabled,
                    'priority': m.priority,
                    'success_count': m.success_count,
                    'failure_count': m.failure_count,
                    'avg_exec_time_ms': m.avg_exec_time,
                    'estimated_cost_ms': m.cost_ms
                }
                for name, m in self.modules.items()
            },
            'performance_budget_ms': self.performance_budget,
            'recent_executions': self.execution_history[-10:]  # Last 10
        }
    
    def coalescence(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unifica risultati di moduli multipli.
        
        Strategia:
        - Merge semplice per ora
        - Future: weighted merge basato su confidence scores
        """
        return self._merge_intelligent(results)

    def _merge_intelligent(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge intelligente dei risultati dei moduli.
        Combina hint, risposte emotive e hook di curiosità.
        """
        merged = {
            'system_instruction': [],
            'user_prefix': [],
            'memory_updates': {},
            'raw_results': results
        }
        
        # 1. Emotional Adaptation
        if 'emotional_adaptation' in results:
            emo_res = results['emotional_adaptation']
            if isinstance(emo_res, str):
                merged['user_prefix'].append(emo_res)
            elif isinstance(emo_res, dict) and 'response' in emo_res:
                merged['user_prefix'].append(emo_res['response'])
                
        # 2. Curiosity System
        if 'curiosity_system' in results:
            cur_res = results['curiosity_system']
            if 'questions' in cur_res:
                questions = cur_res['questions']
                if questions:
                    # Take top 1 question as hook
                    merged['user_prefix'].append(f"\nMi chiedo: {questions[0]}")
                    # Add others to output instructions
                    merged['system_instruction'].append(f"Consider exploring: {', '.join(questions[1:])}")
            
        # 3. Meta Learner
        if 'meta_learner' in results:
            meta_res = results['meta_learner']
            if 'strategy' in meta_res:
                merged['system_instruction'].append(f"Adopt strategy: {meta_res['strategy'].upper()}")
            if 'hints' in meta_res:
                merged['system_instruction'].extend(meta_res['hints'])
                
        # 4. Cognitive Tracker
        if 'cognitive_tracker' in results:
            cog_res = results['cognitive_tracker']
            merged['memory_updates'].update(cog_res.get('abilities', {}))
            
        # Cleanup
        merged['user_prefix'] = " ".join(merged['user_prefix'])
        merged['system_instruction'] = "\n".join(merged['system_instruction'])
        
        return merged
