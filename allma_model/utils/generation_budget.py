"""Bounded reasoning followed by a reserved answer budget on the same prompt."""
import time
from .generation_control import check_cancelled


def bounded_completion(llm, prompt, kwargs, thought_budget, callback=None, cancel_event=None):
    total_budget = int(kwargs['max_tokens'])
    if total_budget < 2 or int(thought_budget) < 1:
        raise ValueError("A positive reasoning budget and at least two total tokens are required")
    thought_budget = min(int(thought_budget), max(1, total_budget // 2))
    started = time.perf_counter()
    first_token_ms = None
    stages = []

    def stage(stage_prompt, budget, stops):
        nonlocal first_token_ms
        check_cancelled(cancel_event)
        options = dict(kwargs, max_tokens=budget, stop=stops, stream=True)
        try:
            output = llm(stage_prompt, **options)
        except TypeError as error:
            if not any(key in str(error) for key in ('repeat_last_n', 'repeat_penalty')):
                raise
            options.pop('repeat_last_n', None)
            options.pop('repeat_penalty', None)
            output = llm(stage_prompt, **options)
        text = ''
        finish = None
        try:
            for chunk in output:
                check_cancelled(cancel_event)
                choice = chunk['choices'][0]
                token = choice.get('text', '')
                finish = choice.get('finish_reason') or finish
                if token and first_token_ms is None:
                    first_token_ms = (time.perf_counter() - started) * 1000
                text += token
                if callback and token:
                    callback(token)
        finally:
            if hasattr(output, 'close'):
                output.close()
        check_cancelled(cancel_event)
        # Stream API does not guarantee usage; identify these as retokenized counts.
        count = len(llm.tokenize(text.encode('utf-8')))
        stages.append({'tokens': count, 'budget': budget, 'finish_reason': finish})
        return text, finish

    thought, thought_stop = stage(prompt, thought_budget, list(kwargs.get('stop') or []) + ['</think>'])
    check_cancelled(cancel_event)
    boundary = '\n</think>\n\n'
    if callback:
        callback(boundary)
    # Reserve answer tokens even when the model never closes its reasoning tag.
    answer, finish = stage(prompt + thought + boundary, total_budget - thought_budget, kwargs.get('stop'))
    elapsed = time.perf_counter() - started
    count = sum(item['tokens'] for item in stages)
    prompt_count = len(llm.tokenize(prompt.encode('utf-8')))
    return {
        'choices': [{'text': thought + boundary + answer, 'finish_reason': finish or 'unknown'}],
        'usage': {'completion_tokens': count, 'prompt_tokens': prompt_count, 'total_tokens': prompt_count + count},
        'budget_meta': {'reasoning_tokens': stages[0]['tokens'], 'answer_tokens': stages[1]['tokens'],
                        'reasoning_finish_reason': thought_stop,
                        'reasoning_truncated': thought_stop in ('length', 'max_tokens'),
                        'reasoning_budget': thought_budget,
                        'answer_budget': total_budget - thought_budget, 'token_count_source': 'retokenized',
                        'generation_ms': elapsed * 1000, 'ttft_ms': first_token_ms,
                        'generation_tok_s': count / elapsed if elapsed else None},
    }
