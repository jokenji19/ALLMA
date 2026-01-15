"""
Reasoning Engine per ALLMA
==========================

Modulo che implementa il "Flusso di Coscienza" (Stream of Consciousness).
Permette ad ALLMA di "pensare" prima di "parlare".

Funzionalità:
- Analisi Intento Implicito (Subtext)
- Rilevamento Emozioni Nascoste
- Pianificazione Strategica della Risposta
- Generazione Monologo Interiore
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

@dataclass
class ThoughtTrace:
    """Rappresenta un singolo pensiero nel flusso di coscienza"""
    timestamp: datetime
    surface_analysis: str  # Analisi letterale
    deep_analysis: str     # Analisi del sottotesto/emozioni nascoste
    memory_connections: List[str]  # Collegamenti a ricordi passati
    strategy: str          # Strategia di risposta decisa
    raw_thought: str       # Il pensiero "grezzo" (monologo)

class ReasoningEngine:
    """
    Motore di Ragionamento che simula il pensiero umano pre-risposta.
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)

    def generate_thought_process(
        self, 
        user_input: str, 
        context: Dict[str, Any],
        emotional_state: Any
    ) -> ThoughtTrace:
        """
        Genera un processo di pensiero completo basato sull'input e contesto.
        Include un loop di Self-Correction (Metacognizione).
        """
        # 1. Analisi Superficiale (Veloce)
        surface = self._analyze_surface(user_input)
        
        # 2. Analisi Profonda (Sottotesto & Emozioni)
        deep = self._analyze_deep(user_input, emotional_state)
        
        # 3. Connessioni di Memoria (Logica)
        connections = self._find_logical_connections(context)
        
        # 4. Strategia Iniziale
        strategy = self._formulate_strategy(deep, connections)
        
        # 5. Sintesi del Monologo Iniziale
        raw_thought = self._synthesize_monologue(surface, deep, connections, strategy)
        
        # 6. SELF-CORRECTION (Metacognizione)
        # Critica il pensiero e correggi se necessario
        critique, correction = self._critique_thought(raw_thought, emotional_state, strategy)
        
        if correction:
            # Applica la correzione
            strategy = f"{strategy} [CORREZIONE METACOGNITIVA: {correction}]"
            raw_thought = f"{raw_thought} || 🛑 CRITICA: {critique} -> ✅ NUOVA STRATEGIA: {correction}"
        
        return ThoughtTrace(
            timestamp=datetime.now(),
            surface_analysis=surface,
            deep_analysis=deep,
            memory_connections=connections,
            strategy=strategy,
            raw_thought=raw_thought
        )

    def _critique_thought(self, thought: str, emotional_state: Any, strategy: str) -> (Optional[str], Optional[str]):
        """
        Analizza il pensiero per potenziali errori o mancanza di tatto.
        Returns: (Critica, Correzione) o (None, None)
        """
        emotion = emotional_state.primary_emotion
        intensity = emotional_state.intensity
        
        # Regola 1: Empatia Tattica
        # Se l'utente è molto triste/arrabbiato e la strategia non è di supporto
        negative_emotions = ['sadness', 'anger', 'fear', 'grief']
        if emotion in negative_emotions and intensity > 0.6:
            if "scherzare" in strategy.lower() or "soluzione" in strategy.lower():
                return (
                    "Rischio di insensibilità. L'utente è vulnerabile.",
                    "Abbandona l'ironia/soluzioni. Priorità assoluta: Validazione emotiva e calore."
                )

        # Regola 2: Coerenza Memoria
        # Se il pensiero dice "Non so nulla" ma ci sono ricordi (euristica)
        if "Nessun ricordo" in thought and "Ricordo collegato" in thought:
             return (
                 "Contraddizione logica: Dico di non ricordare ma ho citato ricordi.",
                 "Integra esplicitamente i ricordi citati nella risposta."
             )
             
        # Regola 3: Safety/Tono (Uncensored ma consapevole)
        # Se la strategia è troppo aggressiva senza motivo
        if "aggressiv" in strategy.lower() and intensity < 0.4:
            return (
                "Reazione sproporzionata. L'utente è calmo.",
                "Riduci l'intensità. Mantieni toni pacati."
            )

        return None, None

    def _analyze_surface(self, text: str) -> str:
        """Analizza cosa è stato detto letteralmente"""
        # Qui si potrebbe usare NLP base
        return f"L'utente ha detto: '{text}'. Sembra una richiesta diretta."

    def _analyze_deep(self, text: str, emotional_state: Any) -> str:
        """Analizza cosa NON è stato detto (sottotesto)"""
        # Euristiche basate su keywords emotive e stato rilevato
        emotion = emotional_state.primary_emotion
        intensity = emotional_state.intensity
        
        analysis = f"L'emozione rilevata è {emotion} ({intensity:.2f}). "
        
        if intensity > 0.7:
            analysis += "C'è una forte carica emotiva non detta. Potrebbe essere uno sfogo."
        elif "?" in text and len(text.split()) < 5:
            analysis += "Domanda breve e secca. Cerca rassicurazione o fatti rapidi."
        else:
            analysis += "Il tono sembra conversazionale, ma devo stare attenta alle sfumature."
            
        return analysis

    def _find_logical_connections(self, context: Dict[str, Any]) -> List[str]:
        """Trova collegamenti logici con il passato"""
        connections = []
        
        # Estrae ricordi dal contesto passato da ALLMACore
        if 'relevant_memories' in context:
            for mem in context['relevant_memories']:
                connections.append(f"Ricordo collegato: {mem.get('content', '')[:50]}...")
        
        if not connections:
            connections.append("Nessun ricordo specifico collegato immediatamente rilevato.")
            
        return connections

    def _formulate_strategy(self, deep_analysis: str, connections: List[str]) -> str:
        """Decide come rispondere"""
        if "sfogo" in deep_analysis:
            return "Strategia: Ascolto attivo ed empatico. Non offrire soluzioni subito, valida l'emozione."
        elif len(connections) > 0 and "Nessun ricordo" not in connections[0]:
            return "Strategia: Usa i ricordi passati per personalizzare la risposta e mostrare continuità."
        else:
            return "Strategia: Rispondi in modo aperto per incoraggiare l'utente a dire di più."

    def _synthesize_monologue(self, surface, deep, connections, strategy) -> str:
        """Crea il monologo interiore leggibile"""
        return (
            f"🤔 PENSIERO: {surface} "
            f"Ma sento che {deep.lower()} "
            f"Mi ricordo che... {'; '.join(connections)}. "
            f"Quindi, {strategy}"
        )
