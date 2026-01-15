import pytest
from allma_model.incremental_learning.memory_manager import MemoryManager, MemoryItem
from datetime import datetime
import time
import random
import string

def generate_random_content(size=10):
    """Genera contenuto casuale per i test"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=size))

class TestMemoryManager:
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup per ogni test"""
        self.memory_manager = MemoryManager()
    
    def test_initialization(self):
        """Test dell'inizializzazione del sistema"""
        assert self.memory_manager.active_memory is not None
        assert self.memory_manager.archive_memory is not None
        assert self.memory_manager.compression_threshold == 0.7
        assert self.memory_manager.archive_threshold == 0.85
        assert self.memory_manager.cleanup_threshold == 0.95
    
    def test_store_and_retrieve(self):
        """Test della memorizzazione e recupero"""
        # Memorizza un item
        content = {"test_data": "example"}
        timestamp = time.time()
        item = MemoryItem(
            content=content,
            timestamp=timestamp,
            access_count=0,
            last_access=timestamp,
            importance_score=0.5,
            category="test"
        )
        
        # Memorizza l'item
        with self.memory_manager.memory_lock:
            self.memory_manager.active_memory.cache[1] = item
        
        # Verifica che l'item sia nella memoria attiva
        assert 1 in self.memory_manager.active_memory.cache
        assert self.memory_manager.active_memory.cache[1].content == content
    
    def test_compression(self):
        """Test della compressione della memoria"""
        # Crea un item con contenuto comprimibile
        content = {"essential_data": "keep", "non_essential": "compress"}
        timestamp = time.time()
        item = MemoryItem(
            content=content,
            timestamp=timestamp,
            access_count=1,
            last_access=timestamp,
            importance_score=0.3,
            category="test"
        )
        
        # Memorizza l'item
        with self.memory_manager.memory_lock:
            self.memory_manager.active_memory.cache[1] = item
            # Simula il raggiungimento della soglia di compressione
            self.memory_manager.active_memory.current_size = int(self.memory_manager.active_memory.max_size * 0.8)
        
        # Verifica che la compressione venga attivata
        self.memory_manager._manage_memory_space()
        assert self.memory_manager.active_memory.current_size < self.memory_manager.active_memory.max_size * 0.8
    
    def test_archiving(self):
        """Test dell'archiviazione"""
        # Crea un item poco importante
        content = "archive_test"
        timestamp = time.time()
        item = MemoryItem(
            content=content,
            timestamp=timestamp,
            access_count=1,
            last_access=timestamp,
            importance_score=0.2,  # Bassa importanza
            category="test"
        )
        
        # Memorizza l'item
        with self.memory_manager.memory_lock:
            self.memory_manager.active_memory.cache[1] = item
            # Simula il raggiungimento della soglia di archiviazione
            self.memory_manager.active_memory.current_size = int(self.memory_manager.active_memory.max_size * 0.9)
        
        # Verifica che l'archiviazione venga attivata
        self.memory_manager._manage_memory_space()
        assert 1 in self.memory_manager.archive_memory.cache
        assert 1 not in self.memory_manager.active_memory.cache

if __name__ == '__main__':
    pytest.main()
