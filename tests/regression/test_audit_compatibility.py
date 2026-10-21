import json
from datetime import datetime
from unittest.mock import Mock
import numpy as np
import pytest
from allma_model.core.personality_coalescence import PersonalityCore, EmotionalResponse, EmotionalState
from allma_model.core.memory_system.memory_types import Memory


@pytest.fixture
def core(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from allma_model.core.allma_core import ALLMACore
    instance = ALLMACore(db_path=str(tmp_path/'allma.db'),mobile_mode=True)
    instance._ensure_mobile_llm = lambda: None
    instance._llm = None
    yield instance
    instance.close()


def test_technical_level_requires_owned_declaration_and_can_be_revoked(core):
    memory=core.conversational_memory
    chat=core.start_conversation('u')
    assert core._determine_technical_level('u')=='unknown'
    memory.store_message(chat,'Il mio livello tecnico è esperto.',role='user',user_id='other')
    assert core._determine_technical_level('u')=='unknown'
    memory.store_message(chat,'Il mio livello tecnico è principiante.',role='user',user_id='u')
    assert core._determine_technical_level('u')=='beginner'
    memory.store_message(chat,'Non usare più il mio livello tecnico.',role='user',user_id='u')
    assert core._determine_technical_level('u')=='unknown'


def test_project_context_is_real_owned_and_preserves_metadata(core):
    core.project_tracker.create_project('other','Astronomia riservata','')
    assert core._get_project_context('u','Astronomia')['current_project'] is None
    project=core.project_tracker.create_project('u','Navigazione','',{'active_files':['mappa.txt']})
    context=core._get_project_context('u','Navigazione')
    assert context['project_id']==project and context['active_files']==['mappa.txt']
    assert core._get_project_context('u','giardinaggio')['current_project'] is None


def test_legacy_value_api_uses_the_same_vocabulary():
    changes=PersonalityCore().update_values('Vorrei imparare ed esplorare',EmotionalResponse(EmotionalState.CURIOSITY))
    assert changes['curiosità']>0


def test_legacy_memory_embedding_is_stable_and_uses_actual_tokens():
    a=Memory('bussola nord',.5,datetime.now(),{})
    b=Memory('BUSSOLA NORD',.5,datetime.now(),{})
    c=Memory('galassie telescopio',.5,datetime.now(),{})
    assert np.array_equal(a.embedding,b.embedding)
    assert not np.array_equal(a.embedding,c.embedding)
    supplied=np.ones(768)
    assert Memory('x',.5,datetime.now(),{},embedding=supplied).embedding is supplied


def test_compatibility_bridge_reuses_all_cognitive_owners(core):
    from allma_model.api.allma_api import AllmaAndroidBridge
    bridge=AllmaAndroidBridge(core=core)
    assert bridge.learner is core.incremental_learner
    assert bridge.personality is core.personality
    assert bridge.emotional_core is core.emotional_core
    assert bridge.project_tracker is core.project_tracker
    core.incremental_learner.learn_from_interaction({'input':'Testo sintetico','topic':'prova'},'u')
    assert 'prova' in bridge.initialize_user_session('u')['learning_progress']['topics']


@pytest.fixture
def api(core):
    from allma_model.ui.backend.api.app import create_app
    from werkzeug.security import generate_password_hash
    password=generate_password_hash('synthetic-password')
    app=create_app(core=core,config={'TESTING':True,'SECRET_KEY':'synthetic-test-secret-'*3,
                                   'AUTH_USERS':{'u':password,'other':password}})
    client=app.test_client()
    def headers(owner='u'):
        response=client.post('/api/auth/login',json={'username':owner,'password':'synthetic-password'})
        assert response.status_code==200
        return {'Authorization':'Bearer '+response.json['access_token']}
    return client,headers


def test_http_adapter_refuses_demo_auth_before_constructing_core():
    from allma_model.ui.backend.api.app import create_app
    with pytest.raises(ValueError): create_app(config={'SECRET_KEY':None,'AUTH_USERS':{}})


def test_http_conversation_and_stats_use_supported_contracts(api):
    client,headers=api
    auth=headers()
    response=client.post('/api/conversation',headers=auth,json={'message':'Quanto fa 18 + 24? Rispondi solo con un numero'})
    assert response.status_code==200 and response.json['response']=='42'
    assert client.get('/api/dashboard/stats',headers=auth).status_code==200
    assert client.post('/api/conversation',headers=auth,json=[]).status_code==400


def test_http_ownership_authentication_and_no_open_cors(api):
    client,headers=api
    owner,other=headers(),headers('other')
    response=client.post('/api/projects',headers=owner,json={'name':'Progetto riservato'})
    assert response.status_code==201
    project=response.json['project_id']
    assert client.get('/api/projects/'+project,headers=other).status_code==404
    assert client.get('/api/projects',headers=other).json==[]
    assert client.get('/api/projects').status_code==401
    forged={'Authorization':'Bearer invalid'}
    assert client.get('/api/projects',headers=forged).status_code==401
    assert 'Access-Control-Allow-Origin' not in client.get('/api/projects',headers={**owner,'Origin':'https://untrusted.invalid'}).headers
    assert client.post('/api/auth/login',json={'username':'admin','password':'password'}).status_code==401


def test_document_extraction_uses_the_supported_processor_once(tmp_path):
    from allma_model.core.extraction import InformationExtractor
    from allma_model.core.document_processor import DocumentProcessor
    from unittest.mock import patch
    path=tmp_path/'test.txt'
    path.write_text('Documento sintetico di prova.')
    extractor=InformationExtractor.__new__(InformationExtractor)
    extractor.extract_from_text=Mock(return_value={'entities':{}})
    original=DocumentProcessor.process_document
    calls=[]
    def parse(self,file):
        calls.append(file)
        return original(self,file)
    with patch.object(DocumentProcessor,'process_document',parse):
        result=extractor.extract_from_document(str(path))
    assert len(calls)==1
    assert result['text']=='Documento sintetico di prova.'
    assert result['source_kind']=='document_content'


def test_legacy_cleanup_repairs_links_without_erasing_experience():
    from allma_model.core.personalization_integration import PersonalizationIntegration
    from types import SimpleNamespace
    instance=PersonalizationIntegration.__new__(PersonalizationIntegration)
    node=SimpleNamespace(connections={1,99})
    instance.memory_system=SimpleNamespace(nodes={1:node},thematic_map={'tema':[1,99]})
    result=instance._cleanup_memory()
    assert result['memories_preserved']==1 and node.connections=={1}
    assert instance.memory_system.thematic_map['tema']==[1]


def test_normal_turn_does_not_log_user_text(core, caplog, capsys):
    import logging
    caplog.set_level(logging.INFO)
    secret='CodicePersonaleSinteticoJ8Z4'
    core.process_message('u',core.start_conversation('u'),'Spiegami il significato di '+secret)
    output=capsys.readouterr()
    assert secret not in caplog.text+output.out+output.err
