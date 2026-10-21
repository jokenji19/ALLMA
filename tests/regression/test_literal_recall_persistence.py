from allma_model.utils.literal_recall import literal_code_reply
from allma_model.core.autobiographical_identity import user_events
from allma_model.memory_system.conversational_memory import ConversationalMemory


def test_reloaded_sources_keep_user_role_validity_and_exact_value(tmp_path):
    path=str(tmp_path/'memory')
    memory=ConversationalMemory(storage_dir=path)
    memory.store_message('earlier','Il codice di prova è EsAtTo_004.',{},'user','u')
    memory.store_message('earlier','Il codice di prova è MODELLO-123.',{},'assistant','u')
    memory.store_message('earlier','Il codice di prova è INVALIDO-456.',{'is_valid':False},'user','u')
    memory.store_message('other','Il codice di prova è ALTRO-789.',{},'user','other')
    memory.save_memory()
    restored=ConversationalMemory(storage_dir=path)
    query='Quale codice di prova ti avevo indicato? Rispondi solo con il codice.'
    assert literal_code_reply(query,user_events(restored,'u'))[0]=='EsAtTo_004'
    assert literal_code_reply(query,user_events(restored,'other'))[0]=='ALTRO-789'
    assert literal_code_reply(query,user_events(restored,'unknown')) is None



def test_correction_and_revocation_replay_survive_archive_reload(tmp_path):
    path=str(tmp_path/'memory')
    memory=ConversationalMemory(storage_dir=path)
    for text in ('Il codice di prova è PRIMA-123.', 'Rettifico: il codice di prova è Dopo_004.'):
        memory.store_message('old',text,{},'user','u')
    memory.save_memory()
    query='Quale codice di prova ti avevo indicato? Rispondi solo con il codice oppure NON_DISPONIBILE se non è nei ricordi.'
    restored=ConversationalMemory(storage_dir=path)
    assert literal_code_reply(query,user_events(restored,'u'))[0]=='Dopo_004'
    restored.store_message('new','Revoco il codice di prova.',{},'user','u')
    restored.store_message('old-copy','Il codice di prova è PRIMA-123.',{},'user','u')
    restored.save_memory()
    again=ConversationalMemory(storage_dir=path)
    assert literal_code_reply(query,user_events(again,'u'))[1]=='literal_memory_revoked'
