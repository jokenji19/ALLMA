"""Compute completed years from a single attributed biographical passage."""

from dataclasses import dataclass
import re
import unicodedata


_QUESTION_FORMS = {
    'it': (
        r'quanti anni aveva (?:quando|quandp) (?:mori|e mort[oa])(?: (?P<person>.+))?',
        r'quanti anni aveva (?:(?P<person>.+?) )?alla sua morte',
        r'quanti anni (?:ha vissuto|visse)(?: (?P<person>.+))?',
        r'quanti anni aveva (?:(?P<person>.+?) )?(?:quando|quandp) (?:mori|e mort[oa])',
        r'(?P<person>.+?) quanti anni (?:ha vissuto|visse|aveva (?:quando|quandp) (?:mori|e mort[oa]))',
        r'a che eta (?:mori|e mort[oa])(?: (?P<person>.+))?',
    ),
    'en': (
        r'how old was (?P<person>.+?) when (?:he|she|they) died',
        r'how long did (?P<person>.+?) live',
        r'how old was (?P<person>.+?) at (?:his|her|their) death',
    ),
    'es': (
        r'cuantos anos (?:vivio|tenia (?:cuando|al) (?:murio|morir))(?: (?P<person>.+))?',
        r'a que edad murio(?: (?P<person>.+))?',
    ),
}
_FORMS = {language: tuple(re.compile('^' + form + '$') for form in forms)
          for language, forms in _QUESTION_FORMS.items()}
_PRONOUNS = {'he', 'she', 'they', 'lui', 'lei', 'ella', 'el'}
_MONTHS = {
    word: index
    for index, group in enumerate((
        'gennaio january enero', 'febbraio february febrero', 'marzo march',
        'aprile april abril', 'maggio may mayo', 'giugno june junio',
        'luglio july julio', 'agosto august', 'settembre september septiembre',
        'ottobre october octubre', 'novembre november noviembre',
        'dicembre december diciembre',
    ), 1)
    for word in group.split()
}
_MONTH = '|'.join(_MONTHS)
_ERA = (r'(?:a\.?\s*c\.?|d\.?\s*c\.?|a\.?\s*e\.?\s*c\.?|e\.?\s*c\.?|'
        r'b\.?\s*c\.?\s*e\.?|b\.?\s*c\.?|a\.?\s*d\.?|c\.?\s*e\.?)')
_YEAR = re.compile(r'(?<![\w-])(?:(?P<leading_era>a\.?\s*d\.?)\s+)?'
                   r'(?P<year>[1-9][0-9]{0,3})(?:\s+(?P<era>' + _ERA + r'))?\.?$')
_BEFORE_MONTH = re.compile(
    r'(?<!\d)(?P<day>[0-9]{1,2})(?:(?:/|\s+(?:o|or)\s+)(?P<other>[0-9]{1,2}))?'
    r'(?:\s+de)?\s+(?P<month>' + _MONTH + r')(?:\s+de)?\s*$')
_AFTER_MONTH = re.compile(r'\b(?P<month>' + _MONTH + r')\s+(?P<day>[0-9]{1,2})\s*,?\s*$')
_KNOWN_MONTH = re.compile(r'\b(?P<month>' + _MONTH + r')(?:\s+de)?\s*$')
_INVALID_SCOPE = re.compile(r'\b(?:regno|regn\w*|reign\w*|born\w*|died|regency|regencia|'
                            r'mandato|mandate|pontificat\w*|governo|govern\w*|dal|dalla|'
                            r'desde|from|non|not|never)\b')
_BIOGRAPHICAL_CONTEXT = re.compile(r'^[\s,;]*(?:[a-z][^\d(),;]*[,;]\s*)*$')
_LIFE_PARENTHESIS = re.compile(r'^\s*\(([^()]{1,350})\)')
_ALIAS_DATELINE = re.compile(
    r'^[^()]{2,100}\((?P<dates>[^()]{1,350})\),\s*'
    r'(?:(?:most )?(?:commonly )?known as|conocid[oa] como|(?:universalmente )?conosciut[oa] come) '
    r'(?P<aliases>[^,.!?]{1,130}),')
_OTHER_PERSON = re.compile(r'\b(?:figli[oa]|padre|madre|son|father|mother|hijo|parente)\b')
_ALTERNATIVE_DATE = re.compile(r'\s+(?:o|or)\s+(?=\d)')
_BORN = re.compile(r'^(?:nacque|e nat[oa]|was born|nacio)\s+', re.I)
_DIED = re.compile(r'\s+[, ]*(?:(?:e|and|y)\s+)?(?:mori|e mort[oa]|died|fallecio|murio)\s+', re.I)
_DEATH_AGE = re.compile(
    r'\b(?:all[\'’]eta di|at (?:the age of|age)|a los)\s+(?P<age>[0-9]{1,3})'
    r'(?:\s+(?:anni|years old|anos))?(?!\w)')
_MONTH_DAYS = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _plain(text):
    return ''.join(char for char in unicodedata.normalize('NFKD', text.casefold())
                   if not unicodedata.combining(char))


def lifespan_question(text):
    text = text.strip(' ¿¡?!.')
    folded = _plain(text)
    for language, forms in _FORMS.items():
        for form in forms:
            match = form.fullmatch(folded)
            if match:
                start, end = match.span('person')
                person = text[start:end].strip(' ,') if start >= 0 else ''
                return language, '' if _plain(person) in _PRONOUNS else person
    return None


@dataclass(frozen=True)
class BiographicalDate:
    year: int
    era: str
    earliest: tuple
    latest: tuple

    @property
    def timeline_year(self):
        return 1 - self.year if self.era == 'bce' else self.year


@dataclass(frozen=True)
class Lifespan:
    minimum: int
    maximum: int
    birth: BiographicalDate | None = None
    death: BiographicalDate | None = None


def _month_window(prefix):
    date = (_BEFORE_MONTH.search(prefix) or _AFTER_MONTH.search(prefix) or _KNOWN_MONTH.search(prefix))
    if not date:
        return None
    location = prefix[:date.start()].strip()
    if not _BIOGRAPHICAL_CONTEXT.fullmatch(location) or _INVALID_SCOPE.search(location):
        return None
    month = _MONTHS[date['month']]
    days = date.groupdict()
    start = int(days.get('day') or 1)
    finish = int(days.get('other') or days.get('day') or _MONTH_DAYS[month - 1])
    if not 1 <= start <= finish <= _MONTH_DAYS[month - 1]:
        return None
    return (month, start), (month, finish)


def _parse_date(text):
    text = text.strip(' ,;')
    found = _YEAR.search(text)
    if not found or (found['leading_era'] and found['era']):
        return None
    prefix = text[:found.start()].strip()
    prefix = re.sub(r'^(?:il|el|on|in|nel|en)\s+', '', prefix)
    raw_era = re.sub(r'\W', '', found['era'] or found['leading_era'] or '')
    era = ('bce' if raw_era in ('ac', 'aec', 'bc', 'bce') else 'ce' if raw_era else '')
    window = _month_window(prefix)
    if window is None:
        for separator in _ALTERNATIVE_DATE.finditer(prefix):
            earlier = _month_window(prefix[:separator.start()])
            later = _month_window(prefix[separator.end():])
            if earlier and later:
                window = min(earlier[0], later[0]), max(earlier[1], later[1])
                break
    if window is None and _BIOGRAPHICAL_CONTEXT.fullmatch(prefix) and not _INVALID_SCOPE.search(prefix):
        window = (1, 1), (12, 31)
    return BiographicalDate(int(found['year']), era, *window) if window else None


def _date_pair(left, right):
    birth, death = _parse_date(left), _parse_date(right)
    if not birth or not death:
        return None
    # The common suffix in "356–323 BC" applies to both endpoints. A range
    # starting in BC with the second era omitted is ambiguous.
    if birth.era == 'bce' and not death.era:
        return None
    birth = BiographicalDate(birth.year, birth.era or death.era or 'ce', birth.earliest, birth.latest)
    death = BiographicalDate(death.year, death.era or birth.era, death.earliest, death.latest)
    span = death.timeline_year - birth.timeline_year
    if not 0 <= span <= 130 or (span == 0 and death.latest < birth.earliest):
        return None
    minimum = max(0, span - int(death.earliest < birth.latest))
    maximum = max(0, span - int(death.latest < birth.earliest))
    return Lifespan(minimum, maximum, birth, death)


def _parenthetical_dates(text):
    dates = text.rsplit(';', 1)[-1]
    endpoints = re.split(r'\s*[–—−]\s*|\s+-\s+|(?<=\d)-(?=\d)', dates, maxsplit=1)
    return _date_pair(*endpoints) if len(endpoints) == 2 else None


def lifespan_evidence(topic, passage):
    if not isinstance(passage, str) or len(passage) > 900:
        return None
    text = _plain(passage).replace('\u200b', '')
    name = re.escape(_plain(topic)).replace(r'\ ', r'\s+')
    person = re.compile(r'(?<!\w)' + name + r'(?!\w)')
    if alias := _ALIAS_DATELINE.match(text):
        if person.search(alias['aliases']) and not _OTHER_PERSON.search(text[:alias.start('dates')]):
            if pair := _parenthetical_dates(alias['dates']):
                return pair
    for subject in person.finditer(text):
        intro = text[:subject.start()]
        if subject.start() > 220 or _OTHER_PERSON.search(intro):
            continue
        following = text[subject.end():].strip(' ,')
        if (match := _LIFE_PARENTHESIS.match(following)) and (pair := _parenthetical_dates(match[1])):
            return pair
        if birth := _BORN.match(following):
            tail = following[birth.end():]
            if death := _DIED.search(tail):
                if pair := _date_pair(tail[:death.start()], tail[death.end():].rstrip('.')):
                    return pair
        if re.match(r'^(?:mori|e mort[oa]|died|murio|fallecio)\b', following):
            reported = _DEATH_AGE.search(following.split(';', 1)[0])
            if reported and not _INVALID_SCOPE.search(following[:reported.start()]):
                age = int(reported['age'])
                if 0 <= age <= 130:
                    return Lifespan(age, age)
    return None


def lifespan_answer(request, passage, audit):
    evidence = lifespan_evidence(request.topic, passage)
    if not evidence:
        return None
    low, high = evidence.minimum, evidence.maximum
    subject = audit.get('citation', {}).get('title') or request.topic
    if request.language == 'en':
        answer = f'{subject} died at age {low}.' if low == high else (
            f'The documented years put {subject}’s age at death between {low} and {high}.')
    elif request.language == 'es':
        answer = f'{subject} murió a los {low} años.' if low == high else (
            f'Los años documentados sitúan la edad de {subject} al morir entre {low} y {high} años.')
    else:
        answer = f'{subject} morì a {low} anni.' if low == high else (
            f'Gli anni documentati indicano che {subject} aveva tra {low} e {high} anni quando morì.')
    return answer, dict(audit, basis='reference_lifespan', source_excerpt=passage,
                        age_minimum=low, age_maximum=high, calculated=evidence.birth is not None)
