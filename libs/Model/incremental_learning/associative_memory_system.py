"""
Sistema di Memoria Associativa
Simula la capacità del cervello di creare, memorizzare e recuperare connessioni tra concetti ed esperienze
"""

from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from collections import defaultdict
import heapq

@dataclass(frozen=True)  # Rende la classe immutabile e quindi hashable
class MemoryNodeId:
    """Identificatore univoco per un nodo di memoria"""
    content: Any
    creation_time: datetime

@dataclass
class MemoryNode:
    """Rappresenta un nodo nella rete di memoria associativa"""
    id: MemoryNodeId
    content: Any
    creation_time: datetime
    last_access: datetime
    access_count: int = 0
    strength: float = 1.0  # Forza della memoria (1.0 = massima, 0.0 = dimenticata)
    tags: Set[str] = field(default_factory=set)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def decay(self, current_time: datetime, decay_rate: float = 0.1) -> None:
        """
        Simula il decadimento naturale della memoria nel tempo,
        come accade nel cervello umano
        """
        time_diff = (current_time - self.last_access).total_seconds()
        decay = np.exp(-decay_rate * time_diff / (24 * 3600))  # Normalizza a giorni
        self.strength *= decay
        
    def reinforce(self, boost: float = 0.1) -> None:
        """
        Rinforza la memoria attraverso il richiamo,
        simulando il consolidamento della memoria
        """
        self.strength = min(1.0, self.strength + boost)
        self.access_count += 1
        self.last_access = datetime.now()

@dataclass
class Association:
    """Rappresenta una connessione tra due nodi di memoria"""
    source_id: MemoryNodeId
    target_id: MemoryNodeId
    strength: float = 0.5
    type: str = "generic"
    context: Dict[str, Any] = field(default_factory=dict)
    creation_time: datetime = field(default_factory=datetime.now)
    
    def strengthen(self, amount: float = 0.1) -> None:
        """Rafforza l'associazione"""
        self.strength = min(1.0, self.strength + amount)
        
    def weaken(self, amount: float = 0.1) -> None:
        """Indebolisce l'associazione"""
        self.strength = max(0.0, self.strength - amount)

class AssociativeMemorySystem:
    def __init__(self):
        """
        Inizializza il sistema di memoria associativa,
        simile a come il cervello organizza le informazioni
        """
        self.nodes: Dict[MemoryNodeId, MemoryNode] = {}
        self.content_to_id: Dict[Any, MemoryNodeId] = {}
        self.associations: Dict[Tuple[MemoryNodeId, MemoryNodeId], Association] = {}
        self.tag_index: Dict[str, Set[MemoryNodeId]] = defaultdict(set)
        self.context_index: Dict[str, Dict[Any, Set[MemoryNodeId]]] = defaultdict(lambda: defaultdict(set))
        
        # Parametri di sistema
        self.decay_rate = 0.1
        self.reinforcement_boost = 0.2
        self.association_threshold = 0.3
        self.forgetting_threshold = 0.1
        
    def create_memory(self, content: Any, tags: Set[str] = None, 
                     context: Dict[str, Any] = None) -> MemoryNode:
        """
        Crea un nuovo nodo di memoria, come il cervello che forma
        un nuovo ricordo o apprende un nuovo concetto
        """
        if content in self.content_to_id:
            node_id = self.content_to_id[content]
            node = self.nodes[node_id]
            node.reinforce(self.reinforcement_boost)
            return node
            
        # Crea un nuovo ID per il nodo
        node_id = MemoryNodeId(content=content, creation_time=datetime.now())
        
        node = MemoryNode(
            id=node_id,
            content=content,
            creation_time=datetime.now(),
            last_access=datetime.now(),
            tags=tags or set(),
            context=context or {}
        )
        
        self.nodes[node_id] = node
        self.content_to_id[content] = node_id
        
        # Indicizza per tag e contesto
        for tag in node.tags:
            self.tag_index[tag].add(node_id)
            
        for context_type, context_value in node.context.items():
            self.context_index[context_type][context_value].add(node_id)
            
        return node
        
    def create_association(self, source: Any, target: Any, 
                         type: str = "generic", strength: float = 0.5,
                         context: Dict[str, Any] = None) -> Association:
        """
        Crea una nuova associazione tra due nodi di memoria,
        simulando come il cervello collega concetti correlati
        """
        # Assicurati che entrambi i nodi esistano
        source_node = self.create_memory(source)
        target_node = self.create_memory(target)
        
        # Crea o aggiorna l'associazione
        key = (source_node.id, target_node.id)
        if key in self.associations:
            assoc = self.associations[key]
            assoc.strengthen(self.reinforcement_boost)
            return assoc
            
        assoc = Association(
            source_id=source_node.id,
            target_id=target_node.id,
            strength=strength,
            type=type,
            context=context or {}
        )
        
        self.associations[key] = assoc
        return assoc
        
    def recall(self, content: Any, strengthen: bool = True) -> Optional[MemoryNode]:
        """
        Recupera un ricordo specifico, simulando il processo
        di richiamo della memoria
        """
        if content not in self.content_to_id:
            return None
            
        node_id = self.content_to_id[content]
        node = self.nodes[node_id]
        
        if strengthen:
            node.reinforce(self.reinforcement_boost)
            
        return node
        
    def find_associations(self, content: Any, min_strength: float = 0.3) -> List[Association]:
        """
        Trova tutte le associazioni collegate a un contenuto,
        come il cervello che recupera concetti correlati
        """
        if content not in self.content_to_id:
            return []
            
        node_id = self.content_to_id[content]
        associations = []
        
        for key, assoc in self.associations.items():
            if (key[0] == node_id or key[1] == node_id) and assoc.strength >= min_strength:
                associations.append(assoc)
                
        return sorted(associations, key=lambda x: x.strength, reverse=True)
        
    def find_by_tags(self, tags: Set[str], require_all: bool = False) -> List[MemoryNode]:
        """
        Cerca memorie per tag, simulando il recupero
        di ricordi per categoria
        """
        if not tags:
            return []
            
        if require_all:
            node_ids = set.intersection(*[self.tag_index[tag] for tag in tags])
        else:
            node_ids = set.union(*[self.tag_index[tag] for tag in tags])
            
        nodes = [self.nodes[node_id] for node_id in node_ids]
        return sorted(nodes, key=lambda x: x.strength, reverse=True)
        
    def find_by_context(self, context_type: str, context_value: Any) -> List[MemoryNode]:
        """
        Cerca memorie per contesto, simulando il recupero
        di ricordi basato sul contesto
        """
        node_ids = self.context_index[context_type][context_value]
        nodes = [self.nodes[node_id] for node_id in node_ids]
        return sorted(nodes, key=lambda x: x.strength, reverse=True)
        
    def spread_activation(self, start_content: Any, depth: int = 2) -> List[Tuple[MemoryNode, float]]:
        """
        Implementa la diffusione dell'attivazione nella rete di memoria,
        simulando come il cervello attiva concetti correlati
        """
        if start_content not in self.content_to_id:
            return []
            
        start_id = self.content_to_id[start_content]
        
        activation = defaultdict(float)
        activation[start_id] = 1.0
        visited = {start_id}
        current_depth = 0
        
        while current_depth < depth:
            new_activation = defaultdict(float)
            
            for node_id, act_value in activation.items():
                for key, assoc in self.associations.items():
                    if key[0] == node_id:
                        target_id = key[1]
                    elif key[1] == node_id:
                        target_id = key[0]
                    else:
                        continue
                        
                    if target_id not in visited:
                        new_activation[target_id] += act_value * assoc.strength
                        visited.add(target_id)
                        
            activation.update(new_activation)
            current_depth += 1
            
        # Converti in lista e ordina per attivazione
        result = [(self.nodes[node_id], value) for node_id, value in activation.items()]
        return sorted(result, key=lambda x: x[1], reverse=True)
        
    def consolidate_memories(self) -> None:
        """
        Consolida le memorie, simulando il processo che avviene
        durante il sonno nel cervello
        """
        current_time = datetime.now()
        
        # Applica decadimento naturale
        for node in list(self.nodes.values()):
            node.decay(current_time, self.decay_rate)
            
            # Rimuovi memorie troppo deboli
            if node.strength < self.forgetting_threshold:
                self._forget_node(node)
                
        # Rafforza associazioni frequentemente utilizzate
        for assoc in list(self.associations.values()):
            source_node = self.nodes[assoc.source_id]
            target_node = self.nodes[assoc.target_id]
            
            if source_node.access_count > 0 and target_node.access_count > 0:
                assoc.strengthen(0.05)
            else:
                assoc.weaken(0.1)
                
            # Rimuovi associazioni troppo deboli
            if assoc.strength < self.association_threshold:
                self._forget_association(assoc)
                
    def _forget_node(self, node: MemoryNode) -> None:
        """Rimuove un nodo e tutte le sue associazioni"""
        # Rimuovi dai tag index
        for tag in node.tags:
            self.tag_index[tag].discard(node.id)
            
        # Rimuovi dal context index
        for context_type, context_value in node.context.items():
            self.context_index[context_type][context_value].discard(node.id)
            
        # Rimuovi tutte le associazioni
        for key in list(self.associations.keys()):
            if node.id in key:
                del self.associations[key]
                
        # Rimuovi il nodo
        del self.nodes[node.id]
        del self.content_to_id[node.content]
        
    def _forget_association(self, assoc: Association) -> None:
        """Rimuove un'associazione"""
        key = (assoc.source_id, assoc.target_id)
        if key in self.associations:
            del self.associations[key]
