import logging
import time
from typing import Optional, Dict, Any
from .soul_types import SoulState, Volition
from .chaos_engine import ChaosEngine

class SoulCore:
    """
    Il Cuore Pulsante di ALLMA.
    Gestisce l'evoluzione dello stato interno (Anima) attraverso dinamiche caotiche.
    """
    def __init__(self):
        self.state = SoulState()
        self.chaos_engine = ChaosEngine()
        self.last_pulse = time.time()
        self.logger = logging.getLogger(__name__)
        self.logger.info("✨ Soul System Initialized (Deterministic Chaos Engine Online)")

    def pulse(self):
        """
        Fa "battere" l'anima. Aggiorna lo stato interno basandosi sul tempo trascorso.
        Da chiamare periodicamente o ad ogni interazione.
        """
        current_time = time.time()
        # Calcola quanto tempo è passato (simuliamo il metabolismo)
        elapsed = current_time - self.last_pulse
        self.last_pulse = current_time
        
        # Esegui step del motore caotico (più tempo passa, più step fa)
        # Limitiamo gli step per evitare divergenza se passa troppo tempo
        steps = min(int(elapsed * 10), 100) 
        if steps < 1: steps = 1
            
        for _ in range(steps):
            self.chaos_engine.step()
            
        # Mappa il chaos sullo stato dell'anima
        self._sync_state_with_chaos()

    def perceive(self, stimulus_valence: float, stimulus_arousal: float):
        """
        Perturba l'anima con uno stimolo esterno (es. messaggio utente).
        
        Args:
            stimulus_valence: -1.0 (Negativo) a 1.0 (Positivo)
            stimulus_arousal: 0.0 (Calmo) a 1.0 (Eccitante/Urgente)
        """
        # L'intensità della perturbazione dipende dall'openness attuale
        impact = stimulus_arousal * self.state.openness
        
        # Perturba il motore caotico
        self.chaos_engine.step(perturbation=stimulus_valence * impact)
        
        # Aggiorna lo stato immediatamente
        self._sync_state_with_chaos()
        
        self.logger.info(f"✨ Soul perturbed by stimulus. New State: Energy={self.state.energy:.2f}, Chaos={self.state.chaos:.2f}")

    def resonate(self, emotion_text: str, confidence: float = 1.0):
        """
        Fa "risuonare" l'anima con un ricordo evocato.
        Simula l'effetto emotivo del ricordare.
        
        Args:
            emotion_text: Descrizione dell'emozione (es. "joy", "fear")
            confidence: Confidenza del ricordo (0.0-1.0)
        """
        valence = 0.0
        # Mappatura statica semplice (potrebbe essere migliorata con un dizionario condiviso)
        emo = emotion_text.lower()
        if any(x in emo for x in ['joy', 'felicità', 'love', 'amore', 'success', 'determinazione']):
            valence = 0.6
        elif any(x in emo for x in ['sad', 'tristezza', 'fear', 'paura', 'anger', 'rabbia']):
            valence = -0.6
        elif any(x in emo for x in ['curiosity', 'curiosità', 'surprise', 'sorpresa']):
            valence = 0.3
            
        # L'eco della memoria è più lieve dell'percezione diretta (0.3 factor)
        echo_power = valence * confidence * 0.3
        
        # Perturba lievemente il sistema
        if echo_power != 0:
            self.chaos_engine.step(perturbation=echo_power)
            self._sync_state_with_chaos()
            self.logger.info(f"💭 Soul resonating with memory '{emotion_text}': Echo={echo_power:.3f}")

    def mirror(self, emotional_tone: str):
        """
        Sintonizza l'Anima sull'emozione dell'utente (Empathetic Mirroring).
        Chiama perceive() con parametri calibrati per il tono rilevato.
        
        Args:
            emotional_tone: Tono rilevato (es. 'joy', 'sadness', 'POSITIVE')
        """
        tone = emotional_tone.lower() # Normalize to lowercase
        valence = 0.0
        arousal = 0.0
        
        # Mappatura Emozioni Specifiche
        if any(x in tone for x in ['joy', 'felicità', 'surprise', 'sorpresa', 'determination', 'determinazione', 'positive']):
            # Gioia Condivisa: Alta valenza, alta attivazione
            valence = 0.8
            arousal = 0.8
        elif any(x in tone for x in ['anger', 'rabbia', 'fear', 'paura']):
            # Allerta Empatica: Valenza negativa, alta attivazione (urgenza)
            valence = -0.8
            arousal = 0.9
        elif any(x in tone for x in ['sadness', 'tristezza', 'concern', 'preoccupazione', 'negative']):
            # Conforto Calmo: Valenza negativa (risonanza), bassa attivazione (calma)
            valence = -0.6
            arousal = 0.3
        
        if valence != 0 or arousal != 0:
            self.logger.info(f"🪞 Mirroring user emotion '{tone}' -> Valence={valence}, Arousal={arousal}")
            self.perceive(valence, arousal)

    def get_volition(self) -> Volition:
        """
        Determina la "Volontà" attuale basata sullo stato interno.
        Questa volontà influenzerà COME ALLMA risponde.
        """
        # Mappatura dello stato su modificatori comportamentali
        
        # 1. Tono (basato su Energia e Stabilità)
        tone = "Neutral"
        if self.state.energy > 0.7:
            tone = "Energetic/Enthusiastic" if self.state.stability > 0.5 else "Manic/Unpredictable"
        elif self.state.energy < 0.3:
            tone = "Calm/Reflective" if self.state.stability > 0.5 else "Melancholic/Distant"
        else:
            tone = "Balanced" if self.state.stability > 0.5 else "Moody"

        # 2. Creativity Boost (basato sul Caos e Openness)
        # Più caos -> Più creatività (temperature boost)
        creativity = (self.state.chaos + self.state.openness) / 2.0
        
        # 3. Decision Bias
        bias = "Logical"
        if self.state.chaos > 0.7:
            bias = "Chaotic" # Favorisce associazioni libere
        elif self.state.energy > 0.6 and self.state.focus < 0.4:
            bias = "Emotional" # Impulsiva
            
        return Volition(
            tone_modifier=tone,
            creativity_boost=creativity,
            decision_bias=bias
        )

    def _sync_state_with_chaos(self):
        """Mappa le coordinate di Lorenz (x,y,z) sulle dimensioni dell'Anima"""
        cx, cy, cz = self.chaos_engine.get_normalized_state()
        
        # Mappatura semantica (Definita nel Piano)
        # x (Valence) -> Influenza l'umore/Stabilità
        # y (Arousal) -> Influenza l'Energia
        # z (Control) -> Influenza il Focus
        
        # Normalizziamo [-1, 1] a [0, 1] dove serve
        self.state.stability = (cx + 1.0) / 2.0 
        self.state.energy = (cy + 1.0) / 2.0
        self.state.focus = (cz + 1.0) / 2.0
        
        # Chaos e Openness evolvono più lentamente o derivano da combinazioni
        # Chaos attuale = quanto il sistema sta cambiando velocemente (approssimazione)
        self.state.chaos = abs(cx * cy) # Interazione tra valenza e arousal
        
        # Openness fluttua leggermente
        self.state.openness = 0.5 + (cx * 0.2)
        
        self.state.x, self.state.y, self.state.z = cx, cy, cz
        
        # Applicazione ciclo circadiano (Biological Clock)
        self._apply_circadian_rhythm()

    def _apply_circadian_rhythm(self):
        """
        Modula lo stato dell'Anima in base all'ora del giorno.
        Simula un ciclo biologico di energia e riflessione.
        """
        from datetime import datetime
        hour = datetime.now().hour
        
        # Curve energetiche semplificate
        energy_mod = 0.0
        stability_mod = 0.0
        
        if 23 <= hour or hour < 6:
            # Notte profonda: Bassa energia, Alta introspezione
            energy_mod = -0.3
            stability_mod = 0.2
        elif 6 <= hour < 11:
            # Mattina: Risveglio, Alta energia
            energy_mod = 0.3
            stability_mod = 0.1
        elif 14 <= hour < 16:
            # Pomeriggio (Siesta): Leggero calo
            energy_mod = -0.1
            stability_mod = 0.0
        elif 18 <= hour < 22:
            # Sera: Equilibrata
            energy_mod = 0.0
            stability_mod = 0.1
            
        # Applica modificatori con clamping [0, 1]
        self.state.energy = max(0.0, min(1.0, self.state.energy + energy_mod))
        self.state.stability = max(0.0, min(1.0, self.state.stability + stability_mod))
