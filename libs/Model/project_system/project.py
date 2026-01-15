"""Project - Classe per rappresentare un progetto"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

@dataclass
class Project:
    """Rappresenta un progetto nel sistema."""
    id: int
    user_id: str
    name: str
    description: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    interaction_count: int = 0

    @classmethod
    def from_dict(cls, data: Dict) -> 'Project':
        """
        Crea un'istanza di Project da un dizionario.
        
        Args:
            data: Dizionario contenente i dati del progetto
            
        Returns:
            Istanza di Project
        """
        if isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)
