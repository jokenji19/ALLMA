"""Describe wired capabilities without treating them as personal memories."""
import re
from .dialogue_continuity import normalized
from .dialogue_recovery import (
    clarification_question, unanswered_attempt, opening_recovery,
)


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
    if getattr(core, 'goal_progress', None) is not None:
        items.append('conservare obiettivi, progressi e correzioni tra le chat, distinguendo i risultati dichiarati dalla tua conferma; puoi chiedermi come gestire gli obiettivi')
    references=getattr(core,'public_references',None)
    if references is not None:
        items.append('consultare Wikipedia per gli argomenti generali riconosciuti, con fonti visibili' if references.status()['enabled'] else
            'consultare Wikipedia se abiliti le ricerche in Impostazioni → Internet e fonti; al momento sono disattivate')
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
    if query in {'hai accesso a internet','puoi cercare su internet','puoi andare su internet',
                 'puoi navigare su internet','sei connessa a internet','sei connesso a internet'}:
        references=getattr(core,'public_references',None)
        enabled=references is not None and references.status()['enabled']
        return (('Le ricerche online sono abilitate: posso consultare Wikipedia per gli argomenti generali riconosciuti e mostrarti la fonte. Identità e memoria restano locali.' if enabled else
            'Le ricerche online sono disattivate. Puoi abilitarle in Impostazioni → Internet e fonti; identità e memoria restano locali.'),
            'runtime_web_access',[])
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
    pending = unanswered_attempt(history)
    opening = opening_recovery(message)
    if opening:
        source = opening['source'] if pending else 'dialogue_opening'
        return opening['content'], source, opening['evidence']
    if clarification_question(message):
        last = history[-1] if history else None
        if pending or (last is not None and last.role == 'assistant' and last.metadata.get('is_valid') is False):
            reason = pending['reason'] if pending else (last.metadata.get('generation') or {}).get('status')
            reasons = {'dialogue_repetition': 'ripeteva una risposta o una domanda già affrontata',
                       'internal_commentary': 'commentava le istruzioni invece di affrontare la domanda',
                       'subject_mismatch': 'non distingueva correttamente la tua esperienza dalla mia',
                       'unsupported_personal_claim': 'attribuiva ad ALLMA esperienze personali non documentate',
                       'identity_conflict': 'descriveva un’identità incoerente con ALLMA',
                       'format_mismatch': 'non rispettava il formato richiesto'}
            if reason in reasons:
                recovery = opening_recovery(pending['request'].content) if pending else None
                explicit_reason = query in {'perché hai bloccato la risposta', 'perche hai bloccato la risposta'}
                text = ((f'Il controllo ha trattenuto la risposta perché {reasons[reason]}. '
                         'Questo segnala un problema della risposta generata, non del tuo messaggio.')
                        if explicit_reason else
                        'La mia risposta precedente non era utilizzabile; la tua richiesta è ancora senza risposta.')
                if query in {'what do you mean', 'why was the answer blocked'}:
                    text = 'My previous answer was unusable; your request is still unanswered.'
                if recovery:
                    text += ' ' + recovery['content']
                return (text,
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
