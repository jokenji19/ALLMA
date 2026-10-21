"""An artistic portrait of persistent growth, not a biometric or emotion model.

Identity is random and local to a profile. Morphology depends only on that seed
and consolidated software dispositions. Recent user affect changes expression,
never identity. Viewing the portrait creates no learning or model inference.
"""
import hashlib
import math
import secrets
import time
from allma_model.utils.cognitive_state import CognitiveStateStore


def bounded(value, low=0., high=1., default=0.):
    return float(value) if type(value) in (float, int) and math.isfinite(value) and low <= value <= high else default


class AvatarPresence:
    PRESENTATIONS = frozenset(('feminine', 'masculine', 'neutral'))

    def __init__(self, db_path=None):
        self.store = CognitiveStateStore(db_path)
        self.identities = {}
        self.appearances = {}

    def appearance(self, owner, presentation=None):
        """Explicit visual choice, independent of identity and emotional history."""
        if not isinstance(owner, str) or not owner:
            raise ValueError('Attributed visual identity required')
        if presentation is not None and (not isinstance(presentation, str) or presentation not in self.PRESENTATIONS):
            raise ValueError('Unknown avatar presentation')
        with self.store.lock:
            saved = self.store.get('avatar_appearance') if self.store.path else self.appearances
            if saved and (saved.get('version') != 1 or not isinstance(saved.get('profiles'), dict)):
                raise ValueError('Invalid avatar appearance archive')
            saved = saved or {'version': 1, 'profiles': {}}
            if any(not isinstance(key, str) or not key or not isinstance(value, str)
                   or value not in self.PRESENTATIONS for key, value in saved['profiles'].items()):
                raise ValueError('Invalid avatar appearance archive')
            if presentation is not None:
                saved['profiles'][owner] = presentation
                self.store.put('avatar_appearance', saved)
                self.appearances = saved
            return saved['profiles'].get(owner)

    def identity(self, owner):
        if not isinstance(owner, str) or not owner:
            raise ValueError('Attributed visual identity required')
        if owner in self.identities:
            return self.identities[owner]
        with self.store.lock:
            saved = self.store.get('avatar_identity')
            if saved and (saved.get('version') != 1 or not isinstance(saved.get('profiles'), dict)):
                raise ValueError('Invalid avatar identity archive')
            saved = saved or {'version': 1, 'profiles': {}}
            if any(not isinstance(key, str) or not key or not isinstance(value, str) or len(value) != 32
                   or any(c not in '0123456789abcdef' for c in value)
                   for key, value in saved['profiles'].items()):
                raise ValueError('Invalid avatar identity archive')
            seed = saved['profiles'].get(owner)
            if seed is None:
                seed = secrets.token_hex(16)
                saved['profiles'][owner] = seed
                self.store.put('avatar_identity', saved)
            if not isinstance(seed, str) or len(seed) != 32 or any(c not in '0123456789abcdef' for c in seed):
                raise ValueError('Invalid avatar identity seed')
            self.identities[owner] = seed
            return seed

    def snapshot(self, core, owner, now=None):
        now = time.time() if now is None else now
        seed = self.identity(owner)
        presentation = self.appearance(owner)
        # Fixed, bounded differences, unrelated to name, body, age or gender.
        genes = [v / 255 for v in hashlib.sha256(seed.encode()).digest()]
        personality = getattr(core, 'coalescence_processor', None)
        growth = personality.emotion_growth_view(owner) if personality else {}
        expression = personality.expression_view(owner) if personality else {}
        associations = growth.get('associations', {})
        integrated = sum(item.get('stage') == 'integrated' for item in associations.values())
        deltas = growth.get('trait_deltas', {})
        curiosity = bounded(deltas.get('curiosity', 0), 0, .1) / .1
        care = bounded(deltas.get('empathy', 0), 0, .1) / .1
        learned = {axis: item.get('value') for axis, item in expression.get('tendencies', {}).items()
                   if item.get('stage') == 'integrated'}
        # Recomputable from persistent evidence; opening/refreshing changes nothing.
        shape = {'jaw': .92 + genes[0] * .16, 'cheeks': .94 + genes[1] * .12,
                 'nose': .91 + genes[2] * .18, 'eyes': .94 + genes[3] * .12,
                 'brow': (genes[4] - .5) * .04,
                 'softness': care * .05 + (.01 if learned.get('directness') == 'gentle' else 0),
                 'openness': curiosity * .03 + (.01 if learned.get('questions') == 'exploratory' else 0)}
        policy = growth.get('response_disposition', {}).get('mode')
        pose = {'smile': 0., 'attention': .12 + curiosity * .15, 'energy': .12, 'concern': 0.}
        basis = 'neutral'
        emotional = getattr(core, 'emotional_core', None)
        current = emotional.get_user_emotional_state(owner) if emotional else None
        read = current.get if isinstance(current, dict) else lambda k, d=None: getattr(current, k, d)
        context = read('context', {}) or {}
        observed = context.get('observed_at')
        fresh = type(observed) in (int, float) and math.isfinite(observed) and 0 <= now-observed <= 180
        if (fresh and context.get('user_id') == owner
                and bounded(read('confidence', 0)) >= .6):
            fade = max(0., 1-(now-observed)/180)
            intensity = bounded(read('intensity', 0)) * fade
            valence = bounded(read('valence', 0), -1, 1)
            arousal = bounded(read('arousal', 0))
            pose.update(smile=max(0., valence)*intensity*.65,
                        concern=max(0., -valence)*intensity*.42,
                        energy=.12+arousal*intensity*.35,
                        attention=.22+curiosity*.15)
            basis = 'recent_user_expression'
        return {'version': 1, 'available': True, 'seed': seed, 'shape': shape,
                'configured': presentation is not None, 'presentation': presentation,
                'visual_age_months': 96, 'life_stage': 'child',
                'expression': pose, 'expression_basis': basis,
                'growth': {'integrated': integrated,
                           'style_tendencies': sum(v.get('stage') == 'integrated' for v in expression.get('tendencies', {}).values()),
                           'care': round(care, 4), 'curiosity': round(curiosity, 4),
                           'mode': policy if policy in ('care', 'exploration') else 'forming'},
                'symbolic': True, 'subject': 'ALLMA_visual_representation'}
