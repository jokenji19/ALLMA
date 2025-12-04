"""
API Bridge per l'integrazione di ALLMA con Android.
Questo modulo fornisce un'interfaccia pulita per l'accesso alle funzionalità di ALLMA
dall'app Android.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any

from Model.core.allma_core import ALLMACore
from Model.project_tracking.project_tracker import ProjectTracker, ProjectStatus
from Model.emotional_system.emotional_core import EmotionalCore
from Model.learning_system.incremental_learning import IncrementalLearner
from Model.personality_system.personality import Personality
from Model.user_preferences.preference_analyzer import PreferenceAnalyzer

class AllmaAndroidBridge:
    """Bridge per l'integrazione di ALLMA con Android"""
    
    def __init__(self, db_path: str = "allma.db"):
        """Inizializza il bridge ALLMA-Android"""
        self.allma = ALLMACore(db_path=db_path)
        self.project_tracker = ProjectTracker(db_path)
        self.emotional_core = EmotionalCore()
        self.learner = IncrementalLearner()
        self.personality = Personality()
        self.preference_analyzer = PreferenceAnalyzer(db_path)
        
    def initialize_user_session(self, user_id: str) -> Dict[str, Any]:
        """
        Inizializza una nuova sessione utente.

        Args:
            user_id: ID univoco dell'utente

        Returns:
            Dict con lo stato iniziale della sessione
        """
        if not user_id:
            raise ValueError("User ID non può essere vuoto")

        # Ottieni i progetti attivi dell'utente
        all_projects = self.project_tracker.get_user_projects(user_id)
        
        # Filtra solo i progetti attivi
        active_projects = []
        for project in all_projects:
            # Converti lo stato in un formato leggibile
            status_map = {
                "active": "Active",
                "in_progress": "In Progress",
                "paused": "Paused",
                "completed": "Completed",
                "archived": "Archived"
            }
            
            # Formatta i metadati
            metadata = {}
            if project.get('metadata'):
                metadata = json.loads(project['metadata'])
            
            formatted_project = {
                "id": str(project['id']),
                "name": project['name'],
                "description": project['description'],
                "status": status_map.get(project['status'], project['status']),
                "metadata": metadata,
                "created_at": project['created_at'],
                "updated_at": project['updated_at'],
                "interaction_count": project['interaction_count']
            }
            
            # Aggiungi solo i progetti attivi
            if project['status'] == 'active':
                active_projects.append(formatted_project)

        return {
            "user_id": user_id,
            "emotional_state": self.emotional_core.get_current_state(),
            "personality_state": self.personality.get_current_state(),
            "active_projects": active_projects,
            "learning_progress": self.learner.get_learning_progress(user_id)
        }
        
    def process_message(self, user_id: str, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Processa un messaggio dell'utente.
        
        Args:
            user_id: ID dell'utente
            message: Messaggio da processare
            context: Contesto aggiuntivo opzionale
            
        Returns:
            Dict con la risposta processata
        """
        if not user_id or not message:
            raise ValueError("User ID e messaggio sono richiesti")
            
        # Usa il session_id dal contesto come conversation_id se presente
        conversation_id = context.get("session_id") if context else None
        if not conversation_id:
            # Se non c'è un conversation_id, usa l'user_id
            conversation_id = user_id
            
        # Aggiungi user_id al contesto
        context = context or {}
        context["user_id"] = user_id
            
        try:
            # Processa il messaggio
            response = self.allma.process_message(
                user_id=user_id,
                conversation_id=conversation_id,
                message=message,
                context=context
            )
            
            # Formatta la risposta per l'API
            return {
                "response": response.content,
                "emotional_state": {
                    "primary": response.emotion,
                    "detected": response.emotion_detected
                },
                "personality_state": {
                    "topics": response.topics if hasattr(response, 'topics') else [],
                    "metadata": response.metadata if hasattr(response, 'metadata') else {}
                }
            }
            
        except Exception as e:
            raise Exception(f"Errore nel processare il messaggio: {str(e)}")
        
    def get_project_summary(self, project_id: str) -> Dict[str, Any]:
        """
        Ottiene il riepilogo di un progetto.
        
        Args:
            project_id: ID del progetto
            
        Returns:
            Dict con i dettagli del progetto
        """
        if not project_id:
            raise Exception("Project ID non può essere vuoto")
            
        try:
            # Ottieni il progetto
            project = self.project_tracker.get_project_summary(project_id)
            if not project:
                raise Exception(f"Progetto {project_id} non trovato")
                
            # Formatta il progetto per l'API
            metadata = {}
            if project.get('metadata'):
                metadata = json.loads(project['metadata'])
                
            # Converti lo stato in un formato leggibile
            status_map = {
                "active": "Active",
                "in_progress": "In Progress",
                "paused": "Paused",
                "completed": "Completed",
                "archived": "Archived"
            }
            
            return {
                "id": str(project['id']),
                "name": project['name'],
                "description": project['description'],
                "status": status_map.get(project['status'], project['status']),
                "metadata": metadata,
                "created_at": project['created_at'],
                "updated_at": project['updated_at'],
                "interaction_count": project['interaction_count']
            }
            
        except Exception as e:
            raise Exception(f"Errore nel recupero del progetto: {str(e)}")
        
    def create_project(self, user_id: str, name: str, description: str, metadata: Optional[Dict] = None) -> str:
        """
        Crea un nuovo progetto.
        
        Args:
            user_id: ID dell'utente che crea il progetto
            name: Nome del progetto
            description: Descrizione del progetto
            metadata: Metadati opzionali del progetto
            
        Returns:
            ID del progetto creato
        """
        if not user_id or not name:
            raise ValueError("User ID e nome del progetto sono richiesti")
            
        try:
            # Crea il progetto
            success = self.project_tracker.create_project(
                name=name,
                description=description,
                user_id=user_id,
                metadata=metadata
            )
            
            if not success:
                raise Exception("Creazione del progetto fallita")
            
            # Ottieni il riepilogo del progetto per ottenere l'ID
            project = self.project_tracker.get_project_summary(name)
            if not project:
                raise Exception("Progetto creato ma impossibile recuperare l'ID")
            
            # Converti l'ID in stringa per l'API
            return str(project['id'])
            
        except Exception as e:
            raise Exception(f"Errore nella creazione del progetto: {str(e)}")
        
    def update_project(self, project_id: str, status: str, metadata: Optional[Dict] = None) -> bool:
        """
        Aggiorna lo stato di un progetto.

        Args:
            project_id: ID del progetto
            status: Nuovo stato del progetto
            metadata: Metadati opzionali da aggiornare

        Returns:
            True se l'aggiornamento è riuscito, False altrimenti
        """
        if not project_id:
            raise Exception("Project ID non può essere vuoto")

        try:
            # Ottieni il progetto
            project = self.project_tracker.get_project_summary(project_id)
            if not project:
                raise Exception(f"Progetto {project_id} non trovato")

            # Converti lo stato in un valore valido per l'enum
            status_map = {
                "active": ProjectStatus.ACTIVE,
                "in progress": ProjectStatus.IN_PROGRESS,
                "paused": ProjectStatus.PAUSED,
                "completed": ProjectStatus.COMPLETED,
                "archived": ProjectStatus.ARCHIVED
            }
            
            # Normalizza lo stato in input
            normalized_status = status.lower().strip()
            if normalized_status not in status_map:
                raise Exception(f"Stato del progetto non valido: {status}")
                
            # Aggiorna lo stato del progetto
            project_status = status_map[normalized_status]
            success = self.project_tracker.update_project_status(
                project['user_id'],
                project['name'],
                project_status
            )

            if not success:
                raise Exception(f"Stato del progetto non aggiornato correttamente")
                
            # Se ci sono metadati da aggiornare, aggiornali
            if metadata:
                # Ottieni i metadati attuali
                current_metadata = {}
                if project.get('metadata'):
                    current_metadata = json.loads(project['metadata'])
                    
                # Aggiorna i metadati
                current_metadata.update(metadata)
                success = self.project_tracker.update_project_metadata(
                    project['user_id'],
                    project['name'],
                    current_metadata
                )
                
                if not success:
                    raise Exception(f"Metadati del progetto non aggiornati correttamente")

            return True

        except Exception as e:
            raise Exception(f"Errore nell'aggiornamento del progetto: {str(e)}")
        
    def get_learning_progress(self, user_id: str) -> Dict[str, Any]:
        """
        Ottiene il progresso di apprendimento di un utente.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Dict con il progresso di apprendimento
            
        Raises:
            Exception: Se l'utente non è valido
        """
        if not user_id:
            raise Exception("User ID non può essere vuoto")
            
        try:
            # Verifica che l'utente esista
            user_exists = self.preference_analyzer.has_user_preferences(user_id)
            if not user_exists:
                raise Exception(f"Utente {user_id} non trovato")
            
            # Ottieni il progresso
            progress = self.allma.get_learning_progress(user_id)
            if not progress:
                return {
                    "topics": [],
                    "confidence_levels": {},
                    "recent_learning": []
                }
                
            return progress
            
        except Exception as e:
            raise Exception(f"Errore nel recupero del progresso: {str(e)}")
        
    def get_emotional_analysis(self, text: str) -> Dict[str, Any]:
        """
        Analizza il contenuto emotivo di un testo.
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Dict con l'analisi emotiva
        """
        return self.emotional_core.analyze_text(text)
        
    def get_personality_insights(self, user_id: str) -> Dict[str, Any]:
        """
        Ottiene insights sulla personalità dell'utente.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Dict con gli insights sulla personalità
        """
        return self.personality.get_insights(user_id)
        
    def save_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """
        Salva le preferenze dell'utente.

        Args:
            user_id: ID dell'utente
            preferences: Dizionario con le preferenze

        Returns:
            True se il salvataggio è riuscito

        Raises:
            Exception: Se le preferenze non sono valide
        """
        if not user_id:
            raise Exception("User ID non può essere vuoto")

        if not isinstance(preferences, dict):
            raise Exception("Le preferenze devono essere un dizionario")

        try:
            # Verifica che le chiavi siano stringhe
            for key in preferences.keys():
                if not isinstance(key, str):
                    raise Exception("Le chiavi delle preferenze devono essere stringhe")

            # Salva le preferenze
            return self.preference_analyzer._store_preferences(user_id, preferences)

        except Exception as e:
            raise Exception(f"Errore nel salvare le preferenze: {str(e)}")
        
    def get_conversation_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Ottiene la cronologia delle conversazioni dell'utente.
        
        Args:
            user_id: ID dell'utente
            limit: Numero massimo di messaggi da recuperare
            
        Returns:
            Lista di messaggi della conversazione
        """
        if not user_id:
            raise ValueError("User ID non può essere vuoto")
            
        try:
            # Usa l'ultima conversazione dell'utente
            conversations = self.allma.conversational_memory.get_conversation_history(user_id)
            if limit:
                conversations = conversations[:limit]
            
            # Formatta i messaggi per l'API
            history = []
            for msg in conversations:
                history.append({
                    "text": msg.content,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                    "sender": msg.sender,
                    "metadata": msg.metadata
                })
                
            return history
            
        except Exception as e:
            raise Exception(f"Errore nel recuperare la cronologia: {str(e)}")
