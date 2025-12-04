"""
Test del sistema di meta-learning
"""

import pytest
import time
from datetime import datetime
from Model.incremental_learning.meta_learning_system import (
    MetaLearningSystem,
    LearningStrategy,
    LearningExperience,
    LearningInsight
)
from Model.incremental_learning.user_profile import UserProfile

def test_strategy_adaptation():
    """Test dell'adattamento delle strategie al profilo utente"""
    meta_system = MetaLearningSystem()
    user_profile = UserProfile("test_user")
    
    # Simula una serie di interazioni per costruire il profilo
    interactions = [
        {
            "sentiment": 1,
            "topic": "programming",
            "formality_feedback": 0.8,
            "verbosity_feedback": 0.3,
            "technical_feedback": 0.9,
            "emotional_feedback": 0.6,
            "topic_feedback": 0.8
        },
        {
            "sentiment": 1,
            "topic": "programming",
            "formality_feedback": 0.7,
            "verbosity_feedback": 0.4,
            "technical_feedback": 0.85,
            "emotional_feedback": 0.5,
            "topic_feedback": 0.7
        }
    ]
    
    for interaction in interactions:
        user_profile.update_from_interaction(interaction)
        
    # Debug: stampa il livello tecnico
    print(f"Technical level: {user_profile.preferences.technical_level}")
    print(f"Communication style: {user_profile.get_communication_style()}")
    
    # Adatta le strategie
    initial_difficulty = meta_system.strategies["elaboration"].optimal_difficulty
    meta_system.adapt_to_user_profile(user_profile)
    
    # Verifica che le strategie si siano adattate
    strategy = meta_system.strategies["elaboration"]
    assert strategy.optimal_difficulty > initial_difficulty  # Dovrebbe aumentare per alto livello tecnico
    assert "programming" in strategy.preferred_contexts
    assert abs(strategy.parameters["depth"] - 0.35) < 0.2  # Dovrebbe essere vicino al livello di verbosità medio

def test_learning_from_interaction():
    """Test dell'apprendimento dalle interazioni"""
    meta_system = MetaLearningSystem()
    
    # Simula un'interazione
    interaction_data = {
        "sentiment": 0.8,
        "technical_feedback": 0.7,
        "formality_feedback": 0.6,
        "topic": "testing"
    }
    
    # Aggiorna il sistema
    insight = meta_system.update_from_user_interaction(interaction_data)
    
    # Verifica che l'insight sia stato generato correttamente
    assert isinstance(insight, LearningInsight)
    assert insight.system_name == "meta_learning"
    assert insight.value > 0.5  # Dovrebbe essere positivo dato il sentiment positivo
    
    # Verifica che l'esperienza sia stata registrata
    assert len(meta_system.experiences) == 1
    latest_exp = meta_system.experiences[-1]
    assert latest_exp.success_level > 0.5
    assert latest_exp.context["topic"] == "testing"

def test_learning_recommendations():
    """Test delle raccomandazioni di apprendimento"""
    meta_system = MetaLearningSystem()
    user_profile = UserProfile("test_user")
    
    # Imposta il profilo utente
    user_profile.update_from_interaction({
        "sentiment": 1,
        "topic": "python",
        "formality_feedback": 0.7,
        "verbosity_feedback": 0.6,
        "technical_feedback": 0.8,
        "topic_feedback": 0.9
    })
    
    # Ottieni raccomandazioni
    recommendations = meta_system.get_learning_recommendations(user_profile)
    
    # Verifica le raccomandazioni
    assert len(recommendations) > 0
    for rec in recommendations:
        assert "strategy_name" in rec
        assert "compatibility" in rec
        assert "reason" in rec
        assert "suggested_parameters" in rec
        assert rec["compatibility"] > 0.5

def test_strategy_evolution():
    """Test dell'evoluzione delle strategie nel tempo"""
    meta_system = MetaLearningSystem()
    
    # Simula una serie di interazioni
    interactions = [
        {"sentiment": 0.8, "technical_feedback": 0.7, "topic": "testing"},
        {"sentiment": 0.9, "technical_feedback": 0.8, "topic": "testing"},
        {"sentiment": 0.7, "technical_feedback": 0.6, "topic": "testing"}
    ]
    
    initial_success_rate = meta_system._get_current_strategy().success_rate
    
    # Processa le interazioni
    for interaction in interactions:
        meta_system.update_from_user_interaction(interaction)
    
    # Verifica che la strategia sia migliorata
    final_success_rate = meta_system._get_current_strategy().success_rate
    assert final_success_rate > initial_success_rate
    
    # Verifica che ci siano insights per ogni interazione
    assert len(meta_system.insights) == len(interactions)

def test_strategy_compatibility():
    """Test della compatibilità delle strategie con il profilo utente"""
    meta_system = MetaLearningSystem()
    user_profile = UserProfile("test_user")
    
    # Simula una serie di interazioni per costruire un profilo tecnico
    interactions = [
        {
            "sentiment": 1,
            "topic": "advanced_programming",
            "formality_feedback": 0.9,
            "verbosity_feedback": 0.8,
            "technical_feedback": 0.9,
            "topic_feedback": 0.9
        },
        {
            "sentiment": 1,
            "topic": "advanced_programming",
            "formality_feedback": 0.85,
            "verbosity_feedback": 0.75,
            "technical_feedback": 0.95,
            "topic_feedback": 0.85
        },
        {
            "sentiment": 1,
            "topic": "advanced_programming",
            "formality_feedback": 0.8,
            "verbosity_feedback": 0.7,
            "technical_feedback": 0.85,
            "topic_feedback": 0.8
        }
    ]
    
    for interaction in interactions:
        user_profile.update_from_interaction(interaction)
        
    # Debug: stampa il livello tecnico
    print(f"Technical level: {user_profile.preferences.technical_level}")
    print(f"Communication style: {user_profile.get_communication_style()}")
    
    # Adatta le strategie
    meta_system.adapt_to_user_profile(user_profile)
    
    # Verifica che le strategie si siano adattate al livello tecnico
    for strategy in meta_system.strategies.values():
        if "intensity" in strategy.parameters:
            # Dovrebbe essere molto vicino al livello tecnico medio (0.9)
            assert strategy.parameters["intensity"] > 0.8
