"""
Modulo per l'estrazione dei topic dai messaggi.
"""
import logging
from typing import List, Dict

import numpy as np
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity as cs
import math
from collections import Counter
import numpy as np

class SimpleTfidf:
    def __init__(self):
        self.vocab = {}
        self.doc_count = 0
        
    def fit_transform(self, documents):
        self.doc_count = len(documents)
        word_counts = []
        all_words = set()
        
        for doc in documents:
            words = doc.lower().split()
            counts = Counter(words)
            word_counts.append(counts)
            all_words.update(words)
            
        self.vocab = sorted(list(all_words))
        self.idf = {}
        
        for word in self.vocab:
            doc_freq = sum(1 for counts in word_counts if word in counts)
            self.idf[word] = math.log(self.doc_count / (1 + doc_freq))
            
        vectors = []
        for counts in word_counts:
            vector = [counts[word] * self.idf[word] for word in self.vocab]
            vectors.append(vector)
            
        return np.array(vectors)

def cosine_similarity(v1, v2):
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return np.array([[0.0]])
    return np.array([[np.dot(v1, v2.T) / (norm1 * norm2)]])

class TopicExtractor:
    """
    Classe per l'estrazione dei topic dai messaggi.
    """
    def __init__(self, model_path: str = "models"):
        """
        Inizializza l'estrattore di topic.
        
        Args:
            model_path: Percorso dei modelli
        """
        self.model_path = model_path
        self.vectorizer = TfidfVectorizer()
        
    def get_embeddings(self, text: str) -> np.ndarray:
        """
        Calcola gli embeddings di un testo.
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Embeddings del testo
        """
        try:
            # Definisci un vocabolario base per garantire dimensioni consistenti
            base_vocab = [
                "technical", "programming", "code", "development",
                "project", "management", "tasks", "timeline",
                "learning", "education", "training", "study",
                "help", "support", "assistance", "guidance",
                "general", "conversation", "discussion", "chat"
            ]
            
            # Aggiungi il testo corrente al vocabolario
            texts = base_vocab + [text]
            
            # Calcola gli embeddings
            self.vectorizer = TfidfVectorizer(max_features=20)  # Limita a 20 features
            embeddings = self.vectorizer.fit_transform(texts)
            
            # Restituisci l'embedding dell'ultimo testo (quello corrente)
            return embeddings[-1].toarray()[0]
            
        except Exception as e:
            logging.error(f"Errore nel calcolo embeddings: {e}")
            return np.zeros(20)  # Restituisci un vettore di zeri con 20 dimensioni
            
    def extract_topic(
        self,
        text: str
    ) -> str:
        """
        Estrae il topic da un testo.
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Topic estratto
        """
        try:
            # Calcola gli embeddings del testo
            embeddings = self.get_embeddings(text)
            
            # Definisci i topic predefiniti con i loro embeddings
            default_topics = {
                "technical": self.get_embeddings("technical programming code development"),
                "project": self.get_embeddings("project management tasks timeline"),
                "learning": self.get_embeddings("learning education training study"),
                "support": self.get_embeddings("help support assistance guidance"),
                "general": self.get_embeddings("general conversation discussion chat")
            }
            
            # Calcola la similarità con ogni topic
            similarities = {}
            for topic, topic_emb in default_topics.items():
                similarity = cs(
                    embeddings.reshape(1, -1),
                    topic_emb.reshape(1, -1)
                )[0][0]
                similarities[topic] = similarity
                
            # Restituisci il topic con similarità maggiore
            return max(similarities.items(), key=lambda x: x[1])[0]
            
        except Exception as e:
            logging.error(f"Errore nell'estrazione del topic: {e}")
            return "general"  # Topic di default in caso di errore

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calcola la similarità tra due testi.
        
        Args:
            text1: Primo testo
            text2: Secondo testo
            
        Returns:
            Similarità tra i testi (0-1)
        """
        try:
            # Calcola gli embeddings dei testi
            emb1 = self.get_embeddings(text1)
            emb2 = self.get_embeddings(text2)
            
            # Calcola la similarità del coseno
            similarity = cs(
                emb1.reshape(1, -1),
                emb2.reshape(1, -1)
            )[0][0]
            
            return float(similarity)
            
        except Exception as e:
            logging.error(f"Errore nel calcolo della similarità: {e}")
            return 0.0  # Restituisci 0 in caso di errore

    def _extract_topic_from_text(self, text: str) -> str:
        """
        Estrae il topic da un testo.
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Topic estratto
        """
        # Lista di topic comuni
        common_topics = [
            "python",
            "java",
            "javascript",
            "programming",
            "web",
            "database",
            "api",
            "testing",
            "deployment",
            "security"
        ]
        
        # Cerca il topic nel testo
        text_lower = text.lower()
        for topic in common_topics:
            if topic in text_lower:
                return topic
                
        return "general"

    def get_related_topics(self, topic: str) -> List[str]:
        """
        Recupera i topic correlati a quello dato
        
        Args:
            topic: Il topic di cui trovare i correlati
            
        Returns:
            List[str]: Lista di topic correlati
        """
        # Dizionario dei topic correlati
        related_topics = {
            'python': ['programming', 'scripting', 'coding', 'development'],
            'programming': ['coding', 'development', 'software', 'engineering'],
            'web': ['frontend', 'backend', 'fullstack', 'development'],
            'database': ['sql', 'nosql', 'data', 'storage'],
            'api': ['rest', 'graphql', 'webservices', 'integration'],
            'testing': ['unittest', 'integration', 'qa', 'quality'],
            'deployment': ['devops', 'ci/cd', 'cloud', 'infrastructure'],
            'security': ['authentication', 'authorization', 'encryption', 'protection'],
            'java': ['programming', 'android', 'enterprise', 'development'],
            'javascript': ['web', 'frontend', 'nodejs', 'development']
        }

        # Normalizza il topic in input
        topic = topic.lower()
        
        # Se il topic è presente nel dizionario, restituisci i correlati
        if topic in related_topics:
            return related_topics[topic]
            
        # Cerca il topic come valore in altre chiavi
        for key, values in related_topics.items():
            if topic in values:
                result = [key] + [v for v in values if v != topic]
                return result
                
        # Se non trova corrispondenze, calcola la similarità con i topic noti
        similar_topics = []
        for key in related_topics.keys():
            similarity = self.calculate_similarity(topic, key)
            if similarity > 0.5:  # Soglia di similarità
                similar_topics.append(key)
                
        return similar_topics if similar_topics else ["general"]
