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
    consecutive_failures: int = 0
    attempt_count: int = 0
    last_status: str = "never_run"


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
            performance_budget_ms: Budget di ammissione dei moduli (non interrompe una chiamata in corso)
        """
        if performance_budget_ms <= 0:
            raise ValueError("performance_budget_ms must be positive")
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
        start_time = time.perf_counter()
        outcomes = {}
        results = {}
        active_modules = []
        turn_context = dict(context, user_input=user_input)

        for module in self.modules.values():
            if not module.enabled:
                outcomes[module.name] = {'status': 'disabled'}
                continue
            try:
                if self._is_relevant(module, intent, turn_context):
                    active_modules.append(module)
                else:
                    outcomes[module.name] = {'status': 'not_relevant'}
            except Exception as error:
                self._record_failure(module, error)
                outcomes[module.name] = {'status': 'failed', 'stage': 'selection'}
        active_modules.sort(key=lambda m: m.priority, reverse=True)

        for module in active_modules:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            # Learn admission cost from every completed attempt, including failures.
            # Calls are synchronous: this is not a hard timeout or thread cancellation.
            estimated_ms = max(module.cost_ms, module.avg_exec_time)
            if elapsed_ms + estimated_ms > self.performance_budget:
                outcomes[module.name] = {'status': 'budget_skipped', 'estimated_ms': estimated_ms}
                continue
            module_start = time.perf_counter()
            module.attempt_count += 1
            try:
                handler = getattr(module.instance, 'process', None)
                if not callable(handler):
                    handler = getattr(module.instance, 'analyze', None)
                if not callable(handler):
                    raise TypeError('Module has no callable process/analyze method')
                activity = getattr(self, 'activity', None)
                result = (activity.call(module.name, handler, user_input, dict(turn_context))
                          if activity is not None else handler(user_input, dict(turn_context)))
                if result is None:
                    result = {}
                # A malformed adapter must not crash coalescence or the whole chat.
                if not isinstance(result, dict) and not (
                        module.name == 'emotional_adaptation' and isinstance(result, str)):
                    raise TypeError('Module output must be a dictionary')
                results[module.name] = result
                module.success_count += 1
                module.consecutive_failures = 0
                outcomes[module.name] = {'status': 'executed' if result else 'no_output'}
            except Exception as error:
                self._record_failure(module, error)
                outcomes[module.name] = {'status': 'failed', 'stage': 'execution'}
            finally:
                duration = (time.perf_counter() - module_start) * 1000
                module.avg_exec_time += (duration - module.avg_exec_time) / module.attempt_count
                outcomes[module.name]['duration_ms'] = duration

        for name, outcome in outcomes.items():
            self.modules[name].last_status = outcome['status']
            activity = getattr(self, 'activity', None)
            if activity is not None:
                activity.emit(name, outcome['status'], outcome.get('duration_ms'))
        merged = self.coalescence(results)
        for name, result in results.items():
            contribution = self.coalescence({name: result})
            outcomes[name]['output_role'] = ('guidance' if contribution['system_instruction'] or contribution['user_prefix']
                                             else 'observational' if result else 'none')
        activity = getattr(self, 'activity', None)
        if activity is not None:
            for name, outcome in outcomes.items():
                if outcome.get('output_role') in ('guidance', 'observational'):
                    activity.emit(name, 'guidance' if outcome['output_role']=='guidance' else 'observed')
        total_time_ms = (time.perf_counter() - start_time) * 1000
        report = {
            'timestamp': time.time(), 'executed': len(results),
            'total_time_ms': total_time_ms,
            'budget_used_pct': total_time_ms / self.performance_budget * 100,
            'budget_exceeded': total_time_ms > self.performance_budget,
            'outcomes': outcomes,
        }
        self.execution_history.append(report)
        del self.execution_history[:-100]
        # Diagnostic data only: never inject these counters as autobiographical facts.
        merged['execution_report'] = report
        logger.info('Orchestrator: %s outputs in %.1fms', len(results), total_time_ms)
        return merged

    def _record_failure(self, module, error):
        module.failure_count += 1
        module.consecutive_failures += 1
        logger.warning("Module '%s' failed: %s", module.name, error)
        if module.consecutive_failures >= 6:
            self.disable_module(module.name)

    def _is_relevant(self, module: ModuleConfig, intent: Optional[str], context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determina se un modulo è rilevante per l'intent corrente.
        
        Filtra secondo intento e segnali dell'adattatore; conserva il monitoraggio.
        """
        context = context or {}
        intent = {'domanda': 'question', 'richiesta': 'request', 'emozione': 'emotional',
                  'accordo': 'agreement', 'disaccordo': 'disagreement', 'chiarimento': 'confused'}.get(intent, intent)
        if module.priority == ModulePriority.CRITICAL:
            return True
            
        # Cognitive Tracker is always relevant for monitoring
        if module.name in {'cognitive_tracker', 'cognitive_tracking'}:
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
            
        if module.name in {'curiosity_system', 'curiosity'}:
            curiosity_intents = {'question', 'learning', 'unknown', 'confused', 'curiosity'}
            return intent in curiosity_intents or intent == 'request'
            
        if module.name in {'meta_learner', 'meta_learning'}:
            return True  # this adapter learns feedback and explicit style requests on every turn
            
        if module.name in {'creativity_enhancer', 'creativity'}:
            if hasattr(module.instance, 'is_creative_request'):
                return module.instance.is_creative_request(context.get('user_input', ''))
            creative_intents = {'creative', 'story', 'generate', 'write', 'imagine'}
            return intent in creative_intents
            
        if module.name == 'planning' and hasattr(module.instance, '_is_planning_query'):
            return module.instance._is_planning_query(context.get('user_input', ''))

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
                    'consecutive_failures': m.consecutive_failures,
                    'last_status': m.last_status,
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
        
        # All current adapters share these fields; preserve their outputs.
        for result in results.values():
            if not isinstance(result, dict):
                continue
            for field in ('system_instruction', 'user_prefix'):
                value = result.get(field, [])
                if isinstance(value, str):
                    value = [value]
                if isinstance(value, (list, tuple)):
                    merged[field].extend(v for v in value if isinstance(v, str) and v.strip())

        def strings(value):
            if isinstance(value, str):
                return [value] if value.strip() else []
            if isinstance(value, (list, tuple)):
                return [v for v in value if isinstance(v, str) and v.strip()]
            return []

        emo = results.get('emotional_adaptation')
        merged['user_prefix'].extend(strings(emo if isinstance(emo, str)
                                             else emo.get('response') if isinstance(emo, dict) else None))
        curiosity = results.get('curiosity_system') or results.get('curiosity')
        if isinstance(curiosity, dict):
            questions = strings(curiosity.get('questions'))
            if questions:
                merged['user_prefix'].append(f"Mi chiedo: {questions[0]}")

        meta = results.get('meta_learning') or results.get('meta_learner')
        if isinstance(meta, dict):
            confidence = meta.get('confidence', 0)
            if isinstance(confidence, (int, float)) and confidence > .55:
                for key, label in [('suggested_style', 'STYLE PREFERENCE'),
                                   ('suggested_comm', 'COMMUNICATION MODE'), ('strategy', 'STRATEGY')]:
                    value = meta.get(key)
                    if isinstance(value, str) and value.strip():
                        merged['system_instruction'].append(f'{label}: {value.upper()}')
                merged['system_instruction'].extend(strings(meta.get('hints')))

        muse = results.get('creativity') or results.get('creativity_enhancer')
        if isinstance(muse, dict):
            merged['system_instruction'].extend(f'[MUSE]: {v}' for v in strings(muse.get('instruction')))
        personality = results.get('personality_style')
        if isinstance(personality, dict):
            merged['system_instruction'].extend(strings(personality.get('style_hint')))

        tracker = results.get('cognitive_tracker') or results.get('cognitive_tracking')
        if isinstance(tracker, dict) and isinstance(tracker.get('abilities'), dict):
            merged['memory_updates'].update(tracker['abilities'])

        # Remove identical hints from overlapping adapters without changing order.
        merged['user_prefix'] = list(dict.fromkeys(merged['user_prefix']))
        merged['system_instruction'] = list(dict.fromkeys(merged['system_instruction']))

        # Cleanup
        merged['user_prefix'] = " ".join(merged['user_prefix'])
        merged['system_instruction'] = "\n".join(merged['system_instruction'])
        
        return merged
