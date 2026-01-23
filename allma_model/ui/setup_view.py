from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.lang import Builder

from allma_model.utils.model_downloader import ModelDownloader
from allma_model.ui.theme import Theme
# Register Theme in Factory for KV access if not already (safeguard)
from kivy.factory import Factory
Factory.register('Theme', cls=Theme)

Builder.load_string('''
#:import Theme allma_model.ui.theme.Theme

<SetupView>:
    # Main Gradient Background
    canvas.before:
        Rectangle:
            pos: self.pos
            size: self.size
            texture: Theme.get_vertical_gradient_texture(Theme.bg_start, Theme.bg_end)

    BoxLayout:
        orientation: 'vertical'
        padding: dp(40)
        spacing: dp(30)
        
        # Spacer
        Widget:
            size_hint_y: 0.3

        # Modern Card-like grouping (Visual only)
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            spacing: dp(15)
            
            Label:
                text: "✨ ALLMA"
                font_name: 'Roboto'
                font_size: '32sp'
                bold: True
                color: Theme.primary
                size_hint_y: None
                height: dp(50)
                halign: 'center'

            Label:
                id: status_label
                text: "Verifico i requisiti..."
                font_name: 'Roboto'
                font_size: '16sp'
                text_size: self.width, None
                halign: 'center'
                color: Theme.text_secondary
                size_hint_y: None
                height: dp(30)

            # Custom Progress Bar styling is hard in pure Kivy without KivyMD
            # We stick to default but placed nicely
            ProgressBar:
                id: progress_bar
                max: 100
                value: 0
                size_hint_y: None
                height: dp(10)
                # Kivy standard progress bar is usually blue, might clash if lucky
            
            Label:
                id: details_label
                text: ""
                font_name: 'Roboto'
                font_size: '12sp'
                halign: 'center'
                color: Theme.text_secondary
                size_hint_y: None
                height: dp(20)

        # Spacer to push up
        Widget:

''')

class SetupView(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.downloader = ModelDownloader()
        self.missing_models = []
        self.completion_callback = None

    def set_callback(self, callback):
        self.completion_callback = callback

    def on_enter(self):
        # Start check on enter
        Clock.schedule_once(self.check_requirements, 0.5)

    def check_requirements(self, dt):
        self.ids.status_label.text = "Controllo Modelli AI..."
        self.missing_models = self.downloader.check_models_missing()
        
        if not self.missing_models:
            self.finish_setup()
        else:
            self.start_downloads()

    def start_downloads(self):
        count = len(self.missing_models)
        self.ids.status_label.text = f"Scarico {count} Moduli AI..."
        self.ids.details_label.text = "Potrebbe volerci un po', resta con me."
        
        # Start background download
        self.downloader.start_background_download(
            self.missing_models, 
            self.update_progress,
            self.on_download_complete,
            self.on_single_model_downloaded
        )

    def on_single_model_downloaded(self, model_key):
        # Called from background thread
        Clock.schedule_once(lambda dt: self.show_toast(f"Modulo {model_key} acquisito!"))

    def show_toast(self, text):
        from kivy.utils import platform
        if platform == 'android':
            from jnius import autoclass, cast
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            JString = autoclass('java.lang.String')
            Toast = autoclass('android.widget.Toast')
            context =  PythonActivity.mActivity
            Toast.makeText(context, cast('java.lang.CharSequence', JString(text)), Toast.LENGTH_LONG).show()
        else:
            print(f"[TOAST] {text}")

    def update_progress(self, model_key, current, total):
        # Called from thread, must schedule UI update
        Clock.schedule_once(lambda dt: self._update_bar(model_key, current, total))

    def _update_bar(self, model_key, current, total):
        percent = (current / total) * 100 if total > 0 else 0
        self.ids.progress_bar.value = percent
        mb_curr = current / (1024*1024)
        mb_tot = total / (1024*1024)
        self.ids.details_label.text = f"{model_key}: {mb_curr:.1f}MB / {mb_tot:.1f}MB ({percent:.1f}%)"

    def on_download_complete(self, success, error_msg):
        Clock.schedule_once(lambda dt: self._handle_complete(success, error_msg))

    def _handle_complete(self, success, error_msg):
        if success:
            self.finish_setup()
        else:
            self.ids.status_label.text = "Download Fallito"
            self.ids.status_label.color = (1, 0.2, 0.2, 1)
            self.ids.details_label.text = f"Errore: {error_msg}\nRiavvia l'app."

    def finish_setup(self):
        self.ids.status_label.text = "Tutto Pronto."
        self.ids.progress_bar.value = 100
        Clock.schedule_once(lambda dt: self._notify_complete(), 1.0)

    def _notify_complete(self):
        if self.completion_callback:
            self.completion_callback()
