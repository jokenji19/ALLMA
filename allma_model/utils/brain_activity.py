"""Bounded, content-free observation of actual foreground work. No model calls."""
from collections import deque
from copy import deepcopy
from threading import RLock, get_ident
import time

# Positions are an illustrative layout, never a claim about anatomical neurons.
CATALOG = [
    ('input','La tua domanda','Ingresso','Ricezione di un turno di conversazione.',[-.65,.72,.12]),
    ('identity','Identità','Identità','Regole e dati che distinguono ALLMA dall’utente.',[-.72,.25,.1]),
    ('memory','Memoria','Memoria','Ricerca o richiamo di informazioni disponibili.',[-.5,-.2,.5]),
    ('decider','Decider','Direzione','Proposta di un percorso; ALLMA mantiene i controlli.',[0,.55,.28]),
    ('emotion','Emozioni','Emozioni','Analisi delle emozioni espresse, senza attribuire sentimenti reali ad ALLMA.',[.5,.1,.55]),
    ('coalescence','Coalescenza','Evoluzione','Osservazione dell’esperienza per l’evoluzione emotiva progressiva.',[.38,-.38,.4]),
    ('understanding','Comprensione','Linguaggio','Analisi dell’intento e della struttura del messaggio.',[-.35,.5,.48]),
    ('orchestrator','Coordinamento','Direzione','Selezione dei moduli pertinenti nel budget disponibile.',[0,.15,0]),
    ('curiosity','Curiosità','Evoluzione','Valuta possibili spunti; esecuzione non significa domanda aggiunta.',[.62,.55,.05]),
    ('emotional_adaptation','Adattamento emotivo','Emozioni','Adattamento del tono in base ai segnali disponibili.',[.72,.03,-.18]),
    ('creativity','Creatività','Linguaggio','Contributo creativo quando selezionato.',[-.68,.02,-.32]),
    ('planning','Pianificazione','Direzione','Contributo di pianificazione quando pertinente.',[-.24,.74,-.22]),
    ('perception','Percezione','Linguaggio','Adattatore percettivo; nessun output non equivale a visione attiva.',[-.65,-.38,-.12]),
    ('language_processing','Linguaggio','Linguaggio','Analisi linguistica del turno.',[-.75,.44,-.12]),
    ('personality_style','Personalità','Evoluzione','Espressione della personalità: preferenze dichiarate, tendenze apprese e adattamento temporaneo al turno.',[.72,-.3,.02]),
    ('meta_learning','Meta-apprendimento','Evoluzione','Strategie e stile appresi da riscontri attribuiti; le proposte richiedono conferma.',[.4,-.65,.02]),
    ('cognitive_tracking','Tracciamento','Direzione','Stime operative; non misurano intelligenza o coscienza.',[.1,-.58,-.4]),
    ('model','Modello linguistico','Linguaggio','Generazione tramite il modello selezionato; non è la memoria personale.',[0,.13,.65]),
    ('validation','Controlli','Direzione','Verifica di formato, attribuzione, identità e ripetizioni.',[.12,-.2,-.48]),
    ('learning','Apprendimento','Evoluzione','Osservazione di un’interazione; non certifica apprendimento consolidato.',[.4,-.55,-.26]),
    ('storage','Archivio','Memoria','Scrittura di messaggi e metadati nell’archivio conversazionale.',[-.4,-.6,.04]),
    ('tools','Strumenti','Direzione','Risultato prodotto da un percorso nativo, ad esempio un calcolo.',[.43,.47,-.38]),
    ('dreams','Sogni','Memoria','Stato corrente del motore onirico. Le sue fasi interne non vengono ricostruite dalla chat.',[-.25,-.45,-.45]),
    ('output','Risposta','Uscita','Conclusione del turno; eventuali blocchi rimangono distinti dal successo.',[.12,-.78,.1]),
]
IDS = frozenset(row[0] for row in CATALOG)
PHASES = frozenset(('running','completed','no_output','failed','cancelled','not_relevant','disabled','budget_skipped','observed','guidance'))


class BrainActivity:
    def __init__(self):
        self._lock = RLock()
        self._events = deque(maxlen=96)
        self._states = {}
        self._seq = self._turn = 0
        self._owner = None
        self._active = False
        self._last = None
        self._started = None
        self._status = 'idle'

    def begin(self):
        with self._lock:
            self._turn += 1
            self._states = {}
            self._active = True
            self._owner = get_ident()
            self._started = time.monotonic()
            self._last = None
            self._status = 'running'
            self.emit('input','completed')

    def emit(self, module, phase, duration_ms=None):
        with self._lock:
            if not self._active or self._owner != get_ident() or module not in IDS or phase not in PHASES:
                return
            self._seq += 1
            event = {'seq':self._seq, 'turn':self._turn, 'module':module, 'phase':phase,
                     'at_ms':round((time.monotonic()-self._started)*1000,2)}
            if duration_ms is None and phase in ('observed','guidance'):
                duration_ms = self._states.get(module, {}).get('duration_ms')
            if isinstance(duration_ms,(int,float)) and duration_ms >= 0:
                event['duration_ms'] = round(duration_ms,3)
            if self._last and self._last != module and phase in ('running','completed'):
                event['from'] = self._last
            if phase in ('running','completed'):
                self._last = module
            self._states[module] = dict(event)
            self._events.append(event)

    def call(self, module, function, *args, **kwargs):
        if not self._active or self._owner != get_ident():
            return function(*args, **kwargs)
        self.emit(module,'running')
        started = time.monotonic()
        try:
            result = function(*args, **kwargs)
        except BaseException as error:
            from .generation_control import GenerationCancelled
            self.emit(module,'cancelled' if isinstance(error, GenerationCancelled) else 'failed',(time.monotonic()-started)*1000)
            raise
        self.emit(module,'no_output' if result is None else 'completed',(time.monotonic()-started)*1000)
        return result

    def finish(self, status='completed'):
        with self._lock:
            if not self._active or self._owner != get_ident():
                return
            for module, state in list(self._states.items()):
                if state['phase']=='running':
                    self.emit(module,'cancelled' if status=='cancelled' else 'failed')
            self.emit('output',status)
            self._active = False
            self._status = status
            self._owner = None

    def snapshot(self, after=0):
        if type(after) is not int or after < 0:
            after = 0
        with self._lock:
            return deepcopy({'version':1,'seq':self._seq,'turn':self._turn,
                'active':self._active,'status':self._status,
                'nodes':[{'id':key,'label':label,'group':group,'description':desc,'position':pos,
                          'state':self._states.get(key)} for key,label,group,desc,pos in CATALOG],
                'events':[e for e in self._events if e['seq']>after and e['turn']==self._turn],
                'scope':'foreground_observed_work','symbolic_geometry':True})
