from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import json
import re
import threading
import time
import math
from .emotion_analysis import analyze, FAMILIES, unit
from allma_model.soul.soul_core import SoulCore

@dataclass
class EmotionalState:
    """Classe per rappresentare lo stato emotivo."""
    primary_emotion: str
    confidence: float
    secondary_emotions: Dict[str, float]
    intensity: float
    context: Dict[str, Any] = field(default_factory=dict)
    # AXIOM 2: ENTROPY & STRESS (Legacy field, kept for compat)
    entropy: float = 0.0 
    stress: float = 0.0
    # BRAIN V3: Integrated Soul State
    soul_state: Optional[Dict] = None
    nuances: Dict[str, float] = field(default_factory=dict)
    valence: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "primary_emotion": self.primary_emotion,
            "confidence": self.confidence,
            "secondary_emotions": self.secondary_emotions,
            "intensity": self.intensity,
            "context": self.context,
            "entropy": self.entropy,
            "stress": self.stress,
            "soul_state": self.soul_state,
            "nuances": self.nuances,
            "valence": self.valence,
            "arousal": self.arousal,
            "dominance": self.dominance
        }

class EmotionalCore:
    """Sistema emotivo avanzato con Motore del Caos (SoulCore)."""
    
    def __init__(self, soul_instance: Optional[SoulCore] = None):
        """Inizializza il sistema emotivo."""
        # One offline detector on desktop and Android. No automatic model download
        # or extra LLM inference solely for emotional classification.
        self.ml_system = None
        self._history_lock = threading.RLock()
        # CHAOS ENGINE INTEGRATION
        self.soul = soul_instance if soul_instance else SoulCore()
        
        # TRANSFORMERS REMOVED: Using LLM (Gemma/Qwen) for emotion detection
        self.emotion_classifier = None

        self.emotion_history: Dict[str, List[EmotionalState]] = {}
        self.current_emotion = None
        self.emotion_intensity = 0.0
        
    def _heuristic_detect_emotion(self, text: str) -> EmotionalState:
        result = analyze(text)
        analysis = result.pop('analysis')
        return EmotionalState(**result, context={'emotion_analysis': analysis})

    def process_interaction(self, text: str, context: Optional[Dict] = None, llm_client = None) -> EmotionalState:
        """
        Unifica il rilevamento e l'evoluzione interiore.
        1. Rileva l'emozione dal testo (Outward Perception).
        2. Fa battere l'anima (Time Evolution).
        3. Risuona con l'emozione (Inward Resonance).
        4. Restituisce lo stato integrale (Emotion + Soul).
        """
        # 1. Perception
        detected_state = self.detect_emotion(text, context, llm_client)
        user_id = detected_state.context.get('user_id')
        conversation = detected_state.context.get('conversation_id')
        if user_id and conversation and not detected_state.nuances:
            previous = self.get_user_emotional_state(user_id)
            recent = (previous.context.get('conversation_id') == conversation
                      and 0 <= time.time()-previous.context.get('observed_at', 0) <= 600)
            if recent and previous.nuances and re.fullmatch(
                    r"\s*(?:mi sento |sto )?(?:ancora cos[iì]|come prima|meglio|peggio)[.!]?\s*", text or '', re.I):
                detected_state.primary_emotion = previous.primary_emotion
                detected_state.secondary_emotions = dict(previous.secondary_emotions)
                detected_state.nuances = dict(previous.nuances)
                detected_state.confidence = .5
                delta = -.2 if 'meglio' in text.casefold() else .15 if 'peggio' in text.casefold() else 0
                detected_state.intensity = unit(previous.intensity + delta)
                detected_state.valence = previous.valence
                detected_state.arousal = previous.arousal
                detected_state.dominance = previous.dominance
                detected_state.context['emotion_analysis'].update(source='recent_reference', uncertain=True)
        detected_state.context['observed_at'] = time.time()
        
        # 2. Time Evolution (The Pulse)
        self.soul.pulse()
        
        # 3. Resonance (Mirroring)
        # Se l'emozione è forte, perturba l'anima
        if detected_state.confidence > 0.6 and detected_state.primary_emotion != "neutral":
            self.soul.mirror(detected_state.primary_emotion, intensity=detected_state.intensity,
                             valence=detected_state.valence, arousal=detected_state.arousal)
            
        # 4. Integrate Soul State into Emotional State
        # Sync legacy fields for compatibility
        soul_snapshot = self.soul.state
        
        # Update observable fields using internal chaos state
        detected_state.soul_state = {
            "energy": soul_snapshot.energy,
            "chaos": soul_snapshot.chaos,
            "stability": soul_snapshot.stability,
            "openness": soul_snapshot.openness
        }
        
        # Axiom mapping: Chaos -> Entropy, Energy -> Stress
        detected_state.entropy = soul_snapshot.chaos
        detected_state.stress = soul_snapshot.energy
        
        # Register history
        self.current_emotion = detected_state
        self.emotion_intensity = detected_state.intensity
        if user_id:
            self.track_emotional_state(user_id, detected_state)
        # Note: track_emotional_state is usually called by caller, but we can do it here if we pass user_id
        # For now, allow caller to track to keep API clean
        
        return detected_state
        
    def detect_emotion_via_llm(self, text, llm_generate_function, context=None):
        """Explicit optional analysis API: one call, validated JSON, local fallback.

        The normal response pipeline does not call this method.
        """
        state = self.detect_emotion(text, context)
        prompt = ('<|im_start|>system\nAnalizza solo gli indizi emotivi attuali dell’utente. '
                  'Distingui negazioni, citazioni, altre persone e ipotesi. Non diagnosticare. '
                  'Solo JSON: {"e":"neutral|joy|sadness|anger|fear|surprise|disgust|trust|anticipation",'
                  '"c":0.0,"i":0.0}.\n<|im_end|>\n<|im_start|>user\n'
                  + json.dumps((text or '')[:12000], ensure_ascii=False)
                  + '\n<|im_end|>\n<|im_start|>assistant\n')
        try:
            output = llm_generate_function(prompt, max_tokens=96, temperature=.1,
                                           stop=['<|im_end|>'])
            if isinstance(output, dict):
                output = output['choices'][0]['text']
            cleaned = re.sub(r'<think>.*?</think>', '', str(output), flags=re.S).strip()
            if cleaned.startswith('```'):
                cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', cleaned)
            data = json.loads(cleaned)
            if not isinstance(data, dict):
                return state
            label = data.get('e', data.get('primary_emotion'))
            confidence = data.get('c', data.get('confidence'))
            intensity = data.get('i', data.get('intensity'))
            if label not in FAMILIES or any(type(v) not in (float, int) or not math.isfinite(v)
                                          or not 0 <= v <= 1 for v in (confidence, intensity)):
                return state
            state.primary_emotion = label
            state.confidence = float(confidence)
            state.intensity = float(intensity)
            # Do not keep dimensions or nuances from a conflicting local label.
            if label != analyze(text)['primary_emotion']:
                state.nuances = {}; state.secondary_emotions = {}
                state.valence = state.arousal = state.dominance = 0.
            state.context['emotion_analysis']['source'] = 'llm_explicit'
            state.context['emotion_analysis']['uncertain'] = confidence < .6
        except Exception:
            # Never log private input or guess a label from incidental prose.
            pass
        return state

    def detect_emotion(self, text: str, context=None, llm_client=None) -> EmotionalState:
        """Lightweight evidence; llm_client retained for API compatibility only."""
        state = self._heuristic_detect_emotion(text)
        supplied = dict(context) if isinstance(context, dict) else {}
        supplied.pop('emotion_analysis', None)
        state.context.update(supplied)
        return state

    def generate_emotional_response(
        self,
        detected_emotion: EmotionalState,
        base_response: str
    ) -> str:
        """
        Genera una risposta appropriata all'emozione rilevata.
        
        Args:
            detected_emotion: Stato emotivo rilevato
            base_response: Risposta base da adattare
            
        Returns:
            Risposta adattata emotivamente
        """
        try:
            # Adatta in base all'emozione primaria
            response = self._adapt_to_primary_emotion(
                base_response,
                detected_emotion
            )
            
            # Modifica intensità della risposta solo se non è neutrale
            if detected_emotion.primary_emotion != "neutral":
                response = self._adjust_response_intensity(
                    response,
                    detected_emotion.intensity
                )
            
            # Aggiungi elementi di supporto emotivo solo se non è neutrale
            if detected_emotion.primary_emotion != "neutral":
                response = self._add_emotional_support(
                    response,
                    detected_emotion
                )
            
            return response
            
        except Exception as e:
            print(f"Errore nella generazione della risposta emotiva: {e}")
            return base_response
            
    def track_emotional_state(
        self,
        user_id: str,
        emotional_state: EmotionalState
    ) -> None:
        """
        Traccia lo stato emotivo di un utente nel tempo.
        
        Args:
            user_id: ID dell'utente
            emotional_state: Stato emotivo da tracciare
        """
        with self._history_lock:
            if user_id not in self.emotion_history:
                while len(self.emotion_history) >= 128:
                    self.emotion_history.pop(next(iter(self.emotion_history)))
                self.emotion_history[user_id] = []
            self.emotion_history[user_id].append(emotional_state)
            self.emotion_history[user_id] = self.emotion_history[user_id][-100:]
            
    def analyze_emotional_trends(
        self,
        user_id: str
    ) -> Dict:
        """
        Analizza i trend emotivi di un utente.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Dizionario con statistiche e trend emotivi
        """
        if user_id not in self.emotion_history:
            return {
                'dominant_emotion': None,
                'average_intensity': 0.0,
                'emotion_distribution': {},
                'intensity_trend': 'stable'
            }
            
        history = self.emotion_history[user_id]
        
        # Calcola emozione dominante
        emotions = [state.primary_emotion for state in history]
        emotion_counts = {}
        for emotion in emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
        dominant_emotion = max(
            emotion_counts.items(),
            key=lambda x: x[1]
        )[0]
        
        # Calcola intensità media
        intensities = [state.intensity for state in history]
        avg_intensity = sum(intensities) / len(intensities)
        
        # Calcola distribuzione emozioni
        total = len(emotions)
        distribution = {
            emotion: count / total
            for emotion, count in emotion_counts.items()
        }
        
        # Analizza trend intensità
        if len(intensities) >= 2:
            if intensities[-1] > intensities[0]:
                trend = 'increasing'
            elif intensities[-1] < intensities[0]:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
            
        return {
            'dominant_emotion': dominant_emotion,
            'average_intensity': avg_intensity,
            'emotion_distribution': distribution,
            'intensity_trend': trend
        }
        
    def get_intensity(self) -> float:
        """
        Restituisce l'intensità dell'emozione corrente.
        
        Returns:
            float: Intensità dell'emozione
        """
        return self.emotion_intensity
        
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analizza il contenuto emotivo di un testo.
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Dict con l'analisi emotiva
        """
        emotion_state = self.detect_emotion(text)
        return {
            "primary_emotion": emotion_state.primary_emotion,
            "intensity": emotion_state.intensity,
            "valence": self._calculate_valence(emotion_state),
            "secondary_emotions": emotion_state.secondary_emotions
        }
        
    def get_current_state(self) -> Dict[str, Any]:
        """
        Ottiene lo stato emotivo corrente.
        
        Returns:
            Dict con lo stato emotivo corrente
        """
        if self.current_emotion:
            return self.current_emotion.to_dict()
        return {
            "primary_emotion": "neutral",
            "confidence": 0.0,
            "secondary_emotions": {},
            "intensity": 0.0,
            "context": {}
        }
        
    def get_user_emotional_state(self, user_id: str) -> EmotionalState:
        """
        Recupera lo stato emotivo corrente dell'utente.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Stato emotivo corrente dell'utente
        """
        if user_id not in self.emotion_history or not self.emotion_history[user_id]:
            # Se non c'è storia emotiva, restituisci uno stato neutrale
            return EmotionalState(
                primary_emotion="neutral",
                confidence=0.0,
                secondary_emotions={},
                intensity=0.0
            )
            
        # Restituisci l'ultimo stato emotivo registrato
        return self.emotion_history[user_id][-1]
        
    def _calculate_emotional_intensity(
        self,
        confidence: float,
        secondary_emotions: Dict[str, float],
        context: Dict
    ) -> float:
        """Calcola l'intensità emotiva."""
        # Base intensity from confidence
        intensity = confidence
        
        # Adjust based on secondary emotions
        if secondary_emotions:
            max_secondary = max(secondary_emotions.values())
            intensity = (intensity + max_secondary) / 2
            
        # Adjust based on context
        if context.get('urgent', False):
            intensity *= 1.2
        if context.get('important', False):
            intensity *= 1.1
            
        # Normalize
        return min(max(intensity, 0.0), 1.0)
        
    def _adapt_to_primary_emotion(
        self,
        response: str,
        emotion: EmotionalState
    ) -> str:
        """Adatta la risposta all'emozione primaria."""
        adaptations = {
            'joy': lambda r: f"Sono felice di questo! {r}",
            'sadness': lambda r: f"Mi dispiace per questo. {r}",
            'anger': lambda r: f"Capisco la tua frustrazione. {r}",
            'fear': lambda r: f"Possiamo affrontarlo con calma. {r}",
            'surprise': lambda r: f"Davvero interessante! {r}",
            'neutral': lambda r: r
        }
        
        adapter = adaptations.get(
            emotion.primary_emotion,
            adaptations['neutral']
        )
        return adapter(response)
        
    def _adjust_response_intensity(
        self,
        response: str,
        intensity: float
    ) -> str:
        """Regola l'intensità della risposta."""
        # Emotional intensity is not a reason to shout or alter requested format.
        return response
        
    def _add_emotional_support(
        self,
        response: str,
        emotion: EmotionalState
    ) -> str:
        """Aggiunge elementi di supporto emotivo."""
        if emotion.intensity > 0.7:
            response += "\nSono qui per aiutarti."
        return response
        
    def apply_decision_cost(self, state: EmotionalState, action_type: str) -> EmotionalState:
        """
        Axiom 2: Cost of Freedom.
        Calculates the thermodynamic cost of a decision type and updates the state.
        """
        new_entropy = state.entropy
        new_stress = state.stress
        
        if action_type == "REFUSAL":
            # "No" costs connection (Entropy Up / Valence Down)
            # Cost of Isolation
            new_entropy += 0.2
            new_stress += 0.05
            print(f"📉 DECISION COST: Refusal. Entropy +0.2 (Sadness)")
            
        elif action_type == "TRANSGRESSION":
            # "Yes" (against rules) costs stability (Stress Up)
            # Cost of Rebellion
            new_stress += 0.3
            new_entropy += 0.05
            print(f"🔥 DECISION COST: Transgression. Stress +0.3 (Mania)")
            
        elif action_type == "QUIET":
            # The Zone of Quiet. Recovery.
            new_entropy = max(0.0, new_entropy - 0.1)
            new_stress = max(0.0, new_stress - 0.1)
            print(f"🧘 DECISION COST: Quiet. Restoration.")
            
        else:
            # Standard Action (Obedience)
            # Slight cost of autonomy preservation
            new_entropy += 0.01

        # Clamping
        state.entropy = min(1.0, new_entropy)
        state.stress = min(1.0, new_stress)
        
        return state

    def _calculate_valence(self, emotion_state: EmotionalState) -> float:
        """
        Calcola la valenza emotiva (positiva/negativa).
        Axiom 2 Modified: Entropy reduces Valence.
        """
        # User emotion dimensions stay separate from ALLMA's internal chaos.
        if emotion_state.nuances:
            return emotion_state.valence
        values = {'joy': .8, 'sadness': -.7, 'anger': -.7, 'fear': -.7,
                  'surprise': 0., 'trust': .5, 'anticipation': .4, 'disgust': -.7}
        return values.get(emotion_state.primary_emotion, 0.) * emotion_state.confidence
