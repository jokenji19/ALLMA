"""GemmaLanguageGenerator - usa Gemma 3n E2B int4 per generare risposte
   Richiede che Gemma sia stato scaricato (huggingface hub first run scarica automaticamente).
"""
from typing import Dict
from allma_model.llm.gemma_wrapper import GemmaGenerator

class GemmaLanguageGenerator:
    def __init__(self):
        self.model = GemmaGenerator()

    def generate(self, plan: Dict, personality: Dict) -> str:
        # Costruisci prompt da plan + personality
        style = personality.get('style', 'friendly')
        keywords = ', '.join(plan.get('keywords', [])) if plan.get('keywords') else ''
        intent = plan.get('intent', 'informazione')
        tone = plan.get('tone', 'neutrale')

        prompt = (
            "Sei ALLMA, un assistente AI in italiano. "
            f"Stile: {style}. "
            f"Intento: {intent}. "
            f"Tono emotivo: {tone}. "
        )
        if keywords:
            prompt += f"Parole chiave rilevanti: {keywords}. "
        prompt += "Rispondi brevemente e in modo naturale alla richiesta dell'utente: \n" + plan.get('user_text', '') + "\nRisposta:"

        response = self.model.generate(prompt, max_tokens=128)
        return response.strip()
