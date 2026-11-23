"""Bind searches for a public fact to the requested subject and relation."""

from dataclasses import dataclass
from functools import lru_cache
import re

from .web_search import _plain


_QUESTIONS = {
    'it': (
        ('date', r'(?:quando|in che anno) (?:e |fu |venne )?(?P<event>cadut[oa]|crollat[oa]|inaugurat[oa]|apert[oa]|firmat[oa]|fondat[oa]|sottoscritt[oa]|cominciat[oa]|iniziat[oa]) (?P<subject>.+)'),
        ('date', r'(?:quando|in che anno) (?P<event>cadde|crollo|inizio|si tenne|si e tenuto|si svolse) (?P<subject>.+)'),
        ('author', r'chi (?:ha scritto|scrisse) (?P<subject>.+)'),
        ('painter', r'chi (?:ha dipinto|dipinse) (?P<subject>.+)'),
        ('composer', r'chi (?:ha composto|compose) (?P<subject>.+)'),
        ('mouth', r'dove (?:sfocia|sbocca|si getta) (?P<subject>.+)'),
        ('connection', r'quali (?:mari|oceani) collega (?P<subject>.+)'),
        ('countries', r'tra quali (?:paesi|stati) si trova (?P<subject>.+)'),
        ('capital', r'qual e la capitale (?:della |del |di |dell[\'’])(?P<subject>.+)'),
    ),
    'en': (
        ('date', r'when did (?P<subject>.+?) (?P<event>fall|collapse|open|begin|start)'),
        ('date', r'when was (?P<subject>.+?) (?P<event>(?:first )?(?:issued|signed|opened|founded|established|inaugurated))'),
        ('author', r'who (?:wrote|authored) (?P<subject>.+)'),
        ('painter', r'who painted (?P<subject>.+)'),
        ('composer', r'who composed (?P<subject>.+)'),
        ('mouth', r'where does (?P<subject>.+?) (?:flow|empty) into'),
        ('connection', r'which (?:seas|oceans) does (?P<subject>.+?) (?:connect|link)'),
        ('capital', r'what is the capital of (?P<subject>.+)'),
    ),
    'es': (
        ('date', r'cuando (?P<event>cayo|se inauguro|se fundo|se firmo|comenzo|empezo|se proclamo) (?P<subject>.+)'),
        ('author', r'quien escribio (?P<subject>.+)'),
        ('painter', r'quien pinto (?P<subject>.+)'),
        ('composer', r'quien compuso (?P<subject>.+)'),
        ('mouth', r'donde desemboca (?P<subject>.+)'),
        ('city', r'en que ciudad (?:esta|se encuentra) (?P<subject>.+)'),
        ('capital', r'cual es la capital de (?P<subject>.+)'),
    ),
    'fr': (
        ('date', r'quand (?P<subject>.+?) (?:a-t-il|a-t-elle) ete (?P<event>signe[es]?|fonde[es]?|ouvert[es]?|inaugure[es]?)'),
        ('author', r'qui a ecrit (?P<subject>.+)'),
        ('painter', r'qui a peint (?P<subject>.+)'),
        ('composer', r'qui a compose (?P<subject>.+)'),
        ('mouth', r'dans (?:quelle mer|quel ocean|quel fleuve) se jette (?P<subject>.+)'),
        ('capital', r'quelle est la capitale (?:de |du |des |d[\'’])(?P<subject>.+)'),
    ),
    'pt': (
        ('date', r'quando foi (?P<event>proclamad[ao]|inaugurad[ao]|assinad[ao]|fundad[ao]) (?P<subject>.+)'),
        ('author', r'quem escreveu (?P<subject>.+)'),
        ('composer', r'quem compos (?P<subject>.+)'),
        ('continent', r'em que continente (?:fica|esta) (?P<subject>.+)'),
        ('capital', r'qual e a capital (?:de |do |da )(?P<subject>.+)'),
    ),
    'de': (
        ('author', r'wer schrieb (?P<subject>.+)'),
        ('composer', r'wer komponierte (?P<subject>.+)'),
        ('country', r'in welchem land liegt (?P<subject>.+)'),
    ),
}
_FORMS = {language: tuple((kind, re.compile(pattern)) for kind, pattern in forms)
          for language, forms in _QUESTIONS.items()}
_ARTICLES = re.compile(r"^(?:(?:il|lo|la|le|les|der|die|das|el|the|a|o|un|una) |l['’])")
_WORK_TYPE = re.compile(r'^(?:novel|poem|book|play|romanzo|libro|roman|novela|livro|poema) ')
_RIVER_TYPE = re.compile(r'^(?:rio|river|fiume|fleuve) ')
_GENERIC_TYPE = re.compile(r"^(?:stretto di|cordilheira dos|cordilheira de) ")
_LINK_WORDS = frozenset('a an of the de do dos das da di del della des du in en von il lo la le el las los'.split())
_COUNTRY_FORMS = {'italia': ('italiano', 'italiana', 'italian'),
                  'mexico': ('mexicano', 'mexicana', 'mexican')}
_KEYWORD_VARIANTS = {form: country for country, forms in _COUNTRY_FORMS.items() for form in forms}
_DATE = re.compile(r'(?<![\w.,])(?:[1-9][0-9]{2,3})(?!\w|[.,]\d)')
_DATED_TITLE = re.compile(r'\s+\(([12]\d{3})\)$')
_FALSE_FALL = re.compile(r'\b(?:cadut\w* (?:in|da)|fell (?:into|from)|chute de tension|fell short)\b')
_DERIVATIVE = re.compile(
    r'\b(?:adattament\w*|trasposizion\w*|adapt(?:ation|ed|acion|acao)|retelling|sequel|'
    r'fumett\w*|comic(?:s| book)?|ser[ie]+ (?:televisiv\w*|de television)|pelicula|film ?version)\b')
_HYPOTHETICAL = re.compile(r'\b(?:scheduled to|was (?:never|not) |did not |non (?:fu|venne|e stato)|'
                           r'no se |previst[ao] per|projet(?:ee)? pour|should have)\b')
_LOCATION_RELATIONS = {
    'mouth': r'\b(?:(?:se jette|debouche|desemboc\w*|sfocia|sbocca|si getta|empties|flows)\b[^;:.]{0,25}\b'
             r'(?:in|into|en|dans|nel|nello|nella|al|a)|s[\'’]ouvre sur)\b',
    'connection': r'\b(?:connects?|link(?:s|ing)|connecting|collega|collegando|mette in comunicazione|reliant)\b',
    'countries': r'\b(?:al confine|sul confine|confine tra|confina con|diviso tra|suddiviso tra|'
                 r'si trova (?:a cavallo )?(?:tra|fra)|ripartito tra|between|border(?:s|ing))\b',
    'city': r'\b(?:(?:en|in) (?:la ciudad de|the city of)|(?:con sede|ubicad[oa]|situad[oa]|located) (?:en|in))\b',
    'country': r'\b(?:(?:in|im) (?:nord\w*|sud\w*) von|'
               r'(?:liegt|befindet sich) (?:in|im)|in der [^;:. ]{1,30} region)\b',
    'continent': r'\b(?:(?:america do sul|america do norte|america central|africa|asia|europa|oceania)|'
                 r'(?:sul|norte)-american[ao])\b',
}
_AUTHOR_RELATIONS = {
    'author': (r'(?:scriss\w*|ha scritto|wrote|authored|escribio|ecrivit|a ecrit|escreveu|schrieb)',
               r'(?:(?:scritto|scritta) (?:da|di)|written by|escrit[ao] por|ecrit par|escrit[ao] de|'
               r'verfasst von|(?:poema|romanzo|commedia|tragedia)\b[^,;:.]{0,55}\bdi|'
               r'(?:novel|poem|play|book)\b[^,;:.]{0,65}\bby|'
               r'(?:novela|poema|poesia epica|romance|epopeia|poesie|roman)\b[^,;:.]{0,55}\b(?:de|do|d[\'’]|por))'),
    'painter': (r'(?:dipinse|ha dipinto|painted|pinto|a peint|gemalt)',
                r"""(?:dipinto da|painted by|pintad[oa] por|peint par|gemalt von|(?:cuadro|pintura|dipinto|painting)\b[^,;:.]{0,55}\b(?:de|di|by)|(?:huile sur toile|tableau) (?:de |d['’]))"""),
    'composer': (r'(?:compose|composed|compuso|compos|ha composto|komponierte)',
                 r'(?:compost[ao] (?:da|por)|composed by|composee? par|komponiert von|'
                 r'(?:sinfonia|sinfonie|symphony|symphonie|ballet|balletto|musique|partition|oper)\b[^,;:.]{0,70}\b(?:de|di|by|von))'),
}
_DATE_RELATIONS = (
    (r'cad|croll|fall|collapse|cayo', r'cadde|caduta|caduto|croll\w*|abbattut\w*|fell|fall|collapse\w*|chute|cayo|caida|queda'),
    (r'inaugur|apert|open|ouvert', r'inaugur\w*|apert\w*|apri|opened|opening|ouvert\w*|abri\w*'),
    (r'firm|sottoscrit|sign|assin', r'firm\w*|sottoscri\w*|signed|signing|signe\w*|assin\w*'),
    (r'fond|fund|establish', r'fond\w*|fund\w*|found(?:ed|ing)|establish\w*'),
    (r'comenc|comenz|cominc|inizi|begin|start|empez', r'comenz\w*|empez\w*|inizi\w*|cominc\w*|began|begun|beginning|start\w*|debut\w*'),
    (r'proclam', r'proclam\w*|declar\w*'),
    (r'tenne|tenuto|svolse', r'tenn\w*|tenut\w*|svol\w*|celebr\w*'),
    (r'issu', r'issu\w*|grant(?:ed)?|sealed'),
)
_CAPITAL = re.compile(r"\b(?:capital (?:city )?of|capitale (?:di|de|du|del|della)|capital (?:de|do|da))\b")
_PREVIOUS_CAPITAL = re.compile(r'\b(?:former|first|previous|historical|ancienne|ex|antica|prima|'
                               r'was|fro[mn]|until|jusqu|era|antes|fino)\b')
_CAPITAL_PREDICATE = re.compile(r"^(?:'s|’s)? (?:capital(?: city)? (?:is|has been)|"
                               r"est la capitale|ha come capitale|tiene como capital|tem como capital) ")
_CAPITAL_DISCOVERY = {'en': 'capital of', 'it': 'capitale di', 'fr': 'capitale de',
                      'es': 'capital de', 'pt': 'capital de'}
_FACT_REFINEMENTS = {
    'date': {'it': 'data', 'en': 'date', 'es': 'fecha', 'fr': 'date', 'pt': 'data'},
    'author': {'it': 'autore', 'en': 'author', 'es': 'autor', 'fr': 'auteur', 'pt': 'autor', 'de': 'Autor'},
    'painter': {'it': 'dipinto pittore', 'en': 'painting artist', 'es': 'pintura pintor', 'fr': 'tableau peintre'},
    'composer': {'it': 'compositore', 'en': 'composer', 'es': 'compositor', 'fr': 'compositeur',
                 'pt': 'compositor', 'de': 'Komponist'},
    'connection': {'en': 'strait seas', 'it': 'stretto mari'},
    'countries': {'it': 'confine paesi'},
    'mouth': {'it': 'foce', 'en': 'river mouth', 'es': 'desembocadura', 'fr': 'embouchure'},
}
_INTERFERING_SUBJECT = re.compile(r'\b(?:mentre|whereas|while|mientras|tandis que|wahrend)\b')
_EMBEDDED_CLAUSE = re.compile(r'\b(?:dove|where|wo|ou|donde|onde|in cui|during which)\b')
_RIVER_BARRIER = re.compile(r'\b(?:affluents?|afluentes?|affluente|tributar\w*|conflue\w*|rejoint)\b')
_DATE_SUBJECT_LINK = re.compile(r"^\s+(?:(?:of|de|di|del|della|du|des|da|do|von)\s+)?"
                                r"(?:(?:the|il|lo|la|el|le|o|a|der|die|das) |[ld]['’])?$")
_LEADING_DATE = re.compile(r"^[^,;]{0,45}\b[1-9][0-9]{2,3},\s*(?:(?:the|il|lo|la|le|el|o|der|die) |[ld]['’])?$")
_DATE_PREDICATE = re.compile(r'^\s*,?\s*(?:(?:e un evento [^,;]{0,45} avvenuto|'
                             r'fue [^,;]{0,45}|ocurrio|avvenne|took place) )?'
                             r'(?:il|nel|en|em|el|le|in|on|am)\s+[^,;]{0,30}\b[1-9][0-9]{2,3}\b')
_DATE_CLAUSE_BREAK = re.compile(r'[;:]|,?\s+\b(?:che fu|cuando|which was|after|'
                                r'despite|quando|whose|although|mientras|avant que|'
                                r'y (?:concluyo|termino)|and (?:ended|concluded))\b')
_RELATIVE_CREATOR = re.compile(r'\b(?:who|quien|que|chi|che|qui|der|die)\s*$')
_WATER_BODY = re.compile(r"\b(?:sea|ocean|oceano|mar|mare|golfo|gulf|mer)\b")
_NAME_AFTER = r"[A-ZÀ-ÖØ-Þ][^\W\d_]+(?:[’'\-][^\W\d_]+)*"
_CREATOR_DESCRIPTOR = re.compile(
    r'^(?:(?:el|la|o|a|um|una) )?(?:espanol[ae]?|escritor[a]?|poeta|pintor[a]?|compositor[a]?)'
    r'(?: (?:portugues[a]?|espanol[ae]?|italian[oa]|frances[a]?))? ', re.I)


def _keywords(text):
    return tuple(_KEYWORD_VARIANTS.get(word, word) for word in re.findall(r'[^\W_]+', _plain(text))
                 if word not in _LINK_WORDS)


@lru_cache(maxsize=128)
def _topic_pattern(words):
    linker = r"[^\w]+(?:(?:" + '|'.join(sorted(_LINK_WORDS)) + r")[^\w]+)*"
    variants = (r'(?:' + '|'.join(map(re.escape, (word, *_COUNTRY_FORMS[word]))) + ')'
                if word in _COUNTRY_FORMS else re.escape(word) for word in words)
    return re.compile(r'(?<!\w)' + linker.join(variants) + r'(?!\w)')


def _beginning(text, match):
    before = text[:match.start()].strip(' ,')
    return not before or bool(re.fullmatch(r"(?:the|il|lo|le|les|la|el|o|a|der|die|das|l['’])", before))


def _topic_span(text, subject):
    return _topic_pattern(subject).search(text)


def _remove_parentheses(value):
    return re.sub(r'\([^()]{1,125}\)', '', value)


@dataclass(frozen=True)
class PublicFactQuery:
    kind: str
    topic: str
    language: str
    event: str = ''

    @property
    def words(self):
        return _keywords(self.topic)

    def discovery_queries(self):
        prefix = _CAPITAL_DISCOVERY.get(self.language) if self.kind == 'capital' else None
        if prefix:
            return f'{prefix} {self.topic}', self.topic
        detail = _FACT_REFINEMENTS.get(self.kind, {}).get(self.language)
        return (self.topic, f'{self.topic} {detail}') if detail else (self.topic,)

    def accepts_document_title(self, title):
        year = _DATED_TITLE.search(title) if self.kind == 'date' else None
        return year is None or year[1] in _DATE.findall(self.topic)

    def supports(self, sentence, *, article_title='', opening=False):
        """Accept only a statement with the requested relation on the subject."""
        text = _plain(sentence)
        subject = _topic_span(text, self.words)
        article_matches = opening and bool(article_title and _keywords(article_title) == self.words)
        if not self.accepts_document_title(article_title) or not (subject or article_matches):
            return False
        if _HYPOTHETICAL.search(text):
            return False
        if self.kind == 'date':
            return self._supports_date(text, subject, article_matches)
        if self.kind in _AUTHOR_RELATIONS:
            return self._supports_creator(sentence, text, subject)
        if self.kind == 'capital':
            return self._supports_capital(text, subject)
        if not subject:
            return False
        return self._supports_place(text, subject)

    def supports_place_continuation(self, lead, sentence, article_title):
        """Link adjacent geographic statements using an explicit subject or alias."""
        text, next_text = _plain(lead), _plain(sentence)
        subject = _topic_span(text, self.words)
        if not subject:
            return False
        if self.kind == 'countries':
            if text.startswith(('se ', 'if ')) and ',' in text:
                text = text.split(',', 1)[1].lstrip()
                subject = _topic_span(text, self.words)
            continuation = re.match(r'^(?:si trova (?:a cavallo )?(?:tra|fra)|it (?:lies|is) between)\b', next_text)
            return bool(_keywords(article_title) == self.words and subject and _beginning(text, subject) and continuation
                        and re.search(r'\b(?:stati|paesi|nazioni|confine|countries|border)\b', next_text)
                        and self.supports(f'{self.topic} {sentence}'))
        if self.kind == 'city':
            return bool(_keywords(article_title) == self.words and _beginning(text, subject)
                        and re.match(r'^Con sede en ' + _NAME_AFTER, sentence)
                        and self.supports(f'{self.topic} {sentence}'))
        canonical = _keywords(article_title)
        if self.kind != 'connection' or not canonical:
            return False
        alias = _topic_span(text, canonical)
        next_subject = _topic_span(next_text, canonical)
        return bool(alias and next_subject and _beginning(text, alias) and _beginning(next_text, next_subject)
                    and re.fullmatch(r' (?:or|also called|also known as|ou|oppure) (?:(?:the|le|il) )?',
                                     text[alias.end():subject.start()])
                    and self._supports_place(next_text, next_subject))

    def _supports_date(self, text, subject, article_matches):
        if not subject or _FALSE_FALL.search(text) or _DERIVATIVE.search(text) or _INTERFERING_SUBJECT.search(text):
            return False
        relations = next((terms for hint, terms in _DATE_RELATIONS if re.search(hint, self.event)), '')
        if not relations:
            return False
        for event in re.finditer(r'\b(?:' + relations + r')\b', text):
            if not self._date_subject_matches(text, subject, event):
                continue
            if self.event.startswith('first ') and not (
                    re.search(r'\bfirst\s*$', text[max(0, event.start() - 16):event.start()])
                    or (article_matches and _beginning(text, subject))):
                continue
            tail = _DATE_CLAUSE_BREAK.split(text[event.end():event.end() + 150], maxsplit=1)[0]
            lead = text[:subject.start()] if _LEADING_DATE.fullmatch(text[:subject.start()]) else ''
            clause = lead + tail
            if len(set(_DATE.findall(clause))) == 1:
                return True
        return False

    @staticmethod
    def _date_subject_matches(text, subject, event):
        if event.end() <= subject.start():
            between = _remove_parentheses(text[event.end():subject.start()])
            after = re.sub(r'^\s*\([^()]{1,125}\)', '', text[subject.end():])
            return bool(_DATE_SUBJECT_LINK.fullmatch(between) and _DATE_PREDICATE.match(after))
        between = text[subject.end():event.start()]
        if not (_beginning(text, subject) or _LEADING_DATE.fullmatch(text[:subject.start()])):
            return not between.strip() and bool(_DATE_PREDICATE.match(text[event.end():]))
        between = _remove_parentheses(between).lstrip()
        between = re.sub(r'^, (?:sometimes spelled|also written|also known as) [^,]{1,65},', '', between)
        return (len(between) <= 95 and not _EMBEDDED_CLAUSE.search(between)
                and not re.search(r'[;:]|,\s*[^,]+,\s*\S', between))

    @staticmethod
    def _supports_capital(text, subject):
        if not subject:
            return False
        if _beginning(text, subject) and _CAPITAL_PREDICATE.match(text[subject.end():]):
            return True
        match = _CAPITAL.search(text)
        return bool(match and 0 <= subject.start() - match.end() <= 8
                    and not _PREVIOUS_CAPITAL.search(text))

    def _supports_creator(self, original, text, subject):
        if not subject or _DERIVATIVE.search(text) or re.search(r'\b(?:non|no|never|nunca|jamais|nicht)\b', text):
            return False
        active, passive = _AUTHOR_RELATIONS[self.kind]
        before, after = text[:subject.start()], text[subject.end():]
        action = re.search(r'\b' + active + r"\b(?: (?:il|la|el|su|the|obra|cuadro|romanzo|novel|poema|opera|sua|his|her))*[ '\"«“’]*$", before)
        if action:
            actor = before[:action.start()].rstrip()
            return bool(actor and not _RELATIVE_CREATOR.search(actor) and not _INTERFERING_SUBJECT.search(actor)
                        and re.search(_NAME_AFTER, original[:action.start()]))
        # A first occurrence in a related title or comparative clause cannot
        # lend the queried work's author relation to another work.
        if not _beginning(text, subject) and not re.search(
                r'\b(?:come|titulat\w*|called|titled|denominad\w*)\s*$', before):
            return False
        if self.kind == 'composer' and self.language == 'fr':
            credit = re.match(r" de " + _NAME_AFTER + r"(?: " + _NAME_AFTER + r"){1,4}"
                              r"(?= est (?:un|une) (?:musique|ballet|partition|symphonie|opera)\b)",
                              original[subject.end():])
            if credit and re.search(r'\bcomposee?\s+en\s+\d{4}\b', after):
                return True
        match = re.search(r'\b' + passive + r"(?=[\s’']|(?<=[’']))[ ’']*", after[:155])
        return bool(match and re.match(_NAME_AFTER, _CREATOR_DESCRIPTOR.sub(
            '', original[subject.end() + match.end():])))

    def _supports_place(self, text, subject):
        after = text[subject.end():]
        # Strip a parenthetical alias so kinship and translation notes do not
        # hide the verb of the main clause.
        after = re.sub(r'^\s*\([^()]{1,130}\)', '', after, count=1)
        if self.kind == 'mouth':
            after = re.sub(r'—[^—]{1,170}—', '', after)
        after = re.split(r'[;:]|\b(?:mentre|mientras|while|tandis que)\b', after, maxsplit=1)[0]
        match = re.search(_LOCATION_RELATIONS[self.kind], after[:300 if self.kind == 'mouth' else 205])
        if not match:
            return False
        before = after[:match.start()]
        if self.kind == 'mouth':
            destination = _topic_span(after[match.end():match.end() + 32], self.words)
            scoped_subject = _beginning(text, subject) or (
                match[0] == "s'ouvre sur" and text[:subject.start()] == 'le delta du ')
            return bool(scoped_subject and not _RIVER_BARRIER.search(before)
                        and not _EMBEDDED_CLAUSE.search(before)
                        and (destination is None or destination.start() > 8)
                        and (len(before) <= 90 and before.count(',') <= 1
                             or re.match(r'^\s*es (?:uno de los|un) rios?\b', before)))
        if self.kind in ('connection', 'countries'):
            answers = after[match.end():]
            conjunction = re.search(r"\b(?:e|ed|and|et|y|und|a|to)\b", answers)
            return bool(conjunction and not _DERIVATIVE.search(before) and (
                self.kind == 'countries' or (_WATER_BODY.search(answers[:conjunction.start()])
                                             and _WATER_BODY.search(answers[conjunction.end():]))))
        return not _INTERFERING_SUBJECT.search(before)


def fact_question(query, language=None):
    if not isinstance(query, str) or len(query) > 160:
        return None
    text = _plain(query).replace('’', "'").strip(' ¿¡?!.')
    for code in _FORMS if language is None else (language,):
        for kind, form in _FORMS.get(code, ()):
            match = form.fullmatch(text)
            if match is None:
                continue
            topic = _ARTICLES.sub('', match['subject'])
            if kind in _AUTHOR_RELATIONS:
                topic = _ARTICLES.sub('', _WORK_TYPE.sub('', topic))
            if kind == 'mouth':
                topic = _RIVER_TYPE.sub('', topic)
            if kind == 'continent':
                topic = _GENERIC_TYPE.sub('', topic)
            if not _keywords(topic) or not re.fullmatch(r"[\w]+(?:[ '\-][\w]+)*", topic):
                return None
            return PublicFactQuery(kind, topic, code, match.groupdict().get('event') or '')
    return None
