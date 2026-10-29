"""A bounded conversational state transition, never a prewritten reply.

Only an explicit short answer to ALLMA's pending wellbeing question qualifies.
Requests, quotations, reciprocal questions and substantive disclosures retain
the normal reasoning/perception route.
"""
from dataclasses import dataclass
import json
import re
import unicodedata

VERSION = 1


def _plain(text):
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', text).casefold()))


@dataclass(frozen=True)
class CheckinTurn:
    reply: str
    question: str
    positive: bool
    language: str
    kind: str = 'answer_checkin'
    personal_fields: tuple = ()

    @property
    def direct(self):
        return self.positive

    @property
    def model_request(self):
        return ('La tua domanda precedente era: '+json.dumps(self.question,ensure_ascii=False)+'. '
                'L’utente ha risposto: '+json.dumps(self.reply,ensure_ascii=False)+'. '
                'Prosegui il dialogo riconoscendo la sua risposta, in '+self.language+'.')

    def instruction(self):
        return ('Il turno attuale risponde alla domanda sul benessere che avevi posto tu. '
                'Riconosci ciò che riferisce l’utente con una breve risposta rivolta a lui. '
                'Non rifare la domanda a cui ha appena risposto e non riaprire il saluto. '
                'Non descrivere il suo stato come se fosse il tuo. '
                'Puoi lasciare spazio a un nuovo argomento o, se sta male, chiedere se vuole parlarne. '
                'Nessun ricordo passato è necessario per comprendere questa risposta.')

    def decision(self):
        return {'domain':'dialogue_route','mode':'operational','status':'selected',
                'choice':'reason','source':'host_dialogue_task','task':self.kind,
                'total_ms':0.,'elapsed_ms':0.}

    def output_issue(self, answer):
        return 'instruction_echo' if _plain(answer)==_plain(self.model_request) else None

    def borrowed_state(self, answer):
        # A first-person wellbeing answer would appropriate this user's report.
        # Quoted/reported speech is data, not an autobiographical claim.
        text=re.sub(r'«[^»]*»|“[^”]*”|"[^"\n]*"|`[^`]*`', '', answer or '')
        return bool(re.search(r'\b(?:sto (?:molto |abbastanza )?(?:bene|male)|'
            r'mi sento (?:bene|male|felice|triste)|i am (?:fine|good|sad)|'
            r"i[’']m (?:fine|good|sad)|i feel (?:good|bad|sad))\b",text,re.I))


def checkin_task(message, question):
    from .dialogue_continuity import wellbeing_question
    if (not isinstance(message,str) or len(message)>100 or not wellbeing_question(question)
            or re.search(r'[?\n«»“”"`{}<>]',message)):
        return None
    text=_plain(message)
    text=re.sub(r'^(?:grazie|thanks|thank you)\s+|\s+(?:grazie|thanks|thank you)$','',text).strip()
    positive_it=re.fullmatch(r'(?:(?:sto|mi sento) )?(?:(?:molto|abbastanza|davvero|piuttosto) )?bene|'
        r'tutto bene|non c è male|benissimo|alla grande|(?:sono|mi sento) (?:felice|content[oa]|seren[oa])',text)
    negative_it=re.fullmatch(r'(?:sto )?(?:molto )?male|non (?:sto )?bene|cos[iì] cos[iì]|'
        r'(?:sono|mi sento) (?:triste|giù|giu)|non lo so',text)
    positive_en=re.fullmatch(r'(?:(?:i am|i m|i feel) )?(?:fine|good|great|okay|ok|well)|'
        r'not bad|pretty good',text)
    negative_en=re.fullmatch(r'(?:(?:i am|i m|i feel) )?(?:bad|sad|not (?:good|well|okay))|i don t know',text)
    if not any((positive_it,negative_it,positive_en,negative_en)):
        return None
    language='italiano' if positive_it or negative_it else 'inglese'
    # A single ambiguous "ok" follows the language of the actual question.
    if text in {'ok','okay'} and re.search(r'\bcome\b|tutto bene',question,re.I):
        language='italiano'
    return CheckinTurn(message,question,bool(positive_it or positive_en),language)
