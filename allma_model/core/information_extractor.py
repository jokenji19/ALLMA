from typing import Dict, List, Optional
import re

class InformationExtractor:
    """Classe per l'estrazione di informazioni dal testo"""
    
    def __init__(self):
        """Inizializza l'estrattore di informazioni"""
        self._latin_letter_re = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]", flags=re.UNICODE)
        self._person_stopwords = {
            "ciao", "salve", "hey", "ehi", "buongiorno", "buonasera", "buonanotte",
            "ok", "okay", "okey", "fine", "good", "great", "nice", "thanks", "thank", "you",
            "va", "bene",
            "chi", "che", "cosa", "quale", "quali", "quanto", "quanta", "quanti", "quante",
            "come", "quando", "dove", "perché", "perche", "per", "non", "si", "no", "sì",
            "io", "tu", "lui", "lei", "noi", "voi", "loro", "mi", "ti", "ci", "vi",
            "ha", "hai", "hanno", "sono", "sei", "è", "e",
            "who", "what", "which", "when", "where", "why", "how", "is", "are", "am", "was", "were", "be", "been", "being",
            "do", "does", "did", "can", "could", "would", "should", "will", "shall", "may", "might", "must",
            "i", "you", "he", "she", "we", "they", "me", "him", "her", "us", "them", "my", "your", "his", "its", "our", "their",
            "and", "or", "but", "not", "yes", "no",
            "que", "quien", "quién", "cual", "cuál", "cuando", "cuándo", "donde", "dónde", "porque", "porqué", "como", "cómo",
            "bonjour", "salut", "qui", "quoi", "quel", "quels", "quelle", "quelles", "quand", "où", "ou", "pourquoi", "comment",
            "hallo", "guten", "morgen", "abend", "nacht", "wer", "was", "welche", "wann", "wo", "warum", "wie",
        }
        self.known_concepts = {
            'machine_learning': ['machine learning', 'ml', 'apprendimento automatico'],
            'deep_learning': ['deep learning', 'dl', 'apprendimento profondo'],
            'data_science': ['data science', 'ds', 'scienza dei dati'],
            'neural_networks': ['reti neurali', 'neural networks', 'nn'],
            'artificial_intelligence': ['intelligenza artificiale', 'ai', 'ia']
        }
        
    def extract_information(self, text: str) -> Dict:
        """Estrae informazioni strutturate dal testo"""
        return {
            'concepts': self.extract_concepts(text),
            'entities': self.extract_entities(text),
            'keywords': self.extract_keywords(text),
            'topics': self.extract_topics(text)
        }
        
    def extract_concepts(self, text: str) -> List[str]:
        """Estrae i concetti noti dal testo"""
        text = (text or "").lower()
        found_concepts = []
        
        # Dizionario dei concetti e delle loro varianti
        concepts = {
            'machine_learning': [
                'machine learning', 'ml', 'apprendimento automatico',
                'apprendimento macchina', 'apprendimento supervisionato',
                'apprendimento non supervisionato'
            ],
            'neural_networks': [
                'reti neurali', 'neural networks', 'nn', 'reti neurali artificiali',
                'artificial neural networks', 'ann'
            ],
            'deep_learning': [
                'deep learning', 'dl', 'apprendimento profondo',
                'deep neural networks', 'reti neurali profonde',
                'convolutional networks', 'reti convoluzionali'
            ],
            'data_science': [
                'data science', 'ds', 'scienza dei dati',
                'analisi dati', 'data analysis', 'data mining',
                'data visualization', 'visualizzazione dati'
            ],
            'artificial_intelligence': [
                'artificial intelligence', 'ai', 'intelligenza artificiale',
                'ia', 'machine intelligence', 'intelligenza macchina'
            ],
            'natural_language_processing': [
                'natural language processing', 'nlp', 'elaborazione del linguaggio naturale',
                'text analysis', 'analisi del testo', 'text mining'
            ]
        }
        
        # Cerca ogni concetto e le sue varianti nel testo
        for concept, aliases in concepts.items():
            for alias in aliases:
                a = alias.lower().strip()
                if not a:
                    continue
                if " " in a:
                    if a in text:
                        found_concepts.append(concept)
                        break
                else:
                    if len(a) <= 3:
                        if re.search(rf"\b{re.escape(a)}\b", text):
                            found_concepts.append(concept)
                            break
                    else:
                        if re.search(rf"\b{re.escape(a)}\b", text) or a in text:
                            found_concepts.append(concept)
                            break
                
        return found_concepts
        
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Estrae le entità dal testo"""
        return {
            'persons': self.extract_persons(text),
            'organizations': self.extract_organizations(text),
            'locations': self.extract_locations(text)
        }
        
    def extract_persons(self, text: str) -> List[str]:
        """Estrae i nomi di persona dal testo"""
        if not text:
            return []

        cleaned = re.sub(r"[^\w\s'’À-ÖØ-öø-ÿ]", " ", text, flags=re.UNICODE)
        if not self._latin_letter_re.search(cleaned):
            return []
        tokens = [t for t in cleaned.split() if t]

        results: List[str] = []
        seen = set()

        i = 0
        while i < len(tokens):
            token = tokens[i]
            token_clean = token.strip("'’")
            if len(token_clean) <= 1 or not token_clean[0].isupper() or token_clean.isdigit():
                i += 1
                continue

            phrase_tokens = [token_clean]
            j = i + 1
            while j < len(tokens):
                nxt = tokens[j].strip("'’")
                if len(nxt) <= 1 or nxt.isdigit() or not nxt[0].isupper():
                    break
                phrase_tokens.append(nxt)
                j += 1

            phrase_lowers = [p.lower() for p in phrase_tokens]
            if any(p not in self._person_stopwords for p in phrase_lowers):
                phrase = " ".join(phrase_tokens)
                key = phrase.lower()
                if key not in seen:
                    results.append(phrase)
                    seen.add(key)

            i = j

        return results
        
    def extract_organizations(self, text: str) -> List[str]:
        """Estrae i nomi di organizzazioni dal testo"""
        # Per ora restituisce una lista vuota
        return []
        
    def extract_locations(self, text: str) -> List[str]:
        """Estrae i nomi di luoghi dal testo"""
        # Per ora restituisce una lista vuota
        return []
        
    def extract_keywords(self, text: str) -> List[str]:
        """Estrae le parole chiave dal testo"""
        # Rimuove la punteggiatura e converte in minuscolo
        text = re.sub(r'[^\w\s]', '', text.lower())
        
        # Divide in parole e rimuove le stop words
        stop_words = {'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una',
                     'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra',
                     'è', 'sono', 'ha', 'hanno', 'essere', 'avere', 'fare'}
        words = text.split()
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return keywords

    def extract_topics(self, text: str) -> List[str]:
        """
        Estrae i topic dal testo
        
        Args:
            text: Il testo da analizzare
            
        Returns:
            List[str]: Lista di topic estratti
        """
        if not text:
            return []
            
        # Lista di topic conosciuti e loro sinonimi
        known_topics = {
            'machine_learning': ['machine learning', 'ml', 'artificial intelligence', 'ai'],
            'deep_learning': ['deep learning', 'neural networks', 'dl'],
            'data_science': ['data science', 'data analysis', 'analytics'],
            'computer_vision': ['computer vision', 'image processing', 'cv'],
            'nlp': ['natural language processing', 'nlp', 'text analysis'],
            'robotics': ['robotics', 'robots', 'automation'],
            'iot': ['internet of things', 'iot', 'connected devices']
        }
        
        found_topics = []
        text_lower = text.lower()
        
        # Cerca i topic nel testo
        for topic, synonyms in known_topics.items():
            for syn in synonyms:
                s = syn.lower().strip()
                if not s:
                    continue
                if " " in s:
                    if s in text_lower:
                        found_topics.append(topic)
                        break
                else:
                    if len(s) <= 3:
                        if re.search(rf"\b{re.escape(s)}\b", text_lower):
                            found_topics.append(topic)
                            break
                    else:
                        if re.search(rf"\b{re.escape(s)}\b", text_lower) or s in text_lower:
                            found_topics.append(topic)
                            break
                
        return found_topics

    def get_related_topics(self, topic: str) -> List[str]:
        """
        Recupera i topic correlati a quello dato
        
        Args:
            topic: Il topic di cui trovare i correlati
            
        Returns:
            List[str]: Lista di topic correlati
        """
        # Implementazione base: restituisce topic simili basati su regole semplici
        related = []
        
        # 1. Aggiungi varianti maiuscole/minuscole
        related.append(topic.lower())
        related.append(topic.upper())
        related.append(topic.capitalize())
        
        # 2. Gestisci plurali/singolari semplici
        if topic.endswith('s'):
            related.append(topic[:-1])  # Rimuovi 's'
        else:
            related.append(topic + 's')  # Aggiungi 's'
            
        # 3. Gestisci alcuni sinonimi comuni
        synonyms = {
            'python': ['py', 'python3', 'python2'],
            'javascript': ['js', 'ecmascript'],
            'typescript': ['ts'],
            'java': ['jvm'],
            'database': ['db', 'rdbms'],
            'function': ['func', 'method'],
            'variable': ['var'],
            'constant': ['const'],
            'class': ['object', 'type'],
            'module': ['package', 'library']
        }
        
        if topic in synonyms:
            related.extend(synonyms[topic])
            
        # Rimuovi duplicati e il topic originale
        return list(set(related) - {topic})
