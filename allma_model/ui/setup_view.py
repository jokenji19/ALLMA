from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.lang import Builder

from allma_model.utils.model_downloader import ModelDownloader

Builder.load_string('''
<SetupView>:
    BoxLayout:
        orientation: 'vertical'
        padding: 50
        spacing: 20
        canvas.before:
            Color:
                rgba: 0.05, 0.05, 0.1, 1
            Rectangle:
                pos: self.pos
                size: self.size

        Label:
            text: "Allma Setup"
            font_size: '24sp'
            size_hint_y: 0.2
            color: 0.8, 0.8, 1, 1

        Label:
            id: status_label
            text: "Checking system requirements..."
            text_size: self.width, None
            halign: 'center'
            valign: 'middle'
            size_hint_y: 0.2
            color: 0.9, 0.9, 0.9, 1

        ProgressBar:
            id: progress_bar
            max: 100
            value: 0
            size_hint_y: None
            height: '20dp'

        Label:
            id: details_label
            text: ""
            font_size: '12sp'
            size_hint_y: 0.6
            color: 0.6, 0.6, 0.6, 1
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
        self.ids.status_label.text = "Verifying AI Models..."
        self.missing_models = self.downloader.check_models_missing()
        
        if not self.missing_models:
            self.finish_setup()
        else:
            self.start_downloads()

    def start_downloads(self):
        count = len(self.missing_models)
        self.ids.status_label.text = f"Downloading {count} AI Model(s)..."
        self.ids.details_label.text = "This may take a while depending on your connection."
        
        # Start background download
        self.downloader.start_background_download(
            self.missing_models, 
            self.update_progress,
            self.on_download_complete
        )

    def update_progress(self, model_key, current, total):
        # Called from thread, must schedule UI update
        Clock.schedule_once(lambda dt: self._update_bar(model_key, current, total))

    def _update_bar(self, model_key, current, total):
        percent = (current / total) * 100 if total > 0 else 0
        self.ids.progress_bar.value = percent
        mb_curr = current / (1024*1024)
        mb_tot = total / (1024*1024)
        self.ids.details_label.text = f"Downloading {model_key}: {mb_curr:.1f}MB / {mb_tot:.1f}MB ({percent:.1f}%)"

    def on_download_complete(self, success, error_msg):
        Clock.schedule_once(lambda dt: self._handle_complete(success, error_msg))

    def _handle_complete(self, success, error_msg):
        if success:
            self.finish_setup()
        else:
            self.ids.status_label.text = "Download Failed"
            self.ids.status_label.color = (1, 0.2, 0.2, 1)
            self.ids.details_label.text = f"Error: {error_msg}\nRestart app to try again."

    def finish_setup(self):
        self.ids.status_label.text = "System Ready."
        self.ids.progress_bar.value = 100
        Clock.schedule_once(lambda dt: self._notify_complete(), 1.0)

    def _notify_complete(self):
        if self.completion_callback:
            self.completion_callback()
