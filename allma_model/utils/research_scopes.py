"""Public historical scopes with independently checked source passages."""

from dataclasses import dataclass
import re

from .web_search import _plain


@dataclass(frozen=True)
class Source:
    title: str
    url: str
    markers: tuple[str, ...]
    adjacent: bool = False


@dataclass(frozen=True)
class Facet:
    key: str
    sources: tuple[Source, ...]
    sentences: tuple[str, str, str]


_LANGUAGE_INDEX = {'it': 0, 'en': 1, 'es': 2}

_AMERICAS = (
    Facet('people', (Source(
        'Smithsonian · National Museum of the American Indian',
        'https://americanindian.si.edu/nk360/about/essential-understandings',
        (r'american indians|indigenous peoples', r'western hemisphere|americas', r'15,000|20,000|millennia'),
    ), Source(
        'National Park Service · White Sands footprints',
        'https://home.nps.gov/places/stories-from-the-ice-age.htm',
        (r'footprints', r'23[, ]?000', r'north america'),
    ), Source(
        'Wikipedia · Peopling of the Americas',
        'https://en.wikipedia.org/wiki/Peopling_of_the_Americas',
        (r'(?:earliest|first) (?:people|inhabitants|populations|humans)|ancestral',
         r'americas|north america', r'\d{2}[, ]?000|thousands|pleistocene'),
    )), (
        'I primi abitanti delle Americhe precedono di millenni i viaggi europei e il nome del primo individuo è sconosciuto.',
        'The earliest inhabitants of the Americas predate European voyages by millennia, and the first individual is unknown.',
        'Los primeros habitantes de América preceden en milenios a los viajes europeos y se desconoce la identidad de la primera persona.',
    )),
    Facet('europe', (Source(
        'Parks Canada · L’Anse aux Meadows',
        'https://parks.canada.ca/culture/spm-whs/sites-canada/sec02a',
        (r'viking|norse', r'1,000-year|1000', r'first known european settlement|north america'),
    ), Source(
        'Nature · Dating the Norse presence in Newfoundland',
        'https://www.nature.com/articles/s41586-021-03972-8',
        (r'vikings|norse', r'newfoundland', r'1021'),
    )), (
        'I norreni erano presenti in Nord America, a Terranova, attorno all’anno Mille.',
        'The Norse were present in North America, in Newfoundland, around the year 1000.',
        'Los nórdicos estuvieron en América del Norte, en Terranova, hacia el año 1000.',
    )),
    Facet('voyage', (Source(
        'Library of Congress · October 12',
        'https://www.loc.gov/item/today-in-history/October-12',
        (r'columbus', r'1492', r'baham|caribbean|guanahani'),
    ), Source(
        'Wikipedia · Voyages of Christopher Columbus',
        'https://en.wikipedia.org/wiki/Voyages_of_Christopher_Columbus',
        (r'columbus', r'1492', r'bahamas', r'guanahani|san salvador'),
    )), (
        'Cristoforo Colombo raggiunse le Bahamas, nei Caraibi, nel 1492.',
        'Christopher Columbus reached the Bahamas in the Caribbean in 1492.',
        'Cristóbal Colón llegó a las Bahamas, en el Caribe, en 1492.',
    )),
)

_AUSTRALIA = (
    Facet('people', (Source(
        'National Library of Australia · Europeans and Terra Australis',
        'https://www.library.gov.au/research/research-guides-0/europeans-and-terra-australis',
        (r'indigenous australians', r'inhabited', r'tens of thousands'),
    ), Source(
        'National Museum of Australia · Evidence of first peoples',
        'https://www.nma.gov.au/defining-moments/resources/evidence-of-first-peoples',
        (r'aboriginal|first australians|first peoples', r'australia', r'65,000|60,000|tens of thousands'),
    )), (
        'I popoli aborigeni vivevano in Australia da decine di migliaia di anni prima dei viaggi europei e il nome del primo individuo è sconosciuto.',
        'Aboriginal peoples lived in Australia for tens of thousands of years before European voyages, and the earliest individual is unknown.',
        'Los pueblos aborígenes vivían en Australia desde decenas de miles de años antes de los viajes europeos y se desconoce la identidad de la primera persona.',
    )),
    Facet('europe', (Source(
        'National Library of Australia · Europeans and Terra Australis',
        'https://www.library.gov.au/research/research-guides-0/europeans-and-terra-australis',
        (r'willem janszoon', r'1606', r'first documented landing', r'charted'),
        adjacent=True,
    ),), (
        'Il primo contatto europeo documentato risale al 1606, quando Willem Janszoon esplorò e cartografò parte della costa australiana.',
        'The earliest documented European contact was in 1606, when Willem Janszoon explored and mapped part of the Australian coast.',
        'El primer contacto europeo documentado fue en 1606, cuando Willem Janszoon exploró y cartografió parte de la costa australiana.',
    )),
    Facet('voyage', (Source(
        'National Museum of Australia · Cook claims Australia',
        'https://www.nma.gov.au/defining-moments/resources/cook-claims-australia',
        (r'james cook', r'1770', r'east coast', r'land\w*|reach\w*|sail\w*'),
    ), Source(
        'Wikipedia · First voyage of James Cook',
        'https://en.wikipedia.org/wiki/First_voyage_of_James_Cook',
        (r'cook', r'1770', r'east coast of australia', r'landfall|reach\w*'),
    )), (
        'La spedizione di James Cook raggiunse la costa orientale dell’Australia nel 1770.',
        'James Cook’s expedition reached the east coast of Australia in 1770.',
        'La expedición de James Cook llegó a la costa oriental australiana en 1770.',
    )),
)

_SCOPES = {
    **dict.fromkeys(('america', 'americas', 'le americhe', 'americhe', 'las americas',
                     'continente americano', 'american continent', 'continente de america'), _AMERICAS),
    **dict.fromkeys(('australia', 'continente australiano', 'australian continent'), _AUSTRALIA),
}

_PRINTING = (
    Facet('east_asia', (Source(
        'Wikipedia · Movable type',
        'https://en.wikipedia.org/wiki/Movable_type',
        (r'bi sheng', r'china', r'1040', r'movable[- ]type', r'ceramic'),
    ), Source(
        'Wikipedia · Imprenta',
        'https://es.wikipedia.org/wiki/Imprenta',
        (r'bi sheng', r'china', r'1041', r'tipos moviles', r'porcelana|ceramica'),
    )), (
        'Per la stampa a caratteri mobili, Bi Sheng sviluppò un sistema con caratteri in ceramica in Cina nell’XI secolo.',
        'For movable-type printing, Bi Sheng developed a system using ceramic type in eleventh-century China.',
        'En la impresión con tipos móviles, Bi Sheng desarrolló un sistema con tipos de cerámica en la China del siglo XI.',
    )),
    Facet('metal_type', (Source(
        'UNESCO · Jikji',
        'https://www.unesco.org/en/memory-world/baegun-hwasang-chorok-buljo-jikji-simche-yojeol-volii-second-volume-anthology-great-buddhist-priests',
        (r'jikji', r'cheongju|korea', r'movable metal type', r'1377'),
    ), Source(
        'Wikipedia · Jikji',
        'https://en.wikipedia.org/wiki/Jikji',
        (r'jikji', r'1377', r'metal type', r'korea|goryeo|cheongju'),
    ),), (
        'In Corea, il Jikji documenta l’uso di caratteri mobili metallici nel 1377.',
        'In Korea, the Jikji documents the use of movable metal type in 1377.',
        'En Corea, el Jikji documenta el uso de tipos móviles metálicos en 1377.',
    )),
    Facet('europe', (Source(
        'Gutenberg-Gesellschaft · Gutenberg’s invention',
        'https://www.gutenberg-gesellschaft.de/en/johannes-gutenberg/gutenbergs-invention/seite',
        (r'gutenberg', r'1450', r'movable type'),
    ), Source(
        'Library of Congress · The Gutenberg Bible',
        'https://www.loc.gov/exhibits/bibles/interactives/gutenberg/index.html',
        (r'gutenberg', r'western europe', r'moveable metal type'),
    ), Source(
        'Wikipedia · Printing press',
        'https://en.wikipedia.org/wiki/Printing_press',
        (r'gutenberg', r'1440|1450', r'europe|mainz|holy roman empire', r'printing press'),
    )), (
        'Per la stampa tipografica in Europa, Johannes Gutenberg sviluppò il suo sistema a caratteri mobili a metà del Quattrocento.',
        'For printing in Europe, Johannes Gutenberg developed his movable-type printing system in the mid-fifteenth century.',
        'En Europa, Johannes Gutenberg desarrolló su sistema de impresión con tipos móviles a mediados del siglo XV.',
    )),
)
_PRINTING_TOPICS = frozenset(('imprenta', 'imprenta de tipos moviles', 'printing press',
                              'movable type printing', 'stampa', 'stampa a caratteri mobili'))

_APOLLO = Facet('record', (Source(
    'NASA · Apollo 11',
    'https://www.nasa.gov/learning-resources/for-kids-and-students/what-was-the-apollo-program-grades-k-4/',
    (r'neil armstrong', r'first (?:person|man|human) to (?:walk|set foot)', r'moon'),
), Source(
    'NASA · Neil A. Armstrong',
    'https://www.nasa.gov/people/neil-a-armstrong/',
    (r'armstrong', r'first person to set foot on the moon', r'1969'),
)), (
    'Neil Armstrong fu la prima persona a camminare sulla Luna, durante la missione Apollo 11.',
    'Neil Armstrong was the first person to walk on the Moon, during the Apollo 11 mission.',
    'Neil Armstrong fue la primera persona en caminar sobre la Luna, durante la misión Apolo 11.',
))

_VOSTOK = Facet('record', (Source(
    'European Space Agency · First woman in space',
    'https://www.esa.int/About_Us/ESOC/First_woman_in_space_visits_ESOC',
    (r'valentina tereshkova', r'first woman to travel in space', r'vostok 6', r'1963'),
), Source(
    'European Space Agency · Flight of Vostok 6',
    'https://www.esa.int/articles/about-us/who-we-are/history/first-woman-in-space-valentina',
    (r'tereshkova had become the first woman in space', r'vostok 6', r'16 june'),
    adjacent=True,
)), (
    'Valentina Tereškova fu la prima donna a volare nello spazio, a bordo della Vostok 6 nel 1963.',
    'Valentina Tereshkova was the first woman to fly in space, aboard Vostok 6 in 1963.',
    'Valentina Tereshkova fue la primera mujer en viajar al espacio, a bordo de la Vostok 6 en 1963.',
))

_EVEREST = Facet('record', (Source(
    'NZ History · Hillary and Tenzing reach summit of Everest',
    'https://nzhistory.govt.nz/edmund-hillary-and-tensing-norgay-reach-summit-of-everest',
    (r'edmund hillary', r'tenzing norgay', r'first people to stand on the summit'),
), Source(
    'Guinness World Records · First ascent of Everest',
    'https://www.guinnessworldrecords.com/world-records/first-ascent-of-mount-everest',
    (r'hillary', r'tenzing norgay', r'everest', r'first climbed', r'1953'),
)), (
    'Edmund Hillary e Tenzing Norgay furono le prime persone a raggiungere la vetta dell’Everest, nel 1953.',
    'Edmund Hillary and Tenzing Norgay were the first people to reach the summit of Everest, in 1953.',
    'Edmund Hillary y Tenzing Norgay fueron las primeras personas en llegar a la cima del Everest, en 1953.',
))

_DOCUMENTED_RECORDS = {
    **dict.fromkeys((('walk', 'luna', ''), ('walk', 'moon', '')), _APOLLO),
    **dict.fromkeys((('fly', 'spazio', 'donna'), ('fly', 'space', 'woman'), ('fly', 'espacio', 'mujer')), _VOSTOK),
    **dict.fromkeys((('climb', topic, '') for topic in ('everest', 'monte everest', 'mount everest')), _EVEREST),
}


def historical_facets(question):
    if question.action == 'invent' and not question.role and question.topic in _PRINTING_TOPICS:
        return _PRINTING
    if question.action not in ('discover', 'reach'):
        return ()
    facets = _SCOPES.get(question.topic, ())
    if question.role.startswith('europ'):
        return tuple(facet for facet in facets if facet.key == 'europe')
    return facets if not question.role else ()


def documented_record(question):
    return _DOCUMENTED_RECORDS.get((question.action, question.topic, question.role))


def source_passage(paragraphs, markers, *, adjacent=False):
    """Keep the proposition in one paragraph or in a documented adjacent pair."""
    for index, paragraph in enumerate(paragraphs):
        if adjacent:
            paragraph = ' '.join(paragraphs[index:index + 2])
        folded = _plain(paragraph)
        if len(paragraph) <= 1300 and all(re.search(marker, folded) for marker in markers):
            return paragraph
    return None


def localized_statement(facet, language):
    return facet.sentences[_LANGUAGE_INDEX[language]]
