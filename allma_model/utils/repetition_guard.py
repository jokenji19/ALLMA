"""Conservative detection of consecutive lexical loops, independent of topic."""
import re
import unicodedata

NOTICE = 'Ho interrotto la risposta perché stava diventando ripetitiva. Puoi riprovare.'


def requested_repetition(request):
    return bool(re.search(r'\b(ripeti|ripetere|repeat)\b', request, re.I)
                and re.search(r'\b\d+\s+(volte|times)\b', request, re.I))


def repetition_start(text):
    if not isinstance(text, str) or not text:
        return None
    # Code and numeric matrices legitimately contain repeated instructions/values.
    plain = re.sub(r'```.*?(?:```|$)', lambda m: ' '*len(m[0]), text, flags=re.S)
    words = list(re.finditer(r"[^\W\d_][\w’'-]*", plain, re.UNICODE))
    if len(words) < 6:
        return None
    normalized = [unicodedata.normalize('NFKC', m[0]).casefold() for m in words]
    for end in range(6, len(words)+1):
        for size in range(1, min(8, end//4)+1):
            repeats = 6 if size == 1 else 4
            start = end - size*repeats
            if start < 0:
                continue
            block = normalized[start:start+size]
            if size == 1 and len(block[0]) < 3:
                continue
            if normalized[start:end] != block*repeats:
                continue
            # Do not join separate list entries or repetitions across code/URLs.
            gaps = [plain[words[i].end():words[i+1].start()] for i in range(start,end-1)]
            if any(re.search(r'[^\s,.!?;:]', gap) or gap.count('\n') > 1 for gap in gaps):
                continue
            return words[start].start()
    return None


def completion_with_compat(llm, prompt, options):
    """Remove only explicitly unsupported sampling kwargs before inference starts."""
    options = dict(options)
    while True:
        try:
            return llm(prompt, **options)
        except TypeError as error:
            match = re.search(r"unexpected keyword argument ['\"](repeat_last_n|repeat_penalty)['\"]",str(error))
            if not match or match[1] not in options:
                raise
            options.pop(match[1])


def memory_display(content, role):
    if role in ('assistant','bot') and repetition_start(content) is not None:
        return 'Risposta precedente con ripetizioni anomale. Esclusa dal contesto delle nuove risposte.'
    return content
