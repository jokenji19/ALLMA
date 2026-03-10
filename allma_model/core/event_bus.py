"""
EventBus — ALLMA V6 Sprint 2

Un bus di messaggi asincrono Pub/Sub basato su asyncio.Queue.

Scopo:
    Disaccoppiare il Subconscio (Soul, Dream, Proactive) dal Core LLM.
    I moduli in background pubblicano eventi sul bus senza chiamare
    allma_core direttamente. Il Core li consuma quando è libero.

Architettura:
    Producers → publish(event)  → asyncio.Queue
    Consumer  → subscribe(loop) → processa eventi in sicurezza

Tipi di eventi:
    'proactive_message'  → ProactiveAgency vuole inviare un messaggio all'utente
    'dream_insight'      → DreamManager ha elaborato un insight da condividere
    'soul_state_change'  → SoulCore ha subito una variazione di stato significativa
"""

from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable, Awaitable
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class BusEvent:
    """Un evento sul bus. Leggero e serializzabile."""
    event_type: str           # es. 'proactive_message', 'dream_insight'
    payload: Dict[str, Any]  # Dati specifici dell'evento
    source: str               # Chi lo ha pubblicato (es. 'dream_manager')
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 5         # 1 (alta) → 10 (bassa)


class EventBus:
    """
    Bus Pub/Sub asincrono per la comunicazione Subconscio ↔ Core.

    Usage (producer):
        bus = EventBus.get_instance()
        await bus.publish(BusEvent('proactive_message', {'text': '...'}, 'proactive_agency'))

    Usage (consumer — tipicamente allma_core):
        async def _handle_event(event: BusEvent):
            if event.event_type == 'proactive_message':
                self.output_callback(event.payload['text'])

        bus.register_consumer(_handle_event)
        # Il loop di consumo gira automaticamente nell'async loop del Core
    """

    _instance: Optional['EventBus'] = None

    def __init__(self, maxsize: int = 50):
        """
        Args:
            maxsize: Numero massimo di eventi in coda. Se piena, publish() dropppa
                     eventi a bassa priorità invece di bloccare il producer.
        """
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._consumer: Optional[Callable[[BusEvent], Awaitable[None]]] = None
        self._running = False
        self._dropped = 0

    @classmethod
    def get_instance(cls) -> 'EventBus':
        """Singleton thread-safe (da usare fuori dal loop async)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_consumer(self, handler: Callable[[BusEvent], Awaitable[None]]):
        """
        Registra la coroutine che consumerà gli eventi.
        Tipicamente chiamata da allma_core dopo aver avviato il suo async loop.
        """
        self._consumer = handler
        logger.info("[EventBus] Consumer registered.")

    async def publish(self, event: BusEvent) -> bool:
        """
        Pubblica un evento sul bus in modo non bloccante.
        Se la coda è piena, droppa l'evento e logga un warning.

        Returns:
            True se l'evento è stato accodato, False se droppato.
        """
        if self._queue.full():
            self._dropped += 1
            logger.warning(
                f"[EventBus] Queue full! Dropping event '{event.event_type}' "
                f"from '{event.source}'. Total dropped: {self._dropped}"
            )
            return False

        await self._queue.put(event)
        logger.debug(f"[EventBus] Event published: {event.event_type} from {event.source}")
        return True

    def publish_sync(self, event: BusEvent) -> bool:
        """
        Versione sincrona di publish per producers fuori da un loop asyncio
        (es. DreamManager in un thread separato).
        """
        try:
            self._queue.put_nowait(event)
            logger.debug(f"[EventBus] Sync event published: {event.event_type}")
            return True
        except asyncio.QueueFull:
            self._dropped += 1
            logger.warning(
                f"[EventBus] Queue full (sync)! Dropping '{event.event_type}'. "
                f"Total dropped: {self._dropped}"
            )
            return False

    async def consume_loop(self):
        """
        Coroutine da avviare nel loop asincrono del Core.
        Consuma eventi dalla coda e li passa al consumer registrato.
        Si ferma automaticamente se non c'è un consumer registrato.
        """
        self._running = True
        logger.info("[EventBus] Consume loop started.")

        while self._running:
            try:
                # Attendi un evento con timeout per non bloccare il loop
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)

                if self._consumer:
                    try:
                        await self._consumer(event)
                    except Exception as e:
                        logger.error(
                            f"[EventBus] Consumer error handling '{event.event_type}': {e}",
                            exc_info=True
                        )
                    finally:
                        self._queue.task_done()
                else:
                    # Nessun consumer: rimetti in coda o droppa
                    logger.warning(f"[EventBus] No consumer for event: {event.event_type}")
                    self._queue.task_done()

            except asyncio.TimeoutError:
                # Normale: nessun evento in questo secondo, continua il loop
                continue
            except Exception as e:
                logger.error(f"[EventBus] Unexpected error in consume loop: {e}", exc_info=True)

    def stop(self):
        """Ferma il consume loop al prossimo ciclo."""
        self._running = False
        logger.info("[EventBus] Stopping consume loop.")

    def get_stats(self) -> Dict[str, Any]:
        """Statistiche diagnostiche del bus."""
        return {
            "queue_size": self._queue.qsize(),
            "events_dropped": self._dropped,
            "consumer_registered": self._consumer is not None,
            "running": self._running,
        }
