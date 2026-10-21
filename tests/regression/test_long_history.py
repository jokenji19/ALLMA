"""Synthetic long histories, scoped uncertainty and resource contracts.

Cases are defined before production changes; no GGUF output is scored here.
"""
from datetime import datetime, timedelta
from types import SimpleNamespace
import sqlite3
from unittest.mock import Mock
import numpy as np
import pytest

from allma_model.core.vector_memory_engine import VectorMemoryEngine, _LightTfidf
from allma_model.memory_system.conversational_memory import ConversationalMemory, Message
from allma_model.utils.literal_recall import literal_code_reply
from allma_model.utils.memory_evidence import is_replayed_question


def populate(memory, texts, user='u', conversation='long'):
    start=datetime(2026,1,1)
    memory.messages.extend(Message(conversation,'user',text,start+timedelta(seconds=i),{},user)
                           for i,text in enumerate(texts))
    memory.save_memory()


@pytest.mark.parametrize('limit',[0,1,6,50])
def test_limited_history_returns_the_latest_turns_in_chronological_order(tmp_path,limit):
    memory=ConversationalMemory(load_persistent=False,storage_dir=str(tmp_path))
    texts=[f'Intervento di prova {i}.' for i in range(300)]
    populate(memory,texts)
    expected=texts[-limit:] if limit else []
    assert [m.content for m in memory.get_conversation_history('long',limit=limit)]==expected
    assert len(memory.messages)==300


def test_recent_history_time_window_filters_before_limiting(tmp_path):
    memory=ConversationalMemory(load_persistent=False,storage_dir=str(tmp_path))
    populate(memory,[f'Turno {i}' for i in range(90)])
    rows=memory.get_conversation_history('long',start_time=datetime(2026,1,1,0,0,20),
        end_time=datetime(2026,1,1,0,1,0),limit=3)
    assert [r.content for r in rows]==['Turno 58','Turno 59','Turno 60']


@pytest.mark.parametrize('limit',[-1,True,1.5])
def test_invalid_history_limit_cannot_silently_change_window(tmp_path,limit):
    memory=ConversationalMemory(load_persistent=False,storage_dir=str(tmp_path))
    with pytest.raises(ValueError):memory.get_conversation_history('long',limit=limit)


@pytest.mark.parametrize('kind',['prova','accesso','riferimento'])
@pytest.mark.parametrize('other_text',[
    'Il codice di {other} potrebbe essere ALTRO-781.',
    'Il codice di {other} non è ALTRO-781.',
    'Se il codice di {other} è ALTRO-781.',
])
def test_uncertainty_in_one_code_category_cannot_block_a_different_known_category(kind,other_text):
    other=next(k for k in ('prova','accesso','riferimento') if k!=kind)
    original=f'Il codice di {kind} è EsAtTo_006.'
    texts=[original]+[f'Oggi ho studiato il capitolo {i}.' for i in range(500)]+[other_text.format(other=other)]
    result=literal_code_reply(f'Quale codice di {kind} ti avevo indicato? Rispondi solo con il codice.',
                              [SimpleNamespace(content=t) for t in texts])
    assert result==('EsAtTo_006','literal_user_memory',[original])


@pytest.mark.parametrize('text',['Sto imparando a scrivere codice.',
    'Oggi abbiamo revisionato il codice sorgente.', 'Mi interessa la qualità del codice.'])
def test_programming_discussion_does_not_revoke_an_unrelated_literal_identifier(text):
    result=literal_code_reply('Dimmi il codice di prova. Rispondi solo con il codice.',
        [SimpleNamespace(content=t) for t in ['Il codice di prova è SEQ-309.',text]])
    assert result[0]=='SEQ-309' and result[1]=='literal_user_memory'


@pytest.mark.parametrize('text',['Il codice potrebbe essere NUOVO-877.',
    'Il codice di prova potrebbe essere NUOVO-877.', 'Il codice di prova non è SEQ-309.'])
def test_late_relevant_ambiguity_still_blocks_literal_recall(text):
    result=literal_code_reply('Dimmi il codice di prova. Rispondi solo con il codice.',
        [SimpleNamespace(content=t) for t in ['Il codice di prova è SEQ-309.',text]])
    assert result[1]=='memory_clarification'


RECALL_QUESTIONS=['Dove ho messo il mio ombrello?', 'Ti ricordi dove tengo il mio ombrello?',
    'Mi ricordi dove ho lasciato l’ombrello?', 'Sai dove si trova il mio ombrello?']


@pytest.mark.parametrize('query',RECALL_QUESTIONS)
def test_rephrased_recall_requests_do_not_bury_the_original_source(tmp_path,query):
    engine=VectorMemoryEngine(str(tmp_path/'vectors.db'))
    original='Il mio ombrello è nell’armadio del corridoio.'
    engine.add('u',original,metadata={'role':'user'})
    for i in range(140):engine.add('u',RECALL_QUESTIONS[i%len(RECALL_QUESTIONS)],metadata={'role':'user'})
    found=engine.search('u',query,top_k=3,allowed_roles=('user',),exclude_query_replays=True)
    assert [r['content'] for r in found]==[original]
    assert engine.count('u')==141


@pytest.mark.parametrize('report',[
    'L’ombrello è nello zaino, dove ho messo la torcia?',
    'Ho lasciato il mio ombrello in ufficio. Ti ricordi?',
    'Dove ho messo il mio ombrello? Ieri lo tenevo nello zaino.',
    'Ho ansia per il viaggio, cosa posso fare?',
])
def test_filter_preserves_mixed_reports_and_requests_to_recall_prior_questions(report):
    assert not is_replayed_question(report,'Dove ho messo il mio ombrello?')
    assert not is_replayed_question('Dove ho messo il mio ombrello?',
                                     'Quali domande ti ho fatto nella conversazione precedente?')


def test_large_vocabulary_index_uses_memory_for_present_terms_not_all_pairs(tmp_path):
    engine=VectorMemoryEngine(str(tmp_path/'vectors.db'))
    for i in range(1800):engine.add('u',f'Appunto univoco voce{i} tema{i}.',metadata={'role':'user'})
    assert engine.search('u','voce1379')[0]['content']=='Appunto univoco voce1379 tema1379.'
    numeric_bytes=sum(vec.nbytes for _,_,vec in engine._index)
    assert numeric_bytes < 1800*256, f'Dense numeric cache still allocates {numeric_bytes} bytes'
    with sqlite3.connect(engine.db_path) as db:
        stored=db.execute('SELECT SUM(LENGTH(vector_blob)) FROM memories').fetchone()[0]
    assert (stored or 0)<1800*256, 'Derived vectors still grow quadratically in SQLite'


def test_sparse_retrieval_matches_dense_cosine_reference(tmp_path):
    texts=['Una stella illumina il mare.', 'Studio stelle lontane e pianeti.',
           'Il libro contiene appunti sul mare.', 'La musica accompagna la lettura.',
           'Mare stelle mare, appunti e stelle.']
    engine=VectorMemoryEngine(str(tmp_path/'vectors.db'))
    for text in texts:engine.add('u',text,metadata={'role':'user'})
    tfidf=_LightTfidf()
    for text in texts:tfidf.partial_fit(text)
    matrix=np.vstack([tfidf.encode(text) for text in texts])
    for query in ('mare stelle','appunti libro','musica','nessuntermine'):
        scores=matrix@tfidf.encode(query)
        expected=[(texts[i],float(np.clip(scores[i],0,1)))
                  for i in np.lexsort((-np.arange(1,len(texts)+1),-scores)) if scores[i]>0]
        actual=engine.search('u',query,top_k=20,allowed_roles=('user',),use_expansion=False)
        assert [r['content'] for r in actual]==[r[0] for r in expected]
        assert [r['score'] for r in actual]==pytest.approx([r[1] for r in expected],abs=2e-7)


def test_long_personal_history_keeps_corrections_revocations_and_user_scope(tmp_path):
    from allma_model.core.autobiographical_identity import grounded_reply
    memory=ConversationalMemory(load_persistent=False,storage_dir=str(tmp_path))
    texts=['Mi chiamo Elia.','Il mio colore preferito è verde.']
    texts += [f'Oggi ho letto la pagina {i}.' for i in range(400)]
    texts += ['Ora mi chiamo Noemi.','Non ho più un colore preferito.']
    populate(memory,texts)
    populate(memory,['Mi chiamo Andrea.','Il mio colore preferito è rosso.'],user='other',conversation='foreign')
    reopened=ConversationalMemory(storage_dir=str(tmp_path))
    assert 'Noemi' in grounded_reply('Come mi chiamo?',reopened,'u')[0]
    assert grounded_reply('Qual è il mio colore preferito?',reopened,'u')[1]=='personal_fact_revoked'
    assert 'Andrea' in grounded_reply('Come mi chiamo?',reopened,'other')[0]


@pytest.mark.parametrize('inactive',[{'revoked':True},{'status':'revoked'},{'status':'superseded'}])
def test_fallback_backend_cannot_restore_an_inactive_record(inactive):
    from allma_model.agency_system.operational_actions import retrieve_user_memory
    def record(text,metadata):
        return SimpleNamespace(content=text,metadata={'role':'user',**metadata},user_id='u',timestamp=None)
    memory=SimpleNamespace(vector_engine=None,retrieve_relevant_context=Mock(return_value=[
        (.9,record('Ombrello nel luogo precedente.',inactive)),(.8,record('Ombrello nel luogo attuale.',{}))]))
    assert [r['content'] for r in retrieve_user_memory(memory,'u','ombrello')]==['Ombrello nel luogo attuale.']


def test_long_history_literal_recall_uses_the_real_core_without_model_inference(tmp_path):
    from allma_model.core.allma_core import ALLMACore
    core=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'core.db'))
    core._ensure_mobile_llm=lambda:None
    core._llm=Mock()
    try:
        populate(core.conversational_memory,['Il codice di prova è NUOVO_007.']+
            [f'Ho letto il capitolo {i}.' for i in range(350)]+
            ['Il codice di accesso potrebbe essere ALTRO-481.'])
        cid=core.start_conversation('u')
        result=core.process_message('u',cid,'Dimmi il codice di prova. Rispondi solo con il codice.')
        assert result.is_valid and result.content=='NUOVO_007'
        assert result.metadata['source']=='literal_user_memory'
        core._llm.generate.assert_not_called()
    finally:core.close()


def test_backlog_larger_than_one_recovery_batch_is_drained_without_duplicate_growth(tmp_path):
    from allma_model.core.allma_core import ALLMACore
    core=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'core.db'))
    try:
        cid=core.start_conversation('u')
        for i in range(70):
            text=f'Sono felice per il risultato numero {i}.'
            core._store_user_message(cid,text,{},'u')
            intent=core.conversational_memory.messages[-1].metadata['experience_update']
            core.delivery_updates._enqueue(intent)
        pending=[]
        for _ in range(3):pending.append(core.delivery_updates.recover()['pending'])
        assert pending==[38,6,0]
        before=core.coalescence_processor.emotion_growth_view('u')
        assert before['associations']['joy']['observations']==70
        assert core.delivery_updates.recover()['pending']==0
        assert core.coalescence_processor.emotion_growth_view('u')==before
    finally:core.close()


def test_android_long_history_challenges_share_disposable_runner_and_pass(tmp_path):
    from long_history_battery import run_battery
    from reliability_android import AndroidLongHistoryRun
    result=run_battery(tmp_path/'reports')
    assert result['complete'] and result['passed']==result['planned']==24,result['failures']
    assert AndroidLongHistoryRun.battery_module=='long_history_battery'
