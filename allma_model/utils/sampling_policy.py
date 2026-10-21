"""Model-specific thinking sampling; leaves unknown models on existing defaults."""
from pathlib import Path


def sampling_options(model_path):
    if isinstance(model_path, (str, Path)) and 'qwen3' in Path(model_path).name.lower():
        # Qwen/Qwen3-1.7B model card, thinking-mode recommendations.
        return {'temperature': 0.6, 'top_p': 0.95, 'top_k': 20, 'min_p': 0.0}
    return {'temperature': 0.4, 'top_p': 0.9}


REASONING_INSTRUCTION = (
    'Ragiona sul punto decisivo, verifica premesse e conclusione, poi rispondi. '
    'Non consumare il ragionamento ripetendo la domanda. Non inventare dettagli.'
)


def reasoning_instruction(request):
    """Keep internal reasoning separate from an explicitly constrained answer.

    This is guidance, not a formatter or proof of model compliance. The existing
    output validator remains authoritative; no generated answer is truncated.
    """
    from .output_contract import requested_sentence_count, requested_contract
    count = requested_sentence_count(request)
    contract = requested_contract(request)
    if count or contract:
        text = ('Svolgi ragionamento e verifiche internamente. Non consumare il ragionamento ripetendo la domanda. '
                'Nella risposta finale dai soltanto '
                'la risposta richiesta, senza etichette di verifica, conclusione o spiegazione del procedimento. ')
        if count:
            text += f'La risposta finale deve contenere esattamente {count} ' + ('frase. ' if count == 1 else 'frasi. ')
        if contract:
            text += {'json':'Restituisci soltanto JSON valido, senza blocchi Markdown.',
                     'number':'Restituisci soltanto un numero.',
                     'yes_no_it':'Restituisci soltanto sì oppure no.',
                     'yes_no_en':'Restituisci soltanto yes oppure no.'}[contract]
        return text
    return REASONING_INSTRUCTION


def brief_answer_instruction(request):
    from .output_contract import requested_sentence_count, requested_contract
    if requested_sentence_count(request) or requested_contract(request):
        return 'Budget breve: completa soltanto la risposta nel formato richiesto, senza aggiungere sezioni o spiegazioni esterne al formato.'
    return 'Budget breve: dai prima la conclusione e una spiegazione essenziale. Completa il punto principale, senza introduzioni o ripetizioni.'
