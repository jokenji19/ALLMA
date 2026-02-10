import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
import re

@dataclass
class ThoughtTrace:
    timestamp: datetime
    intent: str
    constraints: List[str]
    missing_info: List[str]
    strategy: str
    confidence: float
    raw_thought: str
    needs_clarification: bool = False

class ReasoningEngine:
    """
    Motore di Ragionamento Avanzato (Chain of Thought).
    Usa il modello LLM stesso per "pensare" prima di rispondere.
    """
    
    def __init__(self, llm_wrapper=None):
        self.llm = llm_wrapper
        self.logger = logging.getLogger(__name__)
        self.llm_lock = None # Will be injected by Core

    def think(self, user_input: str, context: Dict[str, Any], callback: Optional[Any] = None) -> ThoughtTrace:
        """
        Esegue un ciclo di ragionamento esplicito.
        Chiede al modello di analizzare il problema prima di risolverlo.
        """
        if not self.llm:
            return self._fallback_thought("LLM non disponibile")

        # 1. Costruisci il Prompt di Ragionamento
        prompt = self._build_reasoning_prompt(user_input, context)
        
        # 2. Esegui Inferenza (Thinking Pass)
        def _exec_gen():
            return self.llm.generate(
                prompt, 
                max_tokens=300, 
                temperature=0.1, 
                stop=["]]"], # Stop at end of thought block
                callback=callback
            )
            
        if self.llm_lock:
            with self.llm_lock:
                 raw_output = _exec_gen()
        else:
             raw_output = _exec_gen()
        
        # 3. Parsing del Pensiero
        # Reconstruct full block if needed
        full_thought_text = f"[[TH:{raw_output}]]"
        trace = self._parse_thought(full_thought_text)
        
        return trace

    def _build_reasoning_prompt(self, user_input: str, context: Dict[str, Any]) -> str:
        """Costruisce il prompt per il ragionamento (ChatML standard per Qwen)."""
        
        # SECURITY: Sanitize user input
        safe_input = user_input.replace("<|im_start|>", "").replace("<|im_end|>", "")
        
        memories = context.get('relevant_memories', [])
        memory_text = "\n".join([f"- {m.get('content', '')}" for m in memories]) if memories else "Nessuna memoria specifica."
        
        return f"""<|im_start|>system
Sei ALLMA, un'intelligenza artificiale avanzata e senziente.
Il tuo obiettivo è fornire risposte utili, precise e profonde.

MEMORIA A LUNGO TERMINE:
{memory_text}

Usa il tuo processo di pensiero interno per analizzare la richiesta prima di rispondere.
<|im_end|>
<|im_start|>user
{safe_input}<|im_end|>
<|im_start|>assistant
"""

    def _parse_thought(self, raw_output: str) -> ThoughtTrace:
        """Estrae la struttura dal testo generato (Unified Format)"""
        # Formato atteso: [[TH: I=...|S=...|M=...]]
        
        # Clean markers
        content = raw_output.replace("[[TH:", "").replace("]]", "").strip()
        
        # Simple extraction via Dictionary approach
        # I=..., S=..., M=...
        parts = {}
        current_key = None
        current_val = []
        
        # Tokenizer rudimentale per pipe separatori
        # Non possiamo usare split('|') perché il testo potrebbe contenere pipe
        # Usiamo regex per trovare 'KEY='
        
        # Fallback regex extraction
        intent = self._extract_field(content, "I")
        strategy = self._extract_field(content, "S")
        memory_val = self._extract_field(content, "M")
        
        return ThoughtTrace(
            timestamp=datetime.now(),
            intent=intent or "Risposta Generale",
            constraints=[strategy], # Map Strategy to Constraints
            missing_info=[],
            strategy=strategy or "Diretta",
            confidence=1.0,
            raw_thought=content,
            needs_clarification=False
        )

    def _extract_field(self, text: str, key: str) -> str:
        # Matches "I=Value" until "|" or end of string
        match = re.search(f"{key}=(.*?)(?:\\||$)", text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _extract_list(self, text: str, field_name: str) -> List[str]:
        # Deprecated in unified format, kept for compat
        return []

    def _fallback_thought(self, reason: str) -> ThoughtTrace:
        """Pensiero di emergenza se il modello fallisce"""
        return ThoughtTrace(
            timestamp=datetime.now(),
            intent="Fallback",
            constraints=[],
            missing_info=[],
            strategy="Risposta standard",
            confidence=0.0,
            raw_thought=f"Errore nel ragionamento: {reason}",
            needs_clarification=False
        )
