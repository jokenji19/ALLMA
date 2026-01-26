"""MobileGemmaWrapper - Wrapper per il modello Gemma-2b su Android via llama.cpp"""

from __future__ import annotations

import os
import logging
import threading # <--- Added
from typing import List, Optional

# Delayed import mechanism match
# We set this to True to bypass allma_core checks and let _load() handle the actual import/failure
LLAMA_CPP_AVAILABLE = True

# Default model path (relative to creating this class, but should be passed in)
_DEFAULT_MODEL_NAME = "Hermes-3-Llama-3.2-3B.Q4_K_M.gguf"

class MobileGemmaWrapper:
    """
    Carica Gemma 2 2B (GGUF) e genera testo usando llama.cpp.
    Ottimizzato per Android/Mobile.
    """

    def __init__(self, models_dir: str, model_name: str = _DEFAULT_MODEL_NAME, n_ctx: int = 2048):
        """
        Inizializza il wrapper mobile.
        
        Args:
            models_dir: Directory contenente i file .gguf
            model_name: Nome del file del modello
            n_ctx: Context window size
        """
        self.models_dir = models_dir
        self.model_path = os.path.join(models_dir, model_name)
        self.n_ctx = n_ctx
        self.llm = None
        self.inference_lock = threading.Lock() # <--- CRITICAL FIX: Global Lock
        
        if not LLAMA_CPP_AVAILABLE:
            logging.error("Tentativo di inizializzare MobileGemmaWrapper senza llama_cpp installato.")
            return

        if not os.path.exists(self.model_path):
            logging.error(f"Modello non trovato in: {self.model_path}")
            return
            
        size = os.path.getsize(self.model_path)
        logging.info(f"[MobileGemma] File exists! Size: {size} bytes ({size/(1024*1024):.2f} MB)")
        
        self._load()

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
            libggml_path = os.path.join(private_root, "libggml.so")
            
            if os.path.exists(libggml_path):
                print(f"[MobileGemma] Pre-loading libggml.so from {libggml_path}...", flush=True)
                try:
                    ctypes.CDLL(libggml_path, mode=ctypes.RTLD_GLOBAL)
                    print("[MobileGemma] SUCCESS: libggml.so pre-loaded globally.", flush=True)
                except Exception as e:
                    print(f"[MobileGemma] WARNING: Failed to pre-load libggml.so: {e}", flush=True)
            else:
                print(f"[MobileGemma] libggml.so NOT FOUND at {libggml_path}", flush=True)

            logging.info(f"[MobileGemma] Initializing Llama with path={self.model_path}...")
            print(f"[MobileGemma] PRINT DEBUG: Initializing Llama...", flush=True)
            
            # PERMANENT FIX: Respect main.py's smuggling and verify paths
            import os
            import ctypes
            
            # 0. Check if LLAMA_CPP_LIB is already set (by main.py)
            env_lib = os.environ.get("LLAMA_CPP_LIB")
            lib_path = None
            
            if env_lib and os.path.exists(env_lib):
                print(f"[MobileGemma] Using env LLAMA_CPP_LIB: {env_lib}", flush=True)
                lib_path = env_lib
            else:
                print(f"[MobileGemma] env LLAMA_CPP_LIB is {env_lib} (missing or invalid), searching...", flush=True)
                
                # Possible locations for the library
                private_root = os.environ.get("ANDROID_PRIVATE", "/data/data/org.allma.allma_prime/files/app")
                possible_paths = [
                    # 1. The smuggled location (MOST LIKELY)
                    os.path.join(private_root, "libllama.so"),
                    # 2. Custom location in site-packages
                    os.path.join(private_root, "_python_bundle/site-packages/llama_cpp/libllama.so"),
                    # 3. As a sibling to this file
                    os.path.join(os.path.dirname(__file__), "libllama.so"),
                    # 4. Standard Android native lib dir
                    "/data/app/org.allma.allma_prime/lib/arm64/libllama.so",
                ]
                
                for p in possible_paths:
                    if os.path.exists(p):
                        lib_path = p
                        break
            
            if lib_path:
                print(f"[MobileGemma] Resolved libllama.so at {lib_path}, setting env...", flush=True)
                os.environ["LLAMA_CPP_LIB"] = lib_path
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
            except ImportError:
                print("[MobileGemma] ImportError for Llama class. Re-trying with manual extensive lib check...", flush=True)
                # Fallback: Try to force load libraries again manually just in case
                if lib_path:
                    try:
                       ctypes.CDLL(lib_path, mode=ctypes.RTLD_GLOBAL)
                    except: pass
                
                from llama_cpp import Llama # Retry or fail hard

            # STABILIZATION FIX (2026-01-26):
            # The previous setting (Batch=256, Threads=8) caused crashes during LONG generation.
            # We are switching to "Safe Mode" to prioritize stability over raw speed.
            
            # import gc and gc.collect() are already above
            import gc
            gc.collect()

            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=4096,         # RESTORED FULL QUALITY (v163)
                                    # Concurrency Crash fixed via Lock.
                                    # OOM Risk handled by mmap=True.
                n_threads=4,        # Stable Threads
                n_batch=128,        # Stable Batch
                use_mmap=True,      # Mmap Active
                use_mlock=False,
                verbose=True
            )
            
            print(f"[MobileGemma] PRINT DEBUG: Llama Init Success! (Threads: 8)", flush=True)
            logging.info("[MobileGemma] Model loaded successfully.")
        except Exception as e:
            logging.error(f"[MobileGemma] Error loading model: {e}")
            self.llm = None

    def generate(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        callback: Optional[callable] = None # Support streaming
    ) -> str:
        """
        Genera testo dato un prompt.
        Args:
            prompt: Può essere raw text o formatted chat.
            max_tokens: Limite token generati.
            callback: Funzione(str) chiamata per ogni token generato.
        """
        if not self.llm:
            return "Error: Model not loaded."

        # Default stop tokens for Gemma if none provided
        if stop is None:
            stop = ["<end_of_turn>"]

        try:
            # CRITICAL: LOCK THE LLM. 
            # Prevents "Dream Cycle" / Background threads from crashing the engine 
            # while main chat is generating.
            with self.inference_lock:
                # Enable streaming if callback is provided
                stream_mode = (callback is not None)
                
                logging.info(f"[MobileGemma] Generating response (Stream={stream_mode})")
                
                output = self.llm(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    stop=stop,
                    echo=False,
                    stream=stream_mode 
                )
                
                if stream_mode:
                    text_buffer = ""
                    for chunk in output:
                        # llama-cpp-python stream chunk format:
                        # {'id': '...', 'object': 'text_completion', 'created': 123, 'model': '...', 'choices': [{'text': 'T', 'index': 0, 'logprobs': None, 'finish_reason': None}]}
                        token = chunk['choices'][0]['text']
                        text_buffer += token
                        if callback:
                            callback(token)
                    return text_buffer
                else:
                    return output['choices'][0]['text']

        except Exception as e:
            logging.error(f"[MobileGemma] Inference error: {e}")
            return f"Error during inference: {e}"
