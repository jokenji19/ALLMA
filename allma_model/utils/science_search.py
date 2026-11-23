"""Bounded public science questions and the evidence each relation requires."""

from dataclasses import dataclass
import re

from .web_search import _plain


@dataclass(frozen=True)
class ScienceQuestion:
    language: str
    form: str
    topics: tuple[str, ...]
    evidence: tuple[str, ...]
    official: tuple[tuple[str, str], ...] = ()

    def supports(self, passage):
        body = _plain(passage)
        return bool(body and not _UNSUPPORTED.search(body)
                    and all(re.search(pattern, body) for pattern in self.evidence))


_UNSUPPORTED = re.compile(
    r"\b(?:myth\w*|mitos?|leggenda|leyenda|supostamente|supposedly|incorrectly|"
    r"nao \w+ ultravioleta|does not cause|non dipende|non (?:galleggia|e causat\w*)|"
    r"n['’]est pas|keine[nr]? spannung)\b")
_HOW_IT = r"come (?:si form(?:a|ano)|avviene|si verifica(?:no)?) "
_QUESTIONS = (
    ScienceQuestion('en',
        r"(?:what|which) was (?:the )?first artificial (?:earth )?satellite(?: (?:launched|put|placed) into orbit)?",
        ('first artificial Earth satellite', 'first artificial satellite launch'),
        (r"\b(?:the |world['’]s )first (?:artificial (?:earth )?satellite|earth-orbiting artificial satellite)\b",
         r'\blaunch\w*\b', r'\borbit\w*\b', r'\b(?:19|20)\d{2}\b'),
        (('NASA · The Dawn of the Space Age', 'https://www.nasa.gov/history/dawn-of-the-space-age/'),
         ('NASA · Sputnik and the Origins of the Space Age', 'https://www.nasa.gov/history/sputnik/sputorig.html'))),
    ScienceQuestion('it',
        r"(?:perche|come mai) (?:il |del |un cubetto di )?ghiaccio (?:galleggia|resta a galla|sta a galla)"
        r"(?: (?:in |nell['’]|sull['’]|sopra l['’])acqua(?: liquida)?)?",
        ('ghiaccio galleggia acqua', 'acqua'),
        (r'\bghiaccio\b', r'\bacqua(?: liquida)?\b',
         r'\bmeno dens[oa]\b|densita [^.;]{0,38}\b(?:minore|inferiore|piu bassa)\b|densita [^.;]{0,24}\bmaggiore di quella del ghiaccio\b')),
    ScienceQuestion('es',
        r"(?:por que|como es que) marte (?:es roj[oa]|(?:se )?ve roj[oa]|(?:tiene (?:un )?|es de )color roj[oa])",
        ('marte color rojo', 'marte planeta'),
        (r'\b(?:marte|marcian\w*|planeta rojo)\b', r'\broj\w*\b',
         r'\b(?:oxidos? de hierro|hierro oxidad\w*|herrumbre)\b',
         r'\b(?:debido|se debe|confiere|causa\w*|proporcion\w*|provoc\w*)\b')),
    ScienceQuestion('en',
        r"(?:why (?:is mars red|does mars (?:look|appear) red)|what makes mars red)",
        ('mars red iron', 'mars'),
        (r'\b(?:mars|martian|red planet)\b', r'\bred\b', r'\biron\b',
         r'\b(?:oxid\w*|rust\w*)\b', r'\b(?:because|due to|caus\w*|gives?)\b'),
        (('NASA Science · Mars Facts', 'https://science.nasa.gov/mars/facts/'),)),
    ScienceQuestion('en',
        r"(?:(?:why|how) (?:do (?:the )?(?:ocean )?tides (?:happen|occur|form))|what causes (?:the )?(?:ocean )?tides)",
        ('ocean tides', 'tide'),
        (r'\btid(?:e|es|al)\b', r'\b(?:moon|lunar)\b', r'\bgravit\w*\b',
         r'\b(?:caus\w*|result\w* from|driven by|pull\w*|exerts?|exerted)\b'),
        (('NOAA · Tides', 'https://oceanservice.noaa.gov/facts/tidescurrents.html'),)),
    ScienceQuestion('it',
        _HOW_IT + r"(?:un['’]|l['’]|le )?(?:eclissi solar[ei]|eclissi (?:di|del) sole)",
        ('eclissi solare',),
        (r"\bluna\b", r"\bsole\b", r"\bterra\b",
         r"\b(?:la luna (?:si trova|passa|si interpone) (?:allineata )?(?:tra|fra) (?:il sole e la terra|la terra e il sole)|"
         r"luna [^.;]{0,45}(?:oscura|copre|nasconde) (?:il |una parte del )?sole)\b"),
        (('INAF · Eclissi di Sole', 'https://www.media.inaf.it/2022/10/17/eclissi-sole-25-ottobre/'),)),
    ScienceQuestion('en',
        r"(?:(?:how|why) (?:does a solar eclipse|do solar eclipses) (?:happen|occur|form)|what causes (?:a solar eclipse|solar eclipses))",
        ('solar eclipse',),
        (r'\bsolar eclipse\w*\b',
         r'\b(?:the )?moon (?:passes|moves|is) between (?:the )?(?:sun and (?:the )?earth|earth and (?:the )?sun)\b'),
        (('NASA Science · Why Do Eclipses Happen?', 'https://science.nasa.gov/eclipses/geometry/'),)),
    ScienceQuestion('en',
        r"(?:what(?: is|'s) (?:the )?difference between (?:magma and lava|lava and magma)|"
        r"how (?:is magma different from lava|does magma become lava|are magma and lava different))",
        ('magma lava',),
        (r'\bmagma\b', r'\blava\b', r'\b(?:surface|erupt\w*)\b',
         r'\b(?:known as|called|becomes?|lava is magma|extruded as)\b'),
        (('USGS · The Nature of Volcanoes', 'https://pubs.usgs.gov/gip/volc/nature.html'),)),
    ScienceQuestion('fr',
        r"(?:combien vaut|a combien s['’]eleve|quelle est(?: la valeur de)?) la vitesse de la lumiere(?: dans le vide)?",
        ('vitesse lumiere vide',),
        (r'\bvitesse de la lumiere\b', r'\bdans le vide\b', r'\b(?:egale|vaut|valeur numerique fixee)\b',
         r'(?<![/\d])\d{2,3}(?:[ .]\d{3}){1,2}(?:\s+(?:lorsqu.elle est exprimee en|quand elle est exprimee en))?'
         r'\s+(?:m/s|m s\s*[−-]?\s*1|metres? par seconde)\b'),
        (('BIPM · Unité de base du SI, le mètre', 'https://www.bipm.org/fr/si-base-units/metre'),)),
    ScienceQuestion('pt',
        r"(?:qual (?:e )?a funcao d(?:as|a) |(?:para que|o que) (?:servem?|fazem?) (?:as? )?)"
        r"mitocondrias?(?: nas celulas| na celula)?",
        ('mitocôndria', 'respiração celular mitocôndria'),
        (r'\bmitocondri\w*\b', r'\b(?:atp|trifosfato de adenosina)\b',
         r'\b(?:energia|respiracao celular|fosforilacao oxidativa)\b',
         r'\b(?:produ\w*|sintese|converte|gera\w*|sintetiza\w*|fornecem?|transforma\w*)\b'),
        (('Universidade de São Paulo · Atlas de Biologia Celular',
          'https://atin.icb.usp.br/inicio/topicos/mitocondrias/'),)),
    ScienceQuestion('de',
        r"(?:wie entstehen|wie kommt es zu|warum entstehen) erdbeben (?:an (?:den )?plattengrenzen|"
        r"an tektonischen plattengrenzen|entlang (?:der )?plattengrenzen)",
        ('Erdbeben Plattengrenzen', 'Erdbeben Entstehung'),
        (r'\berdbeben\b', r'\b(?:erdplatten|platten|plattengrenzen)\b',
         r'\bspann\w*\b', r'\b(?:entlad\w*|ruckartig\w*|schlagartig\w*|freigesetzt|gelost)\b')),
    ScienceQuestion('pt',
        r"(?:qual (?:e )?a funcao da|para que serve|o que faz) (?:a )?camada de ozon(?:i)?o",
        ('camada de ozônio',),
        (r'\bcamada de ozon(?:i)?o\b', r'\b(?:ultravioleta\w*|uv[abc]?)\b',
         r'\b(?:absorv\w*|proteg\w*|filtr\w*|bloquei\w*|impede\w*|reduz\w*)\b'),
        (('Ministério do Meio Ambiente · Proteção à Camada de Ozônio',
          'https://www.gov.br/mma/pt-br/composicao/smc/dpmi/ozonio/protecao-a-camada-de-ozonio'),)),
    ScienceQuestion('en',
        r"how does (?:a |an |the )?pumped[- ]storage (?:hydropower|hydroelectricity|hydroelectric storage)(?: system)? work",
        ('pumped storage hydropower',),
        (r'\bwater\b', r'\breservoirs?\b',
         r'\b(?:pump\w* (?:the )?water|water [^.;]{0,45}pump\w*)\b[^.;]{0,95}\b(?:upper|higher)\b',
         r'\b(?:generat\w*|discharg\w*)\b', r'\b(?:turbines?|electricity)\b'),
        (('US Department of Energy · Pumped Storage Hydropower',
          'https://www.energy.gov/cmei/water/pumped-storage-hydropower'),)),
    ScienceQuestion('it',
        r"come (?:funziona (?:una |la )?(?:turbina eolica|pala eolica)|"
        r"funziona (?:un |l')?aerogeneratore|(?:produce|genera) elettricita (?:una |la )?turbina eolica)",
        ('turbina eolica vento rotore generatore', 'aerogeneratore'),
        (r'\bvento\b', r'\b(?:rotore|pale|turbina)\b',
         r'\b(?:ruot\w*|rotazion\w*|movimento|gir\w*)\b',
         r'\b(?:trasform\w*|convert\w*)\b[^.;]{0,90}\b(?:elettricita|energia elettrica)\b|'
         r'\b(?:generator\w*|alternator\w*)\b[^.;]{0,65}\b(?:gener\w*|produc\w*)\s+(?:elettricita|energia elettrica)\b'),
        (('Assolombarda · Eolico',
          'https://www.assolombarda.it/transizione-energetica/energia-rinnovabile-elettrica/eolico/intro'),
         ('Enel · Funzionamento della turbina eolica',
          'https://www.enel.com/it/learning-hub/rinnovabili/energia-eolica/pala-eolica'))),
    ScienceQuestion('es',
        r"como (?:(?:produce|genera) (?:electricidad|energia electrica) (?:un |el )?"
        r"panel (?:solar )?fotovoltaico|funciona (?:un |el )?panel (?:solar )?fotovoltaico)",
        ('energia solar fotovoltaica', 'efecto fotovoltaico'),
        (r'\b(?:fotovoltaic\w*|celdas? solares?)\b', r'\b(?:luz|radiacion) solar\b',
         r'\b(?:electricidad|energia electrica|corriente electrica)\b',
         r'\b(?:convierte|conversion|transform\w*|gener\w*)\b'),
        (('IDAE · Solar Fotovoltaica',
          'https://www.idae.es/tecnologias/energias-renovables/uso-electrico/solar-fotovoltaica'),
         ('IDAE · Célula fotovoltaica', 'https://www.idae.es/glosario/celula-fotovoltaica'))),
    ScienceQuestion('en',
        r"(?:what (?:is|was) the (?:long[- ]term )?(?:temperature|warming|global warming) (?:goal|target) "
        r"of (?:the )?paris agreement|what (?:temperature|warming) (?:goal|target) does (?:the )?"
        r"paris agreement set)",
        ('paris agreement temperature goal', 'paris agreement'),
        (r'\b(?:temperature|warming)\b', r'\bpre[- ]industrial\b',
         r'\bwell below\s+2\s*(?:°\s*c|degrees?)\b.{0,170}'
         r'\bpursu\w*\s+efforts\b.{0,100}\b1[.,]5\s*(?:°\s*c|degrees?)\b'),
        (('United Nations · 1.5°C: what it means and why it matters',
          'https://www.un.org/en/climatechange/science/climate-issues/degrees-matter'),
         ('UNFCCC · Key aspects of the Paris Agreement',
          'https://unfccc.int/most-requested/key-aspects-of-the-paris-agreement'))),
    ScienceQuestion('it',
        r"(?:da dove (?:proviene|viene|deriva) (?:l['’]energia geotermica|il calore geotermico)|"
        r"qual e l'origine dell['’]energia geotermica|come si origina l['’]energia geotermica)",
        ('energia geotermica calore terrestre', 'energia geotermica'),
        (r'\bgeotermi(?:a|c\w*)\b', r'\bcalore\b',
         r"\b(?:calore (?:interno (?:della terra|terrestre)|della terra|del sottosuolo|terrestre|"
         r"naturale proveniente dal sottosuolo)|(?:interno|profondita|superficie) della terra)\b",
         r"\bgeotermi(?:a|c\w*)\b[^.;]{0,95}\b(?:trae origine|deriva|proviene|sfrutta|contenut\w*|immagazzinat\w*)\b|"
         r"\bcalore\b[^.;]{0,95}\benergia geotermica (?:in esso racchiusa|che ne deriva)\b"),
        (('INGV · Calore terrestre', 'https://pulse.ingv.it/calore/'),
         ('Università di Padova · Energia geotermica',
          'https://ilbolive.unipd.it/it/news/scienza-ricerca/energia-geotermica-sguardo-dinsieme-fonte'))),
    ScienceQuestion('fr',
        r"comment (?:fonctionne (?:une |la )?pompe a chaleur|(?:une |la )?pompe a chaleur (?:transfere|deplace) la chaleur)",
        ('pompe a chaleur fonctionnement fluide frigorigene', 'pompe a chaleur'),
        (r'\bchaleur\b', r'\b(?:fluide (?:frigorigene|caloporteur)|compresseur|evaporateur)\b',
         r'\b(?:capt\w*|recuper\w*|prelev\w*|absorb\w*)\b',
         r'\b(?:transfer\w*|restitu\w*|ced\w*|liber\w*)\b'),
        (('Saunier Duval · Le rôle du fluide frigorigène',
          'https://www.saunierduval.fr/particulier/nous-vous-accompagnons/je-m-informe/sur-la-pompe-a-chaleur/quel-est-le-role-du-fluide-frigorigene-dans-une-pompe-a-chaleur/'),
         ('ENGIE · Fonctionnement d’une pompe à chaleur',
          'https://particuliers.engie.fr/economies-energie/conseils-equipements-chauffage/conseils-pompe-a-chaleur/pompe-a-chaleur-comment-ca-marche.html'))),
    ScienceQuestion('en',
        r"(?:how do (?:forests act as carbon sinks|forests (?:absorb and store|capture and store|store) carbon(?: dioxide)?)"
        r"|why are forests (?:considered )?carbon sinks)",
        ('forest carbon sinks photosynthesis storage', 'carbon sink forests'),
        (r'\b(?:forests?|trees)\b', r'\b(?:carbon dioxide|co2)\b',
         r'\bphotosynthesis\b', r'\b(?:take(?:s|n)?[- ](?:in|up)|uptake|remov\w*|absorb\w*|captur\w*|draw\w*)\b',
         r'\b(?:stor\w*|sequestr\w*|convert\w* [^.;]{0,35}into (?:plant matter|biomass))\b'),
        (('USDA Climate Hubs · Forests and the Carbon Cycle',
          'https://www.climatehubs.usda.gov/hubs/northeast/topic/forests-carbon-cycle-checking-account'),
         ('USDA Climate Hubs · Glossary of Common Forest Carbon Terms',
          'https://www.climatehubs.usda.gov/hubs/northwest/topic/glossary-common-forest-carbon-terms'))),
)
_FORMS = tuple((re.compile(question.form), question) for question in _QUESTIONS)


def science_question(query, language=None):
    if not isinstance(query, str) or len(query) > 145:
        return None
    text = _plain(query).replace('’', "'").strip(' ¿¡?!.')
    return next((question for form, question in _FORMS
                 if (language is None or language == question.language) and form.fullmatch(text)), None)
