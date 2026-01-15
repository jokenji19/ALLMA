"""
Modulo per la gestione della memoria delle conoscenze di ALLMA
"""
from typing import Dict, List, Optional, Set, Any
import time
import json
from dataclasses import dataclass, field
from enum import Enum, auto
from .learning_feedback import LearningManager, Feedback
import logging
import re

class FeedbackType(str, Enum):
    """Tipi di feedback per l'apprendimento"""
    CREATE = 'create'        # Creazione di un nuovo concetto
    UPDATE = 'update'        # Aggiornamento di un concetto esistente
    VALIDATION = 'validate'  # Verifica positiva di un concetto
    ERROR = 'error'         # Errore o verifica negativa
    EXPANSION = 'expand'    # Espansione della conoscenza
    REINFORCEMENT = 'reinforce' # Rinforzo della conoscenza esistente
    CORRECTION = 'correct'   # Correzione di un concetto errato
    CONFUSION = 'confuse'   # Confusione nell'applicazione del concetto
    EXPANSION_REQUEST = 'request_expansion'  # Richiesta di espansione della conoscenza

@dataclass
class KnowledgeNode:
    """Rappresenta un nodo di conoscenza nella memoria di ALLMA"""
    concept: str
    description: str
    timestamp: float
    source: str  # utente che ha insegnato il concetto
    confidence: float = 0.0  # livello di confidenza sulla comprensione
    related_concepts: Set[str] = field(default_factory=set)
    examples: List[str] = field(default_factory=list)
    applications: List[str] = field(default_factory=list)
    verification_count: int = 0  # numero di volte che il concetto è stato verificato
    feedback_history: List[Dict] = field(default_factory=list)  # storia del feedback
    feedbacks: List[Feedback] = field(default_factory=list)  # storia dei feedback
    
class KnowledgeMemory:
    """Gestisce la memoria delle conoscenze di ALLMA"""
    
    def __init__(self, nlp=None):
        """Inizializza la memoria della conoscenza"""
        self.knowledge_base = {}  # Dict[str, KnowledgeNode]
        self.learning_history = []
        self.concept_relationships = {}  # grafo delle relazioni tra concetti
        self.learning_manager = LearningManager()
        self.nlp = nlp  # Processore NLP
        self.max_entries = 1000  # Numero massimo di entry nella base di conoscenza
        
        # Inizializza con conoscenza di base
        self._initialize_base_knowledge()
        
        # Dizionario per cache delle ricerche Wikipedia
        self.wiki_cache = {}
        
    def _initialize_base_knowledge(self):
        """Inizializza la knowledge base con conoscenza fondamentale"""
        base_knowledge = {
            'machine_learning': {
                'description': """Il machine learning è una tecnologia che permette ai computer di imparare dai dati.
                Utilizza algoritmi per identificare pattern e fare previsioni.""",
                'confidence': 0.9,
                'verification_count': 5
            },
            'deep_learning': {
                'description': """Il deep learning è una branca del machine learning che utilizza reti neurali profonde.
                È particolarmente efficace per compiti come il riconoscimento di immagini e l'elaborazione del linguaggio naturale.""",
                'confidence': 0.9,
                'verification_count': 5
            },
            'neural_networks': {
                'description': """Le reti neurali sono modelli computazionali ispirati al cervello umano.
                Sono composte da nodi (neuroni) interconnessi che elaborano e trasmettono informazioni.""",
                'confidence': 0.9,
                'verification_count': 5
            },
            'artificial_intelligence': {
                'description': """L'intelligenza artificiale è la capacità di un sistema di simulare l'intelligenza umana.
                Include varie tecnologie come machine learning, deep learning e sistemi esperti.""",
                'confidence': 0.9,
                'verification_count': 5
            }
        }
        
        # Aggiungi la conoscenza base
        for topic, info in base_knowledge.items():
            self.knowledge_base[topic] = KnowledgeNode(
                concept=topic,
                description=info['description'],
                timestamp=time.time(),
                source="initial_knowledge",
                confidence=info['confidence']
            )
            self.knowledge_base[topic].verification_count = info['verification_count']
            
    def learn_concept(self, concept: str, description: str = None,
                     examples: List[str] = None, related_concepts: List[str] = None,
                     source: str = None) -> None:
        """Impara o aggiorna un concetto"""
        if not concept:
            return
            
        current_time = time.time()
        
        # Se il concetto esiste già, aggiornalo
        if concept in self.knowledge_base:
            node = self.knowledge_base[concept]
            
            # Calcola la similarità tra la vecchia e la nuova descrizione
            similarity = 0.0
            if description and node.description:
                similarity = self.nlp.compute_similarity(description, node.description)
            
            # Aggiorna la confidenza in base alla similarità
            confidence_impact = 0.0
            if similarity > 0.8:  # Descrizioni molto simili
                confidence_impact = 0.1  # Piccolo boost di confidenza
            elif similarity > 0.5:  # Descrizioni moderatamente simili
                confidence_impact = 0.05  # Boost minimo
            else:  # Descrizioni diverse
                confidence_impact = -0.1  # Penalità per informazioni contrastanti
            
            # Aggiorna la descrizione se la nuova è più dettagliata
            if description and (not node.description or 
                             len(description) > len(node.description)):
                node.description = description
            
            # Aggiorna gli esempi
            if examples:
                for example in examples:
                    if example not in node.examples:
                        node.examples.append(example)
                        confidence_impact += 0.05  # Bonus per nuovi esempi
            
            # Aggiorna i concetti correlati
            if related_concepts:
                for related in related_concepts:
                    if related not in node.related_concepts:
                        node.related_concepts.add(related)
                        confidence_impact += 0.02  # Bonus per nuove relazioni
            
            # Aggiorna il timestamp
            node.timestamp = current_time
            
            # Crea un feedback per l'aggiornamento
            feedback = Feedback(
                type=FeedbackType.UPDATE,
                content="Concetto aggiornato",
                source=source or "system",
                timestamp=current_time,
                context={
                    'similarity': similarity,
                    'description_updated': bool(description),
                    'examples_added': len(examples) if examples else 0,
                    'relations_added': len(related_concepts) if related_concepts else 0
                },
                confidence_impact=confidence_impact
            )
            
            self._process_feedback(concept, feedback)
            
        else:
            # Crea un nuovo nodo per il concetto
            node = KnowledgeNode(
                concept=concept,
                description=description or "",
                timestamp=current_time,
                source=source or "system",
                confidence=0.3,  # Confidenza iniziale moderata
                related_concepts=set(related_concepts or []),
                examples=examples or [],
                verification_count=0,
                feedback_history=[]
            )
            
            self.knowledge_base[concept] = node
            
            # Crea un feedback per la creazione
            feedback = Feedback(
                type=FeedbackType.CREATE,
                content="Nuovo concetto creato",
                source=source or "system",
                timestamp=current_time,
                context={
                    'has_description': bool(description),
                    'examples_count': len(examples) if examples else 0,
                    'relations_count': len(related_concepts) if related_concepts else 0
                },
                confidence_impact=0.3  # Impatto iniziale moderato
            )
            
            self._process_feedback(concept, feedback)
        
    def verify_concept(self, concept: str, success: bool) -> None:
        """Verifica l'apprendimento di un concetto"""
        if concept not in self.knowledge_base:
            return
            
        node = self.knowledge_base[concept]
        node.verification_count += 1
        
        # Calcola l'impatto sulla confidenza in base al contesto
        base_impact = 0.15 if success else -0.2
        
        # Modifica l'impatto in base al numero di verifiche
        if success:
            # Successo dopo molti tentativi ha un impatto maggiore
            base_impact *= (1.0 + min(0.5, node.verification_count * 0.1))
            
            # Se è il primo successo, dai un bonus extra
            if node.verification_count == 1:
                base_impact *= 1.2
        else:
            # Fallimenti ripetuti hanno un impatto crescente
            base_impact *= (1.0 + min(0.3, node.verification_count * 0.05))
        
        # Considera la confidenza attuale
        if success:
            # Successi con alta confidenza hanno meno impatto
            if node.confidence > 0.7:
                base_impact *= 0.7
        else:
            # Fallimenti con bassa confidenza hanno meno impatto
            if node.confidence < 0.3:
                base_impact *= 0.7
        
        # Crea un feedback basato sul risultato della verifica
        feedback = Feedback(
            type=FeedbackType.VALIDATION if success else FeedbackType.ERROR,
            content="Verifica superata con successo" if success else "Verifica fallita",
            source="system",
            timestamp=time.time(),
            context={
                'type': 'verification',
                'attempt': node.verification_count,
                'verification_success': success,
                'previous_confidence': node.confidence
            },
            confidence_impact=base_impact
        )
        
        self._process_feedback(concept, feedback)
        
    def add_feedback(self, concept: str, feedback_type: FeedbackType, 
                    content: str, source: str, context: Dict = None) -> None:
        """Aggiunge feedback esplicito per un concetto"""
        if concept not in self.knowledge_base:
            return
            
        if context is None:
            context = {}
            
        # Mappa il tipo di feedback all'impatto sulla confidenza
        impact_map = {
            FeedbackType.CORRECTION.value: -0.4,    # Impatto negativo significativo
            FeedbackType.EXPANSION.value: 0.4,      # Impatto positivo significativo
            FeedbackType.VALIDATION.value: 0.3,     # Impatto positivo moderato
            FeedbackType.CONFUSION.value: -0.2,     # Impatto negativo moderato
            FeedbackType.ERROR.value: -0.35,        # Impatto negativo significativo
            FeedbackType.EXPANSION_REQUEST.value: 0.0  # Nessun impatto sulla confidenza
        }
        
        feedback = Feedback(
            type=feedback_type,
            content=content,
            source=source,
            timestamp=time.time(),
            context=context,
            confidence_impact=impact_map[feedback_type.value]
        )
        
        self._process_feedback(concept, feedback)
        
    def _process_feedback(self, concept: str, feedback: Feedback) -> None:
        """Processa il feedback e aggiorna la memoria"""
        if not feedback:
            return
            
        # Estrai concetti e confidenza dal feedback
        concept_name = concept.lower().replace(' ', '_')
        confidence = feedback.confidence_impact
        
        # Ottieni o crea il concetto
        if concept_name not in self.knowledge_base:
            self.knowledge_base[concept_name] = KnowledgeNode(
                concept=concept,
                description="",
                timestamp=time.time(),
                source="system",
                confidence=0.5,  # Confidenza iniziale
                related_concepts=set(),
                examples=[],
                applications=[],
                verification_count=0,
                feedback_history=[],
                feedbacks=[]
            )
        
        # Aggiorna la confidenza in base al tipo di feedback
        current = self.knowledge_base[concept_name]
        
        if feedback.type == FeedbackType.CREATE:
            # Nuovo concetto, usa la confidenza fornita
            current.confidence = confidence
        elif feedback.type == FeedbackType.UPDATE:
            # Media pesata con il nuovo feedback
            weight = min(0.4, 1.0 / (len(current.feedbacks) + 1))
            current.confidence = (
                (1 - weight) * current.confidence + 
                weight * confidence
            )
        elif feedback.type == FeedbackType.VALIDATION:
            # Aumenta la confidenza se validato
            current.confidence = min(
                1.0,
                current.confidence + (0.2 * confidence)
            )
        elif feedback.type == FeedbackType.ERROR:
            # Diminuisci la confidenza se errato
            current.confidence = max(
                0.0,
                current.confidence - (0.3 * (1 - confidence))
            )
        elif feedback.type == FeedbackType.EXPANSION:
            # Espandi la conoscenza con nuovi dettagli
            current.confidence = (
                0.6 * current.confidence + 
                0.4 * confidence
            )
        elif feedback.type == FeedbackType.REINFORCEMENT:
            # Rinforza la conoscenza esistente
            current.confidence = min(
                1.0,
                current.confidence + (0.1 * confidence)
            )
        elif feedback.type == FeedbackType.CORRECTION:
            # Correggi la conoscenza errata
            current.confidence = max(
                0.0,
                current.confidence - (0.4 * (1 - confidence))
            )
        elif feedback.type == FeedbackType.CONFUSION:
            # Confusione nell'applicazione del concetto
            current.confidence = max(
                0.0,
                current.confidence - (0.2 * (1 - confidence))
            )
        
        # Aggiorna contatori
        current.feedbacks.append(feedback)
        current.timestamp = feedback.timestamp
        
    def integrate_knowledge(self, text: str, context: Dict[str, Any]) -> float:
        """
        Integra nuova conoscenza dal testo e dal contesto
        
        Args:
            text: Il testo da cui estrarre la conoscenza
            context: Il contesto corrente
            
        Returns:
            float: Livello di confidenza sull'integrazione (0-1)
        """
        try:
            if not text or not context:
                return 0.0
                
            # Estrai i topic dal contesto
            topics = context.get('topics', [])
            emotions = context.get('emotions', {})
            
            # Calcola la rilevanza del testo rispetto ai topic
            relevance_score = self._calculate_relevance(text, topics)
            
            # Estrai informazioni chiave
            key_info = self._extract_key_information(text)
            
            # Calcola la confidenza basata sulla qualità delle informazioni estratte
            info_quality = min(1.0, len(key_info) / 3)  # Normalizza per max 3 informazioni
            
            # Calcola il peso emotivo
            emotional_weight = 0.0
            if emotions:
                positive_emotions = ['joy', 'surprise']
                emotional_weight = sum(emotions.get(e, 0.0) for e in positive_emotions)
            
            # Calcola la confidenza iniziale con peso emotivo
            base_confidence = (relevance_score * 0.4 + info_quality * 0.4 + emotional_weight * 0.2)
            
            # Calcola il boost di confidenza basato sulla memoria a lungo termine
            memory_boost = 0.0
            for topic in topics:
                if topic in self.knowledge_base:
                    # Aumenta il boost se il topic è già conosciuto
                    node = self.knowledge_base[topic]
                    topic_age = time.time() - node.timestamp
                    verification_boost = min(0.3, node.verification_count * 0.1)
                    memory_boost = max(memory_boost, min(0.3, node.confidence + verification_boost))
            
            # Calcola la confidenza finale
            confidence = min(1.0, base_confidence + memory_boost)
            
            # Aggiorna la base di conoscenza se la confidenza è sufficiente
            if confidence > 0.3:
                # Crea l'entry di conoscenza
                knowledge_entry = {
                    'text': text,
                    'topics': topics,
                    'key_info': key_info,
                    'confidence': confidence,
                    'timestamp': time.time()
                }
                
                # Aggiorna o crea i concetti nella base di conoscenza
                for topic in topics:
                    if topic in self.knowledge_base:
                        # Aggiorna il concetto esistente
                        node = self.knowledge_base[topic]
                        node.description += f"\n{text}"
                        
                        # Aumenta la confidenza se c'è un'emozione positiva
                        if emotional_weight > 0:
                            confidence *= 1.2
                            
                        # Aumenta la confidenza in base alle verifiche precedenti
                        confidence = min(1.0, confidence + verification_boost)
                        
                        # Aggiorna la confidenza del nodo
                        node.confidence = max(node.confidence, confidence)
                        
                        # Incrementa il contatore di verifiche
                        node.verification_count += 1
                    else:
                        # Crea un nuovo concetto
                        self.knowledge_base[topic] = KnowledgeNode(
                            concept=topic,
                            description=text,
                            timestamp=time.time(),
                            source="conversation",
                            confidence=confidence
                        )
                        
            return confidence
            
        except Exception as e:
            logging.error(f"Errore nell'integrazione della conoscenza: {str(e)}")
            return 0.0
            
    def _calculate_relevance(self, text: str, topics: List[str]) -> float:
        """Calcola la rilevanza del testo rispetto ai topic"""
        try:
            if not topics:
                return 0.0
                
            # Converti il testo in minuscolo
            text = text.lower()
            
            # Calcola quanti topic sono presenti nel testo
            topic_matches = sum(1 for topic in topics if topic.lower() in text)
            
            # Normalizza il punteggio
            relevance = topic_matches / len(topics)
            
            return min(1.0, relevance)
            
        except Exception as e:
            logging.error(f"Errore nel calcolo della rilevanza: {str(e)}")
            return 0.0
            
    def _extract_key_information(self, text: str) -> Dict[str, Any]:
        """Estrae informazioni chiave dal testo"""
        try:
            # Implementa l'estrazione delle informazioni chiave
            key_info = {
                'concepts': [],
                'entities': [],
                'keywords': []
            }
            
            # Estrai concetti usando regex patterns
            concept_patterns = [
                r'(?i)(machine learning|deep learning|artificial intelligence|neural network)',
                r'(?i)(data science|big data|data mining|data analysis)',
                r'(?i)(natural language processing|computer vision|robotics)'
            ]
            
            for pattern in concept_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                key_info['concepts'].extend([m.group(1) for m in matches])
                
            # Estrai keywords (parole significative)
            words = text.lower().split()
            stopwords = {'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una', 'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra'}
            keywords = [w for w in words if w not in stopwords and len(w) > 3]
            key_info['keywords'] = list(set(keywords))[:10]  # Mantieni solo le prime 10 keywords uniche
            
            return key_info
            
        except Exception as e:
            logging.error(f"Errore nell'estrazione delle informazioni chiave: {str(e)}")
            return {'concepts': [], 'entities': [], 'keywords': []}
        
    def get_concept_knowledge(self, concept: str) -> Optional[Dict]:
        """Recupera la conoscenza di un concetto"""
        if concept in self.knowledge_base:
            node = self.knowledge_base[concept]
            return {
                'description': node.description,
                'confidence': node.confidence,
                'examples': node.examples,
                'related_concepts': list(node.related_concepts),
                'verification_count': node.verification_count,
                'source': node.source,
                'age': time.time() - node.timestamp,
                'feedback_history': node.feedback_history
            }
        return None
        
    def get_learning_statistics(self) -> Dict:
        """Restituisce statistiche sull'apprendimento"""
        total_concepts = len(self.knowledge_base)
        avg_confidence = sum(node.confidence for node in self.knowledge_base.values()) / total_concepts if total_concepts > 0 else 0
        
        # Includi anche le statistiche dal learning manager
        learning_stats = self.learning_manager.analyze_learning_progress()
        
        return {
            'total_concepts': total_concepts,
            'average_confidence': avg_confidence,
            'concepts_by_source': self._count_concepts_by_source(),
            'verification_stats': self._get_verification_stats(),
            'learning_events': len(self.learning_history),
            'feedback_stats': learning_stats
        }
        
    def get_improvement_suggestions(self, concept: str) -> List[str]:
        """Ottiene suggerimenti per migliorare la comprensione di un concetto"""
        if concept not in self.knowledge_base:
            return ["Concetto non trovato nella base di conoscenza"]
            
        node_dict = self.get_concept_knowledge(concept)
        return self.learning_manager.get_feedback_suggestions(node_dict)
        
    def _merge_descriptions(self, old_desc: str, new_desc: str) -> str:
        """Unisce le descrizioni mantenendo le informazioni più rilevanti"""
        # Per ora una semplice concatenazione, da migliorare con NLP
        if old_desc == new_desc:
            return old_desc
        return f"{old_desc}\n\nUlteriori dettagli:\n{new_desc}"
        
    def _update_relationships(self, concept: str, related: Set[str]) -> None:
        """Aggiorna il grafo delle relazioni tra concetti"""
        if concept not in self.concept_relationships:
            self.concept_relationships[concept] = set()
            
        self.concept_relationships[concept].update(related)
        
        # Aggiorna anche le relazioni inverse
        for rel in related:
            if rel not in self.concept_relationships:
                self.concept_relationships[rel] = set()
            self.concept_relationships[rel].add(concept)
            
    def _log_learning_event(self, concept: str, event_type: str, source: str) -> None:
        """Registra un evento di apprendimento"""
        self.learning_history.append({
            'timestamp': time.time(),
            'concept': concept,
            'type': event_type,
            'source': source
        })
        
    def _count_concepts_by_source(self) -> Dict[str, int]:
        """Conta i concetti per fonte"""
        counts = {}
        for node in self.knowledge_base.values():
            counts[node.source] = counts.get(node.source, 0) + 1
        return counts
        
    def _get_verification_stats(self) -> Dict:
        """Calcola statistiche sulle verifiche"""
        verifications = [node.verification_count for node in self.knowledge_base.values()]
        if not verifications:
            return {'min': 0, 'max': 0, 'avg': 0}
            
        return {
            'min': min(verifications),
            'max': max(verifications),
            'avg': sum(verifications) / len(verifications)
        }
        
    def save_to_file(self, filename: str) -> None:
        """Salva la memoria su file"""
        data = {
            'knowledge_base': {
                concept: {
                    'description': node.description,
                    'timestamp': node.timestamp,
                    'source': node.source,
                    'confidence': node.confidence,
                    'related_concepts': list(node.related_concepts),
                    'examples': node.examples,
                    'applications': node.applications,
                    'verification_count': node.verification_count,
                    'feedback_history': node.feedback_history
                }
                for concept, node in self.knowledge_base.items()
            },
            'learning_history': self.learning_history,
            'concept_relationships': {
                concept: list(related)
                for concept, related in self.concept_relationships.items()
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
            
    def load_from_file(self, filename: str) -> None:
        """Carica la memoria da file"""
        with open(filename, 'r') as f:
            data = json.load(f)
            
        self.knowledge_base = {
            concept: KnowledgeNode(
                concept=concept,
                description=info['description'],
                timestamp=info['timestamp'],
                source=info['source'],
                confidence=info['confidence'],
                related_concepts=set(info['related_concepts']),
                examples=info['examples'],
                applications=info['applications'],
                verification_count=info['verification_count'],
                feedback_history=info['feedback_history'],
                feedbacks=[]
            )
            for concept, info in data['knowledge_base'].items()
        }
        
        self.learning_history = data['learning_history']
        self.concept_relationships = {
            concept: set(related)
            for concept, related in data['concept_relationships'].items()
        }
        
    def get_related_concepts(self, concept: str, max_distance: int = 2) -> List[str]:
        """Trova concetti correlati entro una certa distanza nel grafo"""
        if concept not in self.concept_relationships:
            return []
            
        related = set()
        current_level = {concept}
        
        for distance in range(max_distance):
            next_level = set()
            for c in current_level:
                if c in self.concept_relationships:
                    next_level.update(self.concept_relationships[c])
            related.update(next_level)
            current_level = next_level
            
        return list(related - {concept})

    def add_concept(self, concept: str, description: str, confidence: float = 0.5):
        """Aggiunge un nuovo concetto alla memoria"""
        if not concept:
            return False
            
        # Se il concetto non esiste, lo crea
        if concept not in self.knowledge_base:
            self.knowledge_base[concept] = KnowledgeNode(
                concept=concept,
                description=description,
                timestamp=time.time(),
                source="system",
                confidence=confidence,
                related_concepts=set(),
                examples=[],
                applications=[],
                verification_count=0,
                feedback_history=[],
                feedbacks=[]
            )
            return True
            
        # Se il concetto esiste, aggiorna la confidenza e la descrizione
        # solo se la nuova descrizione è sufficientemente diversa
        node = self.knowledge_base[concept]
        if description and self.nlp:
            similarity = self.nlp.compute_similarity(description, node.description)
            if similarity < 0.8:  # Se la descrizione è abbastanza diversa
                node.description = description
                
        # Aggiorna la confidenza come media pesata
        node.confidence = (node.confidence + confidence) / 2
        node.timestamp = time.time()
        
        return True
        
    def get_concept_confidence(self, concept: str) -> float:
        """Restituisce il livello di confidenza per un concetto"""
        if concept in self.knowledge_base:
            return self.knowledge_base[concept].confidence
        return 0.0
        
    def has_concept(self, concept: str) -> bool:
        """Verifica se un concetto è presente nella base di conoscenza"""
        return concept in self.knowledge_base and self.knowledge_base[concept].confidence > 0.0

    def get_relevant_knowledge(self, query: str, current_topic: str) -> List[Dict[str, Any]]:
        """
        Recupera conoscenza rilevante dalla knowledge base e da Wikipedia
        
        Args:
            query: La query dell'utente
            current_topic: Il topic corrente
            
        Returns:
            List[Dict[str, Any]]: Lista di conoscenze rilevanti
        """
        # Prima cerca nella knowledge base locale
        local_knowledge = self._get_local_knowledge(query, current_topic)
        
        # Se non troviamo nulla localmente, cerca su Wikipedia
        if not local_knowledge:
            wiki_knowledge = self._search_wikipedia(query)
            if wiki_knowledge:
                # Aggiungi la nuova conoscenza alla base locale
                self._add_wiki_knowledge(wiki_knowledge)
                return [wiki_knowledge]
                
        return local_knowledge
        
    def _get_local_knowledge(self, query: str, current_topic: str) -> List[Dict[str, Any]]:
        """Cerca nella knowledge base locale"""
        relevant_knowledge = []
        query_lower = query.lower()
        
        for concept, node in self.knowledge_base.items():
            # Controlla se il concetto è menzionato nella query
            if concept.lower() in query_lower:
                relevant_knowledge.append(node)
                continue
                
            # Usa NLP per trovare concetti simili
            if self.nlp:
                similarity = self.nlp.compute_similarity(query_lower, concept.lower())
                if similarity > 0.7:  # Alta similarità
                    relevant_knowledge.append(node)
                    continue
                    
            # Controlla se il concetto è correlato al topic corrente
            if current_topic and self._is_topic_related(concept, current_topic):
                relevant_knowledge.append(node)
                
        return relevant_knowledge
        
    def _search_wikipedia(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Cerca informazioni su Wikipedia
        
        Args:
            query: Query da cercare
            
        Returns:
            Optional[Dict[str, Any]]: Conoscenza trovata o None
        """
        # Se abbiamo già cercato questa query, usa la cache
        if query in self.wiki_cache:
            return self.wiki_cache[query]
            
        try:
            import wikipedia
            wikipedia.set_lang('it')  # Imposta la lingua italiana
            
            # Cerca la pagina più rilevante
            try:
                page = wikipedia.page(query)
                
                # Estrai un sommario conciso
                summary = page.summary.split('\n')[0]
                if len(summary) > 500:
                    summary = summary[:497] + "..."
                    
                knowledge = {
                    'concept': page.title,
                    'description': summary,
                    'confidence': 0.7,  # Confidenza minore per info da Wikipedia
                    'verification_count': 1,
                    'timestamp': time.time(),
                    'source': 'wikipedia',
                    'url': page.url
                }
                
                # Salva nella cache
                self.wiki_cache[query] = knowledge
                
                return knowledge
                
            except wikipedia.exceptions.DisambiguationError as e:
                # In caso di disambiguazione, prendi la prima opzione
                if e.options:
                    return self._search_wikipedia(e.options[0])
                return None
                
            except wikipedia.exceptions.PageError:
                return None
                
        except ImportError:
            print("Wikipedia API non disponibile")
            return None
            
    def _add_wiki_knowledge(self, knowledge: Dict[str, Any]) -> None:
        """
        Aggiunge conoscenza da Wikipedia alla base locale
        
        Args:
            knowledge: Conoscenza da aggiungere
        """
        concept = knowledge['concept']
        
        # Crea un nuovo nodo di conoscenza
        self.knowledge_base[concept] = KnowledgeNode(
            concept=concept,
            description=knowledge['description'],
            timestamp=knowledge['timestamp'],
            source=knowledge['source'],
            confidence=knowledge['confidence']
        )
        
    def get_related_concepts(self, concept: str, max_distance: int = 2) -> List[str]:
        """Trova concetti correlati entro una certa distanza nel grafo"""
        if concept not in self.concept_relationships:
            return []
            
        related = set()
        current_level = {concept}
        
        for distance in range(max_distance):
            next_level = set()
            for c in current_level:
                if c in self.concept_relationships:
                    next_level.update(self.concept_relationships[c])
            related.update(next_level)
            current_level = next_level
            
        return list(related - {concept})

    def _is_topic_related(self, topic: str, text: str) -> bool:
        """Verifica se un topic è correlato al testo"""
        if not text:
            return False
            
        # Normalizza i testi
        topic_lower = topic.lower()
        text_lower = text.lower()
        
        # Controlla se il topic è contenuto nel testo
        if topic_lower in text_lower:
            return True
            
        # Controlla sinonimi e termini correlati
        related_terms = {
            'machine_learning': ['ml', 'ai', 'artificial intelligence', 'deep learning'],
            'deep_learning': ['neural networks', 'dl', 'machine learning'],
            'neural_networks': ['deep learning', 'ai', 'artificial intelligence'],
            'artificial_intelligence': ['ai', 'machine learning', 'deep learning']
        }
        
        # Se il topic ha termini correlati, controlla se sono nel testo
        if topic_lower in related_terms:
            return any(term in text_lower for term in related_terms[topic_lower])
            
        return False
