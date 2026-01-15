"""
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending - ALLMA (Adaptive Learning and Language Model Architecture)

This file defines initial experiences and developmental stages for ALLMA.
Author: Cristof Bano
Created: January 2025
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional

class DevelopmentalStage(Enum):
    PERCEPTION = "perception"
    MEMORY = "memory"
    LEARNING = "learning"
    REASONING = "reasoning"
    CREATIVITY = "creativity"
    PROBLEM_SOLVING = "problem_solving"

@dataclass
class Experience:
    content: str
    stage: DevelopmentalStage
    difficulty: float
    expected_outcome: str
    
class InitialExperienceGenerator:
    def __init__(self):
        self.experiences = {
            DevelopmentalStage.PERCEPTION: [
                Experience("Osserva attentamente questo pattern", 
                          DevelopmentalStage.PERCEPTION, 0.3, 
                          "Pattern identificato correttamente")
            ],
            DevelopmentalStage.MEMORY: [
                Experience("Memorizza ciò che hai osservato", 
                          DevelopmentalStage.MEMORY, 0.4,
                          "Informazione memorizzata correttamente")
            ]
        }
        
    def get_experiences(self, stage: DevelopmentalStage) -> List[Experience]:
        return self.experiences.get(stage, [])
