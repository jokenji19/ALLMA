"""Bounded host task recognition, never a generated or prewritten answer.

Only self-contained greeting composition is recognized. Other recipients,
quotations, multiple actions and requests requiring episodic data fall through
to the existing router. The language model still writes every greeting.
"""
from dataclasses import dataclass
import re


TASK_VERSION = 3
_ADJECTIVE = r'(?:breve|semplice|cordiale|affettuoso|caloroso|gentile|personale|personalizzato)'
_OPENING = (r'(?:per favore[, ]+)?(?:scrivimi|scrivi(?: per me)?|preparami|prepara(?: per me)?|'
            r'componi(?: per me)?|puoi scrivermi|mi scrivi|mi prepari)')
_GREETING = re.compile(
    _OPENING + r'\s+'
    r'un\s+(?:' + _ADJECTIVE + r'\s+){0,3}(?:saluto|messaggio di benvenuto)'
    r'(?:\s+' + _ADJECTIVE + r'){0,3}(?:\s+(?:per me|rivolto a me))?'
    r'(?:,?\s+(?:rispettando i dati che puoi ancora usare|senza usare il mio nome|'
    r'senza il mio nome|usando il mio nome|con il mio nome))?', re.I)


@dataclass(frozen=True)
class DialogueTask:
    kind: str
    personal_fields: tuple
    requires_name: bool = False
    model_request: str = ''

    def instruction(self):
        text = ('Compito attuale: scrivere un saluto rivolto all’utente. '
                'La risposta finale deve essere il saluto, senza commenti sul sistema o sulla gestione dei ricordi. ')
        if not self.personal_fields:
            text += 'Non inserire nomi di persona. '
        elif self.requires_name:
            text += 'Se il nome non è disponibile, chiedi come rivolgerti all’utente senza inventarlo. '
        else:
            text += 'Puoi salutare anche senza un nome. '
        return text

    def output_issue(self, answer):
        # Narrow rejection of instruction-only echoes, not a semantic quality score.
        text = ' '.join(str(answer or '').strip().split()).strip(' .!?"“”').casefold()
        request = self.model_request.strip(' .!?').casefold()
        if text and (text == request or re.fullmatch(
                r'(?:rispondi\s+)?(?:in|con) (?:una|due|tre|1|2|3) fras[ei]', text)):
            return 'instruction_echo'
        return None

    def decision(self):
        return {'domain':'dialogue_route', 'mode':'operational', 'status':'selected',
                'choice':'reason', 'source':'host_dialogue_task', 'task':self.kind,
                'total_ms':0., 'elapsed_ms':0.}


def writing_task(message):
    original = ' '.join(message.strip().split())
    text = original
    # The suffix is a task constraint; do not swallow arbitrary extra actions.
    text = re.sub(r'[.!?]\s*Rispondi (?:in|con) (?:una|due|tre|1|2|3) fras[ei][.!?]?$', '', text, flags=re.I)
    text = text.rstrip('.!?')
    if not _GREETING.fullmatch(text):
        return None
    no_name = bool(re.search(r'\bsenza (?:usare )?il mio nome\b', text, re.I))
    required = bool(re.search(r'\b(?:usando|con) il mio nome\b', text, re.I))
    personal = required or bool(re.search(r'\bpersonal[ei]|\bpersonalizzato\b', text, re.I))
    # Compile a recognized polite request into an imperative. Keep recipient,
    # tone, name constraints and answer format; persist the original separately.
    model_request = re.sub('^' + _OPENING + r'\s+', 'Scrivi ', original, count=1, flags=re.I)
    model_request = re.sub(r'\?(?=\s+Rispondi\b)', '.', model_request, flags=re.I)
    if model_request.endswith('?'):
        model_request = model_request[:-1] + '.'
    return DialogueTask('compose_greeting', ('name',) if personal and not no_name else (), required, model_request)
