"""
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending - ALLMA (Adaptive Learning and Language Model Architecture)

This file implements the Memory Management System of ALLMA.
Author: Cristof Bano
Created: January 2025

This file contains proprietary and patent-pending technologies including:
- Dynamic memory compression
- Selective data archival
- Optimized retrieval systems
- Automatic cleanup algorithms
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import time
import json
import hashlib
from collections import defaultdict
import logging
from threading import Lock

@dataclass
class MemoryItem:
    content: Any
    timestamp: float
    access_count: int
    last_access: float
    importance_score: float
    category: str
    compressed: bool = False
    
class MemoryCache:
    def __init__(self, max_size_mb: int = 100):
        self.max_size = max_size_mb * 1024 * 1024  # Converti in bytes
        self.current_size = 0
        self.cache = {}
        self.access_history = defaultdict(int)

class MemoryManager:
    def __init__(self):
        self.active_memory = MemoryCache(max_size_mb=100)  # Memoria attiva
        self.archive_memory = MemoryCache(max_size_mb=500)  # Archivio
        self.memory_lock = Lock()
        
        # Soglie di gestione memoria
        self.compression_threshold = 0.7  # 70% di utilizzo
        self.archive_threshold = 0.85     # 85% di utilizzo
        self.cleanup_threshold = 0.95     # 95% di utilizzo
        
        # Statistiche di memoria
        self.stats = {
            "total_items": 0,
            "compressed_items": 0,
            "archived_items": 0,
            "memory_usage": 0.0
        }

    def calculate_importance(self, item: MemoryItem) -> float:
        """Calcola l'importanza di un item in memoria"""
        # Fattori di importanza
        recency_weight = 0.4
        access_weight = 0.3
        score_weight = 0.3
        
        # Calcola il fattore di recency (quanto è recente l'ultimo accesso)
        current_time = time.time()
        time_since_access = current_time - item.last_access
        recency_factor = 1.0 / (1.0 + time_since_access / 3600)  # Normalizza per ore
        
        # Calcola il fattore di accesso (quanto spesso viene acceduto)
        access_factor = min(1.0, item.access_count / 10.0)  # Normalizza per 10 accessi
        
        # Usa lo score esistente come terzo fattore
        score_factor = item.importance_score
        
        # Calcola l'importanza totale
        importance = (recency_weight * recency_factor +
                     access_weight * access_factor +
                     score_weight * score_factor)
        
        return min(1.0, max(0.0, importance))

    def compress_item(self, item: MemoryItem) -> MemoryItem:
        """Comprime un item in memoria"""
        if isinstance(item.content, dict):
            # Rimuovi le chiavi non essenziali
            compressed_content = {
                k: v for k, v in item.content.items()
                if k.startswith("essential_")
            }
        else:
            # Se non è un dizionario, prendi solo i primi 100 caratteri
            compressed_content = str(item.content)[:100]
        
        # Crea un nuovo item compresso
        compressed_item = MemoryItem(
            content=compressed_content,
            timestamp=item.timestamp,
            access_count=item.access_count,
            last_access=item.last_access,
            importance_score=item.importance_score,
            category=item.category,
            compressed=True
        )
        
        # Aggiorna le dimensioni della memoria
        self.active_memory.current_size = int(self.active_memory.current_size * 0.7)
        
        return compressed_item

    def store_item(self, content: Any, category: str = "general") -> str:
        """Memorizza un nuovo item"""
        with self.memory_lock:
            # Genera ID univoco
            item_id = hashlib.md5(str(content).encode()).hexdigest()
            
            # Crea nuovo item
            new_item = MemoryItem(
                content=content,
                timestamp=time.time(),
                access_count=0,
                last_access=time.time(),
                importance_score=0.5,  # Score iniziale
                category=category
            )
            
            # Gestisci spazio in memoria
            self._manage_memory_space()
            
            # Memorizza l'item
            self.active_memory.cache[item_id] = new_item
            self.stats["total_items"] += 1
            
            return item_id

    def retrieve_item(self, item_id: str) -> Optional[Any]:
        """Recupera un item dalla memoria"""
        with self.memory_lock:
            # Cerca prima in memoria attiva
            if item_id in self.active_memory.cache:
                item = self.active_memory.cache[item_id]
                self._update_access_stats(item)
                return item.content
                
            # Cerca in archivio
            if item_id in self.archive_memory.cache:
                item = self.archive_memory.cache[item_id]
                # Sposta in memoria attiva se importante
                if self.calculate_importance(item) > 0.7:
                    self._promote_to_active(item_id)
                self._update_access_stats(item)
                return item.content
                
            return None

    def _update_access_stats(self, item: MemoryItem):
        """Aggiorna le statistiche di accesso"""
        item.access_count += 1
        item.last_access = time.time()
        item.importance_score = self.calculate_importance(item)

    def _manage_memory_space(self):
        """Gestisce lo spazio in memoria"""
        memory_usage = self.active_memory.current_size / self.active_memory.max_size
        self.stats["memory_usage"] = memory_usage
        
        if memory_usage > self.cleanup_threshold:
            self._perform_cleanup()
        elif memory_usage > self.archive_threshold:
            self._archive_items()
        elif memory_usage > self.compression_threshold:
            self._compress_items()

    def _compress_items(self):
        """Comprime gli item meno importanti"""
        with self.memory_lock:
            # Ordina gli item per importanza
            items = [(item_id, item) for item_id, item in self.active_memory.cache.items()]
            items.sort(key=lambda x: self.calculate_importance(x[1]))
            
            # Comprimi gli item meno importanti finché non si raggiunge la soglia
            for item_id, item in items:
                if not item.compressed:
                    self.active_memory.cache[item_id] = self.compress_item(item)
                    self.stats["compressed_items"] += 1
                    
                    # Se la memoria è scesa sotto la soglia, termina
                    if self.active_memory.current_size < self.active_memory.max_size * self.compression_threshold:
                        break

    def _archive_items(self):
        """Sposta gli item meno importanti nell'archivio"""
        with self.memory_lock:
            # Ordina gli item per importanza
            items = [(item_id, item) for item_id, item in self.active_memory.cache.items()]
            items.sort(key=lambda x: self.calculate_importance(x[1]))
            
            # Sposta gli item meno importanti nell'archivio finché non si raggiunge la soglia
            for item_id, item in items:
                self._move_to_archive(item_id)
                
                # Se la memoria è scesa sotto la soglia, termina
                if self.active_memory.current_size < self.active_memory.max_size * self.archive_threshold:
                    break

    def _move_to_archive(self, item_id: str):
        """Sposta un item nell'archivio"""
        if item_id in self.active_memory.cache:
            item = self.active_memory.cache.pop(item_id)
            self.archive_memory.cache[item_id] = item
            self.stats["archived_items"] += 1
            
            # Riduci la dimensione della memoria attiva
            self.active_memory.current_size = int(self.active_memory.current_size * 0.7)

    def _promote_to_active(self, item_id: str):
        """Promuove un item dall'archivio alla memoria attiva"""
        if item_id in self.archive_memory.cache:
            item = self.archive_memory.cache.pop(item_id)
            self.active_memory.cache[item_id] = item
            self.stats["archived_items"] -= 1

    def _perform_cleanup(self):
        """Pulizia della memoria quando necessario"""
        # Rimuovi gli item meno importanti dall'archivio
        items_to_remove = []
        for item_id, item in self.archive_memory.cache.items():
            if self.calculate_importance(item) < 0.1:
                items_to_remove.append(item_id)
                
        for item_id in items_to_remove:
            del self.archive_memory.cache[item_id]
            self.stats["total_items"] -= 1

    def get_memory_stats(self):
        """Ottiene le statistiche della memoria"""
        with self.memory_lock:
            # Calcola l'utilizzo della memoria
            active_usage = self.active_memory.current_size / self.active_memory.max_size
            archive_usage = self.archive_memory.current_size / self.archive_memory.max_size
            
            # Calcola la salute del sistema
            memory_health = 1.0
            if active_usage > self.compression_threshold:
                memory_health *= 0.8
            if active_usage > self.archive_threshold:
                memory_health *= 0.6
            if active_usage > self.cleanup_threshold:
                memory_health *= 0.4
                
            return {
                "total_items": self.stats["total_items"],
                "compressed_items": self.stats["compressed_items"],
                "archived_items": self.stats["archived_items"],
                "memory_usage": active_usage,
                "archive_usage": archive_usage,
                "memory_health": memory_health,
                "immediate_count": len(self.active_memory.cache),
                "long_term_count": len(self.archive_memory.cache),
                "total_nodes": len(self.active_memory.cache) + len(self.archive_memory.cache)
            }
