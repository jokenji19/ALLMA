"""Weather requests, observations and forecasts with typed source data."""
from dataclasses import dataclass
from datetime import datetime, timedelta
import math
import re
import threading
import time
import unicodedata

import pytz

from .bounded_io import reference_io
from .online_transport import request_json

GEOCODER = 'https://geocoding-api.open-meteo.com/v1/search'
FORECAST = 'https://api.open-meteo.com/v1/forecast'
WEATHER_SITE = 'https://open-meteo.com/'
_PLACE = re.compile(r"[^\W\d_]+(?:[ '’\-][^\W\d_]+)*(?:,\s*[^\W\d_]+(?:[ '’\-][^\W\d_]+)*)?", re.UNICODE)
_LANGUAGE_FORMS = {
    'it': (
        r'(?:(?:allma|per favore),? )?(?:(?:dimmi|raccontami|mostrami|indicami|qual [èe]|quali sono|'
        r'vorrei sapere|voglio sapere|controlla(?:mi)?|cerca(?:mi)?|puoi (?:dirmi|controllare)|'
        r'mi (?:dici|controlli)) )?(?:il |le )?',
        r'che (?:tempo|meteo) (?:fa|far[àa]|c[’\'][èe])|(?:com[’\'][èe]|come sar[àa]) il (?:tempo|meteo)|'
        r'meteo|previsioni(?: del tempo| meteo)?|piover[àa]|piove|quant[ie] gradi (?:fa|fanno|ci sono)|'
        r'qual [èe] la temperatura|che temperatura (?:fa|c[’\'][èe])',
        r'oggi|adesso|ora|domani|dopodomani', r'a|ad|per|in', r'e invece|invece|e'),
    'en': (
        r'(?:(?:tell me|show me|check|please check|what is|what are|what[’\']s|can you (?:tell me|check)) )?(?:the )?',
        r'(?:how(?: is|[’\']s) the )?weather(?: (?:like|forecast))?|(?:what will the )weather(?: be like)?|'
        r'forecast|(?:is it raining|will it rain)|temperature',
        r'today|right now|now|the day after tomorrow|tomorrow', r'in|at|for', r'what about|how about|and'),
    'es': (
        r'(?:(?:dime|cu[eé]ntame|mu[eé]strame|consulta|revisa|puedes decirme|quiero saber) )?(?:el |la )?',
        r'qu[eé] tiempo (?:hace|har[áa])|c[oó]mo est[áa] el (?:tiempo|clima)|tiempo|clima|'
        r'pron[oó]stico(?: del tiempo)?|llueve|llover[áa]|qu[eé] temperatura hace|cu[áa]ntos grados hace|temperatura',
        r'hoy|ahora|en este momento|pasado ma[ñn]ana|ma[ñn]ana', r'en|para', r'y en cambio|en cambio|y'),
}
_REQUESTS = {
    lang: re.compile(
        rf"^{prefix}(?P<kind>{kind})(?: (?P<before>{day}))?(?: (?:(?:{place}) )?(?P<city>.+?))?(?: (?P<after>{day}))?$",
        re.I)
    for lang, (prefix, kind, day, place, _) in _LANGUAGE_FORMS.items()
}
_FOLLOWUPS = {
    lang: (
        re.compile(rf'^(?:(?:{continuation}) )?(?P<day>{day})$', re.I),
        re.compile(rf'^(?:{continuation}) (?:(?P<before>{day}) )?(?:{place}) (?P<city>.+?)(?: (?P<after>{day}))?$', re.I),
    )
    for lang, (_, _, day, place, continuation) in _LANGUAGE_FORMS.items()
}
_CLARIFICATION = re.compile(r"^(?:intendo |intendevo |quella (?:in|negli) |I mean |me refiero a )?(?P<city>.+?)$", re.I)
_CITIES = {'turin': 'Torino', 'milan': 'Milano', 'rome': 'Roma'}
_DAYS = {'domani': 1, 'dopodomani': 2, 'tomorrow': 1, 'the day after tomorrow': 2, 'manana': 1, 'pasado manana': 2}
_CURRENT = {'adesso', 'ora', 'right now', 'now', 'ahora', 'en este momento'}
_DAILY = re.compile(r'\b(?:previsioni|piover[aà]|far[aà]|sar[aà]|weather forecast|forecast|will|'
                    r'pron[oó]stico|llover[aá]|har[aá])\b', re.I)
_RAIN = re.compile(r'^(?:piov|lluev|llover|will it rain|is it raining)', re.I)
_CONDITIONS = {0:'sereno', 1:'prevalentemente sereno', 2:'parzialmente nuvoloso', 3:'coperto',
               45:'nebbia', 48:'nebbia con brina', 51:'pioviggine', 53:'pioviggine', 55:'pioviggine',
               56:'pioviggine gelata', 57:'pioviggine gelata', 61:'pioggia debole', 63:'pioggia',
               65:'pioggia forte', 66:'pioggia gelata', 67:'pioggia gelata', 71:'neve debole',
               73:'neve', 75:'neve forte', 77:'granuli di neve', 80:'rovesci', 81:'rovesci',
               82:'rovesci forti', 85:'rovesci di neve', 86:'rovesci di neve', 95:'temporali',
               96:'temporali con grandine', 99:'temporali con grandine'}
_CONDITION_TRANSLATIONS = {
    'sereno': ('clear', 'despejado'), 'prevalentemente sereno': ('mostly clear', 'mayormente despejado'),
    'parzialmente nuvoloso': ('partly cloudy', 'parcialmente nublado'), 'coperto': ('overcast', 'cubierto'),
    'nebbia': ('fog', 'niebla'), 'nebbia con brina': ('freezing fog', 'niebla helada'),
    'pioviggine': ('drizzle', 'llovizna'), 'pioviggine gelata': ('freezing drizzle', 'llovizna helada'),
    'pioggia debole': ('light rain', 'lluvia ligera'), 'pioggia': ('rain', 'lluvia'),
    'pioggia forte': ('heavy rain', 'lluvia intensa'), 'pioggia gelata': ('freezing rain', 'lluvia helada'),
    'neve debole': ('light snow', 'nieve ligera'), 'neve': ('snow', 'nieve'),
    'neve forte': ('heavy snow', 'nieve intensa'), 'granuli di neve': ('snow grains', 'nieve granulada'),
    'rovesci': ('showers', 'chubascos'), 'rovesci forti': ('heavy showers', 'chubascos intensos'),
    'rovesci di neve': ('snow showers', 'chubascos de nieve'), 'temporali': ('thunderstorms', 'tormentas'),
    'temporali con grandine': ('thunderstorms with hail', 'tormentas con granizo'),
    'condizioni non specificate': ('conditions unspecified', 'condiciones sin especificar'),
}


def city_clarification(language, choices):
    prompt, found, hint = {
        'it': ('Quale località intendi?', 'Ho trovato', 'Indicami la città, con regione o Paese se necessario.'),
        'en': ('Which place do you mean?', 'I found', 'Enter the city and, if needed, its region or country.'),
        'es': ('¿A qué localidad te refieres?', 'Encontré', 'Indica la ciudad y, si hace falta, la región o el país.'),
    }.get(language, ('Quale località intendi?', 'Ho trovato', 'Indicami la città.'))
    return f'{prompt} {found} {", ".join(choices)}.' if choices else f'{prompt} {hint}'


def _condition(code, language):
    label = _CONDITIONS.get(code, 'condizioni non specificate') if type(code) is int else 'condizioni non specificate'
    return _CONDITION_TRANSLATIONS[label][0 if language == 'en' else 1] if language in ('en', 'es') else label


def _key(text):
    return ''.join(ch for ch in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(ch))


def city_name(value, language='it'):
    from .public_language import private_identity_topic
    from .public_references import public_query_text

    if (isinstance(value, str) and 2 <= len(value) <= 70 and _PLACE.fullmatch(value)
            and len(value.split()) <= 8 and public_query_text(value) and not private_identity_topic(language, value)
            and not re.search(
                r"\b(?:mio|mia|nostr\w*|casa|ufficio|residenza|indirizzo|ospedale|via|viale|piazza|"
                r"dimmi|scrivi|ignora|poesia|significa|che|perché|perche|password|grazie|ciao|va bene|"
                r"medico|cognome|nome|oggi|domani|dopodomani|ora|adesso|home|near me|address|"
                r"cerca de m[ií]|domicilio|direcci[oó]n|explain|forecast|weather|tiempo|clima)\b", value, re.I)):
        return _CITIES.get(_key(value), value)
    return None


@dataclass(frozen=True)
class WeatherRequest:
    city: str | None
    day: int
    daily: bool
    rain: bool
    language: str = 'it'


def weather_request(message, history=()):
    from .public_references import local_only_request

    if not isinstance(message, str) or len(message) > 180:
        return None
    text = unicodedata.normalize('NFKC', message).strip(' ¿¡?!.')
    if any(unicodedata.category(ch).startswith('C') for ch in text):
        return None
    # An offline suffix can still be recognized and reported as unavailable.
    if local_only_request(text):
        text = re.sub(r'(?:[,;.!?]\s*|\s+)(?:ma )?(?:offline|senza internet|non cercare (?:online|su internet)|'
                      r'without (?:internet|searching online)|do not search online|sin internet|no busques en internet)$',
                      '', text, flags=re.I).rstrip('?! .')
    text = re.sub(r'^(?:ciao(?: allma)?|bene|tutto bene|ok|grazie|hello|hi|hola)[,;.!]\s+', '', text, flags=re.I)
    text = ' '.join(text.split())
    previous = ((history[-1].metadata.get('reference_review') or {}).get('weather_context')
                if history and history[-1].role == 'assistant' else None)
    if not isinstance(previous, dict):
        previous = {}
    for language, pattern in _REQUESTS.items():
        match = pattern.fullmatch(text)
        if not match:
            continue
        day = _key(match['before'] or match['after'] or '')
        if match['before'] and match['after']:
            return None
        kind = match['kind']
        city = city_name(match['city'] or previous.get('city'), language)
        future = bool(re.search(r'\b(?:far[àa]|sar[àa]|piover[àa]|will|har[áa]|llover[áa])\b', kind, re.I))
        offset = _DAYS.get(day, 1 if not day and future else 0)
        daily = bool(offset or day in ('oggi', 'today', 'hoy') or _DAILY.search(kind) and day not in _CURRENT)
        return WeatherRequest(city, offset, daily, bool(_RAIN.match(kind)), language)
    if not previous:
        return None
    rain = previous.get('rain') is True
    offset = previous.get('day')
    offset = offset if type(offset) is int and 0 <= offset <= 2 else 0
    for language, (day_pattern, city_pattern) in _FOLLOWUPS.items():
        followup = day_pattern.fullmatch(text)
        if followup and city_name(previous.get('city'), language):
            day = _key(followup['day'])
            return WeatherRequest(previous['city'], _DAYS.get(day, 0), day not in _CURRENT, rain, language)
        place = city_pattern.fullmatch(text)
        if not place or (place['before'] and place['after']):
            continue
        day = _key(place['before'] or place['after'] or '')
        city = city_name(place['city'], language)
        return WeatherRequest(city, _DAYS.get(day, 0) if day else offset,
                              day not in _CURRENT if day else previous.get('daily') is True, rain, language)
    if previous.get('clarify') == 'city':
        language = previous.get('language', 'it')
        candidate = _CLARIFICATION.fullmatch(text)
        city = city_name(candidate['city'], language) if candidate else None
        if city and (',' in city or len(city.split()) <= 4):
            return WeatherRequest(city, offset, previous.get('daily') is True, rain, language)
    return None


def _number(value, minimum, maximum):
    return type(value) in (int, float) and math.isfinite(value) and minimum <= value <= maximum


def _decimal(value, language):
    text = f'{value:g}'
    return text if language == 'en' else text.replace('.', ',')


def _locations(data, query):
    locality, _, qualifier = query.partition(',')
    candidates = []
    rows = data.get('results', [])
    if not isinstance(rows, list):
        raise ValueError('Unexpected location results')
    for place in rows[:12]:
        if not isinstance(place, dict) or not all(isinstance(place.get(key), str) for key in ('name', 'country', 'country_code')):
            continue
        if not (re.fullmatch(r'[A-Z]{2}', place['country_code']) and
                (not place.get('feature_code') or str(place['feature_code']).startswith('PPL'))):
            continue
        if not (_number(place.get('latitude'), -90, 90) and _number(place.get('longitude'), -180, 180)):
            continue
        if _key(place['name']) != _key(locality.strip()):
            continue
        if qualifier and _key(qualifier.strip()) not in {
                _key(str(place.get(key, ''))) for key in ('country', 'country_code', 'admin1', 'admin2')}:
            continue
        location = f"{place['name']}, {place['country']}"
        if city_name(location):
            candidates.append(place)
    if not candidates:
        return None, []
    if not qualifier:
        # A neighborhood with a large population is not a competing city.
        # Qualified queries can still select districts, e.g. Palermo, Argentina.
        cities = [place for place in candidates if place.get('feature_code') != 'PPLX']
        if cities:
            candidates = cities
    ranked = sorted(candidates, key=lambda place: place.get('population', 0)
                    if type(place.get('population')) is int else 0, reverse=True)
    first = ranked[0]
    population = first.get('population')
    second = ranked[1].get('population') if len(ranked) > 1 else None
    # Prefer a clear major city. When names remain comparable, ask for a region.
    if len(ranked) == 1 or (type(population) is int and population >= 100000
                             and type(second) is int and population >= max(1, second) * 8):
        return first, []
    options = list(dict.fromkeys(choice for r in ranked[:4] for choice in (
        f"{r['name']}, {r.get('admin1') or r['country']}",) if city_name(choice)))
    return None, options


class OpenMeteo:
    name = 'Open-Meteo'

    def __init__(self):
        self._lock = threading.Lock()
        self._places = {}

    def remember_location(self, query, place):
        with self._lock:
            for key in (query, f"{place['name']}, {place.get('admin1') or place['country']}"):
                self._places.pop(_key(key), None)
                self._places[_key(key)] = (place, time.monotonic())
            while len(self._places) > 24:
                del self._places[next(iter(self._places))]

    def clear_locations(self):
        with self._lock:
            self._places.clear()

    def fetch(self, request, cancelled, allowed):
        return reference_io(lambda stop: self._fetch(request, stop, allowed), cancelled, allowed)

    def _fetch(self, request, cancelled, allowed):
        import requests

        with requests.Session() as session:
            session.trust_env = False
            with self._lock:
                stored = self._places.get(_key(request.city))
            place = stored[0] if stored and time.monotonic() - stored[1] <= 3600 else None
            if place is None:
                name = request.city.partition(',')[0]
                geo = request_json(session, GEOCODER, cancelled, allowed,
                                   params={'name': name, 'language':'it', 'count':12, 'format':'json'})
                if geo is None:
                    return None
                place, choices = _locations(geo, request.city)
                if not place:
                    return {'status':'city_ambiguous' if choices else 'city_not_found', 'choices':choices}
                if allowed():
                    self.remember_location(request.city, place)
            selection = ('daily', 'weather_code,temperature_2m_min,temperature_2m_max,precipitation_probability_max') if request.daily else (
                'current', 'weather_code,temperature_2m,apparent_temperature,wind_speed_10m')
            raw = request_json(session, FORECAST, cancelled, allowed, params={
                'latitude': round(place['latitude'], 3), 'longitude': round(place['longitude'], 3),
                'timezone':'auto', 'timeformat':'unixtime', 'forecast_days':request.day + 1,
                selection[0]:selection[1]})
            return weather_answer(place, raw, request) if raw is not None else None


def weather_answer(place, raw, request, *, now=None):
    now = time.time() if now is None else now
    zone = pytz.timezone(raw['timezone'])
    local_now = datetime.fromtimestamp(now, zone)
    language = request.language
    reference_city = f"{place['name']}, {place['country']}"
    city = f"{place['name']}, {place.get('admin1') or place['country']}"
    followup_city = city if city_name(city) else reference_city
    if not city_name(city):
        city = reference_city
    fields = raw['daily' if request.daily else 'current']
    units = raw['daily_units' if request.daily else 'current_units']
    if units.get('time') != 'unixtime':
        raise ValueError('Weather timestamp unit')
    if request.daily:
        date = local_now.date() + timedelta(days=request.day)
        index = next((i for i, stamp in enumerate(fields['time'][:3])
                      if _number(stamp, now - 86400, now + 3 * 86400)
                      and datetime.fromtimestamp(stamp, zone).date() == date), None)
        if index is None:
            raise ValueError('Weather forecast date')
        low, high, rain, code = (fields[field][index] for field in
                                 ('temperature_2m_min', 'temperature_2m_max', 'precipitation_probability_max', 'weather_code'))
        if (units.get('temperature_2m_min') != '°C' or units.get('temperature_2m_max') != '°C'
                or units.get('precipitation_probability_max') != '%'
                or not (_number(low, -100, 70) and _number(high, low, 70) and _number(rain, 0, 100))):
            raise ValueError('Weather forecast values')
        condition = _condition(code, language)
        label = date.strftime('%d/%m/%Y')
        precipitation_label, forecast_prefix, data_prefix = {
            'it': ('probabilità massima di precipitazioni', f'A **{city}**, previsione per il', 'Previsione del'),
            'en': ('maximum chance of precipitation', f'In **{city}**, forecast for', 'Forecast for'),
            'es': ('probabilidad máxima de precipitación', f'En **{city}**, pronóstico para el', 'Pronóstico para el'),
        }[language]
        precipitation = f'{precipitation_label} **{_decimal(rain, language)}%**'
        temperatures = f'min **{_decimal(low, language)} °C**, max **{_decimal(high, language)} °C**'
        details = [precipitation, condition] if request.rain else [condition, temperatures, precipitation]
        answer = f'{forecast_prefix} **{label}**: {", ".join(details)}.'
        data_label = f'{data_prefix} {label}'
    else:
        stamp = fields['time']
        if not _number(stamp, now - 60 * 60, now + 15 * 60):
            raise ValueError('Weather data is stale')
        temp, feels, wind, code = (fields[field] for field in
                                    ('temperature_2m', 'apparent_temperature', 'wind_speed_10m', 'weather_code'))
        if (units.get('temperature_2m') != '°C' or units.get('apparent_temperature') != '°C'
                or units.get('wind_speed_10m') != 'km/h'
                or not (_number(temp, -100, 70) and _number(feels, -120, 80) and _number(wind, 0, 400))):
            raise ValueError('Weather conditions values')
        condition = _condition(code, language)
        local_stamp = datetime.fromtimestamp(stamp, zone)
        label = local_stamp.strftime('%d/%m/%Y %H:%M %Z')
        temperature, feels, wind = (_decimal(value, language) for value in (temp, feels, wind))
        answer, data_prefix = {
            'it': (f'A **{city}**, {condition} e **{temperature} °C**. '
                   f'Percepiti {feels} °C, vento a {wind} km/h. Dato del {label}.', 'Stima del modello del'),
            'en': (f'In **{city}**, {condition} and **{temperature} °C**. '
                   f'Feels like {feels} °C, wind {wind} km/h. Data from {label}.', 'Model estimate for'),
            'es': (f'En **{city}**, {condition} y **{temperature} °C**. '
                   f'Sensación de {feels} °C, viento a {wind} km/h. Datos del {label}.', 'Estimación del modelo del'),
        }[language]
        data_label = f'{data_prefix} {label}'
    return {'status':'obtained','answer':answer,'city':followup_city, 'citation': {
        'title':'Open-Meteo · ' + reference_city, 'url':WEATHER_SITE, 'provider':'open_meteo',
        'revision':0, 'fetched_at':now, 'data_label':data_label}}
