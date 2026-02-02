import numpy as np
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import time
import math
import re
# import spacy # Removed for ALLMA Neural-Light Architecture
    
try:
    from transformers import AutoTokenizer, AutoModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    AutoTokenizer = None
    AutoModel = None

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False



class CuriosityDrive:
    """Sistema principale di gestione della curiosità"""
    def __init__(self):
        # 1. Motivazione Intrinseca
        self.intrinsic_motivation = {
            'discovery_drive': 0.5,      # Spinta alla scoperta
            'learning_desire': 0.5,      # Desiderio di apprendere
            'exploration_urge': 0.5,     # Urgenza di esplorare
            'understanding_need': 0.5    # Necessità di capire
        }
        
        # 2. Sviluppo Naturale
        self.development_state = {
            'knowledge_level': 0.3,      # Livello iniziale di conoscenza aumentato
            'question_complexity': 0.4,   # Complessità iniziale delle domande aumentata
            'understanding_depth': 0.3,   # Profondità iniziale di comprensione aumentata
            'connection_ability': 0.3     # Capacità iniziale di fare collegamenti aumentata
        }
        
        # 3. Sistema Pratico
        self.knowledge_gaps = set()      # Concetti non compresi
        self.interest_areas = {}         # Aree di interesse
        self.discovery_reward = 0.0      # Gratificazione dalla scoperta
        
        # 4. Sistema Emotivo
        self.emotional_state = EmotionalCuriosity()
        
        # 5. Sistema di Ricompensa
        self.reward_system = RewardSystem()
        
        # 6. Evoluzione
        self.curiosity_evolution = CuriosityEvolution()
        
        # 7. Bilanciamento
        self.balance_system = CuriosityBalance()
        
        # 8. Prioritizzazione della curiosità
        self.curiosity_prioritization = CuriosityPrioritization()
        
        self.concept_detector = UnknownConceptDetector()
        self.exploration_rate = 0.8
        self.novelty_threshold = 0.5
        
    def detect_unknown_concepts(self, text: str, context: Dict) -> List[str]:
        """
        Rileva concetti sconosciuti nel testo
        
        Args:
            text: Testo da analizzare
            context: Contesto dell'analisi
            
        Returns:
            Lista di concetti sconosciuti trovati
        """
        if not text:
            raise ValueError("Il testo non può essere vuoto")
            
        return self.concept_detector.detect_unknown_concepts(text)

    def process_input(self, input_data: str, context: Optional[Dict] = None) -> Dict:
        """Alias per retrocompatibilità"""
        return self.process(input_data, context)

    def process(self, input_data: str, context: Optional[Dict] = None) -> Dict:
        """Elabora un nuovo input e genera risposta basata sulla curiosità"""
        if context is None:
            context = {}
            
        # Analizza l'input
        unknown_concepts = self._identify_unknowns(input_data)
        interesting_patterns = self._identify_patterns(input_data)
        
        # Aggiorna stato emotivo e ottieni intensità emotiva
        self.emotional_state.update(unknown_concepts, interesting_patterns)
        context['emotional_intensity'] = self.emotional_state.excitement
        
        # Prioritizza gli argomenti
        prioritized_unknowns = set()
        for concept in unknown_concepts:
            if self.curiosity_prioritization.should_explore(concept, context):
                prioritized_unknowns.add(concept)
                self.curiosity_prioritization.update_topic_priority(concept, context)
        
        # Genera domande solo per concetti prioritizzati
        questions = self._generate_questions(prioritized_unknowns, input_data)
        self._update_interests(interesting_patterns)
        
        # Calcola ricompense
        reward = self.reward_system.calculate_reward(len(prioritized_unknowns), len(interesting_patterns))
        self.discovery_reward += reward
        
        # Evolvi la curiosità
        self.curiosity_evolution.evolve(self.development_state)
        
        # Incrementa il livello di conoscenza
        self.development_state['knowledge_level'] += 0.1
        
        # Bilancia l'esplorazione
        balanced_response = self.balance_system.optimize_exploration(
            questions, self.interest_areas, self.development_state
        )
        
        # Aggiungi le domande generate e gli argomenti archiviati alla risposta
        balanced_response['questions'] = questions
        balanced_response['archived_topics'] = self.curiosity_prioritization.get_archived_topics()
        balanced_response['emotional_state'] = {
            'excitement': self.emotional_state.excitement,
            'curiosity': self.emotional_state.wonder
        }
        
        return balanced_response

    def _identify_unknowns(self, input_data: str) -> Set[str]:
        """Identifica concetti potenzialmente interessanti nell'input"""
        words = input_data.lower().split()
        
        # Identifica la categoria del contesto
        category = self.curiosity_prioritization._identify_category(input_data)
        
        # Parole chiave specifiche per categoria
        category_keywords = {
            'fotografia': {'fotografia', 'obiettivo', 'composizione', 'paesaggio', 'post-produzione', 'grandangolare'},
            'musica': {'musica', 'piano', 'melodia', 'nota', 'strumento', 'musicale'},
            'cucina': {'cucina', 'ricetta', 'ingrediente', 'piatto', 'torta', 'molecolare'},
            'tecnologia': {'programmare', 'software', 'computer', 'digitale', 'tecnologia'},
            'benessere': {'meditazione', 'concentrazione', 'mindfulness', 'benessere', 'relax'}
        }
        
        # Trova parole chiave nel testo
        interesting_concepts = set()
        for word in words:
            # Controlla se la parola è una keyword della categoria
            if category in category_keywords and word in category_keywords[category]:
                interesting_concepts.add(word)
            
            # Aggiungi anche parole vicine a keywords per contesto
            if len(word) > 4:  # Ignora parole troppo corte
                interesting_concepts.add(word)
        
        return interesting_concepts

    def _identify_patterns(self, input_data: str) -> List[str]:
        """Identifica pattern interessanti nell'input"""
        words = input_data.lower().split()
        patterns = []
        
        # Cerca pattern di parole consecutive
        for i in range(len(words)-1):
            pattern = f"{words[i]} {words[i+1]}"
            patterns.append(pattern)
            
        return patterns

    def _generate_questions(self, unknowns: Set[str], original_text: str) -> List[str]:
        """Genera domande basate su concetti sconosciuti e contesto"""
        questions = []
        words = original_text.lower().split()
        
        # Identifica la categoria del contesto
        category = self.curiosity_prioritization._identify_category(original_text)
        
        for i, word in enumerate(words):
            if word in unknowns:
                # Ottieni il contesto locale
                start_idx = max(0, i-3)
                end_idx = min(len(words), i+4)
                local_context = " ".join(words[start_idx:end_idx])
                
                # Genera domande basate sul livello di complessità
                complexity = self.development_state['question_complexity']
                
                if complexity < 0.3:
                    # Domande base
                    questions.append(f"Cosa significa {word} in questo contesto?")
                    questions.append(f"Perché {word} è importante qui?")
                
                elif complexity < 0.6:
                    # Domande intermedie
                    questions.append(f"Come si collega {word} con {local_context}?")
                    questions.append(f"Quali sono le implicazioni di {word} in questo ambito?")
                    
                    # Aggiungi domande specifiche per categoria
                    if category in self.curiosity_prioritization.main_categories:
                        category_questions = {
                            'fotografia': [
                                f"Come influisce {word} sulla composizione?",
                                f"Quale attrezzatura serve per {word}?"
                            ],
                            'musica': [
                                f"Come si applica {word} nella pratica musicale?",
                                f"Quali sono gli aspetti teorici di {word}?"
                            ],
                            'cucina': [
                                f"Come si usa {word} nella preparazione?",
                                f"Quali sono le alternative a {word}?"
                            ],
                            'tecnologia': [
                                f"Come si implementa {word}?",
                                f"Quali sono i vantaggi di usare {word}?"
                            ],
                            'benessere': [
                                f"Che benefici porta {word}?",
                                f"Come si integra {word} nella pratica?"
                            ]
                        }
                        questions.extend(category_questions[category])
                
                else:
                    # Domande avanzate
                    questions.append(f"Quali sono le interconnessioni tra {word} e altri concetti in {local_context}?")
                    questions.append(f"Come potremmo innovare o migliorare l'uso di {word} in questo contesto?")
                    questions.append(f"Quali sono le implicazioni a lungo termine di {word}?")
                    
                    # Domande di approfondimento specifiche per categoria
                    if category in self.curiosity_prioritization.main_categories:
                        advanced_questions = {
                            'fotografia': [
                                f"Come evolverà l'uso di {word} con le nuove tecnologie?",
                                f"Quali sono le tecniche avanzate che coinvolgono {word}?"
                            ],
                            'musica': [
                                f"Come si può innovare {word} nella composizione?",
                                f"Quali sono le applicazioni sperimentali di {word}?"
                            ],
                            'cucina': [
                                f"Come si può reinventare {word} con tecniche moderne?",
                                f"Quali sono le frontiere della sperimentazione con {word}?"
                            ],
                            'tecnologia': [
                                f"Come scalerà {word} in futuro?",
                                f"Quali sono le implicazioni etiche di {word}?"
                            ],
                            'benessere': [
                                f"Come evolverà la comprensione di {word} nel tempo?",
                                f"Quali sono le frontiere della ricerca su {word}?"
                            ]
                        }
                        questions.extend(advanced_questions[category])
                
        return questions[:5]  # Limita a 5 domande per evitare overload

    def _update_interests(self, patterns: List[str]) -> None:
        """Aggiorna le aree di interesse basate sui pattern trovati"""
        for pattern in patterns:
            if pattern not in self.interest_areas:
                self.interest_areas[pattern] = {
                    'interest_level': 0.5,
                    'exploration_count': 1,
                    'last_explored': time.time()
                }
            else:
                self.interest_areas[pattern]['interest_level'] *= 1.1
                self.interest_areas[pattern]['exploration_count'] += 1
                self.interest_areas[pattern]['last_explored'] = time.time()

class EmotionalCuriosity:
    """Gestisce l'aspetto emotivo della curiosità"""
    def __init__(self):
        self.excitement = 0.3        # Eccitazione per nuove scoperte
        self.frustration = 0.0       # Frustrazione per non capire
        self.satisfaction = 0.0      # Soddisfazione dall'apprendimento
        self.wonder = 0.3           # Meraviglia per nuove scoperte
        self.concept_detector = UnknownConceptDetector()
        self.learning_history: List[Dict] = []
        
    def update(self, unknowns: Set[str], patterns: List[str]):
        """
        Aggiorna lo stato emotivo basato sulle scoperte
        
        Args:
            unknowns: Concetti sconosciuti trovati
            patterns: Pattern riconosciuti
        """
        # Aggiorna eccitazione in base ai nuovi concetti
        self.excitement = min(1.0, 0.3 + len(unknowns) * 0.1)
        
        # Aggiorna frustrazione se ci sono troppi concetti sconosciuti
        if len(unknowns) > 5:
            self.frustration = min(1.0, self.frustration + 0.2)
        else:
            self.frustration = max(0.0, self.frustration - 0.1)
        
        # Aggiorna soddisfazione in base ai pattern riconosciuti
        self.satisfaction = min(1.0, 0.1 * len(patterns))
        
        # Aggiorna meraviglia in base alla novità delle scoperte
        self.wonder = min(1.0, 0.3 + len(unknowns) * 0.15)
        
        # Applica decadimento naturale
        self._natural_decay()
        
        # Registra nella storia
        self._record_emotional_state(unknowns, patterns)
    
    def _natural_decay(self):
        """Applica decadimento naturale alle emozioni"""
        decay_rate = 0.05
        self.excitement = max(0.0, self.excitement - decay_rate)
        self.frustration = max(0.0, self.frustration - decay_rate)
        self.satisfaction = max(0.0, self.satisfaction - decay_rate)
        self.wonder = max(0.0, self.wonder - decay_rate)
    
    def _record_emotional_state(self, unknowns: Set[str], patterns: List[str]):
        """Registra lo stato emotivo corrente"""
        state = {
            "timestamp": np.datetime64('now'),
            "excitement": self.excitement,
            "frustration": self.frustration,
            "satisfaction": self.satisfaction,
            "wonder": self.wonder,
            "unknown_concepts": list(unknowns),
            "patterns_found": len(patterns)
        }
        self.learning_history.append(state)
        
        # Mantiene solo gli ultimi 1000 stati
        if len(self.learning_history) > 1000:
            self.learning_history = self.learning_history[-1000:]
    
    def get_emotional_state(self) -> Dict[str, float]:
        """Restituisce lo stato emotivo corrente"""
        return {
            "excitement": self.excitement,
            "frustration": self.frustration,
            "satisfaction": self.satisfaction,
            "wonder": self.wonder
        }
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analizza il testo per trovare concetti sconosciuti e aggiornare lo stato emotivo
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Dizionario con i risultati dell'analisi
        """
        unknown_concepts = self.concept_detector.detect_unknown_concepts(text)
        
        # Simula il riconoscimento di pattern per questo esempio
        patterns = []  # In un sistema reale, questo verrebbe dal PatternRecognitionSystem
        
        # Aggiorna lo stato emotivo
        self.update(unknown_concepts, patterns)
        
        return {
            "unknown_concepts": unknown_concepts,
            "emotional_state": self.get_emotional_state(),
            "patterns_found": len(patterns)
        }

class UnknownConceptDetector:
    """Sistema per il rilevamento di concetti sconosciuti"""
    
    def __init__(self, knowledge_memory=None, threshold: float = 0.7):
        self.knowledge_memory = knowledge_memory
        self.confidence_threshold = threshold
        self.known_concepts = {} # Initialize empty knowledge base
        
        # Lista parole comuni (Stopwords estese + vocabolario base)
        # In produzione, caricarla da file json
        self.common_words = {
            "il", "lo", "la", "i", "gli", "le", "un", "uno", "una",
            "di", "a", "da", "in", "con", "su", "per", "tra", "fra",
            "io", "tu", "lui", "lei", "noi", "voi", "loro",
            "essere", "avere", "fare", "dire", "potere", "volere", "sapere",
            "stare", "dovere", "vedere", "andare", "venire", "dare", "parlare",
            "trovare", "sentire", "lasciare", "prendere", "guardare", "mettere",
            "pensare", "passare", "credere", "portare", "parere", "tornare",
            "sembrare", "tenere", "capire", "morire", "chiamare", "conoscere",
            "rimanere", "chiedere", "cercare", "entrare", "vivere", "aprire",
            "uscire", "ricordare", "bisognare", "cominciare", "rispondere",
            "spettare", "correre", "scrivere", "diventare", "restare", "seguire",
            "bastare", "perdere", "rendere", "salire", "piacere", "continuare",
            "partire", "servire", "giungere", "fermare", "apparire", "amare",
            "esistere", "ricevere", "ridere", "cambiare", "spiegami"
        }
        
    def detect_unknown_concepts(self, text: str) -> Set[str]:
        """
        Rileva concetti sconosciuti nel testo (Logic-Heavy method)
        """
        unknown_concepts = set()
        
        # 1. Pulisci testo
        text_clean = re.sub(r'[^\w\s]', '', text)
        words = text_clean.split()
        
        # 2. Euristica: Parole con Maiuscola (non a inizio frase) sono potenziali Entità espresse
        #    Parole rare (non in common_words e non conosciute) sono concetti
        
        for i, word in enumerate(words):
            w_lower = word.lower()
            
            # Skip common words
            if w_lower in self.common_words:
                continue
                
            # Skip numbers
            if w_lower.isdigit():
                continue
                
            # Check knowledge memory
            if self._is_known_concept(w_lower):
                continue
            
            # Se siamo qui, è una parola "rara" per il sistema
            
            # Skip adverbs (ending in 'mente')
            if w_lower.endswith('mente'):
                continue

            # Aggiungi se è Maiuscola (e non è la prima parola assoluta, o lo è ma non è comune)
            if word[0].isupper():
                if i > 0 or w_lower not in self.common_words:
                     unknown_concepts.add(w_lower)
            
            # Aggiungi se è lunga, complessa e non è un verbo generico
            elif len(word) > 9:
                 # Exclude common verb endings to avoid flagging actions as concepts
                 if not (w_lower.endswith('are') or w_lower.endswith('ere') or w_lower.endswith('ire')):
                     unknown_concepts.add(w_lower)
        
        return unknown_concepts
    
    def _is_potential_concept(self, token) -> bool:
        """Verifica se un token può essere un concetto"""
        return (
            token.pos_ in ["NOUN", "PROPN"] and
            not token.is_stop and
            len(token.text) > 2
        )
    
    def _is_known_concept(self, concept: str) -> bool:
        """Verifica se un concetto è già conosciuto"""
        if concept not in self.known_concepts:
            return False
            
        return self.known_concepts[concept].confidence >= self.confidence_threshold
    
    def learn_concept(self, concept: str, context: str):
        """
        Apprende un nuovo concetto dal contesto
        
        Args:
            concept: Concetto da apprendere
            context: Contesto in cui appare il concetto
        """
        if self.tokenizer is None or self.model is None or not TORCH_AVAILABLE:
            return # Skip if no model available
            
        # Codifica il contesto
        inputs = self.tokenizer(context, return_tensors="pt", padding=True, truncation=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
            context_embedding = outputs.last_hidden_state.mean(dim=1)
        
        if concept not in self.known_concepts:
            self.known_concepts[concept] = ConceptKnowledge(
                name=concept,
                confidence=0.1,
                occurrences=1,
                context_embeddings=[context_embedding]
            )
        else:
            knowledge = self.known_concepts[concept]
            knowledge.occurrences += 1
            knowledge.context_embeddings.append(context_embedding)
            # Aumenta la confidenza in base alle occorrenze
            knowledge.confidence = min(1.0, knowledge.confidence + 0.1)
    
    def find_related_concepts(self, concept: str, threshold: float = 0.7) -> List[str]:
        """
        Trova concetti correlati a quello dato
        
        Args:
            concept: Concetto di riferimento
            threshold: Soglia di similarità
            
        Returns:
            Lista di concetti correlati
        """
        if concept not in self.known_concepts:
            return []
            
        related = []
        concept_embeddings = self.known_concepts[concept].context_embeddings
        
        for other_concept, knowledge in self.known_concepts.items():
            if other_concept == concept:
                continue
                
            # Calcola similarità media tra i contesti
            similarities = []
            for emb1 in concept_embeddings:
                for emb2 in knowledge.context_embeddings:
                    sim = cosine_similarity(
                        emb1.numpy().reshape(1, -1),
                        emb2.numpy().reshape(1, -1)
                    )[0][0]
                    similarities.append(sim)
            
            avg_similarity = np.mean(similarities)
            if avg_similarity >= threshold:
                related.append(other_concept)
        
        return related

class ConceptKnowledge:
    """Rappresenta la conoscenza di un concetto"""
    def __init__(self, name: str, confidence: float = 0.0, occurrences: int = 0, last_seen: Optional[float] = None, related_concepts: Dict[str, float] = {}, context_embeddings: List['torch.Tensor'] = []):
        self.name = name
        self.confidence = confidence
        self.occurrences = occurrences
        self.last_seen = last_seen
        self.related_concepts = related_concepts
        self.context_embeddings = context_embeddings

class RewardSystem:
    """Gestisce il sistema di ricompensa interno"""
    def __init__(self):
        self.discovery_value = 0.1   # Valore base per nuove scoperte
        self.pattern_value = 0.2     # Valore base per pattern trovati
        self.threshold = 0.7         # Soglia per ricompensa significativa

    def calculate_reward(self, num_unknowns: int, num_patterns: int) -> float:
        """Calcola la ricompensa basata sulle scoperte"""
        discovery_reward = num_unknowns * self.discovery_value
        pattern_reward = num_patterns * self.pattern_value
        
        total_reward = discovery_reward + pattern_reward
        
        # Bonus per scoperte significative
        if total_reward > self.threshold:
            total_reward *= 1.5
            
        return min(1.0, total_reward)

class CuriosityEvolution:
    """Gestisce l'evoluzione della curiosità nel tempo"""
    def __init__(self):
        self.evolution_rate = 0.2    # Tasso di evoluzione base
        self.maturity_level = 0.1    # Livello di maturità della curiosità
        self.complexity_threshold = 0.3  # Soglia per aumentare complessità

    def evolve(self, development_state: Dict) -> None:
        """Evolve la curiosità basata sullo stato di sviluppo"""
        # Aumenta maturità
        self.maturity_level = min(1.0, self.maturity_level + self.evolution_rate * 0.1)
        
        # Aggiorna complessità delle domande
        if development_state['knowledge_level'] > self.complexity_threshold:
            development_state['question_complexity'] = min(
                1.0, 
                development_state['question_complexity'] + 0.1
            )
            self.complexity_threshold += 0.1
            
        # Aggiorna altri parametri di sviluppo
        development_state['understanding_depth'] = min(
            1.0,
            development_state['understanding_depth'] + 0.05
        )
        
        development_state['connection_ability'] = min(
            1.0,
            development_state['connection_ability'] + 0.08
        )

class CuriosityBalance:
    """Gestisce il bilanciamento della curiosità"""
    def __init__(self):
        self.exploration_rate = 0.7   # Tasso di esplorazione
        self.focus_rate = 0.3        # Tasso di focus
        self.max_questions = 3       # Numero massimo di domande per volta

    def optimize_exploration(self, questions: List[str], 
                           interests: Dict, 
                           development: Dict) -> Dict:
        """Ottimizza l'esplorazione bilanciando diversi fattori"""
        # Seleziona domande più rilevanti
        prioritized_questions = self._prioritize_questions(
            questions, 
            development['question_complexity']
        )
        
        # Bilancia tra esplorazione e approfondimento
        exploration_focus = self._balance_exploration_focus(
            interests, 
            development['knowledge_level']
        )
        
        return {
            'questions': prioritized_questions[:self.max_questions],
            'exploration_focus': exploration_focus
        }

    def _prioritize_questions(self, questions: List[str], 
                            complexity: float) -> List[str]:
        """Prioritizza le domande basate sulla complessità"""
        if complexity < 0.3:
            # Preferisci domande semplici
            return sorted(questions, key=len)
        elif complexity < 0.7:
            # Mix di domande
            return questions
        else:
            # Preferisci domande complesse
            return sorted(questions, key=len, reverse=True)

    def _balance_exploration_focus(self, interests: Dict, 
                                 knowledge_level: float) -> str:
        """Determina il focus tra esplorazione e approfondimento"""
        if knowledge_level < 0.3:
            return "exploration"
        elif len(interests) < 5:
            return "expansion"
        else:
            return "deepening"

class CuriosityPrioritization:
    """Gestisce la prioritizzazione della curiosità per evitare overload cognitivo"""
    def __init__(self):
        self.topic_priorities = {}  # Priorità per argomento
        self.topic_categories = {}  # Categorie per argomento
        self.archived_topics = {}   # Argomenti da esplorare in futuro
        self.attention_threshold = 0.3  # Abbassata la soglia di attenzione
        
        # Definizione delle categorie principali
        self.main_categories = {
            'fotografia': ['foto', 'camera', 'obiettivo', 'treppiede', 'paesaggio', 'notturna', 'post-produzione'],
            'musica': ['piano', 'suono', 'melodia', 'nota', 'strumento', 'musicale'],
            'cucina': ['ricetta', 'cucinare', 'ingrediente', 'piatto', 'torta', 'molecolare'],
            'tecnologia': ['programmare', 'computer', 'software', 'app', 'digitale'],
            'benessere': ['meditazione', 'concentrazione', 'mindfulness', 'benessere', 'relax']
        }
        
        # Persistence
        from allma_model.core.module_state_manager import ModuleStateManager
        self.state_manager = ModuleStateManager()
        self._load_state()

    def _load_state(self):
        """Restore state from DB."""
        state = self.state_manager.load_state('curiosity_prioritization')
        if state:
            self.topic_priorities = state.get('topic_priorities', {})
            self.archived_topics = state.get('archived_topics', {})
            # Ensure float conversion for existing data if needed
            
    def _save_state(self):
        """Save current state to DB."""
        state = {
            'topic_priorities': self.topic_priorities,
            'archived_topics': self.archived_topics
        }
        self.state_manager.save_state('curiosity_prioritization', state)
    
    def _identify_category(self, topic: str) -> str:
        """Identifica la categoria di un argomento"""
        topic_words = set(topic.lower().split())
        
        for category, keywords in self.main_categories.items():
            if any(keyword in topic_words for keyword in keywords):
                return category
        return 'altro'
    
    def evaluate_relevance(self, topic: str, context: Dict) -> float:
        """Valuta la rilevanza di un argomento basandosi sul contesto"""
        relevance_score = 0.0
        
        # Frequenza dell'argomento
        frequency = self.topic_priorities.get(topic, {}).get('frequency', 0)
        relevance_score += frequency * 0.2
        
        # Rilevanza emotiva
        emotional_intensity = context.get('emotional_intensity', 0)
        relevance_score += emotional_intensity * 0.3
        
        # Rilevanza temporale
        temporal_relevance = self._calculate_temporal_relevance(topic)
        relevance_score += temporal_relevance * 0.2
        
        # Rilevanza categoriale
        category_relevance = self._calculate_category_relevance(topic)
        relevance_score += category_relevance * 0.3
        
        return min(1.0, relevance_score)
    
    def _calculate_category_relevance(self, topic: str) -> float:
        """Calcola la rilevanza basata sulla categoria"""
        category = self._identify_category(topic)
        if category == 'altro':
            return 0.1
            
        category_topics = [t for t, c in self.topic_categories.items() if c == category]
        if not category_topics:
            return 0.5
            
        # Media delle priorità degli argomenti nella stessa categoria
        category_priorities = [
            self.topic_priorities.get(t, {}).get('frequency', 0)
            for t in category_topics
        ]
        return min(1.0, sum(category_priorities) / len(category_priorities))
    
    def _calculate_temporal_relevance(self, topic: str) -> float:
        """Calcola la rilevanza temporale di un argomento"""
        if topic not in self.topic_priorities:
            return 0.0
            
        last_seen = self.topic_priorities[topic].get('last_seen', 0)
        current_time = time.time()
        time_diff = current_time - last_seen
        
        # Decadimento esponenziale
        return math.exp(-time_diff / (24 * 3600))  # 24 ore come costante di tempo

    def archive_topic(self, topic: str) -> None:
        """Archivia un argomento per esplorazione futura"""
        category = self._identify_category(topic)
        if topic not in self.archived_topics:
            self.archived_topics[topic] = {
                'archived_at': time.time(),
                'priority': self.topic_priorities.get(topic, {}).get('frequency', 0),
                'category': category,
                'related_questions': self._generate_archived_questions(topic, category)
            }
            self._save_state()
    
    def _generate_archived_questions(self, topic: str, category: str) -> List[str]:
        """Genera domande specifiche per argomenti archiviati"""
        questions = []
        
        # Domande generali per categoria
        category_questions = {
            'fotografia': [
                f"Come si collega {topic} con la composizione fotografica?",
                f"Quale attrezzatura serve per {topic}?",
                f"Quali tecniche specifiche si usano per {topic}?"
            ],
            'musica': [
                f"Quali sono i principi teorici dietro {topic}?",
                f"Come si pratica {topic}?",
                f"Quali sono le applicazioni pratiche di {topic}?"
            ],
            'cucina': [
                f"Quali ingredienti sono fondamentali per {topic}?",
                f"Quali tecniche di preparazione si usano per {topic}?",
                f"Come si può innovare {topic}?"
            ],
            'tecnologia': [
                f"Quali sono i prerequisiti per imparare {topic}?",
                f"Come si applica {topic} in progetti reali?",
                f"Quali sono le best practices per {topic}?"
            ],
            'benessere': [
                f"Che benefici porta la pratica di {topic}?",
                f"Come si integra {topic} nella routine quotidiana?",
                f"Quali sono gli aspetti più importanti di {topic}?"
            ]
        }
        
        # Aggiungi domande specifiche per categoria
        if category in category_questions:
            questions.extend(category_questions[category])
        
        # Aggiungi domande generali
        questions.extend([
            f"Quali sono i principi fondamentali di {topic}?",
            f"Come si può migliorare in {topic}?",
            f"Quali sono le applicazioni pratiche di {topic}?"
        ])
        
        return questions

    def update_topic_priority(self, topic: str, context: Dict) -> None:
        """Aggiorna la priorità di un argomento"""
        if topic not in self.topic_priorities:
            self.topic_priorities[topic] = {
                'frequency': 0,
                'emotional_weight': 0,
                'last_seen': time.time()
            }
        
        # Aggiorna frequenza
        self.topic_priorities[topic]['frequency'] += 1
        
        # Aggiorna peso emotivo
        emotional_intensity = context.get('emotional_intensity', 0)
        current_weight = self.topic_priorities[topic]['emotional_weight']
        self.topic_priorities[topic]['emotional_weight'] = (current_weight + emotional_intensity) / 2
        
        # Aggiorna timestamp
        self.topic_priorities[topic]['last_seen'] = time.time()
        
        self._save_state()
    
    def should_explore(self, topic: str, context: Dict) -> bool:
        """Decide se un argomento dovrebbe essere esplorato ora"""
        relevance = self.evaluate_relevance(topic, context)
        
        if relevance >= self.attention_threshold:
            return True
        elif relevance >= 0.1:  # Abbassata la soglia per l'archiviazione
            self.archive_topic(topic)
            return False
        else:
            return False
    
    def get_archived_topics(self) -> List[str]:
        """Recupera argomenti archiviati pronti per essere esplorati"""
        current_time = time.time()
        ready_topics = []
        
        for topic, info in self.archived_topics.items():
            time_archived = current_time - info['archived_at']
            if time_archived > (24 * 3600):  # 24 ore di attesa
                ready_topics.append(topic)
                
        return ready_topics
