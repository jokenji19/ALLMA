"""Resolve focused public questions without using generated prose as evidence."""

from dataclasses import dataclass
import re
import unicodedata

from .lifespan import lifespan_evidence, lifespan_question


_ARTICLE = re.compile(r"^(?:il |lo |la |i |gli |le |un |una |uno |the |l['’])", re.I)
_WORDS = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*")
_FOCUS = re.compile(r"^(?:e|allora|quindi|and|so)[, ]+", re.I)
_SUFFIX = re.compile(
    r"\s*[.!?,;]?\s*(?:(?:non cercare|non usare) (?:su )?(?:internet|online|il web)|"
    r"offline|senza (?:internet|cercare online)|rispondi in (?:una|due|tre|quattro|cinque|[1-5]) frasi?)\s*[.!?]*$",
    re.I,
)
_OUTBREAK_QUESTION = re.compile(
    r"^(?:contro chi (?:ha fatto scoppiare|(?:è|e) scoppiat[ao]|fu scatenat[ao])\s+|"
    r"chi (?:venne invas[oa]|fu invas[oa]) "
    r"(?:all['’]inizio (?:dell['’]|d(?:el|ella)\s+)|quando (?:è|e) scoppiat[ao]\s+))(?P<topic>.+)$",
    re.I,
)
_INVASION = re.compile(
    r"\b(?:(?:invasione|attacco|invasion|attack)\s+(?:[^\W\d_]+\s+)?"
    r"(?:(?:della|del|di|alla|al|a|against|of)\s+|dell['’])[^\W\d_][\w'’-]*|"
    r"(?:invase|invadere|attacc[oò]|attaccare|invaded|attacked)"
    r"\s+(?:(?:il|lo|la|i|gli|le|the)\s+|l['’])?[^\W\d_][\w'’-]*)",
    re.I,
)
_OUTBREAK = re.compile(
    r"\b(?:scoppi\w*|cominci\w*|cominci[òo]|inizi\w*|inizio|avvio|avvi\w*|"
    r"began|beginning|outbreak|start\w*|trigger\w*)\b",
    re.I,
)
_CAUSE = re.compile(
    r"\b(?:provoc\w*|caus\w*|scaten\w*|determin\w*|innesc\w*|"
    r"segn\w*|dando\s+(?:inizio|avvio)|port\w*\s+(?:allo|all['’])|"
    r"trigger\w*|mark\w*|lead(?:ing)?\s+to|led\s+to)\b",
    re.I,
)
_BEGIN_WITH = re.compile(r"\b(?:con|with)\s+(?:l['’]|the |un['’]|un |una )?$|\b(?:quando|when)\b[^,.!?;]{0,75}$", re.I)
_DATE = re.compile(r"(?<!\w)(?:[12]\d{3}|(?:[IVXLCDM]{1,8}|\d{1,2})\s+(?:secolo|century))(?!\w)", re.I)
_NEGATED = re.compile(r"\b(?:non|nessun[ao]?|senza|not|never|without)\b|n['’]t\b", re.I)
_IMPLICIT_RIVER_ROUTE = re.compile(
    r"^(?:ha origine|nasce|scorre|attraversa)\b[\s\S]{1,600},\s*prima di (?:sfociare|sboccare)\s+"
    r"(?:in|nel|nello|nella|nelle|nei|nell['’])\s*[^\W\d_]+[^,;]*\.$", re.I)
_IMPLICIT_CONFLICT_START = re.compile(
    r"^(?:il conflitto|la guerra) (?:ebbe inizio|inizi[oò]|cominci[oò]|scoppi[oò])\b"
    r"[^.!?;]{0,90}?\bcon\s+l['’](?:attacco|invasione)\s+(?:della|del|dell['’])\s*"
    r"[^,.!?;]{2,85}?\s+(?:alla|al|alle|contro)\s+[^,.!?;]{2,85}(?:[,.;]|$)", re.I)

# Each rule pairs a bounded question shape with the source relation it needs.
# A named public subject can be supplied by that question or a cited answer.
_FACTS = (
    (
        'mouth',
        re.compile(r"^dove (?:sfocia(?:no)?|sbocca(?:no)?)(?: (?P<topic>.+))?$", re.I),
        re.compile(r"\b(?:sfoci\w*|sbocc\w*|si gett\w*|si immett\w*|sfoc[ia]+)"
                   r"\s+(?:in|nel|nello|nella|nelle|nei|nel[l]?['’])\s*[^\W\d_]+", re.I),
    ),
    (
        'location',
        re.compile(r"^dove (?:si trova(?:no)?|è situat[oa]|sono situat[ie])(?: (?P<topic>.+))?$", re.I),
        re.compile(r"\b(?:si (?:trova(?:no)?|estend\w*)|è situat[oa]|sono situat[ie]|è ubicat[oa]|"
                   r"è localizzat[oa]|è collocat[oa]|sorge|located)\b"
                   r"\s+(?:a|in|nel|allo|alla|nella|presso|vicino|sotto|sopra|tra|fra|at|on|under|"
                   r"nell['’])\s*[^\W\d_]+", re.I),
    ),
    (
        'birth',
        re.compile(r"^(?:e )?(?P<question>quando|dove|in che anno) (?:è nat[ao]|nacque)(?: (?P<topic>.+))?$", re.I),
        re.compile(r"\b(?:nacque|nat[ao]|diede i natali|born)\b", re.I),
    ),
    (
        'death',
        re.compile(r"^(?P<question>quando|dove|in che anno) (?:è mort[ao]|morì)(?: (?P<topic>.+))?$", re.I),
        re.compile(r"\b(?:morì|mort[ao]|decedut[ao]|scomparv\w*|died)\b", re.I),
    ),
    (
        'award',
        re.compile(
            r"^(?P<question>quando|in che anno) (?:(?:ha (?:vinto|ricevuto|ottenuto)|vinse|ricevette|ottenne)"
            r" (?P<facet>(?:il |la |un |una )?(?:premio|medaglia|riconoscimento) [\wÀ-ž '’-]{2,54})"
            r"|(?P<topic>.+?) (?:ha (?:vinto|ricevuto|ottenuto)|vinse|ricevette|ottenne)"
            r" (?P<named_facet>(?:il |la |un |una )?(?:premio|medaglia|riconoscimento) [\wÀ-ž '’-]{2,54}))$",
            re.I,
        ),
        re.compile(r"\b(?:vins\w*|vint\w*|ricev\w*|otten\w*|conquist\w*|"
                   r"aggiudic\w*|insignit\w*|assegn\w*|awarded|received|won)\b", re.I),
    ),
    (
        'start',
        re.compile(r"^(?P<question>quando|in che anno) (?:è iniziat[oa]|cominciò|iniziò|scoppiò|"
                   r"è cominciat[oa]|è scoppiat[oa])(?: (?P<topic>.+))?$", re.I),
        _OUTBREAK,
    ),
    (
        'written_work',
        re.compile(r"^(?P<facet>che (?:romanzo|libro|racconto|poesia)|qual[ei] (?:romanz[oi]|libr[oi]|"
                   r"raccont[oi]|poesi[ae])) (?:ha scritto|scrisse)(?: (?P<topic>.+))?$", re.I),
        re.compile(r"\b(?:scrisse|ha scritto|compose|ha composto|pubblicò|ha pubblicato|wrote|"
                   r"published)\b", re.I),
    ),
    (
        'consumption',
        re.compile(r"^(?:che cosa|cosa) (?:assorbe|assorbono)(?: (?:le piante|gli organismi))?"
                   r" durante (?P<topic>.+)$", re.I),
        re.compile(r"\b(?:(?:assorb[eo]\w*|assorbono|assorbire|assorbiment\w*|absorbs?|absorption)\s+\w+|"
                   r"(?:producono|sintetizzano|fabbricano)\b[^,;.!?]{1,125}\ba partire da\s+\w+)", re.I),
    ),
)
_LOCATION_COMPLEMENT = re.compile(
    r"\b(?:a|in|nel|nella|vicino a|presso|at)\s+[A-ZÀ-ÖØ-Þ][^\W\d_]+"
)
_SUBJECT_BRIDGE = {'nel', 'fu', 'e', 'era', 'venne', 'ha', 'aveva', 'si', 'poi', 'infine', 'anche', 'il', 'allora'}
_DEPENDENT_SUBJECT = re.compile(r"^(?:(?:quel|quell[oa]|quest[oa])\b|quell['’]|quest['’])\s*(.*)$", re.I)
_FACET_STOP = {'che', 'quale', 'quali', 'di', 'del', 'della', 'in', 'the', 'of'}
_WWII_ALLIANCE = re.compile(
    r'^(?:con chi (?:si era alleat[oa]|si alle[oò]|era alleat[oa]|si è alleat[oa])|quali erano i suoi alleati)'
    r' (?:durante|nella|nella fase iniziale della) (?:la )?(?:seconda|II) guerra mondiale$', re.I)
_TRIPARTITE = re.compile(r'\b(?:accordo|alleanza)\b(?=[^.!?]{0,290}\bitalia\b)'
                         r'(?=[^.!?]{0,290}\bgermania\b)(?=[^.!?]{0,290}\bgiappon\w*\b)', re.I)
_DEPARTURE_QUESTIONS = (
    (r'(?P<question>quando|perch[eé]) (?:ha lasciato|lasciò) (?:il |lo |la |l[’\'])?(?P<target>.+)',
     r'(?:ha lasciato|lasciò)\s+(?:il |lo |la |l[’\'])?', r'(?:perch[eé]|a causa di)',
     'A quale addio di {person} ti riferisci? Per cercare il passaggio su {target}, mi aiuta sapere l’anno o il ruolo.'),
    (r'(?P<question>when|why) did (?:he|she|they) leave (?:the )?(?P<target>.+)',
     r'left\s+(?:the )?', r'(?:because|due to)',
     'Which year or role at {target} do you mean? That helps me identify the departure you’re asking about.'),
    (r'¿?(?P<question>cu[aá]ndo|por qu[eé]) (?:dej[oó]|se fue de) (?:el |la )?(?P<target>.+)',
     r'(?:dej[oó]|se fue de)\s+(?:el |la )?', r'(?:porque|debido a|a causa de)',
     '¿A qué año o etapa de {person} en {target} te refieres?'),
    (r'(?P<question>quand|pourquoi) (?:a-t-il|a-t-elle) quitt[eé] (?:le |la |l[’\'])?(?P<target>.+)',
     r'a quitt[eé]\s+(?:le |la |l[’\'])?', r'(?:parce que|en raison de|à cause de)',
     'Tu parles de quelle année ou de quel rôle de {person} au sein de {target} ?'),
)
_DEPARTURE_FORMS = tuple((re.compile(form, re.I), verb, cause, clarification)
                         for form, verb, cause, clarification in _DEPARTURE_QUESTIONS)
_DAY_MONTH = re.compile(
    r'(?<!\d)(?:[1-9]|[12]\d|3[01])(?:er|st|nd|rd|th)? (?:de )?(?:'
    r'gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre|'
    r'january|february|march|april|may|june|july|august|september|october|november|december|'
    r'enero|febrero|abril|mayo|junio|julio|septiembre|octubre|noviembre|diciembre|'
    r'janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\b', re.I)
_RETIREMENT = re.compile(r"\b(?:annuncia (?:il (?:proprio )?)?ritiro dall['’]attività agonistica|"
                         r"announced (?:his|her) retirement from football|"
                         r"anunci[oó] su retiro (?:oficial )?del f[uú]tbol profesional|"
                         r"annonce sa retraite (?:du football|sportive))\b", re.I)
_CONTRACT_DATE = re.compile(
    r'\b(?:contratt\w*|contract\w*|contrat\w*)\b[^.!?]{1,170}\b(?:fino al|until|hasta el|jusqu[’\']au)\b'
    r'[^.!?]{1,60}\b[12]\d{3}\b', re.I)


def _plain(text):
    return ''.join(ch.casefold() for ch in unicodedata.normalize('NFKD', text)
                   if not unicodedata.combining(ch))


def _subject_in(subject, text):
    query = r"[\s'’\-]+".join(re.escape(word) for word in re.findall(r"[^\W_]+", subject))
    return re.search(r"(?<!\w)" + query + r"(?!\w)", text, re.I)


def _question_shape(message):
    if not isinstance(message, str) or not 0 < len(message) <= 250:
        return ''
    normalized = unicodedata.normalize('NFKC', message)
    if len(normalized) > 250 or any(unicodedata.category(char).startswith('C') for char in normalized):
        return ''
    text = _SUFFIX.sub('', normalized.strip()).strip(' ?!.')
    return _FOCUS.sub('', text)


def _source_title(history):
    if not history or history[-1].role != 'assistant':
        return None
    meta = getattr(history[-1], 'metadata', {}) or {}
    review = meta.get('reference_review')
    if (meta.get('is_valid') is not True or meta.get('source') not in {'reference_excerpt', 'saved_reference_recall'}
            or not isinstance(review, dict) or review.get('basis') != 'reference_text'
            or review.get('truth_verified') is not False):
        return None
    from .saved_references import saved_topic

    return saved_topic('reference_excerpt', review)


def _departure_citation(history):
    from .public_references import research_followup, research_subject

    for index in range(len(history) - 1, max(-1, len(history) - 9), -1):
        row = history[index]
        if row.role == 'assistant':
            if _source_title(history[:index + 1]):
                citation = row.metadata['reference_review']['citation']
                return citation if citation.get('provider') == 'wikipedia' else None
            continue
        if research_followup(row.content):
            continue
        question = research_subject(row.content, ()) or row.content
        if not any(pattern.fullmatch(_question_shape(question)) for pattern, *_ in _DEPARTURE_FORMS):
            break
    return None


def lifespan_history(history):
    """Follow an age question back across earlier attempts on the same topic."""
    from .public_references import research_followup, research_subject

    for index in range(len(history) - 1, max(-1, len(history) - 9), -1):
        row = history[index]
        if row.role == 'assistant':
            if _source_title(history[:index + 1]):
                return history[:index + 1]
            continue
        if research_followup(row.content):
            continue
        question = research_subject(row.content, ()) or row.content
        question = lifespan_question(_question_shape(question))
        if question is None or question[1]:
            break
    return ()


def contextual_identity_question(message, history):
    """Use a cited subject to disambiguate a new proper name in the same domain."""
    if (re.fullmatch(r'chi (?:era|fu|è) ettore', _question_shape(message), re.I)
            and (_source_title(history) or '').casefold() in {'achille', 'iliade', 'guerra di troia'}):
        return "Chi era Ettore nell'Iliade?"
    return None


def _question_for(topic):
    from .public_references import public_topic

    topic = _ARTICLE.sub('', unicodedata.normalize('NFC', topic.strip()))
    words = topic.split()
    if (not 1 <= len(words) <= 10 or any(not _WORDS.fullmatch(word) for word in words)
            or _DEPENDENT_SUBJECT.match(topic)):
        return None
    question = f'Che cos’è {topic}?'
    return (question, topic) if public_topic(question) else None


def _conflict_outbreak(clause, subject, action):
    # The passage may name the attack first or describe what started the
    # conflict first. An attack elsewhere in the same sentence is insufficient.
    if action.end() < subject.start():
        between = _plain(clause[action.end():subject.start()])
        return bool(_OUTBREAK.search(between) and _CAUSE.search(between))
    between = _plain(clause[subject.end():action.start()])
    if _OUTBREAK.search(between):
        return bool(_BEGIN_WITH.search(between))
    prefix = _plain(clause[max(0, subject.start()-24):subject.start()])
    return bool(_OUTBREAK.search(prefix) and _CAUSE.search(between))


@dataclass(frozen=True)
class ContextualReferenceRequest:
    candidate_question: str
    topic: str
    relation: re.Pattern | None
    kind: str
    facet: tuple = ()
    answer_type: str = ''
    anchor_title: str | None = None
    focus_evidence: bool = True
    clarification: str = ''
    article_citation: dict | None = None
    departure_target: str = ''
    language: str = ''

    @property
    def evidence_terms(self):
        # Hint for the extract selector. The passage check remains authoritative.
        return tuple((word,) for word in self.facet)

    def matches_passage(self, text):
        if self.kind == 'lifespan':
            return bool(self.topic and lifespan_evidence(self.topic, text))
        if not isinstance(text, str) or not text.strip() or len(text) > 900:
            return False
        matches = 0
        for clause in re.split(r"[;\n]|(?<=[.!?])\s+", text):
            clause = unicodedata.normalize('NFC', clause)
            subject = _subject_in(self.topic, clause)
            if subject is None or _NEGATED.search(clause):
                continue
            if self.kind == 'conflict_target':
                matches += sum(_conflict_outbreak(clause, subject, action)
                               for action in self.relation.finditer(clause))
                continue
            match = self.relation.search(clause)
            if not match:
                continue
            if self.kind in {'mouth', 'location', 'written_work', 'award', 'birth', 'death', 'departure'}:
                bridge = re.findall(r"\w+", _plain(clause[subject.end():match.start()]))
                if subject.end() > match.start() or any(
                        word not in _SUBJECT_BRIDGE and not _DATE.fullmatch(word) for word in bridge):
                    continue
            # Fact and date/place must occur near the same relation in a
            # standalone statement. Do not reuse broad article prose.
            nearby = clause[max(0, match.start() - 90):match.end() + 100]
            words = set(re.findall(r"[^\W\d_]+", _plain(nearby)))
            if any(word not in words for word in self.facet):
                continue
            if (self.answer_type == 'date' and not _DATE.search(nearby)
                    and not (self.departure_target and _DAY_MONTH.search(nearby))):
                continue
            if self.answer_type == 'place' and not _LOCATION_COMPLEMENT.search(nearby):
                continue
            matches += 1
        return matches == 1

    def matches_continuation(self, text, introducing_sentences):
        if not introducing_sentences:
            return False
        if self.kind == 'conflict_target':
            prior = introducing_sentences[-1]
            return bool(_subject_in(self.topic, prior) and not _NEGATED.search(prior)
                        and _IMPLICIT_CONFLICT_START.match(text) and not _NEGATED.search(text))
        if self.kind != 'mouth' or not self.anchor_title:
            return False
        first, *rest = introducing_sentences
        return bool(_subject_in(self.topic, first) and re.search(r'\b(?:è un fiume|is a river)\b', first, re.I)
                    and all(re.match(r'^la sua (?:lunghezza|portata)\b', sentence, re.I) for sentence in rest)
                    and not re.search(r'\b(?:affluente|tributario|non prima|prima di non)\b', text, re.I)
                    and _IMPLICIT_RIVER_ROUTE.fullmatch(text))

    def matches_at(self, sentences, index, *, full_article=False):
        return self.matches_passage(sentences[index]) or self.matches_continuation(
            sentences[index], sentences[max(0, index - 2):index]) or bool(
                full_article and self._retirement_event(sentences[index]))

    def _retirement_event(self, sentence):
        # The revision is pinned to the person already cited. This states the
        # documented retirement event without inferring a personal motive.
        return (self.departure_target and _RETIREMENT.search(sentence)
                and _DAY_MONTH.search(sentence) and _subject_in(self.departure_target, sentence)
                and not _NEGATED.search(sentence))

    def article_passage(self, paragraph):
        from .contribution_review import statements

        sentences = statements(paragraph, limit=40)
        for index, sentence in enumerate(sentences):
            if self.matches_at(sentences, index, full_article=True):
                if self.answer_type == 'date' and self.departure_target and not _DATE.search(sentence):
                    # Include the actual season context when the event gives only
                    # day and month. Do not manufacture a full date.
                    context = next((previous for previous in reversed(sentences[:index])
                                    if len(previous) <= 300 and self.date_context(previous)), None)
                    if context:
                        return context + '\n' + sentence
                return sentence
        return None

    def date_context(self, text):
        return (self.departure_target and _CONTRACT_DATE.search(text)
                and _subject_in(self.departure_target, text) and not _NEGATED.search(text))

    def matches_document(self, text, *, full_article=False):
        from .contribution_review import statements

        sentences = statements(text, limit=48)
        return any(self.matches_at(sentences, index, full_article=full_article) for index in range(len(sentences)))


def contextual_reference_request(message, history=(), *, attempt_history=None):
    """Provide a public title and an extract criterion for a focused question."""
    from .public_references import explicit_research, public_query_text

    text = _question_shape(message)
    if not text:
        return None
    frame, separator, rest = text.partition(':')
    if separator and public_query_text(frame) and explicit_research(frame):
        text = rest.strip()
    if (lifespan := lifespan_question(text)) and public_query_text(text):
        language, person = lifespan
        previous = lifespan_history(attempt_history if attempt_history is not None else history)
        anchor = _source_title(previous)
        if person:
            title = _question_for(person)
            if not title:
                return None
        elif anchor:
            title = _question_for(anchor)
        else:
            title = None
        return ContextualReferenceRequest(*(title or ('', '')), None, 'lifespan',
            anchor_title=anchor, language=language)
    for form, verb, cause, clarification in _DEPARTURE_FORMS:
        match = form.fullmatch(text)
        if not match:
            continue
        citation = _departure_citation(attempt_history if attempt_history is not None else history)
        target = match['target']
        if not citation or not public_query_text(text) or not re.fullmatch(
                r"[^\W\d_]+(?:[ '’.-][^\W\d_]+){0,6}", target):
            return None
        anchor = citation['title']
        title = _question_for(anchor)
        if not title:
            return None
        when = _plain(match['question']) in ('quando', 'when', 'cuando', 'quand')
        relation = re.compile(r'\b' + verb + re.escape(target) + r'\b'
                              + ('' if when else r'[,]?\s+' + cause + r'\b'), re.I)
        return ContextualReferenceRequest(*title, relation, 'departure', anchor_title=anchor,
            answer_type='date' if when else 'reason', clarification=clarification.format(person=anchor, target=target),
            article_citation=citation, departure_target=target)
    if _WWII_ALLIANCE.fullmatch(text):
        # Bind the pronoun only to a sourced referent. The treaty documents
        # Italy's alliance with Germany and Japan in one attributable passage.
        if (_source_title(history) or '').casefold() == 'benito mussolini':
            return ContextualReferenceRequest('Che cos’è il Patto tripartito?', 'Patto tripartito',
                _TRIPARTITE, 'alliance')
        return None
    conflict = _OUTBREAK_QUESTION.fullmatch(text)
    if conflict:
        title = _question_for(conflict['topic'])
        if title and public_query_text(text):
            return ContextualReferenceRequest(*title, _INVASION, 'conflict_target')
        return None
    for kind, pattern, relation in _FACTS:
        match = pattern.fullmatch(text)
        if not match:
            continue
        fields = match.groupdict()
        value = fields.get('topic') or ''
        dependent = _DEPENDENT_SUBJECT.fullmatch(value)
        # Only allow a demonstrative to bind to an actual noun in the already
        # confirmed title. Do not carry unresolved/private phrases to the web.
        remainder = (dependent[1] if dependent else '').strip()
        anchor = _source_title(history) if not value or dependent else None
        # General named locations retain the standard encyclopedia route. Here
        # a location question needs a public referent supplied by the exchange.
        if kind == 'location' and anchor is None:
            return None
        if dependent and (not anchor or (remainder and not _WORDS.fullmatch(remainder))
                          or (remainder and not _subject_in(_plain(remainder), _plain(anchor)))):
            return None
        if not public_query_text(text if not dependent else text[:match.start('topic')] + remainder):
            return None
        title = _question_for(anchor or value)
        if not title:
            return None
        raw_facet = fields.get('named_facet') or fields.get('facet') or ''
        facet = tuple(word for word in re.findall(r"[^\W\d_]+", _plain(_ARTICLE.sub('', raw_facet)))
                      if word not in _FACET_STOP)
        answer_type = ('place' if (fields.get('question') or '').casefold() == 'dove' else
                       'date' if fields.get('question') else '')
        return ContextualReferenceRequest(*title, relation, kind, facet, answer_type, anchor)
    return None
