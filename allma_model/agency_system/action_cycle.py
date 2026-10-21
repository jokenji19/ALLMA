"""Bounded choose -> act -> observe -> verify cycle owned by ALLMA.

The motor selects names only. Code controls arguments, permissions, available
tools and verification. No self-generated success, implicit retries or learning.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class LocalAction:
    description: str
    execute: object
    verify: object
    permission: str = 'read'


class ActionCycle:
    def __init__(self, motor, actions, *, max_steps=2, authority=None, diagnostic=False):
        if (type(max_steps) is not int or not 1 <= max_steps <= 4
                or type(diagnostic) is not bool or not isinstance(actions, dict)
                or not 1 <= len(actions) <= 7 or 'stop' in actions
                or any(not isinstance(key,str) or not key or len(key)>64
                       or not isinstance(action,LocalAction) or not callable(action.execute)
                       or not callable(action.verify) or not isinstance(action.description,str)
                       or not action.description.strip()
                       or not isinstance(action.permission,str)
                       or action.permission not in {'read','memory_write','state_write','external'}
                       for key,action in actions.items())):
            raise ValueError('Invalid action budget or registry')
        self.motor, self.actions, self.max_steps = motor, dict(actions), max_steps
        self.authority, self.diagnostic = authority, diagnostic

    def run(self, state, *, permissions=frozenset({'read'}), cancel_event=None,
            user_id=None, goal_id=None, initial_decision=None):
        trace, used = [], set()
        if self.authority is None and not self.diagnostic:
            return {'status': 'authority_required', 'steps': trace}
        # Unscoped diagnostic execution can never gain persistent-write or
        # external permissions through a caller/model-provided permission list.
        if self.authority is None:
            permissions = frozenset(permissions) & {'read'}
        else:
            goal = self.authority.snapshot(user_id, goal_id)
            if not goal or goal.get('status') != 'active':
                return {'status': 'goal_inactive', 'steps': trace}
            state = 'ALLMA host goal: ' + goal['objective'] + '\nContext:\n' + state[:6000]
        for _ in range(self.max_steps):
            if cancel_event is not None and cancel_event.is_set():
                return {'status': 'cancelled', 'steps': trace}
            available = {key: action for key, action in self.actions.items()
                         if key not in used and action.permission in permissions
                         and (self.authority is None or self.authority.permits(
                             user_id, goal_id, key, action.permission))}
            if not available:
                return {'status': 'exhausted', 'steps': trace}
            options = {key: action.description for key, action in available.items()}
            options['stop'] = 'Stop: no additional action is needed or suitable.'
            # The already evaluated route supplies the first proposal only.
            # All normal membership, permission and revocation checks still apply.
            if initial_decision is not None and not trace:
                decision, initial_decision = initial_decision, None
            else:
                decision = self.motor.decide(state, 'Which next action helps address the request?',
                                             options, cancel_event=cancel_event)
            if decision.status != 'selected' or decision.choice is None:
                return {'status': decision.status, 'steps': trace}
            if decision.choice == 'stop':
                return {'status': 'stopped', 'steps': trace}
            if decision.choice not in available:
                return {'status': 'invalid_action', 'steps': trace}
            if cancel_event is not None and cancel_event.is_set():
                return {'status': 'cancelled', 'steps': trace}
            key, action = decision.choice, available[decision.choice]
            used.add(key)
            try:
                from contextlib import nullcontext
                admission = (self.authority.admission(user_id, goal_id, key, action.permission)
                             if self.authority else nullcontext())
                with admission:
                    observation = action.execute()  # arguments bound by host, never by model
                    verified = action.verify(observation) is True
            except PermissionError:
                return {'status': 'authorization_revoked', 'steps': trace}
            except Exception:
                return {'status': 'action_failed', 'steps': trace + [{'action': key, 'verified': False}]}
            trace.append({'action': key, 'verified': verified})
            if cancel_event is not None and cancel_event.is_set():
                return {'status': 'cancelled', 'steps': trace}
            if not verified:
                return {'status': 'unverified', 'steps': trace}
            # Bounded observations are data, not a model-authored completion claim.
            state = state[:6000] + '\nObserved ' + key + ': ' + str(observation)[:1000]
        return {'status': 'budget_exhausted', 'steps': trace}
