"""Core API; load the orchestrator lazily to avoid circular memory imports."""

__all__ = ['ALLMACore']


def __getattr__(name):
    if name == 'ALLMACore':
        from .allma_core import ALLMACore
        return ALLMACore
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
