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
