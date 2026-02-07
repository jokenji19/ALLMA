from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import json
from allma_model.soul.soul_core import SoulCore
from allma_model.soul.soul_types import SoulState as InternalSoulState

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
    
    def to_dict(self) -> Dict:
        return {
            "primary_emotion": self.primary_emotion,
            "confidence": self.confidence,
            "secondary_emotions": self.secondary_emotions,
            "intensity": self.intensity,
            "context": self.context,
            "entropy": self.entropy,
            "stress": self.stress,
            "soul_state": self.soul_state
        }

class EmotionalCore:
    """Sistema emotivo avanzato con Motore del Caos (SoulCore)."""
    
    def __init__(self, soul_instance: Optional[SoulCore] = None):
        """Inizializza il sistema emotivo."""
        # Phase 17: TinyBERT Integration
        try:
            from allma_model.agency_system.ml_emotional_system import MLEmotionalSystem
            self.ml_system = MLEmotionalSystem()
        except ImportError:
            print("Warning: MLEmotionalSystem not found.")
            self.ml_system = None

        # CHAOS ENGINE INTEGRATION
        self.soul = soul_instance if soul_instance else SoulCore()
        
        # TRANSFORMERS REMOVED: Using LLM (Gemma/Qwen) for emotion detection
        self.emotion_classifier = None

        self.emotion_history: Dict[str, List[EmotionalState]] = {}
        self.current_emotion = None
        self.emotion_intensity = 0.0
        
        # Dizionario di traduzione semplice italiano-inglese per parole emotive comuni
        self.translation_dict = {
            'felice': 'happy',
            'triste': 'sad',
            'arrabbiato': 'angry',
            'contento': 'happy',
            'gioioso': 'joyful',
            'preoccupato': 'worried',
            'spaventato': 'scared',
            'sorpreso': 'surprised',
            'annoiato': 'bored',
            'entusiasta': 'excited',
            'soddisfatto': 'satisfied',
            'deluso': 'disappointed',
            'frustrato': 'frustrated',
            'nervoso': 'nervous',
            'calmo': 'calm',
            'rilassato': 'relaxed',
            'ansioso': 'anxious',
            'stanco': 'tired',
            'energico': 'energetic',
            'molto': 'very',
            'poco': 'little',
            'non': 'not',
            'sono': 'am',
            'mi sento': 'i feel',
            'mi': 'me',
            'sento': 'feel',
            'che': 'that',
            'quando': 'when',
            'perché': 'because',
            'e': 'and',
            'o': 'or',
            'ma': 'but',
            'se': 'if',
            'imparare': 'learning',
            'studiare': 'studying',
            'lavorare': 'working',
            'giocare': 'playing',
            'dormire': 'sleeping',
            'mangiare': 'eating',
            'bere': 'drinking',
            'parlare': 'talking',
            'scrivere': 'writing',
            'leggere': 'reading',
            'guardare': 'watching',
            'ascoltare': 'listening',
            'pensare': 'thinking',
            'credere': 'believing',
            'sapere': 'knowing',
            'capire': 'understanding',
            'volere': 'wanting',
            'potere': 'can',
            'dovere': 'must',
            'python': 'python'
        }
        
    def _translate_to_english(self, text: str) -> str:
        """
        Traduce il testo dall'italiano all'inglese usando un dizionario semplice.
        
        Args:
            text: Testo da tradurre
            
        Returns:
            Testo tradotto
        """
        # Converte il testo in minuscolo
        text = text.lower()
        
        # Divide il testo in parole
        words = text.split()
        
        # Traduce ogni parola se presente nel dizionario
        translated_words = [self.translation_dict.get(word, word) for word in words]
        
        # Unisce le parole tradotte
        return ' '.join(translated_words)

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
        
        # 2. Time Evolution (The Pulse)
        self.soul.pulse()
        
        # 3. Resonance (Mirroring)
        # Se l'emozione è forte, perturba l'anima
        if detected_state.confidence > 0.6 and detected_state.primary_emotion != "neutral":
            self.soul.mirror(detected_state.primary_emotion)
            
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
        # Note: track_emotional_state is usually called by caller, but we can do it here if we pass user_id
        # For now, allow caller to track to keep API clean
        
        return detected_state
        
    def detect_emotion_via_llm(self, text: str, llm_generate_function, context: Optional[Dict] = None) -> EmotionalState:
        """
        Rileva le emozioni usando il modello LLM principale (Gemma/Qwen).
        
        Args:
            text: Testo da analizzare
            llm_generate_function: Funzione .generate() o simile del LLM
            context: Contesto opzionale
        """
        if context is None: context = {}
        
        try:
            # PROMPT ENGINEERING PER ANALISI EMOTIVA (JSON OUTPUT) - Qwen 2.5 ChatML
            prompt = f"""<|im_start|>system
Sei un analista emotivo esperto. Il tuo compito è analizzare il testo dell'utente e identificare lo stato emotivo.
Devi rispondere ESCLUSIVAMENTE con un oggetto JSON valido. Niente altro testo.

Schema JSON richiesto:
{{
    "primary_emotion": "uno tra [joy, sadness, anger, fear, surprise, neutral]",
    "confidence": 0.0-1.0,
    "intensity": 0.0-1.0,
    "secondary_emotions": {{ "emozione": valore }}
}}
<|im_end|>
<|im_start|>user
Analizza il seguente testo: "{text}"<|im_end|>
<|im_start|>assistant
"""
            # Chiamata all'LLM (output breve, max 100 token)
            # Nota: flessibile sull'interfaccia della funzione
            try:
                # Se è un oggetto Llama di llama-cpp
                output = llm_generate_function(
                    prompt,
                    max_tokens=128,
                    stop=["<|im_end|>"],
                    temperature=0.1, # Temperatura bassa per determinismo JSON
                    echo=False
                )
                if isinstance(output, dict) and 'choices' in output:
                    json_str = output['choices'][0]['text'].strip()
                else:
                    json_str = str(output).strip()
            except Exception as e:
                print(f"Errore chiamata LLM diretta: {e}")
                raise e

            # Parsing JSON (gestione errori e pulizia markdown)
            import json
            import re
            
            # Pulisci eventuali ```json ... ```
            clean_json = re.sub(r'```json\s*', '', json_str)
            clean_json = re.sub(r'```', '', clean_json).strip()
            
            data = json.loads(clean_json)
            
            return EmotionalState(
                primary_emotion=data.get("primary_emotion", "neutral").lower(),
                confidence=float(data.get("confidence", 0.5)),
                secondary_emotions=data.get("secondary_emotions", {}),
                intensity=float(data.get("intensity", 0.1)),
                context=context
            )

        except Exception as e:
            print(f"Errore detect_emotion_via_llm: {e} - Input era: {text}")
            # Fallback sicuro
            return EmotionalState(
                primary_emotion="neutral",
                confidence=0.5,
                secondary_emotions={},
                intensity=0.1,
                context=context
            )

    def detect_emotion(
        self,
        text: str,
        context: Optional[Dict] = None,
        llm_client = None # New optional Argument
    ) -> EmotionalState:
        """
        Rileva le emozioni dal testo. Uses TinyBERT (Fast) -> LLM (Deep) -> Fallback.
        """
        if context is None:
            context = {}
            
        # 1. TENTATIVO CON TINYBERT (FAST & SPECIALIZED)
        # Phase 17 Upgrade
        if self.ml_system:
            try:
                # Use synchronous analyze for blocking detection
                emotion_label = self.ml_system.analyze(text)
                if emotion_label and emotion_label != "neutral":
                    return EmotionalState(
                        primary_emotion=emotion_label,
                        confidence=0.9, # High confidence in ML
                        secondary_emotions={},
                        intensity=0.7,
                        context=context
                    )
            except Exception as e:
                print(f"TinyBERT failed: {e}")

        # 2. TENTATIVO CON LLM (FALLBACK / DEEP)
        if llm_client:
            # Se llm_client è l'istanza Llama
            if hasattr(llm_client, '__call__'):
                return self.detect_emotion_via_llm(text, llm_client, context)
            elif hasattr(llm_client, 'create_completion'):
                return self.detect_emotion_via_llm(text, llm_client.create_completion, context)
                
        # 3. FALLBACK FINALE
        print("DEBUG - No Emotion System available, using fallback.")
        return EmotionalState(
            primary_emotion="neutral",
            confidence=0.5,
            secondary_emotions={},
            intensity=0.1,
            context=context
        )
            
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
        if user_id not in self.emotion_history:
            self.emotion_history[user_id] = []
            
        self.emotion_history[user_id].append(emotional_state)
        
        # Mantieni solo gli ultimi 100 stati
        if len(self.emotion_history[user_id]) > 100:
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
            "confidence": 1.0,
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
                confidence=1.0,
                secondary_emotions={},
                intensity=0.5
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
            'fear': lambda r: f"Non preoccuparti. {r}",
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
        if intensity > 0.8:
            response = response.upper()
        elif intensity > 0.6:
            response += "!"
        return response
        
    def _add_emotional_support(
        self,
        response: str,
        emotion: EmotionalState
    ) -> str:
        """Aggiunge elementi di supporto emotivo."""
        if emotion.intensity > 0.7:
            response += "\nSono qui per aiutarti."
        if emotion.confidence > 0.8:
            response += f"\nPercepisco chiaramente il tuo stato d'animo {emotion.primary_emotion}."
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
        # Definisci la valenza per ogni emozione
        valence_map = {
            "joy": 1.0, "love": 0.8, "admiration": 0.6, "approval": 0.4,
            "caring": 0.3, "excitement": 0.5, "gratitude": 0.7, "pride": 0.6,
            "relief": 0.3, "neutral": 0.0,
            "confusion": -0.2, "disapproval": -0.4, "disappointment": -0.5,
            "anger": -0.8, "annoyance": -0.3, "disgust": -0.7,
            "embarrassment": -0.4, "fear": -0.6, "grief": -0.9,
            "nervousness": -0.3, "remorse": -0.5, "sadness": -0.7
        }
        
        # Calcola la valenza pesata
        valence = valence_map.get(emotion_state.primary_emotion, 0.0) * emotion_state.confidence
        
        # Considera anche le emozioni secondarie
        for emotion, score in emotion_state.secondary_emotions.items():
            valence += valence_map.get(emotion, 0.0) * score * 0.5  # Peso dimezzato
        
        # AXIOM 2: ENTROPY DRAG
        # High entropy pulls valence down (Depression/Numbness)
        entropy_drag = emotion_state.entropy * 0.5
        valence -= entropy_drag
        
        # Normalizza tra -1 e 1
        return max(min(valence, 1.0), -1.0)
