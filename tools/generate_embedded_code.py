import os
import zipfile
import base64
import sys

def generate_embedded():
    source_dir = 'allma_model' # Changed from libs/Model
    zip_filename = 'temp_brain.zip'
    
    print(f"Zipping {source_dir}...")
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')
            
            for file in files:
                if file.endswith('.py') or file.endswith('.json') or file.endswith('.kv'):
                    file_path = os.path.join(root, file)
                    # Archive structure: allma_model/...
                    arcname = os.path.join('allma_model', os.path.relpath(file_path, source_dir))
                    zf.write(file_path, arcname)
                    # print(f"Adding: {arcname}")

    # Read and encode
    with open(zip_filename, 'rb') as f:
        data = f.read()
    
    b64_str = base64.b64encode(data).decode('utf-8')
    print(f"Blob Size: {len(data)/1024:.2f} KB")
    
    # Prepare main.py content
    header = f"""import base64
import os
import sys
import threading
import time
import zipfile
import shutil
import logging
import traceback

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.core.window import Window

# ALLMA BRAIN BLOB (Build 154)
ZIP_DATA = "{b64_str}"
"""

    # Read the footer code from reconstruct_main.py to ensure consistency
    # Or strict hardcoding here to be safe.
    # Let's use the current footer logic which is proven.
    
    footer = r"""
# --- EXECUTION LOGIC ---

class SetupScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=[50, 100, 50, 100], spacing=20)
        
        # Try to load logo if available
        if os.path.exists('logo.png'):
            try:
                img = Image(source='logo.png', size_hint=(1, 0.4), allow_stretch=True, keep_ratio=True)
                layout.add_widget(img)
            except:
                pass
                
        self.label = Label(text="Initializing ALLMA Systems...", font_size='20sp', halign='center', valign='middle')
        self.label.bind(size=self.label.setter('text_size'))
        
        self.progress = ProgressBar(max=100, size_hint_y=None, height=20)
        
        layout.add_widget(self.label)
        layout.add_widget(self.progress)
        self.add_widget(layout)

    def on_enter(self):
        Clock.schedule_once(lambda dt: threading.Thread(target=self.extract_and_run).start(), 0.5)

    def extract_and_run(self):
        try:
            self.update_status("Decrypting Neural Core...", 10)
            if not ZIP_DATA:
                raise ValueError("ZIP_DATA is empty!")
                
            data = base64.b64decode(ZIP_DATA)
            
            self.update_status("Allocating Memory Space...", 30)
            app = App.get_running_app()
            data_dir = getattr(app, 'user_data_dir', '.')
            
            # Debug override
            if os.path.exists('unpacked_brain'):
                extract_path = os.path.abspath('unpacked_brain')
            else:
                extract_path = os.path.join(data_dir, 'allma_brain_v154')
            
            # Clean old versions
            if os.path.exists(extract_path):
                try:
                    shutil.rmtree(extract_path)
                except:
                    pass
            
            os.makedirs(extract_path, exist_ok=True)
            
            self.update_status("Deploying Cognitive Modules...", 50)
            zip_path = os.path.join(extract_path, 'brain.zip')
            
            with open(zip_path, 'wb') as f:
                f.write(data)
                
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_path)
                
            self.update_status("Synapsing Neural Network...", 80)
            
            if extract_path not in sys.path:
                sys.path.insert(0, extract_path)
            
            # Verify module exists
            if not os.path.exists(os.path.join(extract_path, 'allma_model')):
                 raise ImportError(f"allma_model not found in {extract_path}")

            # Import the actual app module
            try:
                from allma_model.ui.app_entry import AllmaInternalApp
                self.update_status("Launching Core System...", 100)
                
                # Switch to the internal app
                Clock.schedule_once(lambda dt: self.switch_to_internal_app(AllmaInternalApp))
            except ImportError as e:
                self.show_error(f"Internal App Not Found: {e}")
            
        except Exception as e:
            err = traceback.format_exc()
            logging.error(err)
            print(err)
            Clock.schedule_once(lambda dt: self.show_error(str(e)))

    def update_status(self, text, val):
        Clock.schedule_once(lambda dt: self._update_ui(text, val))

    def _update_ui(self, text, val):
        self.label.text = text
        self.progress.value = val

    def show_error(self, err):
        self.label.text = f"CRITICAL ERROR:\n{err}"
        self.label.color = (1, 0.3, 0.3, 1)

    def switch_to_internal_app(self, InternalAppClass):
        # Instantiate the internal app to get its build result
        try:
            app_instance = InternalAppClass()
            new_root = app_instance.build()
            
            # Get the current running app (The Installer)
            current_app = App.get_running_app()
            
            # Clear current screen and set new root
            Window.remove_widget(current_app.root)
            Window.add_widget(new_root)
            current_app.root = new_root
        except Exception as e:
           self.show_error(f"App Launch Failed: {e}")

class AllmaApp(App):
    def build(self):
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(SetupScreen(name='setup'))
        return sm

if __name__ == '__main__':
    try:
        AllmaApp().run()
    except Exception as e:
        with open('crash.log', 'w') as f:
            f.write(traceback.format_exc())
        print(traceback.format_exc())
"""

    with open('main.py', 'w') as f:
        f.write(header + footer)
    
    os.remove(zip_filename)
    print("Successfully regenerated main.py with Build 154 code.")

if __name__ == '__main__':
    generate_embedded()
