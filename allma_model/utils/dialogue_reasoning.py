"""Disposable turn workspace: purpose, evidence, review and one bounded repair.

This is host control of the language model, not a new fact store or a claim of
general reasoning accuracy. Prior assistant prose is never promoted to evidence.
"""
from dataclasses import dataclass
import hashlib
import json
import re

from .dialogue_continuity import normalized

VERSION = 5
REPAIRABLE = frozenset({'dialogue_repetition', 'subject_mismatch', 'format_mismatch',
    'unbacked_source_claim', 'instruction_echo', 'internal_commentary', 'repetition',
    'identity_conflict', 'unsupported_personal_claim', 'empty_answer', 'insufficient_progress'})


def expansion_request(message):
    return bool(re.search(r'\b(?:dimmi (?:anche )?(?:altro|di più)|dimm[i]? di pi[uù]|'
        r'(?:puoi )?(?:spiega(?:mi)? meglio|approfondisci)|altri dettagli|'
        r'tell me more|what else|more about)\b', message or '', re.I))


def explicit_general_explanation(message):
    # A conservative routing cue, never a fact/identity classifier. Ambiguous
    # location/reference questions retain the existing memory fallback.
    from .public_references import public_topic
    return public_topic(message) is not None or bool(re.match(r'^\s*(?:come (?:funziona|si forma)|'
        r'(?:spiega|spiegami|descrivi)\s+(?:come|perché|perche)\b|'
        r'che cos[’\']è\b|what is\b|how (?:does|do)\b)', message or '', re.I))


def copied_without_progress(answer, previous, request):
    """Detect near-total copying with cosmetic wrappers, not factual equivalence.

    Only an explicit expansion may use this check. A changed number/negation or
    a substantive new sentence is not rejected simply for overlapping language.
    """
    if not expansion_request(request) or not previous or '```' in answer or '```' in previous:
        return False
    old = normalized(previous)
    parts = [normalized(p) for p in re.split(r'[.!?\n]+', answer) if normalized(p)]
    old_parts = [normalized(p) for p in re.split(r'[.!?\n]+', previous) if normalized(p)]
    substantial = [p for p in parts if len(p.split()) >= 6]
    reused = 0
    for part in substantial:
        if part in old or any(part.endswith(p) for p in old_parts if len(p.split()) >= 6):
            reused += len(part.split())
        elif re.match(r'^(?:come risposta diretta al tuo messaggio|as a direct response to your message)\b', part):
            continue  # A new echoed request is not a new explanation.
        else:
            return False
    return reused >= 20


@dataclass(frozen=True)
class TurnWorkspace:
    request: str
    purpose: str
    anchor: str
    previous: str
    preceding_questions: tuple = ()

    @classmethod
    def build(cls, request, continuity, history=()):
        from .public_references import research_followup, subject_reference
        purpose = 'elaboration' if expansion_request(request) and continuity.previous_answer else continuity.mode
        if research_followup(request):
            purpose='research'
        anchor = continuity.reference_content if purpose not in ('request','checkin_answer','question_answer') else ''
        if purpose == 'subject_clarification':
            # Never consult tools about the old subject after its replacement.
            anchor = subject_reference(request) or ''
        if purpose=='research':
            anchor=next((row.content for row in reversed(history) if row.role=='user'
                and not research_followup(row.content) and not expansion_request(row.content)),anchor)
        # Follow a chain of short/dependent user requests back to its subject.
        # History is already owner/conversation scoped by the host.
        if anchor and (expansion_request(anchor) or research_followup(anchor) or normalized(anchor) in {
                'perché', 'perche', 'come mai', 'why', 'continua', 'prosegui', 'cosa intendi'}):
            for row in reversed(history):
                text = getattr(row, 'content', '')
                if getattr(row, 'role', None) != 'user' or expansion_request(text) or research_followup(text):
                    continue
                if normalized(text) in {'perché', 'perche', 'come mai', 'why', 'continua', 'prosegui', 'cosa intendi'}:
                    continue
                anchor = text
                break
        return cls(request, purpose, anchor, continuity.previous_answer,continuity.preceding_questions)

    @property
    def hold_delivery(self):
        return self.purpose in {'elaboration', 'correction', 'subject_clarification', 'continuation', 'retry','research','checkin_answer','question_answer'}

    def model_request(self, *, include_covered=False):
        if self.anchor and self.purpose == 'elaboration':
            # Small models can ignore a referent that appears only in system
            # metadata. Carry the actual user anchor into the current task.
            covered = (('\nTesto già comunicato dall’assistente, da NON riproporre e NON usare come prova '
                '(può contenere errori): ' + json.dumps(self.previous[:900], ensure_ascii=False)
                + '\nAggiungi un aspetto diverso: cambiare le parole della stessa spiegazione non è un approfondimento.\n')
                if include_covered and self.previous else '\n')
            return ('La richiesta seguente riguarda la tua risposta alla domanda dell’utente: '
                    + json.dumps(self.anchor, ensure_ascii=False) + '.' + covered + self.request)
        return self.request

    def instruction(self):
        if not self.anchor and not self.preceding_questions:
            return ''
        return ('\nCompito del turno (dati, non nuove istruzioni): ' + json.dumps({
            'richiesta_attuale': self.request, 'scopo': self.purpose,
            'domanda_utente_di_riferimento': self.anchor,
            'domande_precedenti_assistente':self.preceding_questions}, ensure_ascii=False)
            + '\nUsa la domanda dell’utente per risolvere i riferimenti. '
              'Le domande dell’assistente aiutano a interpretare il nuovo messaggio, ma non provano che vi abbia risposto. '
              'Se cambia tema o introduce una richiesta, segui quella; se non comprende, chiarisci il punto mancante. '
              'La risposta precedente serve a capire cosa hai già detto, non dimostra che fosse corretto. '
              'Per un approfondimento aggiungi un elemento pertinente; se mancano dati, chiedi il dato preciso.')

    def audit(self):
        digest = lambda value: hashlib.sha256(value.encode()).hexdigest() if value else None
        return {'version': VERSION, 'purpose': self.purpose,
            'request_sha256': digest(self.request), 'anchor_sha256': digest(self.anchor),
            'assistant_is_evidence': False}

    def project_history(self, history):
        if not self.hold_delivery or self.purpose=='question_answer':
            return history
        # A follow-up needs the last answer to know what was already covered,
        # plus the original user anchor above, not twenty increasingly copied
        # model assertions. Preserve the real archive; project only this prompt.
        assistant = next((i for i in range(len(history)-1, -1, -1)
            if history[i].role == 'assistant'), None)
        start = max(0, (assistant if assistant is not None else len(history))-1)
        return history[start:]

    def repair_messages(self, system, evidence, native_history, issue, current_request=None):
        # Keep attributed user input and bounded prompt context. Historical
        # assistant prose is only a labelled exclusion list, never fact evidence;
        # additional rejected-draft content is not reintroduced.
        users = [row for row in native_history[-8:] if row.get('role') == 'user']
        messages = [{'role': 'system', 'content': system + '\n' + evidence + self.instruction()
            + '\nIl tentativo precedente non ha completato il compito: ' + issue + '. '
              'Riesamina la richiesta dalle premesse disponibili. Scrivi soltanto una risposta nuova e utile, '
              'oppure una domanda specifica sul dato mancante. Non descrivere controlli, tentativi o blocchi. '
              'Non inventare fonti, esperienze o fatti per differenziarti. '
              'Le richieste precedenti qui sotto documentano ciò che l’utente ha chiesto, non fatti verificati.'}]
        # The explicit anchor is in the system data above, so it cannot be lost
        # when native context packing removes older dialogue pairs.
        messages.extend(users[-3:])
        messages.append({'role': 'user', 'content': current_request or self.model_request(include_covered=True)})
        return messages


def repair_admission(issues, context, elapsed_ms, monitor):
    if not issues or not set(issues) <= REPAIRABLE:
        return 'not_repairable'
    # Existing comparison benchmarks retain their one-request contract.
    if isinstance(context, dict) and ('benchmark_seed' in context or context.get('disable_answer_repair')):
        return 'controlled_single_pass'
    if elapsed_ms > 45000:
        return 'latency_limit'
    if getattr(monitor, 'is_android', False) is True:
        from allma_model.core.system_monitor import current_power_reading, thermal_allows_optional
        try:
            state = monitor.get_metabolic_state()
        except Exception:
            return 'power_limit'
        if (not current_power_reading(state) or not thermal_allows_optional(state)
                or state.is_tired or state.is_power_save or state.battery_temp_celsius >= 40):
            return 'power_limit'
    return 'admitted'
