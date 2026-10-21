"""Fixed 24-scenario challenge: long histories, scoped recall and sparse memory.

Synthetic archives only; no learned model weights or general semantic score.
"""
from datetime import datetime,timedelta
import sqlite3
from types import SimpleNamespace
from unittest.mock import Mock

from memory_recovery_battery import require,run_challenges

CASES=[]


def case(group,name,criterion):
    def register(fn):
        CASES.append((group,name,criterion,fn))
        return fn
    return register


def memory(path,texts,user='u',cid='long'):
    from allma_model.memory_system.conversational_memory import ConversationalMemory,Message
    store=ConversationalMemory(load_persistent=False,storage_dir=str(path))
    store.messages.extend(Message(cid,'user',text,datetime(2026,1,1)+timedelta(seconds=i),{},user)
                          for i,text in enumerate(texts))
    store.save_memory()
    return store


for limit in (0,1,6,50):
    def run(path,limit=limit):
        texts=[f'Turno sintetico {i}.' for i in range(300)]
        store=memory(path,texts)
        rows=store.get_conversation_history('long',limit=limit)
        require([r.content for r in rows]==(texts[-limit:] if limit else []),'Wrong recent history window')
    case('history','recent_'+str(limit),'A limited read returns the latest turns, ordered chronologically')(run)


for kind in ('prova','accesso','riferimento'):
    for variant in ('uncertain','hypothetical'):
        def run(path,kind=kind,variant=variant):
            from allma_model.utils.literal_recall import literal_code_reply
            other=next(k for k in ('prova','accesso','riferimento') if k!=kind)
            source=f'Il codice di {kind} è EsAtTo_006.'
            later=(f'Il codice di {other} potrebbe essere ALTRO-781.' if variant=='uncertain'
                   else f'Se il codice di {other} è ALTRO-781.')
            texts=[source]+[f'Appunto della pagina {i}.' for i in range(500)]+[later]
            rows=[SimpleNamespace(content=t) for t in texts]
            found=literal_code_reply(f'Dimmi il codice di {kind}. Rispondi solo con il codice.',rows)
            require(found and found[0]=='EsAtTo_006' and found[2]==[source],'Foreign category blocked exact source')
        case('scope',kind+'_'+variant,'Uncertainty affects its identifier category, never another known category')(run)


QUESTIONS=['Dove ho messo il mio ombrello?','Ti ricordi dove tengo il mio ombrello?',
           'Mi ricordi dove ho lasciato l’ombrello?','Sai dove si trova il mio ombrello?']
for index,query in enumerate(QUESTIONS):
    def run(path,query=query):
        from allma_model.core.vector_memory_engine import VectorMemoryEngine
        store=VectorMemoryEngine(str(path/'vectors.db'))
        source='Il mio ombrello è nell’armadio del corridoio.'
        store.add('u',source,metadata={'role':'user'})
        for i in range(80):store.add('u',QUESTIONS[i%4],metadata={'role':'user'})
        found=store.search('u',query,top_k=3,allowed_roles=('user',),exclude_query_replays=True)
        require([r['content'] for r in found]==[source],'Recall requests displaced factual source')
        require(store.count('u')==81,'Filtering erased the original history')
    case('replay','request_'+str(index),'Rephrased recall requests cannot hide the original report')(run)


for index,report in enumerate(['L’ombrello è nello zaino, dove ho messo la torcia?',
    'Ho lasciato il mio ombrello in ufficio. Ti ricordi?',
    'Dove ho messo il mio ombrello? Ieri lo tenevo nello zaino.']):
    def run(path,report=report):
        from allma_model.utils.memory_evidence import is_replayed_question
        require(not is_replayed_question(report,QUESTIONS[0]),'Mixed report removed')
        require(not is_replayed_question(QUESTIONS[0],'Quali domande ti ho fatto prima?'),'Past question removed')
    case('replay','mixed_'+str(index),'Mixed reports and explicit requests about previous questions remain available')(run)


@case('resources','large_vocabulary','Numeric cache and new SQLite entries scale with observed terms, not all document-term pairs')
def large(path):
    from allma_model.core.vector_memory_engine import VectorMemoryEngine
    store=VectorMemoryEngine(str(path/'vectors.db'))
    for i in range(1000):store.add('u',f'Appunto voce{i} tema{i}.',metadata={'role':'user'})
    require(store.search('u','voce799')[0]['content']=='Appunto voce799 tema799.','Large archive lost source')
    require(sum(v.nbytes for _,_,v in store._index)<256000,'Dense numeric cache remains')
    with sqlite3.connect(store.db_path) as db:
        require((db.execute('SELECT SUM(LENGTH(vector_blob)) FROM memories').fetchone()[0] or 0)<256000,
                'Dense blobs still copied at each insertion')


@case('resources','restart_and_cache','Sparse search survives cache release and restart without erasing original data')
def cache(path):
    from allma_model.core.vector_memory_engine import VectorMemoryEngine
    store=VectorMemoryEngine(str(path/'vectors.db'))
    store.add('u','Cavatappi nel cassetto.',metadata={'role':'user'})
    require(store.release_cache()==1,'Cache release lost record count')
    require(store.search('u','cavatappi')[0]['content']=='Cavatappi nel cassetto.','Cache release lost retrieval')
    reopened=VectorMemoryEngine(store.db_path)
    require(reopened.search('u','cavatappi')[0]['content']=='Cavatappi nel cassetto.','Restart lost retrieval')


for variant in ('name','revocation'):
    def run(path,variant=variant):
        from allma_model.core.autobiographical_identity import grounded_reply
        from allma_model.memory_system.conversational_memory import ConversationalMemory,Message
        store=memory(path,['Mi chiamo Elia.','Il mio colore preferito è verde.']+
            [f'Appunto della pagina {i}.' for i in range(300)]+['Ora mi chiamo Noemi.','Non ho più un colore preferito.'])
        store.messages.append(Message('other','user','Mi chiamo Andrea.',datetime.now(),{},'other'))
        store.save_memory()
        restored=ConversationalMemory(storage_dir=str(path))
        answer=grounded_reply('Come mi chiamo?' if variant=='name' else 'Qual è il mio colore preferito?',restored,'u')
        require(('Noemi' in answer[0] if variant=='name' else answer[1]=='personal_fact_revoked'),'Old or foreign personal state restored')
    case('history','personal_'+variant,'Current personal state survives a long history, foreign user and restart')(run)


@case('recovery','backlog','Recovery drains multiple bounded batches without counting an emotional experience twice')
def backlog(path):
    from allma_model.core.allma_core import ALLMACore
    core=ALLMACore(mobile_mode=True,db_path=str(path/'core.db'))
    try:
        cid=core.start_conversation('u')
        for i in range(40):
            core._store_user_message(cid,f'Sono felice per il risultato numero {i}.',{},'u')
            core.delivery_updates._enqueue(core.conversational_memory.messages[-1].metadata['experience_update'])
        require(core.delivery_updates.recover()['pending']==8,'First batch skipped or duplicated work')
        require(core.delivery_updates.recover()['pending']==0,'Second batch did not complete')
        before=core.coalescence_processor.emotion_growth_view('u')
        require(before['associations']['joy']['observations']==40,'Experiences counted incorrectly')
        core.delivery_updates.recover()
        require(core.coalescence_processor.emotion_growth_view('u')==before,'Repeated recovery changed growth')
    finally:core.close()


for inactive in ({'revoked':True},{'status':'superseded'}):
    def run(path,inactive=inactive):
        from allma_model.agency_system.operational_actions import retrieve_user_memory
        def row(text,meta):return SimpleNamespace(content=text,user_id='u',timestamp=None,metadata={'role':'user',**meta})
        store=SimpleNamespace(vector_engine=None,retrieve_relevant_context=Mock(return_value=[
            (.9,row('Valore precedente.',inactive)),(.8,row('Valore attuale.',{}))]))
        require([r['content'] for r in retrieve_user_memory(store,'u','valore')]==['Valore attuale.'],'Fallback restored inactive source')
    case('scope','fallback_'+next(iter(inactive)),'The alternative backend also rejects revoked or superseded records')(run)


def run_battery(output,*,scope=None,cancel_event=None,progress_callback=None):
    require(len(CASES)==24,'Unexpected long-history plan size')
    return run_challenges(output,CASES,version='long-history-v1',scope=scope,cancel_event=cancel_event,
                          progress_callback=progress_callback,harness_path=__file__)


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    print(json.dumps(run_battery(parser.parse_args().output),ensure_ascii=False,indent=2))
