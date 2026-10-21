"""MobileGemmaWrapper - Wrapper per il modello Gemma-2b su Android via llama.cpp"""

from __future__ import annotations
from allma_model.utils.generation_control import GenerationCancelled, check_cancelled
from allma_model.utils.repetition_guard import repetition_start

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

    def __init__(self, models_dir: str, model_name: str = _DEFAULT_MODEL_NAME, n_ctx: int = 2048, system_monitor=None, reasoning=None):  # Optimized: was 2048, keeping for performance
        """
        Inizializza il wrapper mobile.
        
        Args:
            models_dir: Directory contenente i file .gguf
            model_name: Nome del file del modello
            n_ctx: Context window size
            system_monitor: Istanza per Adaptive Metabolic Coupling (V6.4)
        """
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

    def _load(self):
        """Carica il modello con llama.cpp"""
        logging.info(f"[MobileGemma] Loading model from {self.model_path} ...")
        try:
            import sys
            import os
            import ctypes
            
            # --- CRITICAL: PRE-LOAD libggml.so GLOBALLY ---
            # llama-cpp-python usually fails because it can't find symbols from libggml.so
            private_root = os.environ.get("ANDROID_PRIVATE", "/data/data/org.allma.allma_prime/files/app")
            
            # Handle p4a structure variations
            if private_root.endswith("/app"):
                 base_internal = private_root
            else:
                 base_internal = os.path.join(private_root, "app")

            # PRIORITIZE INTERNAL LIBGGML (Vulkan/Optimized)
            internal_ggml = os.path.join(base_internal, "_python_bundle", "site-packages", "llama_cpp", "libggml.so")
            fallback_ggml = os.path.join(private_root, "libggml.so")
            candidate_dirs = [
                os.path.dirname(internal_ggml),
                os.path.join(base_internal, "site-packages", "llama_cpp"),
                os.path.join(private_root, "site-packages", "llama_cpp"),
                os.path.dirname(fallback_ggml),
            ]
            
            target_ggml = None
            if os.path.exists(internal_ggml):
                 target_ggml = internal_ggml
                 print(f"[MobileGemma] Found INTERNAL libggml.so at {internal_ggml}", flush=True)
            elif os.path.exists(fallback_ggml):
                 target_ggml = fallback_ggml
                 print(f"[MobileGemma] Found fallback libggml.so at {fallback_ggml}", flush=True)
            else:
                for d in candidate_dirs:
                    if not d or not os.path.exists(d):
                        continue
                    for name in ("libggml.so", "libggml-base.so"):
                        p = os.path.join(d, name)
                        if os.path.exists(p):
                            target_ggml = p
                            print(f"[MobileGemma] Found libggml at {p}", flush=True)
                            break
                    if target_ggml:
                        break
                    for f in os.listdir(d):
                        if f.startswith("libggml") and f.endswith(".so"):
                            target_ggml = os.path.join(d, f)
                            print(f"[MobileGemma] Found libggml variant: {target_ggml}", flush=True)
                            break
                    if target_ggml:
                        break
            
            if target_ggml:
                ggml_dir = os.path.dirname(target_ggml)
                print(f"[MobileGemma] Scanning for libggml dependencies in {ggml_dir}...", flush=True)
                
                # CRITICAL: Load backends (cpu, vulkan) FIRST
                # dlopen fails if these aren't loaded when libggml.so is loaded
                if os.path.exists(ggml_dir):
                    for f in os.listdir(ggml_dir):
                        if f.startswith("libggml-") and f.endswith(".so"):
                            # RESTORED (Build 163-v23): We MUST load libggml-vulkan.so because libggml.so is linked against it.
                            # We will disable actual GPU usage via env vars below.
                            
                            full_path = os.path.join(ggml_dir, f)
                            try:
                                ctypes.CDLL(full_path, mode=ctypes.RTLD_GLOBAL)
                                print(f"[MobileGemma] Pre-loaded backend: {f}", flush=True)
                            except Exception as e:
                                print(f"[MobileGemma] WARN: Failed to load backend {f}: {e}", flush=True)

                print(f"[MobileGemma] Pre-loading main libggml.so from {target_ggml}...", flush=True)
                
                # FORCE IGNORE VULKAN DEVICES (Virtual CPU Mode)
                # This prevents llama.cpp from finding the GPU even if the library is loaded.
                os.environ["GGML_VULKAN_DEVICE"] = "-1"
                os.environ["GGML_VK_VISIBLE_DEVICES"] = ""
                os.environ["GGML_VK_DISABLE_FUSION"] = "1" # Extra safety
                
                try:
                    ctypes.CDLL(target_ggml, mode=ctypes.RTLD_GLOBAL)
                    print("[MobileGemma] SUCCESS: libggml.so pre-loaded globally.", flush=True)
                except Exception as e:
                    print(f"[MobileGemma] WARNING: Failed to pre-load libggml.so: {e}", flush=True)
            else:
                print(f"[MobileGemma] CRITICAL: libggml not found (Checked: {internal_ggml}, {fallback_ggml})", flush=True)

            logging.info(f"[MobileGemma] Initializing Llama with path={self.model_path}...")
            print(f"[MobileGemma] PRINT DEBUG: Initializing Llama...", flush=True)
            
            # PERMANENT FIX: Respect main.py's smuggling and verify paths
            import os
            import ctypes
            
            # 0. Check if LLAMA_CPP_LIB is already set (by main.py)
            env_lib = os.environ.get("LLAMA_CPP_LIB")
            lib_path = None
            
            if env_lib and os.path.exists(env_lib):
                print(f"[MobileGemma] Env LLAMA_CPP_LIB set to: {env_lib}", flush=True)
                
                # CRITICAL FIX: main.py might forcefully set this to 'files/libllama.so' (stale)
                # If we found a better INTERNAL lib, we must override it.
                is_stale_fallback = "files/libllama.so" in env_lib or "libllama.so" in env_lib and "app" not in env_lib
                
                if is_stale_fallback and target_ggml:
                    # We have a valid internal ggml, so we should look for internal llama too
                    internal_llama_dir = os.path.dirname(target_ggml)
                    possible_internal_llama = os.path.join(internal_llama_dir, "libllama.so")
                    
                    if os.path.exists(possible_internal_llama):
                        print(f"[MobileGemma] OVERRIDE: Ignoring stale env lib {env_lib}. Switching to internal: {possible_internal_llama}", flush=True)
                        lib_path = possible_internal_llama
                        os.environ["LLAMA_CPP_LIB"] = lib_path
                    else:
                        print(f"[MobileGemma] Stale env lib detected but no internal libllama found at {possible_internal_llama}. Using env.", flush=True)
                        lib_path = env_lib
                else:
                    lib_path = env_lib
            else:
                print(f"[MobileGemma] env LLAMA_CPP_LIB is {env_lib} (missing or invalid), searching...", flush=True)
                
                # Possible locations for the library
                private_root = os.environ.get("ANDROID_PRIVATE", "/data/data/org.allma.allma_prime/files/app")
                
                # Handle p4a structure variations (files/app vs just files)
                if private_root.endswith("/app"):
                     base_internal = private_root
                else:
                     base_internal = os.path.join(private_root, "app")

                possible_paths = [
                    # 1. Custom location in site-packages (CORRECT NEW VERSION - VULKAN)
                    os.path.join(base_internal, "_python_bundle", "site-packages", "llama_cpp", "libllama.so"),
                     # 2. Site-packages direct (alternative p4a)
                    os.path.join(private_root, "site-packages", "llama_cpp", "libllama.so"),
                    # 3. Standard Android native lib dir (Fallback)
                    "/data/app/org.allma.allma_prime/lib/arm64/libllama.so",
                    # 4. As a sibling to this file
                    os.path.join(os.path.dirname(__file__), "libllama.so"),
                ]
                
                # REMOVED: os.path.join(private_root, "libllama.so") - This location contains STALE 20MB lib!
                
                for p in possible_paths:
                    if os.path.exists(p):
                        lib_path = p
                        size = os.path.getsize(p)
                        print(f"[MobileGemma] Found libllama.so at {p} (Size: {size} bytes)", flush=True)
                        break
                
                if not lib_path:
                    search_roots = [base_internal, private_root]
                    for root in search_roots:
                        if not os.path.exists(root):
                            continue
                        for dirpath, dirnames, filenames in os.walk(root):
                            if "libllama.so" in filenames:
                                candidate = os.path.join(dirpath, "libllama.so")
                                if "files/libllama.so" in candidate and "app" not in candidate:
                                    continue
                                lib_path = candidate
                                size = os.path.getsize(candidate)
                                print(f"[MobileGemma] Found libllama.so at {candidate} (Size: {size} bytes)", flush=True)
                                break
                        if lib_path:
                            break
            
            if lib_path:
                print(f"[MobileGemma] Resolved libllama.so at {lib_path}, setting env...", flush=True)
                os.environ["LLAMA_CPP_LIB"] = lib_path
                os.environ["LLAMA_CPP_LIB_PATH"] = os.path.dirname(lib_path)
                
                # --- OPENCL DIAGNOSTIC LOAD (Build 164-v2) ---
                try:
                    # 0. SEARCH FOR SYSTEM OPENCL
                    system_opencl_paths = [
                        "/vendor/lib64/libOpenCL.so",
                        "/system/vendor/lib64/libOpenCL.so",
                        "/system/lib64/libOpenCL.so",
                        "/vendor/lib64/libOpenCL-pixel.so", # Pixel devices
                        "/data/local/tmp/libOpenCL.so"      # Debug fallback
                    ]
                    
                    loaded_opencl = False
                    for ocl_path in system_opencl_paths:
                        if os.path.exists(ocl_path):
                            print(f"[MobileGemma] Found system OpenCL at {ocl_path}", flush=True)
                            try:
                                ctypes.CDLL(ocl_path)
                                print(f"[MobileGemma] SUCCESS: Pre-loaded system {ocl_path}", flush=True)
                                loaded_opencl = True
                                break
                            except Exception as e_ocl:
                                print(f"[MobileGemma] Failed to load system {ocl_path}: {e_ocl}", flush=True)
                    
                    if not loaded_opencl:
                         print(f"[MobileGemma] WARNING: System libOpenCL.so NOT FOUND or BLOCKED by Namespace.", flush=True)
                         print(f"[MobileGemma] Using internal statically-linked OpenCL proxy...", flush=True)

                    # 1. Try to load libggml-opencl.so from the same directory
                    lib_dir = os.path.dirname(lib_path)
                    opencl_lib = os.path.join(lib_dir, "libggml-opencl.so")
                    
                    if os.path.exists(opencl_lib):
                        print(f"[MobileGemma] Found libggml-opencl.so at {opencl_lib}", flush=True)
                        # We use RTLD_GLOBAL just in case libllama requires symbols from it
                        ctypes.CDLL(opencl_lib, mode=ctypes.RTLD_GLOBAL)
                        print(f"[MobileGemma] SUCCESS: Pre-loaded libggml-opencl.so via ctypes!", flush=True)
                        logging.info("[MobileGemma] GPU Backend Loaded: OpenCL")
                    else:
                        print(f"[MobileGemma] WARNING: libggml-opencl.so NOT FOUND in {lib_dir}", flush=True)
                        logging.warning("[MobileGemma] GPU Backend Missing: libggml-opencl.so")

                except Exception as e:
                    print(f"[MobileGemma] CRITICAL ERROR loading libggml-opencl.so: {e}", flush=True)
                    logging.error(f"[MobileGemma] GPU Init Failed: {e}")
                # ---------------------------------------------

                try:
                    ctypes.CDLL(lib_path)
                    print(f"[MobileGemma] Pre-loaded {lib_path} successfully!", flush=True)
                except Exception as e:
                    print(f"[MobileGemma] FAILED to pre-load {lib_path}: {e}", flush=True)
            else:
                 print(f"[MobileGemma] CRITICAL WARNING: libllama.so NOT FOUND in any known path. Search paths: {possible_paths}", flush=True)

            # --- LAZY IMPORT ---
            try:
                from llama_cpp import Llama
                print("[MobileGemma] Llama class imported successfully!", flush=True)
            except ImportError as e:
                print(f"[MobileGemma] ImportError for Llama class: {e}", flush=True)
                logging.error(f"ImportError detail: {e}")
                
                # ATTEMPT RECOVERY: CLEAR CONFLICTS
                try:
                    if "LLAMA_CPP_LIB" in os.environ:
                        print(f"[MobileGemma] Clearing LLAMA_CPP_LIB ({os.environ['LLAMA_CPP_LIB']}) and retrying...", flush=True)
                        del os.environ["LLAMA_CPP_LIB"]
                    
                    import importlib
                    import llama_cpp
                    importlib.reload(llama_cpp)
                    
                    from llama_cpp import Llama
                    print("[MobileGemma] RECOVERY SUCCESS: Llama class imported after reset.", flush=True)

                    try:
                        import ctypes
                        import llama_cpp.llama_cpp as _llama_cpp

                        if not getattr(Llama, "_allma_light_cache_patched", False):
                            class _ALLMALightState:
                                def __init__(self, input_ids, n_tokens: int, llama_state: bytes, llama_state_size: int):
                                    self.input_ids = input_ids
                                    self.n_tokens = n_tokens
                                    self.llama_state = llama_state
                                    self.llama_state_size = llama_state_size

                            def _save_state_light(self):
                                state_size = _llama_cpp.llama_get_state_size(self._ctx.ctx)
                                llama_state = (ctypes.c_uint8 * int(state_size))()
                                n_bytes = _llama_cpp.llama_copy_state_data(self._ctx.ctx, llama_state)
                                llama_state_compact = (ctypes.c_uint8 * int(n_bytes))()
                                ctypes.memmove(llama_state_compact, llama_state, int(n_bytes))
                                return _ALLMALightState(
                                    input_ids=self.input_ids.copy(),
                                    n_tokens=self.n_tokens,
                                    llama_state=bytes(llama_state_compact),
                                    llama_state_size=int(n_bytes),
                                )

                            def _load_state_light(self, state):
                                self.input_ids = state.input_ids.copy()
                                self.n_tokens = int(state.n_tokens)
                                LLamaStateArrayType = ctypes.c_uint8 * int(state.llama_state_size)
                                llama_state = LLamaStateArrayType.from_buffer_copy(state.llama_state)
                                if _llama_cpp.llama_set_state_data(self._ctx.ctx, llama_state) != int(state.llama_state_size):
                                    raise RuntimeError("Failed to set llama state data")

                            Llama.save_state = _save_state_light
                            Llama.load_state = _load_state_light
                            Llama._allma_light_cache_patched = True
                    except Exception:
                        pass
                    
                    # Limit threads based on environment
                    max_threads = 4 if getattr(self, 'models_dir', "").startswith("/data") else 8
                    
                    self.llm = Llama(
                        model_path=self.model_path,
                        n_ctx=self.n_ctx,
                        n_threads=max_threads, 
                        n_gpu_layers=0, # DEBUG: Force CPU to check if Vulkan is crashing
                        verbose=True
                    )
                    # If successful, we don't go to the main init block below, 
                    # but we need to ensure self.llm is set.
                    # Actually, better to just let it fall through or raise.
                    
                except Exception as e2:
                    print(f"[MobileGemma] RECOVERY FAILED: {e2}", flush=True)
                    # CRITICAL: Re-raise the ORIGINAL error to show in UI
                    raise e

            try:
                import ctypes
                import llama_cpp.llama_cpp as _llama_cpp

                if not getattr(Llama, "_allma_light_cache_patched", False):
                    class _ALLMALightState:
                        def __init__(self, input_ids, n_tokens: int, llama_state: bytes, llama_state_size: int):
                            self.input_ids = input_ids
                            self.n_tokens = n_tokens
                            self.llama_state = llama_state
                            self.llama_state_size = llama_state_size

                    def _save_state_light(self):
                        state_size = _llama_cpp.llama_get_state_size(self._ctx.ctx)
                        llama_state = (ctypes.c_uint8 * int(state_size))()
                        n_bytes = _llama_cpp.llama_copy_state_data(self._ctx.ctx, llama_state)
                        llama_state_compact = (ctypes.c_uint8 * int(n_bytes))()
                        ctypes.memmove(llama_state_compact, llama_state, int(n_bytes))
                        return _ALLMALightState(
                            input_ids=self.input_ids.copy(),
                            n_tokens=self.n_tokens,
                            llama_state=bytes(llama_state_compact),
                            llama_state_size=int(n_bytes),
                        )

                    def _load_state_light(self, state):
                        self.input_ids = state.input_ids.copy()
                        self.n_tokens = int(state.n_tokens)
                        LLamaStateArrayType = ctypes.c_uint8 * int(state.llama_state_size)
                        llama_state = LLamaStateArrayType.from_buffer_copy(state.llama_state)
                        if _llama_cpp.llama_set_state_data(self._ctx.ctx, llama_state) != int(state.llama_state_size):
                            raise RuntimeError("Failed to set llama state data")

                    Llama.save_state = _save_state_light
                    Llama.load_state = _load_state_light
                    Llama._allma_light_cache_patched = True
            except Exception:
                pass

            # PERFORMANCE OPTIMIZATION (2026-02-02):
            # Real-world testing revealed unacceptable slowness (20-40s responses).
            # Root causes:
            # 1. n_ctx=4096 creates massive overhead (exponential slowdown)
            # 2. n_threads=4 uses only 50% of S25 Ultra's 8 cores
            # 3. n_batch=128 underutilizes GPU bandwidth
            #
            # New "Performance Mode" config:
            # - Halve context (4096→2048): -50% memory, +70% speed
            # - Double threads (4→8): use all cores, +40% speed  
            # - Double batch (128→256): better GPU utilization, +20% speed
            #
            # Expected: 2-3x total speedup (20-40s → 7-15s)
            # Trade-off: Shorter conversation memory (10 exchanges → 5-7)
            
            # VULKAN RESTORATION (Build 163-v18)
            # OpenCL blocked by Android Namespace (clns-9).
            # Reverting to Vulkan with STABILITY FLAGS to prevent crash.
            
            # CPU FALLBACK (Build 163-v21)
            # Vulkan Shaders rejected by Adreno 830 Driver (Pipeline create failed).
            # Forcing CPU mode to guarantee stability.
            
            # --- FUTURE GPU ENABLEMENT (ADRENO 830) ---
            # To re-enable GPU acceleration when drivers/llama.cpp are updated:
            # 1. Uncomment the flags below.
            # 2. Set n_gpu_layers = 99.
            # 
            # os.environ["GGML_VK_DISABLE_FUSION"] = "1"  # Stability
            # os.environ["GGML_VK_DISABLE_F16"] = "1"      # Stability
            # os.environ["GGML_VK_DISABLE_COOPMAT"] = "1"  # Stability
            # ------------------------------------------

            # Limit threads based on environment to avoid OS freezing
            # If we're on android (/data/...), give 4 threads to LLM, keep 4 for OS/Async
            is_mobile = getattr(self, '_is_android', True) # Assumed true if not explicitly mock
            try:
                if "/Users/" in self.model_path: is_mobile = False
            except: pass
            
            safe_threads = 4 if is_mobile else 8
            
            # --- V6.4 ADAPTIVE METABOLIC COUPLING (OVERDRIVE INIT) ---
            if is_mobile and getattr(self, 'system_monitor', None):
                try:
                    state = self.system_monitor.get_metabolic_state()
                    # Overdrive: < 30C and charging
                    if state.battery_temp_celsius > 0 and state.battery_temp_celsius < 30.0 and state.is_charging:
                        safe_threads = 6
                        print(f"[MobileGemma] 🚀 OVERDRIVE Attivato! Temp: {state.battery_temp_celsius}°C. Threads: {safe_threads}", flush=True)
                    else:
                        print(f"[MobileGemma] 🏎️ Comfort Mode. Temp: {state.battery_temp_celsius}°C. Threads: {safe_threads}", flush=True)
                except Exception as e:
                    print(f"[MobileGemma] Errore lettura SystemMonitor per Overdrive: {e}", flush=True)

            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=safe_threads,   # Hybrid Arch: leave cores for AsyncIO and OS
                n_batch=512,        # Performance: High batch for CPU
                n_gpu_layers=0,     # CPU FALLBACK: Disabled GPU to eliminate OpenCL dispatch latency
                flash_attn=False,
                use_mmap=True,
                use_mlock=False,
                verbose=True
            )
            
            print(f"[MobileGemma] PRINT DEBUG: Llama Init Success! (CPU-ONLY MODE)", flush=True)
            logging.info("[MobileGemma] Model loaded successfully.")
        except Exception as e:
            logging.error(f"[MobileGemma] Error loading model: {e}")
            self.llm = None

    def prepare_chat(self, messages, budget, reasoning=True):
        from .model_binding import ModelBinding
        with self.inference_lock:
            if not self.llm:
                raise RuntimeError('Model is not loaded')
            if not hasattr(self, 'binding'):
                self.binding = ModelBinding.from_native(self.llm, self.n_ctx)
            return self.binding.prepare(messages, lambda data: self.llm.tokenize(data, add_bos=False, special=True), budget, reasoning)

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
            lock_started = time.perf_counter()
            with self.inference_lock:
                lock_wait_ms = (time.perf_counter()-lock_started)*1000
                prepare_started = time.perf_counter()
                check_cancelled(cancel_event)
                import random
                random_seed = seed if type(seed) is int and 0 <= seed < 2**31 else random.randint(0, 2**31 - 1)
                stream_mode = callback is not None or cancel_event is not None
                self.last_generation = {
                    "request_id": request_id,
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
                            state = self.system_monitor.get_metabolic_state()
                            if state.battery_temp_celsius > 40.0:
                                pacing_delay = 0.02  # Leggero underclock di sicurezza (20ms)
                                # Avoid log spam on every generation, log only at start
                                logging.info(f"[MobileGemma] 🥵 PACING TERMICO RIDOTTO: {state.battery_temp_celsius}°C. Pacing: {pacing_delay}s")
                            elif state.battery_temp_celsius > 0 and state.battery_temp_celsius < 30.0 and state.is_charging:
                                pacing_delay = 0.0 # Overdrive Assoluto
                        except Exception as e:
                            logging.error(f"[MobileGemma] Thermal Pacing exception: {e}")
                    
                    try:
                        for chunk in output:
                            check_cancelled(cancel_event)
                            token = chunk["choices"][0]["text"]
                            generated_text += token
                            if first_token_ts is None:
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
                        if self.last_generation.get("prompt_tokens") is not None:
                            self.last_generation["total_tokens"] = int(self.last_generation["prompt_tokens"] + self.last_generation["completion_tokens"])
                    except Exception:
                        pass
                    try:
                        ct = self.last_generation.get("completion_tokens")
                        mt = self.last_generation.get("max_tokens")
                        if self.last_generation.get('finish_reason') != 'repetition' and ct is not None and mt is not None and mt != -1 and int(ct) >= int(mt) - 1:
                            self.last_generation["finish_reason"] = "max_tokens"
                        else:
                            self.last_generation["finish_reason"] = self.last_generation.get("finish_reason") or "stop"
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
            raise
        except Exception as e:
            logging.error(f"[MobileGemma] Inference error: {e}")
            return f"Error during inference: {e}"

    def get_generation_meta(self, request_id: str):
        try:
            return getattr(self, "_generation_meta_by_id", {}).get(request_id)
        except Exception:
            return None
