"""
PersonalityAdapterLite - Communication style adaptation

PHASE 24: Tier 2 Module Integration
Lightweight version that cooperates with CoalescenceProcessor.
Focuses ONLY on communication style (formality, verbosity, humor).
Personality traits are handled by Coalescence.
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class CommunicationStyle:
    """Communication style parameters."""
    formality: float = 0.5  # 0=informal, 1=formal
    verbosity: float = 0.6  # 0=concise, 1=verbose  
    humor: float = 0.4      # 0=serious, 1=playful
    directness: float = 0.7 # 0=indirect, 1=direct


class PersonalityAdapterLite:
    """
    Lightweight communication style adapter.
    Does NOT manage personality traits (Coalescence handles that).
    
    Cost: ~30ms
    Priority: LOW (4/10) - Optional, disabled by default
    """
    
    def __init__(self, coalescence_processor=None):
        self.coalescence = coalescence_processor
        self.style = CommunicationStyle()
        
        # Track user preferences from interactions
        self.user_prefers_brief = False
        self.user_prefers_formal = False
        self.interaction_count = 0
    
    def process(self, user_input: str, context: Dict) -> Dict:
        """
        Main entry point for ModuleOrchestrator.
        
        Args:
            user_input: User's message
            context: Conversation context (with emotional_state)
            
        Returns:
            Dict with style adaptation suggestions
        """
        # Update style based on user input
        self._adapt_from_input(user_input)
        
        # Get emotional context if available
        emotional_state = context.get('emotional_state')
        if emotional_state:
            self._adapt_from_emotion(emotional_state)
        
        return {
            'tone_params': {
                'formality': self.style.formality,
                'verbosity': self.style.verbosity,
                'humor': self.style.humor,
                'directness': self.style.directness
            },
            'style_hint': self._generate_style_hint()
        }
    
    def _adapt_from_input(self, text: str):
        """Learns communication preferences from user's style."""
        self.interaction_count += 1
        
        # Detect brevity preference
        if len(text) < 20 and '?' in text:
            # Short questions suggest preference for concise answers
            self.style.verbosity = max(0.3, self.style.verbosity - 0.05)
            self.user_prefers_brief = True
        elif len(text) > 100:
            # Long messages suggest user OK with verbose
            self.style.verbosity = min(0.8, self.style.verbosity + 0.03)
        
        # Detect formality preference  
        formal_indicators = ['per favore', 'cortesemente', 'grazie', 'saluti']
        if any(ind in text.lower() for ind in formal_indicators):
            self.style.formality = min(0.8, self.style.formality + 0.05)
            self.user_prefers_formal = True
        
        informal_indicators = ['ciao', 'hey', 'ok', 'cool']
        if any(ind in text.lower() for ind in informal_indicators):
            self.style.formality = max(0.3, self.style.formality - 0.05)
        
        # Detect humor appreciation
        if any(emoji in text for emoji in ['😂', '😄', '🤣', '😊']):
            self.style.humor = min(0.7, self.style.humor + 0.05)
    
    def _adapt_from_emotion(self, emotional_state):
        """Adapts style based on user's emotional state."""
        
        # If emotion object has primary_emotion attribute
        if hasattr(emotional_state, 'primary_emotion'):
            primary = str(emotional_state.primary_emotion).lower()
        elif isinstance(emotional_state, dict):
            primary = emotional_state.get('primary_emotion', 'neutral').lower()
        else:
            primary = str(emotional_state).lower()
        
        # Adjust directness based on emotion
        if 'sadness' in primary or 'fear' in primary:
            self.style.directness = max(0.4, self.style.directness - 0.1)
            self.style.humor = max(0.2, self.style.humor - 0.1)
        elif 'anger' in primary:
            self.style.directness = min(0.5, self.style.directness - 0.1)
            self.style.formality = min(0.7, self.style.formality + 0.1)
        elif 'joy' in primary or 'excitement' in primary:
            self.style.humor = min(0.7, self.style.humor + 0.1)
    
    def _generate_style_hint(self) -> str:
        """Generates text hint for LLM about desired style."""
        hints = []
        
        if self.style.formality > 0.7:
            hints.append("Mantieni tono formale e professionale")
        elif self.style.formality < 0.4:
            hints.append("Usa tono informale e amichevole")
        
        if self.style.verbosity > 0.7:
            hints.append("Fornisci spiegazioni dettagliate")
        elif self.style.verbosity < 0.4:
            hints.append("Risposte concise e dirette")
        
        if self.style.humor > 0.6:
            hints.append("Touch di umorismo appropriato OK")
        
        if self.style.directness > 0.7:
            hints.append("Comunicazione diretta senza giri di parole")
        
        return "; ".join(hints) if hints else "Stile bilanciato"
    
    def get_current_style(self) -> CommunicationStyle:
        """Returns current communication style parameters."""
        return self.style
