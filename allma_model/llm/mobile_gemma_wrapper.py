"""MobileGemmaWrapper - Wrapper per il modello Gemma-2b su Android via llama.cpp"""

from __future__ import annotations
from allma_model.utils.generation_control import GenerationCancelled, check_cancelled
from allma_model.utils.repetition_guard import repetition_start
from .native_backend import native_operation, native_work
from .cpu_cancellation import CPUCancellation

import os
import logging
import threading
import re
from typing import List, Optional
from collections import OrderedDict

# Delayed import mechanism match
# We set this to True to bypass allma_core checks and let _load() handle the actual import/failure
LLAMA_CPP_AVAILABLE = True

# Default model path (relative to creating this class, but should be passed in)
# UPGRADED 2026-02-06: Qwen2.5-Coder-3B-Instruct-Abliterated (Bartowski)
_DEFAULT_MODEL_NAME = "qwen3-1.7b-q8_0.gguf"

class MobileGemmaWrapper:
    """
    Carica Gemma 2 2B (GGUF) e genera testo usando llama.cpp.
    Ottimizzato per Android/Mobile.
    """

    def __init__(self, models_dir: str, model_name: str = _DEFAULT_MODEL_NAME, n_ctx: int = 2048, system_monitor=None, reasoning=None, backend_preference=None):
        """
        Inizializza il wrapper mobile.
        
        Args:
            models_dir: Directory contenente i file .gguf
            model_name: Nome del file del modello
            n_ctx: Context window size
            system_monitor: Istanza per Adaptive Metabolic Coupling (V6.4)
        """
        if backend_preference not in (None, 'cpu'):
            raise ValueError('Only explicit CPU diagnostics may override backend selection')
        self.backend_preference = backend_preference
        self.models_dir = models_dir
        self.model_path = os.path.join(models_dir, model_name)
        self.n_ctx = n_ctx
        self.reasoning_capability = reasoning
        self.system_monitor = system_monitor
        self.llm = None
        self.inference_lock = threading.Lock() # <--- CRITICAL FIX: Global Lock
        self._conv_caches = OrderedDict()
        self._conv_cache_prefix = {}
        self._active_conv = None
        
        if not LLAMA_CPP_AVAILABLE:
            logging.error("Tentativo di inizializzare MobileGemmaWrapper senza llama_cpp installato.")
            return

        from .model_binding import select_model
        if model_name != _DEFAULT_MODEL_NAME and not os.path.isfile(self.model_path):
            raise ValueError('Selected model is unavailable')
        preferred = model_name if os.path.isfile(self.model_path) else None
        self.model_path = str(select_model(models_dir, preferred))

        size = os.path.getsize(self.model_path)
        logging.info(f"[MobileGemma] File exists! Size: {size} bytes ({size/(1024*1024):.2f} MB)")
        
        self._load()
        if self.llm is not None:
            from .model_binding import ModelBinding
            try:
                self.binding = ModelBinding.from_native(self.llm, self.n_ctx, self.reasoning_capability)
            except Exception:
                self.close()
                raise

    @native_work
    def _load(self):
        """Load the matched runtime once and keep CPU as a recoverable backend."""
        from contextlib import nullcontext
        from .native_backend import BackendChoice, prepare_android_backend
        self._native_guard = None
        self.backend_info = {'kind': 'cpu', 'reason': 'not_loaded'}
        try:
            force_cpu = getattr(self, 'backend_preference', None) == 'cpu'
            choice = prepare_android_backend(self.model_path, force_cpu=True) if force_cpu else prepare_android_backend(self.model_path)
            from llama_cpp import Llama
            if choice.device_ids is not None and not getattr(Llama, '_allma_explicit_devices', False):
                raise RuntimeError('Bundled runtime lacks explicit device isolation')
            try:
                import ctypes
                import llama_cpp.llama_cpp as native
                if not getattr(Llama, '_allma_light_cache_patched', False):
                    class LightState:
                        def __init__(self, input_ids, n_tokens, llama_state, llama_state_size):
                            self.input_ids = input_ids
                            self.n_tokens = n_tokens
                            self.llama_state = llama_state
                            self.llama_state_size = llama_state_size

                    def save_state(instance):
                        size = native.llama_get_state_size(instance._ctx.ctx)
                        state = (ctypes.c_uint8 * int(size))()
                        used = native.llama_copy_state_data(instance._ctx.ctx, state)
                        if not 0 < int(used) <= int(size):
                            raise RuntimeError('Invalid llama state size')
                        return LightState(instance.input_ids.copy(), instance.n_tokens,
                                          ctypes.string_at(ctypes.addressof(state), int(used)), int(used))

                    def load_state(instance, state):
                        instance.input_ids = state.input_ids.copy()
                        instance.n_tokens = int(state.n_tokens)
                        buffer = (ctypes.c_uint8 * int(state.llama_state_size)).from_buffer_copy(state.llama_state)
                        if native.llama_set_state_data(instance._ctx.ctx, buffer) != int(state.llama_state_size):
                            raise RuntimeError('Failed to restore llama state')

                    Llama.save_state = save_state
                    Llama.load_state = load_state
                    Llama._allma_light_cache_patched = True
            except (AttributeError, ImportError):
                pass

            mobile = 'ANDROID_PRIVATE' in os.environ or '/Users/' not in self.model_path
            threads = 4 if mobile else 8
            if choice.kind == 'cpu' and mobile and self.system_monitor and not force_cpu:
                try:
                    from allma_model.core.system_monitor import current_power_reading
                    state = self.system_monitor.get_metabolic_state()
                    if (current_power_reading(state) and state.is_power_save is False
                            and 0 < state.battery_temp_celsius < 30.0 and state.is_charging):
                        threads = 6
                except Exception as error:
                    logging.warning('[MobileGemma] Power reading unavailable: %s', error)
            arguments = dict(model_path=self.model_path, n_ctx=self.n_ctx,
                             n_threads=threads, n_batch=512, flash_attn=False,
                             use_mmap=True, use_mlock=False, verbose=True)
            if force_cpu:
                arguments.update(n_threads=4, n_threads_batch=4, n_ubatch=256)
            retry_cpu = False
            try:
                with choice.guard.operation('load') if choice.guard else nullcontext():
                    self.llm = Llama(**arguments, **choice.kwargs)
            except Exception as error:
                if choice.kind != 'opencl':
                    raise
                logging.warning('[MobileGemma] GPU model initialization failed; retrying CPU: %s', error)
                retry_cpu = True
            if retry_cpu:
                import gc
                gc.collect()
                choice = choice.cpu_fallback('gpu_model_initialization_failed')
                self.llm = Llama(**arguments, **choice.kwargs)
            self._native_guard = choice.guard
            self.backend_info = {'kind': choice.kind, 'reason': choice.reason, 'driver': choice.driver}
            self.backend_info['physical_batch'] = arguments.get('n_ubatch', choice.kwargs.get('n_ubatch', 512))
            self.backend_info['batch_threads'] = arguments.get('n_threads_batch', choice.kwargs.get('n_threads_batch'))
            logging.info('[NativeBackend] model=%s backend=%s reason=%s',
                         os.path.basename(self.model_path), choice.kind, choice.reason)
        except Exception as error:
            logging.error('[MobileGemma] Error loading model: %s', error)
            self.llm = None

    def prepare_chat(self, messages, budget, reasoning=True):
        from .model_binding import ModelBinding
        with self.inference_lock:
            if not self.llm:
                raise RuntimeError('Model is not loaded')
            if not hasattr(self, 'binding'):
                self.binding = ModelBinding.from_native(self.llm, self.n_ctx)
            return self.binding.prepare(messages, lambda data: self.llm.tokenize(data, add_bos=False, special=True), budget, reasoning)

    @native_work
    def close(self):
        with self.inference_lock:
            native, self.llm = self.llm, None
            if hasattr(self, '_conv_caches'):
                self._conv_caches.clear()
                self._conv_cache_prefix.clear()
            if hasattr(self, 'binding'):
                del self.binding
            if native is not None:
                native.close()

    @native_operation
    def generate(
        self,
        prompt: str,
        max_tokens: int = -1,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        callback: Optional[callable] = None, # Support streaming
        conversation_id: Optional[str] = None,
        prefix_hash: Optional[str] = None,
        prefix_prompt: Optional[str] = None,
        request_id: Optional[str] = None,
        repeat_penalty: Optional[float] = None,
        repeat_last_n: Optional[int] = None,
        cancel_event=None,
        thought_budget=None,
        allow_repetition=False,
        seed=None,
        answer_contract=None,
        top_k=None,
        min_p=None,
        native_prompt=False
    ) -> str:
        """
        Genera testo dato un prompt.
        Args:
            prompt: Può essere raw text o formatted chat.
            max_tokens: Limite token generati.
            callback: Funzione(str) chiamata per ogni token generato.
        """
        check_cancelled(cancel_event)
        if not self.llm:
            return "Error: Model not loaded."

        # Default stop tokens for Qwen 2.5 (ChatML) if none provided
        if stop is None:
            stop = ["<|im_end|>", "<|endoftext|>"]

        try:
            def strip_think(text: str) -> str:
                from allma_model.utils.thinking_stream import answer_from_completion
                return answer_from_completion(text, prompt)

            # Adapt older internal prompt call sites (dreams/reasoning) too.
            metadata = getattr(self.llm, 'metadata', None)
            if not native_prompt and isinstance(metadata, dict) and metadata.get('tokenizer.chat_template'):
                from .model_binding import legacy_messages
                messages = legacy_messages(prompt)
                if messages is None:
                    from allma_model.core.autobiographical_identity import system_instruction
                    messages = [{'role':'system','content':system_instruction()}, {'role':'user','content':prompt}]
                prepared = self.prepare_chat(messages, max_tokens, reasoning=thought_budget is not None)
                prompt = prepared.prompt
                stop = list(prepared.stops) or None
                native_prompt = True
                if not prepared.reasoning:
                    thought_budget = None

            import time
            from allma_model.ui.render_budget import gpu_render_budget
            lock_started = time.perf_counter()
            with self.inference_lock, gpu_render_budget(
                    enabled=getattr(self, 'backend_info', {}).get('kind') == 'opencl'), CPUCancellation(self, cancel_event) as native_cancel:
                lock_wait_ms = (time.perf_counter()-lock_started)*1000
                prepare_started = time.perf_counter()
                check_cancelled(cancel_event)
                import random
                random_seed = seed if type(seed) is int and 0 <= seed < 2**31 else random.randint(0, 2**31 - 1)
                stream_mode = callback is not None or cancel_event is not None
                self.last_generation = {
                    "request_id": request_id,
                    "backend": getattr(self, "backend_info", {}).get("kind", "cpu"),
                    "physical_batch": getattr(self, "backend_info", {}).get("physical_batch"),
                    "native_cpu_cancellation": native_cancel.supported,
                    "render_budget_hz": 60 if getattr(self, "backend_info", {}).get("kind") == 'opencl' else None,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "stop": stop,
                    "repeat_penalty": repeat_penalty,
                    "repeat_last_n": repeat_last_n,
                    "seed": random_seed,
                    "lock_wait_ms": lock_wait_ms,
                    "stream": stream_mode,
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "total_tokens": None,
                    "finish_reason": None,
                    "ttft_ms": None,
                }
                if not hasattr(self, "_generation_meta_by_id"):
                    self._generation_meta_by_id = {}

                try:
                    use_prefix_state_cache = False

                    hybrid = getattr(getattr(self, 'binding', None), 'architecture', '') in {'qwen35', 'qwen35moe'}
                    if conversation_id and hasattr(self.llm, "set_cache") and not hybrid:
                        from llama_cpp import LlamaCache
                        conv = str(conversation_id)
                        prev_prefix = self._conv_cache_prefix.get(conv)
                        if prev_prefix is None or (prefix_hash and prev_prefix != prefix_hash):
                            self._conv_cache_prefix[conv] = prefix_hash or ""
                            self._conv_caches.pop(conv, None)
                            logging.info(f"[MobileGemma] Prompt cache invalidated conv={conv}")
                        cache = self._conv_caches.get(conv)
                        if cache is None:
                            cache = LlamaCache(capacity_bytes=(256 << 20))
                            self._conv_caches[conv] = cache
                        self._conv_caches.move_to_end(conv)
                        while len(self._conv_caches) > 2:
                            old_conv, _ = self._conv_caches.popitem(last=False)
                            self._conv_cache_prefix.pop(old_conv, None)
                        self.llm.set_cache(cache)
                        if getattr(self, "_active_conv", None) != conv:
                            logging.info(f"[MobileGemma] Prompt cache enabled conv={conv}")
                        self._active_conv = conv
                    else:
                        if getattr(self, "_active_conv", None) is not None and hasattr(self.llm, "set_cache"):
                            self.llm.set_cache(None)
                            logging.info("[MobileGemma] Prompt cache disabled")
                        self._active_conv = None
                except Exception:
                    pass

                # Calcola dinamicamente i token liberi nel contesto
                if max_tokens == -1:
                    try:
                        prompt_token_count = len(self.llm.tokenize(prompt.encode("utf-8")))
                    except Exception:
                        prompt_token_count = len(prompt) // 4  # stima approssimativa
                    # Riserva 64 token di margine di sicurezza
                    max_tokens = max(64, self.n_ctx - prompt_token_count - 64)
                    logging.info(f"[MobileGemma] Dynamic max_tokens={max_tokens} (ctx={self.n_ctx}, prompt={prompt_token_count} tokens)")
                    self.last_generation["max_tokens"] = max_tokens
                    self.last_generation["prompt_tokens"] = int(prompt_token_count)
                else:
                    try:
                        self.last_generation["prompt_tokens"] = int(len(self.llm.tokenize(prompt.encode("utf-8"))))
                    except Exception:
                        pass

                from allma_model.utils.prompt_budget import fit_prompt
                # Reserve enough context for both reasoning and final answer. Do not
                # silently cut the current question when old history fills the window.
                if native_prompt:
                    native_tokens = self.llm.tokenize(prompt.encode('utf-8'), add_bos=False, special=True)
                    if len(native_tokens) > self.n_ctx-max_tokens-32:
                        raise ValueError('Prepared native prompt exceeds context')
                    removed_turns = 0
                    prompt_count = len(native_tokens)
                else:
                    prompt, removed_turns = fit_prompt(prompt, self.llm.tokenize, self.n_ctx, max_tokens)
                    prompt_count = len(self.llm.tokenize(prompt.encode('utf-8')))
                self.last_generation['history_turns_removed'] = removed_turns
                self.last_generation['prompt_tokens'] = prompt_count

                logging.info(f"[MobileGemma] Generating response (Stream={stream_mode}, Seed={random_seed})")
                grammar = None
                if answer_contract:
                    from allma_model.utils.output_contract import native_grammar
                    grammar = native_grammar(answer_contract)
                self.last_generation['answer_contract'] = answer_contract
                self.last_generation['answer_grammar_active'] = grammar is not None
                self.last_generation['prompt_prepare_ms'] = (time.perf_counter()-prepare_started)*1000

                llm_kwargs = dict(
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    stop=stop,
                    echo=False,
                    stream=stream_mode,
                    seed=random_seed
                )
                if top_k is not None:
                    llm_kwargs['top_k'] = int(top_k)
                    self.last_generation['top_k'] = int(top_k)
                if min_p is not None:
                    llm_kwargs['min_p'] = float(min_p)
                    self.last_generation['min_p'] = float(min_p)
                if repeat_penalty is not None:
                    llm_kwargs["repeat_penalty"] = float(repeat_penalty)
                if repeat_last_n is not None:
                    if hasattr(self.llm, 'last_n_tokens_size'):
                        self.llm.last_n_tokens_size = max(16,min(512,int(repeat_last_n)))
                    else:
                        llm_kwargs["repeat_last_n"] = int(repeat_last_n)

                generation_llm = self.llm
                if native_prompt:
                    from .model_binding import NativeCompletion
                    generation_llm = NativeCompletion(self.llm)
                if thought_budget is not None and prompt.rstrip().endswith('<think>'):
                    from allma_model.utils.generation_budget import bounded_completion
                    output = bounded_completion(generation_llm, prompt, llm_kwargs, thought_budget,
                                                callback, cancel_event, allow_repetition=allow_repetition, answer_grammar=grammar)
                    self.last_generation.update(output['budget_meta'])
                    stream_mode = False  # callbacks were delivered by the bounded iterator
                else:
                    from allma_model.utils.repetition_guard import completion_with_compat
                    if grammar is not None:
                        llm_kwargs['grammar'] = grammar
                    output = completion_with_compat(generation_llm, prompt, llm_kwargs)

                if stream_mode:
                    full_text = ""
                    generated_text = ""
                    import time
                    gen_t0 = time.perf_counter()
                    first_token_ts = None
                    
                    # --- V6.5 DECOUPLED THERMAL PACING (RACE TO SLEEP) ---
                    # Il vero pacing ora vive nell'UI JS (Buffer Sinuoso).
                    # Qui rimuoviamo quasi totalmente i freni per fare finire la CPU 
                    # il prima possibile ("Race to Sleep"), raffreddandola in anticipo.
                    pacing_delay = 0.0  # Massima velocità, 0ms
                    if getattr(self, 'system_monitor', None):
                        try:
                            from allma_model.core.system_monitor import current_power_reading
                            state = self.system_monitor.get_metabolic_state()
                            if state.battery_temp_celsius > 40.0:
                                pacing_delay = 0.02  # Leggero underclock di sicurezza (20ms)
                                # Avoid log spam on every generation, log only at start
                                logging.info(f"[MobileGemma] 🥵 PACING TERMICO RIDOTTO: {state.battery_temp_celsius}°C. Pacing: {pacing_delay}s")
                            elif (current_power_reading(state) and state.is_power_save is False
                                  and 0 < state.battery_temp_celsius < 30.0 and state.is_charging):
                                pacing_delay = 0.0 # Overdrive Assoluto
                        except Exception as e:
                            logging.error(f"[MobileGemma] Thermal Pacing exception: {e}")
                    
                    try:
                        for chunk in output:
                            check_cancelled(cancel_event)
                            choice = chunk["choices"][0]
                            token = choice["text"]
                            native_finish = choice.get('finish_reason')
                            if native_finish in ('stop', 'length'):
                                self.last_generation['finish_reason'] = native_finish
                                self.last_generation['finish_reason_source'] = 'native_stream'
                            generated_text += token
                            if token and first_token_ts is None:
                                first_token_ts = time.perf_counter()
                                try:
                                    self.last_generation["ttft_ms"] = float((first_token_ts - gen_t0) * 1000.0)
                                except Exception:
                                    pass
                            candidate = full_text + token
                            loop = None if allow_repetition else repetition_start(candidate)
                            if loop is not None:
                                full_text = candidate[:loop]
                                self.last_generation['finish_reason'] = 'repetition'
                                self.last_generation['finish_reason_source'] = 'local_repetition_guard'
                                break
                            full_text = candidate
                            if callback:
                                try:
                                    callback(token)
                                except Exception as cb_err:
                                    logging.error(f"[MobileGemma] Stream callback error: {cb_err}")
                            if pacing_delay > 0:
                                time.sleep(pacing_delay)
                    finally:
                        if hasattr(output, 'close'):
                            output.close()
                    check_cancelled(cancel_event)
                    try:
                        self.last_generation["completion_tokens"] = int(len(self.llm.tokenize(generated_text.encode("utf-8"))))
                        self.last_generation['token_count_source'] = 'retokenized'
                        if self.last_generation.get("prompt_tokens") is not None:
                            self.last_generation["total_tokens"] = int(self.last_generation["prompt_tokens"] + self.last_generation["completion_tokens"])
                    except Exception:
                        pass
                    try:
                        ct = self.last_generation.get("completion_tokens")
                        mt = self.last_generation.get("max_tokens")
                        if self.last_generation.get('finish_reason') is None:
                            # Text can retokenize to fewer tokens than the live
                            # stream: this fallback must not override native EOF.
                            self.last_generation['finish_reason_source'] = 'retokenized_heuristic'
                            self.last_generation['finish_reason'] = (
                                'max_tokens' if ct is not None and mt is not None and mt != -1
                                and int(ct) >= int(mt) - 1 else 'stop')
                    except Exception:
                        pass
                    try:
                        if request_id:
                            self._generation_meta_by_id[request_id] = dict(self.last_generation)
                            if len(self._generation_meta_by_id) > 32:
                                self._generation_meta_by_id.pop(next(iter(self._generation_meta_by_id)))
                    except Exception:
                        pass
                    return strip_think(full_text)
                else:
                    raw_text = output["choices"][0]["text"]
                    try:
                        finish_reason = output["choices"][0].get("finish_reason")
                    except Exception:
                        finish_reason = None
                    try:
                        usage = output.get("usage") or {}
                    except Exception:
                        usage = {}
                    if isinstance(usage, dict) and usage:
                        self.last_generation["prompt_tokens"] = usage.get("prompt_tokens", self.last_generation.get("prompt_tokens"))
                        self.last_generation["completion_tokens"] = usage.get("completion_tokens", self.last_generation.get("completion_tokens"))
                        self.last_generation["total_tokens"] = usage.get("total_tokens", self.last_generation.get("total_tokens"))
                    if finish_reason:
                        self.last_generation["finish_reason"] = finish_reason
                    else:
                        if max_tokens != -1:
                            try:
                                completion_tokens = len(self.llm.tokenize(raw_text.encode("utf-8")))
                                self.last_generation["completion_tokens"] = int(completion_tokens)
                                if self.last_generation.get("prompt_tokens") is not None:
                                    self.last_generation["total_tokens"] = int(self.last_generation["prompt_tokens"] + completion_tokens)
                            except Exception:
                                pass
                        try:
                            ct = self.last_generation.get("completion_tokens")
                            mt = self.last_generation.get("max_tokens")
                            if ct is not None and mt is not None and mt != -1 and int(ct) >= int(mt) - 1:
                                self.last_generation["finish_reason"] = "max_tokens"
                            else:
                                self.last_generation["finish_reason"] = self.last_generation.get("finish_reason") or "stop"
                        except Exception:
                            pass
                    clean_answer = strip_think(raw_text)
                    loop = None if allow_repetition else repetition_start(clean_answer)
                    if loop is not None:
                        clean_answer = clean_answer[:loop]
                        self.last_generation['finish_reason'] = 'repetition'
                    try:
                        if request_id:
                            self._generation_meta_by_id[request_id] = dict(self.last_generation)
                            if len(self._generation_meta_by_id) > 32:
                                self._generation_meta_by_id.pop(next(iter(self._generation_meta_by_id)))
                    except Exception:
                        pass
                    return clean_answer

        except GenerationCancelled:
            if request_id:
                previous = getattr(self, 'last_generation', {})
                metadata = dict(previous) if isinstance(previous, dict) and previous.get('request_id') == request_id else {'request_id':request_id}
                metadata.update(status='cancelled', finish_reason='cancelled')
                if 'native_cancel' in locals():metadata['native_cpu_abort_fired'] = native_cancel.fired
                self.last_generation = metadata
                if not isinstance(getattr(self,'_generation_meta_by_id',None),dict):self._generation_meta_by_id = {}
                self._generation_meta_by_id[request_id] = dict(metadata)
                while len(self._generation_meta_by_id) > 32:self._generation_meta_by_id.pop(next(iter(self._generation_meta_by_id)))
            raise
        except Exception as e:
            logging.error(f"[MobileGemma] Inference error: {e}")
            return f"Error during inference: {e}"

    def get_generation_meta(self, request_id: str):
        try:
            return getattr(self, "_generation_meta_by_id", {}).get(request_id)
        except Exception:
            return None
