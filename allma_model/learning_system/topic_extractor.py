"""
Modulo per l'estrazione dei topic dai messaggi.
"""
import logging
from typing import List, Dict
import re

import numpy as np
from allma_model.utils.text_processing import SimpleTfidf, cosine_similarity

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
        self.vectorizer = SimpleTfidf()
        
    def get_embeddings(self, text: str) -> np.ndarray:
        """
        Calcola gli embeddings di un testo.
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Embeddings del testo
        """
        try:
            base_vocab = [
                "technical", "programming", "code", "development", "python", "java", "javascript", "tecnologia", "intelligenza", "artificiale",
                "progetto", "project", "management", "tasks", "timeline", "android", "apk", "buildozer", "kivy",
                "learning", "education", "training", "study", "imparare", "studiare", "lezione",
                "help", "support", "assistance", "guidance", "aiuto", "supporto", "assistenza",
                "history", "storia", "chi era", "quando", "guerra", "impero", "napoleone",
                "emotion", "emozione", "felice", "triste", "arrabbiato", "paura", "ansia",
                "preference", "preferisco", "mi piace", "odio", "adoro", "colore", "colori", "chiaro", "chiari", "scuro", "scuri", "vestiti", "tessuto", "estate", "sudare",
                "general", "conversation", "discussion", "chat", "parla", "spiega"
            ]
            
            # Aggiungi il testo corrente al vocabolario
            texts = base_vocab + [text]
            
            # Calcola gli embeddings
            max_features = 40
            self.vectorizer = SimpleTfidf(max_features=max_features)
            embeddings = self.vectorizer.fit_transform(texts)
            
            # Restituisci l'embedding dell'ultimo testo (quello corrente)
            vec = embeddings[-1]
            if hasattr(vec, 'toarray'):
                return vec.toarray()[0]
            else:
                return vec
            
        except Exception as e:
            logging.error(f"Errore nel calcolo embeddings: {e}")
            return np.zeros(40)
            
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
            rule_topic = self._extract_topic_from_text(text)
            if rule_topic and rule_topic != "general":
                return rule_topic

            # Calcola gli embeddings del testo
            embeddings = self.get_embeddings(text)
            
            # Definisci i topic predefiniti con i loro embeddings
            default_topics = {
                "technical": self.get_embeddings("technical programming code development python java javascript bug errore"),
                "project": self.get_embeddings("project management tasks timeline android apk buildozer kivy deploy"),
                "learning": self.get_embeddings("learning education training study imparare studiare lezione"),
                "support": self.get_embeddings("help support assistance guidance aiuto supporto assistenza come fare"),
                "history": self.get_embeddings("history storia chi era quando guerra impero napoleone"),
                "emotion": self.get_embeddings("emotion emozione felice triste rabbia paura ansia stress"),
                "preference": self.get_embeddings("preference preferisco mi piace adoro odio scelta colore colori chiari scuri vestiti tessuto estate sudare"),
                "general": self.get_embeddings("general conversation discussion chat parlare spiegare")
            }
            
            # Calcola la similarità con ogni topic
            similarities = {}
            for topic, topic_emb in default_topics.items():
                similarity = cosine_similarity(
                    embeddings.reshape(1, -1),
                    topic_emb.reshape(1, -1)
                )[0][0]
                similarities[topic] = similarity
                
            # Restituisci il topic con similarità maggiore
            best_topic, best_score = max(similarities.items(), key=lambda x: x[1])
            if best_score < 0.05:
                return "general"
            return best_topic
            
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
            similarity = cosine_similarity(
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
        if not text:
            return "general"
        t = text.lower()
        t = re.sub(r'\s+', ' ', t).strip()
        if len(t) <= 3:
            return "general"

        if re.search(r'\b(ciao|salve|hey|ehi|buongiorno|buonasera|buonanotte|hola|hello|hi)\b', t):
            return "general"

        if re.search(r'\b(allma|kivy|buildozer|apk|android|logcat|deploy|ndk|sdk)\b', t):
            return "project"

        if re.search(r'\b(python|java|javascript|js|typescript|ts|bug|errore|stacktrace|traceback|codice|script|funzione|classe|api|database|sql|tecnolog\w*|intelligenza artificiale|\bia\b)\b', t):
            return "technical"

        if re.search(r'\b(lezione|imparare|studiare|spiegami|spiega|insegnami|tutorial)\b', t):
            return "learning"

        if re.search(r'\b(aiuto|supporto|assistenza|come faccio|non funziona|problema|issue)\b', t):
            return "support"

        if re.search(r'\b(storia|chi era|quando|guerra|impero|napoleone|cesare|medioevo|rivoluzione)\b', t):
            return "history"

        if re.search(r'\b(mi sento|sono (felice|triste|arrabbiat[oa]?|ansios[oa]?|spaventat[oa]?)|paura|ansia|stress|depress)\b', t):
            return "emotion"

        if re.search(r'\b(preferisco|mi piace|mi piacciono|adoro|odio|scelgo|scegli|scelta|colore|colori|chiaro|chiari|scuro|scuri|tessut\w*|vestit\w*|magliett\w*|pantalon\w*|estate|sudare|caldo|fresco|rosso|blu|verde|giallo)\b', t):
            return "preference"

        if re.search(r'\bpython\b', t):
            return "python"
        if re.search(r'\bjava\b', t):
            return "java"
        if re.search(r'\bjavascript\b', t):
            return "javascript"

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
