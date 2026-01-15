"""
Integration between emotional system and memory management.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any

@dataclass
class EmotionalMemory:
    content: str
    emotion: str
    intensity: float
    context: Dict[str, float]

class EmotionalMemoryIntegration:
    def __init__(self):
        self.emotional_memories = []
        self.emotion_thresholds = {
            'joy': 0.7,
            'sadness': 0.3,
            'interest': 0.5
        }
        
    def process_emotional_memory(self, memory: EmotionalMemory) -> None:
        if memory.intensity > self.emotion_thresholds.get(memory.emotion, 0.5):
            self.emotional_memories.append(memory)
            
    def retrieve_by_emotion(self, emotion: str) -> List[EmotionalMemory]:
        return [m for m in self.emotional_memories if m.emotion == emotion]
        
    def generate_response(self, prompt: str, context: Dict[str, Any]) -> str:
        # Generate response based on emotional memories and context
        if context.get('is_significant', False):
            relevant_memories = [m for m in self.emotional_memories 
                               if any(word in m.content for word in prompt.split())]
            if relevant_memories:
                return f"Based on similar emotional experiences: {relevant_memories[0].content}"
        return "I understand your feelings."
