"""Compatibility API over the canonical ALLMA core; no second cognitive state."""
from copy import deepcopy
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from allma_model.core.allma_core import ALLMACore
from allma_model.utils.cognitive_state import CognitiveStateStore


class AllmaAndroidBridge:
    def __init__(self, db_path='allma.db', *, core=None):
        if core is None:
            Path(db_path).resolve().parent.mkdir(parents=True, exist_ok=True)
        self.allma = core if core is not None else ALLMACore(db_path=db_path, mobile_mode=True)
        self.project_tracker = self.allma.project_tracker
        self.emotional_core = self.allma.emotional_core
        self.learner = self.allma.incremental_learner
        self.personality = self.allma.personality
        self.preference_analyzer = self.allma.preference_analyzer
        self._settings = CognitiveStateStore(self.allma.db_path)
        self._active_user = None

    def _user(self, user_id):
        if not isinstance(user_id,str) or not user_id.strip():
            raise ValueError('User ID richiesto')
        return user_id

    def _emotional_state(self, user_id):
        with self.allma.conversational_memory.lock:
            records = [m for m in self.allma.conversational_memory.messages
                       if (m.user_id or m.metadata.get('user_id')) == user_id
                       and m.metadata.get('is_valid') is not False and m.metadata.get('emotion_analysis')]
        return deepcopy(records[-1].metadata['emotion_analysis']) if records else {
            'primary_emotion':'neutral', 'confidence':0., 'source':'no_evidence'}

    def initialize_user_session(self, user_id):
        self._user(user_id)
        self._active_user = user_id
        return {'user_id':user_id, 'emotional_state':self._emotional_state(user_id),
                'personality_state':self.allma.coalescence_processor.get_current_personality_state(user_id),
                'active_projects':[self.get_project_summary(p.id, user_id=user_id)
                                   for p in self.project_tracker.get_user_projects(user_id)
                                   if self.project_tracker.get_project_summary(p.id)['status']=='active'],
                'learning_progress':self.learner.get_learning_progress(user_id)}

    def process_message(self, user_id, message, context=None):
        self._user(user_id)
        if not isinstance(message,str) or not message.strip():
            raise ValueError('Messaggio richiesto')
        self._active_user = user_id
        context = dict(context or {})
        memory = self.allma.conversational_memory
        conversation = context.get('session_id')
        with memory.lock:
            owners = {u for u, chats in memory.conversations.items()
                      if any(c.id == conversation for c in chats)} if conversation else set()
        if owners and owners != {user_id}:
            raise PermissionError('Conversazione non disponibile')
        if not owners:
            conversation = self.allma.start_conversation(user_id)
        response = self.allma.process_message(user_id, conversation, message, context=context)
        emotion = getattr(response.emotion,'value',response.emotion)
        return {'response':response.content, 'session_id':conversation, 'is_valid':response.is_valid,
                'emotional_state':{'primary':emotion, 'detected':response.emotion_detected},
                'personality_state':{'topics':response.topics, 'metadata':deepcopy(response.metadata)}}

    def get_project_summary(self, project_id, *, user_id=None):
        if not project_id:
            raise ValueError('Project ID richiesto')
        project = self.project_tracker.get_project_summary(project_id)
        owner = user_id or self._active_user
        if not project or not owner or project['user_id'] != owner:
            raise ValueError('Progetto non disponibile')
        result = dict(project)
        result['id'] = str(result['id'])
        result['status'] = result['status'].replace('_',' ').title()
        return result

    def create_project(self, user_id, name, description='', metadata=None):
        self._user(user_id)
        if not isinstance(name,str) or not name.strip():
            raise ValueError('Nome richiesto')
        self._active_user = user_id
        project_id = self.project_tracker.create_project(user_id,name,description,metadata)
        if not project_id:
            raise ValueError('Progetto non creato')
        return str(project_id)

    def update_project(self, project_id, status, metadata=None, *, user_id=None):
        project = self.get_project_summary(project_id,user_id=user_id)
        normalized = status.casefold().strip().replace(' ','_')
        if normalized not in {'active','in_progress','paused','completed','archived'}:
            raise ValueError('Stato non valido')
        current = dict(project.get('metadata') or {})
        current.update(metadata or {})
        return self.project_tracker.update_project_status(project_id,normalized,current)

    def get_learning_progress(self, user_id):
        self._user(user_id)
        known = (user_id == self._active_user
                 or user_id in self.allma.conversational_memory.conversations
                 or user_id in self._settings.get('api_preferences').get('users',{}))
        if not known:
            raise ValueError('Utente non disponibile')
        return self.learner.get_learning_progress(user_id)

    def get_emotional_analysis(self, text):
        return self.emotional_core.analyze_text(text)

    def get_personality_insights(self, user_id):
        self._user(user_id)
        expression = self.allma.coalescence_processor.expression_view(user_id)
        return {'communication_style':expression,
                'learning_preferences':self._settings.get('api_preferences').get('users',{}).get(user_id,{}),
                'interaction_patterns':{'observations':expression.get('observations',0)}}

    def save_user_preferences(self, user_id, preferences):
        self._user(user_id)
        if not isinstance(preferences,dict) or any(not isinstance(k,str) for k in preferences):
            raise ValueError('Preferenze non valide')
        with self._settings.lock:
            state = deepcopy(self._settings.get('api_preferences'))
            state.setdefault('users',{})[user_id] = deepcopy(preferences)
            self._settings.put('api_preferences',state)
        return True

    def get_conversation_history(self, user_id, limit=50):
        self._user(user_id)
        if type(limit) is not int or limit < 0:
            raise ValueError('Limite non valido')
        with self.allma.conversational_memory.lock:
            messages = [m for m in self.allma.conversational_memory.messages
                        if (m.user_id or m.metadata.get('user_id')) == user_id]
            return [{'text':m.content,'timestamp':m.timestamp.isoformat(),'sender':m.role,
                     'metadata':deepcopy(m.metadata)} for m in (messages[-limit:] if limit else [])]

    def get_memory_data(self, user_id):
        if not user_id:
            return {'facts':{},'logs':[]}
        memory = self.allma.conversational_memory
        with memory.lock:
            facts = deepcopy(memory.user_data.get(user_id,{}))
        history = self.get_conversation_history(user_id,10)
        return {'facts':facts, 'logs':[{'role':m['sender'],'content':m['text'],
                    'timestamp':m['timestamp'],'is_thought':False} for m in history]}
