"""Delivery settings for spoken answers; cognitive checks remain shared with chat."""
VOICE_INSTRUCTION = (
    '\nQuesta risposta sarà ascoltata: usa frasi brevi e naturali, senza preamboli. '
    'Per una domanda semplice bastano 1-3 frasi. Per richieste complesse conserva '
    'i passaggi necessari e tutti i punti richiesti; evita ripetizioni e tabelle '
    'se non richieste. Non sacrificare correttezza o dettagli richiesti alla brevità.'
)


def voice_token_limit(current_limit, complexity):
    """Cap output length without overriding stricter metabolic limits."""
    return current_limit if complexity == 'COMPLEX' else min(current_limit, 192)
