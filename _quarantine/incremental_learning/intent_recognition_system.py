"""
Sistema per il riconoscimento degli intenti dell'utente
"""
from typing import Dict, List, Optional, Tuple
import re

class IntentRecognitionSystem:
    def __init__(self):
        # Definizione dei pattern per il riconoscimento degli intenti
        self.intent_patterns = {
            "greeting": [
                r"\b(ciao|salve|buon(giorno|asera|anotte)|hey|hi)\b",
                r"\b(come va)\b"
            ],
            "how_are_you": [
                r"\b(come stai|come va|tutto bene|come procede)\b",
                r"\bstai\s+bene\b"
            ],
            "introduction": [
                r"\b(chi sei|presentati|raccontami di te)\b",
                r"\b(parlami di te)\b"
            ],
            "capabilities": [
                r"\b(cosa sai fare|quali sono le tue capacità|cosa puoi fare)\b",
                r"\b(come funzioni|come mi puoi aiutare)\b"
            ],
            "personal_questions": [
                r"\b(hai|provi|senti|pensi|credi)\b",
                r"\b(sei reale|sei umano|sei una persona|sei un bot|sei un programma)\b",
                r"\b(chi ti ha creato|chi ti ha fatto|chi ti ha programmato)\b"
            ],
            "language": [
                r"\b(parli inglese|do you speak|sprechen sie|habla|parlez-vous)\b",
                r"\b(in che lingua|quale lingua|che lingue)\b"
            ],
            "purpose": [
                r"\b(perché sei qui|qual è il tuo scopo|a cosa servi)\b",
                r"\b(in che senso|che significa)\b"
            ],
            "identity": [
                r"\b(come ti chiami|qual è il tuo nome|chi sei)\b",
                r"\b(sei ALLMA|sei un assistente)\b"
            ],
            "unknown": [
                r".*"  # Fallback per quando non viene riconosciuto nessun altro intent
            ]
        }
        
        # Compilazione delle espressioni regolari
        self.compiled_patterns = {
            category: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for category, patterns in self.intent_patterns.items()
        }
        
    def recognize_intent(self, text: str) -> Tuple[str, float, Optional[str]]:
        """
        Riconosce l'intento dell'utente dal testo
        Returns: (intent_category, confidence, subject)
        """
        best_match = ("unknown", 0.3, None)  # Default fallback
        
        # Controlla ogni categoria di intent
        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(text.lower())
                if match:
                    # Calcola un punteggio di confidenza basato sulla lunghezza del match
                    # e la sua posizione nel testo
                    match_length = len(match.group())
                    text_length = len(text)
                    position_score = 1 - (match.start() / text_length) if text_length > 0 else 0
                    confidence = min(0.9, (match_length / text_length + position_score) / 2)
                    
                    # Estrai il soggetto se presente
                    subject = self._extract_subject(text, match)
                    
                    # Aggiorna il best match se questo è migliore
                    if confidence > best_match[1]:
                        best_match = (category, confidence, subject)
                        
        return best_match
        
    def _extract_subject(self, text: str, match: re.Match) -> Optional[str]:
        """Estrae il soggetto della domanda se presente"""
        # Lista di pronomi interrogativi comuni
        question_words = ["chi", "cosa", "dove", "quando", "perché", "come"]
        
        # Cerca il pronome interrogativo più vicino al match
        text_before = text[:match.start()].lower()
        for word in question_words:
            if word in text_before:
                # Prendi il testo tra il pronome e il match come soggetto
                start = text_before.rfind(word) + len(word)
                end = match.start()
                subject = text[start:end].strip()
                if subject:
                    return subject
                    
        # Se non troviamo un pronome, prendiamo il resto della frase dopo il match
        text_after = text[match.end():].strip()
        if text_after:
            # Prendi solo la prima parte significativa
            words = text_after.split()
            if len(words) > 3:
                text_after = " ".join(words[:3])
            return text_after
            
        return None
