"""
CreativityEnhancer - Lightweight prompt enhancement for LLM creativity

PHASE 24: Tier 2 Module Integration
Refactored from full CreativitySystem to focus ONLY on prompt enhancement.
Does NOT generate content, only enriches prompts for better LLM output.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import re


@dataclass
class CreativeEnhancement:
    """Enhancement suggestions for creative prompts."""
    system_addition: str = ""
    tone: str = "neutral"
    examples_needed: bool = False
    use_analogies: bool = False
    encourage_unconventional: bool = False


class CreativityEnhancer:
    """
    Lightweight prompt enhancement system.
    Detects creative requests and suggests prompt modifications.
    
    Cost: ~20ms
    Priority: MEDIUM (6/10)
    """
    
    def __init__(self):
        # Keywords indicating creative intent
        self.creative_keywords = [
            'crea', 'inventa', 'immagina', 'idea', 'originale',
            'creativo', 'innovativo', 'unico', 'fantasioso',
            'storia', 'racconto', 'poesia', 'metafora'
        ]
        
        # Keywords for different creative modes
        self.storytelling_keywords = ['storia', 'racconto', 'narrativa', 'favola']
        self.brainstorming_keywords = ['idee', 'possibilità', 'alternative', 'soluzioni']
        self.artistic_keywords = ['artistico', 'poetico', 'metaforico', 'simbolico']
    
    def process(self, user_input: str, context: Dict) -> Dict:
        """
        Main entry point for ModuleOrchestrator.
        
        Args:
            user_input: User's message
            context: Conversation context
            
        Returns:
            Dict with enhancement suggestions or empty dict
        """
        creativity_level = self._detect_creative_request(user_input)
        
        if creativity_level == 0:
            return {}  # No creative enhancement needed
        
        enhancement = self._generate_enhancement(user_input, creativity_level)
        
        return {
            'enhancement': enhancement,
            'creativity_level': creativity_level,
            'mode': self._detect_creative_mode(user_input)
        }
    
    def _detect_creative_request(self, text: str) -> int:
        """
        Detects if user is requesting creative thinking.
        
        Returns:
            0 = no creativity needed
            1 = mild creativity
            2 = high creativity
        """
        text_lower = text.lower()
        
        # Count creative keyword matches
        matches = sum(1 for kw in self.creative_keywords if kw in text_lower)
        
        # High creativity signals
        if matches >= 2:
            return 2
        
        # Mild creativity signals
        if matches == 1:
            return 1
        
        # Check for implicit creative requests
        if '?' in text and any(word in text_lower for word in ['come', 'modo', 'possibile']):
            if len(text.split()) > 8:  # Complex question
                return 1
        
        return 0
    
    def _detect_creative_mode(self, text: str) -> str:
        """Identifies the type of creative request."""
        text_lower = text.lower()
        
        if any(kw in text_lower for kw in self.storytelling_keywords):
            return 'storytelling'
        elif any(kw in text_lower for kw in self.brainstorming_keywords):
            return 'brainstorming'
        elif any(kw in text_lower for kw in self.artistic_keywords):
            return 'artistic'
        else:
            return 'general_creative'
    
    def _generate_enhancement(self, text: str, level: int) -> CreativeEnhancement:
        """
        Generates enhancement suggestions based on creativity level.
        
        Args:
            text: User input
            level: Creativity level (1 or 2)
            
        Returns:
            CreativeEnhancement with suggested modifications
        """
        mode = self._detect_creative_mode(text)
        
        if level == 2:
            # High creativity mode
            return self._high_creativity_enhancement(mode)
        else:
            # Mild creativity mode
            return self._mild_creativity_enhancement(mode)
    
    def _high_creativity_enhancement(self, mode: str) -> CreativeEnhancement:
        """Full creative mode activation."""
        
        base_prompt = """
MODALITÀ CREATIVA MASSIMA ATTIVA:
- Pensa completamente fuori dagli schemi
- Usa analogie audaci e metafore inaspettate  
- Connessioni non convenzionali sono BENVENUTE
- Originalità prioritaria sulla convenzione
"""
        
        mode_specific = {
            'storytelling': "\n- Narrativa coinvolgente con elementi sorpresa\n- Personaggi vividi e memorabili",
            'brainstorming': "\n- Genera molte alternative diverse\n- Combina concetti apparentemente non correlati",
            'artistic': "\n- Linguaggio evocativo e simbolico\n- Immagini poetiche e suggestive"
        }
        
        system_addition = base_prompt + mode_specific.get(mode, "")
        
        return CreativeEnhancement(
            system_addition=system_addition,
            tone='imaginative',
            examples_needed=True,
            use_analogies=True,
            encourage_unconventional=True
        )
    
    def _mild_creativity_enhancement(self, mode: str) -> CreativeEnhancement:
        """Moderate creative mode."""
        
        system_addition = """
MODALITÀ CREATIVA ATTIVA:
- Pensa in modo flessibile
- Esplora opzioni diverse  
- Usa esempi concreti quando utile
"""
        
        return CreativeEnhancement(
            system_addition=system_addition,
            tone='flexible',
            examples_needed=True,
            use_analogies=False,
            encourage_unconventional=False
        )
    
    def get_prompt_modification(self, enhancement: CreativeEnhancement) -> str:
        """
        Converts enhancement to actual prompt text.
        
        Args:
            enhancement: CreativeEnhancement object
            
        Returns:
            Text to inject into system prompt
        """
        return enhancement.system_addition
