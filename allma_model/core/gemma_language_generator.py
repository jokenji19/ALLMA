"""GemmaLanguageGenerator - usa Gemma 3n E2B int4 per generare risposte
   Richiede che Gemma sia stato scaricato (huggingface hub first run scarica automaticamente).
"""
from typing import Dict
from allma_model.llm.gemma_wrapper import GemmaGenerator

class GemmaLanguageGenerator:
    def __init__(self):
        try:
            self.model = GemmaGenerator()
        except Exception:
            self.model = None

    def generate(self, plan: Dict, personality: Dict) -> str:
        style = personality.get('style', 'friendly')
        keywords = ', '.join(plan.get('keywords', [])) if plan.get('keywords') else ''
        intent = plan.get('intent', 'informazione')
        tone = plan.get('tone', 'neutrale')
        tone_value = tone.value if hasattr(tone, "value") else str(tone)
        user_text = plan.get('user_text', '')

        prompt = (
            "Sei ALLMA, un assistente AI in italiano. "
            f"Stile: {style}. "
            f"Intento: {intent}. "
            f"Tono emotivo: {tone}. "
        )
        if keywords:
            prompt += f"Parole chiave rilevanti: {keywords}. "
        prompt += "Rispondi brevemente e in modo naturale alla richiesta dell'utente: \n" + user_text + "\nRisposta:"

        if self.model:
            try:
                response = self.model.generate(prompt, max_tokens=128)
                return response.strip()
            except Exception:
                self.model = None

        return self._fallback_generate(user_text, intent, tone_value)

    def _fallback_generate(self, user_text: str, intent: str, tone: str) -> str:
        text = (user_text or "").lower()
        if "non ho capito" in text or "non capisco" in text or "spiegami" in text:
            return "Posso spiegare meglio questo concetto."
        if "grazie" in text or (intent == "ringraziamento") or ("capito" in text and "non ho capito" not in text):
            return "Prego, sono disponibile ad aiutarti."
        if "ciao" in text or "salve" in text or intent == "saluto":
            return "Ciao! Sono qui per aiutarti."
        if "chiami" in text or "nome" in text:
            return "Mi chiamo ALLMA."
        if tone in ["negativo", "negative", "negative_emotion"]:
            return "Capisco, posso aiutarti a risolvere."
        return "Capisco. Come posso aiutarti?"
