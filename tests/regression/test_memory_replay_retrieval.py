from allma_model.core.vector_memory_engine import VectorMemoryEngine
from allma_model.utils.memory_evidence import is_replayed_question


def test_many_identical_questions_cannot_hide_original_report(tmp_path):
    engine=VectorMemoryEngine(str(tmp_path/'vectors.db'))
    query='Quale codice di prova ti avevo indicato?'
    engine.add('u','Dato sintetico: il codice di prova è LUNA-483.',metadata={'role':'user','conversation_id':'origin'})
    for i in range(12):
        engine.add('u',query,metadata={'role':'user','conversation_id':str(i)})
    ordinary=engine.search('u',query,top_k=3,allowed_roles=('user',))
    assert all(r['content']==query for r in ordinary)
    found=engine.search('u',query,top_k=3,allowed_roles=('user',),exclude_query_replays=True)
    assert len(found)==1 and 'LUNA-483' in found[0]['content']
    assert engine.count('u')==13  # Filtering never deletes history.
    reopened=VectorMemoryEngine(str(tmp_path/'vectors.db'))
    assert 'LUNA-483' in reopened.search('u',query,allowed_roles=('user',),exclude_query_replays=True)[0]['content']


def test_questions_with_reports_and_other_users_keep_existing_scope(tmp_path):
    engine=VectorMemoryEngine(str(tmp_path/'vectors.db'))
    mixed='Ho ansia per il viaggio, cosa posso fare?'
    engine.add('u',mixed,metadata={'role':'user'})
    engine.add('other','Il viaggio è a Roma.',metadata={'role':'user'})
    results=engine.search('u','Ricordi il mio viaggio?',allowed_roles=('user',),exclude_query_replays=True)
    assert any(r['content']==mixed for r in results)
    assert all('Roma' not in r['content'] for r in results)
    assert not is_replayed_question(mixed,'Ricordi il mio viaggio?')
    assert not is_replayed_question('Il mio codice è A.','Il mio codice è A.')


def test_legitimate_repeated_declarations_are_preserved_with_different_values(tmp_path):
    engine=VectorMemoryEngine(str(tmp_path/'vectors.db'))
    for _ in range(4):engine.add('u','Il codice di prova è A.',metadata={'role':'user'})
    engine.add('u','Il codice di prova è B.',metadata={'role':'user'})
    results=engine.search('u','codice di prova',top_k=10,allowed_roles=('user',),exclude_query_replays=True)
    assert len(results)==5
    assert sum(r['content']=='Il codice di prova è A.' for r in results)==4


def test_tfidf_fallback_filters_before_limit_and_accepts_numpy_scores(tmp_path):
    from datetime import datetime
    from types import SimpleNamespace
    from allma_model.memory_system.conversational_memory import ConversationalMemory, Conversation
    from allma_model.agency_system.operational_actions import retrieve_user_memory
    memory=ConversationalMemory(storage_dir=str(tmp_path/'memory'))
    memory.vector_engine=None
    query='Quale codice di prova ti avevo indicato?'
    records=[Conversation(id=str(i),user_id='u',content=query,timestamp=datetime.now(),metadata={'role':'user'}) for i in range(12)]
    records.append(Conversation(id='original',user_id='u',content='Il codice di prova è LUNA-483.',
                               timestamp=datetime.now(),metadata={'role':'user','conversation_id':'old'}))
    memory.conversations={'u':records}
    result=retrieve_user_memory(memory,'u',query)
    assert len(result)==1 and 'LUNA-483' in result[0]['content']
    assert type(result[0]['score']) is float



def test_format_instruction_does_not_turn_an_identical_recall_question_into_evidence(tmp_path):
    engine=VectorMemoryEngine(str(tmp_path/'vectors.db'))
    query='Quale codice di prova ti avevo indicato? Rispondi solo con il codice oppure NON_DISPONIBILE se non è nei ricordi.'
    for _ in range(4):
        engine.add('u',query,metadata={'role':'user'})
    assert engine.search('u',query,allowed_roles=('user',),exclude_query_replays=True)==[]
    assert engine.count('u')==4
    mixed='Il codice di prova è VENTO-987. Lo ricordi? Rispondi solo con il codice.'
    assert not is_replayed_question(mixed,mixed)
