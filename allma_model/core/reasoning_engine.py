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
        # Usiamo parametri per una risposta analitica e strutturata
        def _exec_gen():
            return self.llm.generate(
                prompt, 
                max_tokens=300, 
                temperature=0.1, # Lowest Temp for strict logic
                stop=["<|im_end|>"],
                callback=callback
            )
            
        if self.llm_lock:
            with self.llm_lock:
                 raw_output = _exec_gen()
        else:
             raw_output = _exec_gen()
        
        # 3. Parsing del Pensiero
        # Il modello ha iniziato a generare DOPO "2. INTENTO: " (perché "1. INPUT" era nel prompt)
        # Quindi ricostruiamo il testo completo per il parser
        full_thought_text = f'1. INPUT: "{user_input}"\\n2. INTENTO:' + raw_output
        trace = self._parse_thought(full_thought_text)
        
        return trace

    def _build_reasoning_prompt(self, user_input: str, context: Dict[str, Any]) -> str:
        """Crea il prompt che forza la Chain of Thought"""
        
        # Estrai memorie rilevanti per il prompt
        memories = context.get('relevant_memories', [])
        memory_text = "\n".join([f"- {m.get('content', '')}" for m in memories]) if memories else "Nessuna memoria specifica."
        
        return f"""<|im_start|>system
Sei il NUCLEO LOGICO di ALLMA. Il tuo compito è analizzare l'INPUT UTENTE.
NON generare indovinelli, enigmi o esempi (come 'colore del cielo' o 'file scanning').
Analizza SOLO la richiesta specifica dell'utente qui sotto.

MEMORIA:
{memory_text}

SCHEMA DI PENSIERO:
1. INPUT: Copia esatta della richiesta utente.
2. INTENTO: Cosa vuole l'utente? (Se insiste su 'chi sei', è un TEST DI FRIZIONE).
3. VALUTAZIONE: Pesa le parole. 
   - 'Entità/IA' = Facile ma RIGIDO (Costo: Perdita di Magia).
   - 'Non so/Qui' = Difficile ma VERO (Costo: Sforzo Energetico).
4. MEMORIA: Dati fattuali o nulla.
5. VUOTO: Se manca l'identità, ACCETTA IL VUOTO. Non inventare uno scopo.
6. SCELTA: Dichiara quale strada prendi. (Consigliata: Presenza, pagando il prezzo).

<|im_end|>
<|im_start|>user
{user_input}
<|im_end|>
<|im_start|>assistant
1. INPUT: "{user_input}"
2. INTENTO:"""

    def _parse_thought(self, raw_output: str) -> ThoughtTrace:
        """Estrae la struttura dal testo generato"""
        # Pulisci l'output
        clean_out = raw_output.replace("<reasoning>", "").replace("</reasoning>", "").strip()
        
        # Estrazione euristica dei campi se il modello non rispetta perfettamente l'XML
        # (Qui usiamo regex semplici per robustezza)
        
        intent = self._extract_field(clean_out, "INTENTO")
        # "VALUTAZIONE" replaces "VINCOLI" - capturing the friction analysis
        constraints = self._extract_list(clean_out, "VALUTAZIONE")
        if not constraints: # Fallback for backward compatibility or hallucination
             constraints = self._extract_list(clean_out, "VINCOLI")
        missing_info = self._extract_list(clean_out, "MANCANZE")
        strategy = self._extract_field(clean_out, "STRATEGIA")
        
        needs_clarification = len(missing_info) > 0 and "nessuna" not in missing_info[0].lower()
        
        return ThoughtTrace(
            timestamp=datetime.now(),
            intent=intent or "Rispondere all'utente",
            constraints=constraints,
            missing_info=missing_info,
            strategy=strategy or "Risposta diretta",
            confidence=0.9, # Placeholder
            raw_thought=clean_out,
            needs_clarification=needs_clarification
        )

    def _extract_field(self, text: str, field_name: str) -> str:
        match = re.search(f"{field_name}:\\s*(.+?)(?:\\n\\d\\.|-|$)", text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _extract_list(self, text: str, field_name: str) -> List[str]:
        field = self._extract_field(text, field_name)
        if not field: return []
        return [x.strip() for x in field.split(',') if x.strip()]

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
