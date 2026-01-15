from typing import Dict, Any, Optional, List
from datetime import datetime

class ProjectTracker:
    """Tracker per i progetti e le loro interazioni."""
    
    def __init__(self):
        """Inizializza il project tracker."""
        self.projects = {}
        self.interactions = {}
        
    def create_project(
        self,
        user_id: str,
        name: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Crea un nuovo progetto.
        
        Args:
            user_id: ID dell'utente che crea il progetto
            name: Nome del progetto
            description: Descrizione del progetto
            metadata: Metadati opzionali
            
        Returns:
            ID del progetto creato
        """
        project_id = f"{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.projects[project_id] = {
            'user_id': user_id,
            'name': name,
            'description': description,
            'metadata': metadata or {},
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'status': 'active'
        }
        
        self.interactions[project_id] = []
        return project_id
        
    def update_project_interaction(
        self,
        project_id: str,
        interaction: Dict[str, Any]
    ) -> None:
        """
        Aggiorna le interazioni di un progetto.
        
        Args:
            project_id: ID del progetto
            interaction: Dettagli dell'interazione
        """
        if project_id not in self.projects:
            raise ValueError(f"Progetto {project_id} non trovato")
            
        # Aggiorna l'ultima modifica del progetto
        self.projects[project_id]['updated_at'] = datetime.now()
        
        # Aggiungi l'interazione alla lista
        self.interactions[project_id].append({
            **interaction,
            'timestamp': datetime.now()
        })
        
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        Ottiene i dettagli di un progetto.
        
        Args:
            project_id: ID del progetto
            
        Returns:
            Dettagli del progetto
        """
        if project_id not in self.projects:
            raise ValueError(f"Progetto {project_id} non trovato")
            
        return {
            **self.projects[project_id],
            'interactions': self.interactions[project_id]
        }
        
    def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Ottiene tutti i progetti di un utente.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Lista dei progetti dell'utente
        """
        return [
            {
                'project_id': pid,
                **project
            }
            for pid, project in self.projects.items()
            if project['user_id'] == user_id
        ]
        
    def update_project_state(
        self,
        project_id: str,
        state: Dict[str, Any]
    ) -> None:
        """
        Aggiorna lo stato di un progetto.
        
        Args:
            project_id: ID del progetto
            state: Nuovo stato del progetto
        """
        if project_id not in self.projects:
            raise ValueError(f"Progetto {project_id} non trovato")
            
        # Aggiorna lo stato del progetto
        self.projects[project_id].update(state)
        self.projects[project_id]['updated_at'] = datetime.now()
