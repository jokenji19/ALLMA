"""Bind arbitrary replies to the assistant's actual preceding questions.

The host supplies roles and dialogue continuity, not the meaning of an
unknown sentence. The model interprets that sentence in its real context.
There is no vocabulary of allowed answers and no stored response template.
"""
from dataclasses import dataclass
import json
import re

VERSION = 1


def questions(text):
    if not isinstance(text,str):
        return ()
    # Punctuation inside reported speech/code is not a question to the user.
    # Preserve quoted alternatives inside a real question verbatim.
    text=text[-2400:]; spans=[];start=0;quote=None;code=False;i=0
    closing={'«':'»','“':'”','"':'"','`':'`'}
    while i<len(text):
        if text.startswith('```',i) and quote is None:
            code=not code;i+=3;start=i;continue
        char=text[i]
        if not code:
            if quote:
                if char==quote and (i==0 or text[i-1]!='\\'):quote=None
            elif char in closing:quote=closing[char]
            elif char=='?':
                value=text[start:i+1].strip()
                if value:spans.append(value)
                start=i+1
            elif char in '.!\n':start=i+1
        i+=1
    return tuple(spans[-3:])


@dataclass(frozen=True)
class ConversationReply:
    reply: str
    preceding_questions: tuple
    kind: str = 'answer_question'
    personal_fields = None
    direct: bool = False
    skip_episode_lookup: bool = False
    host_route: bool = False

    @property
    def model_request(self):
        return ('Nel turno precedente hai rivolto all’utente queste domande: '+
            json.dumps(self.preceding_questions,ensure_ascii=False)+'. '
            'Il suo messaggio attuale è: '+json.dumps(self.reply,ensure_ascii=False)+'. '
            'Interpretalo nel contesto e prosegui affrontandone il contenuto.')

    def instruction(self):
        return ('Mantieni la continuità fra la domanda che hai posto e ciò che risponde l’utente. '
            'Usa le nuove informazioni, anche se espresse con parole o frasi diverse. '
            'Il messaggio può rispondere, precisare, rifiutare o introdurre una nuova richiesta: '
            'dai priorità al suo significato attuale. Se manca un dato, chiedi il dettaglio mancante '
            'invece di ripetere l’intera domanda. Non trattare le sue esperienze come tue.')

    def output_issue(self,answer):
        return 'instruction_echo' if str(answer or '').strip()==self.model_request else None


def reply_task(message, preceding_questions):
    if not preceding_questions or not isinstance(message,str) or not message.strip():
        return None
    # No vocabulary gate. This is context, not a claim that the question was
    # satisfied. Routing, retrieval, output constraints and reasoning stay live.
    return ConversationReply(message,preceding_questions)


def reasked(sentence, preceding_questions):
    from .dialogue_continuity import normalized,wellbeing_question
    if len(preceding_questions)!=1:
        return False  # A reply may have answered only one of several questions.
    original=preceding_questions[0]
    return (normalized(sentence)==normalized(original)
        or (wellbeing_question(original) and bool(re.fullmatch(
            r'(?:(?:e|and)\s+)?(?:come (?:stai|ti senti|ti va|va)|tutto bene|how are you)'
            r'(?:\s+(?:oggi|adesso|ora|in questo momento|today|now))?\s*\?',sentence,re.I))))
