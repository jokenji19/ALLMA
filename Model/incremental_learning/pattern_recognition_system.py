"""
Sistema per il riconoscimento di pattern nel testo con apprendimento incrementale
"""
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from typing import List, Set, Dict, Any, Optional, Union
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer
from nltk.util import ngrams
import numpy as np
import logging
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity
import spacy
import re
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@dataclass
class PatternMatch:
    """Rappresenta un match di un pattern."""
    pattern: 'Pattern'
    confidence: float
    context: str

@dataclass
class Pattern:
    """Classe che rappresenta un pattern riconosciuto."""
    category: str
    confidence: float = 0.0
    keywords: Set[str] = field(default_factory=set)
    text: str = ""
    embedding: List[float] = field(default_factory=list)
    features: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))  # ID univoco per ogni pattern

    def __str__(self):
        return f"Pattern(category={self.category}, confidence={self.confidence:.2f}, keywords={self.keywords})"

@dataclass
class Subtopic:
    """Sottotema estratto da un pattern"""
    category: str
    confidence: float = 0.0
    keywords: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

class PatternRecognitionSystem:
    """Sistema di riconoscimento pattern basato su regole e apprendimento incrementale."""
    
    def __init__(self):
        """Inizializza il sistema di riconoscimento pattern."""
        # Inizializza lo stemmer italiano
        self.stemmer = SnowballStemmer('italian')
        
        # Inizializza le strutture dati
        self.observers = []
        self.known_patterns = {}
        self.pattern_categories = defaultdict(set)
        self.learned_keywords = defaultdict(set)
        self.keyword_counts = defaultdict(Counter)
        
        # Carica le stopwords italiane
        self.stop_words = set(stopwords.words('italian'))
        
        # Inizializza le categorie e le parole chiave
        self.categories = {
            'programming': 'programmazione',
            'learning': 'apprendimento',
            'positive_emotion': 'emozione_positiva',
            'negative_emotion': 'emozione_negativa',
            'problem': 'problema',
            'success': 'successo'
        }
        
        # Inizializza le parole chiave per ogni categoria
        self.keywords = {
            'programmazione': {'codice', 'java', 'coding', 'sviluppo', 'python', 'javascript', 'programmare', 'software'},
            'apprendimento': {'corso', 'conoscenza', 'imparare', 'concetto', 'apprendere', 'studiare', 'lezione', 'comprendere', 'capire'},
            'emozione_positiva': {'contento', 'felice', 'piace', 'soddisfatto', 'entusiasta', 'ottimo', 'eccellente', 'positivo', 'funziona', 'successo'},
            'emozione_negativa': {'arrabbiato', 'triste', 'deluso', 'frustrato', 'male', 'pessimo', 'terribile', 'negativo', 'errore', 'problema', 'difficile', 'sbagliato'},
            'problema': {'blocco', 'problema', 'bug', 'ostacolo', 'difficoltà', 'sfida', 'complicato', 'errore'},
            'successo': {'ottenuto', 'successo', 'raggiunto', 'vittoria', 'funziona', 'superato', 'completato', 'risolto'}
        }
        
        # Stemming delle parole chiave
        self.stemmed_keywords = {}
        for category, keywords in self.keywords.items():
            self.stemmed_keywords[category] = {self.stemmer.stem(word) for word in keywords}
            
        # Parole di negazione
        self.negation_words = {'non', 'nessun', 'niente', 'mai', 'nessuno'}
        self.stemmed_negations = {self.stemmer.stem(word) for word in self.negation_words}
        
        # Parole per sentiment analysis
        self.positive_keywords = {
            'ottimo', 'eccellente', 'successo', 'positivo', 'piace', 'funziona', 'contento', 'bene', 'felice',
            'soddisfatto', 'perfetto', 'fantastico', 'meraviglioso', 'bravo', 'efficace', 'efficiente',
            'utile', 'piacevole', 'brillante', 'superato', 'vittoria', 'risolto', 'raggiunto', 'completato',
            'entusiasta', 'contento', 'soddisfatto'
        }
        
        self.negative_keywords = {
            'errore', 'problema', 'brutto', 'terribile', 'difficile', 'pessimo', 'male', 'negativo', 'sbagliato',
            'frustrato', 'deluso', 'inutile', 'inefficace', 'inefficiente', 'complicato', 'confuso', 'blocco',
            'bug', 'fallito', 'impossibile', 'fastidioso', 'noioso', 'lento', 'arrabbiato', 'triste', 'odio',
            'detesto', 'insopportabile', 'irritante', 'spiacevole', 'deludente', 'insoddisfatto'
        }
        
        # Stemming delle parole per sentiment
        self.stemmed_positive = {self.stemmer.stem(word) for word in self.positive_keywords}
        self.stemmed_negative = {self.stemmer.stem(word) for word in self.negative_keywords}
        
        # Carica il modello spaCy per l'italiano
        try:
            self.nlp = spacy.load('it_core_news_sm')
        except OSError:
            # Se il modello non è installato, scaricalo
            import subprocess
            subprocess.run(['python', '-m', 'spacy', 'download', 'it_core_news_sm'])
            self.nlp = spacy.load('it_core_news_sm')
            
        # Tasso di apprendimento per l'aggiornamento dei pattern
        self.learning_rate = 0.1
        
        # Soglia minima di confidence per considerare un pattern valido
        self.confidence_threshold = 0.5
        
        # Inizializza gli osservatori
        self.observers = []
        self.pattern_history = []
        self.current_context = {}
        
        # Initialize important keywords
        self.important_keywords = {
            "programmazione": {"python", "java", "javascript", "coding"},
            "apprendimento": {"imparare", "studio", "corso"},
            "emozione_positiva": {"felice", "contento", "soddisfatto", "entusiasta"},
            "emozione_negativa": {"arrabbiato", "triste", "deluso", "frustrato"},
            "problema": {"bug", "errore", "blocco"},
            "successo": {"completato", "risolto", "funziona"}
        }
        
        # Alias per le categorie
        self.category_aliases = {
            'coding': 'programming',
            'development': 'programming',
            'happy': 'positive_emotion',
            'sad': 'negative_emotion'
        }
        
    def register_observer(self, observer):
        """Registra un nuovo osservatore"""
        if observer not in self.observers:
            self.observers.append(observer)
            
    def notify_observers(self, event_type: str, data: Dict[str, Any]):
        """Notifica gli osservatori"""
        for observer in self.observers:
            observer.update(event_type, data)
            
    def preprocess_text(self, text: Union[str, spacy.tokens.doc.Doc]) -> str:
        """
        Preprocessa il testo per l'analisi
        Args:
            text: Testo da preprocessare o documento spaCy
        Returns:
            str: Testo preprocessato
        """
        # Se l'input è un documento spaCy, estrai il testo
        if hasattr(text, 'text'):
            text = text.text
            
        # Converti in minuscolo
        text = text.lower()
        
        # Rimuovi caratteri speciali e numeri
        text = re.sub(r'[^a-zA-ZàèéìòùÀÈÉÌÒÙ\s]', ' ', text)
        
        # Rimuovi spazi multipli
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
        
    def analyze_pattern(self, text: str) -> Pattern:
        """
        Analizza il testo per trovare pattern comportamentali.
        Args:
            text: Testo da analizzare
        Returns:
            Pattern: Pattern comportamentale trovato
        """
        if text is None:
            raise ValueError("Il testo non può essere None")
            
        # Preprocessa il testo
        preprocessed = self.preprocess_text(text)
        tokens = word_tokenize(preprocessed)
        stemmed = [self.stemmer.stem(token) for token in tokens]
        
        # Cerca parole chiave per ogni categoria
        matches = defaultdict(set)
        for category, keywords in self.stemmed_keywords.items():
            for token, stem in zip(tokens, stemmed):
                if stem in keywords:
                    matches[category].add(token)
                    
        # Se troviamo parole emotive, analizziamo il sentiment
        if matches['emozione_negativa'] or matches['emozione_positiva']:
            sentiment = self.analyze_sentiment(text)
            if sentiment.category == "negative":
                return Pattern(
                    category="negative_emotion",
                    confidence=sentiment.confidence,
                    keywords=matches['emozione_negativa'],
                    text=text
                )
            elif sentiment.category == "positive":
                return Pattern(
                    category="positive_emotion",
                    confidence=sentiment.confidence,
                    keywords=matches['emozione_positiva'],
                    text=text
                )
                
        # Altrimenti, trova la categoria con più match
        best_category = "unknown"
        max_matches = 0
        for category, matched_words in matches.items():
            if len(matched_words) > max_matches:
                max_matches = len(matched_words)
                best_category = category
                
        # Converti la categoria interna in categoria esterna
        if best_category in self.categories.values():
            # Trova la chiave corrispondente al valore
            best_category = next(k for k, v in self.categories.items() if v == best_category)
                
        # Calcola la confidence
        if max_matches > 0:
            confidence = min(0.95, 0.5 + (max_matches / len(tokens)) * 0.5)
        else:
            confidence = 0.5
            
        # Crea il pattern
        pattern = Pattern(
            category=best_category,
            confidence=confidence,
            keywords=matches[best_category],
            text=text
        )
        
        return pattern

    def learn_pattern(self, text: Union[str, List[float], np.ndarray], category: Optional[str] = None) -> Pattern:
        """
        Analizza e apprende pattern dal testo o dal vettore di feature
        Args:
            text: Testo da analizzare o vettore di feature
            category: Categoria del pattern
        Returns:
            Pattern: Pattern appreso
        """
        # Se l'input è un vettore di feature, lo salviamo direttamente
        if isinstance(text, (list, np.ndarray)):
            features = list(text)  # Converti in lista per compatibilità
        else:
            features = []  # Per input testuali, features vuoto
            
        pattern = self.analyze_pattern(text)
        pattern.features = features  # Salva le feature nel pattern
        
        # Se viene fornita una categoria, aggiorna il pattern
        if category:
            pattern.category = category
            
            # Aumenta la confidence in base alle feature estratte
            features = self._extract_pattern_features(text)
            category_coverage = features.get(f'{category}_coverage', 0)
            sentiment_match = abs(0.5 - features['sentiment_score']) > 0.2
            
            # Calcola la confidence base
            base_confidence = 0.7  # Ridotto da 0.85
            
            # Calcola i boost
            coverage_boost = min(0.2, category_coverage * 0.4)
            sentiment_boost = 0.1 if sentiment_match else 0
            
            # Aggiungi un boost basato sul numero di pattern simili
            similar_patterns = self._find_similar_patterns(pattern)
            similarity_boost = min(0.2, len(similar_patterns) * 0.05)
            
            # Aggiungi un boost basato sull'apprendimento
            learning_boost = min(0.1, len(self.learned_keywords[category]) * 0.01)
            
            # Combina tutti i boost
            pattern.confidence = min(0.95, base_confidence + coverage_boost + sentiment_boost + similarity_boost + learning_boost)
            
            # Aggiorna le parole chiave apprese
            tokens = word_tokenize(self.preprocess_text(text))
            stemmed_tokens = [self.stemmer.stem(token) for token in tokens]
            
            if category not in self.learned_keywords:
                self.learned_keywords[category] = set()
            
            # Miglioriamo l'apprendimento delle parole chiave
            for token, stemmed in zip(tokens, stemmed_tokens):
                # Aggiungiamo solo se non è una stopword e ha lunghezza > 2
                if stemmed not in self.stop_words and len(stemmed) > 2:
                    if stemmed not in self.stemmed_keywords.get(category, set()):
                        self.learned_keywords[category].add(stemmed)
                        # Incrementiamo il contatore
                        self.keyword_counts[category][stemmed] += 1
            
            # Calcola embedding per il pattern
            pattern.embedding = self._calculate_embedding(text)
            
            # Aggiungi il pattern alla lista dei pattern conosciuti
            self.known_patterns[pattern.id] = pattern
            
            # Aggiorna il dizionario delle categorie
            if pattern.category:
                if pattern.category not in self.pattern_categories:
                    self.pattern_categories[pattern.category] = set()
                self.pattern_categories[pattern.category].add(pattern.id)
                
        return pattern

    def update_from_feedback(self, pattern: Pattern, feedback: float) -> None:
        """
        Aggiorna il sistema basandosi sul feedback ricevuto
        """
        if not pattern.category or feedback <= 0:
            return
            
        # Rafforza le associazioni positive
        for keyword in pattern.keywords:
            self.keyword_counts[pattern.category][keyword] += 1
            
            # Se la parola è molto usata in questa categoria, aggiungila alle parole chiave base
            if self.keyword_counts[pattern.category][keyword] > 5:
                self.keywords[pattern.category].add(keyword)

    def _find_similar_patterns(self, pattern: Union[Pattern, List[float]], features: Optional[Dict[str, float]] = None, threshold: float = 0.5) -> List[Pattern]:
        """
        Trova pattern simili basandosi sulle parole chiave, embedding e feature linguistiche
        Args:
            pattern: Pattern o embedding da confrontare
            features: Feature linguistiche opzionali
            threshold: Soglia minima di similarità
        Returns:
            List[Pattern]: Lista di pattern simili trovati
        """
        similar_patterns = []
        
        # Se l'input è un pattern, usa il suo embedding
        if isinstance(pattern, Pattern):
            embedding = pattern.embedding
            pattern_category = pattern.category
        else:
            embedding = pattern
            pattern_category = None
            
        # Confronta con i pattern conosciuti
        for known_pattern in self.known_patterns.values():
            similarity_score = 0.0
            
            # Calcola similarità basata su embedding
            if embedding and known_pattern.embedding:
                embedding_similarity = cosine_similarity(
                    np.array(embedding).reshape(1, -1),
                    np.array(known_pattern.embedding).reshape(1, -1)
                )[0][0]
                similarity_score += 0.6 * embedding_similarity  # Peso maggiore per embedding
                
            # Calcola similarità basata su feature linguistiche
            if features and hasattr(known_pattern, 'features'):
                feature_similarity = 0.0
                if isinstance(features, dict) and isinstance(known_pattern.features, dict):
                    common_features = set(features.keys()) & set(known_pattern.features.keys())
                    if common_features:
                        feature_diffs = [
                            abs(features[f] - known_pattern.features[f])
                            for f in common_features
                        ]
                        feature_similarity = 1 - (sum(feature_diffs) / len(feature_diffs))
                        similarity_score += 0.4 * feature_similarity  # Peso minore per feature
                
            # Se c'è una categoria, aumenta lo score per pattern della stessa categoria
            if pattern_category and pattern_category == known_pattern.category:
                similarity_score *= 1.2  # Boost del 20% per stessa categoria
                
            if similarity_score > threshold:
                similar_patterns.append(known_pattern)
                    
        return similar_patterns

    def update_from_feedback(self, pattern: Pattern, feedback: float) -> None:
        """
        Aggiorna il sistema basandosi sul feedback ricevuto
        """
        if not pattern.category or feedback <= 0:
            return
            
        # Rafforza le associazioni positive
        for keyword in pattern.keywords:
            self.keyword_counts[pattern.category][keyword] += 1
            
            # Se la parola è molto usata in questa categoria, aggiungila alle parole chiave base
            if self.keyword_counts[pattern.category][keyword] > 5:
                self.keywords[pattern.category].add(keyword)

    def analyze_sentiment(self, text: str) -> Pattern:
        """
        Analizza il sentiment del testo
        Args:
            text: Testo da analizzare
        Returns:
            Pattern: Pattern con categoria di sentiment e confidence
        """
        # Preprocessa il testo
        preprocessed = self.preprocess_text(text)
        tokens = word_tokenize(preprocessed)
        stemmed = [self.stemmer.stem(token) for token in tokens]
        
        # Inizializza contatori
        pos_count = 0
        neg_count = 0
        negation = False
        
        # Analizza ogni token
        for i, (token, stem) in enumerate(zip(tokens, stemmed)):
            # Controlla per negazioni
            if stem in self.stemmed_negations:
                negation = True
                continue
                
            # Controlla parole positive
            if stem in self.stemmed_positive:
                if negation:
                    neg_count += 1
                else:
                    pos_count += 1
                    
            # Controlla parole negative
            elif stem in self.stemmed_negative:
                if negation:
                    pos_count += 1
                else:
                    neg_count += 1
                    
            # Reset negazione dopo 3 token o alla fine della frase
            if negation and (i - tokens.index(token) >= 3 or token in {'.', '!', '?'}):
                negation = False
                
        # Determina la categoria
        if pos_count > neg_count:
            category = "positive"
            confidence = pos_count / (pos_count + neg_count)
        elif neg_count > pos_count:
            category = "negative"
            confidence = neg_count / (pos_count + neg_count)
        else:
            category = "neutral"
            confidence = 0.5
            
        # Raccogli le parole chiave trovate
        keywords = {token for token, stem in zip(tokens, stemmed)
                   if stem in self.stemmed_positive or stem in self.stemmed_negative}
        
        return Pattern(
            category=category,
            confidence=confidence,
            keywords=keywords,
            text=text
        )

    def _calculate_sentiment_score(self, tokens: List[str]) -> float:
        """
        Calcola uno score di sentiment basato sui token
        Returns: float tra 0 e 1 (0 = molto negativo, 1 = molto positivo)
        """
        pos_count = 0
        neg_count = 0
        negation = False
        
        for token in tokens:
            if token in self.stemmed_negations:
                negation = True
                continue
                
            if token in self.stemmed_positive:
                if negation:
                    neg_count += 1
                else:
                    pos_count += 1
            elif token in self.stemmed_negative:
                if negation:
                    pos_count += 1
                else:
                    neg_count += 1
                    
            negation = False
            
        total = pos_count + neg_count
        if total == 0:
            return 0.5
            
        return (pos_count / total) if total > 0 else 0.5

    def _find_similar_patterns(self, pattern: Union[Pattern, List[float]], features: Optional[Dict[str, float]] = None, threshold: float = 0.5) -> List[Pattern]:
        """
        Trova pattern simili basandosi sulle parole chiave, embedding e feature linguistiche
        Args:
            pattern: Pattern o embedding da confrontare
            features: Feature linguistiche opzionali
            threshold: Soglia minima di similarità
        Returns:
            List[Pattern]: Lista di pattern simili trovati
        """
        similar_patterns = []
        
        # Se l'input è un pattern, usa il suo embedding
        if isinstance(pattern, Pattern):
            embedding = pattern.embedding
            pattern_category = pattern.category
        else:
            embedding = pattern
            pattern_category = None
            
        # Confronta con i pattern conosciuti
        for known_pattern in self.known_patterns.values():
            similarity_score = 0.0
            
            # Calcola similarità basata su embedding
            if embedding and known_pattern.embedding:
                embedding_similarity = cosine_similarity(
                    np.array(embedding).reshape(1, -1),
                    np.array(known_pattern.embedding).reshape(1, -1)
                )[0][0]
                similarity_score += 0.6 * embedding_similarity  # Peso maggiore per embedding
                
            # Calcola similarità basata su feature linguistiche
            if features and hasattr(known_pattern, 'features'):
                feature_similarity = 0.0
                if isinstance(features, dict) and isinstance(known_pattern.features, dict):
                    common_features = set(features.keys()) & set(known_pattern.features.keys())
                    if common_features:
                        feature_diffs = [
                            abs(features[f] - known_pattern.features[f])
                            for f in common_features
                        ]
                        feature_similarity = 1 - (sum(feature_diffs) / len(feature_diffs))
                        similarity_score += 0.4 * feature_similarity  # Peso minore per feature
                
            # Se c'è una categoria, aumenta lo score per pattern della stessa categoria
            if pattern_category and pattern_category == known_pattern.category:
                similarity_score *= 1.2  # Boost del 20% per stessa categoria
                
            if similarity_score > threshold:
                similar_patterns.append(known_pattern)
                    
        return similar_patterns

    def analyze_themes(self, texts: List[str]) -> List[Pattern]:
        """
        Analizza i temi presenti in una lista di testi
        Args:
            texts: Lista di testi da analizzare
        Returns:
            List[Pattern]: Lista di pattern tematici trovati
        """
        # Inizializza contatori per parole chiave e categorie
        keyword_counts = defaultdict(Counter)
        category_counts = Counter()
        total_keywords = Counter()  # Contatore totale per tutte le parole chiave
        
        # Analizza ogni testo
        for text in texts:
            # Preprocessa il testo
            preprocessed = self.preprocess_text(text)
            tokens = word_tokenize(preprocessed)
            stemmed = [self.stemmer.stem(token) for token in tokens]
            
            # Cerca parole chiave per ogni categoria
            for category, keywords in self.stemmed_keywords.items():
                for token, stem in zip(tokens, stemmed):
                    if stem in keywords:
                        keyword_counts[category][token] += 1
                        category_counts[category] += 1
                        total_keywords[token] += 1
                        
            # Cerca anche nelle parole chiave apprese
            for category, keywords in self.learned_keywords.items():
                for token, stem in zip(tokens, stemmed):
                    if stem in keywords:
                        keyword_counts[category][token] += 1
                        category_counts[category] += 1
                        total_keywords[token] += 1
                        
        # Crea pattern per ogni tema trovato
        themes = []
        total_occurrences = sum(category_counts.values())
        
        for category, count in category_counts.most_common():
            if count > 0:
                # Calcola la confidence basata su diversi fattori
                
                # 1. Frequenza relativa della categoria
                frequency_score = count / total_occurrences if total_occurrences > 0 else 0
                
                # 2. Copertura nei testi
                texts_with_category = sum(1 for text in texts if any(
                    self.stemmer.stem(token) in self.stemmed_keywords.get(category, set()) 
                    for token in word_tokenize(self.preprocess_text(text))
                ))
                coverage_score = texts_with_category / len(texts)
                
                # 3. Diversità delle parole chiave
                unique_keywords = len(set(keyword_counts[category].keys()))
                diversity_score = min(1.0, unique_keywords / 5)  # Normalizza a 5 parole chiave uniche
                
                # Combina i punteggi con pesi
                confidence = min(0.95, (
                    0.4 * frequency_score +   # Peso maggiore per la frequenza
                    0.4 * coverage_score +    # Peso maggiore per la copertura
                    0.2 * diversity_score     # Peso minore per la diversità
                ))
                
                # Boost minimo per garantire una confidence di base
                confidence = max(0.5, confidence)
                
                # Crea il pattern tematico
                pattern = Pattern(
                    category=category,
                    confidence=confidence,
                    keywords=set(keyword_counts[category].keys()),
                    text=f"Theme: {category}"
                )
                themes.append(pattern)
                
                # Se questa categoria ha un alias, crea un pattern anche per l'alias
                if category in self.categories.values():
                    # Trova l'alias corrispondente
                    alias = next(k for k, v in self.categories.items() if v == category)
                    alias_pattern = Pattern(
                        category=alias,
                        confidence=confidence,
                        keywords=set(keyword_counts[category].keys()),
                        text=f"Theme: {alias}"
                    )
                    themes.append(alias_pattern)
                
        return themes

    def get_all_patterns(self) -> List[Pattern]:
        """Restituisce tutti i pattern riconosciuti finora.
        
        Returns:
            Lista di tutti i Pattern riconosciuti
        """
        all_patterns = []
        
        # Aggiungi i pattern dal dizionario dei pattern conosciuti
        for pattern in self.known_patterns.values():
            all_patterns.append(pattern)
            
        return all_patterns

    def learn_pattern(self, text: Union[str, List[float], np.ndarray], category: Optional[str] = None) -> Pattern:
        """
        Analizza e apprende pattern dal testo o dal vettore di feature
        Args:
            text: Testo da analizzare o vettore di feature
            category: Categoria del pattern
        Returns:
            Pattern: Pattern appreso
        """
        # Se l'input è un vettore di feature, lo salviamo direttamente
        if isinstance(text, (list, np.ndarray)):
            features = list(text)  # Converti in lista per compatibilità
        else:
            features = []  # Per input testuali, features vuoto
            
        pattern = self.analyze_pattern(text)
        pattern.features = features  # Salva le feature nel pattern
        
        # Se viene fornita una categoria, aggiorna il pattern
        if category:
            pattern.category = category
            
            # Aumenta la confidence in base alle feature estratte
            features = self._extract_pattern_features(text)
            category_coverage = features.get(f'{category}_coverage', 0)
            sentiment_match = abs(0.5 - features['sentiment_score']) > 0.2
            
            # Calcola la confidence base
            base_confidence = 0.7  # Ridotto da 0.85
            
            # Calcola i boost
            coverage_boost = min(0.2, category_coverage * 0.4)
            sentiment_boost = 0.1 if sentiment_match else 0
            
            # Aggiungi un boost basato sul numero di pattern simili
            similar_patterns = self._find_similar_patterns(pattern)
            similarity_boost = min(0.2, len(similar_patterns) * 0.05)
            
            # Aggiungi un boost basato sull'apprendimento
            learning_boost = min(0.1, len(self.learned_keywords[category]) * 0.01)
            
            # Combina tutti i boost
            pattern.confidence = min(0.95, base_confidence + coverage_boost + sentiment_boost + similarity_boost + learning_boost)
            
            # Aggiorna le parole chiave apprese
            tokens = word_tokenize(self.preprocess_text(text))
            stemmed_tokens = [self.stemmer.stem(token) for token in tokens]
            
            if category not in self.learned_keywords:
                self.learned_keywords[category] = set()
            
            # Miglioriamo l'apprendimento delle parole chiave
            for token, stemmed in zip(tokens, stemmed_tokens):
                # Aggiungiamo solo se non è una stopword e ha lunghezza > 2
                if stemmed not in self.stop_words and len(stemmed) > 2:
                    if stemmed not in self.stemmed_keywords.get(category, set()):
                        self.learned_keywords[category].add(stemmed)
                        # Incrementiamo il contatore
                        self.keyword_counts[category][stemmed] += 1
            
            # Calcola embedding per il pattern
            pattern.embedding = self._calculate_embedding(text)
            
            # Aggiungi il pattern alla lista dei pattern conosciuti
            self.known_patterns[pattern.id] = pattern
            
            # Aggiorna il dizionario delle categorie
            if pattern.category:
                if pattern.category not in self.pattern_categories:
                    self.pattern_categories[pattern.category] = set()
                self.pattern_categories[pattern.category].add(pattern.id)
                
        return pattern

    def _find_similar_patterns(self, pattern: Union[Pattern, List[float]], features: Optional[Dict[str, float]] = None, threshold: float = 0.5) -> List[Pattern]:
        """
        Trova pattern simili basandosi sulle parole chiave, embedding e feature linguistiche
        Args:
            pattern: Pattern o embedding da confrontare
            features: Feature linguistiche opzionali
            threshold: Soglia minima di similarità
        Returns:
            List[Pattern]: Lista di pattern simili trovati
        """
        similar_patterns = []
        
        # Se l'input è un pattern, usa il suo embedding
        if isinstance(pattern, Pattern):
            embedding = pattern.embedding
            pattern_category = pattern.category
        else:
            embedding = pattern
            pattern_category = None
            
        # Confronta con i pattern conosciuti
        for known_pattern in self.known_patterns.values():
            similarity_score = 0.0
            
            # Calcola similarità basata su embedding
            if embedding and known_pattern.embedding:
                embedding_similarity = cosine_similarity(
                    np.array(embedding).reshape(1, -1),
                    np.array(known_pattern.embedding).reshape(1, -1)
                )[0][0]
                similarity_score += 0.6 * embedding_similarity  # Peso maggiore per embedding
                
            # Calcola similarità basata su feature linguistiche
            if features and hasattr(known_pattern, 'features'):
                feature_similarity = 0.0
                if isinstance(features, dict) and isinstance(known_pattern.features, dict):
                    common_features = set(features.keys()) & set(known_pattern.features.keys())
                    if common_features:
                        feature_diffs = [
                            abs(features[f] - known_pattern.features[f])
                            for f in common_features
                        ]
                        feature_similarity = 1 - (sum(feature_diffs) / len(feature_diffs))
                        similarity_score += 0.4 * feature_similarity  # Peso minore per feature
                
            # Se c'è una categoria, aumenta lo score per pattern della stessa categoria
            if pattern_category and pattern_category == known_pattern.category:
                similarity_score *= 1.2  # Boost del 20% per stessa categoria
                
            if similarity_score > threshold:
                similar_patterns.append(known_pattern)
                    
        return similar_patterns

    def _update_pattern_statistics(self, pattern: Pattern, response: str, context: Dict[str, Any]):
        """Aggiorna le statistiche del pattern"""
        # Aggiorna le statistiche di utilizzo
        pattern.metadata["usage_count"] = pattern.metadata.get("usage_count", 0) + 1
        
        # Aggiorna le statistiche di risposta
        if response:
            pattern.metadata["response_count"] = pattern.metadata.get("response_count", 0) + 1
            
        # Aggiorna le statistiche di contesto
        if context:
            pattern.metadata["context_count"] = pattern.metadata.get("context_count", 0) + 1
            
        # Notifica gli osservatori
        self.notify_observers("pattern_updated", {
            "pattern": pattern,
            "response": response,
            "context": context
        })

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calcola la similarità tra due testi
        Args:
            text1: Primo testo
            text2: Secondo testo
        Returns:
            float: Score di similarità tra 0 e 1
        """
        # Preprocessa i testi
        processed_text1 = self.preprocess_text(text1)
        processed_text2 = self.preprocess_text(text2)
        
        # Tokenizza
        tokens1 = word_tokenize(processed_text1)
        tokens2 = word_tokenize(processed_text2)
        
        # Rimuovi stop words e applica stemming
        tokens1 = [self.stemmer.stem(token) for token in tokens1 if token not in self.stop_words]
        tokens2 = [self.stemmer.stem(token) for token in tokens2 if token not in self.stop_words]
        
        # Calcola l'intersezione e l'unione dei token
        common_tokens = set(tokens1) & set(tokens2)
        all_tokens = set(tokens1) | set(tokens2)
        
        # Calcola similarità di Jaccard
        if not all_tokens:
            return 0.0
        return len(common_tokens) / len(all_tokens)

    def extract_topics(self, texts: Union[str, List[str]]) -> List[Subtopic]:
        """
        Estrae i topic principali dai testi
        Args:
            texts: Testo singolo o lista di testi da analizzare
        Returns:
            List[Subtopic]: Lista di subtopic trovati
        """
        # Assicurati che texts sia una lista
        if isinstance(texts, str):
            texts = [texts]
            
        # Preprocessa ogni testo individualmente
        processed_texts = []
        for text in texts:
            preprocessed = self.preprocess_text(text)
            processed_texts.append(preprocessed)
            
        # Unisci i testi preprocessati
        combined_text = " ".join(processed_texts)
        
        # Tokenizza il testo combinato
        tokens = word_tokenize(combined_text)
        stemmed_tokens = [self.stemmer.stem(token) for token in tokens]
        
        # Estrai feature linguistiche
        features = self._extract_linguistic_features(combined_text)
        
        subtopics = []
        for category, keywords in self.stemmed_keywords.items():
            # Includiamo anche le parole chiave apprese
            all_keywords = keywords | self.learned_keywords.get(category, set())
            matched_keywords = set(token for token in tokens 
                                if self.stemmer.stem(token) in all_keywords)
            
            if matched_keywords:
                # Miglioriamo il calcolo della confidence
                # 1. Base confidence basato sulla copertura delle parole chiave
                keyword_coverage = len(matched_keywords) / len(all_keywords)
                
                # 2. Frequenza media delle parole chiave trovate
                avg_frequency = len(matched_keywords) / len(tokens)
                frequency_score = min(1.0, avg_frequency)
                
                # 3. Peso delle parole chiave importanti
                important_keywords = set()
                for stem in matched_keywords:
                    if sum(1 for k in self.stemmed_keywords.values() if stem in k) > 1:
                        important_keywords.add(stem)
                importance_score = len(important_keywords) / len(matched_keywords) if matched_keywords else 0
                
                # Combina i punteggi con pesi
                confidence = (
                    0.4 * keyword_coverage +
                    0.35 * frequency_score +
                    0.25 * importance_score
                )
                
                # Abbassiamo la soglia minima per considerare un topic
                if confidence >= 0.1:  # Ridotta da 0.15
                    metadata = {
                        'frequency_score': frequency_score,
                        'importance_score': importance_score,
                        'related_themes': [],
                        'important_keywords': list(matched_keywords & self.important_keywords.get(category, set())),
                        'original_keywords': list(matched_keywords)
                    }
                    
                    subtopic = Subtopic(
                        category=category,
                        confidence=confidence,
                        keywords=matched_keywords,
                        metadata=metadata
                    )
                    subtopics.append(subtopic)
        
        # Ordina per confidence e ritorna i top N
        return sorted(subtopics, key=lambda x: x.confidence, reverse=True)[:8]  # Aumentato da 5 a 8

    def _calculate_embedding(self, text: str) -> List[float]:
        """
        Calcola un embedding semplice per il testo
        Args:
            text: Testo da analizzare
        Returns:
            List[float]: Vettore embedding
        """
        # Preprocessa il testo
        doc = self.nlp(text)
        
        # Usa i vettori delle parole per creare un embedding medio
        if doc.vector_norm:
            return doc.vector.tolist()
            
        # Se non ci sono vettori, restituisci un vettore di zeri
        return [0.0] * 300  # spaCy usa vettori di dimensione 300

    def _extract_linguistic_features(self, text: Union[str, spacy.tokens.doc.Doc]) -> Dict[str, float]:
        """
        Estrae feature linguistiche dal testo
        Args:
            text: Testo da analizzare o documento spaCy
        Returns:
            Dict[str, float]: Dizionario delle feature estratte
        """
        # Se l'input è un documento spaCy, estrai il testo
        if hasattr(text, 'text'):
            text = text.text
            
        # Preprocessa il testo
        preprocessed = self.preprocess_text(text)
        tokens = word_tokenize(preprocessed)
        stemmed = [self.stemmer.stem(token) for token in tokens]
        
        # Inizializza il dizionario delle feature
        features = {}
        
        # Calcola il sentiment score
        sentiment_score = self._calculate_sentiment_score(stemmed)
        features['sentiment_score'] = sentiment_score
        
        # Calcola la copertura per ogni categoria
        for category in self.stemmed_keywords:
            keywords = self.stemmed_keywords[category]
            matches = sum(1 for stem in stemmed if stem in keywords)
            coverage = matches / len(tokens) if tokens else 0
            features[f'{category}_coverage'] = coverage
            
        return features

    def _extract_pattern_features(self, text: str) -> dict:
        """
        Estrae feature per il pattern matching
        Args:
            text: Testo da analizzare
        Returns:
            dict: Dizionario con le feature estratte
        """
        tokens = self.preprocess_text(text)
        stemmed_tokens = [self.stemmer.stem(token) for token in tokens]
        
        features = {
            'token_count': len(tokens),
            'avg_token_length': sum(len(token) for token in tokens) / len(tokens) if tokens else 0,
            'unique_tokens': len(set(tokens)),
            'has_negation': any(token in self.stemmed_negations for token in stemmed_tokens),
            'sentiment_score': self._calculate_sentiment_score(stemmed_tokens)
        }
        
        # Calcola coverage per ogni categoria
        for category, keywords in self.stemmed_keywords.items():
            matched = set(stemmed_tokens) & keywords
            features[f'{category}_coverage'] = len(matched) / len(keywords) if keywords else 0
            features[f'{category}_matched'] = len(matched)
            
        return features

    def validate_pattern(self, pattern: Pattern) -> bool:
        """
        Valida un pattern in base alla sua confidence
        Args:
            pattern: Pattern da validare
        Returns:
            bool: True se il pattern è valido, False altrimenti
        """
        return pattern.confidence >= self.confidence_threshold

    def find_similar_patterns(self, pattern: Pattern, min_similarity: Optional[float] = None) -> List[Pattern]:
        """
        Trova pattern simili a quello dato
        Args:
            pattern: Pattern di riferimento
            min_similarity: Soglia minima di similarità opzionale
        Returns:
            List[Pattern]: Lista di pattern simili
        """
        threshold = min_similarity if min_similarity is not None else self.confidence_threshold
        similar_patterns = []
        
        for known_pattern in self.known_patterns.values():
            similarity = self.calculate_similarity(known_pattern.text, pattern.text)
            if similarity >= threshold:
                similar_patterns.append(known_pattern)
                
        return similar_patterns

    def update_pattern(self, pattern: Pattern, new_text: str) -> Pattern:
        """
        Aggiorna un pattern esistente con nuovo testo
        Args:
            pattern: Pattern da aggiornare
            new_text: Nuovo testo da incorporare
        Returns:
            Pattern: Pattern aggiornato
        """
        # Estrai feature dal nuovo testo
        new_features = self._extract_pattern_features(new_text)
        
        # Aggiorna l'embedding con media pesata
        new_embedding = self._calculate_embedding(new_text)
        pattern.embedding = [
            (1 - self.learning_rate) * old + self.learning_rate * new
            for old, new in zip(pattern.embedding, new_embedding)
        ]
        
        # Aggiorna keywords e confidence
        new_pattern = self.analyze_pattern(new_text)
        pattern.keywords.update(new_pattern.keywords)
        pattern.confidence = (1 - self.learning_rate) * pattern.confidence + self.learning_rate * new_pattern.confidence
        
        return pattern

    def merge_patterns(self, pattern1: Pattern, pattern2: Pattern) -> Pattern:
        """
        Unisce due pattern simili
        Args:
            pattern1: Primo pattern
            pattern2: Secondo pattern
        Returns:
            Pattern: Pattern risultante dalla fusione
        """
        if pattern1.category != pattern2.category:
            raise ValueError("Non è possibile unire pattern di categorie diverse")
            
        # Calcola la similarità
        similarity = self.calculate_similarity(pattern1.text, pattern2.text)
        if similarity < self.confidence_threshold:
            raise ValueError("I pattern non sono abbastanza simili per essere uniti")
            
        # Unisci keywords e calcola nuova confidence
        merged_keywords = pattern1.keywords | pattern2.keywords
        merged_confidence = max(pattern1.confidence, pattern2.confidence)
        
        # Media pesata degli embedding
        w1 = pattern1.confidence / (pattern1.confidence + pattern2.confidence)
        w2 = 1 - w1
        merged_embedding = [
            w1 * e1 + w2 * e2
            for e1, e2 in zip(pattern1.embedding, pattern2.embedding)
        ]
        
        return Pattern(
            category=pattern1.category,
            confidence=merged_confidence,
            keywords=merged_keywords,
            text=pattern1.text,  # Usa il testo del pattern con confidence maggiore
            embedding=merged_embedding
        )

    def find_patterns_by_category(self, category: str, min_confidence: Optional[float] = None) -> List[Pattern]:
        """
        Trova tutti i pattern appartenenti a una categoria
        Args:
            category: Categoria da cercare
            min_confidence: Confidence minima opzionale
        Returns:
            List[Pattern]: Lista di pattern trovati
        """
        threshold = min_confidence if min_confidence is not None else self.confidence_threshold
        matching_patterns = []
        
        # Usa il dizionario delle categorie per una ricerca più efficiente
        for pattern_id in self.pattern_categories.get(category, set()):
            pattern = self.known_patterns[pattern_id]
            if pattern.confidence >= threshold:
                matching_patterns.append(pattern)
                
        # Ordina per confidence decrescente
        return sorted(matching_patterns, key=lambda p: p.confidence, reverse=True)

    def calculate_pattern_similarity(self, pattern1: Pattern, pattern2: Pattern) -> float:
        """
        Calcola la similarità tra due pattern
        Args:
            pattern1: Primo pattern
            pattern2: Secondo pattern
        Returns:
            float: Score di similarità tra 0 e 1
        """
        similarity_score = 0.0
        weights = 0.0
        
        # Calcola similarità basata su embedding
        if pattern1.embedding and pattern2.embedding:
            embedding_similarity = cosine_similarity(
                np.array(pattern1.embedding).reshape(1, -1),
                np.array(pattern2.embedding).reshape(1, -1)
            )[0][0]
            similarity_score += 0.6 * embedding_similarity  # Peso maggiore per embedding
            weights += 0.6
            
        # Calcola similarità basata su parole chiave
        if pattern1.keywords and pattern2.keywords:
            keyword_similarity = len(pattern1.keywords & pattern2.keywords) / max(
                len(pattern1.keywords), len(pattern2.keywords)
            )
            similarity_score += 0.4 * keyword_similarity  # Peso minore per parole chiave
            weights += 0.4
            
        # Se hanno la stessa categoria, aumenta lo score
        if pattern1.category == pattern2.category:
            similarity_score *= 1.2  # Boost del 20%
            
        # Se non abbiamo né embedding né parole chiave, usa solo la categoria
        if weights == 0:
            if pattern1.category == pattern2.category:
                return 0.8  # Score alto per stessa categoria
            return 0.0  # Score basso per categorie diverse
            
        # Normalizza il punteggio in base ai pesi
        return min(1.0, similarity_score / weights)  # Normalizza a 1.0

def main():
    # Esempio di utilizzo
    system = PatternRecognitionSystem()
    text = "Ho imparato a programmare in Python e adesso sto studiando Java."
    pattern = system.analyze_pattern(text)
    logger.info(f"Pattern riconosciuto: {pattern.category} con confidence {pattern.confidence}")

if __name__ == "__main__":
    main()
