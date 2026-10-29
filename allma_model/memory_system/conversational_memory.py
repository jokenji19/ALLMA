"""ConversationalMemory - Sistema di memoria conversazionale per ALLMA."""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import json
import os
import hashlib
from allma_model.utils.persistence import atomic_write_json
from allma_model.core.autobiographical_identity import delivery_visible
from .history_changes import PersistedRow, HistoryChanges
import re
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict, is_dataclass
from enum import Enum
import numpy as np
from allma_model.utils.text_processing import SimpleTfidf, cosine_similarity
# V6 Sprint 3: Vector Engine
try:
    from allma_model.core.vector_memory_engine import VectorMemoryEngine
    _VECTOR_ENGINE_AVAILABLE = True
except ImportError:
    _VECTOR_ENGINE_AVAILABLE = False
    import logging
    logging.getLogger(__name__).warning("[V6.3] VectorMemoryEngine non disponibile, fallback a TF-IDF classico.")



@dataclass
class Conversation(PersistedRow):
    """Classe per rappresentare una conversazione."""
    id: str
    user_id: str
    timestamp: datetime
    content: str
    metadata: Dict
    embeddings: Optional[np.ndarray] = None

@dataclass
class Message(PersistedRow):
    """Classe per rappresentare un messaggio."""
    conversation_id: str
    role: str  # "user" o "assistant"
    content: str
    timestamp: datetime
    metadata: Dict
    user_id: Optional[str] = None

class ConversationalMemory:
    """Sistema di memoria conversazionale."""
    
    def __setattr__(self, name, value):
        changes = self.__dict__.get('_changes')
        if changes is not None and name in ('messages', 'conversations', 'user_data', 'trauma_log'):
            with self.lock:
                value = changes.replace(name, value, self.__dict__.get(name))
                object.__setattr__(self, name, value)
        else:
            object.__setattr__(self, name, value)

    def __init__(self, load_persistent: bool = True, storage_dir: Optional[str] = None,
                 *, incremental: bool = False):
        """Inizializza il sistema di memoria conversazionale."""
        self.storage_dir = os.path.abspath(storage_dir or os.getcwd())
        self.memory_path = os.path.join(self.storage_dir, "allma_memory.json")
        self._changes = None
        self._history_store = None
        archive = os.path.join(self.storage_dir, 'conversation_history.db')
        # Once migrated, even legacy callers must read the authoritative DB.
        if incremental or os.path.exists(archive) or os.path.exists(archive+'.init.lock'):
            from .history_store import HistoryStore
            self._history_store = HistoryStore(archive, self.memory_path)
            self.memory_path = archive
        self.user_data = {}
        self.conversations: Dict[str, List[Conversation]] = defaultdict(list)
        self.vectorizer = SimpleTfidf()
        self.conversation_vectors = {}
        self.messages: List[Message] = []
        self._load_error = None
        self._projection_stale = False
        self.trauma_log: List[Dict] = [] # AXIOM 3: Sedimentation
        
        # Concurrency safety
        import threading
        self.lock = threading.RLock()
        
        # V6 Sprint 3: Vector Engine (SQLite-backed)
        if _VECTOR_ENGINE_AVAILABLE:
            try:
                self.vector_engine = VectorMemoryEngine(
                    db_path=os.path.join(self.storage_dir, "data", "allma_vectors.db"), defer_index=True)
                import logging
                logging.getLogger(__name__).info(
                    f"[V6.3] VectorMemoryEngine attivo: {self.vector_engine.count()} memorie in DB."
                )
            except Exception as e:
                self.vector_engine = None
                import logging
                logging.getLogger(__name__).warning(f"[V6.3] VectorMemoryEngine init failed: {e}")
        else:
            self.vector_engine = None
        
        if load_persistent or self._history_store is not None:
            self.load_memory()
            if self._history_store is None:self._index_messages()
        
    def _index_messages(self, messages=None, *, touched=None):
        if self.vector_engine is None:
            return
        if self._history_store is not None:
            if any(self._changes.dirty.values()) or any(self._changes.deleted.values()):
                from allma_model.utils.persistence import StateRecoveryRequired
                raise StateRecoveryRequired('Save pending history edits before rebuilding its projection')
            if messages is None or self._projection_stale:
                self.vector_engine.sync_history(self._message_index_rows(self.messages),default=self._json_serial,
                    guard=self._history_store.check_current_generation)
            else:
                messages=list(messages)
                touched=touched if touched is not None else {row._archive_key for row in messages}
                self.vector_engine.sync_history(self._message_index_rows(messages),touched,default=self._json_serial,
                    guard=self._history_store.check_current_generation)
            self._projection_stale=False
            return
        if messages is None:
            self.vector_engine.add_many(self._message_index_rows(self.messages))
            return
        for record in self._message_index_rows(messages):
            self.vector_engine.add(**record)

    def _message_index_rows(self, messages, *, resolve_legacy=True):
        owners=None
        for message in messages:
            if (not message.content.strip() or message.metadata.get('is_valid') is False
                    or not delivery_visible(message.metadata)):
                continue
            uid = message.user_id or message.metadata.get('user_id')
            if not uid and resolve_legacy:
                if owners is None:
                    owners={}
                    for user,conversations in self.conversations.items():
                        for conversation in conversations:
                            # A conflicting legacy identifier has no safe owner.
                            prior=owners.setdefault(conversation.id,user)
                            if prior!=user:owners[conversation.id]=None
                uid=owners.get(message.conversation_id)
                if not uid and self._history_store is not None:
                    uid=self._history_store.conversation_owner(message.conversation_id)
            if not isinstance(uid,str) or not uid:
                continue  # Never guess the owner of legacy records.
            if self._history_store is not None:
                from allma_model.core.history_projection import source_key
                token=getattr(message,'_archive_key',None)
                if not token:continue
                key=source_key(token)
            else:
                key = hashlib.sha256(json.dumps([message.conversation_id, message.role,
                    message.timestamp.isoformat(), message.content], ensure_ascii=False).encode()).hexdigest()
            yield {'user_id':uid,'content':message.content,'metadata':{**message.metadata,
                   'role':message.role,'conversation_id':message.conversation_id,'user_id':uid},
                   'timestamp':message.timestamp,'source_key':key}

    def search_user_reports(self,user_id,message,top_k=3):
        """Search once; only current, attributed history can become evidence."""
        with self.lock:
            if self._history_store is None:
                return self.vector_engine.search(user_id=user_id,query=message,top_k=top_k,
                    use_expansion=True,allowed_roles=('user',),exclude_query_replays=True)
            if self._load_error is not None or self._history_store.read_error is not None:
                from allma_model.utils.persistence import StateRecoveryRequired
                raise StateRecoveryRequired('History must be recovered before searching user reports')
            if self._projection_stale:self._index_messages()
            with self._history_store.connect(readonly=True) as db:
                db.execute('BEGIN');self._history_store._check_generation(db)
                raw=self.vector_engine.search(user_id=user_id,query=message,top_k=top_k,
                    use_expansion=True,allowed_roles=('user',),exclude_query_replays=True)
                verified=self._history_store.verified_sources(db,raw,user_id)
                if len(verified)!=len(raw):self._projection_stale=True
                return verified

    def add_trauma_event(self, description: str, context: Dict = None) -> None:
        """
        Axiom 3: Sedimentation.
        Adds a scar (Trauma Event) to the memory.
        """
        if context is None: context = {}
        event = {
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "context": context,
            "severity": context.get("severity", 0.5)
        }
        with self.lock:
            self.trauma_log.append(event)
            # Keep log manageable (Scars accumulate)
            if len(self.trauma_log) > 1000:
                self.trauma_log.pop(0) 
        
        print(f"🩹 TRAUMA ADDED: {description}")
        self.save_memory() # Commit scar immediately

    def get_relevant_traumas(self, query: str = "") -> List[Dict]:
        """
        Retrieves traumas relevant to the current context.
        """
        # Return mostly recent ones or high severity ones.
        return sorted(self.trauma_log, key=lambda x: x.get('severity', 0.5), reverse=True)[:5]
        
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
            
        if metadata is None:
            metadata = {}
            
        with self.lock:
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
        
        # Calcola embedding (fallback TF-IDF classico)
        try:
            vectors = self.vectorizer.fit_transform([content])
            if hasattr(vectors, "toarray"):
                conversation.embeddings = vectors.toarray()[0]
            else:
                conversation.embeddings = vectors[0]
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
        
        # V6 Sprint 3: aggiungi anche al VectorEngine
        if self.vector_engine is not None and self._history_store is None:
            try:
                self.vector_engine.add(
                    user_id=user_id,
                    content=content,
                    metadata=metadata,
                    timestamp=conversation.timestamp,
                )
            except Exception as ve:
                import logging
                logging.getLogger(__name__).warning(f"[V6.3] VectorEngine.add failed: {ve}")
        
        # Aggiorna vettori conversazione (legato a TF-IDF classico)
        if conversation.embeddings is not None:
            self.conversation_vectors[conversation_id] = conversation.embeddings
            
        return conversation_id
        
    def retrieve_relevant_context(
        self,
        current_topic: str,
        user_id: Optional[str] = None,
        max_results: int = 5,
        exclude_query_replays: bool = False
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
        if user_id and hasattr(self, 'user_data') and user_id in self.user_data:
            user_facts = self.user_data[user_id]
            for key, value in user_facts.items():
                if key in current_topic.lower() or value in current_topic.lower():
                    fact_conv = Conversation(
                        id=f"fact_{key}",
                        user_id=user_id,
                        timestamp=datetime.now(),
                        content=f"FACT: Il tuo {key} è {value}.",
                        metadata={'type': 'fact'}
                    )
                    results.append((1.0, fact_conv))

        if not current_topic.strip():
            return results

        # 2. V6 Sprint 3: Vector Engine fast-path (SQLite-backed)
        if self.vector_engine is not None:
            try:
                hits = self.vector_engine.search(
                    user_id=user_id or "user_default",
                    query=current_topic,
                    top_k=max_results,
                    exclude_query_replays=exclude_query_replays,
                )
                for hit in hits:
                    synth = Conversation(
                        id=f"vec_{hit['id']}",
                        user_id=user_id or "user_default",
                        timestamp=datetime.fromisoformat(hit['timestamp']) if hit.get('timestamp') else datetime.now(),
                        content=hit['content'],
                        metadata=hit.get('metadata', {}),
                    )
                    results.append((hit['score'], synth))
                if results:
                    results.sort(key=lambda x: x[0], reverse=True)
                    return results[:max_results]
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"[V6.3] VectorEngine.search failed, fallback TF-IDF: {e}")

        # 3. Fallback: TF-IDF classico O(n)
        conversations = (
            self.conversations[user_id] if user_id
            else [c for convs in self.conversations.values() for c in convs]
        )
        
        if conversations and (
            not self.vectorizer.vocab
            or any(c.embeddings is None for c in conversations)
            or any(len(c.embeddings) != len(self.vectorizer.vocab) for c in conversations if c.embeddings is not None)
        ):
            contents = [c.content for c in conversations]
            vectors = self.vectorizer.fit_transform(contents)
            if hasattr(vectors, "toarray"):
                vectors = vectors.toarray()
            for conv, vec in zip(conversations, vectors):
                conv.embeddings = vec
                self.conversation_vectors[conv.id] = vec

        try:
            topic_vectors = self.vectorizer.transform([current_topic])
            if hasattr(topic_vectors, "toarray"):
                topic_vector = topic_vectors.toarray()[0]
            else:
                topic_vector = topic_vectors[0]
        except Exception as e:
            print(f"Errore nel calcolo embedding topic: {e}")
            return results
        
        # Calcola similarità con ogni conversazione
        for conv in conversations:
            if conv.embeddings is not None:
                similarity = cosine_similarity(
                    [topic_vector],
                    [conv.embeddings]
                )[0][0]
                results.append((similarity, conv))
                
        topic_tokens = set(current_topic.lower().split())
        if results:
            def score_pair(item):
                sim, conv = item
                content_tokens = set(conv.content.lower().split()) if isinstance(conv.content, str) else set()
                bonus = 0.5 if topic_tokens & content_tokens else 0.0
                return sim + bonus
            results.sort(reverse=True, key=score_pair)
            if exclude_query_replays:
                from allma_model.utils.memory_evidence import is_replayed_question
                filtered = []
                for item in results:
                    text = item[1].content
                    if item[1].metadata.get('role') != 'user' or item[1].metadata.get('is_valid') is False:
                        continue
                    if item[1].metadata.get('revoked') is True or item[1].metadata.get('status') in ('revoked','superseded'):
                        continue
                    if is_replayed_question(text, current_topic):
                        continue
                    filtered.append(item)
                results = filtered
            return results[:max_results]

        for conv in conversations:
            content_tokens = set(conv.content.lower().split()) if isinstance(conv.content, str) else set()
            overlap = len(topic_tokens & content_tokens)
            if overlap:
                results.append((overlap / max(len(topic_tokens), 1), conv))

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
        if limit is not None and (type(limit) is not int or limit < 0):
            raise ValueError('Il limite deve essere un intero non negativo')
            
        with self.lock:
            selected=(msg for msg in self.messages
                if msg.conversation_id==conversation_id and delivery_visible(msg.metadata)
                and (start_time is None or msg.timestamp>=start_time)
                and (end_time is None or msg.timestamp<=end_time))
            if limit is None:return sorted(selected,key=lambda msg:msg.timestamp)
            if limit==0:return []
            # Preserve exact timestamp/tie ordering while retaining at most the
            # requested window, even when the device clock moved backwards.
            from heapq import nlargest
            newest=nlargest(limit,enumerate(selected),key=lambda item:(item[1].timestamp,item[0]))
            newest.sort(key=lambda item:(item[1].timestamp,item[0]))
            return [row for _,row in newest]

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

        if not common_topics:
            tokens = []
            for text in all_content:
                if isinstance(text, str):
                    tokens.extend([t for t in re.findall(r'\b\w+\b', text.lower()) if len(t) > 2])
            if tokens:
                common_topics = [w for w, _ in Counter(tokens).most_common(10)]
            
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
            
        if user_id not in self.conversations:
            return 0
            
        with self.lock:
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

    def condense_and_clear_old(
        self,
        user_id: str,
        before_date: datetime,
        llm_callback: callable,
        cancel_event=None
    ) -> int:
        """
        Estrae citazioni dell'utente dalle vecchie conversazioni, conservando
        integralmente la cronologia. Restituisce il numero di record rimossi (zero).
        """
        if user_id not in self.conversations:
            return 0
        from allma_model.utils.generation_control import check_cancelled, GenerationCancelled
        check_cancelled(cancel_event)
            
        with self.lock:
            old_messages = [
                m for m in self.messages
                if m.user_id == user_id and m.timestamp < before_date and m.role == 'user'
            ]
        
        if not old_messages:
            return 0
            
        # Preparazione del testo per l'estrazione
        text_to_compress = "\n".join([f"{m.role}: {m.content}" for m in old_messages[-40:]])
        
        prompt = (
            f"Sei un estrattore di memorie a lungo termine. Analizza la seguente cronologia passata e "
            f"estrai un massimo di 5 Fatti Cognitivi su questo utente. "
            f"I fatti devono essere chiavi corte (es. 'hobby', 'lavoro', 'film_preferito', 'relazione') "
            f"e valori sintetici. Rispondi SOLO con un JSON valido in questo formato: "
            f"{{\"hobby\": \"fotografia\", \"colore\": \"rosso\"}}\n"
            f"---\n{text_to_compress[:8000]}\n---"
        )
        
        try:
            extracted_json_str = llm_callback(prompt)
            check_cancelled(cancel_event)
            # Pulizia JSON
            import re
            json_str = re.sub(r'```json\n|\n```|```', '', extracted_json_str).strip()
            extracted_facts = json.loads(json_str)
            if not isinstance(extracted_facts, dict):
                return 0
            # Extraction is not verification: retain only verbatim user evidence.
            normalized_source = ' '.join(text_to_compress[:8000].casefold().split())
            extracted_facts = {k: v for k, v in extracted_facts.items()
                               if isinstance(k, str) and isinstance(v, str) and v.strip()
                               and ' '.join(v.casefold().split()) in normalized_source}

            staged_facts = {}
            for k, v in extracted_facts.items():
                if isinstance(v, str):
                    clean_k = re.sub(r'[^a-zA-Z0-9_]', '_', k.lower())[:30] # safe key
                    if clean_k:
                        staged_facts[clean_k] = v[:100]
                    
        except GenerationCancelled:
            raise
        except Exception as e:
            import logging
            logging.error(f"[ConversationalMemory] GC Condensation failed: {e}", exc_info=True)
            return 0  # Keep original records when extraction fails.

        if not extracted_facts or not any(isinstance(v, str) and v.strip() for v in extracted_facts.values()):
            return 0
        with self.lock:
            check_cancelled(cancel_event)
            # Never overwrite a more recent explicitly learned fact with an old quote.
            target = self.user_data.setdefault(user_id, {})
            for key, value in staged_facts.items():
                target.setdefault(key, value)
        # A lossy summary must not erase autobiographical evidence.
        self.save_memory()
        return 0

    def store_message(
        self,
        conversation_id: str,
        content: str,
        metadata: Optional[Dict] = None,
        role: str = "assistant",
        user_id: Optional[str] = None
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
            
        with self.lock:
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                timestamp=datetime.now(),
                metadata=metadata,
                user_id=user_id
            )
            self.messages.append(message)
            try:
                self.save_memory()
            except Exception:
                # Readers share this lock: a failed transaction never becomes
                # part of the live history or of a later successful save.
                self.messages.pop()
                raise
            if self._history_store is None:self._index_messages([message])

    def save_interaction(self, user_id: str, message: str, role: str):
        """Salva una interazione nella memoria."""
        if user_id not in self.conversations:
            self.conversations[user_id] = []
            
        if user_id not in self.conversations:
            self.conversations[user_id] = []
            
        with self.lock:
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

    def message_count(self,user_id,role=None):
        with self.lock:
            if getattr(self,'_history_store',None) is not None:
                if role is not None:return self._message_counts.get((user_id,role),0)
                return sum(count for (owner,_),count in self._message_counts.items() if owner==user_id)
            return sum((row.user_id or row.metadata.get('user_id'))==user_id and (role is None or row.role==role)
                       for row in self.messages)

    def recent_messages(self,limit=10,*,predicate=None):
        """Latest matching rows, ordered chronologically, with bounded retention."""
        from .paged_history import recent_rows
        with self.lock:return recent_rows(self.messages,limit,predicate=predicate)

    def get_recent_history(self,limit=10,user_id=None):
        owned=None
        def matches(row):
            nonlocal owned
            if user_id is None or row.user_id==user_id:return True
            if row.user_id is not None:return False
            if owned is None:owned={c.id for c in self.conversations.get(user_id,[])}
            return row.conversation_id in owned
        return [{'role':row.role,'content':row.content}
                for row in self.recent_messages(limit,predicate=matches)]

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

    def update_context(self, conversation_id: str, context: Dict[str, Any]) -> None:
        if not conversation_id:
            raise ValueError("Conversation ID è richiesto")
        if context is None:
            return

        with self.lock:
            for uid, convs in self.conversations.items():
                for c in convs:
                    if c.id == conversation_id:
                        if not isinstance(context, dict):
                            raise TypeError("Context must be a dictionary")
                        previous = c.metadata
                        c.metadata = {**(previous or {}), **context}
                        try:
                            self.save_memory()
                        except Exception:
                            c.metadata = previous
                            raise
                        return

    def store_insight(self, content: str, origin_topics: List[str]) -> None:
        """
        [DREAM SYSTEM] Memorizza un insight generato durante il sogno.
        """
        # Creiamo un 'fatto' sintetico che rappresenta l'insight
        user_id = "allma_dream" # Internal ID for dreams
        
        # Salviamo come una conversazione speciale
        conv = Conversation(
            id=f"insight_{datetime.now().timestamp()}",
            user_id=user_id,
            timestamp=datetime.now(),
            content=f"INSIGHT: {content}",
            metadata={
                "type": "dream_insight",
                "origin_topics": origin_topics,
                "confidence": 1.0
            }
        )
        # Calcolo embedding per renderlo ricercabile
        try:
            vectors = self.vectorizer.fit_transform([content])
            conv.embeddings = vectors.toarray()[0]
        except Exception as e:
            import logging
            logging.error(f"[ConversationalMemory] Error calculating embedding for insight: {e}", exc_info=True)
            
        # Aggiungi alla memoria generale (usiamo 'user' principale se disponibile, altrimenti system)
        target_uid = list(self.conversations.keys())[0] if self.conversations else "user"
        self.conversations[target_uid].append(conv)
        
        # FIX PHASE 20: Ensure it exists in Message History for retrieval
        self.store_message(
            conversation_id=conv.id,
            content=conv.content, # "INSIGHT: ..."
            role="system",
            metadata=conv.metadata,
            user_id=target_uid
        )
        
        self.save_memory()
        print(f"🌙 DREAM: Insight stored: '{content[:50]}...'")

    def get_random_topics(self, limit: int = 2) -> List[str]:
        """
        [DREAM SYSTEM] Recupera topic casuali dalle conversazioni recenti.
        """
        import random
        candidates = []
        
        # Raccogli tutti i contenuti recenti
        for uid, convs in self.conversations.items():
            for c in convs[-20:]: # Ultimi 20 scambi
                # Estrai parole chiave grezze (molto semplice per ora)
                # In futuro usare il CognitiveTracker per topic veri
                words = [w for w in c.content.split() if len(w) > 5]
                candidates.extend(words)
                
        if not candidates:
            return ["Vita", "Universo"] # Fallback filosofico
            
        # Rimuovi duplicati e scegli a caso
        candidates = list(set(candidates))
        if len(candidates) < limit:
            return candidates
            
        return random.sample(candidates, limit)

    def _json_serial(self, obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.generic):
            return obj.item()
        raise TypeError (f"Type {type(obj)} not serializable")

    def save_memory(self):
        """Serialize and replace while holding the same lock as mutations."""
        with self.lock:
            if self._load_error is not None:
                raise RuntimeError('Memory archive could not be loaded; preserving original file') from self._load_error
            if self._history_store is not None:
                highest=getattr(self,'_history_highwater',0)
                for row in self._changes.dirty['messages'].values():
                    for key in ('experience_update','delivery_update'):
                        intent=row.metadata.get(key)
                        if isinstance(intent,dict) and type(intent.get('sequence')) is int:
                            highest=max(highest,intent['sequence'])
                from collections import Counter
                count_delta=Counter()
                dirty=list(self._changes.dirty['messages'].values())
                touched=set(self._changes.dirty['messages'])|self._changes.deleted['messages']
                legacy_owners_changed=(bool(self._changes.dirty['conversations'] or self._changes.deleted['conversations']
                                           or 'conversation_users' in self._changes.sections)
                                       and any(owner is None and count for (owner,_),count in self._message_counts.items()))
                for row in dirty:
                    old=row.__dict__.get('_archive_count_key')
                    if row.__dict__.get('_archive_persisted',False) and old is not None:count_delta[old]-=1
                    uid=row.user_id or row.metadata.get('user_id')
                    count_delta[(uid if isinstance(uid,str) else None,row.role)]+=1
                for old in self._changes.deleted_counts.values():
                    if old is not None:count_delta[old]-=1
                self._history_store.commit(self._changes, self._json_serial)
                for key,delta in count_delta.items():self._message_counts[key]=self._message_counts.get(key,0)+delta
                for row in dirty:
                    uid=row.user_id or row.metadata.get('user_id')
                    row._archive_count_key=(uid if isinstance(uid,str) else None,row.role)
                self._history_highwater=highest
                if self.vector_engine is not None and (touched or legacy_owners_changed or self._projection_stale):
                    try:
                        # Recover a previously deferred batch in full. This flag
                        # must not force a full scan on every ordinary insertion.
                        if legacy_owners_changed:self._projection_stale=True
                        self._index_messages(dirty,touched=touched)
                    except Exception as error:
                        self._projection_stale=True
                        import logging
                        logging.getLogger(__name__).warning('History saved; search projection deferred: %s',type(error).__name__)
                return
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
                "user_data": self.user_data,
                "trauma_log": self.trauma_log  # AXIOM 3: Persist Scars
            }
            atomic_write_json(self.memory_path, data, default=self._json_serial)

    def load_memory(self):
        """Validate a complete snapshot before swapping any live collection.

        A failed load disables writes until a successful explicit reload, so
        startup with a damaged archive cannot overwrite its recoverable data.
        """
        with self.lock:
            if self._history_store is not None:
                try:
                    from .paged_history import PagedRows
                    from .history_changes import ConversationGroups
                    def ingest(records):
                        from types import SimpleNamespace
                        def messages():
                            for kind,token,position,row,owner in records:
                                if kind=='messages':
                                    data=dict(row);data.setdefault('metadata',{});data.setdefault('user_id',None)
                                    data['timestamp']=datetime.fromisoformat(data['timestamp'])
                                    if not data['user_id']:data['user_id']=data['metadata'].get('user_id') or owner
                                    data['_archive_key']=token
                                    yield SimpleNamespace(**data)
                        self.vector_engine.sync_history(self._message_index_rows(messages(),resolve_legacy=False),default=self._json_serial)
                    plan=self._history_store.load_pages(ingest if self.vector_engine is not None else None)
                    changes=HistoryChanges(self)
                    messages=PagedRows(self._history_store,changes,'messages',Message,
                        count=plan['counts'].get(('messages',None),0),last=plan['last'].get(('messages',None),-1))
                    messages.preload(plan['recent'])
                    groups=ConversationGroups({owner:PagedRows(self._history_store,changes,'conversations',Conversation,owner,
                        count=plan['counts'].get(('conversations',owner),0),last=plan['last'].get(('conversations',owner),-1))
                        for owner in plan['state']['conversation_users']},changes)
                    candidate={'messages':messages,'conversations':groups,
                        'user_data':changes.replace('user_data',plan['state']['user_data']),
                        'trauma_log':changes.replace('trauma_log',plan['state']['trauma_log'])}
                    changes.committed();changes.loading=False
                    for name,value in candidate.items():object.__setattr__(self,name,value)
                    self._changes=changes
                    self.__dict__.pop('_activity_snapshots',None)
                    self._history_highwater=plan['highwater']
                    self._message_counts=plan['message_counts']
                    self._projection_stale=bool(plan.get('index_deferred'))
                    self.conversation_vectors = {}
                    self._load_error = None
                    return True
                except Exception as error:
                    self._load_error = error
                    import logging
                    logging.getLogger(__name__).error('History load failed; original archive protected: %s', error)
                    return False
            if not os.path.exists(self.memory_path):
                return False
            try:
                with open(self.memory_path, 'r', encoding='utf-8') as stream:
                    data = json.load(stream)
                if not isinstance(data, dict):
                    raise ValueError('Memory root must be an object')
                raw_conversations = data.get('conversations', {})
                raw_messages = data.get('messages', [])
                users = data.get('user_data', {})
                traumas = data.get('trauma_log', [])
                if (not isinstance(raw_conversations, dict) or not isinstance(raw_messages, list)
                        or not isinstance(users, dict) or not isinstance(traumas, list)):
                    raise ValueError('Invalid memory collection types')
                conversations = defaultdict(list)
                messages = []
                for uid, rows in raw_conversations.items():
                    if not isinstance(rows, list):
                        raise ValueError('Invalid conversation list')
                    for row in rows:
                        if not isinstance(row['content'], str) or not isinstance(row['metadata'], dict):
                            raise ValueError('Invalid conversation record')
                        conversations[uid].append(Conversation(
                            id=row['id'], user_id=row['user_id'],
                            timestamp=datetime.fromisoformat(row['timestamp']),
                            content=row['content'], metadata=row['metadata']))
                for row in raw_messages:
                    if (not isinstance(row['content'], str) or not isinstance(row['metadata'], dict)
                            or not isinstance(row['conversation_id'], str)
                            or not isinstance(row['role'], str)):
                        raise ValueError('Invalid message record')
                    messages.append(Message(conversation_id=row['conversation_id'],
                        role=row['role'], content=row['content'],
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        metadata=row['metadata'], user_id=row.get('user_id')))
                self.conversations, self.messages = conversations, messages
                self.__dict__.pop('_activity_snapshots',None)
                self.user_data, self.trauma_log = users, traumas
                self.conversation_vectors = {}
                self._load_error = None
                return True
            except Exception as error:
                self._load_error = error
                import logging
                logging.getLogger(__name__).error('Memory load failed; original archive protected: %s', error)
                return False
