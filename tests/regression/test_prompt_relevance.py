import pytest
from allma_model.utils.prompt_relevance import requested_sensor_tools
from allma_model.utils.model_comparison import diagnostic_budgets, controlled_reasoning_sweep


@pytest.mark.parametrize('message', ['Sono felice oggi', 'Quanto fa 12 + 18?',
    'Ora parliamo di musica', 'Nel cestino ci sono 11 pere', 'Spiega la temperatura di ebollizione'])
def test_unrelated_requests_do_not_prefetch_sensors(message):
    assert requested_sensor_tools(message) == []


@pytest.mark.parametrize('message,tool', [('Che ore sono?', 'SYSTEM_TIME'),
    ('Qual è la data di oggi?', 'SYSTEM_TIME'),('Quanta batteria rimane?', 'READ_BATTERY'),
    ('Qual è la temperatura della batteria?', 'READ_BATTERY')])
def test_device_questions_keep_live_evidence(message,tool):
    assert tool in requested_sensor_tools(message)


def test_reasoning_sweep_requires_controlled_context_and_preserves_reserve():
    context = {'disable_answer_recall':True,'benchmark_seed':1,'benchmark_reasoning_sweep':True,
               'benchmark_max_tokens':272,'benchmark_thought_budget':128}
    assert controlled_reasoning_sweep(context)
    assert not controlled_reasoning_sweep(dict(context,benchmark_seed=True))
    assert diagnostic_budgets(context,'Domanda','NORMAL',384) == (272,128)
    assert diagnostic_budgets(context,'Domanda','NORMAL',64) == (64,21)


def test_natural_closure_requires_isolated_diagnostic_and_explicit_controls():
    from allma_model.utils.model_comparison import diagnostic_reasoning_mode
    ctx={'disable_answer_recall':True,'benchmark_seed':42,'benchmark_reasoning_mode':'natural'}
    assert diagnostic_reasoning_mode(ctx,isolated_synthetic=True)=='natural'
    assert diagnostic_reasoning_mode(ctx)=='bounded'
    assert diagnostic_reasoning_mode(dict(ctx,benchmark_seed=True),isolated_synthetic=True)=='bounded'
    assert diagnostic_reasoning_mode(dict(ctx,disable_answer_recall=False),isolated_synthetic=True)=='bounded'
    assert diagnostic_reasoning_mode(dict(ctx,benchmark_reasoning_mode='other'),isolated_synthetic=True)=='bounded'
