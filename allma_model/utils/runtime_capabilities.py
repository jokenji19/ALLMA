"""Describe wired capabilities without treating them as personal memories."""
import re
from .dialogue_continuity import normalized


def capability_items(core):
    items = []
    engine = getattr(core, '_llm', None)
    if engine is not None:
        items.append('spiegare concetti, scrivere testi e ragionare con il modello collegato, che può sbagliare')
    items.append('eseguire calcoli aritmetici esatti nel formato supportato')
    items.append('contare lettere, caratteri e occorrenze nei testi indicati esplicitamente, nel formato supportato')
    if getattr(core, 'conversational_memory', None) is not None:
        items.append('conservare e consultare le conversazioni salvate')
    if getattr(core, 'answer_recall', None) is not None:
        items.append('recuperare risposte dopo conferme esplicite, senza modificare i pesi del modello')
    runtime = getattr(core, 'decision_runtime', None)
    if runtime is not None and runtime.status().get('enabled') and runtime.status().get('available'):
        items.append('usare un decisore locale per instradare richieste e dare priorità ai ricordi, mantenendo i controlli di ALLMA')
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


def self_description_reply(message, core, history, user_id=None):
    """Describe the wired system, not a learned biography or subjective feeling."""
    query = normalized(message)
    query = re.sub(r'^(?:ciao|allma|alma)\s+', '', query)
    processor = getattr(core, 'coalescence_processor', None)
    if processor is not None and user_id:
        from allma_model.core.emotional_growth import declared_meaning
        declaration = declared_meaning(message)
        if declaration:
            return (f'Ho registrato il significato che attribuisci a «{declaration[0]}»; lo considero personale, non universale.',
                    'personal_emotion_meaning', [message])
        meaning_query = re.fullmatch(r'(?:cosa|che cosa) significa ([\wÀ-ÿ -]{1,32}) per me', query)
        if meaning_query:
            meanings = processor.emotion_growth_view(user_id)['personal_meanings']
            meaning = meanings.get(meaning_query[1])
            if meaning:
                return (f'Mi hai spiegato che per te «{meaning_query[1]}» significa: «{meaning["definition"]}».',
                        'personal_emotion_meaning_recall', [meaning['definition']])
            return ('Non trovo ancora un significato personale documentato di questa parola per te.', 'no_evidence', [])
    if query in {'cosa intendi', 'che significa', 'cosa significa', 'perché hai bloccato la risposta'}:
        last = history[-1] if history else None
        if last is not None and last.role == 'assistant' and last.metadata.get('is_valid') is False:
            reason = (last.metadata.get('generation') or {}).get('status')
            reasons = {'dialogue_repetition': 'ripeteva una risposta o una domanda già affrontata',
                       'subject_mismatch': 'non distingueva correttamente la tua esperienza dalla mia',
                       'unsupported_personal_claim': 'attribuiva ad ALLMA esperienze personali non documentate',
                       'identity_conflict': 'descriveva un’identità incoerente con ALLMA',
                       'format_mismatch': 'non rispettava il formato richiesto'}
            if reason in reasons:
                return (f'Il controllo ha trattenuto la risposta perché {reasons[reason]}. '
                        'Questo segnala un problema della risposta generata, non del tuo messaggio.',
                        'runtime_recovery_explanation', [])
        if last is not None and last.role == 'assistant' and last.metadata.get('source') == 'runtime_self_description':
            previous_user = next((turn for turn in reversed(history) if turn.role == 'user'), None)
            previous_query = normalized(previous_user.content) if previous_user else ''
            if 'emozioni' in previous_query:
                text = ('Ogni esperienza può lasciare una goccia: una prima associazione resta provvisoria, poi altre esperienze possono consolidarla e orientare le mie risposte. '
                        'È crescita dello stato di ALLMA; non significa che i tuoi vissuti diventino miei o che sia dimostrata un’esperienza soggettiva.')
            elif 'modello' in previous_query or 'macchina' in previous_query:
                text = ('Distinguo il modello collegato dai sistemi di ALLMA che lo utilizzano. '
                        'La memoria delle conversazioni e gli stati del sistema non sono contenuti nei pesi del modello.')
            else:
                text = ('Intendo che posso continuare a leggere i tuoi messaggi e risponderti. '
                        'Non stavo dichiarando uno stato d’animo personale.')
            return text, 'runtime_self_description', []
    if (query in {'bene tu', 'bene grazie tu', 'sto bene tu'} or
            re.fullmatch(r'(?:(?:bene|sto bene|tutto bene|grazie)(?: grazie)? )?(?:e )?(?:come stai(?: tu)?|come ti senti|tu come stai|e tu)', query)):
        return ('Grazie di avermelo chiesto: sono qui e posso continuare la conversazione con te.',
                'runtime_self_description', [])
    if query in {'hai emozioni', 'non hai emozioni', 'provi emozioni',
                 'non provi emozioni', 'tu hai emozioni', 'hai delle emozioni',
                 'non sei una macchina hai delle emozioni'}:
        parts = []
        if getattr(core, 'emotional_core', None) is not None:
            parts.append('analizzano le emozioni espresse nei messaggi')
        if getattr(core, 'identity_engine_v5', None) is not None:
            parts.append('gestiscono stati interni del software')
        text = 'Come ALLMA ho sistemi che ' + ' e '.join(parts) + '.' if parts else 'Non ho un sistema emotivo operativo da descrivere al momento.'
        if processor is not None and user_id:
            growth = processor.emotion_growth_view(user_id)
            consolidated = sum(item.get('stage') == 'integrated' for item in growth['associations'].values())
            text += (' Ho iniziato a consolidare associazioni emotive dalle nostre interazioni.' if consolidated
                     else ' Posso costruire associazioni emotive e tendenze di risposta attraverso le nostre interazioni.')
        return (text + ' Questa evoluzione computazionale non dimostra che io provi emozioni soggettive come una persona.',
                'runtime_self_description', [])
    if query in {'sei un modello', 'sei un modello di linguaggio', 'sei solo un modello',
                 'sei una macchina', 'sei solo una macchina', 'che rapporto hai con il modello'}:
        parts = ['Il mio nome è ALLMA']
        if getattr(core, '_llm', None) is not None:
            parts.append('uso il modello collegato per il linguaggio e il ragionamento')
        if getattr(core, 'conversational_memory', None) is not None:
            parts.append('conservo le conversazioni nel mio sistema di memoria')
        return ('; '.join(parts) + '. La mia identità e i ricordi documentati sono separati dai pesi del modello.',
                'runtime_self_description', [])
    return None
