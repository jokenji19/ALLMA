"""Read-only expression adapter for the canonical coalescence owner.

A turn's sadness, length, punctuation, politeness and emoji do not permanently
change personality. The core owns learning from durably stored user messages.
"""
from dataclasses import dataclass
from copy import deepcopy
from allma_model.core.personality_development import empty_state, plan


@dataclass
class CommunicationStyle:
    formality: float = .5
    verbosity: float = .6
    humor: float = .4
    directness: float = .7


class PersonalityAdapterLite:
    def __init__(self, coalescence_processor=None):
        self.coalescence = coalescence_processor
        self.style = CommunicationStyle()
        self.user_prefers_brief = False
        self.user_prefers_formal = False
        self.interaction_count = 0
        self._user_id = None

    def process(self, user_input, context):
        context = context or {}
        user_id = context.get('user_id')
        self._user_id = user_id
        self.interaction_count += 1
        expression = context.get('personality_expression')
        if not isinstance(expression,dict):
            expression = (self.coalescence.expression_plan(user_id,user_input,context.get('emotional_state'))
                          if self.coalescence and user_id else plan(empty_state(),user_id,user_input,context.get('emotional_state')))
        self.style = CommunicationStyle()
        values = expression['values']
        self.style.formality = {'formal':.8,'informal':.3}.get(values.get('formality'),.5)
        self.style.verbosity = {'brief':.3,'detailed':.8}.get(values.get('verbosity'),.6)
        self.style.humor = {'serious':.1,'light':.65}.get(values.get('humor'),.4)
        self.style.directness = {'gentle':.5,'direct':.8}.get(values.get('directness'),.7)
        self.user_prefers_brief = values.get('verbosity')=='brief'
        self.user_prefers_formal = values.get('formality')=='formal'
        return {'tone_params':deepcopy(self.style.__dict__),
                'style_hint':'' if context.get('personality_expression_applied') else expression['instruction'],
                'expression':deepcopy(expression), 'growth_guidance':''}

    def get_current_style(self):
        return deepcopy(self.style)
