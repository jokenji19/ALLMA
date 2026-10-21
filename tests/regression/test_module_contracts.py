from allma_model.core.module_orchestrator import ModuleOrchestrator, ModulePriority
from allma_model.core.curiosity_drive import CuriosityDrive
from allma_model.core.emotional_adaptation_system import EmotionalAdaptationSystem


def test_real_adapters_preserve_hints_and_alias_tracker():
    orchestrator = ModuleOrchestrator()
    curiosity = CuriosityDrive().process('Spiegami perché il cielo è blu e come funziona', {'intent': 'question'})
    emotion = EmotionalAdaptationSystem().process('Sono triste', {'emotional_state': {'primary_emotion': 'sadness'}})
    merged = orchestrator.coalescence({'curiosity': curiosity, 'emotional_adaptation': emotion,
                                     'cognitive_tracking': {'abilities': {'memory': .6}}})
    for hint in curiosity['system_instruction'] + emotion['system_instruction']:
        assert hint in merged['system_instruction']
    assert merged['memory_updates']['memory'] == .6


def test_expensive_module_does_not_block_cheaper_later_module():
    class Module:
        def process(self, text, context):
            return {'system_instruction': ['Istruzione intera']}
    orchestrator = ModuleOrchestrator(20)
    orchestrator.register_module('large', Module(), ModulePriority.HIGH, 100)
    orchestrator.register_module('small', Module(), ModulePriority.LOW, 1)
    output = orchestrator.process('ciao', {})
    assert 'small' in output['raw_results']
    assert 'large' not in output['raw_results']
    assert output['system_instruction'] == 'Istruzione intera'


def test_social_context_matches_legacy_adapter_contract():
    from allma_model.incremental_learning.social_learning_system import SocialLearningSystem
    system = SocialLearningSystem()
    result = system.analyze_social_context('Cortesemente, per favore', {'user_id': 'u'})
    assert result.formality > .6
    assert result.context['user_id'] == 'u'
    assert system.interaction_history[-1]['context'] is result


def test_creativity_receives_italian_request_intent():
    from allma_model.agency_system.creativity_system import CreativitySystem
    orchestrator = ModuleOrchestrator()
    orchestrator.register_module('creativity', CreativitySystem(), ModulePriority.MEDIUM, 20)
    result = orchestrator.process('Inventa una poesia', {}, intent='richiesta')
    assert '[MUSE]' in result['system_instruction']


def test_malformed_outputs_are_isolated_and_reported():
    from unittest.mock import Mock
    o = ModuleOrchestrator()
    o.register_module('curiosity', Mock(process=Mock(return_value=['wrong'])), ModulePriority.HIGH, 1)
    o.register_module('meta_learning', Mock(process=Mock(return_value={
        'confidence': 'high', 'suggested_style': 42, 'hints': [None]})), ModulePriority.LOW, 1)
    o.register_module('cognitive_tracking', Mock(process=Mock(return_value={'abilities': None})), ModulePriority.LOW, 1)
    o.register_module('valid', Mock(process=Mock(return_value={'system_instruction': ['Usa i dati disponibili']})), ModulePriority.LOW, 1)
    result = o.process('ciao', {}, 'question')
    assert result['system_instruction'] == 'Usa i dati disponibili'
    assert result['execution_report']['outcomes']['curiosity']['status'] == 'failed'
    assert result['memory_updates'] == {}


def test_selection_failure_does_not_abort_other_modules():
    from unittest.mock import Mock
    o = ModuleOrchestrator()
    o.register_module('creativity', Mock(is_creative_request=Mock(side_effect=ValueError('broken selector'))), ModulePriority.HIGH, 1)
    o.register_module('valid', Mock(process=Mock(return_value={'system_instruction': ['Continua']})), ModulePriority.LOW, 1)
    result = o.process('crea', {}, 'request')
    assert result['system_instruction'] == 'Continua'
    assert result['execution_report']['outcomes']['creativity']['stage'] == 'selection'


def test_intermittent_failures_do_not_disable_a_recovered_module():
    from unittest.mock import Mock
    module = Mock(process=Mock(side_effect=[value for _ in range(7)
                              for value in (RuntimeError('temporary'), {})]))
    o = ModuleOrchestrator()
    o.register_module('valid', module, ModulePriority.LOW, 1)
    for _ in range(14):
        o.process('ciao', {})
    assert o.modules['valid'].enabled
    assert o.modules['valid'].failure_count == 7
    assert o.modules['valid'].consecutive_failures == 0


def test_missing_handler_is_disabled_after_consecutive_failures():
    o = ModuleOrchestrator()
    o.register_module('broken', object(), ModulePriority.LOW, 1)
    for _ in range(6):
        o.process('ciao', {})
    result = o.process('ciao', {})
    assert not o.modules['broken'].enabled
    assert result['execution_report']['outcomes']['broken']['status'] == 'disabled'


def test_admission_uses_measured_cost_including_failed_calls(monkeypatch):
    from unittest.mock import Mock
    import allma_model.core.module_orchestrator as source
    clock = [0.]
    from types import SimpleNamespace
    import time
    monkeypatch.setattr(source, 'time', SimpleNamespace(perf_counter=lambda: clock[0], time=time.time))
    def slow(*args):
        clock[0] += .08
        raise RuntimeError('slow failure')
    module = Mock(process=Mock(side_effect=slow))
    o = ModuleOrchestrator(100)
    o.register_module('slow', module, ModulePriority.HIGH, 1)
    o.process('ciao', {})
    o.performance_budget = 50
    result = o.process('ciao', {})
    assert module.process.call_count == 1
    assert result['execution_report']['outcomes']['slow']['status'] == 'budget_skipped'
    assert o.get_stats()['modules']['slow']['avg_exec_time_ms'] == 80


def test_planning_and_personality_hints_reach_merged_guidance():
    from allma_model.core.planning_adapter import PlanningSystemAdapter
    from allma_model.core.personality_adapter import PersonalityAdapterLite
    o = ModuleOrchestrator()
    o.register_module('planning', PlanningSystemAdapter(), ModulePriority.MEDIUM, 1)
    o.register_module('personality_style', PersonalityAdapterLite(), ModulePriority.LOW, 1)
    plain = o.process('Ciao', {}, 'statement')
    assert plain['execution_report']['outcomes']['planning']['status'] == 'not_relevant'
    plan = o.process('Pianifica il progetto. Rispondi brevemente.', {}, 'request')
    assert 'non inventare tempi' in plan['system_instruction']
    assert plan['raw_results']['personality_style']['style_hint'] in plan['system_instruction']


def test_perception_does_not_mix_users_or_conversations():
    from allma_model.core.perception_lite import PerceptionSystemLite
    module = PerceptionSystemLite()
    text = 'Perché il cielo è blu?'
    module.process(text, {'user_id': 'u', 'conversation_id': 'a'})
    assert 'repetition' in module.process(text, {'user_id': 'u', 'conversation_id': 'a'})
    assert 'repetition' not in module.process(text, {'user_id': 'v', 'conversation_id': 'a'})
    assert 'repetition' not in module.process(text, {'user_id': 'v', 'conversation_id': 'b'})


def test_transient_personality_style_does_not_leak_between_users():
    from allma_model.core.personality_adapter import PersonalityAdapterLite
    module = PersonalityAdapterLite()
    for _ in range(8):
        module.process('Cortesemente, per favore', {'user_id': 'u'})
    assert module.style.formality == .5  # Politeness alone is not a stable preference.
    module.process('Una domanda neutra', {'user_id': 'other'})
    assert module.style.formality == .5
