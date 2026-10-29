"""Conservative checks across turns; no generated replacement answers."""
import re
import unicodedata
import hashlib
from .dialogue_recovery import dialogue_history, unanswered_attempt

POLICY_VERSION = 4


def task_content(message):
    """Remove only a bounded conversational frame for routing, not user evidence.

    The original input is still stored and sent to the language model. A
    personal reference inside the actual question remains a personal reference.
    """
    match = re.match(
        r'^\s*(?:(?:il mio dubbio|la mia domanda|la mia curiosità)\s+(?:è|e)(?:\s+quest[oa])?'
        r'|(?:mi chiedo|vorrei sapere|volevo sapere)'
        r'|my question is(?: this)?|i wonder)\s*:\s*(\S[\s\S]*)$', message or '', re.I)
    return match[1] if match else message


def _confirmation(message):
    text = normalized(message)
    if re.match(r'^(?:mi confermi|confermi|ho capito bene|è corretto|is that correct|does that mean)\b', text):
        return True
    return bool('?' in message and re.match(r'^(?:quindi|dunque|perciò|so|therefore)\b', text)
                and not re.match(r'^(?:quindi|dunque|perciò|so|therefore) (?:perché|come|why|how)\b', text)
                and len(text.split()) > 3)


def _clarifies_subject(message):
    return bool(re.match(r'^(?:no[,!]?\s+)?(?:non intendevo|intendevo|mi riferivo|parlavo di|'
                         r'volevo dire|i meant|i was referring to)\b', message.strip(), re.I))


def normalized(text):
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', text or '').casefold()))


def explicit_repeat(message):
    text = normalized(message)
    if re.search(r'\b(?:non|evita di|senza) (?:ripetere|ripeti|riassumere|riassumi|sintetizzare|sintetizza|riordinare|riordina)|'
                 r'\bnon ripeterti\b|\b(?:do not|don t) (?:repeat|summari[sz]e|reorder|quote)\b', text):
        return False
    return bool(re.search(r'\b(?:ripeti|ripetimi|riproponi|repeat|copia|ricopia|traduci|translate|riscrivi|riformula|'
                          r'riassumi|sintetizza|riordina|summarize|summarise|reorder|quote)\b', text))


def explicit_no_reuse(message):
    plain = re.sub(r'```.*?(?:```|$)|`[^`]*`|"[^"\n]*"|«[^»]*»|“[^”]*”', ' ', message or '', flags=re.S)
    text = normalized(plain)
    return bool(re.search(r'\b(?:non ripeterti|senza ripeterti|stop repeating yourself|without repeating yourself)\b|'
        r'\b(?:senza|non|evita di) (?:ripetere|ricopiare) '
        r'(?:i (?:punti|concetti|passaggi)(?: già detti| precedenti| già spiegati)|'
        r'la (?:risposta precedente|parte già scritta)|(?:quello|ciò) che hai già (?:detto|scritto))\b|'
        r'\b(?:without repeating|do not repeat) (?:the previous answer|the points already (?:made|covered))\b', text))


def wellbeing_question(text):
    # A narrow dialogue intent, not a general semantic equivalence classifier.
    plain = re.sub(r'```.*?(?:```|$)|"[^"\n]*"|«[^»]*»|“[^”]*”', '', text, flags=re.S)
    return bool(re.search(r'\b(?:come (?:stai|ti senti|ti va|va)|tutto bene|how are you)(?:\s+(?:oggi|adesso|ora|in questo momento))?\s*\?', plain, re.I))


def quantity_guidance(text):
    if re.search(r'\b(?:quanti|quante)\b', text, re.I) and re.search(r'\b(?:rimangono|restano|rimasti|rimaste|totale|rimosse|rimossi|tolti|tolte)\b', text, re.I):
        return (' Nei conteggi distingui il totale presente dagli elementi che cambiano stato: '
                'sottrai solo ciò che è effettivamente rimosso dalla categoria richiesta. '
                'Verifica premesse incompatibili.')
    return ''


class DialogueContinuity:
    def __init__(self, message, history, attempt_history=None):
        attempts = attempt_history if attempt_history is not None else history
        history = dialogue_history(history)
        pending = unanswered_attempt(attempts)
        self.message = message
        self.correction = bool(re.search(
            r'\b(?:già chiesto|già risposto|ti ho risposto|te l ho (?:detto|già detto)|'
            r'non ripeterti|non ripetere|stai ripetendo|ti ripeti|hai ripetuto|'
            r'already answered|already asked|stop repeating)\b', normalized(message)))
        self.previous_answer = ''
        self.previous_question = ''
        # Input is already scoped to the current user/conversation and valid history.
        for turn in reversed(history):
            if turn.role == 'assistant' and not self.previous_answer:
                self.previous_answer = turn.content
            elif turn.role == 'user' and self.previous_answer:
                self.previous_question = turn.content
                break
        from .response_guidance import is_explicit_correction
        self.factual_correction = bool(self.previous_answer and is_explicit_correction(message))
        self.allow_repeat = explicit_repeat(message) and not self.correction
        self.avoid_reuse = explicit_no_reuse(message)
        self.answered_checkin = False
        self.responding_to_checkin = False
        awaiting = False
        for turn in history[-6:]:
            if turn.role == 'assistant' and wellbeing_question(turn.content):
                awaiting = True
            elif turn.role == 'user' and awaiting:
                self.answered_checkin = True
                awaiting = False
        # The current message is also an answer to the latest check-in.
        if awaiting and re.search(r'\b(?:bene|male|sto|mi sento|preferisco non|non lo so)\b', normalized(message)):
            self.answered_checkin = True
            self.responding_to_checkin = True
        from .checkin_turn import checkin_task
        if awaiting and checkin_task(message,self.previous_answer) is not None:
            self.answered_checkin = True
            self.responding_to_checkin = True
        asks_checkin = re.search(r'\b(?:chiedimi|domandami|ask me)\b.*\b(?:come|how)\b', normalized(message))
        if self.allow_repeat or asks_checkin or re.search(r'\b(?:scrivi|inventa|esempio|dialogo|roleplay)\b', normalized(message)):
            self.answered_checkin = False
            self.responding_to_checkin = False
        self.same_request = normalized(message) == normalized(self.previous_question)
        self.confirmation = bool((self.previous_answer or pending) and _confirmation(message))
        self.subject_clarification = bool((self.previous_answer or pending) and _clarifies_subject(message))
        self.continuation = bool(self.previous_answer and re.match(
            r'^(?:continua|prosegui|completa)(?: la risposta precedente| dal punto| da dove| senza ripetere|$)',
            normalized(message)))
        # Failed assistant text is not evidence, but a failed attempt exists.
        # Compare retries with the latest user request, not an older success.
        last = attempts[-1] if attempts else None
        last_user = next((turn for turn in reversed(attempts) if turn.role == 'user'), None)
        self.retry_after_failure = bool(last is not None and last.role == 'assistant'
            and getattr(last, 'metadata', {}).get('is_valid') is False
            and last_user is not None and normalized(last_user.content) == normalized(message))
        if pending and normalized(pending['request'].content) == normalized(message):
            self.retry_after_failure = True
        if self.retry_after_failure and not self.correction:
            self.same_request = True
        self.task_content = task_content(message)
        self.mode = ('correction' if self.factual_correction or self.correction else
                     'subject_clarification' if self.subject_clarification else
                     'confirmation' if self.confirmation else 'repeat' if self.allow_repeat else
                     'continuation' if self.continuation else 'retry' if self.retry_after_failure else
                     'elaboration' if (self.previous_answer or pending) and re.fullmatch(
                         r'(?:puoi )?(?:spiega(?:re)? meglio|approfondisci|approfondire|perché|perche|come mai|'
                         r'cosa intendi|why|explain more|tell me more)', normalized(message)) else
                     'provide_details' if last is not None and last.role == 'assistant'
                         and getattr(last, 'metadata', {}).get('source') in ('dialogue_opening', 'grounded_dialogue_recovery', 'clarification') else
                     'request')
        follows_pending = bool(pending and self.mode in ('retry', 'confirmation', 'elaboration', 'subject_clarification', 'correction'))
        self.pending_request = pending['request'].content if follows_pending else None
        self.reference_request = self.pending_request or self.previous_question
        self.reference_content = task_content(self.reference_request)
        self.checkin_task = (checkin_task(message,self.previous_answer)
            if self.responding_to_checkin or self.retry_after_failure else None)
        if self.checkin_task is not None:
            self.mode = 'checkin_answer'
            self.responding_to_checkin = True
        from .conversation_reply import questions,reply_task
        pending_context = bool(history and history[-1].role=='assistant') or self.retry_after_failure
        self.preceding_questions = questions(self.previous_answer) if pending_context else ()
        self.question_task = self.checkin_task
        if self.question_task is None and self.mode in ('request','retry'):
            self.question_task = reply_task(message,self.preceding_questions)
            if self.question_task is not None:
                self.mode='question_answer'
        self.previous = normalized(self.previous_answer)
        # An equation copied from a previous turn is not an explanation of an
        # explicitly named new subject. Keep legitimate arithmetic/follow-ups.
        plain = normalized(message)
        self.expects_nonnumeric_explanation = bool(self.previous_answer and
            re.match(r'^(?:spiega(?:mi)?|descrivi(?:mi)?|explain|describe)\b', plain) and
            not re.search(r'\d|\b(?:calcol\w*|risultat\w*|operazion\w*|numero|numeri|somma|equazion\w*|precedente|questo|quello|sopra|it|that|previous)\b', plain))
        self.check_duplicate = (not self.factual_correction and not self.allow_repeat and not self.same_request and not self.confirmation
                                and len(self.previous.split()) >= (4 if self.correction else 8))

    def state(self):
        """Rebuildable working view; fingerprints are references, not new facts."""
        digest = lambda text: hashlib.sha256(text.encode('utf-8')).hexdigest() if text else None
        return {'version': POLICY_VERSION, 'mode': self.mode,
                'request_sha256': digest(self.message),
                'reference_sha256': digest(self.reference_request) if self.mode != 'request' else None,
                'unanswered_sha256': digest(self.pending_request),
                'responding_to_checkin': self.responding_to_checkin,
                'preceding_question_sha256': [digest(q) for q in self.preceding_questions],
                'frame_removed_for_routing': self.task_content != self.message}

    def repeated_fragments(self, answer):
        # A bounded exact-fragment check, not a semantic equivalence model.
        # Shared facts can be useful: partial reuse is telemetry, not rejection.
        if '```' in answer or '```' in self.previous_answer:
            return 0, False
        pieces = [normalized(p) for p in re.split(r'[.!?]+(?=\s|$)', answer) if normalized(p)]
        previous = {normalized(p) for p in re.split(r'[.!?]+(?=\s|$)', self.previous_answer) if normalized(p)}
        substantial = [p for p in pieces if len(p.split()) >= 8]
        repeated = [p for p in substantial if p in previous]
        wrapper = {'certo', 'certamente', 'ecco', 'come già detto', 'as mentioned'}
        all_reused = bool(repeated and all(p in repeated or p in wrapper for p in pieces))
        return len(repeated), all_reused

    def irrelevant_arithmetic(self, answer):
        return bool(self.expects_nonnumeric_explanation and re.fullmatch(
            r'[\s\d.,+−*/×÷^=():%!?-]+', str(answer or '').strip()) and re.search(r'\d', answer or ''))

    def duplicate(self, answer):
        from .dialogue_reasoning import copied_without_progress
        return (self.irrelevant_arithmetic(answer) or (self.check_duplicate and
                (normalized(answer) == self.previous or self.repeated_fragments(answer)[1]))
                or (self.avoid_reuse and self.repeated_fragments(answer)[0] > 0)
                or (not self.allow_repeat and not self.factual_correction and
                    copied_without_progress(answer, self.previous_answer, self.message))
                or self.repeated_continuation_prefix(answer)
                or (self.answered_checkin and wellbeing_question(answer)))

    def repeated_continuation_prefix(self, answer):
        words = normalized(answer).split()
        if not self.continuation or len(words) < 10 or '```' in answer:
            return False
        return (' ' + ' '.join(words[:10]) + ' ') in (' ' + self.previous + ' ')

    def hold_prefix(self, answer):
        """Buffer a matching prefix until divergence; do not leak a full duplicate."""
        current = normalized(answer)
        return (self.irrelevant_arithmetic(answer) or
                (self.check_duplicate and (not current or self.previous.startswith(current))))

    def guidance(self):
        if not self.previous_answer:
            return (('La richiesta precedente non ha ricevuto una risposta utilizzabile: riprendi la richiesta attuale, '
                     'senza discutere gli avvisi tecnici. ' if self.retry_after_failure else '')
                    + quantity_guidance(self.message))
        text = ('Continua il dialogo dal messaggio attuale: usa le risposte già date '
                'dall’utente, evita di riaprire il saluto e di riproporre domande già soddisfatte. '
                'Non aggiungere orario, batteria o stato tecnico se non sono pertinenti alla richiesta.')
        if self.answered_checkin:
            text += ' Non reiterare domande sul benessere già affrontate nei turni recenti.'
        if self.confirmation:
            text += ' L’utente chiede conferma: verifica il punto proposto e confermalo o correggilo, motivando solo ciò che serve.'
        if self.subject_clarification:
            text += ' L’utente precisa ciò che intendeva: segui il tema precisato nel messaggio attuale.'
        if self.mode == 'provide_details':
            text += ' L’utente specifica la domanda dopo il chiarimento: affronta ora il contenuto indicato.'
        if self.mode == 'elaboration':
            text += ' Aggiungi una spiegazione o un esempio pertinente al punto precedente.'
        if self.retry_after_failure:
            text += ' La richiesta è ripetuta dopo un tentativo non riuscito: rispondi alla richiesta attuale, senza interpretarla come una correzione o un cambio di argomento.'
        if re.search(r'\b(?:solo quest[oi]|altro|approfondisci|spieg(?:a|are) meglio|più dettagli|piu dettagli)\b', normalized(self.message)):
            text += (' L’utente chiede un ampliamento: aggiungi elementi pertinenti o chiarisci i limiti, '
                     'non ricopiare l’elenco o la risposta precedente.')
        if self.factual_correction:
            text = ('L’utente contesta la risposta: riesamina la domanda originale, premesse e conclusione. '
                    'La correzione è da verificare: non accettarla automaticamente; '
                    'non difendere una risposta perché già data. '
                    'Rispondi brevemente con la premessa decisiva e il risultato.')
        if self.continuation:
            text += (' La risposta precedente è da completare: riparti dall’ultimo punto incompleto. '
                     'Non ricominciare l’introduzione né riassumere ciò che hai già scritto. '
                     'Se è già conclusa, dillo brevemente senza inventare un seguito.')
        quantity_text = self.message + ' ' + (self.reference_request if self.factual_correction else '')
        text += quantity_guidance(quantity_text)
        if self.correction:
            text += (' L’utente segnala una ripetizione: riconosci la correzione, '
                     'rileggi i turni precedenti e non riproporre la risposta contestata. '
                     'Non inventare dettagli per cambiare risposta.')
        return text
