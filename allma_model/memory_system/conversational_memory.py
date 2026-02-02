"""ConversationalMemory - Sistema di memoria conversazionale per ALLMA."""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import re
from collections import defaultdict
from dataclasses import dataclass
import numpy as np
from allma_model.utils.text_processing import SimpleTfidf, cosine_similarity



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
    user_id: Optional[str] = None

class ConversationalMemory:
    """Sistema di memoria conversazionale."""
    
    def __init__(self):
        """Inizializza il sistema di memoria conversazionale."""
        self.conversations: Dict[str, List[Conversation]] = defaultdict(list)
        self.vectorizer = SimpleTfidf()
        self.conversation_vectors = {}
        self.messages: List[Message] = []
        
        # Load persistent memory
        self.load_memory()
        
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
            metadata=metadata,
            user_id=user_id
        )
        self.messages.append(message)
        self.save_memory()
        
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
        results = []
        
        # 1. FACT CHECK (Priority High)
        # Search in extracted User Data first
        if user_id and hasattr(self, 'user_data') and user_id in self.user_data:
            user_facts = self.user_data[user_id]
            for key, value in user_facts.items():
                if key in current_topic.lower() or value in current_topic.lower():
                    # Create a synthetic conversation for the fact
                    fact_conv = Conversation(
                        id=f"fact_{key}",
                        user_id=user_id,
                        timestamp=datetime.now(),
                        content=f"FACT: Il tuo {key} è {value}.",
                        metadata={'type': 'fact'}
                    )
                    results.append((1.0, fact_conv)) # Max score for facts

        if not current_topic.strip():
            return results
            
        # Calcola embedding del topic
        try:
            topic_vector = self.vectorizer.transform([current_topic]).toarray()[0]
        except Exception as e:
            print(f"Errore nel calcolo embedding topic: {e}")
            return results
            
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
            tfidf = SimpleTfidf(
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
        self.save_memory()

    def save_interaction(self, user_id: str, message: str, role: str):
        """Salva una interazione nella memoria."""
        if user_id not in self.conversations:
            self.conversations[user_id] = []
            
        self.user_data = getattr(self, 'user_data', {})
        if user_id not in self.user_data: self.user_data[user_id] = {}

        # NAME CAPTURE PATTERN
        if role == "user":
            import re
            # Name
            name_pattern = re.search(r"(?:mi chiamo|sono|il mio nome è) (\w+)", message, re.IGNORECASE)
            if name_pattern:
                extracted_name = name_pattern.group(1)
                self.user_data[user_id]['name'] = extracted_name
                print(f"🧠 MEMORY: Name captured '{extracted_name}'")
            
            # GENERIC PREFERENCE PATTERN: "Il mio [KEY] preferito è [VALUE]"
            # e.g. "Il mio colore preferito è il blu" -> key=colore, value=blu
            pref_pattern = re.search(r"(?:il mio|la mia) (\w+) preferit[oa] è (?:il |lo |la |i |le )?([\w\s]+)", message, re.IGNORECASE)
            if pref_pattern:
                key = pref_pattern.group(1).lower() # colore
                value = pref_pattern.group(2).strip() # blu
                if value.endswith('.'): value = value[:-1]
                self.user_data[user_id][key] = value
                print(f"🧠 MEMORY: Fact captured '{key}' = '{value}'")
        
        # --- PHASE 18: COGNITIVE MEMORY (LLM-DRIVEN) ---
        # Parse "MEM=" commands from the Assistant's own thought process
        if role == "assistant":
            # Search for [[TH:...]] block
            import re
            th_block = re.search(r"\[\[TH:(.*?)\]\]", message, re.DOTALL)
            if th_block:
                content_inside = th_block.group(1)
                print(f"🧠 [DEBUG] TH Block trovato: {content_inside[:150]}...")  # PHASE 20: Debug logging
                
                # PHASE 20 FIX: More flexible regex to handle underscores, Italian chars, spaces
                # Pattern: MEM=key:value where key can have letters/numbers/underscores/spaces
                # and value can have letters/numbers/spaces/dots/commas/Italian accents
                mem_cmd = re.search(r"MEM=([a-zA-Z0-9_\s]+):([a-zA-Z0-9_\s\.\,àèéìòùÀÈÉÌÒÙ]+)", content_inside)
                
                if mem_cmd:
                    key = mem_cmd.group(1).strip().replace(' ', '_')  # Replace spaces with underscores
                    value = mem_cmd.group(2).strip()
                    self.user_data[user_id][key.lower()] = value
                    print(f"🧠 COGNITIVE MEMORY: Analizzato & Salvato Fatto '{key}' = '{value}'")
                else:
                    print(f"🧠 [DEBUG] Nessun comando MEM= trovato nel blocco TH")  # PHASE 20: Debug logging
            else:
                print(f"🧠 [DEBUG] Nessun blocco [[TH:...]] trovato nel messaggio")  # PHASE 20: Debug logging


        msg = Message(
            role=role,
            content=message,
            timestamp=datetime.now(),
            user_id=user_id,
            conversation_id="default", # Simplification for mobile
            metadata={} 
        )
        self.messages.append(msg) # Assuming self.messages is where interactions are stored
        self.save_memory()

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
        return conversation_id

    def _json_serial(self, obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError (f"Type {type(obj)} not serializable")

    def save_memory(self):
        """Salva lo stato della memoria su file JSON."""
        data = {
            "conversations": {
                uid: [
                    {
                        "id": c.id, 
                        "user_id": c.user_id, 
                        "timestamp": c.timestamp, 
                        "content": c.content, 
                        "metadata": c.metadata
                    } for c in convs
                ] 
                for uid, convs in self.conversations.items()
            },
            "messages": [
                {
                    "conversation_id": m.conversation_id,
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp,
                    "metadata": m.metadata,
                    "user_id": getattr(m, 'user_id', None)
                } for m in self.messages
            ],
            "user_data": getattr(self, 'user_data', {})
        }
        
        try:
            import os
            # Use internal storage path or current dir
            file_path = os.path.join(os.getcwd(), 'allma_memory.json')
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, default=self._json_serial, ensure_ascii=False, indent=2)
            print(f"💾 MEMORY SAVED to {file_path}")
        except Exception as e:
            print(f"❌ MEMORY SAVE FAILED: {e}")

    def load_memory(self):
        """Carica lo stato della memoria da file JSON."""
        try:
            import os
            file_path = os.path.join(os.getcwd(), 'allma_memory.json')
            if not os.path.exists(file_path):
                print("No memory file found. Starting fresh.")
                return

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Restore Conversations
            self.conversations = defaultdict(list)
            for uid, convs_data in data.get("conversations", {}).items():
                for c_data in convs_data:
                    c = Conversation(
                        id=c_data["id"],
                        user_id=c_data["user_id"],
                        timestamp=datetime.fromisoformat(c_data["timestamp"]),
                        content=c_data["content"],
                        metadata=c_data["metadata"]
                    )
                    # Re-calculate embedding on load if needed, or skip for speed
                    self.conversations[uid].append(c)

            # Restore Messages
            self.messages = []
            for m_data in data.get("messages", []):
                m = Message(
                    conversation_id=m_data["conversation_id"],
                    role=m_data["role"],
                    content=m_data["content"],
                    timestamp=datetime.fromisoformat(m_data["timestamp"]),
                    metadata=m_data["metadata"]
                )
                if "user_id" in m_data:
                    m.user_id = m_data["user_id"]
                self.messages.append(m)

            # Restore User Data
            self.user_data = data.get("user_data", {})
            print(f"📂 MEMORY LOADED: {len(self.messages)} messages restored.")

        except Exception as e:
            print(f"❌ MEMORY LOAD FAILED: {e}")
