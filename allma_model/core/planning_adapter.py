"""Cheap planning guidance; persistent plan admission belongs to GoalProgress."""
import re


class PlanningSystemAdapter:
    def __init__(self):
        self._intent = re.compile(r'\b(?:pianific\w*|organizz\w*|programm\w*|piano|task|compito|obiettivo|progetto|strategia|roadmap|passi|fasi)\b',re.I)

    def _is_planning_query(self,text):
        return bool(self._intent.search(text))

    def process(self,user_input,context):
        if not self._is_planning_query(user_input):return {}
        # Actual steps come from the admitted task/model proposal. A generic
        # outline and invented durations must not masquerade as a grounded plan.
        return {'system_instruction':[
            'Per questa richiesta di pianificazione, proponi passi legati ai vincoli dell’utente; '
            'chiedi i dati mancanti e non inventare tempi o risorse.'],
            'has_plan':False,'status':'guidance_only','tasks':[],'timeline':None}
