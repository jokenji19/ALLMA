from typing import Dict, List, Optional
import re

class InformationExtractor:
    """Classe per l'estrazione di informazioni dal testo"""
    
    def __init__(self):
        """Inizializza l'estrattore di informazioni"""
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
        text = text.lower()
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
            if any(alias in text for alias in aliases):
                found_concepts.append(concept)
                
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
        # Semplice euristica: parole che iniziano con maiuscola
        words = text.split()
        return [word for word in words if word[0].isupper() and len(word) > 1]
        
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
            if any(syn in text_lower for syn in synonyms):
                found_topics.append(topic)
                
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
