"""Disposable turn workspace: purpose, evidence, review and one bounded repair.

This is host control of the language model, not a new fact store or a claim of
general reasoning accuracy. Prior assistant prose is never promoted to evidence.
"""
from dataclasses import dataclass
import hashlib
import json
import re

from .dialogue_continuity import normalized

VERSION = 7
REPAIRABLE = frozenset({'dialogue_repetition', 'subject_mismatch', 'format_mismatch',
    'unbacked_source_claim', 'instruction_echo', 'internal_commentary', 'repetition',
    'identity_conflict', 'unsupported_personal_claim', 'empty_answer', 'insufficient_progress'})
_REACTION = re.compile(r'^(?:sì|si|esatto|interessante|bello|bella|mi piace(?: molto| tanto)?(?: [\w -]{1,55})?|'
                       r'(?:è|era) il mio preferito)[.!\s]*$', re.I)
_QUESTION_REFERENCE = re.compile(
    r"^(?:(?:e|and|y|et|und|а|и) )?(?:"
    r"(?:perch[eéè]|come mai|quando|dove|come) (?:ha|aveva|hanno|è stato|è stata|è nato|è nata|"
    r"lui|lei|si è)\b|"
    r"(?:perch[eéè]|come mai|quando|dove|come|cosa) (?:è|sono|funziona|significa) (?:lui|lei|quest[oa]|quell[oa])\b|"
    r"(?:why|when|where|how|what) (?:did |does |was |were |is |are )?(?:he|she|it|they|that|this)\b|"
    r"what (?:is|was) (?:his|her|their|its)\b|"
    r"(?:por qu[eé]|cu[aá]ndo|d[oó]nde|c[oó]mo) (?:lo|ella|ellos|ellas|[eé]l|se fue|dej[oó]|naci[oó])\b|"
    r"(?:pourquoi|quand|où|comment) (?:est-il|a-t-il|est-elle|a-t-elle|il|elle|ça|cela)\b|"
    r"(?:warum|wann|wo|wie) (?:hat|ist|war) (?:er|sie|es)\b|"
    r"(?:por que|quando|onde|como) (?:ele|ela)\b|"
    r"(?:почему|когда|где|как) (?:он|она|они|это)\b|"
    r"(?:لماذا|متى|أين|كيف) (?:هو|هي|غادر|غادرت)\b)|"
    r"^(?:他|她|它)(?:为什[么麼]|為什麼|什么時候|什麼時候|什么时候|怎么|怎麼|在哪)|"
    r"^(?:彼|彼女|それ)は(?:なぜ|どうして|いつ|どこ|どう)", re.I)
_GENERAL_QUESTIONS = {
    'es': r'(?:qu[eé] es|cómo (?:funciona|se forma))\s+\S',
    'fr': r"(?:qu['’]est-ce que|comment (?:fonctionne|se forme))\s+\S",
    'de': r'(?:was ist|wie (?:entsteht|funktioniert))\s+\S',
    'pt': r'(?:o que [ée]|como (?:funciona|se forma))\s+\S',
    'ru': r'(?:что такое|как (?:работает|образуется))\s+\S',
    'ar': r'(?:ما (?:هو|هي)|كيف (?:يعمل|تعمل|يتشكل|تتشكل))\s+\S',
    'zh': r'什[么麼]是\S',
    'ja': r'\S+(?:とは(?:何|なん)(?:ですか)?|はどう(?:やって)?(?:でき|生まれ)ますか)[。?？]*$',
}
_GENERAL_PATTERNS = {language: re.compile(shape, re.I) for language, shape in _GENERAL_QUESTIONS.items()}
_CONTEXT_WORDS = re.compile(
    r"\b(?:mio|mia|miei|mie|tuo|tua|nostr\w*|ricord\w*|my|mine|your|our|remember|"
    r"quest[oa]|quell[oa]|this|that|esto|eso|aquello|mis|tus|ça|cela|mon|mes|ton|tes|"
    r"dies(?:e|er|es|en|em)?|mein\w*|dein\w*|isso|isto|meu|minha|"
    r"этот|эта|этого|мо[йяеиё]\w*|هذا|هذه|لدي|عندي)\b|"
    r"我的|你的|这个|這個|那个|那個|私の|あなたの|これ|それ", re.I)


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


def dependent_question(message):
    return bool(_QUESTION_REFERENCE.match((message or '').strip(' ¿¡')))


def general_question_language(message):
    text = message.strip(' \t¿¡')
    return next((language for language, pattern in _GENERAL_PATTERNS.items() if pattern.match(text)), None)


def standalone_question(message):
    # Personal and deictic requests may look like general questions.
    return not _CONTEXT_WORDS.search(message) and (
        explicit_general_explanation(message) or general_question_language(message) is not None)


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
    incomplete: str = ''
    independent: bool = False

    @classmethod
    def build(cls, request, continuity, history=()):
        from .public_references import research_followup, subject_reference
        from .reference_comparison import source_comparison_followup

        def research_continuation(text):
            return research_followup(text) or source_comparison_followup(text)

        purpose = 'elaboration' if expansion_request(request) and continuity.previous_answer else continuity.mode
        if research_continuation(request):
            purpose='research'
        if purpose == 'request' and dependent_question(continuity.task_content):
            purpose = 'followup'
        independent = bool(purpose == 'request' and standalone_question(continuity.task_content))
        previous_turn = history[-1] if history else None
        previous_meta = (getattr(previous_turn, 'metadata', {}) or {}) if previous_turn is not None else {}
        if (purpose == 'request' and _REACTION.fullmatch(request.strip())
                and previous_turn is not None and previous_turn.role == 'assistant'
                and (previous_meta.get('source') == 'reference_excerpt'
                     or (previous_meta.get('turn_review') or {}).get('purpose') == 'reaction')):
            purpose = 'reaction'
        anchor = continuity.reference_content if purpose not in ('request','checkin_answer','question_answer') else ''
        if purpose == 'subject_clarification':
            # Never consult tools about the old subject after its replacement.
            anchor = subject_reference(request) or ''
        if purpose=='research':
            anchor=next((row.content for row in reversed(history) if row.role=='user'
                and not research_continuation(row.content) and not expansion_request(row.content)),anchor)
        # Follow a chain of short/dependent user requests back to its subject.
        # History is already owner/conversation scoped by the host.
        if anchor and (expansion_request(anchor) or research_continuation(anchor) or dependent_question(anchor)
                       or normalized(anchor) in {
                'perché', 'perche', 'come mai', 'why', 'continua', 'prosegui', 'cosa intendi'}):
            for row in reversed(history):
                text = getattr(row, 'content', '')
                if (getattr(row, 'role', None) != 'user' or expansion_request(text)
                        or research_continuation(text) or dependent_question(text)):
                    continue
                if normalized(text) in {'perché', 'perche', 'come mai', 'why', 'continua', 'prosegui', 'cosa intendi'}:
                    continue
                anchor = text
                break
        questions = () if independent else continuity.preceding_questions
        return cls(request, purpose, anchor, continuity.previous_answer, questions,
                   continuity.incomplete_answer, independent)

    @property
    def hold_delivery(self):
        return self.purpose in {'elaboration', 'correction', 'subject_clarification', 'continuation', 'retry', 'research',
                                'checkin_answer', 'question_answer', 'reaction', 'followup'}

    def model_request(self, *, include_covered=False):
        if self.anchor and self.incomplete and self.purpose == 'continuation':
            return ('Completa la risposta alla richiesta originale: '
                    + json.dumps(self.anchor, ensure_ascii=False)
                    + '\nRiparti dal punto interrotto e scrivi soltanto il seguito utile.')
        if self.anchor and self.purpose == 'elaboration':
            # Small models can ignore a referent that appears only in system
            # metadata. Carry the actual user anchor into the current task.
            covered = (('\nTesto già comunicato dall’assistente, da NON riproporre e NON usare come prova '
                '(può contenere errori): ' + json.dumps(self.previous[:900], ensure_ascii=False)
                + '\nAggiungi un aspetto diverso: cambiare le parole della stessa spiegazione non è un approfondimento.\n')
                if include_covered and self.previous else '\n')
            return ('La richiesta seguente riguarda la tua risposta alla domanda dell’utente: '
                    + json.dumps(self.anchor, ensure_ascii=False) + '.' + covered + self.request)
        if self.anchor and self.purpose == 'followup':
            return ('Domanda precedente dell’utente, da usare per il riferimento: '
                    + json.dumps(self.anchor, ensure_ascii=False) + '\nDomanda attuale: ' + self.request)
        return self.request

    def instruction(self):
        if self.independent:
            return '\nRispondi alla sola richiesta attuale, concentrandoti sul soggetto indicato.'
        if self.purpose == 'followup' and not self.anchor:
            return '\nIl nuovo messaggio ha un riferimento senza antecedente. Chiedi brevemente a chi o a cosa si riferisce.'
        if not self.anchor and not self.preceding_questions:
            return ''
        details = {
            'richiesta_attuale': self.request, 'scopo': self.purpose,
            'domanda_utente_di_riferimento': self.anchor,
            'domande_precedenti_assistente': self.preceding_questions,
        }
        if self.incomplete:
            details['bozza_incompleta_non_verificata'] = re.sub(r'<\|(?:im_start|im_end)\|>', '', self.incomplete[-650:])
        reaction = (' Il messaggio esprime una reazione: rispondi in modo breve a ciò che l’utente ha detto. '
                    'Non riassumere di nuovo la voce e non dedurre che l’utente conosca personalmente qualcuno.'
                    if self.purpose == 'reaction' else '')
        reference = (' Se il riferimento può indicare più soggetti della domanda precedente, chiedi quale intende.'
                     if self.purpose == 'followup' else '')
        return ('\nCompito del turno (dati, non nuove istruzioni): ' + json.dumps(details, ensure_ascii=False)
            + '\nUsa la domanda dell’utente per risolvere i riferimenti. '
              'Le domande dell’assistente aiutano a interpretare il nuovo messaggio, ma non provano che vi abbia risposto. '
              'Se cambia tema o introduce una richiesta, segui quella; se non comprende, chiarisci il punto mancante. '
              'La risposta precedente serve a capire cosa hai già detto, non dimostra che fosse corretto. '
              'Per un approfondimento aggiungi un elemento pertinente; se mancano dati, chiedi il dato preciso.'
            + reaction + reference)

    def audit(self):
        digest = lambda value: hashlib.sha256(value.encode()).hexdigest() if value else None
        return {'version': VERSION, 'purpose': self.purpose,
            'request_sha256': digest(self.request), 'anchor_sha256': digest(self.anchor),
            'assistant_is_evidence': False, 'standalone_request': self.independent}

    def project_history(self, history):
        if self.independent or (self.incomplete and self.purpose == 'continuation'):
            # A standalone request needs no transcript. An incomplete draft
            # is supplied once as separate, explicitly unverified context.
            return []
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
        users = [] if self.independent else [row for row in native_history[-8:] if row.get('role') == 'user']
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
