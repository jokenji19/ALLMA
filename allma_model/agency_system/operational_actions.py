"""Host-bound read actions; outcomes describe execution, never factual truth."""
import hashlib
import logging
import math
from numbers import Real
import time
from .action_cycle import ActionCycle, LocalAction
from .decision_engine import Decision


def retrieve_user_memory(memory, user_id, message):
    """Both backends are explicitly scoped to the requesting user.

    Only attributed user records can become prompt evidence. A retrieved report
    is evidence of what a user said, not independent verification of world facts.
    """
    if getattr(memory, 'vector_engine', None) is not None:
        raw = memory.vector_engine.search(user_id=user_id, query=message, top_k=3,
                                         use_expansion=True, allowed_roles=('user',), exclude_query_replays=True)
    else:
        raw = []
        for score, record in memory.retrieve_relevant_context(message, user_id=user_id, max_results=3, exclude_query_replays=True):
            if (getattr(record, 'user_id', None) or record.metadata.get('user_id')) != user_id:
                continue
            raw.append({'content': record.content, 'metadata': record.metadata,
                        'score': score, 'timestamp': record.timestamp.isoformat() if record.timestamp else None})
    result = []
    for item in raw:
        metadata = item.get('metadata', {})
        score = item.get('score', 0.)
        if (not isinstance(metadata, dict) or metadata.get('role') != 'user'
                or metadata.get('is_valid') is False
                or metadata.get('revoked') is True or metadata.get('status') in ('revoked','superseded')
                or metadata.get('user_id', user_id) != user_id
                or not isinstance(item.get('content'), str) or not item['content'].strip()
                or not isinstance(score, Real) or isinstance(score, bool) or not math.isfinite(score) or not 0 <= score <= 1):
            continue
        result.append({'content': item['content'], 'metadata':dict(metadata),
                       'score':float(score), 'timestamp':item.get('timestamp')})
    return sorted(result, key=lambda item: item['score'], reverse=True)[:3]


def memory_step(core, user_id, message, decision, cancel_event=None):
    """One read, then deterministic provenance verification; no second inference.

    A host-required personal lookup cannot be vetoed by a mistaken model route.
    No durable goal is silently opened for every message. Scope expires on exit.
    """
    started = time.perf_counter()
    observations = []

    def execute():
        records = retrieve_user_memory(core.conversational_memory, user_id, message)
        observations.extend(records)
        return {'records': records, 'scope_user':user_id, 'source':'scoped_user_reports'}

    def verify(value):
        return (isinstance(value, dict) and value.get('scope_user') == user_id
                and value.get('source') == 'scoped_user_reports' and isinstance(value.get('records'), list))

    selected = decision.get('status') == 'selected' and decision.get('choice') == 'memory'
    proposal = Decision('memory', {}, 'selected', 0)
    with core.action_authority.turn_scope(user_id, 'Retrieve attributed reports needed for this user request',
                                         allowed_actions={'memory':'read'}) as (authority, goal_id):
        result = ActionCycle(None, {'memory':LocalAction('Read attributed user conversation records', execute, verify)},
                             max_steps=1, authority=authority).run('', user_id=user_id, goal_id=goal_id,
                             cancel_event=cancel_event, initial_decision=proposal)
    verified = bool(result['steps'] and result['steps'][-1].get('verified') is True
                    and result['status'] == 'budget_exhausted')
    summary = {'status':'observed' if verified else result['status'], 'steps':result['steps'],
               'proposal_source':'decider' if selected else 'host_memory_policy',
               'record_count':len(observations) if verified else 0,
               'evidence_kind':'user_reports_not_world_verification',
               'elapsed_ms':(time.perf_counter()-started)*1000, 'additional_inferences':0}
    # Only aggregate operational outcomes are persisted, never prompts or records.
    store = core.action_authority.store
    if store is not None and result['status'] != 'cancelled':
        try:
            key = hashlib.sha256(user_id.encode()).hexdigest()
            with store.lock:
                state = store.get('decision_outcomes')
                if key in state or len(state) < 128:
                    previous = state.get(key, {})
                    def count(name):
                        value = previous.get(name, 0)
                        return value if type(value) is int and value >= 0 else 0
                    state[key] = {'memory_attempts':count('memory_attempts')+1,
                                  'observed':count('observed')+int(verified),
                                  'with_records':count('with_records')+int(verified and bool(observations)),
                                  'failed':count('failed')+int(not verified),
                                  'decider_proposals':count('decider_proposals')+int(selected)}
                    store.put('decision_outcomes', state)
        except Exception as error:
            logging.warning('[ActionCycle] Outcome persistence unavailable: %s', type(error).__name__)
    logging.info('[ActionCycle] memory status=%s records=%s source=%s',
                 summary['status'], summary['record_count'], summary['proposal_source'])
    return observations if verified else [], summary
