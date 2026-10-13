"""Keep the current question and system contract within the real native context."""
import re


def fit_prompt(prompt, tokenize, context_size, completion_budget, reserve=32):
    limit = context_size - completion_budget - reserve
    if limit <= 0:
        raise ValueError('Completion budget exceeds context')
    removed = 0
    while len(tokenize(prompt.encode('utf-8'))) > limit:
        blocks = list(re.finditer(r'<\|im_start\|>(user|assistant)\n.*?<\|im_end\|>\n?', prompt, re.S))
        # Last closed user block is the current request; never shorten its text.
        users = [block for block in blocks if block.group(1) == 'user']
        if not users:
            raise ValueError('Prompt exceeds context without removable ChatML history')
        current = users[-1]
        candidates = [block for block in blocks if block.start() < current.start()]
        if not candidates:
            raise ValueError('Question and system context exceed native context')
        # Remove an oldest complete turn, not just the first half of a pair.
        end = candidates[0].end()
        if len(candidates) > 1 and candidates[0].group(1) == 'user' and candidates[1].group(1) == 'assistant':
            end = candidates[1].end()
        prompt = prompt[:candidates[0].start()] + prompt[end:]
        removed += 1
    return prompt, removed


def reasoning_budget(message, complexity, total):
    target = 128 if complexity == 'COMPLEX' else 64
    # Narrow social turns still receive reasoning; avoid a full explanatory budget.
    if complexity != 'COMPLEX' and re.fullmatch(r'(?:ciao[,!]?\s+)?(?:come stai|come ti va|come va|bene[,!]? tu)\s*[?.!]*', message.strip(), re.I):
        target = 32
    from .output_contract import requested_contract
    if complexity != 'COMPLEX' and len(message) < 350 and requested_contract(message) in ('number','yes_no_it','yes_no_en'):
        target = 32
    if complexity == 'COMPLEX' and re.search(r'\b(?:dimostra|deduci|ragiona|passo per passo|step by step)\b', message, re.I):
        target = 192
    # Leave at least half the total for the answer; very low energy stays brief.
    return min(target, max(1, total // 2 if total > 192 else total // 3))
