"""
Package per il sistema di apprendimento incrementale di ALLMA
"""

from .emotional_system import EmotionalSystem, EmotionType, Emotion
from .cognitive_evolution_system import CognitiveEvolutionSystem, CognitiveStage
from .memory_system import MemorySystem
from .pattern_recognition_system import PatternRecognitionSystem
from .pattern_validation import PatternValidator
from .perception_system import PerceptionSystem
from .metacognition_system import MetaCognitionSystem
from .communication_system import CommunicationSystem

__all__ = [
    'EmotionalSystem',
    'EmotionType',
    'Emotion',
    'CognitiveEvolutionSystem',
    'CognitiveStage',
    'MemorySystem',
    'PatternRecognitionSystem',
    'PatternValidator',
    'PerceptionSystem',
    'MetaCognitionSystem',
    'CommunicationSystem'
]
