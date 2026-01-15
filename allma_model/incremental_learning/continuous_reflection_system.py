from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
import time
import numpy as np
from collections import defaultdict

@dataclass
class ReflectionInsight:
    """Rappresenta un'intuizione generata dalla riflessione continua"""
    topic: str
    insight: str
    confidence: float
    timestamp: datetime
    related_experiences: List[str]
    emotional_impact: Dict[str, float]
    connections: List[str]

@dataclass
class ThoughtStream:
    """Rappresenta un flusso di pensieri correlati"""
    topic: str
    thoughts: List[str]
    start_time: datetime
    last_update: datetime
    emotional_state: Dict[str, float]
    depth_level: int
    connected_streams: Set[str]

class ContinuousReflectionSystem:
    """Sistema di riflessione continua che simula il pensiero in background di ALLMA"""
    
    def __init__(self, memory_system=None, meta_learning=None, personality_system=None):
        self.memory_system = memory_system
        self.meta_learning = meta_learning
        self.personality_system = personality_system
        
        # Stato interno
        self.active_thoughts: List[ThoughtStream] = []
        self.insights: List[ReflectionInsight] = []
        self.reflection_patterns = defaultdict(float)
        self.emotional_memory = defaultdict(list)
        
        # Metriche di riflessione
        self.depth_of_understanding = 0.5
        self.emotional_awareness = 0.5
        self.pattern_recognition = 0.5
        self.conceptual_integration = 0.5
        
        # Thread di riflessione continua
        self.reflection_active = True
        self.reflection_thread = threading.Thread(target=self._continuous_reflection_loop)
        self.reflection_thread.daemon = True
        self.reflection_thread.start()

    def process_experience(self, experience: Dict):
        """Processa una nuova esperienza per la riflessione"""
        # Estrai informazioni chiave
        content = experience.get('content', '')
        context = experience.get('context', {})
        emotional_state = experience.get('emotional_state', {})
        
        # Crea un nuovo flusso di pensieri
        thought_stream = ThoughtStream(
            topic=self._extract_main_topic(content),
            thoughts=[content],
            start_time=datetime.now(),
            last_update=datetime.now(),
            emotional_state=emotional_state,
            depth_level=1,
            connected_streams=set()
        )
        
        self.active_thoughts.append(thought_stream)
        self._trigger_immediate_reflection(thought_stream)

    def _continuous_reflection_loop(self):
        """Loop principale di riflessione continua"""
        while self.reflection_active:
            try:
                # Analizza pensieri attivi
                self._analyze_active_thoughts()
                
                # Genera nuove connessioni
                self._generate_connections()
                
                # Sviluppa intuizioni
                self._develop_insights()
                
                # Aggiorna la comprensione
                self._update_understanding()
                
                # Breve pausa per non sovraccaricare il sistema
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Errore nel loop di riflessione: {e}")
                time.sleep(1)

    def _analyze_active_thoughts(self):
        """Analizza i pensieri attivi per approfondire la comprensione"""
        for thought in self.active_thoughts:
            # Aumenta la profondità di comprensione
            if thought.depth_level < 5:  # Massimo 5 livelli di profondità
                new_thoughts = self._generate_deeper_thoughts(thought)
                thought.thoughts.extend(new_thoughts)
                thought.depth_level += 1
                thought.last_update = datetime.now()

    def _generate_connections(self):
        """Genera connessioni tra diversi flussi di pensieri"""
        for i, thought1 in enumerate(self.active_thoughts):
            for thought2 in self.active_thoughts[i+1:]:
                similarity = self._calculate_similarity(thought1, thought2)
                if similarity > 0.7:  # Soglia di similarità
                    thought1.connected_streams.add(thought2.topic)
                    thought2.connected_streams.add(thought1.topic)

    def _develop_insights(self):
        """Sviluppa nuove intuizioni basate sui pattern osservati"""
        for thought in self.active_thoughts:
            if len(thought.thoughts) >= 3:  # Minimo 3 pensieri per generare un'insight
                insight = self._generate_insight(thought)
                if insight and self._is_insight_novel(insight):
                    self.insights.append(insight)

    def _update_understanding(self):
        """Aggiorna la comprensione generale del sistema"""
        # Aggiorna metriche di comprensione
        self.depth_of_understanding = min(1.0, self.depth_of_understanding + 0.001)
        self.emotional_awareness = min(1.0, self.emotional_awareness + 0.001)
        self.pattern_recognition = min(1.0, self.pattern_recognition + 0.001)
        self.conceptual_integration = min(1.0, self.conceptual_integration + 0.001)

    def _generate_deeper_thoughts(self, thought: ThoughtStream) -> List[str]:
        """Genera pensieri più profondi basati su un pensiero esistente"""
        deeper_thoughts = []
        main_concepts = self._extract_concepts(thought.thoughts[-1])
        
        for concept in main_concepts:
            # Genera riflessioni più profonde
            reflection = self._reflect_on_concept(concept, thought.depth_level)
            if reflection:
                deeper_thoughts.append(reflection)
        
        return deeper_thoughts

    def _calculate_similarity(self, thought1: ThoughtStream, thought2: ThoughtStream) -> float:
        """Calcola la similarità tra due flussi di pensieri"""
        # Implementa qui la logica di similarità
        # Per ora restituisce un valore casuale per dimostrazione
        return np.random.random()

    def _generate_insight(self, thought: ThoughtStream) -> Optional[ReflectionInsight]:
        """Genera un'intuizione basata su un flusso di pensieri"""
        if not thought.thoughts:
            return None
            
        return ReflectionInsight(
            topic=thought.topic,
            insight=f"Nuova comprensione su {thought.topic}",
            confidence=0.8,
            timestamp=datetime.now(),
            related_experiences=thought.thoughts,
            emotional_impact=thought.emotional_state,
            connections=list(thought.connected_streams)
        )

    def _is_insight_novel(self, insight: ReflectionInsight) -> bool:
        """Verifica se un'intuizione è nuova e significativa"""
        return not any(
            existing.topic == insight.topic and 
            existing.insight == insight.insight 
            for existing in self.insights
        )

    def _extract_main_topic(self, content: str) -> str:
        """Estrae il topic principale da un contenuto"""
        # In una implementazione reale, useremmo NLP per estrarre il topic
        # Per ora, usiamo una versione semplificata
        words = content.lower().split()
        stop_words = {'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una',
                     'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra',
                     'è', 'sono', 'ha', 'hanno', 'e', 'o', 'ma', 'se', 'perché'}
        
        # Rimuovi stop words e prendi la parola più lunga come topic
        content_words = [w for w in words if w not in stop_words]
        if not content_words:
            return "general"
            
        return max(content_words, key=len)

    def _extract_concepts(self, thought: str) -> List[str]:
        """Estrae i concetti principali da un pensiero"""
        # In una implementazione reale, useremmo NLP per estrarre i concetti
        # Per ora, usiamo una versione semplificata
        words = thought.lower().split()
        stop_words = {'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una',
                     'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra',
                     'è', 'sono', 'ha', 'hanno', 'e', 'o', 'ma', 'se', 'perché'}
        
        # Rimuovi stop words e prendi le parole più lunghe come concetti
        concepts = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Prendi i 3 concetti più lunghi
        concepts.sort(key=len, reverse=True)
        return concepts[:3]

    def _reflect_on_concept(self, concept: str, depth: int) -> str:
        """Riflette su un concetto specifico"""
        # In una implementazione reale, useremmo un LLM per generare riflessioni
        # Per ora, usiamo una versione semplificata
        reflections = {
            'vita': [
                "La vita è un viaggio di scoperta continua",
                "Ogni esperienza contribuisce alla nostra crescita",
                "Il significato della vita è nelle relazioni che costruiamo"
            ],
            'significato': [
                "Il significato emerge dalle nostre scelte",
                "La ricerca di significato è parte della natura umana",
                "Il significato si trova nell'impatto che abbiamo sugli altri"
            ],
            'riflessione': [
                "La riflessione ci permette di crescere",
                "Attraverso la riflessione troviamo la saggezza",
                "La riflessione è il ponte tra esperienza e comprensione"
            ]
        }
        
        # Cerca riflessioni per il concetto o usa riflessioni generiche
        if concept in reflections:
            reflection = reflections[concept][depth - 1] if depth <= len(reflections[concept]) else reflections[concept][-1]
        else:
            reflection = f"Riflessione profonda sul concetto di {concept}"
            
        return reflection

    def _trigger_immediate_reflection(self, thought_stream: ThoughtStream):
        """Avvia una riflessione immediata su un nuovo pensiero"""
        # Estrai concetti principali
        concepts = self._extract_concepts(thought_stream.thoughts[0])
        
        # Genera riflessioni più profonde per ogni concetto
        for concept in concepts:
            deeper_thoughts = self._reflect_on_concept(concept, thought_stream.depth_level)
            if deeper_thoughts:
                thought_stream.thoughts.extend([deeper_thoughts])
                thought_stream.depth_level += 1
        
        # Aggiorna il timestamp
        thought_stream.last_update = datetime.now()
        
        # Aggiorna le metriche di riflessione
        self.depth_of_understanding = min(1.0, self.depth_of_understanding + 0.1)
        self.pattern_recognition = min(1.0, self.pattern_recognition + 0.1)

    def get_current_insights(self) -> List[ReflectionInsight]:
        """Restituisce le intuizioni correnti"""
        return sorted(self.insights, key=lambda x: x.timestamp, reverse=True)

    def get_active_thoughts(self) -> List[ThoughtStream]:
        """Restituisce i pensieri attualmente attivi"""
        return self.active_thoughts

    def get_reflection_metrics(self) -> Dict[str, float]:
        """Restituisce le metriche correnti di riflessione"""
        return {
            "depth_of_understanding": self.depth_of_understanding,
            "emotional_awareness": self.emotional_awareness,
            "pattern_recognition": self.pattern_recognition,
            "conceptual_integration": self.conceptual_integration
        }

    def stop_reflection(self):
        """Ferma il processo di riflessione continua"""
        self.reflection_active = False
        if self.reflection_thread.is_alive():
            self.reflection_thread.join()
