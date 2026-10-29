"""One operational decision motor shared by ALLMA subsystems.

The motor proposes branches, never facts, permissions, identities or memories.
Missing weights, uncertainty, heat and cancellation preserve host policy.
"""
from pathlib import Path
import threading
import time
import logging
from .decision_engine import DECIDER_MODEL, LocalDecisionEngine


ROUTES = {
    'calculate': 'Use an exact arithmetic calculator for an explicit calculation.',
    'memory': 'Search the personal conversation memory for a past interaction.',
    'reason': 'Use the language and reasoning model for general knowledge or explanations.',
    'clarify': 'Ask for clarification because the request has no identifiable subject.',
}


class DecisionRuntime:
    def __init__(self, models_dir, store, *, temperature=None, factory=LocalDecisionEngine):
        self.path = Path(models_dir)/'decider-0.8b'/DECIDER_MODEL['filename'] if models_dir else None
        self.store, self.temperature, self.factory = store, temperature, factory
        self.power_guard = None
        self.enabled = store.get('decision_runtime').get('enabled', True) is True
        self._engine = None
        self._lock = threading.Lock()
        self._closed = threading.Event()
        self._retry_after = 0.
        self.last = {'status':'not_used'}

    def status(self):
        try:
            available = self.path is not None and self.path.is_file() and self.path.stat().st_size == DECIDER_MODEL['size_bytes']
        except OSError:
            available = False
        return {'enabled':self.enabled, 'available':available, 'loaded':self._engine is not None,
                'closed':self._closed.is_set(), 'last_status':self.last.get('status'),
                'backend':getattr(self._engine,'backend_info',{}).get('kind','not_loaded'),
                'mode':'operational', 'model':'Decider 0.8B · Q4_K_M'}

    def configure(self, enabled):
        if type(enabled) is not bool:
            raise ValueError('Boolean required')
        if enabled == self.enabled:
            if enabled:
                self._retry_after = 0.
            return self.status()
        self.store.put('decision_runtime', {'enabled':enabled})
        self.enabled = enabled
        if enabled:
            self._retry_after = 0.
        if not enabled:
            # UI callers never wait for a native inference to finish.
            threading.Thread(target=self.release, daemon=True, name='DeciderRelease').start()
        return self.status()

    def choose(self, domain, state, question, options, *, cancel_event=None):
        start = time.perf_counter()
        result = {'domain':domain, 'mode':'operational', 'choice':None, 'status':'unavailable',
                  'elapsed_ms':0., 'total_ms':0.}
        if self._closed.is_set() or not self.enabled:
            result['status'] = 'closed' if self._closed.is_set() else 'disabled'
            return result
        if cancel_event is not None and cancel_event.is_set():
            result['status'] = 'cancelled'
            return result
        if not isinstance(state, str) or len(state) > 8000:
            result['status'] = 'context_limit'
            return result
        if time.monotonic() < self._retry_after:
            result['status'] = 'retry_deferred'
            return result
        if not self._lock.acquire(blocking=False):
            result['status'] = 'busy'
            return result
        try:
            if self._closed.is_set() or not self.enabled:
                result['status'] = 'disabled'
                return result
            if self.power_guard is not None and not self.power_guard():
                self._release_locked()
                result['status'] = 'thermal_pause'
                return result
            if self.temperature and (self.temperature() or 0) >= 42:
                self._release_locked()
                result['status'] = 'thermal_pause'
                return result
            if self.path is None or not self.path.is_file():
                result['status'] = 'model_missing'
                return result
            if self._engine is None:
                engine = self.factory(self.path)
                try:
                    engine.load()
                except Exception:
                    engine.close()
                    raise
                self._engine = engine
            answer = self._engine.decide(state, question, options, cancel_event=cancel_event)
            result.update(choice=answer.choice, status=answer.status,
                          probabilities=dict(answer.probabilities), elapsed_ms=answer.elapsed_ms,
                          backend=getattr(self._engine,'backend_info',{}).get('kind','cpu'))
            # Never consume a stale result after an opt-out or shutdown.
            if self._closed.is_set() or not self.enabled or (cancel_event is not None and cancel_event.is_set()):
                result.update(choice=None, status='cancelled')
                self._release_locked()
        except Exception as error:
            self._release_locked()
            self._retry_after = time.monotonic() + 60
            result.update(choice=None, status='unavailable', error=type(error).__name__)
        finally:
            result['total_ms'] = (time.perf_counter()-start)*1000
            self.last = dict(result)
            self._lock.release()
            logging.info('[Decider] domain=%s status=%s choice=%s total_ms=%.0f',
                         domain, result['status'], result['choice'], result['total_ms'])
        return result

    @staticmethod
    def prompt_history(history, decision):
        if decision.get('status') != 'selected' or decision.get('choice') != 'reason':
            return history
        result = []
        administrative = {'conversational','runtime_self_description','runtime_capabilities','communication_preference'}
        for turn in history:
            if turn.role == 'assistant' and getattr(turn, 'metadata', {}).get('source') in administrative:
                if result and result[-1].role == 'user':
                    result.pop()
                continue
            result.append(turn)
        return result

    def route(self, message, history=(), cancel_event=None):
        # No assistant claims in the router's evidence: previous wrong answers
        # must not become facts for the decision layer.
        relevant = self.prompt_history(history, {'status':'selected','choice':'reason'})
        previous = [m.content[:180] for m in relevant if m.role == 'user'][-2:]
        state = message if not previous else 'Earlier user requests: ' + ' | '.join(previous) + '\nCurrent request: ' + message
        # Offer only executable resources: supported exact expressions have
        # already returned through the host calculator before reaching this path.
        # Never ask the motor to select an unbound natural-language calculation.
        options = {key:value for key,value in ROUTES.items() if key != 'calculate'}
        return self.choose('dialogue_route', state, 'Which resource is most useful?', options,
                           cancel_event=cancel_event)

    def prioritize_dreams(self, memories, cancel_event=None):
        if len(memories) < 2:
            return memories
        options = {str(i): str(m.get('text') or m.get('content',''))[:240] or 'Empty record'
                   for i,m in enumerate(memories[:3])}
        result = self.choose('dream_order', 'These are attributed user reports, not verified world facts.',
                             'Which experience is most useful to explore first for a tentative reflection?',
                             options, cancel_event=cancel_event)
        choice = result.get('choice')
        if result.get('status') != 'selected' or choice not in options:
            return memories
        index = int(choice)
        return [memories[index]] + [m for i,m in enumerate(memories) if i != index]

    def _release_locked(self):
        engine, self._engine = self._engine, None
        if engine:
            try:
                engine.close()
            except Exception:
                logging.warning('[Decider] Native release failed')

    def release(self):
        with self._lock:
            self._release_locked()

    def close(self):
        self._closed.set()
        self.release()
