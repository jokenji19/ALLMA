"""MobileGemmaWrapper - Wrapper per il modello Gemma-2b su Android via llama.cpp"""

from __future__ import annotations

import os
import logging
from typing import List, Optional

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logging.warning("llama-cpp-python not found. This is expected during desktop dev if not installed.")

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
            # -1 threads = auto detect on Android
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=-1, 
                verbose=False
            )
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
            output = self.llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=stop,
                echo=False 
            )
            # llama-cpp-python ritorna un dict in stile OpenAI
            # {'id': '...', 'object': 'text_completion', 'created': 123, 'model': '...', 'choices': [{'text': '...', ...}], ...}
            text = output['choices'][0]['text']
            return text.strip()
        except Exception as e:
            logging.error(f"[MobileGemma] Inference error: {e}")
            return f"Error during inference: {e}"
