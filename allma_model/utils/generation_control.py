"""Cancellation shared by the core, model wrapper and chat controller."""


class GenerationCancelled(Exception):
    """The caller cancelled this turn; partial output must not be learned."""


def check_cancelled(event):
    if event is not None and event.is_set():
        raise GenerationCancelled('Generazione interrotta')
