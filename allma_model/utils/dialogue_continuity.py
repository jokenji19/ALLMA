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


class DialogueContinuity:
    def __init__(self, message, history):
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
        self.allow_repeat = explicit_repeat(message) and not self.correction
        self.answered_checkin = False
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
        asks_checkin = re.search(r'\b(?:chiedimi|domandami|ask me)\b.*\b(?:come|how)\b', normalized(message))
        if self.allow_repeat or asks_checkin or re.search(r'\b(?:scrivi|inventa|esempio|dialogo|roleplay)\b', normalized(message)):
            self.answered_checkin = False
        self.same_request = normalized(message) == normalized(self.previous_question)
        self.previous = normalized(self.previous_answer)
        self.check_duplicate = (not self.allow_repeat and not self.same_request
                                and len(self.previous.split()) >= (4 if self.correction else 8))

    def duplicate(self, answer):
        return ((self.check_duplicate and normalized(answer) == self.previous)
                or (self.answered_checkin and wellbeing_question(answer)))

    def hold_prefix(self, answer):
        """Buffer a matching prefix until divergence; do not leak a full duplicate."""
        current = normalized(answer)
        return self.check_duplicate and (not current or self.previous.startswith(current))

    def guidance(self):
        if not self.previous_answer:
            return ''
        text = ('Continua il dialogo dal messaggio attuale: usa le risposte già date '
                'dall’utente, evita di riaprire il saluto e di riproporre domande già soddisfatte. '
                'Non aggiungere orario, batteria o stato tecnico se non sono pertinenti alla richiesta.')
        if self.answered_checkin:
            text += ' Non reiterare domande sul benessere già affrontate nei turni recenti.'
        if re.search(r'\b(?:solo quest[oi]|altro|approfondisci|spieg(?:a|are) meglio|più dettagli|piu dettagli)\b', normalized(self.message)):
            text += (' L’utente chiede un ampliamento: aggiungi elementi pertinenti o chiarisci i limiti, '
                     'non ricopiare l’elenco o la risposta precedente.')
        if self.correction:
            text += (' L’utente segnala una ripetizione: riconosci la correzione, '
                     'rileggi i turni precedenti e non riproporre la risposta contestata. '
                     'Non inventare dettagli per cambiare risposta.')
        return text
