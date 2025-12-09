"""ConversationalMemory - Sistema di memoria conversazionale per ALLMA."""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import re
from collections import defaultdict
from dataclasses import dataclass
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity
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

    def transform(self, documents):
        vectors = []
        for doc in documents:
            words = doc.lower().split()
            counts = Counter(words)
            vector = [counts[word] * self.idf.get(word, 0) for word in self.vocab]
            vectors.append(vector)
        return np.array(vectors)

def cosine_similarity(v1, v2):
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return np.array([[0.0]])
    return np.array([[np.dot(v1, v2.T) / (norm1 * norm2)]])
import numpy as np

@dataclass
class Conversation:
    """Classe per rappresentare una conversazione."""
    id: str
    user_id: str
    timestamp: datetime
    content: str
    metadata: Dict
    embeddings: Optional[np.ndarray] = None

@dataclass
class Message:
    """Classe per rappresentare un messaggio."""
    conversation_id: str
    role: str  # "user" o "assistant"
    content: str
    timestamp: datetime
    metadata: Dict

class ConversationalMemory:
    """Sistema di memoria conversazionale."""
    
    def __init__(self):
        """Inizializza il sistema di memoria conversazionale."""
        self.conversations: Dict[str, List[Conversation]] = defaultdict(list)
        self.vectorizer = SimpleTfidf()
        self.conversation_vectors = {}
        self.messages: List[Message] = []
        
    def store_conversation(
        self,
        user_id: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Memorizza una conversazione con metadata.
        
        Args:
            user_id: ID dell'utente
            content: Contenuto della conversazione
            metadata: Metadata opzionali
            
        Returns:
            ID della conversazione memorizzata
        """
        if metadata is None:
            metadata = {}
            
        # Genera ID univoco
        conversation_id = f"{user_id}_{datetime.now().timestamp()}"
        
        # Crea oggetto conversazione
        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            timestamp=datetime.now(),
            content=content,
            metadata=metadata
        )
        
        # Calcola embedding
        try:
            vectors = self.vectorizer.fit_transform([content])
            conversation.embeddings = vectors.toarray()[0]
        except Exception as e:
            print(f"Errore nel calcolo embeddings: {e}")
            
        # Memorizza conversazione
        self.conversations[user_id].append(conversation)
        
        # Crea e memorizza il messaggio
        message = Message(
            conversation_id=conversation_id,
            role="user",
            content=content,
            timestamp=conversation.timestamp,
            metadata=metadata
        )
        self.messages.append(message)
        
        # Aggiorna vettori conversazione
        if conversation.embeddings is not None:
            self.conversation_vectors[conversation_id] = conversation.embeddings
            
        return conversation_id
        
    def retrieve_relevant_context(
        self,
        current_topic: str,
        user_id: Optional[str] = None,
        max_results: int = 5
    ) -> List[Tuple[float, Conversation]]:
        """
        Recupera il contesto rilevante per il topic corrente.
        
        Args:
            current_topic: Topic corrente
            user_id: ID utente opzionale per filtrare per utente
            max_results: Numero massimo di risultati
            
        Returns:
            Lista di tuple (score, conversazione) ordinate per rilevanza
        """
        if not current_topic.strip():
            return []
            
        # Calcola embedding del topic
        try:
            topic_vector = self.vectorizer.transform([current_topic]).toarray()[0]
        except Exception as e:
            print(f"Errore nel calcolo embedding topic: {e}")
            return []
            
        results = []
        
        # Filtra conversazioni per utente se specificato
        conversations = (
            self.conversations[user_id] if user_id
            else [c for convs in self.conversations.values() for c in convs]
        )
        
        # Calcola similarità con ogni conversazione
        for conv in conversations:
            if conv.embeddings is not None:
                similarity = cosine_similarity(
                    [topic_vector],
                    [conv.embeddings]
                )[0][0]
                results.append((similarity, conv))
                
        # Ordina per similarità e prendi i top N
        results.sort(reverse=True, key=lambda x: x[0])
        return results[:max_results]

    def get_conversation_history(
        self,
        conversation_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        Recupera la storia di una conversazione.
        
        Args:
            conversation_id: ID della conversazione
            start_time: Tempo di inizio opzionale
            end_time: Tempo di fine opzionale
            limit: Numero massimo di messaggi da recuperare
            
        Returns:
            Lista di messaggi
        """
        if not conversation_id:
            raise ValueError("Conversation ID è richiesto")
            
        # Filtra i messaggi per conversation_id e timestamp
        messages = [
            msg for msg in self.messages
            if msg.conversation_id == conversation_id and
            (start_time is None or msg.timestamp >= start_time) and
            (end_time is None or msg.timestamp <= end_time)
        ]
        
        # Ordina per timestamp
        messages = sorted(messages, key=lambda x: x.timestamp)
        
        # Applica il limite se specificato
        if limit is not None:
            messages = messages[:limit]
            
        return messages
        
    def analyze_conversation_patterns(
        self,
        user_id: str
    ) -> Dict:
        """
        Analizza i pattern nelle conversazioni di un utente.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Dizionario con statistiche e pattern identificati
        """
        conversations = self.conversations[user_id]
        
        if not conversations:
            return {
                'total_conversations': 0,
                'avg_length': 0,
                'common_topics': [],
                'time_patterns': {}
            }
            
        # Calcola statistiche base
        total = len(conversations)
        avg_length = sum(len(c.content) for c in conversations) / total
        
        # Analizza pattern temporali
        hour_distribution = defaultdict(int)
        for conv in conversations:
            hour = conv.timestamp.hour
            hour_distribution[hour] += 1
            
        # Identifica topic comuni
        all_content = [c.content for c in conversations]
        try:
            tfidf = TfidfVectorizer(
                max_features=10,
                stop_words='english'
            )
            tfidf.fit_transform(all_content)
            common_topics = tfidf.get_feature_names_out().tolist()
        except:
            common_topics = []
            
        return {
            'total_conversations': total,
            'avg_length': avg_length,
            'common_topics': common_topics,
            'time_patterns': dict(hour_distribution)
        }
        
    def clear_old_conversations(
        self,
        user_id: str,
        before_date: datetime
    ) -> int:
        """
        Rimuove le conversazioni vecchie per un utente.
        
        Args:
            user_id: ID dell'utente
            before_date: Data prima della quale rimuovere
            
        Returns:
            Numero di conversazioni rimosse
        """
        if user_id not in self.conversations:
            return 0
            
        original_count = len(self.conversations[user_id])
        
        # Filtra conversazioni
        self.conversations[user_id] = [
            c for c in self.conversations[user_id]
            if c.timestamp >= before_date
        ]
        
        # Aggiorna vettori
        for conv_id in list(self.conversation_vectors.keys()):
            if conv_id.startswith(f"{user_id}_"):
                try:
                    parts = conv_id.split('_')
                    if len(parts) >= 2:
                        timestamp = float(parts[-1])
                        if datetime.fromtimestamp(timestamp) < before_date:
                            del self.conversation_vectors[conv_id]
                except (ValueError, IndexError):
                    continue
                    
        return original_count - len(self.conversations[user_id])

    def store_message(
        self,
        conversation_id: str,
        content: str,
        metadata: Optional[Dict] = None,
        role: str = "assistant"
    ) -> None:
        """
        Memorizza un messaggio.
        
        Args:
            conversation_id: ID della conversazione
            content: Contenuto del messaggio
            metadata: Metadati opzionali
            role: Ruolo del messaggio ("user" o "assistant")
        """
        if metadata is None:
            metadata = {}
            
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata
        )
        self.messages.append(message)

    def get_recent_interactions(self, user_id: str, limit: int = 10) -> List[Message]:
        """
        Recupera le interazioni recenti per un utente
        
        Args:
            user_id: ID dell'utente
            limit: Numero massimo di interazioni da recuperare
            
        Returns:
            List[Message]: Lista delle interazioni recenti
        """
        # Filtra i messaggi per user_id
        user_messages = []
        for message in self.messages:
            conversation = next((c for c in self.conversations[user_id] if c.id == message.conversation_id), None)
            if conversation:
                user_messages.append(message)
                
        # Ordina per timestamp decrescente e limita il numero
        user_messages.sort(key=lambda m: m.timestamp, reverse=True)
        return user_messages[:limit]

    def create_conversation(self, user_id: str) -> str:
        """
        Crea una nuova conversazione.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            ID della conversazione
        """
        from uuid import uuid4
        conversation_id = str(uuid4())
        self.conversations[user_id].append(
            Conversation(
                id=conversation_id,
                user_id=user_id,
                timestamp=datetime.now(),
                content="",
                metadata={},
                embeddings=None
            )
        )
        return conversation_id
