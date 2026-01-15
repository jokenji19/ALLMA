"""
Test del sistema di memoria avanzato
"""

import pytest
from datetime import datetime, timedelta
import numpy as np
from allma_model.core.memory_system.memory_types import Memory, MemoryNode, MemoryConnection, EmotionalMemory, EmotionalPattern
from allma_model.core.memory_system.memory_manager import AdvancedMemorySystem

def test_memory_creation():
    """Test della creazione base di una memoria"""
    content = "Test memory content"
    importance = 0.8
    context = {"type": "test", "source": "unit_test"}
    
    memory = Memory(
        content=content,
        importance=importance,
        timestamp=datetime.now(),
        context=context
    )
    
    assert memory.content == content
    assert memory.importance == importance
    assert isinstance(memory.embedding, np.ndarray)
    assert memory.embedding.shape == (768,)  # Dimensione standard BERT
    
def test_memory_node():
    """Test delle funzionalità del nodo di memoria"""
    memory = Memory(
        content="Test node",
        importance=0.5,
        timestamp=datetime.now(),
        context={}
    )
    
    node = MemoryNode(memory=memory)
    
    # Test accesso
    assert node.access_count == 0
    assert node.last_accessed is None
    
    node.access()
    assert node.access_count == 1
    assert node.last_accessed is not None
    
    # Test forza della memoria
    strength = node.get_strength()
    assert 0 <= strength <= 1
    
    # Test decadimento
    original_strength = node.get_strength()
    node.last_accessed = datetime.now() - timedelta(days=1)
    decayed_strength = node.get_strength()
    assert decayed_strength < original_strength

def test_memory_connection():
    """Test delle connessioni tra memorie"""
    memory1 = Memory("First memory", 0.5, datetime.now(), {})
    memory2 = Memory("Second memory", 0.5, datetime.now(), {})
    
    node1 = MemoryNode(memory1)
    node2 = MemoryNode(memory2)
    
    connection = MemoryConnection(
        target=node2,
        relationship_type="semantic",
        strength=0.8,
        created_at=datetime.now()
    )
    
    node1.connections.append(connection)
    
    assert len(node1.connections) == 1
    assert node1.connections[0].target == node2
    assert abs(node1.connections[0].strength - 0.8) < 1e-10
    
    # Test rinforzo e indebolimento
    connection.reinforce(0.1)
    assert abs(connection.strength - 0.9) < 1e-10
    
    connection.weaken(0.3)
    assert abs(connection.strength - 0.6) < 1e-10

def test_emotional_memory():
    """Test della memoria emotiva"""
    emotional_memory = EmotionalMemory(
        emotional_valence=0.8,
        emotional_arousal=0.6,
        emotional_dominance=0.7,
        emotional_tags=["joy", "excitement"]
    )
    
    vector = emotional_memory.get_emotional_vector()
    assert len(vector) == 3
    assert vector[0] == 0.8  # valence
    assert vector[1] == 0.6  # arousal
    assert vector[2] == 0.7  # dominance
    
    # Test similarità emotiva
    other_memory = EmotionalMemory(
        emotional_valence=0.7,
        emotional_arousal=0.5,
        emotional_dominance=0.6,
        emotional_tags=["joy"]
    )
    
    similarity = emotional_memory.calculate_emotional_similarity(other_memory)
    assert 0 <= similarity <= 1

def test_emotional_pattern():
    """Test dei pattern emotivi"""
    pattern = EmotionalPattern()
    
    # Aggiungi alcuni stati emotivi
    emotions = [
        EmotionalMemory(emotional_valence=0.8, emotional_arousal=0.6, emotional_dominance=0.7, emotional_tags=["joy"]),
        EmotionalMemory(emotional_valence=0.7, emotional_arousal=0.5, emotional_dominance=0.6, emotional_tags=["joy"]),
        EmotionalMemory(emotional_valence=-0.6, emotional_arousal=0.8, emotional_dominance=0.3, emotional_tags=["anger"])
    ]
    
    contexts = [
        {"trigger": "good_news", "time": "morning"},
        {"trigger": "success", "time": "afternoon"},
        {"trigger": "conflict", "time": "evening"}
    ]
    
    for emotion, context in zip(emotions, contexts):
        pattern.add_emotional_state(emotion, context)
    
    # Test emozioni dominanti
    dominant = pattern.get_dominant_emotions(2)
    assert len(dominant) == 2
    assert "joy" in dominant
    
    # Test trigger
    triggers = pattern.identify_triggers()
    assert len(triggers) > 0
    assert "joy" in triggers

def test_advanced_memory_system():
    """Test del sistema di memoria completo"""
    memory_system = AdvancedMemorySystem()
    
    # Test aggiunta memoria
    emotional_state = {
        'primary_emotion': 'joy',
        'intensity': 0.8,
        'valence': 0.7,
        'arousal': 0.6,
        'dominance': 0.5
    }
    
    node = memory_system.add_memory(
        content="Test memory",
        context={"type": "test"},
        emotional_state=emotional_state,
        importance=0.8
    )
    
    assert node is not None
    assert node.id in memory_system.nodes
    assert memory_system.nodes[node.id].content == "Test memory"
    
    # Test recupero memoria
    stats = memory_system.get_memory_stats()
    assert stats['immediate_count'] >= 0
    assert stats['total_nodes'] == 1

def test_memory_lifecycle():
    """Test della gestione del ciclo di vita delle memorie"""
    memory_system = AdvancedMemorySystem()
    
    # Crea una memoria immediata
    node1 = memory_system.create_memory_node(
        content="Test immediate memory",
        metadata={
            "emotional_state": {
                "primary_emotion": "joy",
                "intensity": 0.8
            }
        }
    )
    
    assert memory_system.nodes[node1].layer == 'immediate'
    
    # Simula il passaggio di 2 giorni
    memory_system.nodes[node1].timestamp = datetime.now() - timedelta(days=2)
    memory_system._manage_memory_lifecycle()
    
    # Verifica che la memoria sia passata a short_term
    assert memory_system.nodes[node1].layer == 'short_term'
    
    # Simula il passaggio di 31 giorni
    memory_system.nodes[node1].timestamp = datetime.now() - timedelta(days=31)
    memory_system._manage_memory_lifecycle()
    
    # Verifica che la memoria sia passata a long_term
    assert memory_system.nodes[node1].layer == 'long_term'

def test_thematic_pattern_analysis():
    """Test dell'analisi dei pattern tematici"""
    memory_system = AdvancedMemorySystem()
    
    # Crea memorie con temi comuni
    metadata1 = {
        "topics": ["AI", "learning"],
        "emotional_state": {"primary_emotion": "curiosity", "intensity": 0.7}
    }
    metadata2 = {
        "topics": ["AI", "memory"],
        "emotional_state": {"primary_emotion": "interest", "intensity": 0.8}
    }
    
    node1 = memory_system.create_memory_node("AI learning concepts", metadata1)
    node2 = memory_system.create_memory_node("AI memory systems", metadata2)
    
    # Verifica che i temi siano stati mappati
    assert "AI" in memory_system.thematic_map
    assert len(memory_system.thematic_map["AI"]) == 2
    
    # Verifica che le connessioni tematiche siano state create
    assert node2 in memory_system.nodes[node1].connections

def test_emotional_pattern_analysis():
    """Test dell'analisi dei pattern emotivi"""
    memory_system = AdvancedMemorySystem()
    
    # Crea memorie con stati emotivi
    emotions = [
        {"primary_emotion": "joy", "intensity": 0.8, "valence": 0.7},
        {"primary_emotion": "joy", "intensity": 0.9, "valence": 0.8},
        {"primary_emotion": "curiosity", "intensity": 0.6, "valence": 0.5}
    ]
    
    for i, emotion in enumerate(emotions):
        memory_system.create_memory_node(
            f"Memory {i}",
            {"emotional_state": emotion}
        )
    
    # Verifica che i pattern emotivi siano stati registrati
    assert "intensity" in memory_system.emotional_patterns
    assert len(memory_system.emotional_patterns["intensity"]) == 3
    
    # Verifica che i valori siano corretti
    intensities = memory_system.emotional_patterns["intensity"]
    assert 0.8 in intensities
    assert 0.9 in intensities
    assert 0.6 in intensities

def test_contextual_pattern_analysis():
    """Test dell'analisi dei pattern contestuali"""
    memory_system = AdvancedMemorySystem()
    
    # Crea memorie in orari diversi
    now = datetime.now()
    
    # Memoria creata alle 10:00
    node1 = memory_system.create_memory_node(
        "Morning memory",
        {"emotional_state": {"primary_emotion": "alert", "intensity": 0.7}}
    )
    memory_system.nodes[node1].timestamp = now.replace(hour=10)
    
    # Memoria creata alle 15:00
    node2 = memory_system.create_memory_node(
        "Afternoon memory",
        {"emotional_state": {"primary_emotion": "focused", "intensity": 0.8}}
    )
    memory_system.nodes[node2].timestamp = now.replace(hour=15)
    
    # Aggiorna i pattern contestuali
    memory_system._update_contextual_patterns(memory_system.nodes[node1])
    memory_system._update_contextual_patterns(memory_system.nodes[node2])
    
    # Verifica che i pattern orari siano stati registrati
    assert 'time_patterns' in memory_system.contextual_patterns
    assert memory_system.contextual_patterns['time_patterns']['hourly'][10] == 1
    assert memory_system.contextual_patterns['time_patterns']['hourly'][15] == 1

def test_emotional_similarity():
    """Test del calcolo della similarità emotiva"""
    memory_system = AdvancedMemorySystem()
    
    # Crea due stati emotivi simili
    emotions1 = {
        "intensity": 0.8,
        "valence": 0.7,
        "arousal": 0.6,
        "dominance": 0.5
    }
    
    emotions2 = {
        "intensity": 0.7,
        "valence": 0.6,
        "arousal": 0.5,
        "dominance": 0.4
    }
    
    # Calcola la similarità
    similarity = memory_system._calculate_emotional_similarity(emotions1, emotions2)
    
    # La similarità dovrebbe essere alta dato che i valori sono vicini
    assert similarity > 0.8
    
    # Test con stati emotivi molto diversi
    emotions3 = {
        "intensity": 0.1,
        "valence": -0.8,
        "arousal": 0.9,
        "dominance": 0.2
    }
    
    similarity = memory_system._calculate_emotional_similarity(emotions1, emotions3)
    
    # La similarità dovrebbe essere bassa dato che i valori sono molto diversi
    assert similarity < 0.5
    
    # Test con dati mancanti
    emotions4 = {
        "intensity": 0.8,
        "valence": 0.7
        # arousal e dominance mancanti
    }
    
    similarity = memory_system._calculate_emotional_similarity(emotions1, emotions4)
    
    # Dovrebbe gestire correttamente i dati mancanti
    assert 0 <= similarity <= 1

def test_error_handling():
    """Test della gestione degli errori nel sistema di memoria"""
    memory_system = AdvancedMemorySystem()
    
    # Test creazione nodo con metadati non validi
    with pytest.raises(ValueError):
        memory_system.create_memory_node(
            content="Test memory",
            metadata={"emotional_state": "non_un_dizionario"}  # Dovrebbe essere un dict
        )
    
    # Test accesso a nodo non esistente
    with pytest.raises(KeyError):
        memory_system.get_node(999)
    
    # Test connessione con nodo non esistente
    node1 = memory_system.create_memory_node(
        content="Test memory",
        metadata={"emotional_state": {"primary_emotion": "joy"}}
    )
    with pytest.raises(ValueError):
        memory_system.connect_nodes(node1, 999)

def test_advanced_search():
    """Test delle funzioni di ricerca avanzate"""
    memory_system = AdvancedMemorySystem()
    
    # Crea alcune memorie di test
    metadata1 = {
        "topics": ["AI", "learning"],
        "emotional_state": {
            "primary_emotion": "curiosity",
            "intensity": 0.7,
            "valence": 0.6
        },
        "context": {"location": "lab", "time": "morning"}
    }
    
    metadata2 = {
        "topics": ["AI", "memory"],
        "emotional_state": {
            "primary_emotion": "joy",
            "intensity": 0.8,
            "valence": 0.8
        },
        "context": {"location": "office", "time": "afternoon"}
    }
    
    node1 = memory_system.create_memory_node("Learning about AI", metadata1)
    node2 = memory_system.create_memory_node("Memory systems in AI", metadata2)
    
    # Test ricerca per contenuto
    results = memory_system.search_by_content("AI")
    assert len(results) == 2
    
    # Test ricerca per metadati
    results = memory_system.search_by_metadata({"location": "lab"})
    assert len(results) == 1
    assert results[0].id == node1
    
    # Test ricerca per stato emotivo
    context = {
        "emotional_state": {
            "primary_emotion": "curiosity",
            "intensity": 0.7
        }
    }
    results = memory_system.get_relevant_memories(context)
    assert len(results) > 0
    assert results[0].id == node1

def test_pattern_analysis():
    """Test delle funzioni di analisi dei pattern"""
    memory_system = AdvancedMemorySystem()
    
    # Crea memorie con pattern temporali
    times = [10, 10, 15, 15, 15]  # Ore del giorno
    emotions = ["joy", "joy", "focus", "focus", "focus"]
    
    for i, (time, emotion) in enumerate(zip(times, emotions)):
        # Crea il timestamp con l'ora specificata
        timestamp = datetime.now().replace(hour=time)
        
        # Crea il nodo con il timestamp nei metadati
        node = memory_system.create_memory_node(
            f"Memory {i}",
            {
                "timestamp": timestamp,
                "emotional_state": {
                    "primary_emotion": emotion,
                    "intensity": 0.8
                }
            }
        )
    
    # Debug: stampa i pattern temporali
    time_patterns = memory_system.contextual_patterns['time_patterns']
    print("\nPattern temporali:")
    print(f"Orari: {time_patterns['hourly']}")
    
    # Verifica pattern temporali
    assert time_patterns['hourly'][10] == 2  # 2 memorie alle 10
    assert time_patterns['hourly'][15] == 3  # 3 memorie alle 15
    
    # Debug: stampa i valori massimi
    max_count = max(time_patterns['hourly'])
    print(f"\nConteggio massimo: {max_count}")
    print(f"Indici con conteggio massimo:")
    for hour, count in enumerate(time_patterns['hourly']):
        if count == max_count:
            print(f"Ora {hour}: {count} memorie")
    
    # Verifica pattern emotivi
    assert len(memory_system.emotional_patterns.get('intensity', [])) == 5
    
    # Debug: stampa i pattern dominanti
    patterns = memory_system.get_dominant_patterns()
    print("\nPattern dominanti:")
    print(f"Ore di picco: {patterns['peak_hours']}")
    print(f"Emozioni dominanti: {patterns['dominant_emotions']}")
    
    # Test get_dominant_patterns
    assert patterns['peak_hours'] == [15]  # L'ora con più attività
    assert 'focus' in patterns['dominant_emotions']  # L'emozione più frequente

def test_long_term_memory():
    """Test della gestione della memoria a lungo termine"""
    memory_system = AdvancedMemorySystem()
    
    # Crea alcune memorie
    nodes = []
    for i in range(5):
        node = memory_system.create_memory_node(
            f"Memory {i}",
            {
                "emotional_state": {
                    "primary_emotion": "joy",
                    "intensity": 0.8
                },
                "importance": 0.5 + i * 0.1  # Importanza crescente
            }
        )
        nodes.append(node)
        # Simula memorie vecchie
        memory_system.nodes[node].timestamp = datetime.now() - timedelta(days=31)
    
    # Forza l'aggiornamento del ciclo di vita
    memory_system._manage_memory_lifecycle()
    
    # Verifica che tutte le memorie siano nel layer long_term
    for node in nodes:
        assert memory_system.nodes[node].layer == 'long_term'
    
    # Test consolidamento memoria
    memory_system.consolidate_long_term_memories()
    
    # Verifica che le memorie più importanti siano state mantenute
    remaining_nodes = [node for node in nodes 
                      if node in memory_system.nodes]
    assert len(remaining_nodes) <= len(nodes)  # Alcune memorie potrebbero essere state rimosse
    
    # Le memorie rimanenti dovrebbero essere quelle più importanti
    for node in remaining_nodes:
        assert memory_system.nodes[node].metadata.get('importance', 0) > 0.6

def test_memory_stats():
    """Test delle statistiche della memoria"""
    memory_system = AdvancedMemorySystem()
    
    # Crea memorie in diversi layer
    # Immediate
    node1 = memory_system.create_memory_node(
        "Recent memory",
        {"emotional_state": {"primary_emotion": "joy"}}
    )
    
    # Short-term
    node2 = memory_system.create_memory_node(
        "Older memory",
        {"emotional_state": {"primary_emotion": "curiosity"}}
    )
    memory_system.nodes[node2].timestamp = datetime.now() - timedelta(days=2)
    
    # Long-term
    node3 = memory_system.create_memory_node(
        "Old memory",
        {"emotional_state": {"primary_emotion": "nostalgia"}}
    )
    memory_system.nodes[node3].timestamp = datetime.now() - timedelta(days=31)
    
    # Aggiorna i layer
    memory_system._manage_memory_lifecycle()
    
    # Ottieni e verifica le statistiche
    stats = memory_system.get_memory_stats()
    
    assert stats['total_nodes'] == 3
    assert stats['immediate_count'] == 1
    assert stats['short_term_count'] == 1
    assert stats['long_term_count'] == 1
    assert 'average_importance' in stats
    assert 'emotional_distribution' in stats

if __name__ == '__main__':
    pytest.main([__file__])
