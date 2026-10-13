from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp

from allma_model.utils.model_downloader import ModelDownloader
from allma_model.ui.theme import Theme
from kivy.factory import Factory
Factory.register('Theme', cls=Theme)


class SetupView(Screen):
    from kivy.properties import ObjectProperty
    background_texture = ObjectProperty(None)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from allma_model.ui.cosmic_widgets import StartupPanel
        self.intro = StartupPanel()
        self.add_widget(self.intro)
        self.ids.status_label = self.intro.status_label
        self.ids.details_label = self.intro.details_label
        self.ids.progress_bar = self.intro.progress_bar
        self.downloader = ModelDownloader()
        self.missing_models = []
        self.completion_callback = None
        self.tick = 0
        self._downloading = False
        self._heartbeat_event = None

    def set_callback(self, callback):
        self.completion_callback = callback

    def on_enter(self):
        # Start check on enter
        Clock.schedule_once(self.check_requirements, 0.5)
        self.intro.set_stage('Verifico il modello…','Controllo che i componenti siano pronti.',0)

    def on_leave(self):
        self.intro.stop()
        if self._heartbeat_event is not None:
            self._heartbeat_event.cancel()
            self._heartbeat_event = None

    def _heartbeat(self, dt):
        self.tick += 1
        dots = "." * (self.tick % 4)
        current = self.ids.status_label.text
        if "SCARICO" in current:
             # Just keep dots active
             pass

    def check_requirements(self, dt):
        if getattr(self, '_checking', False) or self._downloading:
            return
        self._checking = True
        self.intro.set_stage("Verifico il modello…","Controllo i file già presenti sul dispositivo.",0)
        # Hashing a large GGUF must not block Kivy's UI thread.
        from threading import Thread
        def check():
            try:
                missing = self.downloader.check_models_missing()
                error = None
            except Exception as exc:
                missing, error = [], str(exc)
            def apply(dt):
                self._checking = False
                if error:
                    self.intro.stop()
                    self.ids.status_label.text = "Verifica non riuscita"
                    self.ids.details_label.text = error
                    return
                self.missing_models = missing
                if missing:
                    self.start_downloads()
                else:
                    self.finish_setup()
            Clock.schedule_once(apply)
        Thread(target=check, daemon=True, name='ModelVerification').start()

    def start_downloads(self):
        if self._downloading:
            return
        self._downloading = True
        self.intro.stop()
        count = len(self.missing_models)
        self.ids.status_label.text = f"Preparo {count} componenti"
        self.ids.details_label.text = "Download in corso. Mantieni ALLMA aperta."
        self.show_toast("Download avviato")
        
        # Start background download
        self.downloader.start_background_download(
            self.missing_models, 
            self.update_progress,
            self.on_download_complete,
            self.on_single_model_downloaded
        )

    def on_single_model_downloaded(self, model_key):
        # Called from background thread
        Clock.schedule_once(lambda dt: self.show_toast(f"Modulo {model_key} Pronta per parlare!"))

    def show_toast(self, text):
        from kivy.utils import platform
        if platform == 'android':
            try:
                from jnius import autoclass, cast
                from android.runnable import run_on_ui_thread
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                JString = autoclass('java.lang.String')
                Toast = autoclass('android.widget.Toast')
                context =  PythonActivity.mActivity

                @run_on_ui_thread
                def _toast_ui(t_text):
                    Toast.makeText(context, cast('java.lang.CharSequence', JString(t_text)), Toast.LENGTH_SHORT).show()

                _toast_ui(text)
            except Exception as e:
                print(f"Toast Error: {e}")
        else:
            print(f"[TOAST] {text}")

    def update_progress(self, model_key, current, total):
        # Called from thread, must schedule UI update
        Clock.schedule_once(lambda dt: self._update_bar(model_key, current, total))

    def _update_bar(self, model_key, current, total):
        percent = (current / total) * 100 if total > 0 else 0
        self.ids.progress_bar.indeterminate = total <= 0
        self.ids.progress_bar.value = percent
        mb_curr = current / (1024*1024)
        mb_tot = total / (1024*1024)
        self.ids.details_label.text = f"{model_key}\n{mb_curr:.0f}MB / {mb_tot:.0f}MB ({percent:.0f}%)"
        
        # Pulse the status label to show activity
        self.ids.status_label.text = f"Download al {percent:.0f}%"

    def on_download_complete(self, success, error_msg):
        Clock.schedule_once(lambda dt: self._handle_complete(success, error_msg))

    def _handle_complete(self, success, error_msg):
        self._downloading = False
        if success:
            self.finish_setup()
        else:
            self.intro.stop()
            self.ids.status_label.text = "Download non riuscito"
            self.ids.status_label.color = (1, 0, 0, 1)
            self.ids.details_label.text = f"{error_msg}"
            self.show_toast("Errore Download!")

    def finish_setup(self):
        self.intro.set_stage("Modello verificato","Ora preparo il modello e la memoria.",1,busy=False)
        Clock.schedule_once(lambda dt: self._notify_complete(), 0)

    def _notify_complete(self):
        if self.completion_callback:
            self.completion_callback()
