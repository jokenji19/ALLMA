import pytest
import time
import tempfile
import os
from pathlib import Path
from Model.incremental_learning.user_profile import UserProfile, CommunicationPreference, InteractionMetrics

def test_communication_preference_initialization():
    """Test dell'inizializzazione delle preferenze di comunicazione"""
    prefs = CommunicationPreference()
    
    # Verifica valori di default
    assert prefs.formality_level == 0.5
    assert prefs.verbosity_level == 0.5
    assert prefs.technical_level == 0.5
    assert prefs.emotional_style == "neutral"
    assert isinstance(prefs.preferred_topics, list)
    assert isinstance(prefs.avoided_topics, list)
    assert len(prefs.preferred_topics) == 0
    assert len(prefs.avoided_topics) == 0

def test_interaction_metrics_initialization():
    """Test dell'inizializzazione delle metriche di interazione"""
    metrics = InteractionMetrics()
    
    assert metrics.total_interactions == 0
    assert metrics.positive_responses == 0
    assert metrics.negative_responses == 0
    assert metrics.average_session_length == 0.0
    assert isinstance(metrics.topic_frequencies, dict)
    assert len(metrics.topic_frequencies) == 0

def test_user_profile_initialization():
    """Test dell'inizializzazione del profilo utente"""
    profile = UserProfile("test_user")
    
    assert profile.user_id == "test_user"
    assert profile.creation_time <= time.time()
    assert profile.last_update <= time.time()
    assert isinstance(profile.preferences, CommunicationPreference)
    assert isinstance(profile.metrics, InteractionMetrics)
    assert isinstance(profile.interaction_history, list)
    assert len(profile.interaction_history) == 0

def test_profile_update_from_interaction():
    """Test dell'aggiornamento del profilo da interazione"""
    profile = UserProfile("test_user")
    
    # Test interazione positiva
    interaction_data = {
        "sentiment": 1,
        "topic": "programming",
        "formality_feedback": 0.8,
        "verbosity_feedback": 0.3,
        "technical_feedback": 0.6,
        "emotional_feedback": 0.9,
        "topic_feedback": 0.8
    }
    
    profile.update_from_interaction(interaction_data)
    
    # Verifica aggiornamenti base
    assert profile.metrics.total_interactions == 1
    assert profile.metrics.positive_responses == 1
    assert profile.metrics.topic_frequencies["programming"] == 1
    
    # Verifica adattamento preferenze
    assert profile.preferences.formality_level > 0.5  # Dovrebbe essere aumentato
    assert profile.preferences.verbosity_level < 0.5  # Dovrebbe essere diminuito
    assert profile.preferences.technical_level > 0.5  # Dovrebbe essere aumentato
    assert profile.preferences.emotional_style == "empathetic"
    assert "programming" in profile.preferences.preferred_topics

def test_profile_adaptation():
    """Test dell'adattamento del profilo nel tempo"""
    profile = UserProfile("test_user")
    
    # Simula una serie di interazioni
    interactions = [
        {"sentiment": 1, "formality_feedback": 0.8},
        {"sentiment": 1, "formality_feedback": 0.9},
        {"sentiment": 1, "formality_feedback": 0.7}
    ]
    
    initial_formality = profile.preferences.formality_level
    
    for interaction in interactions:
        profile.update_from_interaction(interaction)
        
    # Verifica che il profilo si sia adattato
    assert profile.preferences.formality_level > initial_formality
    assert profile.metrics.total_interactions == 3
    assert profile.metrics.positive_responses == 3

def test_profile_persistence(tmp_path):
    """Test del salvataggio e caricamento del profilo"""
    profile = UserProfile("test_user")
    
    # Aggiungi alcuni dati
    profile.update_from_interaction({
        "sentiment": 1,
        "topic": "testing",
        "formality_feedback": 0.8
    })
    
    # Salva il profilo
    filepath = tmp_path / "test_profile.json"
    profile.save_to_file(str(filepath))
    
    # Carica il profilo
    loaded_profile = UserProfile.load_from_file(str(filepath))
    
    # Verifica che i dati siano stati preservati
    assert loaded_profile.user_id == profile.user_id
    assert loaded_profile.creation_time == profile.creation_time
    assert loaded_profile.metrics.total_interactions == profile.metrics.total_interactions
    assert loaded_profile.preferences.formality_level == profile.preferences.formality_level
    assert loaded_profile.interaction_history == profile.interaction_history

def test_communication_style():
    """Test dello stile di comunicazione"""
    profile = UserProfile("test_user")
    
    # Imposta alcune preferenze
    profile.preferences.formality_level = 0.8
    profile.preferences.verbosity_level = 0.3
    profile.preferences.technical_level = 0.6
    profile.preferences.emotional_style = "professional"
    profile.preferences.preferred_topics = ["python", "testing"]
    
    style = profile.get_communication_style()
    
    assert style["formality"] == 0.8
    assert style["verbosity"] == 0.3
    assert style["technical_level"] == 0.6
    assert style["emotional_style"] == "professional"
    assert "python" in style["preferred_topics"]
    assert "testing" in style["preferred_topics"]
