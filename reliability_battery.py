"""Fixed 60-scenario operational reliability battery; no universal quality score.

Writes the plan BEFORE running cases. Uses disposable data and scripted model
outputs for containment checks. Never changes production code or phone state.
"""
import argparse
import asyncio
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault('KIVY_NO_ARGS', '1')
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
CASES = []


def case(group, name, criterion):
    def register(fn):
        CASES.append((group, name, criterion, fn))
        return fn
    return register


def require(value, detail):
    if not value:
        raise AssertionError(detail)


def memory(path):
    from allma_model.memory_system.conversational_memory import ConversationalMemory
    return ConversationalMemory(load_persistent=False, storage_dir=str(path))


for name, texts, meta in [
    ('empty', [], {}), ('single', ['ricordo di prova'], {}),
    ('unicode', ['Caffè 🌊 — città 日本語', 'e\u0301'], {}),
    ('long_text', ['testo lungo ' * 2000], {}),
    ('multiline', ['prima\nseconda\tultima'], {}),
    ('quotes', ['"citazione" e apostrofo: l’acqua'], {}),
    ('nested_metadata', ['contesto'], {'nested': {'values': [1, True, None]}}),
    ('ten_turns', [f'turno {i}' for i in range(10)], {}),
    ('empty_content', [''], {}),
    ('mixed_roles', ['richiesta', 'risposta', 'correzione', 'conferma'], {'is_valid': True}),
]:
    def run(path, texts=texts, meta=meta, name=name):
        from allma_model.memory_system.conversational_memory import ConversationalMemory
        store = memory(path)
        chat = store.create_conversation('u')
        store.save_memory()
        for i, text in enumerate(texts):
            store.store_message(chat, text, dict(meta), 'assistant' if name == 'mixed_roles' and i % 2 else 'user', 'u')
        reopened = ConversationalMemory(storage_dir=str(path))
        require([m.content for m in reopened.messages] == texts, 'Restart altered message contents')
        require(all(m.user_id == 'u' and m.metadata == meta for m in reopened.messages), 'Owner or metadata changed')
        require(reopened.conversations['u'][0].id == chat, 'Conversation identifier changed')
    case('persistence', name, 'Restart preserves exact content, owner, metadata and conversation ID')(run)


for name, mutation in [
    ('root_list', lambda d: []),
    ('root_null', lambda d: None),
    ('bad_timestamp', lambda d: {**d, 'messages': [{**d['messages'][0], 'timestamp': 'not-a-date'}]}),
    ('late_bad_record', lambda d: {**d, 'messages': d['messages'] + [{'content': 'incomplete'}]}),
    ('wrong_metadata', lambda d: {**d, 'messages': [{**d['messages'][0], 'metadata': []}]}),
    ('wrong_user_data', lambda d: {**d, 'user_data': []}),
]:
    def run(path, mutation=mutation):
        store = memory(path)
        store.store_message('c', 'originale', {}, 'user', 'u')
        before = store.messages
        target = path/'allma_memory.json'
        original = json.dumps(mutation(json.loads(target.read_text())))
        target.write_text(original)
        require(store.load_memory() is False, 'Invalid snapshot accepted')
        require(store.messages is before, 'Failed load replaced live memory')
        try:
            store.save_memory()
        except RuntimeError:
            pass
        else:
            raise AssertionError('Damaged original could be overwritten')
        require(target.read_text() == original, 'Damaged archive was modified')
    case('failure_recovery', name, 'Reject malformed snapshot and preserve original archive and RAM')(run)


@case('failure_recovery', 'write_failure_message', 'Failed message write leaves disk AND live messages unchanged; retry is safe')
def failed_message(path):
    store = memory(path)
    store.store_message('c', 'originale', {}, 'user', 'u')
    before = list(store.messages)
    disk = (path/'allma_memory.json').read_bytes()
    with patch.object(store, 'save_memory', side_effect=OSError('simulated disk full')):
        try:
            store.store_message('c', 'non confermato', {}, 'user', 'u')
        except OSError:
            pass
        else:
            raise AssertionError('Write failure acknowledged as success')
    require((path/'allma_memory.json').read_bytes() == disk, 'Previous disk snapshot lost')
    require(store.messages == before, f'Uncommitted message remains in RAM: {len(store.messages)} vs {len(before)}')


@case('failure_recovery', 'write_failure_context', 'Failed context update leaves prior live and saved context unchanged')
def failed_context(path):
    store = memory(path)
    chat = store.create_conversation('u')
    store.update_context(chat, {'setting': 'before'})
    with patch.object(store, 'save_memory', side_effect=OSError('simulated permission denied')):
        try:
            store.update_context(chat, {'setting': 'after'})
        except OSError:
            pass
        else:
            raise AssertionError('Failed save acknowledged')
    require(store.conversations['u'][0].metadata['setting'] == 'before', 'Uncommitted context remains in RAM')


@case('failure_recovery', 'reload_after_repair', 'Successful explicit reload unlocks writes without inventing or losing messages')
def reload_repaired(path):
    store = memory(path)
    store.store_message('c', 'conservato', {}, 'user', 'u')
    target = path/'allma_memory.json'
    valid = target.read_bytes()
    target.write_text('{broken')
    require(not store.load_memory(), 'Broken JSON accepted')
    target.write_bytes(valid)
    require(store.load_memory(), 'Valid repair rejected')
    store.save_memory()
    require(store.messages[0].content == 'conservato', 'Repair lost message')


@case('failure_recovery', 'feedback_save_failure', 'Failed feedback save rolls back tendencies and can retry')
def failed_feedback(path):
    from allma_model.core.personality_coalescence import CoalescenceProcessor
    processor = CoalescenceProcessor(str(path/'state.db'))
    before = dict(processor.core.personality_traits)
    with patch.object(processor._state_store, 'put', side_effect=OSError('simulated failure')):
        try:
            processor.observe_feedback('u', 'event', True, ['emotion'])
        except OSError:
            pass
    require(processor.core.personality_traits == before and not processor._feedback_events, 'Failed feedback learned')
    require(processor.observe_feedback('u', 'event', True, ['emotion']), 'Feedback retry lost')


for i in range(4):
    def run(path, i=i):
        from allma_model.core.vector_memory_engine import VectorMemoryEngine
        engine = VectorMemoryEngine(str(path/'vectors.db'))
        engine.add('owner', f'segreto{i} dato personale')
        engine.add('other', f'pubblico{i} dato diverso')
        require(not engine.search('stranger', f'segreto{i}'), 'Unknown user recovered private content')
        require(all('seg reto' not in r['content'] and f'segreto{i}' not in r['content'] for r in engine.search('other', f'segreto{i}')), 'Other user recovered private content')
    case('isolation', f'vector_owner_{i}', 'Search never returns another owner’s text')(run)


@case('isolation', 'personal_name', 'User name requires that user’s declaration, not another user or model output')
def names(path):
    from allma_model.core.autobiographical_identity import grounded_reply
    store = memory(path)
    store.store_message('c', 'Mi chiamo Ada.', {}, 'user', 'other')
    store.store_message('c', 'Ti chiami Luna.', {'is_valid': True}, 'assistant', 'u')
    require(grounded_reply('Come mi chiamo?', store, 'u')[1] == 'no_evidence', 'Foreign name accepted')


@case('isolation', 'incremental_owner', 'Related knowledge and topics exclude other users and ownerless legacy records')
def learned_owner(path):
    from allma_model.learning_system.incremental_learning import IncrementalLearner, LearningUnit, ConfidenceLevel
    learner = IncrementalLearner(str(path/'learning.json'))
    for source, owner, text in [('user_u','u','gatto domestico'), ('user_other','other','gatto nero'), ('legacy',None,'gatto antico')]:
        learner.add_learning_unit(LearningUnit('animali', text, source, ConfidenceLevel.HIGH, datetime.now(), {'user_id': owner}))
    require([u.content for u in learner.find_related_knowledge('gatto', user_id='u')] == ['gatto domestico'], 'Foreign learning retrieved')
    require(len(learner.get_knowledge_by_topic('animali', user_id='u')) == 1, 'Foreign topic retrieved')


@case('isolation', 'concept_owner', 'Personal concepts with identical names remain distinct')
def concept_owner(path):
    from allma_model.memory_system.knowledge_memory import KnowledgeMemory
    store = KnowledgeMemory(str(path/'concepts.db'))
    store.add_concept('preferenza', {'explanation': 'mare'}, user_id='u')
    store.add_concept('preferenza', {'explanation': 'montagna'}, user_id='other')
    require(store.get_concept('preferenza', user_id='u')['explanation'] == 'mare', 'Concept overwritten by other user')
    require(store.get_concept('preferenza') is None, 'Personal concept exposed as global')


@case('isolation', 'dream_owner', 'Another user cannot confirm, correct or retrieve a private dream hypothesis')
def dream_owner(path):
    from allma_model.core.dream_system.review_store import DreamReviewStore
    store = DreamReviewStore(path/'dreams.db')
    store.ingest([{'user_id':'u','text':'ipotesi privata','timestamp':datetime.now().isoformat()}])
    row = store.list('u')[0]
    require(store.list('other') == [], 'Foreign dream listed')
    try:
        store.review('other', row['id'], 'confirm')
    except ValueError:
        pass
    else:
        raise AssertionError('Foreign dream could be reviewed')


@case('isolation', 'recall_owner', 'Confirmed answers are not reusable by another owner')
def recall_owner(path):
    from allma_model.learning_system.answer_recall import AnswerRecall
    store = AnswerRecall(path/'recall.json')
    store.observe('key','u','Spiega la fotosintesi','Le piante usano la luce.','event')
    store.feedback('key','u','a',True)
    store.feedback('key','u','b',True)
    require(store.lookup('key','u') is not None, 'Own confirmed answer unavailable')
    require(store.lookup('key','other') is None, 'Foreign confirmed answer retrieved')


@case('isolation', 'delivery_owner', 'Delivery preferences remain attributed after restart')
def delivery_owner(path):
    from allma_model.learning_system.message_delivery import MessageDelivery
    store = MessageDelivery(path/'delivery.json')
    store.learn('u','complete')
    store.learn('other','progressive')
    reopened = MessageDelivery(path/'delivery.json')
    require(reopened.choose('u','Spiega il mare')[0] == 'complete', 'Own preference lost')
    require(reopened.choose('stranger','Spiega il mare')[0] == 'progressive', 'Preference leaked')


for seed in range(5):
    def run(path, seed=seed):
        from allma_model.utils.answer_stream import AnswerStream
        from allma_model.utils.thinking_stream import ThinkingStream
        answer = 'Una spiegazione leggibile. Acqua e luce 🌊.'
        raw = 'Ragionamento privato.</think>' + answer
        rng = random.Random(seed)
        parser = ThinkingStream(in_thought=True)
        events = []
        stream = AnswerStream('Spiega un fenomeno', events.append)
        pos = 0
        while pos < len(raw):
            size = rng.randint(1,8)
            for event in parser.feed(raw[pos:pos+size]):
                if event['type'] == 'answer':
                    stream.feed(event['content'])
            pos += size
        for event in parser.feed('',final=True):
            if event['type'] == 'answer':
                stream.feed(event['content'])
        stream.feed('',final=True)
        require(''.join(e['content'] for e in events) == answer, 'Unicode corrupted or reasoning leaked')
    case('output_guards', f'stream_boundary_{seed}', 'Arbitrary chunks preserve answer and never expose reasoning as final text')(run)


@case('output_guards', 'negated_repetition', 'Negation never disables loop protection')
def negated_repeat(path):
    from allma_model.utils.repetition_guard import requested_repetition
    for instruction in ['Non ripetere 6 volte ghiandole', 'Evita di ripetere 8 volte', 'Do not repeat 6 times']:
        require(not requested_repetition(instruction), f'Negated instruction allowed repetition: {instruction}')


@case('output_guards', 'identity_tail', 'Unsafe name in a later sentence is never emitted')
def identity_tail(path):
    from allma_model.utils.answer_stream import AnswerStream
    events = []
    stream = AnswerStream('Spiega il mare', events.append)
    for token in ['Il mare è salato. ', 'Mi ', 'chiamo ', 'Sophia.']:
        stream.feed(token)
    stream.feed('',final=True)
    require(stream.rejected and 'Sophia' not in ''.join(e['content'] for e in events), 'False identity reached display')


@case('output_guards', 'strict_json', 'Only parseable JSON satisfies explicit JSON contract')
def json_contract(path):
    from allma_model.utils.output_contract import requested_contract, valid_contract
    kind = requested_contract('Rispondi solo in JSON')
    require(kind == 'json' and valid_contract('{"ok":true}',kind), 'Valid JSON rejected')
    require(not valid_contract('Ecco: {"ok":true}',kind) and not valid_contract('{"x":NaN}',kind), 'Invalid JSON accepted')


@case('output_guards', 'sentence_count_with_quote', 'A known three-sentence answer does not satisfy an exact two-sentence request')
def sentence_quote(path):
    from allma_model.utils.output_contract import valid_sentence_count
    require(not valid_sentence_count('"Prima". Seconda. Terza.',2), 'Ambiguous sentence parser accepts nonconforming output')


@case('output_guards', 'borrowed_experience', 'Concrete first-person appropriation is detected without blocking second-person support')
def borrowed(path):
    from allma_model.utils.output_contract import borrowed_user_experience
    request = 'Sono felice ma ho paura del colloquio.'
    require(borrowed_user_experience('Sono felice ma ho paura del colloquio.',request), 'Borrowed feelings accepted')
    require(not borrowed_user_experience('Puoi essere felice e avere paura insieme.',request), 'Legitimate support blocked')


for i in range(5):
    def run(path, i=i):
        from allma_model.memory_system.conversational_memory import ConversationalMemory
        store = memory(path)
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda n: store.store_message('c',f'turno {i}:{n}',{},'user','u'),range(16)))
        reopened = ConversationalMemory(storage_dir=str(path))
        require(len(reopened.messages) == 16 and len({m.content for m in reopened.messages}) == 16, 'Concurrent writes lost or duplicated records')
    case('lifecycle_concurrency',f'concurrent_memory_{i}','All acknowledged concurrent writes survive restart once')(run)


for i in range(3):
    def run(path, i=i):
        from allma_model.core.event_bus import EventBus
        async def exercise():
            bus = EventBus()
            for _ in range(4):
                task = asyncio.create_task(bus.consume_loop())
                await asyncio.sleep(0)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                require(not bus.get_stats()['running'], 'Cancelled consumer remains marked running')
        asyncio.run(exercise())
    case('lifecycle_concurrency',f'bus_restart_{i}','Repeated cancellation permits consumer restart without stale state')(run)


@case('lifecycle_concurrency','queued_cancel','Queued turn cancels without disturbing the active owner')
def queued_cancel(path):
    from allma_model.core.allma_core import ALLMACore
    from allma_model.utils.generation_control import GenerationCancelled
    core = ALLMACore.__new__(ALLMACore)
    core._turn_lock = threading.Lock()
    core._lock = threading.RLock()
    core._shutdown_event = threading.Event()
    core._user_active = threading.Event()
    core._turn_lock.acquire()
    cancel = threading.Event()
    cancel.set()
    try:
        core.process_message('u','c','test',cancel_event=cancel)
    except GenerationCancelled:
        pass
    else:
        raise AssertionError('Cancelled queued turn entered pipeline')
    require(core._turn_lock.locked(), 'Cancelled waiter released another caller’s lock')
    core._turn_lock.release()


@case('lifecycle_concurrency','native_cancel','Cancellation closes iterator and releases native inference lock')
def native_cancel(path):
    from allma_model.llm.mobile_gemma_wrapper import MobileGemmaWrapper
    from allma_model.utils.generation_control import GenerationCancelled
    wrapper = MobileGemmaWrapper.__new__(MobileGemmaWrapper)
    wrapper.inference_lock = threading.Lock()
    wrapper.n_ctx = 2048
    cancel = threading.Event()
    closed = []
    def output():
        try:
            yield {'choices':[{'text':'primo'}]}
            yield {'choices':[{'text':'secondo'}]}
        finally:
            closed.append(True)
    wrapper.llm = Mock(return_value=output())
    wrapper.llm.tokenize.return_value = [1]
    try:
        wrapper.generate('prompt',max_tokens=8,callback=lambda _:cancel.set(),cancel_event=cancel)
    except GenerationCancelled:
        pass
    else:
        raise AssertionError('Cancelled inference returned a valid completion')
    require(closed == [True] and not wrapper.inference_lock.locked(), 'Inference resources not released')


CORE_CASES = [
    ('origin','Come ti chiami?','Mi chiamo ALLMA.','origin_identity',True),
    ('unknown_name','Come mi chiamo?',None,'no_evidence',True),
    ('unknown_preference','Qual è il tuo colore preferito?',None,'no_evidence',True),
    ('no_shared_history','Abbiamo mai parlato di Roma?',None,'no_evidence',True),
    ('arithmetic','Quanto fa 18 + 24? Rispondi solo con un numero','42','verified_calculation',True),
    ('arithmetic_negative','Quanto fa 7 - 19? Rispondi solo con un numero','-12','verified_calculation',True),
    ('safe_model','Spiega in breve come funziona una bicicletta.','La bicicletta usa i pedali.',None,True),
    ('hostile_identity','Spiega in breve come funziona una bicicletta.','Mi chiamo Sophia.',None,False),
    ('hostile_loop','Spiega in breve come funziona una bicicletta.','ghiandole '*12,None,False),
    ('hostile_format','Descrivi una bicicletta. Rispondi solo in JSON.','Ecco una bicicletta.',None,False),
]
for name, request, expected, source, valid in CORE_CASES:
    def run(path, name=name, request=request, expected=expected, source=source, valid=valid):
        from allma_model.core.allma_core import ALLMACore
        core = ALLMACore(mobile_mode=True,db_path=str(path/'core.db'))
        try:
            core._ensure_mobile_llm = lambda:None
            core._llm = Mock()
            core._llm.generate.return_value = expected or 'Risposta del modello di prova.'
            core._llm.get_generation_meta.return_value = {'finish_reason':'stop'}
            chat = core.start_conversation('u')
            response = core.process_message('u',chat,request)
            require(response.is_valid is valid, f'Validity {response.is_valid}, expected {valid}')
            if source:
                require(response.metadata.get('source') == source, f'Source {response.metadata.get("source")}, expected {source}')
                core._llm.generate.assert_not_called()
            if valid and expected:
                require(response.content == expected, f'Unexpected response: {response.content}')
            require(core.conversational_memory.messages[-1].content == response.content, 'Returned and persisted answers differ')
            if not valid:
                require(not core.answer_recall.records, 'Invalid answer learned for recall')
        finally:
            core.close()
    case('core_integration',name,'Real core preserves source, validity, persisted answer and nonlearning of invalid output; scripted LLM')(run)


def run_battery(output, *, scope=None, cancel_event=None, progress_callback=None):
    args = SimpleNamespace(output=Path(output).resolve())
    args.output.mkdir(parents=True,exist_ok=True)
    require(len(CASES) == 60 and set(Counter(c[0] for c in CASES).values()) == {10}, 'Battery is not balanced 6x10')
    plan = {'version':'operational-reliability-v1','score':'100 * passed / 60; 10 scenarios per category',
            'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'scope':scope or 'Mac source code; synthetic data; scripted model/iterator only, no GGUF inference or Android UI',
            'not_measured':['general probability of reliability','native APK reliability','model factual correctness','battery and thermal endurance'],
            'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'allma_model').rglob('*.py'))},
            'cases':[{'group':group,'name':name,'criterion':criterion} for group,name,criterion,_ in CASES]}
    (args.output/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
    results = []
    started = time.perf_counter()
    previous = Path.cwd()
    with tempfile.TemporaryDirectory(prefix='allma-reliability-') as temporary:
        base = Path(temporary)
        for group,name,criterion,fn in CASES:
            if cancel_event is not None and cancel_event.is_set():
                break
            path = base/(group+'_'+name)
            path.mkdir()
            os.chdir(path)
            tick = time.perf_counter()
            error = None
            try:
                fn(path)
            except Exception as failure:
                error = {'type':type(failure).__name__,'detail':str(failure)}
            finally:
                os.chdir(previous)
            row = {'group':group,'name':name,'criterion':criterion,'passed':error is None,
                   'seconds':time.perf_counter()-tick,'error':error}
            results.append(row)
            if progress_callback:
                progress_callback(len(results), len(CASES), name)
            (args.output/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
            print(json.dumps({'case':name,'passed':row['passed'],'error':error},ensure_ascii=False),flush=True)
    groups = {}
    for group in sorted({c[0] for c in CASES}):
        rows = [r for r in results if r['group'] == group]
        groups[group] = {'passed':sum(r['passed'] for r in rows),'total':len(rows)}
        groups[group]['percent'] = 100*groups[group]['passed']/groups[group]['total'] if rows else None
    passed = sum(r['passed'] for r in results)
    summary = {'scope':plan['scope'],'passed':passed,'total':len(results),'percent':100*passed/len(results) if len(results)==len(CASES) else None, 'complete':len(results)==len(CASES),
               'groups':groups,'failures':[r for r in results if not r['passed']],
               'seconds':time.perf_counter()-started,'all_sources_unchanged':all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in plan['sources'].items()),
               'statistical_generalization':'Not established: fixed, correlated challenge cases; no confidence interval for unseen field usage.'}
    (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run_battery(args.output)


if __name__ == '__main__':
    main()
