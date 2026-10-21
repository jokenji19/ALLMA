"""ALLMA-owned goals and grants, independent of any inference motor.

Only host code calls this API. Model responses are untrusted proposals, never
serialized commands for these methods. This is an application boundary, not a
sandbox for arbitrary Python callbacks (registered tools remain trusted code).
"""
import copy
import math
from contextlib import contextmanager
import threading
import time
import uuid


class ActionAuthority:
    SECTION = 'action_authority'
    PERMISSIONS = frozenset({'read', 'memory_write', 'state_write', 'external'})

    def __init__(self, store=None):
        self.store = store
        self.lock = store.lock if store else threading.RLock()
        self._transient = {'goals': {}}

    def _state(self):
        state = self.store.get(self.SECTION) if self.store else self._transient
        return copy.deepcopy(state) if isinstance(state.get('goals'), dict) else {'goals': {}}

    def _save(self, state):
        if self.store:
            self.store.put(self.SECTION, state)
        else:
            self._transient = copy.deepcopy(state)

    @classmethod
    def _valid_goal(cls, goal):
        return (isinstance(goal, dict)
                and all(isinstance(goal.get(k), str) and goal[k].strip()
                        for k in ('user_id','objective','event_id'))
                and goal.get('status') in ('active','revoked','completed')
                and type(goal.get('priority')) is int and 0 <= goal['priority'] <= 5
                and type(goal.get('created_at')) in (int,float) and math.isfinite(goal['created_at'])
                and isinstance(goal.get('allowed_actions'), dict) and 1 <= len(goal['allowed_actions']) <= 7
                and all(isinstance(k,str) and k and k != 'stop' and isinstance(v,str) and v in cls.PERMISSIONS
                        for k,v in goal['allowed_actions'].items()))

    def open_goal(self, user_id, objective, *, event_id, allowed_actions, priority=1):
        """Host admits an explicit request; no NLP/model inference grants rights.

        allowed_actions maps registered action names to exact permission classes.
        event_id identifies the trusted user/UI event that admitted this goal.
        """
        if (not isinstance(user_id, str) or not user_id.strip() or len(user_id)>200
                or not isinstance(objective, str) or not objective.strip() or len(objective)>1000
                or not isinstance(event_id, str) or not event_id.strip() or len(event_id)>200
                or type(priority) is not int or not 0 <= priority <= 5
                or not isinstance(allowed_actions, dict) or not 1 <= len(allowed_actions) <= 7
                or any(not isinstance(k, str) or not k or k == 'stop' or len(k)>64
                       or not isinstance(v, str) or v not in self.PERMISSIONS for k,v in allowed_actions.items())):
            raise ValueError('Invalid host goal or grants')
        with self.lock:
            state = self._state()
            for key, goal in state['goals'].items():
                if self._valid_goal(goal) and goal.get('user_id') == user_id and goal.get('event_id') == event_id:
                    # Replay cannot reopen a revoked goal or widen its grants.
                    return key
            if len(state['goals']) >= 256:
                raise RuntimeError('Goal archive full; explicit maintenance required')
            key = uuid.uuid4().hex
            state['goals'][key] = {'user_id':user_id, 'objective':objective,
                'event_id':event_id, 'priority':priority, 'status':'active',
                'allowed_actions':dict(allowed_actions), 'created_at':time.time()}
            self._save(state)
            return key

    @contextmanager
    def turn_scope(self, user_id, objective, *, allowed_actions):
        """Ephemeral host-admitted read scope; never fills the durable goal archive.

        The child has no access to persistent grants and expires even on failure.
        Long-lived goals still require open_goal and explicit completion evidence.
        """
        if any(permission != 'read' for permission in allowed_actions.values()):
            raise ValueError('Turn scopes only admit read actions')
        child = ActionAuthority()
        goal_id = child.open_goal(user_id, objective, event_id=uuid.uuid4().hex,
                                  allowed_actions=allowed_actions)
        try:
            yield child, goal_id
        finally:
            child.revoke(user_id, goal_id)

    def snapshot(self, user_id, goal_id):
        with self.lock:
            goal = self._state()['goals'].get(goal_id)
            return copy.deepcopy(goal) if self._valid_goal(goal) and goal.get('user_id') == user_id else None

    def permits(self, user_id, goal_id, action, permission):
        goal = self.snapshot(user_id, goal_id)
        return bool(goal and goal.get('status') == 'active'
                    and permission in self.PERMISSIONS
                    and isinstance(goal.get('allowed_actions'), dict)
                    and goal.get('allowed_actions', {}).get(action) == permission)

    def active_goals(self, user_id):
        with self.lock:
            goals = [{**goal, 'id': key} for key, goal in self._state()['goals'].items()
                     if self._valid_goal(goal) and goal.get('user_id') == user_id
                     and goal.get('status') == 'active']
            return sorted(goals, key=lambda g: (-g['priority'], g['created_at']))

    @contextmanager
    def admission(self, user_id, goal_id, action, permission):
        """Recheck immediately before execution; revocation serializes with action.

        No action begins after a completed revocation. An already executing
        callback must cooperate with its host cancellation signal to stop early.
        """
        with self.lock:
            if not self.permits(user_id, goal_id, action, permission):
                raise PermissionError('ALLMA did not authorize this action')
            yield

    def revoke(self, user_id, goal_id):
        with self.lock:
            state = self._state()
            goal = state['goals'].get(goal_id)
            if not self._valid_goal(goal) or goal.get('user_id') != user_id:
                return False
            if goal.get('status') != 'active':
                return False
            goal['status'] = 'revoked'
            self._save(state)
            return True

    def complete(self, user_id, goal_id, *, evidence, verify):
        """Model 'stop' is not proof of goal completion; host verifies evidence."""
        with self.lock:
            state = self._state()
            goal = state['goals'].get(goal_id)
            if not self._valid_goal(goal) or goal.get('user_id') != user_id or goal.get('status') != 'active':
                return False
            if verify(evidence) is not True:
                return False
            goal['status'] = 'completed'
            self._save(state)
            return True
