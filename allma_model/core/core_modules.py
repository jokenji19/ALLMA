from allma_model.core.dream_system.dream_manager import DreamManager
from allma_model.agency_system.proactive_core import ProactiveAgency
from allma_model.response_system.dynamic_response_engine import DynamicResponseEngine
from allma_model.vision_system.vision_core import VisionSystem
from allma_model.voice_system.voice_core import VoiceSystem


def init_runtime_modules(core):
    core.dream_manager = DreamManager(
        memory_system=core.memory_system,
        incremental_learner=core.incremental_learner,
        reasoning_engine=core.reasoning_engine,
        coalescence_processor=core.coalescence_processor,
        system_monitor=core.system_monitor
    )

    core.proactive_agency = ProactiveAgency(
        memory_system=core.memory_system,
        reasoning_engine=core.reasoning_engine
    )

    core.dynamic_response = DynamicResponseEngine()
    core.vision_system = VisionSystem()
    core.voice_system = VoiceSystem()
