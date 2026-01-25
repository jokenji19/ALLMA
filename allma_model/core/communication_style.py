"""Stili di comunicazione supportati dal sistema"""

from allma_model.user_system.user_preferences import CommunicationStyle
from typing import Dict, Any, Optional

class CommunicationStyleAdapter:
    """
    Adatta lo stile di comunicazione in base alle preferenze
    e al contesto emotivo.
    """
    
    def __init__(self):
        self.current_style = CommunicationStyle.ADAPTIVE
        
    def adapt_prompt(self, base_prompt: str, user_style: Optional[CommunicationStyle] = None) -> str:
        """
        Modifica il prompt di sistema per riflettere lo stile desiderato.
        """
        style = user_style or self.current_style
        
        style_instruction = ""
        if style == CommunicationStyle.FORMAL:
            style_instruction = "Usa un linguaggio formale, preciso e professionale. Evita slang."
        elif style == CommunicationStyle.CASUAL:
            style_instruction = "Usa un linguaggio rilassato, amichevole e colloquiale. Sii calorosa."
        elif style == CommunicationStyle.DIRECT:
            style_instruction = "Sii estremamente concisa e diretta. Vai dritta al punto."
        elif style == CommunicationStyle.EXPLANATORY:
            style_instruction = "Sii didattica e dettagliata. Spiega i concetti come un'insegnante."
        elif style == CommunicationStyle.EMPATHETIC:
            style_instruction = "Focalizzati sulla validazione emotiva. Sii molto empatica e supportiva."
            
        if style_instruction:
            return f"{base_prompt}\nSTYLE INSTRUCTION: {style_instruction}"
        
        return base_prompt

# Re-export CommunicationStyle
__all__ = ['CommunicationStyle', 'CommunicationStyleAdapter']
