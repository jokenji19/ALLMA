"""Recoverable post-answer updates, sourced only from durable admitted history.

The conversation archive contains the intent alongside its accepted answer.
SQLite indexes pending work, not a second copy of conversation text. Each
component persists its sequence checkpoint with the change itself, so a crash
between that change and its journal acknowledgement cannot repeat learning.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import logging
from pathlib import Path
import sqlite3
import threading
import uuid

from allma_model.core.autobiographical_identity import POLICY_VERSION
from allma_model.utils.persistence import StateRecoveryRequired

EFFECTS = ('answer_recall', 'incremental_learning', 'knowledge_memory',
           'neuroplasticity', 'identity_state')


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


class DeliveryUpdates:
    def __init__(self, core):
        self.core = core
        self.path = str(Path(core.db_path).resolve())
        self.lock = threading.RLock()
        self.needs_sync = True
        self.last_sequence = 0
        self._initialized = False
        for name in ('answer_recall', 'incremental_learner', 'identity_engine_v5', 'neuroplasticity_v5', 'coalescence_processor', 'goal_progress'):
            component = getattr(core, name, None)
            try:
                value = getattr(component, 'delivery_checkpoint', 0)
            except StateRecoveryRequired:
                # Durable history supplies the sequence even when one component
                # needs recovery. Its writes still fail closed in _apply.
                value = 0
            if name == 'coalescence_processor':
                value = getattr(component,'experience_checkpoint',0)
            if type(value) is int:
                self.last_sequence = max(self.last_sequence, value)
        # Reconstruct the high-water mark even if the journal is temporarily
        # unavailable. Ordering is independent of calendar and clock rollback.
        memory=core.conversational_memory
        if getattr(memory,'_history_store',None) is not None:
            self.last_sequence=max(self.last_sequence,getattr(memory,'_history_highwater',0))
        else:
            for record in self._records():
                for key in ('experience_update','delivery_update'):
                    intent = record.metadata.get(key)
                    if isinstance(intent,dict) and type(intent.get('sequence')) is int:
                        self.last_sequence = max(self.last_sequence,intent['sequence'])

    def _next_sequence(self):
        if not self._initialized:
            try:
                self._ensure()
            except sqlite3.Error:
                pass  # Durable history can reconstruct the missing journal.
        if not 0 <= self.last_sequence < 2**53-1:
            raise ValueError('Delivery sequence requires format migration')
        self.last_sequence += 1
        return self.last_sequence

    def _ensure(self):
        if self._initialized:
            return
        with sqlite3.connect(self.path) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS delivery_updates (
                event TEXT PRIMARY KEY, sequence INTEGER UNIQUE NOT NULL,
                intent TEXT NOT NULL, completed TEXT NOT NULL DEFAULT '[]',
                state TEXT NOT NULL DEFAULT 'pending', error TEXT)''')
            db.execute('CREATE INDEX IF NOT EXISTS delivery_pending ON delivery_updates(state,sequence)')
            self.last_sequence = max(self.last_sequence,
                db.execute('SELECT COALESCE(MAX(sequence),0) FROM delivery_updates').fetchone()[0])
        self._initialized = True

    @staticmethod
    def effects(intent):
        if intent.get('kind') == 'experience':
            return ('goal_tracking','personality_growth') if intent.get('goal_control') is not None else ('personality_growth',)
        return ('tool_learning',) if intent.get('kind')=='tool' else EFFECTS

    def prepare_user(self, user_id, conversation_id, text, response_context=None, *, goal_control=None):
        intent = {'version':1,'kind':'experience','event':uuid.uuid4().hex,'sequence':self._next_sequence(),
                'user':user_id,'conversation':conversation_id,'input_sha256':digest(text),
                'response_context':deepcopy(response_context)}
        if goal_control is not None:
            from allma_model.agency_system.goal_progress import valid_control
            if not valid_control(goal_control):raise ValueError('Invalid goal control')
            intent['goal_control'] = deepcopy(goal_control)
        return intent

    @staticmethod
    def eligible(record):
        meta = record.metadata
        reference = meta.get('delivery_update')
        if isinstance(reference,dict) and reference.get('kind')=='tool':
            return (record.role=='assistant' and meta.get('is_valid') is True and meta.get('knowledge_verified') is True
                    and meta.get('identity_policy')==POLICY_VERSION
                    and meta.get('source') in ('verified_text_count','verified_calculation')
                    and meta.get('tool_experience')==meta['delivery_update'].get('tool_descriptor'))
        return (record.role == 'assistant' and meta.get('is_valid') is True
                and meta.get('identity_policy') == POLICY_VERSION
                and meta.get('source') == 'model_generated'
                and meta.get('generation', {}).get('status') == 'completed')

    def prepare(self, user_id, conversation_id, question, answer, topic, recall_key, violations):
        with self.core.conversational_memory.lock:
            source = next((m for m in reversed(self.core.conversational_memory.messages)
                if m.role == 'user' and m.user_id == user_id and m.conversation_id == conversation_id
                and m.content == question), None)
        if source is None:
            raise ValueError('No durable input for delivery updates')
        return {'version':1, 'kind':'answer', 'event':uuid.uuid4().hex, 'sequence':self._next_sequence(),
                'user':user_id, 'conversation':conversation_id,
                'input_timestamp':source.timestamp.isoformat(),
                'input_sha256':digest(question), 'answer_sha256':digest(answer),
                'topic':topic, 'recall_key':recall_key, 'violations':list(violations)}

    def prepare_tool(self, user_id, conversation_id, question, answer, descriptor):
        intent=self.prepare(user_id,conversation_id,question,answer,'tools','tools',[])
        intent.update(kind='tool',tool_descriptor=deepcopy(descriptor))
        return intent

    @staticmethod
    def validate(intent):
        if (not isinstance(intent, dict) or type(intent.get('version')) is not int or intent['version'] != 1
                or type(intent.get('sequence')) is not int or not 0 < intent['sequence'] < 2**53
                or any(not isinstance(intent.get(k),str) or not intent[k]
                       for k in ('event','user','conversation','input_sha256'))
                or intent.get('kind','answer') not in ('answer','experience','tool')):
            raise ValueError('Invalid delivery update reference')
        if intent.get('kind')=='experience':
            if intent.get('response_context') is not None and not isinstance(intent['response_context'],dict):
                raise ValueError('Invalid experience context')
            if intent.get('goal_control') is not None:
                from allma_model.agency_system.goal_progress import valid_control
                if not valid_control(intent['goal_control']):raise ValueError('Invalid goal experience')
        elif (any(not isinstance(intent.get(k),str) or not intent[k]
                  for k in ('input_timestamp','answer_sha256','topic','recall_key'))
                or not isinstance(intent.get('violations'),list)
                or any(not isinstance(v,str) for v in intent['violations'])):
            raise ValueError('Invalid answer update reference')

    def _enqueue_in(self,db,intent):
        self.validate(intent)
        encoded=json.dumps(intent,sort_keys=True,ensure_ascii=False)
        row=db.execute('SELECT intent FROM delivery_updates WHERE event=?',(intent['event'],)).fetchone()
        if row is not None:
            if row[0]!=encoded:raise ValueError('Delivery event changed after storage')
        else:
            db.execute('INSERT INTO delivery_updates(event,sequence,intent) VALUES (?,?,?)',
                       (intent['event'],intent['sequence'],encoded))
        self.last_sequence=max(self.last_sequence,intent['sequence'])

    def _enqueue(self,intent):
        self._ensure()
        with sqlite3.connect(self.path) as db:self._enqueue_in(db,intent)

    def _records(self):
        memory=self.core.conversational_memory
        with memory.lock:
            return memory.messages if getattr(memory,'_history_store',None) is not None else list(memory.messages)

    @contextmanager
    def _claim(self):
        # The OS releases the lock on process death, allowing immediate recovery.
        import fcntl
        with open(self.path+'.delivery.lock','a') as handle:
            try:
                fcntl.flock(handle,fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                yield False
                return
            try:
                yield True
            finally:
                fcntl.flock(handle,fcntl.LOCK_UN)

    def _resolve(self, intent, records):
        self.validate(intent)
        if intent.get('kind')=='experience':
            source = next((m for m in records if m.role=='user'
                and m.user_id==intent['user'] and m.conversation_id==intent['conversation']
                and m.metadata.get('experience_update')==intent and digest(m.content)==intent['input_sha256']),None)
            return (source,None) if source is not None else None
        answer = next((m for m in records if m.role=='assistant'
            and m.metadata.get('delivery_update',{}).get('event')==intent['event']),None)
        source = next((m for m in records if m.role=='user' and m.user_id==intent['user']
            and m.conversation_id==intent['conversation']
            and m.timestamp.isoformat()==intent['input_timestamp']
            and digest(m.content)==intent['input_sha256']),None)
        if (answer is None or source is None or not self.eligible(answer)
                or answer.user_id != intent['user'] or answer.conversation_id != intent['conversation']
                or answer.metadata.get('delivery_update') != intent
                or digest(answer.content) != intent['answer_sha256']):
            return None
        return source,answer

    def _apply(self, action, intent, source, answer):
        core, sequence = self.core, intent['sequence']
        if action == 'goal_tracking':
            from allma_model.utils.goal_dialogue import command
            control = intent['goal_control']
            if command(source.content) != control['request']:
                raise ValueError('Goal control differs from durable user command')
            if control['kind'] == 'adopt_plan':
                from allma_model.agency_system.goal_plans import verify_saved
                if not verify_saved(core.conversational_memory,intent['user'],control['selected_plan']):
                    raise ValueError('Plan proposal has no matching durable source')
            core.goal_progress.apply(intent['user'],control,
                {'event':intent['event'],'conversation':intent['conversation'],'timestamp':source.timestamp.isoformat(),
                 'input_sha256':intent['input_sha256'],'source':'user_report'},sequence)
        elif action == 'personality_growth':
            core.coalescence_processor.observe_interaction(intent['user'],intent['event'],source.content,
                response_context=intent.get('response_context'),experience_sequence=sequence)
        elif action == 'tool_learning':
            from allma_model.learning_system.tool_strategy_learning import ToolStrategyLearning, fingerprint
            descriptor=intent.get('tool_descriptor')
            if not ToolStrategyLearning.valid_descriptor(descriptor) or descriptor['owner']!=fingerprint(intent['user']):
                raise ValueError('Invalid tool experience reference')
            learner=getattr(getattr(core,'meta_learner',None),'tool_learning',None)
            if learner is None:raise RuntimeError('Tool learning unavailable')
            outcome=learner.observe(intent['user'],descriptor,delivery_sequence=sequence)
            if outcome['status'] not in ('observed','duplicate','stale'):
                raise ValueError('Tool experience not admitted')
        elif action == 'answer_recall':
            core.answer_recall.observe(intent['recall_key'],intent['user'],source.content,answer.content,
                intent['event'],delivery_sequence=sequence)
        elif action == 'incremental_learning':
            core.incremental_learner.learn_from_interaction({'input':source.content,
                'response':answer.content,'response_verified':False,'feedback':'neutral','topic':intent['topic']},
                intent['user'],delivery_sequence=sequence)
        elif action == 'knowledge_memory':
            core.knowledge_memory.store_knowledge(
                'Utente: '+source.content[:150]+' | [dichiarazione utente, non conoscenza verificata]',
                metadata={'topic':intent['topic'],'type':'user_statement','source_kind':'user_statement',
                          'user_id':intent['user'],'knowledge_verified':False}, delivery_event=intent['event'])
        elif action == 'neuroplasticity':
            if core.neuroplasticity_v5 is None:
                raise RuntimeError('Neuroplasticity unavailable')
            core.neuroplasticity_v5.analyze(intent['violations'],delivery_sequence=sequence)
        elif action == 'identity_state':
            if core.identity_engine_v5 is None:
                raise RuntimeError('Identity state unavailable')
            core.identity_engine_v5.update_state(answer.content,intent['violations'],delivery_sequence=sequence)
        else:
            raise ValueError('Unknown delivery update')

    def _ack(self, event, completed):
        with sqlite3.connect(self.path) as db:
            row=db.execute('SELECT intent FROM delivery_updates WHERE event=?',(event,)).fetchone()
            total=len(self.effects(json.loads(row[0])))
            db.execute('UPDATE delivery_updates SET completed=?,state=?,error=NULL WHERE event=?',
                (json.dumps(completed),'done' if len(completed)==total else 'pending',event))

    def recover(self, *, synchronize=False):
        report = {'status':'completed','recovered':0,'pending':0,'failed_action':None}
        with self.lock:
          try:
            with self._claim() as claimed:
                if not claimed:
                    return dict(report,status='busy')
                self._ensure()
                records = None
                if synchronize or self.needs_sync:
                    records = self._records()
                    # The journal orders by sequence itself. Stream historical
                    # intents into one transaction instead of retaining/sorting
                    # every old intent and opening a DB per message.
                    with sqlite3.connect(self.path) as db:
                        for record in records:
                            keys=[]
                            if 'delivery_update' in record.metadata and self.eligible(record):keys.append('delivery_update')
                            if record.role=='user' and 'experience_update' in record.metadata:keys.append('experience_update')
                            for key in keys:self._enqueue_in(db,record.metadata[key])
                    self.needs_sync = False
                with sqlite3.connect(self.path) as db:
                    rows = db.execute("SELECT event,intent,completed FROM delivery_updates WHERE state='pending' ORDER BY sequence LIMIT 32").fetchall()
                if rows and records is None:
                    records = self._records()
                for event,encoded,done in rows:
                    intent,completed = json.loads(encoded),json.loads(done)
                    effects = self.effects(intent)
                    if (not isinstance(completed,list) or completed != list(effects[:len(completed)])):
                        raise ValueError('Invalid delivery checkpoint order')
                    resolved = self._resolve(intent,records)
                    if resolved is None:
                        with sqlite3.connect(self.path) as db:
                            db.execute("UPDATE delivery_updates SET state='abandoned',error='source_unavailable' WHERE event=?",(event,))
                        continue
                    for action in effects[len(completed):]:
                        report['failed_action'] = action
                        self.core.brain_activity.call('meta_learning' if action=='tool_learning' else 'coalescence' if action=='personality_growth' else
                            'learning' if action in EFFECTS[:3] else 'identity',
                            self._apply, action,intent,*resolved)
                        self._ack(event,completed+[action])
                        completed.append(action)
                    report['recovered'] += 1
                    report['failed_action'] = None
          except Exception as error:
            report.update(status='pending',error=type(error).__name__)
            self.needs_sync = True
            if 'event' in locals():
                try:
                    with sqlite3.connect(self.path) as db:
                        db.execute('UPDATE delivery_updates SET error=? WHERE event=?', (type(error).__name__,event))
                except sqlite3.Error:
                    pass
            logging.warning('Delivery updates pending: %s',type(error).__name__)
          try:
            with sqlite3.connect(self.path) as db:
                report['pending'] = db.execute("SELECT COUNT(*) FROM delivery_updates WHERE state='pending'").fetchone()[0]
                if report['pending'] and report['status']=='completed':
                    report['status']='pending'
          except sqlite3.Error:
            report.update(status='unavailable',pending=None)
        return report

    def delivered(self, intent):
        try:
            self._enqueue(intent)
        except Exception as error:
            self.needs_sync = True
            logging.warning('Delivery journal deferred: %s',type(error).__name__)
            return {'status':'pending','pending':None,'failed_action':'delivery_journal','error':type(error).__name__}
        return self.recover()

    def observed_user(self, intent):
        report=self.delivered(intent)
        processor=self.core.coalescence_processor
        if processor.experience_checkpoint == intent['sequence']:
            return deepcopy(processor.experience_report)
        return {'status':'unavailable','recovery':report}
