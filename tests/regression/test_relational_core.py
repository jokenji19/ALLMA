from tests.regression.test_exact_text_core import core


def test_explicit_boundary_is_respected_without_inference_or_learning_a_fact(core):
    result=core.process_message('u',core.start_conversation('u'),'Non voglio parlarne.')
    assert result.is_valid and result.metadata['source']=='conversation_boundary'
    assert '?' not in result.content
    assert not result.metadata['knowledge_verified']
    core._llm.generate.assert_not_called()
    assert not core.answer_recall.records


def test_core_supplies_current_needs_and_previous_emotion_as_separate_evidence(core):
    core._llm.generate.return_value='Ti ascolto. Puoi raccontare quello che desideri.'
    cid=core.start_conversation('u')
    core.process_message('u',cid,'Sono triste per la partenza.')
    result=core.process_message('u',cid,'Non sono triste, sono stanco. Voglio solo sfogarmi.')
    assert result.is_valid
    perception=result.metadata['relational_perception']
    assert perception['relation']=='self_correction' and 'sadness' in perception['denied_labels']
    assert 'sadness' not in perception['prior_labels']
    expression=result.metadata['personality_expression']
    assert expression['values']['support_mode']=='listening' and expression['instruction_received']
    call=core._llm.generate.call_args
    prompt=call.args[0] if call.args else call.kwargs['prompt']
    assert 'non riproporre le emozioni che ha negato' in prompt
    assert 'senza consigli o soluzioni non richiesti' in prompt
    assert not core.coalescence_processor.expression_view('u')['preferences']


def test_explicit_support_feedback_is_routed_to_existing_coalescence(core):
    core._llm.generate.return_value='Ti ascolto. Puoi raccontare quello che desideri.'
    cid=core.start_conversation('u')
    answer=core.process_message('u',cid,'Sono triste per la partenza. Voglio solo sfogarmi.')
    assert answer.metadata['personality_delivery']['offered']['support_mode']=='listening'
    feedback=core.process_message('u',cid,'Il tuo ascolto senza consigli mi è stato utile.')
    assert feedback.metadata['source']=='personality_response_feedback'
    assert feedback.metadata['personality_feedback']['status']=='feedback_recorded'
    learned=core.coalescence_processor.expression_view('u')['outcome_learning']
    assert learned['contexts']['support']['support_mode']['positive']==1
    assert learned['contexts']['support']['support_mode']['stage']=='suspended'


def test_general_questions_do_not_receive_unrelated_emotional_guidance(core):
    core._llm.generate.return_value='Il Sole è una stella.'
    cid=core.start_conversation('u')
    core.coalescence_processor.observe_interaction('u','p','Quando sto male preferisco essere ascoltato senza consigli.')
    result=core.process_message('u',cid,'Spiega il Sole.')
    assert result.is_valid and result.metadata['relational_perception']['relation']=='none'
    assert 'instruction' not in result.metadata['relational_perception']
    assert 'support_mode' not in result.metadata['personality_expression']['values']
