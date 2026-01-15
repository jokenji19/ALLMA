"""TopicExtractor - Estrazione di topic da testi"""

import logging
from typing import Optional
import numpy as np
from allma_model.utils.text_processing import SimpleTfidf, cosine_similarity

class TopicExtractor:
    """Classe per l'estrazione di topic da testi"""

    def __init__(self):
        """Inizializza il TopicExtractor"""
        self.vectorizer = SimpleTfidf(
            max_features=1000,
            stop_words='english'
        )
        self.topics = []  # Lista di topic conosciuti
        self.topic_vectors = None  # Vettori dei topic

    def extract_topic(self, text: str) -> Optional[str]:
        """
        Estrae il topic principale da un testo.
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Topic estratto o None se non trovato
        """
        try:
            # Vettorizza il testo
            text_vector = self.vectorizer.fit_transform([text])
            
            # Estrai le parole chiave più rilevanti
            feature_array = np.array(self.vectorizer.get_feature_names_out())
            tfidf_sorting = np.argsort(text_vector.toarray()).flatten()[::-1]
            
            # Prendi le prime N parole come topic
            n_words = 3
            top_words = feature_array[tfidf_sorting][:n_words]
            
            # Unisci le parole in un topic
            topic = " ".join(top_words)
            
            return topic
            
        except Exception as e:
            logging.error(f"Errore nell'estrazione del topic: {str(e)}")
            return None

    def add_known_topic(self, topic: str, keywords: list[str]):
        """
        Aggiunge un topic conosciuto con le sue parole chiave.
        
        Args:
            topic: Nome del topic
            keywords: Lista di parole chiave associate
        """
        self.topics.append((topic, keywords))
        # Aggiorna i vettori dei topic
        if self.topic_vectors is None:
            self.topic_vectors = self.vectorizer.fit_transform([" ".join(keywords)])
        else:
            self.topic_vectors = np.vstack([
                self.topic_vectors,
                self.vectorizer.transform([" ".join(keywords)])
            ])

    def find_similar_topic(self, text: str, threshold: float = 0.5) -> Optional[str]:
        """
        Trova il topic più simile tra quelli conosciuti.
        
        Args:
            text: Testo da analizzare
            threshold: Soglia minima di similarità
            
        Returns:
            Topic più simile o None se nessuno supera la soglia
        """
        if not self.topics:
            return None
            
        try:
            # Vettorizza il testo
            text_vector = self.vectorizer.transform([text])
            
            # Calcola similarità con tutti i topic
            similarities = cosine_similarity(text_vector, self.topic_vectors)
            
            # Trova il topic più simile
            best_match = np.argmax(similarities)
            if similarities[0][best_match] >= threshold:
                return self.topics[best_match][0]
                
            return None
            
        except Exception as e:
            logging.error(f"Errore nel calcolo della similarità: {str(e)}")
            return None
