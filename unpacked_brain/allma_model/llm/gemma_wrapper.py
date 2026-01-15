"""Wrapper per il modello Gemma-3n-E2B-it-int4.
Si occupa di caricare il modello quantizzato INT4 tramite transformers/
bitsandbytes e fornire un semplice metodo generate(prompt: str)."""

from __future__ import annotations

import os
from typing import List, Optional

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    GenerationConfig,
)

_DEFAULT_REPO = "google/gemma-3n-E4B-it"  # Nome repo su HuggingFace
_MODEL_CACHE_DIR = os.getenv("GEMMA_MODEL_DIR", os.path.join(os.path.dirname(__file__), "../../models/gemma-3n-E2B-it-int4"))

class GemmaGenerator:
    """Carica Gemma 3n (INT4) e genera testo."""

    def __init__(self, repo_id: str = _DEFAULT_REPO, cache_dir: Optional[str] = None):
        self.repo_id = repo_id
        self.cache_dir = cache_dir or _MODEL_CACHE_DIR
        self.tokenizer = None
        self.model = None
        self._load()

    def _load(self):
        # Config 4-bit quantization con bitsandbytes
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype="float16",
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )
        print(f"[GemmaGenerator] Loading model {self.repo_id} in {self.cache_dir} …")
        self.tokenizer = AutoTokenizer.from_pretrained(self.repo_id, cache_dir=self.cache_dir)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.repo_id,
            device_map="auto",
            quantization_config=bnb_config,
            cache_dir=self.cache_dir,
            trust_remote_code=True,
        )

    def generate(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
    ) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        gen_cfg = GenerationConfig(
            do_sample=True,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )
        output_ids = self.model.generate(**inputs, generation_config=gen_cfg)
        text = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        # Restituisci solo la parte generata dopo il prompt
        return text[len(prompt):].strip()
