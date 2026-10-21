"""Small technical preferences in ALLMA's existing, backed-up module archive."""
from .languages import voice_options


class VoicePreferences:
    KEY = 'voice_preferences_v1'

    def __init__(self, manager=None):
        self.manager = manager
        self.options = voice_options()
        self.writable = True
        if manager:
            try:
                self.options = voice_options(manager.load_state(self.KEY, strict=True))
            except Exception:
                self.writable = False

    def update(self, value):
        options = voice_options(value)
        if not self.writable:
            raise ValueError('Preferenze vocali non leggibili: archivio preservato.')
        if self.manager and not self.manager.save_state(self.KEY, options):
            raise OSError('Impossibile salvare le preferenze vocali.')
        self.options = options
        return dict(options)
