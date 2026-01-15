from enum import Enum

class CommunicationStyle(Enum):
    """Stili di comunicazione supportati"""
    DIRECT = 'direct'
    DETAILED = 'detailed'
    TECHNICAL = 'technical'
    SIMPLIFIED = 'simplified'

class LearningStyle(Enum):
    """Stili di apprendimento supportati"""
    VISUAL = 'visual'
    PRACTICAL = 'practical'
    THEORETICAL = 'theoretical'
    INTERACTIVE = 'interactive'

class ProjectStatus(Enum):
    """Stati possibili di un progetto"""
    ACTIVE = 'active'
    COMPLETED = 'completed'
    ARCHIVED = 'archived'
    DELETED = 'deleted'
