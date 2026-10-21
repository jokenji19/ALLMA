"""Explicit diagnostic budgets and descriptive paired outcomes, never an IQ score."""
from .prompt_budget import reasoning_budget


def diagnostic_budgets(context, message, complexity, total):
    context = context if isinstance(context, dict) else {}
    enabled = (context.get('disable_answer_recall') is True
               and type(context.get('benchmark_seed')) is int)
    requested = context.get('benchmark_max_tokens')
    if enabled and type(requested) is int and requested >= 2:
        total = min(total, requested)
    thought = reasoning_budget(message, complexity, total)
    requested = context.get('benchmark_thought_budget')
    if enabled and type(requested) is int and requested >= 1:
        thought = min(requested, max(1, total // 2 if total > 192 else total // 3))
    return total, thought


def summarize_pairs(results):
    pairs = {}
    for result in results:
        if result.get('pair_id'):
            pairs.setdefault(result['pair_id'], {})[result['execution_mode']] = result
    output = []
    for pair_id, arms in pairs.items():
        row = {'pair_id': pair_id, 'complete': set(arms) == {'pipeline', 'model'}}
        if not row['complete']:
            output.append(row)
            continue
        pipeline, model = arms['pipeline'], arms['model']
        a, b = pipeline['generation'], model['generation']
        bypass = a.get('llm_used') is False
        controls = ('max_tokens', 'seed', 'repeat_penalty', 'repeat_last_n',
                    'temperature', 'top_p', 'reasoning_budget')
        row.update(pipeline_source=pipeline.get('source'), pipeline_bypassed_model=bypass,
                   matched_generation_controls=(not bypass and all(
                       a.get(key) is not None and a[key] == b.get(key) for key in controls)),
                   control_differences=[key for key in controls if a.get(key) != b.get(key)],
                   pipeline_seconds=pipeline['duration'], model_seconds=model['duration'],
                   pipeline_checks=pipeline['evaluation']['automatic_status'],
                   model_checks=model['evaluation']['automatic_status'],
                   human_review_required=True)
        # Even identical generation settings do not equalize prompts or caches.
        row['causal_attribution'] = 'not_established'
        output.append(row)
    return output


def controlled_reasoning_sweep(context):
    return (isinstance(context, dict) and context.get('disable_answer_recall') is True
            and type(context.get('benchmark_seed')) is int
            and context.get('benchmark_reasoning_sweep') is True)


def diagnostic_closure_requested(context, *, isolated_synthetic=False):
    return (isolated_synthetic is True and isinstance(context, dict)
            and context.get('disable_answer_recall') is True
            and type(context.get('benchmark_seed')) is int
            and context.get('benchmark_reasoning_mode') in ('bounded', 'natural'))


def diagnostic_reasoning_mode(context, *, isolated_synthetic=False):
    """Natural closure is opt-in on an isolated synthetic diagnostic core only."""
    if (diagnostic_closure_requested(context, isolated_synthetic=isolated_synthetic)
            and context['benchmark_reasoning_mode'] == 'natural'):
        return 'natural'
    return 'bounded'
