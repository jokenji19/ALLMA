from datetime import datetime
from typing import Optional
import logging

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from allma_model.learning_system.incremental_learning import LearningUnit, ConfidenceLevel


def build_emotion_pipeline(mobile_mode: bool, emotion_pipeline=None):
    if emotion_pipeline:
        return emotion_pipeline
    if mobile_mode or not TRANSFORMERS_AVAILABLE:
        return None
    try:
        return pipeline(
            "text-classification",
            model="j-hartmann/emotion-english-distilroberta-base",
            return_all_scores=True
        )
    except Exception as e:
        logging.warning(f"Impossibile caricare emotion pipeline: {e}")
        return None


def ensure_initial_knowledge(incremental_learner) -> None:
    if incremental_learner.get_knowledge_by_topic("python"):
        return
    initial_python_knowledge = LearningUnit(
        topic="python",
        content="Python è un linguaggio di programmazione ad alto livello, interpretato e orientato agli oggetti.",
        source="system",
        confidence=ConfidenceLevel.HIGH,
        timestamp=datetime.now(),
        metadata={"type": "initial_knowledge"}
    )
    incremental_learner.add_learning_unit(initial_python_knowledge)
