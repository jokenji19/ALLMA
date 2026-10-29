"""Optional local decision motor. No generation, tools, network or personal writes.

Plain state-first prompt and temperature follow Mapika/decider-0.8b v1.
The Q4 checkpoint is a third-party conversion; its confidence needs local validation.
"""
from dataclasses import dataclass
from contextlib import nullcontext
import logging
import math
from pathlib import Path
import threading
import time
from allma_model.utils.model_integrity import verified_models
from allma_model.llm.native_backend import native_work


DECIDER_MODEL = {
    'name': 'Decider · 0.8B (sperimentale)', 'required': False,
    'filename': 'decider-0.8b-Q4_K_M.gguf', 'size_bytes': 529297504,
    'sha256': '5cb5d042a236add5cde5459f8e8b8f8f80161ad4a1779a49377b70a64eb7b11a',
    'url': 'https://huggingface.co/seongukjeong/decider-0.8b-GGUF/resolve/48c1a1dfb87edda1fff62c037cf3cf559f6dbafd/decider-0.8b-Q4_K_M.gguf',
}


@dataclass(frozen=True)
class Decision:
    choice: str | None
    probabilities: dict
    status: str
    elapsed_ms: float


class LocalDecisionEngine:
    """Explicit load/close; separate from the chat-model catalog and identity.

    At most 8 options, bounded input, single native evaluation, no prefix reuse
    across requests (Qwen3.5 has recurrent state). No import of torch/transformers.
    """
    def __init__(self, model_path, *, factory=None, n_ctx=1024, min_confidence=.80, min_margin=.20):
        if not 0 <= min_confidence <= 1 or not 0 <= min_margin <= 1:
            raise ValueError('Invalid decision thresholds')
        self.path = Path(model_path)
        self.factory = factory
        self.n_ctx = n_ctx
        self.min_confidence, self.min_margin = min_confidence, min_margin
        self._native = None
        self._native_guard = None
        self.backend_info = {'kind':'cpu','reason':'not_loaded'}
        self.load_metrics = {}
        self._lock = threading.Lock()

    @native_work
    def load(self):
        with self._lock:
            if self._native is not None:
                return
            start = time.perf_counter()
            if self.path.stat().st_size != DECIDER_MODEL['size_bytes']:
                raise ValueError('Decider size mismatch')
            if not verified_models.valid(self.path, DECIDER_MODEL):
                raise ValueError('Decider checksum mismatch or file changed')
            verified = time.perf_counter()
            factory = self.factory
            from allma_model.llm.native_backend import BackendChoice
            choice = BackendChoice(reason='decision_cpu')
            if factory is None:
                from allma_model.llm.decision_backend import prepare_android_backend
                choice = prepare_android_backend()
                from llama_cpp import Llama
                factory = Llama
                if choice.device_ids is not None and not getattr(factory,'_allma_explicit_devices',False):
                    raise RuntimeError('Bundled runtime lacks Decider device isolation')
            prepared = time.perf_counter()
            arguments = dict(model_path=str(self.path), n_ctx=self.n_ctx, n_batch=self.n_ctx,
                             n_threads=2, n_threads_batch=2, logits_all=False, verbose=False)
            try:
                with choice.guard.operation() if choice.guard else nullcontext():
                    native = factory(**dict(arguments, **choice.kwargs))
            except Exception:
                if choice.kind!='hexagon':raise
                choice = choice.cpu_fallback('npu_model_initialization_failed')
                native = factory(**dict(arguments, **choice.kwargs))
            loaded = time.perf_counter()
            try:
                self._labels = []
                for label in 'ABCDEFGH':
                    ids = native.tokenize(label.encode(), add_bos=False, special=False)
                    if len(ids) != 1:
                        raise ValueError('Unsupported Decider label tokenizer')
                    self._labels.append(ids[0])
                if len(set(self._labels)) != 8:
                    raise ValueError('Duplicate decision label tokens')
                self._native_guard = choice.guard
                self.backend_info = {'kind':choice.kind,'reason':choice.reason}
                self._native = native
                finished = time.perf_counter()
                self.load_metrics = {'verification_ms': (verified-start)*1000,
                                     'backend_ms': (prepared-verified)*1000,
                                     'model_ms': (loaded-prepared)*1000,
                                     'labels_ms': (finished-loaded)*1000,
                                     'total_ms': (finished-start)*1000}
                logging.info('[DeciderBackend] backend=%s reason=%s',choice.kind,choice.reason)
                logging.info('[DeciderLoad] backend=%s verification_ms=%.1f backend_ms=%.1f model_ms=%.1f labels_ms=%.1f total_ms=%.1f',
                             choice.kind, *self.load_metrics.values())
            except Exception:
                native.close()
                raise

    @native_work
    def decide(self, state, question, options, *, cancel_event=None):
        if not isinstance(state, str) or len(state) > 8000:
            raise ValueError('Decision state must be text up to 8000 characters')
        if not isinstance(question, str) or not question.strip() or len(question) > 500:
            raise ValueError('Invalid decision question')
        if not isinstance(options, dict) or not 2 <= len(options) <= 8:
            raise ValueError('A decision needs 2..8 named options')
        if any(not isinstance(k, str) or not k or not isinstance(v, str) or not v.strip()
               or len(k) > 64 or len(v) > 400 for k, v in options.items()):
            raise ValueError('Invalid decision options')
        if cancel_event is not None and cancel_event.is_set():
            return Decision(None, {}, 'cancelled', 0)
        if not self._lock.acquire(blocking=False):
            return Decision(None, {}, 'busy', 0)
        start = time.perf_counter()
        try:
            native = self._native
            if native is None:
                return Decision(None, {}, 'unavailable', 0)
            if self.backend_info.get('kind')=='hexagon':
                from allma_model.llm.decision_backend import android_thermal_status
                if android_thermal_status() not in (0,1):
                    return Decision(None, {}, 'thermal_pause', 0)
            # Match the upstream two-piece tokenization, without a chat template.
            head = native.tokenize(('Context:\n' + state).encode(), add_bos=False, special=False)
            suffix = '\n\nQuestion: ' + question + '\nOptions:'
            suffix += ''.join(f'\n({label}) {text}' for label, text in zip('ABCDEFGH', options.values()))
            suffix += '\nAnswer: ('
            tokens = head + native.tokenize(suffix.encode(), add_bos=False, special=False)
            if len(tokens) > self.n_ctx:
                return Decision(None, {}, 'context_limit', 0)
            # Explicit native memory clearing also supports wrappers whose
            # reset() only resets the Python token counter.
            with self._native_guard.operation() if self._native_guard else nullcontext():
                if self.factory is None:
                    import llama_cpp as L
                    L.llama_memory_clear(L.llama_get_memory(native._ctx.ctx), True)
                native.reset()
                if cancel_event is not None and cancel_event.is_set():
                    return Decision(None, {}, 'cancelled', 0)
                native.eval(tokens)
                # Copy the bounded label scores while the native guard is held.
                row = native._ctx.get_logits()
                logits = [float(row[token]) / 1.03
                          for token in self._labels[:len(options)]]
            if not all(math.isfinite(value) for value in logits):
                return Decision(None, {}, 'invalid_scores', (time.perf_counter()-start)*1000)
            weights = [math.exp(value - max(logits)) for value in logits]
            probs = [value / sum(weights) for value in weights]
            order = sorted(range(len(probs)), key=probs.__getitem__, reverse=True)
            accepted = (probs[order[0]] >= self.min_confidence
                        and probs[order[0]] - probs[order[1]] >= self.min_margin)
            cancelled = cancel_event is not None and cancel_event.is_set()
            return Decision(list(options)[order[0]] if accepted and not cancelled else None,
                            dict(zip(options, probs)),
                            'cancelled' if cancelled else 'selected' if accepted else 'abstained',
                            (time.perf_counter()-start)*1000)
        finally:
            self._lock.release()

    @native_work
    def close(self):
        with self._lock:
            if self._native is not None:
                try:
                    with self._native_guard.operation() if self._native_guard else nullcontext():
                        self._native.close()
                finally:
                    self._native = None
                    self._native_guard = None
