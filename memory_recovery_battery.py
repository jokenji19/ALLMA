"""Fixed synthetic challenges for hybrid retrieval and interrupted learning.

Runs the production components in disposable archives. The scripted model does
not measure GGUF quality; the score describes only these sixteen challenges.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parent
CASES = []


def case(group, name, criterion):
    def register(fn):
        CASES.append((group, name, criterion, fn))
        return fn
    return register


def require(condition, message):
    if not condition:
        raise AssertionError(message)


for name, statement, query in [
    ('rain_cover', 'Ombrello nel mobile blu.', 'Cosa uso per ripararmi dalla pioggia?'),
    ('cutting', 'Forbici nel cassetto.', 'Cosa uso per tagliare la carta?'),
    ('power', 'Powerbank nello zaino.', 'Cosa uso per ricaricare il telefono fuori casa?'),
    ('temperature', 'Termometro nella scatola.', 'Cosa uso per misurare la febbre?'),
]:
    def run(path, statement=statement, query=query):
        from allma_model.core.vector_memory_engine import VectorMemoryEngine
        store = VectorMemoryEngine(str(path/'vectors.db'))
        store.add('u', statement, metadata={'role':'user'})
        rows = store.search('u', query, allowed_roles=('user',))
        require(rows and rows[0]['content']==statement, 'Functional paraphrase missed its source')
        require(rows[0]['retrieval']['world_truth_verified'] is False, 'Relevance claimed verification')
        reopened = VectorMemoryEngine(str(path/'vectors.db'))
        require(reopened.search('u',query)[0]['content']==statement, 'Restart changed retrieval')
    case('retrieval',name,'Functional description retrieves the original attributed source, also after restart')(run)


@case('retrieval','generic_abstention','Vague question without a concept does not select a personal object')
def generic(path):
    from allma_model.core.vector_memory_engine import VectorMemoryEngine
    store = VectorMemoryEngine(str(path/'vectors.db'))
    store.add('u','Ombrello nel mobile blu.',metadata={'role':'user'})
    require(not store.search('u','Dove ho messo quella cosa?'), 'Vague request invented an object')


@case('retrieval','owner_isolation','Concept retrieval cannot cross user boundaries')
def owner(path):
    from allma_model.core.vector_memory_engine import VectorMemoryEngine
    store = VectorMemoryEngine(str(path/'vectors.db'))
    store.add('other','Ombrello nel mobile blu.',metadata={'role':'user'})
    require(not store.search('u','Ripararmi dalla pioggia'), 'Foreign personal source returned')


@case('retrieval','revoked_sources','Revoked or superseded sources cannot displace the current original')
def revoked(path):
    from allma_model.core.vector_memory_engine import VectorMemoryEngine
    store = VectorMemoryEngine(str(path/'vectors.db'))
    store.add('u','Ombrello in cucina.',metadata={'role':'user','revoked':True})
    store.add('u','Ombrello in garage.',metadata={'role':'user','status':'superseded'})
    store.add('u','Ombrello nel mobile blu.',metadata={'role':'user'})
    rows=store.search('u','Ripararmi dalla pioggia',allowed_roles=('user',))
    require([r['content'] for r in rows]==['Ombrello nel mobile blu.'], 'Inactive source selected')


@case('retrieval','sqlite_batches','More than 999 candidates are fetched in bounded batches and role-filtered before limiting')
def batches(path):
    from allma_model.core.vector_memory_engine import VectorMemoryEngine
    store = VectorMemoryEngine(str(path/'vectors.db'))
    store.add('u','Ombrello nel mobile blu.',metadata={'role':'user'})
    for _ in range(1005):
        store.add('u','Ombrello in cucina.',metadata={'role':'assistant'})
    rows=store.search('u','ombrello',top_k=1,allowed_roles=('user',))
    require(rows and rows[0]['content']=='Ombrello nel mobile blu.', 'Batch fetch lost eligible source')


@contextmanager
def cores(path):
    from allma_model.core.allma_core import ALLMACore
    instances=[]
    def create():
        core=ALLMACore(mobile_mode=True,db_path=str(path/'core.db'))
        instances.append(core)
        core._ensure_mobile_llm=lambda:None
        core._llm=Mock()
        core._llm.generate.return_value='La luce bianca contiene diversi colori.'
        core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
        return core
    try:
        yield create
    finally:
        for core in instances:
            core.close()


def ask(core, text='Spiegami come funziona la luce bianca.'):
    return core.process_message('u',core.start_conversation('u'),text)


def counts(core):
    with sqlite3.connect(core.db_path) as db:
        knowledge=db.execute('SELECT COUNT(*) FROM knowledge_delivery_events').fetchone()[0]
    return (sum(len(v) for v in core.incremental_learner.knowledge_base.values()),
            sum(v['observations'] for v in core.answer_recall.records.values()),
            knowledge,core.identity_engine_v5.accepted_turns)


@case('recovery','failed_learning_write','Restart finishes pending learning once after a failed component write')
def failed_write(path):
    with cores(path) as create:
        core=create()
        with patch.object(core.answer_recall,'_save',side_effect=OSError('synthetic failure')):
            response=ask(core)
        require(response.is_valid and counts(core)==(0,0,0,0),'Failed update published partial learning')
        core.close()
        restored=create()
        require(counts(restored)==(1,1,1,1),'Restart did not complete all derived updates')
        require(restored.delivery_updates.recover()['pending']==0,'Pending work remains')
        require(counts(restored)==(1,1,1,1),'Second recovery duplicated learning')


for action in ('answer_recall','incremental_learning','knowledge_memory','neuroplasticity','identity_state'):
    def run(path, action=action):
        with cores(path) as create:
            core=create()
            original=core.delivery_updates._ack
            interrupted=False
            def ack(event,completed):
                nonlocal interrupted
                if completed[-1]==action and not interrupted:
                    interrupted=True
                    raise OSError('synthetic interrupted acknowledgement')
                return original(event,completed)
            with patch.object(core.delivery_updates,'_ack',side_effect=ack):
                require(ask(core).is_valid,'Synthetic answer rejected')
            require(interrupted,'Fault injection did not reach component')
            core.close()
            restored=create()
            require(restored.delivery_recovery['pending']==0,'Restart left pending work')
            require(counts(restored)==(1,1,1,1),'Acknowledgement interruption duplicated or lost an update')
    case('recovery','ack_'+action,'Component saved before journal acknowledgement is not applied twice after restart')(run)


@case('recovery','personality_write','Explicit preference survives interrupted coalescence write without model inference')
def personality_write(path):
    with cores(path) as create:
        core=create()
        with patch.object(core.coalescence_processor._state_store,'put',side_effect=OSError('synthetic failure')):
            ask(core,'Preferisco risposte brevi.')
        core._llm.generate.assert_not_called()
        core.close()
        restored=create()
        require(restored.coalescence_processor.expression_view('u')['preferences']['verbosity']=='brief',
                'Stored preference lost across interruption')
        require(counts(restored)==(0,0,0,0),'Native preference response created model-answer learning')


@case('recovery','personality_ack','A stored emotional experience is not counted again when acknowledgement fails')
def personality_ack(path):
    with cores(path) as create:
        core=create()
        original=core.delivery_updates._ack
        def ack(event,completed):
            if completed[-1]=='personality_growth':
                raise OSError('synthetic interrupted acknowledgement')
            return original(event,completed)
        with patch.object(core.delivery_updates,'_ack',side_effect=ack):
            ask(core,'Sono felice per il risultato di oggi.')
        before=core.coalescence_processor.emotion_growth_view('u')
        require(before['associations']['joy']['observations']==1,'Experience not observed once')
        core.close()
        restored=create()
        require(restored.coalescence_processor.emotion_growth_view('u')==before,'Experience counted twice')
        require(restored.delivery_recovery['pending']==0,'Experience still pending')


def run_battery(output, *, scope=None, cancel_event=None, progress_callback=None):
    require(len(CASES)==16,'Unexpected memory recovery plan size')
    return run_challenges(output,CASES,version='memory-recovery-v1',scope=scope,
        cancel_event=cancel_event,progress_callback=progress_callback)


def run_challenges(output, cases, *, version, scope=None, cancel_event=None,
                   progress_callback=None, harness_path=__file__):
    """Shared disposable runner; each battery keeps its explicit fixed plan."""
    output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    plan={'version':version,'scope':scope or 'Mac; synthetic archives; scripted model',
          'harness_sha256':hashlib.sha256(Path(harness_path).read_bytes()).hexdigest(),
          'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'cases':[{'group':g,'name':n,'criterion':c} for g,n,c,_ in cases],
          'not_measured':['unseen semantic queries','GGUF answer quality','battery','thermal endurance']}
    (output/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
    started=time.perf_counter()
    results=[]
    previous=Path.cwd()
    with tempfile.TemporaryDirectory(prefix='allma-memory-recovery-') as temporary:
        for group,name,criterion,fn in cases:
            if cancel_event is not None and cancel_event.is_set():
                break
            path=Path(temporary)/name
            path.mkdir()
            tick=time.perf_counter()
            error=None
            try:
                os.chdir(path)
                fn(path)
            except Exception as failure:
                error={'type':type(failure).__name__,'detail':str(failure)}
            finally:
                os.chdir(previous)
            results.append({'group':group,'name':name,'criterion':criterion,'passed':error is None,
                            'seconds':time.perf_counter()-tick,'error':error})
            (output/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
            if progress_callback:
                progress_callback(len(results),len(cases),name)
    groups={}
    for group in sorted({g for g,_,_,_ in cases}):
        rows=[r for r in results if r['group']==group]
        groups[group]={'passed':sum(r['passed'] for r in rows),'total':len(rows)}
    passed=sum(r['passed'] for r in results)
    complete=len(results)==len(cases)
    summary={'scope':plan['scope'],'passed':passed,'total':len(results),'planned':len(cases),
             'percent':100*passed/len(results) if complete else None,'complete':complete,
             'groups':groups,'failures':[r for r in results if not r['passed']],
             'seconds':time.perf_counter()-started}
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(run_battery(parser.parse_args().output),ensure_ascii=False,indent=2))
