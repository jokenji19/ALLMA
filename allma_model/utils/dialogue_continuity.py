"""Conservative checks across turns; no generated replacement answers."""
import re
import unicodedata


def normalized(text):
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', text or '').casefold()))


def explicit_repeat(message):
    text = normalized(message)
    if re.search(r'\b(?:non|evita di|senza) (?:ripetere|ripeti)|\bnon ripeterti\b', text):
        return False
    return bool(re.search(r'\b(?:ripeti|ripetimi|riproponi|repeat|copia|ricopia|traduci|translate|riscrivi|riformula)\b', text))


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
        asks_checkin = re.search(r'\b(?:chiedimi|domandami|ask me)\b.*\b(?:come|how)\b', normalized(message))
        if self.allow_repeat or asks_checkin or re.search(r'\b(?:scrivi|inventa|esempio|dialogo|roleplay)\b', normalized(message)):
            self.answered_checkin = False
            self.responding_to_checkin = False
        self.same_request = normalized(message) == normalized(self.previous_question)
        self.continuation = bool(self.previous_answer and re.match(
            r'^(?:continua|prosegui|completa)(?: la risposta precedente| dal punto| da dove| senza ripetere|$)',
            normalized(message)))
        # Failed assistant text is not evidence, but a failed attempt exists.
        # Compare retries with the latest user request, not an older success.
        attempts = attempt_history if attempt_history is not None else history
        last = attempts[-1] if attempts else None
        last_user = next((turn for turn in reversed(attempts) if turn.role == 'user'), None)
        self.retry_after_failure = bool(last is not None and last.role == 'assistant'
            and getattr(last, 'metadata', {}).get('is_valid') is False
            and last_user is not None and normalized(last_user.content) == normalized(message))
        if self.retry_after_failure and not self.correction:
            self.same_request = True
        self.previous = normalized(self.previous_answer)
        # An equation copied from a previous turn is not an explanation of an
        # explicitly named new subject. Keep legitimate arithmetic/follow-ups.
        plain = normalized(message)
        self.expects_nonnumeric_explanation = bool(self.previous_answer and
            re.match(r'^(?:spiega(?:mi)?|descrivi(?:mi)?|explain|describe)\b', plain) and
            not re.search(r'\d|\b(?:calcol\w*|risultat\w*|operazion\w*|numero|numeri|somma|equazion\w*|precedente|questo|quello|sopra|it|that|previous)\b', plain))
        self.check_duplicate = (not self.factual_correction and not self.allow_repeat and not self.same_request
                                and len(self.previous.split()) >= (4 if self.correction else 8))

    def irrelevant_arithmetic(self, answer):
        return bool(self.expects_nonnumeric_explanation and re.fullmatch(
            r'[\s\d.,+−*/×÷^=():%!?-]+', str(answer or '').strip()) and re.search(r'\d', answer or ''))

    def duplicate(self, answer):
        return (self.irrelevant_arithmetic(answer) or (self.check_duplicate and normalized(answer) == self.previous)
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
            return quantity_guidance(self.message)
        text = ('Continua il dialogo dal messaggio attuale: usa le risposte già date '
                'dall’utente, evita di riaprire il saluto e di riproporre domande già soddisfatte. '
                'Non aggiungere orario, batteria o stato tecnico se non sono pertinenti alla richiesta.')
        if self.answered_checkin:
            text += ' Non reiterare domande sul benessere già affrontate nei turni recenti.'
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
        quantity_text = self.message + ' ' + (self.previous_question if self.factual_correction else '')
        text += quantity_guidance(quantity_text)
        if self.correction:
            text += (' L’utente segnala una ripetizione: riconosci la correzione, '
                     'rileggi i turni precedenti e non riproporre la risposta contestata. '
                     'Non inventare dettagli per cambiare risposta.')
        return text
