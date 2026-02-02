"""
LanguageProcessorLite - Fast NLP without external libraries

PHASE 24: Tier 3 Module Integration
Lightweight intent/sentiment detection using keyword matching.
NO spacy, NO nltk, pure Python pattern matching.
"""

from typing import Dict, List, Set
from allma_model.core.module_state_manager import ModuleStateManager


class LanguageProcessorLite:
    """
    Fast language processing without NLP libraries.
    Provides intent detection, sentiment analysis, and entity hints.
    
    Cost: ~50ms
    Priority: MEDIUM (5/10)
    """
    
    def __init__(self):
        # Intent detection keywords
        self.intent_patterns = {
            'question': ['?', 'come', 'cosa', 'quando', 'dove', 'perché', 'chi', 'quale'],
            'affermazione': ['è', 'sono', 'credo', 'penso', 'mi sembra'],
            'negazione': ['no', 'non', 'mai', 'niente', 'nessuno'],
            'comando': ['fai', 'crea', 'genera', 'scrivi', 'mostra'],
            'gratitudine': ['grazie', 'thanks', 'thank you', 'ti ringrazio']
        }
        
        # Sentiment word lists (Italian)
        self.positive_words = {
            'felice', 'bene', 'ottimo', 'perfetto', 'fantastico',
            'meraviglioso', 'eccellente', 'buono', 'bella', 'bello',
            'gioioso', 'allegro', 'contento', 'soddisfatto', 'sereno'
        }
        
        self.negative_words = {
            'triste', 'male', 'pessimo', 'terribile', 'orribile',
            'brutto', 'cattivo', 'arrabbiato', 'frustrato', 'deluso',
            'depresso', 'infelice', 'negativo', 'difettoso', 'sbagliato'
        }
        
        # Common Italian stopwords (simplified)
        self.stopwords = {
            'il', 'la', 'un', 'una', 'di', 'da', 'in', 'a', 'per',
            'con', 'su', 'che', 'e', 'ma', 'o', 'se', 'del', 'al'
        }
        
        # Persistence
        self.state_manager = ModuleStateManager()
        self._load_state()

    def _load_state(self):
        """Restore state from DB."""
        state = self.state_manager.load_state('language_processor_lite')
        if state:
            saved_positive = state.get('positive_words', [])
            saved_negative = state.get('negative_words', [])
            self.positive_words.update(saved_positive)
            self.negative_words.update(saved_negative)

    def _save_state(self):
        """Save current state to DB."""
        state = {
            'positive_words': list(self.positive_words),
            'negative_words': list(self.negative_words)
        }
        self.state_manager.save_state('language_processor_lite', state)
    
    def process(self, user_input: str, context: Dict) -> Dict:
        """
        Main entry point for ModuleOrchestrator.
        
        Args:
            user_input: User's message
            context: Conversation context
            
        Returns:
            Dict with intent, sentiment, entities, keywords
        """
        # Detect intent
        intent = self._detect_intent(user_input)
        
        # Analyze sentiment
        sentiment = self._analyze_sentiment(user_input)
        
        # Extract entities (capitalized words)
        entities = self._extract_entities(user_input)
        
        # Extract keywords (non-stopwords)
        keywords = self._extract_keywords(user_input)
        
        return {
            'intent': intent,
            'sentiment': sentiment,
            'entities': entities,
            'keywords': keywords,
            'word_count': len(user_input.split())
        }
    
    def _detect_intent(self, text: str) -> str:
        """
        Keyword-based intent detection.
        
        Returns most likely intent category.
        """
        text_lower = text.lower()
        
        scores = {}
        for intent, patterns in self.intent_patterns.items():
            score = sum(1 for pattern in patterns if pattern in text_lower)
            if score > 0:
                scores[intent] = score
        
        if not scores:
            return 'affermazione'  # Default
        
        # Return intent with highest score
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def _analyze_sentiment(self, text: str) -> float:
        """
        Word-list based sentiment analysis.
        
        Returns:
            Float from -1.0 (negative) to 1.0 (positive)
        """
        words = set(text.lower().split())
        
        pos_count = len(words & self.positive_words)
        neg_count = len(words & self.negative_words)
        
        total = pos_count + neg_count
        if total == 0:
            return 0.0  # Neutral
        
        # Normalize to [-1, 1]
        sentiment = (pos_count - neg_count) / total
        return sentiment
    
    def _extract_entities(self, text: str) -> List[str]:
        """
        Simple entity extraction using capitalization.
        
        Returns:
            List of potential entities (capitalized words)
        """
        words = text.split()
        entities = []
        
        for word in words:
            # Remove punctuation
            clean_word = word.strip('.,!?;:')
            
            # Check if capitalized (and not first word)
            if clean_word and clean_word[0].isupper() and len(clean_word) > 1:
                entities.append(clean_word)
        
        # Remove duplicates, keep first 5
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity not in seen:
                seen.add(entity)
                unique_entities.append(entity)
                if len(unique_entities) >= 5:
                    break
        
        return unique_entities
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extracts keywords by removing stopwords.
        
        Returns:
            List of important words
        """
        words = text.lower().split()
        keywords = []
        
        for word in words:
            # Clean word
            clean_word = word.strip('.,!?;:')
            
            # Skip if stopword or too short
            if clean_word in self.stopwords or len(clean_word) < 3:
                continue
            
            keywords.append(clean_word)
        
        # Return unique keywords (max 10)
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
                if len(unique_keywords) >= 10:
                    break
        
        return unique_keywords
    
    def add_positive_word(self, word: str):
        """Adds a custom positive word to sentiment dictionary."""
        self.positive_words.add(word.lower())
        self._save_state()
    
    def add_negative_word(self, word: str):
        """Adds a custom negative word to sentiment dictionary."""
        self.negative_words.add(word.lower())
        self._save_state()
