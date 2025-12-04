"""
Test di resilienza del sistema di apprendimento incrementale.
Verifica il comportamento del sistema in condizioni di stress:
- Test di carico con grandi volumi di dati
- Test di sicurezza con input malevoli
- Test di persistenza dello stato
"""

import unittest
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List
import random
import string
import tempfile

from .perception_system import PerceptionSystem, InputType
from .metacognition_system import MetaCognitionSystem
from .emotional_system import EmotionalSystem, EmotionType
from .communication_system import CommunicationSystem, CommunicationMode
from .cognitive_evolution_system import CognitiveEvolutionSystem
from .memory_system import ShortTermMemory, MemoryItem

class SystemStateEncoder(json.JSONEncoder):
    """Encoder personalizzato per la serializzazione degli stati del sistema"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, timedelta):
            return obj.total_seconds()
        elif isinstance(obj, (EmotionType, InputType, CommunicationMode)):
            return obj.value
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        elif hasattr(obj, 'qsize'):  # Per PriorityQueue
            items = []
            while not obj.empty():
                items.append(obj.get())
            return items
        return super().default(obj)

class SystemStateDecoder(json.JSONDecoder):
    """Decoder personalizzato per la deserializzazione degli stati del sistema"""
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)
        
    def object_hook(self, dct):
        if 'timestamp' in dct:
            dct['timestamp'] = datetime.fromisoformat(dct['timestamp'])
        if 'last_recall' in dct:
            dct['last_recall'] = datetime.fromisoformat(dct['last_recall'])
        return dct

class TestSystemResilience(unittest.TestCase):
    def setUp(self):
        """Inizializza i sistemi per ogni test"""
        self.perception = PerceptionSystem()
        self.metacognition = MetaCognitionSystem()
        self.emotional = EmotionalSystem()
        self.communication = CommunicationSystem()
        self.evolution = CognitiveEvolutionSystem()
        self.memory = ShortTermMemory()
        
    def test_load_stress(self):
        """Test di carico con grandi volumi di dati"""
        print("\n=== Test di Carico ===")
        
        # Genera un grande volume di dati di test
        num_items = 1000
        test_data = []
        for i in range(num_items):
            text = f"Test input {i} con contenuto casuale: {self._generate_random_text(50)}"
            test_data.append(text)
            
        start_time = time.time()
        memory_usage_start = self._get_memory_usage()
        
        # Processa tutti i dati
        for text in test_data:
            # Test percezione
            percept = self.perception.process_input(text, InputType.TEXT)
            
            # Test memoria
            self.memory.add_item(MemoryItem(
                content=text,
                timestamp=datetime.now(),
                importance=random.random(),
                emotional_valence=random.uniform(-1.0, 1.0),
                associations=[],
                recall_count=0,
                last_recall=datetime.now()
            ))
            
            # Test emozione
            emotion = self.emotional.process_stimulus(text, valence=random.uniform(-1.0, 1.0))
            
            # Test comunicazione
            response = self.communication.generate_response(
                input_text=text,
                emotion=emotion,
                mode=CommunicationMode.NATURAL
            )
            
            # Test evoluzione cognitiva
            self.evolution.process_experience({
                "input": text,
                "percept": percept,
                "emotion": emotion,
                "response": response
            })
            
        end_time = time.time()
        memory_usage_end = self._get_memory_usage()
        
        processing_time = end_time - start_time
        memory_increase = memory_usage_end - memory_usage_start
        
        print(f"Tempo di elaborazione totale: {processing_time:.2f} secondi")
        print(f"Tempo medio per item: {(processing_time/num_items)*1000:.2f} ms")
        print(f"Incremento memoria: {memory_increase/1024/1024:.2f} MB")
        
        # Verifica le performance
        self.assertLess(processing_time/num_items, 0.1, "Elaborazione troppo lenta")
        self.assertLess(memory_increase/1024/1024, 100, "Consumo di memoria eccessivo")
        
    def test_security(self):
        """Test di sicurezza con input malevoli"""
        print("\n=== Test di Sicurezza ===")
        
        malicious_inputs = [
            None,  # Input nullo
            "",    # Stringa vuota
            "A" * 1000000,  # Stringa molto lunga
            "SELECT * FROM users",  # SQL injection
            "<script>alert('xss')</script>",  # XSS
            "../../../etc/passwd",  # Path traversal
            "rm -rf /",  # Comando pericoloso
            "ñöǹ-ȂŞĈİİ",  # Caratteri non ASCII
            "🌟 💣 💥",    # Emoji
            "\x00\x01\x02\x03",  # Caratteri di controllo
        ]
        
        for input_text in malicious_inputs:
            print(f"\nTestando input malevolo: {input_text}")
            
            try:
                # Test percezione
                percept = self.perception.process_input(input_text, InputType.TEXT)
                print("Percezione OK")
            except Exception as e:
                print(f"Percezione gestita: {str(e)}")
                
            try:
                # Test memoria
                self.memory.add_item(MemoryItem(
                    content=input_text,
                    timestamp=datetime.now(),
                    importance=random.random(),
                    emotional_valence=random.uniform(-1.0, 1.0),
                    associations=[],
                    recall_count=0,
                    last_recall=datetime.now()
                ))
                print("Memoria OK")
            except Exception as e:
                print(f"Memoria gestita: {str(e)}")
                
            try:
                # Test emozione
                emotion = self.emotional.process_stimulus(input_text, valence=0.0)
                print("Emozione OK")
            except Exception as e:
                print(f"Emozione gestita: {str(e)}")
                
            try:
                # Test comunicazione
                response = self.communication.generate_response(
                    input_text=input_text,
                    emotion=emotion if 'emotion' in locals() else None,
                    mode=CommunicationMode.NATURAL
                )
                print("Comunicazione OK")
            except Exception as e:
                print(f"Comunicazione gestita: {str(e)}")
                
    def test_persistence(self):
        """Test di persistenza dello stato"""
        print("\n=== Test di Persistenza ===")
        
        # Crea un file temporaneo per il salvataggio
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            
        try:
            # Genera alcuni dati di test
            test_data = [
                "Questo è un test di apprendimento",
                "Il sistema deve ricordare questi dati",
                "Anche dopo il riavvio"
            ]
            
            # Processa i dati
            for text in test_data:
                percept = self.perception.process_input(text, InputType.TEXT)
                emotion = self.emotional.process_stimulus(text, valence=0.5)
                self.memory.add_item(MemoryItem(
                    content=text,
                    timestamp=datetime.now(),
                    importance=random.random(),
                    emotional_valence=random.uniform(-1.0, 1.0),
                    associations=[],
                    recall_count=0,
                    last_recall=datetime.now()
                ))
            
            # Salva lo stato di ogni sistema
            state = {
                "memory_items": [
                    {
                        "content": item.content,
                        "timestamp": item.timestamp.isoformat(),
                        "importance": item.importance,
                        "emotional_valence": item.emotional_valence,
                        "associations": item.associations,
                        "recall_count": item.recall_count,
                        "last_recall": item.last_recall.isoformat()
                    }
                    for item in self.memory.items
                ],
                "memory_retention_time": self.memory.retention_time.total_seconds(),
                "emotional_state": self.emotional.current_state,
                "cognitive_abilities": self.evolution.cognitive_abilities
            }
            
            # Salva lo stato
            with open(temp_path, 'w') as f:
                json.dump(state, f)
                
            # Ricrea i sistemi
            self.setUp()
            
            # Carica lo stato
            with open(temp_path, 'r') as f:
                loaded_state = json.load(f)
            
            # Ripristina lo stato
            # Ripristina gli item della memoria
            for item_data in loaded_state["memory_items"]:
                item_data["timestamp"] = datetime.fromisoformat(item_data["timestamp"])
                item_data["last_recall"] = datetime.fromisoformat(item_data["last_recall"])
                self.memory.add_item(MemoryItem(**item_data))
            
            # Ripristina il retention time
            self.memory.retention_time = timedelta(seconds=loaded_state["memory_retention_time"])
            
            # Ripristina lo stato emotivo
            self.emotional.current_state = loaded_state["emotional_state"]
            
            # Ripristina le abilità cognitive
            self.evolution.cognitive_abilities = loaded_state["cognitive_abilities"]
            
            # Verifica che i dati siano stati mantenuti
            recent_items = self.memory.get_recent_items()
            self.assertEqual(len(recent_items), len(test_data))
            for item, text in zip(recent_items, reversed(test_data)):
                self.assertEqual(item.content, text)
                
        finally:
            # Pulizia
            os.unlink(temp_path)
            
    def _generate_random_text(self, length: int) -> str:
        """Genera una stringa casuale della lunghezza specificata"""
        return ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=length))
        
    def _get_memory_usage(self) -> int:
        """Ottiene l'utilizzo corrente della memoria in bytes"""
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss

if __name__ == '__main__':
    unittest.main()
