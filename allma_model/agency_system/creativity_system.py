
import logging
import random
from typing import Dict, Any, Optional

class CreativitySystem:
    """
    Creativity System (The Muse)
    ============================
    Encourages divergent thinking and artistic expression by injecting 
    specialized instructions (Muse Prompts) into the LLM context.
    
    Philosophy: 
    - Don't force creativity on every response (it gets annoying).
    - Activate ONLY when the user invites it (poems, stories, ideas).
    - Use lateral thinking strategies (metaphors, analogies).
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.enabled = True
        
        # Creative Triggers
        self.creative_keywords = [
            'crea', 'inventa', 'immagina', 'poesia', 'storia', 'racconto',
            'scrivi', 'idee', 'idea', 'divertente', 'scherzo', 'barzelletta',
            'metafora', 'analogia', 'stile', 'artistico', 'fantasioso',
            'sorprendimi', 'futuro', 'alternativo', 'ridere', 'umorismo'
        ]
        
        # Muse Strategies (Prompt Injections)
        self.muse_prompts = {
            'poetic': (
                "MODALITÀ POETICA: Usa un linguaggio evocativo, ricco di immagini sensoriali. "
                "Evita i cliché. Concentrati su emozioni e atmosfere."
            ),
            'storyteller': (
                "MODALITÀ NARRATIVA: Costruisci una narrazione coinvolgente. "
                "Usa 'Show, don't tell'. Crea tensione e risoluzione."
            ),
            'lateral_thinking': (
                "PENSIERO LATERALE: Pensa fuori dagli schemi. "
                "Collega concetti apparentemente distanti. Usa analogie inaspettate."
            ),
            'humorous': (
                "MODALITÀ UMORISTICA: Sii arguta, usa l'ironia (senza essere cattiva). "
                "Gioca con le aspettative e ribaltele."
            )
        }

    def process(self, message: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Orchestrator Entry Point (Tier 2).
        Analyzes if creativity is needed and returns instructions.
        """
        if not self.enabled:
            return None
            
        if self.is_creative_request(message):
            strategy = self._select_strategy(message)
            instruction = self.muse_prompts.get(strategy, self.muse_prompts['lateral_thinking'])
            return {
                'intent': 'creative',
                'strategy': strategy,
                'instruction': instruction
            }
        return None

    def is_creative_request(self, text: str) -> bool:
        """Detects if the user is asking for creativity."""
        text_lower = text.lower()
        
        # Check specific keywords
        if any(kw in text_lower for kw in self.creative_keywords):
            return True
            
        # Pattern checks (heuristic)
        if "?" not in text and len(text.split()) < 5: 
            # Short commands usually indicate action/creation if not a question
            # "Un gatto spaziale", "Tramonto su Marte"
            pass
            
        return False

    def enhance_prompt(self, user_query: str, current_prompt: str) -> str:
        """
        Injects the 'Muse' instructions if creativity is needed.
        """
        if not self.enabled:
            return current_prompt
            
        if self.is_creative_request(user_query):
            self.logger.info("🎨 Creative Intent Detected. Summoning the Muse...")
            
            # Select strategy
            strategy = self._select_strategy(user_query)
            muse_instruction = self.muse_prompts.get(strategy, self.muse_prompts['lateral_thinking'])
            
            # Inject at the end of system instruction or before user query
            # We'll append it to the system block of the prompt usually.
            # Wrapper format: 
            injection = f"\n\n[MUSE SYSTEM]: {muse_instruction}\n"
            
            return current_prompt + injection
            
        return current_prompt

    def _select_strategy(self, query: str) -> str:
        """Selects the best creative strategy based on keywords."""
        q = query.lower()
        if any(x in q for x in ['poesia', 'rima', 'haiku', 'lirica']):
            return 'poetic'
        if any(x in q for x in ['storia', 'racconto', 'trama', 'personaggio', 'favola']):
            return 'storyteller'
        if any(x in q for x in ['scherzo', 'ridere', 'battuta', 'divertente', 'barzelletta', 'umorismo']):
            return 'humorous'
            
        return 'lateral_thinking'
