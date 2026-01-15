import pytest
from allma_model.core.personality_coalescence import (
    PersonalityCore, 
    CoalescenceProcessor,
    EmotionalState,
    EmotionalResponse,
    Memory,
    Value
)
from datetime import datetime
import time

def test_personality_core_initialization():
    """Test dell'inizializzazione del nucleo della personalità"""
    core = PersonalityCore()
    
    # Test valori fondamentali
    assert len(core.values) == 7  # Verifica numero di valori
    assert "empatia" in core.values
    assert "curiosità" in core.values
    
    # Test conflitti tra valori
    assert "autonomia" in core.values["empatia"].conflicts
    assert "empatia" in core.values["autonomia"].conflicts
    
    # Test stato emotivo iniziale
    assert core.current_emotional_state.primary == EmotionalState.REFLECTION
    
    # Test tratti della personalità
    assert 0 <= core.personality_traits["openness"] <= 1
    assert 0 <= core.personality_traits["empathy"] <= 1
    
    # Test resilienza
    assert 0 <= core.resilience_base <= 1
    assert core.resilience_bonus == 0.0

def test_value_relationships():
    """Test delle relazioni tra valori"""
    core = PersonalityCore()
    relationships = core._initialize_value_relationships()
    
    # Verifica che ogni valore abbia relazioni con tutti gli altri
    for v1 in core.values:
        for v2 in core.values:
            if v1 != v2:
                assert v2 in relationships[v1]
                # La relazione dovrebbe essere simmetrica
                assert relationships[v1][v2] == relationships[v2][v1]
                # Il valore dovrebbe essere tra -1 e 1
                assert -1 <= relationships[v1][v2] <= 1

def test_coalescence_processor_droplet():
    """Test del processamento di una nuova esperienza"""
    processor = CoalescenceProcessor()
    
    # Crea una nuova goccia
    content = "Ho aiutato qualcuno a capire un concetto difficile"
    context = {
        "timestamp": time.time(),
        "type": "interaction",
        "topic": "teaching"
    }
    
    droplet = processor.create_droplet(content, context)
    
    # Verifica che la goccia sia stata creata correttamente
    assert isinstance(droplet, Memory)
    assert droplet.content == content
    assert droplet.context["type"] == context["type"]
    assert droplet.context["topic"] == context["topic"]
    
    # Processa la goccia come Memory
    processor._integrate_droplet(droplet)
    
    # Verifica che i valori rilevanti siano stati influenzati
    core = processor.core
    initial_empathy = core.values["empatia"].strength
    initial_help = core.values["aiuto"].strength
    
    # Processa la goccia come dict (per retrocompatibilità)
    droplet_dict = {
        "content": content,
        "context": context
    }
    processor.process_droplet(droplet_dict)
    
    # Verifica che i valori siano stati influenzati
    assert core.values["empatia"].strength >= initial_empathy
    assert core.values["aiuto"].strength >= initial_help

def test_emotional_analysis():
    """Test dell'analisi emotiva del contenuto"""
    processor = CoalescenceProcessor()
    
    # Test con contenuto positivo
    content = "Sono felice di aver aiutato qualcuno oggi"
    emotion = processor._analyze_emotional_context(content)
    assert emotion.primary == EmotionalState.JOY
    assert emotion.intensity > 0.5
    
    # Test con contenuto riflessivo
    content = "Mi chiedo come potrei migliorare questo processo"
    emotion = processor._analyze_emotional_context(content)
    assert emotion.primary == EmotionalState.REFLECTION
    
    # Test con contenuto curioso
    content = "Vorrei capire meglio come funziona questo sistema"
    emotion = processor._analyze_emotional_context(content)
    assert emotion.primary == EmotionalState.CURIOSITY

def test_memory_integration():
    """Test dell'integrazione delle memorie"""
    processor = CoalescenceProcessor()
    
    # Crea una memoria significativa
    memory = Memory(
        content="Una scoperta importante",
        timestamp=time.time(),
        emotional_response=EmotionalResponse(EmotionalState.INSPIRATION, intensity=0.8),
        context={"type": "discovery", "importance": "high"},
        significance=0.9
    )
    
    # Integra la memoria
    processor._integrate_droplet(memory)
    
    # Verifica che la memoria sia stata integrata
    assert len(processor.emotional_memory) > 0
    assert any(m.content == "Una scoperta importante" for m in processor.emotional_memory)

def test_response_generation():
    """Test della generazione di risposte"""
    processor = CoalescenceProcessor()
    
    # Crea un input che dovrebbe generare una risposta empatica
    droplet = {
        "content": "Mi sento triste oggi",
        "context": {
            "type": "emotional_expression",
            "emotion": "sadness"
        }
    }
    
    response = processor.generate_response(droplet)
    
    # Verifica che la risposta sia appropriata
    assert isinstance(response, dict)
    assert "content" in response
    assert "emotional_state" in response
    assert response["emotional_state"]["primary"] == EmotionalState.EMPATHY.value

def test_diary_management():
    """Test della gestione del diario e persistenza"""
    processor = CoalescenceProcessor()
    droplet = {
        "content": "Ho imparato qualcosa di nuovo oggi sulla gentilezza",
        "context": {"situation": "learning", "time": time.time()}
    }
    
    # Creiamo una memoria e la aggiungiamo al diario
    memory = Memory(
        content=droplet["content"],
        timestamp=time.time(),
        emotional_response=EmotionalResponse(EmotionalState.CURIOSITY),
        context=droplet["context"]
    )
    processor.core.add_memory(memory)
    processor._create_diary_entry(memory, {"empathy": 0.1})
    
    # Verifica contenuto diario
    assert len(processor.core.diary) > 0
    last_entry = processor.core.diary[-1]
    assert "datetime" in last_entry
    assert "experience" in last_entry  
    assert "emotional_state" in last_entry
    assert last_entry["emotional_state"] == EmotionalState.CURIOSITY.value

def test_learned_concepts():
    """Test della gestione dei concetti appresi"""
    processor = CoalescenceProcessor()
    content = "Mi sento ispirato ad aiutare e capire gli altri con empatia"
    
    # Identifichiamo i valori rilevanti usando parole chiave specifiche
    relevant_values = processor._identify_relevant_values(content)
    assert "empatia" in relevant_values, "Il contenuto dovrebbe attivare il valore dell'empatia"
    
    # Analizziamo il contesto emotivo
    emotional_response = processor._analyze_emotional_context(content)
    assert isinstance(emotional_response, EmotionalResponse)
    assert emotional_response.primary in [EmotionalState.EMPATHY, EmotionalState.INSPIRATION]
    
    # Creiamo una memoria con questi dati
    memory = Memory(
        content=content,
        timestamp=time.time(),
        emotional_response=emotional_response,
        context={"type": "learning", "values": relevant_values}
    )
    
    # Integriamo la memoria
    processor._integrate_droplet(memory)
    
    # Verifichiamo che i valori siano stati influenzati
    assert processor.core.values["empatia"].strength >= 0.5

def test_droplet_integration():
    """Test dell'integrazione delle gocce di esperienza"""
    processor = CoalescenceProcessor()
    content = "Mi sento ispirato a aiutare gli altri con comprensione"
    
    # Creiamo una memoria
    memory = Memory(
        content=content,
        timestamp=time.time(),
        emotional_response=EmotionalResponse(EmotionalState.INSPIRATION),
        context={"situation": "helping", "type": "experience"}
    )
    
    # Integriamo direttamente la memoria
    processor.core.add_memory(memory)
    processor._integrate_droplet(memory)
    
    # Verifichiamo che la memoria sia stata aggiunta
    assert len(processor.core.memories) > 0, "La memoria dovrebbe essere stata aggiunta"
    
    # Verifichiamo che i tratti della personalità siano stati influenzati
    assert processor.core.personality_traits["empathy"] >= 0.5, "L'empatia dovrebbe essere influenzata"
    
    # Verifichiamo la creazione del diario
    assert len(processor.core.diary) > 0, "Dovrebbe essere stata creata una voce nel diario"

def test_resilience_adaptation():
    """Test dell'adattamento della resilienza"""
    core = PersonalityCore()
    initial_bonus = core.resilience_bonus
    
    # Test impatto positivo
    core.update_resilience(0.2)
    assert core.resilience_bonus > initial_bonus
    
    # Test impatto negativo
    initial_bonus = core.resilience_bonus
    core.update_resilience(-0.1)
    assert core.resilience_bonus < initial_bonus
    
    # Test limiti
    core.resilience_bonus = 0.4
    core.update_resilience(0.5)
    assert core.resilience_bonus <= 0.5  # Limite massimo
    
    core.resilience_bonus = 0.1
    core.update_resilience(-0.5)
    assert core.resilience_bonus >= 0.0  # Limite minimo

def test_memory_networks():
    """Test delle reti di memoria"""
    core = PersonalityCore()
    
    # Creiamo due memorie correlate
    mem1 = Memory(
        content="Prima esperienza di aiuto",
        timestamp=time.time(),
        emotional_response=EmotionalResponse(EmotionalState.EMPATHY),
        context={"type": "helping"}
    )
    mem2 = Memory(
        content="Seconda esperienza simile di aiuto",
        timestamp=time.time() + 60,
        emotional_response=EmotionalResponse(EmotionalState.EMPATHY),
        context={"type": "helping"}
    )
    
    # Aggiungiamo le memorie e verifichiamo le connessioni
    core.add_memory(mem1)
    core.add_memory(mem2)
    
    # Verifichiamo che le memorie siano state aggiunte
    assert len(core.memories) == 2
    
    # Verifichiamo la similarità
    similarity = core._calculate_memory_similarity(mem1, mem2)
    assert 0 <= similarity <= 1
    
    # Verifichiamo che le memorie simili siano state trovate
    similar_memories = core._find_similar_memories(mem2)
    assert len(similar_memories) > 0
    assert mem1 in similar_memories
