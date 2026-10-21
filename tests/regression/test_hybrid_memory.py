import pytest
from allma_model.core.vector_memory_engine import VectorMemoryEngine


PARAPHRASES = [
    ('Ombrello riposto nell’armadio.', 'Dove posso trovare ciò che uso per ripararmi dalla pioggia?'),
    ('Le forbici sono nel cassetto.', 'Dove ho messo lo strumento per tagliare la carta?'),
    ('La torcia è nello zaino.', 'Dove trovo qualcosa per illuminare al buio?'),
    ('Il cacciavite è nella scatola rossa.', 'Dov’è quello che uso per svitare le viti?'),
    ('La penna è sulla scrivania.', 'Dov’è lo strumento che uso per scrivere?'),
    ('Il powerbank è nel cassetto.', 'Dove ho messo quello che serve a ricaricare il telefono?'),
    ('Il termometro è nel bagno.', 'Dove trovo quello per misurare la febbre?'),
    ('Gli occhiali sono sul comodino.', 'Dove sono quelli che uso per vedere meglio?'),
    ('Ho parcheggiato la bicicletta in cortile.', 'Dov’è il mio mezzo a pedali?'),
    ('Appuntamento dal dottore martedì.', 'Quando ho la visita medica?'),
]


@pytest.mark.parametrize('content,question', PARAPHRASES)
def test_functional_paraphrases_retrieve_original_owned_record(tmp_path, content, question):
    engine = VectorMemoryEngine(str(tmp_path/'vectors.db'))
    engine.add('u', content, metadata={'role':'user'})
    engine.add('u', 'La musica è piacevole.', metadata={'role':'user'})
    engine.add('other', content.replace('armadio', 'garage'), metadata={'role':'user'})
    result = engine.search('u', question, allowed_roles=('user',), exclude_query_replays=True)
    assert result and result[0]['content'] == content
    assert result[0]['retrieval']['concept_matches']
    restored = VectorMemoryEngine(engine.db_path)
    assert restored.search('u',question,allowed_roles=('user',))[0]['content'] == content


@pytest.mark.parametrize('question', [
    'Dove ho messo quella cosa?', 'Qualcosa per il viaggio?',
    'Oggi è prevista pioggia?', 'Come funziona la pioggia?',
    'Vorrei scrivere una poesia.', 'Misurare la distanza da Roma.',
])
def test_generic_or_related_topic_does_not_invent_object_link(tmp_path, question):
    engine = VectorMemoryEngine(str(tmp_path/'vectors.db'))
    engine.add('u','Ombrello nell’armadio.', metadata={'role':'user'})
    assert engine.search('u', question, allowed_roles=('user',)) == []


def test_sources_are_filtered_before_limit_and_ambiguity_is_preserved(tmp_path):
    engine = VectorMemoryEngine(str(tmp_path/'vectors.db'))
    for _ in range(8): engine.add('other','Ombrello nel garage.', metadata={'role':'user'})
    engine.add('u','Ombrello nel cassetto.',metadata={'role':'assistant'})
    engine.add('u','Ombrello nel cassetto.',metadata={'role':'user','is_valid':False})
    first = 'Ombrello nell’armadio.'
    second = 'Impermeabile nello zaino.'
    engine.add('u',first,metadata={'role':'user'})
    engine.add('u',second,metadata={'role':'user'})
    result = engine.search('u','Cosa uso per proteggermi dalla pioggia?',allowed_roles=('user',),top_k=2)
    assert {r['content'] for r in result} == {first,second}
    assert all(r['retrieval']['kind']=='concept' for r in result)
    engine.clear_user('u')
    assert engine.search('u','Cosa uso per proteggermi dalla pioggia?') == []


def test_lexical_only_switch_and_exact_names_remain_available(tmp_path):
    engine = VectorMemoryEngine(str(tmp_path/'vectors.db'))
    engine.add('u','Ombrello nell’armadio.',metadata={'role':'user'})
    assert not engine.search('u','Ripararmi dalla pioggia',use_expansion=False)
    assert engine.search('u','ombrello',use_expansion=False)[0]['content']=='Ombrello nell’armadio.'
    assert not engine.search('u','Codice XY8Z')


def test_large_candidate_set_is_batched_and_invalid_sources_cannot_fill_slots(tmp_path):
    engine = VectorMemoryEngine(str(tmp_path/'vectors.db'))
    engine.add('u','Ombrello nell’armadio.',metadata={'role':'user'})
    for _ in range(1050):
        engine.add('u','Ombrello nel cassetto.',metadata={'role':'assistant'})
    result=engine.search('u','ombrello',top_k=1,allowed_roles=('user',))
    assert result[0]['content']=='Ombrello nell’armadio.'


def test_revoked_and_superseded_candidates_do_not_become_current_evidence(tmp_path):
    engine = VectorMemoryEngine(str(tmp_path/'vectors.db'))
    engine.add('u','Ombrello nel garage.',metadata={'role':'user','revoked':True})
    engine.add('u','Ombrello in cucina.',metadata={'role':'user','status':'superseded'})
    engine.add('u','Ombrello nell’armadio.',metadata={'role':'user'})
    result=engine.search('u','Ripararmi dalla pioggia',allowed_roles=('user',),top_k=3)
    assert [r['content'] for r in result]==['Ombrello nell’armadio.']


def test_cold_reader_refreshes_concept_postings_after_other_instance_changes(tmp_path):
    path=str(tmp_path/'vectors.db')
    reader=VectorMemoryEngine(path)
    writer=VectorMemoryEngine(path)
    writer.add('u','Forbici nel cassetto.',metadata={'role':'user'})
    assert reader.search('u','Tagliare carta')[0]['content']=='Forbici nel cassetto.'
    writer.clear_user('u')
    assert not reader.search('u','Tagliare carta')
