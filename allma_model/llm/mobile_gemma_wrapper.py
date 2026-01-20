"""MobileGemmaWrapper - Wrapper per il modello Gemma-2b su Android via llama.cpp"""

from __future__ import annotations

import os
import logging
from typing import List, Optional

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    import traceback
    err = traceback.format_exc()
    logging.error(f"CRITICAL: llama-cpp-python import failed:\n{err}")
    print(f"CRITICAL: llama-cpp-python import failed:\n{err}")
    LLAMA_CPP_AVAILABLE = False

# Default model path (relative to creating this class, but should be passed in)
_DEFAULT_MODEL_NAME = "gemma-3n-e2b-it-q4_k_m.gguf"

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
        
        if not LLAMA_CPP_AVAILABLE:
            logging.error("Tentativo di inizializzare MobileGemmaWrapper senza llama_cpp installato.")
            return

        if not os.path.exists(self.model_path):
            logging.error(f"Modello non trovato in: {self.model_path}")
            return

        self._load()

    def _load(self):
        """Carica il modello con llama.cpp"""
        logging.info(f"[MobileGemma] Loading model from {self.model_path} ...")
        try:
            import sys
            logging.info(f"[MobileGemma] Initializing Llama with path={self.model_path}...")
            print(f"[MobileGemma] PRINT DEBUG: Initializing Llama...", flush=True)
            
            # PERMANENT FIX: Manually load libllama.so to bypass linker issues
            import os
            import ctypes
            
            # Possible locations for the library
            possible_paths = [
                # 1. Custom location in site-packages (where we put it via recipe/hotpatch)
                "/data/data/org.allma.allma_prime/files/app/_python_bundle/site-packages/llama_cpp/libllama.so",
                # 2. As a sibling to this file (if packaged near wrapper)
                os.path.join(os.path.dirname(__file__), "libllama.so"),
                # 3. Standard Android native lib dir (for distributed APKs)
                "/data/app/org.allma.allma_prime/lib/arm64/libllama.so",
                # 4. Fallback: Try to find it relative to site-packages root
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "_python_bundle", "site-packages", "llama_cpp", "libllama.so")
            ]
            
            lib_path = None
            for p in possible_paths:
                if os.path.exists(p):
                    lib_path = p
                    break
            
            if lib_path:
                print(f"[MobileGemma] Found libllama.so at {lib_path}, setting env...", flush=True)
                os.environ["LLAMA_CPP_LIB"] = lib_path
                try:
                    ctypes.CDLL(lib_path)
                    print(f"[MobileGemma] Pre-loaded {lib_path} successfully!", flush=True)
                except Exception as e:
                    print(f"[MobileGemma] FAILED to pre-load {lib_path}: {e}", flush=True)
            else:
                 print(f"[MobileGemma] WARNING: libllama.so NOT FOUND in any known path.", flush=True)

            # Use minimal args first to rule out bad params
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=512,          # Reduced context
                n_threads=1,        # 1 thread
                n_batch=1,          # 1 batch
                verbose=True
            )
            
            print(f"[MobileGemma] PRINT DEBUG: Llama Init Success!", flush=True)
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
    ) -> str:
        """
        Genera testo dato un prompt.
        Args:
            prompt: Può essere raw text o formatted chat.
            max_tokens: Limite token generati.
        """
        if not self.llm:
            return "Error: Model not loaded."

        # Default stop tokens for Gemma if none provided
        if stop is None:
            stop = ["<end_of_turn>"]

        try:
            # ABI FIX APPLIED (0.2.26 pinned). STREAMING DISABLED TO PREVENT CRASH.
            logging.info(f"[MobileGemma] Generating response (Start) - Streaming DISABLED")
            
            # --- DEBUGGING CRASH ---
            # Test 1: Tokenize
            try:
                logging.info("[MobileGemma] DEBUG: Attempting to tokenize prompt...")
                tokens = self.llm.tokenize(prompt.encode('utf-8'))
                logging.info(f"[MobileGemma] DEBUG: Tokenization successful. Loop: {len(tokens)} tokens.")
            except Exception as e_tok:
                logging.error(f"[MobileGemma] DEBUG: Tokenization CRASHED/FAILED: {e_tok}")
            
            # Test 2: Generate
            logging.info("[MobileGemma] DEBUG: Starting Generation...")
            output = self.llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=stop,
                echo=False,
                stream=False
            )
            
            return output['choices'][0]['text']

        except Exception as e:
            logging.error(f"[MobileGemma] Inference error: {e}")
            return f"Error during inference: {e}"
