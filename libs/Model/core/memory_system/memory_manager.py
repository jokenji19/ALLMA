from typing import Dict, List, Any, Optional, Set
import uuid
import logging
from datetime import datetime, timedelta
import numpy as np

# Configura il logging
logging.basicConfig(level=logging.DEBUG)

class MemoryNode:
    """Rappresenta un nodo di memoria che contiene informazioni su un'interazione"""
    _next_id = 0  # Contatore statico per generare ID incrementali
    
    def __init__(self, content: str, metadata: Dict[str, Any] = None):
        """Inizializza un nuovo nodo di memoria"""
        self.id = MemoryNode._next_id
        MemoryNode._next_id += 1
        self.content = content
        self.metadata = metadata or {}
        self.connections: Set[int] = set()  # Lista di ID dei nodi connessi
        self.timestamp = datetime.now()
        self.emotional_state = self.metadata.get('emotional_state', {})
        self.layer = 'immediate'  # 'immediate', 'short_term', 'long_term'
        
    def to_dict(self) -> Dict[str, Any]:
        """Converte il nodo in un dizionario"""
        return {
            'id': self.id,
            'content': self.content,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'connections': list(self.connections),
            'emotional_state': self.emotional_state,
            'layer': self.layer
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryNode':
        """Crea un nodo da un dizionario"""
        node = cls(data['content'], data.get('metadata', {}))
        node.id = data['id']
        node.timestamp = datetime.fromisoformat(data['timestamp'])
        node.connections = set(data.get('connections', []))
        node.emotional_state = data.get('emotional_state', {})
        node.layer = data.get('layer', 'immediate')
        return node

class AdvancedMemorySystem:
    """Sistema di memoria avanzato che gestisce nodi di memoria e le loro connessioni.
    
    Caratteristiche principali:
    - Sistema di layer (immediate, short-term, long-term)
    - Analisi di pattern tematici ed emotivi
    - Gestione automatica del ciclo di vita delle memorie
    - Calcolo avanzato della similarità emotiva
    
    Questa è l'implementazione ufficiale del sistema di memoria ALLMA.
    """
    def __init__(self):
        self.nodes: Dict[int, MemoryNode] = {}
        self.accuracy = 0.0
        self.performance_stats = {
            'nodes_created': 0,
            'connections_created': 0,
            'successful_retrievals': 0
        }
        
        # Pattern analysis
        self.thematic_map: Dict[str, List[int]] = {}  # topic -> node_ids
        self.emotional_patterns: Dict[str, List[float]] = {}
        self.contextual_patterns: Dict[str, Dict[str, Any]] = {}
        
        # Layer management
        self._manage_memory_lifecycle()
        
    def _get_layer_nodes(self, layer: str) -> List[MemoryNode]:
        """Recupera i nodi di un determinato layer"""
        return [node for node in self.nodes.values() if node.layer == layer]
        
    def _manage_memory_lifecycle(self):
        """Gestisce il ciclo di vita delle memorie tra i diversi layer"""
        now = datetime.now()
        
        for node in self.nodes.values():
            time_diff = now - node.timestamp
            
            # Aggiorna il layer in base al tempo trascorso
            if time_diff > timedelta(days=30) and node.layer != 'long_term':
                node.layer = 'long_term'
            elif time_diff > timedelta(days=1) and node.layer == 'immediate':
                node.layer = 'short_term'
                
    def _update_thematic_connections(self, node_id: int) -> None:
        """Aggiorna le connessioni tematiche per un nodo"""
        node = self.nodes[node_id]
        topics = node.metadata.get('topics', [])
        
        for topic in topics:
            if topic not in self.thematic_map:
                self.thematic_map[topic] = set()
            
            # Aggiungi il nodo alla mappa tematica
            self.thematic_map[topic].add(node_id)
            
            # Crea connessioni con altri nodi che condividono lo stesso tema
            for other_node_id in self.thematic_map[topic]:
                if other_node_id != node_id:
                    self.connect_nodes(node_id, other_node_id)
                    self.connect_nodes(other_node_id, node_id)

    def _update_emotional_patterns(self, node: MemoryNode):
        """Aggiorna i pattern emotivi basati sulla nuova memoria"""
        for emotion, value in node.emotional_state.items():
            if isinstance(value, (int, float)):
                if emotion not in self.emotional_patterns:
                    self.emotional_patterns[emotion] = []
                self.emotional_patterns[emotion].append(float(value))
                
    def _update_contextual_patterns(self, node: MemoryNode):
        """Aggiorna i pattern contestuali basati sulla nuova memoria"""
        if 'time_patterns' not in self.contextual_patterns:
            print("\nDebug - Inizializzazione pattern temporali")  # Debug
            self.contextual_patterns['time_patterns'] = {
                'hourly': [0] * 24,  # 24 ore
                'daily': [0] * 7,    # 7 giorni
                'monthly': [0] * 12   # 12 mesi
            }
        
        # Aggiorna pattern orari
        hour = node.timestamp.hour
        print(f"\nDebug - Aggiornamento pattern orari")  # Debug
        print(f"Ora corrente: {hour}")  # Debug
        print(f"Pattern orari prima: {self.contextual_patterns['time_patterns']['hourly']}")  # Debug
        self.contextual_patterns['time_patterns']['hourly'][hour] += 1
        print(f"Pattern orari dopo: {self.contextual_patterns['time_patterns']['hourly']}")  # Debug
        
        # Aggiorna pattern giornalieri
        day = node.timestamp.weekday()
        self.contextual_patterns['time_patterns']['daily'][day] += 1
        
        # Aggiorna pattern mensili
        month = node.timestamp.month - 1  # 0-based index
        self.contextual_patterns['time_patterns']['monthly'][month] += 1

    def _calculate_emotional_similarity(self, emotions1: Dict[str, Any], emotions2: Dict[str, Any]) -> float:
        """Calcola la similarità tra due stati emotivi usando numpy"""
        # Estrai solo i valori numerici
        keys_to_compare = ['intensity', 'valence', 'arousal', 'dominance']
        values1 = []
        values2 = []
        
        for key in keys_to_compare:
            if key in emotions1 and key in emotions2:
                try:
                    val1 = float(emotions1[key])
                    val2 = float(emotions2[key])
                    values1.append(val1)
                    values2.append(val2)
                except (ValueError, TypeError):
                    continue
        
        if not values1 or not values2:
            return 0.0
            
        # Converti in array numpy
        emotions1_array = np.array(values1)
        emotions2_array = np.array(values2)
        
        # Calcola la similarità usando la distanza euclidea normalizzata
        try:
            distance = np.linalg.norm(emotions1_array - emotions2_array)
            max_distance = np.sqrt(len(values1))  # Massima distanza possibile
            similarity = 1 - (distance / max_distance)
            return float(similarity)
        except:
            return 0.0

    def create_memory_node(self, content: str, metadata: Dict[str, Any] = None) -> int:
        """Crea un nuovo nodo di memoria e lo connette al nodo precedente se esiste"""
        # Validazione metadati
        if metadata:
            if 'emotional_state' in metadata and not isinstance(metadata['emotional_state'], dict):
                raise ValueError("emotional_state deve essere un dizionario")
        
        # Se metadata contiene un timestamp, usalo, altrimenti usa l'ora corrente
        timestamp = metadata.get('timestamp', datetime.now()) if metadata else datetime.now()
        
        # Crea il nodo con il timestamp
        node = MemoryNode(content, metadata)
        node.timestamp = timestamp
        
        # Aggiungi il nodo al sistema
        node_id = node.id
        self.nodes[node_id] = node
        
        # Aggiorna le statistiche
        self.performance_stats['nodes_created'] += 1
        
        # Connetti al nodo precedente se esiste
        if self.nodes:
            # Trova il nodo più recente nel layer immediato
            immediate_nodes = [n for n in self.nodes.values() if n.layer == 'immediate']
            if immediate_nodes:
                latest_node = max(immediate_nodes, key=lambda x: x.timestamp)
                if latest_node.id != node_id:  # Non connettere il nodo a se stesso
                    self.connect_nodes(latest_node.id, node_id)
        
        # Aggiorna le connessioni tematiche
        self._update_thematic_connections(node_id)
        
        # Aggiorna i pattern
        self._update_contextual_patterns(node)
        self._update_emotional_patterns(node)
        
        return node_id
        
    def get_node(self, node_id: int) -> MemoryNode:
        """Recupera un nodo di memoria per ID"""
        if node_id not in self.nodes:
            raise KeyError(f"Nodo {node_id} non trovato")
        return self.nodes[node_id]

    def connect_nodes(self, node_id1: int, node_id2: int) -> bool:
        """Crea una connessione bidirezionale tra due nodi"""
        # Verifica che entrambi i nodi esistano
        if node_id1 not in self.nodes:
            raise ValueError(f"Il nodo con ID {node_id1} non esiste")
        if node_id2 not in self.nodes:
            raise ValueError(f"Il nodo con ID {node_id2} non esiste")
        
        # Ottieni i nodi
        node1 = self.nodes[node_id1]
        node2 = self.nodes[node_id2]
        
        # Aggiungi le connessioni in entrambe le direzioni
        node1.connections.add(node_id2)
        node2.connections.add(node_id1)
        
        # Aggiorna le statistiche
        self.performance_stats['connections_created'] += 1
        
        return True

    def get_connections(self, node_id: int) -> Set[int]:
        """Recupera gli ID dei nodi connessi a un dato nodo"""
        if node_id not in self.nodes:
            raise ValueError("Il nodo specificato non esiste")
        
        return self.nodes[node_id].connections
        
    def search_by_content(self, query: str, limit: int = 10) -> List[MemoryNode]:
        """Cerca nodi di memoria basandosi sul contenuto"""
        # Implementazione base: cerca corrispondenze esatte
        matches = []
        for node in self.nodes.values():
            if query.lower() in node.content.lower():
                matches.append(node)
                if len(matches) >= limit:
                    break
                    
        self.performance_stats['successful_retrievals'] += len(matches)
        return matches
        
    def search_by_metadata(self, metadata_query: Dict[str, Any], limit: int = 10) -> List[MemoryNode]:
        """Cerca nodi di memoria basandosi sui metadati"""
        matches = []
        for node in self.nodes.values():
            match = True
            for key, value in metadata_query.items():
                # Cerca ricorsivamente nei metadati annidati
                node_value = None
                for meta_key, meta_value in node.metadata.items():
                    if isinstance(meta_value, dict) and key in meta_value:
                        node_value = meta_value[key]
                    elif meta_key == key:
                        node_value = meta_value
                
                if node_value != value:
                    match = False
                    break
                    
            if match:
                matches.append(node)
                if len(matches) >= limit:
                    break
                    
        self.performance_stats['successful_retrievals'] += len(matches)
        return matches
        
    def get_recent_nodes(self, limit: int = 10) -> List[MemoryNode]:
        """Recupera i nodi più recenti"""
        sorted_nodes = sorted(
            self.nodes.values(),
            key=lambda x: x.timestamp,
            reverse=True
        )
        return sorted_nodes[:limit]
        
    def get_performance_stats(self) -> Dict[str, int]:
        """Restituisce le statistiche di performance del sistema"""
        return self.performance_stats.copy()
        
    def clear(self) -> None:
        """Cancella tutti i nodi di memoria"""
        self.nodes.clear()
        self.performance_stats = {
            'nodes_created': 0,
            'connections_created': 0,
            'successful_retrievals': 0
        }
        
    def get_relevant_memories(self, context: Dict[str, Any], time_frame: str = 'immediate') -> List[MemoryNode]:
        """Recupera memorie rilevanti basate sul contesto e sul timeframe"""
        # Implementazione base: restituisce le memorie più recenti
        nodes = self.get_recent_nodes(limit=5)
        
        # Calcola la rilevanza per ogni nodo
        node_relevance = []
        for node in nodes:
            relevance = self._calculate_relevance(node, context)
            node_relevance.append((node, relevance))
            
        # Ordina per rilevanza
        node_relevance.sort(key=lambda x: x[1], reverse=True)
        
        # Restituisce solo i nodi, senza i punteggi di rilevanza
        return [node for node, _ in node_relevance]
        
    def _calculate_relevance(self, node: MemoryNode, context: Dict[str, Any]) -> float:
        """Calcola la rilevanza di un nodo rispetto al contesto corrente"""
        relevance = 0.0
        
        # Fattore temporale: le memorie più recenti sono più rilevanti
        time_diff = (datetime.now() - node.timestamp).total_seconds()
        time_factor = 1.0 / (1.0 + time_diff / 3600.0)  # Decadimento esponenziale
        relevance += 0.3 * time_factor
        
        # Fattore emotivo: se presente nel contesto
        if 'emotional_state' in context:
            context_emotion = context['emotional_state'].get('primary_emotion', '')
            node_emotion = node.metadata.get('emotional_state', {}).get('primary_emotion', '')
            if context_emotion == node_emotion:
                relevance += 0.3
                
        # Fattore topic: se presente nel contesto
        if 'topics' in context:
            context_topics = set(context['topics'])
            node_topics = set(node.metadata.get('topics', []))
            common_topics = context_topics.intersection(node_topics)
            if common_topics:
                relevance += 0.4 * (len(common_topics) / max(len(context_topics), 1))
                
        return min(relevance, 1.0)

    def add_memory(self, content: str, context: Dict[str, Any], emotional_state: Dict[str, Any], importance: float = 0.5) -> MemoryNode:
        """Aggiunge un nuovo nodo di memoria e crea le connessioni appropriate"""
        # Crea il nuovo nodo
        metadata = {
            'context': context,
            'emotional_state': emotional_state,
            'importance': importance,
            'created_at': datetime.now().isoformat()
        }
        new_node = MemoryNode(content, metadata)
        
        # Aggiungi il nodo al dizionario
        self.nodes[new_node.id] = new_node
        self.performance_stats['nodes_created'] += 1
        
        # Trova i nodi più recenti dello stesso layer per creare connessioni sequenziali
        recent_nodes = sorted(
            [n for n in self.nodes.values() if n.layer == new_node.layer],
            key=lambda x: x.timestamp,
            reverse=True
        )[:5]  # Prendi i 5 nodi più recenti
        
        # Crea connessioni con i nodi recenti
        for node in recent_nodes:
            if self.connect_nodes(new_node.id, node.id):  # connect_nodes incrementa già connections_created
                # Aggiorna la mappa tematica
                topics = context.get('topics', [])
                for topic in topics:
                    if topic not in self.thematic_map:
                        self.thematic_map[topic] = []
                    self.thematic_map[topic].append(new_node.id)
        
        # Aggiorna i pattern emotivi
        emotion = emotional_state.get('primary_emotion', 'neutral')
        if emotion not in self.emotional_patterns:
            self.emotional_patterns[emotion] = []
        self.emotional_patterns[emotion].append(emotional_state.get('intensity', 0.5))
        
        return new_node

    def get_emotional_insights(self) -> Dict[str, Any]:
        """Analizza i pattern emotivi dalle memorie"""
        insights = {
            'dominant_emotions': {},
            'emotion_progression': [],
            'emotional_stability': 0.0
        }
        
        # Se non ci sono nodi, restituisci insights vuoti
        if not self.nodes:
            return insights
            
        # Analizza le emozioni in tutti i nodi
        emotions = []
        for node in self.nodes.values():
            emotional_state = node.metadata.get('emotional_state', {})
            if emotional_state:
                emotion = emotional_state.get('primary_emotion', '')
                if emotion:
                    emotions.append(emotion)
                    # Aggiorna il conteggio delle emozioni dominanti
                    insights['dominant_emotions'][emotion] = insights['dominant_emotions'].get(emotion, 0) + 1
        
        # Ordina le emozioni dominanti
        insights['dominant_emotions'] = dict(
            sorted(insights['dominant_emotions'].items(), 
                  key=lambda x: x[1], 
                  reverse=True)
        )
        
        # Calcola la progressione emotiva (ultimi 5 nodi)
        recent_nodes = sorted(self.nodes.values(), key=lambda x: x.metadata.get('timestamp', ''), reverse=True)[:5]
        for node in recent_nodes:
            emotional_state = node.metadata.get('emotional_state', {})
            if emotional_state:
                insights['emotion_progression'].append({
                    'emotion': emotional_state.get('primary_emotion', ''),
                    'intensity': emotional_state.get('intensity', 0.0),
                    'timestamp': node.metadata.get('timestamp', '')
                })
        
        # Calcola la stabilità emotiva (varianza delle intensità)
        if len(emotions) > 1:
            intensities = [node.metadata.get('emotional_state', {}).get('intensity', 0.0) 
                         for node in self.nodes.values()]
            if intensities:
                mean_intensity = sum(intensities) / len(intensities)
                variance = sum((x - mean_intensity) ** 2 for x in intensities) / len(intensities)
                insights['emotional_stability'] = 1.0 / (1.0 + variance)  # Normalizza tra 0 e 1
        
        return insights

    def get_memory_stats(self) -> Dict[str, Any]:
        """Ottiene statistiche dettagliate sul sistema di memoria"""
        # Calcola l'utilizzo della memoria
        total_size = sum(len(node.content) for node in self.nodes.values())
        max_size = 1000000  # 1MB
        memory_usage = total_size / max_size
        
        # Calcola la salute del sistema
        memory_health = 1.0
        if memory_usage > 0.7:  # compression_threshold
            memory_health *= 0.8
        if memory_usage > 0.85:  # archive_threshold
            memory_health *= 0.6
        if memory_usage > 0.95:  # cleanup_threshold
            memory_health *= 0.4
        
        # Conta i nodi per layer
        immediate_nodes = [n for n in self.nodes.values() if n.layer == 'immediate']
        short_term_nodes = [n for n in self.nodes.values() if n.layer == 'short_term']
        long_term_nodes = [n for n in self.nodes.values() if n.layer == 'long_term']
        
        # Calcola l'intensità emotiva media
        total_intensity = 0
        nodes_with_emotions = 0
        for node in self.nodes.values():
            if hasattr(node, 'emotional_state') and node.emotional_state:
                total_intensity += node.emotional_state.get('intensity', 0)
                nodes_with_emotions += 1
        avg_emotional_intensity = total_intensity / nodes_with_emotions if nodes_with_emotions > 0 else 0
        
        # Prepara le statistiche di base
        stats = {
            'total_nodes': len(self.nodes),
            'immediate_count': len(immediate_nodes),
            'short_term_count': len(short_term_nodes),
            'long_term_count': len(long_term_nodes),
            'memory_usage': memory_usage,
            'memory_health': memory_health,
            'avg_emotional_intensity': avg_emotional_intensity,
            'average_importance': sum(n.metadata.get('importance', 0.5) for n in self.nodes.values()) / len(self.nodes) if self.nodes else 0.0,
            'emotional_distribution': {},
            'topic_distribution': {},
            **self.performance_stats,  # Includi tutte le statistiche di performance
            'connections_made': self.performance_stats['connections_created']  # Alias per retrocompatibilità
        }
        
        # Calcola distribuzione emotiva
        for node in self.nodes.values():
            emotion = node.emotional_state.get('primary_emotion')
            if emotion:
                stats['emotional_distribution'][emotion] = \
                    stats['emotional_distribution'].get(emotion, 0) + 1
        
        # Calcola distribuzione dei topic
        for topic, nodes in self.thematic_map.items():
            stats['topic_distribution'][topic] = len(nodes)
        
        return stats

    def consolidate_long_term_memories(self, retention_threshold: float = 0.6):
        """Consolida le memorie a lungo termine, rimuovendo quelle meno importanti"""
        long_term_nodes = [
            node_id for node_id, node in self.nodes.items()
            if node.layer == 'long_term'
        ]
        
        for node_id in long_term_nodes:
            node = self.nodes[node_id]
            importance = node.metadata.get('importance', 0.0)
            
            if importance <= retention_threshold:  
                # Rimuovi il nodo
                del self.nodes[node_id]
                
                # Rimuovi dalle connessioni
                for other_node in self.nodes.values():
                    if node_id in other_node.connections:
                        other_node.connections.remove(node_id)
                
                # Rimuovi dalla mappa tematica
                for topic_nodes in self.thematic_map.values():
                    if node_id in topic_nodes:
                        topic_nodes.remove(node_id)

    def get_dominant_patterns(self) -> Dict[str, Any]:
        """Recupera i pattern dominanti dal sistema di memoria"""
        patterns = {
            'peak_hours': [],
            'dominant_emotions': [],
            'common_topics': []
        }
        
        # Analizza pattern temporali
        if 'time_patterns' in self.contextual_patterns:
            hourly = self.contextual_patterns['time_patterns']['hourly']
            print(f"\nDebug - Pattern orari: {hourly}")  # Debug
            if any(hourly):  # Se ci sono valori maggiori di 0
                max_count = max(hourly)
                print(f"Debug - Conteggio massimo: {max_count}")  # Debug
                # Trova tutte le ore con il conteggio massimo
                patterns['peak_hours'] = [
                    hour for hour in range(len(hourly))
                    if hourly[hour] == max_count
                ]
                patterns['peak_hours'].sort()  # Ordina le ore per coerenza
                print(f"Debug - Ore di picco: {patterns['peak_hours']}")  # Debug
        
        # Analizza pattern emotivi
        emotion_counts = {}
        for node in self.nodes.values():
            emotion = node.emotional_state.get('primary_emotion')
            if emotion:
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        if emotion_counts:
            max_count = max(emotion_counts.values())
            patterns['dominant_emotions'] = [
                emotion for emotion, count in emotion_counts.items()
                if count == max_count
            ]
            patterns['dominant_emotions'].sort()  # Ordina le emozioni per coerenza
        
        # Analizza topic comuni
        topic_counts = {}
        for topic, nodes in self.thematic_map.items():
            topic_counts[topic] = len(nodes)
        
        if topic_counts:
            max_count = max(topic_counts.values())
            patterns['common_topics'] = [
                topic for topic, count in topic_counts.items()
                if count == max_count
            ]
            patterns['common_topics'].sort()  # Ordina i topic per coerenza
        
        return patterns
