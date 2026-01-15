from typing import List, Dict, Any, Tuple
import re
from .context_understanding import ContextUnderstandingSystem

class EnhancedCognitiveProcessor:
    def __init__(self):
        # Domini di conoscenza espansi
        self.domains = {
            'programmazione': {
                'concetti': ['variabile', 'funzione', 'classe', 'oggetto', 'metodo', 'array', 'loop', 'condizione'],
                'azioni': ['programmare', 'sviluppare', 'debuggare', 'testare', 'ottimizzare', 'implementare'],
                'strumenti': ['IDE', 'compilatore', 'debugger', 'framework', 'libreria', 'API'],
                'linguaggi': ['Python', 'Java', 'C++', 'JavaScript', 'Kotlin', 'Swift'],
                'paradigmi': ['object-oriented', 'funzionale', 'procedurale', 'event-driven']
            },
            'emozioni': {
                'base': ['felicità', 'tristezza', 'rabbia', 'paura', 'sorpresa', 'disgusto'],
                'complesse': ['ansia', 'frustrazione', 'soddisfazione', 'orgoglio', 'delusione', 'entusiasmo'],
                'intensità': ['molto', 'poco', 'abbastanza', 'estremamente'],
                'valenza': ['positiva', 'negativa', 'neutra']
            },
            'apprendimento': {
                'processi': ['memorizzare', 'comprendere', 'applicare', 'analizzare', 'valutare', 'creare'],
                'stili': ['visivo', 'uditivo', 'cinestetico', 'verbale'],
                'fasi': ['iniziale', 'intermedia', 'avanzata', 'esperta'],
                'risultati': ['successo', 'fallimento', 'progresso', 'stallo']
            },
            'problem_solving': {
                'fasi': ['identificazione', 'analisi', 'pianificazione', 'esecuzione', 'verifica'],
                'strategie': ['divide-et-impera', 'forza bruta', 'euristica', 'backtracking'],
                'ostacoli': ['bug', 'errore', 'conflitto', 'limitazione', 'vincolo']
            }
        }
        
        # Topics e keywords associati
        self.topics = {
            'programmazione': ['codice', 'programma', 'sviluppo', 'software', 'applicazione', 'bug', 'debug'],
            'apprendimento': ['imparare', 'studiare', 'capire', 'comprendere', 'memorizzare', 'esercizio'],
            'emozioni': ['sentire', 'provare', 'emozione', 'sensazione', 'stato d\'animo', 'umore'],
            'problem_solving': ['problema', 'soluzione', 'analisi', 'strategia', 'approccio', 'risoluzione'],
            'storia': ['antico', 'epoca', 'periodo', 'civiltà', 'impero', 'regno', 'guerra'],
            'scienza': ['ricerca', 'esperimento', 'teoria', 'ipotesi', 'scoperta', 'studio'],
            'tecnologia': ['innovazione', 'dispositivo', 'sistema', 'hardware', 'software', 'rete'],
            'arte': ['dipinto', 'scultura', 'musica', 'letteratura', 'creatività', 'espressione']
        }
        
        # Tipi di relazioni
        self.relation_types = {
            'causal': ['perché', 'quindi', 'causa', 'effetto', 'conseguenza'],
            'temporale': ['prima', 'dopo', 'durante', 'mentre', 'quando'],
            'spaziale': ['sopra', 'sotto', 'dentro', 'fuori', 'vicino'],
            'logica': ['se', 'allora', 'ma', 'oppure', 'invece'],
            'comparativa': ['più', 'meno', 'come', 'simile', 'diverso'],
            'appartenenza': ['parte di', 'contiene', 'appartiene', 'include'],
            'emotiva': ['mi sento', 'provo', 'sono', 'mi fa'],
            'intensità': ['molto', 'poco', 'abbastanza', 'troppo']
        }
        
        self.understanding_level = 0.0
        self.context_memory = []
        self.concept_confidence_threshold = 0.6
        
        # Inizializza il sistema di comprensione del contesto
        self.context_system = ContextUnderstandingSystem()
        
    def process_input(self, input_text: str, context: Dict[str, Any] = None, 
                     image_path: str = None, audio_path: str = None) -> Dict[str, Any]:
        """
        Processa l'input dell'utente con analisi multimodale
        """
        # Analisi completa del contesto
        context_analysis = self.context_system.analyze_complete_context(
            text=input_text,
            image_path=image_path
        )
        
        # Estrai concetti e relazioni
        concepts = self.extract_concepts(input_text)
        
        # Analisi cognitiva standard
        topics = self.extract_topics(input_text)
        complexity = self._analyze_complexity(input_text)
        understanding = self._evaluate_understanding(topics, complexity, context)
        
        # Integra tutti i risultati
        result = {
            'topics': topics,
            'complexity': complexity,
            'understanding_level': understanding,
            'concepts': concepts,
            'context_analysis': context_analysis,
            'multimodal_confidence': self._calculate_multimodal_confidence(
                concepts, context_analysis
            )
        }
        
        return result
        
    def _calculate_multimodal_confidence(self, concepts: List[Tuple[str, str, float]], 
                                       context_analysis: Dict[str, Any]) -> float:
        """
        Calcola la confidenza combinando analisi concettuale e contestuale
        """
        confidences = []
        
        # Confidenza dai concetti
        if concepts:
            confidences.append(sum(conf for _, _, conf in concepts) / len(concepts))
            
        # Confidenza dall'analisi testuale
        if 'text_analysis' in context_analysis:
            text_analysis = context_analysis['text_analysis']
            if 'confidence' in text_analysis:
                confidences.append(text_analysis['confidence'])
                
        # Confidenza dall'analisi immagini
        if 'image_analysis' in context_analysis:
            image_analysis = context_analysis['image_analysis']
            if 'confidence_scores' in image_analysis:
                scores = image_analysis['confidence_scores']
                if scores:
                    confidences.append(sum(scores) / len(scores))
                    
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def extract_topics(self, text: str) -> List[str]:
        """Estrae i topic dal testo"""
        text = text.lower()
        found_topics = []
        
        for topic, keywords in self.topics.items():
            if any(keyword in text for keyword in keywords):
                found_topics.append(topic)
                
        # Aggiorna la storia dei topic
        self.last_topics = found_topics
        
        return found_topics
        
    def extract_concepts(self, text: str) -> List[Tuple[str, str, float]]:
        """Estrae i concetti dal testo con il loro tipo e confidenza"""
        text = text.lower()
        concepts = []
        
        # Cerca concetti nei domini
        for domain, categories in self.domains.items():
            for category, terms in categories.items():
                for term in terms:
                    if term.lower() in text:
                        confidence = self._calculate_concept_confidence(term, text)
                        if confidence >= self.concept_confidence_threshold:
                            concepts.append((term, f"{domain}.{category}", confidence))
        
        # Cerca relazioni
        for rel_type, markers in self.relation_types.items():
            for marker in markers:
                if marker.lower() in text:
                    confidence = self._calculate_concept_confidence(marker, text)
                    if confidence >= self.concept_confidence_threshold:
                        concepts.append((marker, f"relation.{rel_type}", confidence))
        
        return concepts
    
    def _calculate_concept_confidence(self, concept: str, text: str) -> float:
        """Calcola la confidenza di un concetto nel testo"""
        # Semplice euristica basata su:
        # - Frequenza del concetto
        # - Posizione nel testo
        # - Lunghezza del concetto
        
        text = text.lower()
        concept = concept.lower()
        
        # Frequenza
        frequency = text.count(concept)
        freq_score = min(frequency / 3, 1.0)  # Normalizza a max 1.0
        
        # Posizione (più importante se all'inizio)
        position = text.find(concept)
        pos_score = 1.0 - (position / len(text)) if position >= 0 else 0.0
        
        # Lunghezza (concetti più lunghi sono più significativi)
        len_score = min(len(concept) / 10, 1.0)  # Normalizza a max 1.0
        
        # Media pesata
        confidence = (freq_score * 0.4 + pos_score * 0.3 + len_score * 0.3)
        
        return confidence
    
    def _analyze_complexity(self, text: str) -> float:
        """Analizza la complessità del testo"""
        # Semplice euristica basata su:
        # - Lunghezza delle frasi
        # - Varietà del vocabolario
        # - Presenza di termini specifici
        
        words = text.split()
        unique_words = set(words)
        
        complexity = 0.0
        complexity += len(words) * 0.01  # Lunghezza
        complexity += len(unique_words) / len(words) * 0.5  # Varietà
        
        # Presenza di termini specifici
        specific_terms = sum(1 for topic in self.topics.values() 
                           for term in topic if term in text.lower())
        complexity += specific_terms * 0.1
        
        return min(complexity, 1.0)
    
    def _evaluate_understanding(self, topics: List[str], 
                              complexity: float, 
                              context: Dict[str, Any]) -> float:
        """Valuta il livello di comprensione"""
        understanding = 0.0
        
        # Base sulla complessità
        understanding += (1 - complexity) * 0.4
        
        # Familiarità con i topic
        topic_familiarity = len(set(topics) & set(self.last_topics)) / max(len(topics), 1)
        understanding += topic_familiarity * 0.3
        
        # Contesto precedente
        if context.get('previous_understanding'):
            understanding += context['previous_understanding'] * 0.3
        else:
            understanding += 0.3  # Default
        
        return min(understanding, 1.0)
    
    def _extract_concepts(self, text: str) -> List[str]:
        """Estrae concetti chiave dal testo"""
        # Implementazione base che estrae parole chiave
        words = re.findall(r'\b\w+\b', text.lower())
        concepts = []
        
        # Cerca concetti basati sui topic
        for topic, keywords in self.topics.items():
            for keyword in keywords:
                if keyword in words and keyword not in concepts:
                    concepts.append(keyword)
        
        return concepts
