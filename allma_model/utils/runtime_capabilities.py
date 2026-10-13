"""Describe wired capabilities without treating them as personal memories."""
import re
from .dialogue_continuity import normalized


def capability_items(core):
    items = []
    engine = getattr(core, '_llm', None)
    if engine is not None:
        items.append('spiegare concetti, scrivere testi e ragionare con il modello collegato, che può sbagliare')
    items.append('eseguire calcoli aritmetici esatti nel formato supportato')
    if getattr(core, 'conversational_memory', None) is not None:
        items.append('conservare e consultare le conversazioni salvate')
    if getattr(core, 'answer_recall', None) is not None:
        items.append('recuperare risposte dopo conferme esplicite, senza modificare i pesi del modello')
    if getattr(core, 'emotional_core', None) is not None:
        items.append('analizzare le emozioni espresse nei messaggi, senza presumere di conoscerle con certezza')
    if getattr(core, 'dream_manager', None) is not None and getattr(core, 'dream_enabled', False):
        items.append('elaborare ipotesi nel Diario Sogni da sottoporre alla tua verifica')
    return items


def capability_reply(message, core, history):
    query = normalized(message)
    query = re.sub(r'^(?:ciao|allma|alma)\s+', '', query)
    query = re.sub(r'\s+(?:allma|alma)$', '', query)
    direct = query in {'cosa sai fare', 'che cosa sai fare', 'cosa puoi fare',
                       'quali sono le tue capacità', 'quali sono le tue capacita'}
    followup = query in {'solo questi sai fare', 'solo questo sai fare',
                        'sai fare altro', 'puoi fare altro', 'e poi', 'e altro'}
    previous = history[-1] if history else None
    if not direct and not (followup and previous is not None and previous.role == 'assistant'
                          and previous.metadata.get('source') == 'runtime_capabilities'):
        return None
    items = capability_items(core)
    if followup:
        text = ('Quelle sono le capacità operative che posso descrivere con certezza adesso. '
                'Puoi chiedermi un compito concreto tra quelli elencati. '
                'La riuscita dipende dal modello e dai dati disponibili; non ho capacità fisiche.')
    else:
        text = 'Al momento posso:\n' + '\n'.join('• ' + item + '.' for item in items)
        text += '\nSono capacità del sistema, non esperienze personali; non garantisco risposte sempre corrette.'
    return text, 'runtime_capabilities', []
