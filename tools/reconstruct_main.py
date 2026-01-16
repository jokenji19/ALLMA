
import os

MAIN_PATH = 'main.py'

FOOTER_CODE = r"""

# --- RECONSTRUCTED LOGIC ---

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
        self.label.bind(size=self.label.setter('text_size')) # Text wrapping
        
        self.progress = ProgressBar(max=100, size_hint_y=None, height=20)
        
        layout.add_widget(self.label)
        layout.add_widget(self.progress)
        self.add_widget(layout)

    def on_enter(self):
        # Delay slightly to allow UI to render first frame
        Clock.schedule_once(lambda dt: threading.Thread(target=self.extract_and_run).start(), 0.5)

    def extract_and_run(self):
        try:
            self.update_status("Decrypting Neural Core...", 10)
            if not ZIP_DATA:
                raise ValueError("ZIP_DATA is empty!")
                
            data = base64.b64decode(ZIP_DATA)
            
            self.update_status("Allocating Memory Space...", 30)
            # Determine Extraction Path
            # On Android, user_data_dir is correct. On Desktop, use local 'unpacked_brain' or similar for debug
            app = App.get_running_app()
            data_dir = getattr(app, 'user_data_dir', '.')
            
            # Debug override
            if os.path.exists('unpacked_brain'):
                extract_path = os.path.abspath('unpacked_brain')
            else:
                extract_path = os.path.join(data_dir, 'allma_brain_v153')
            
            if os.path.exists(extract_path):
                try:
                    shutil.rmtree(extract_path)
                except:
                    pass # Might fail if in use, but we try
            
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
            
            # Try to identify the entry point dynamically if possible, or hardcode known structure
            # Structure: allma_model/
            self.update_status("Booting Consciousness...", 90)
            
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
            print(err) # For logcat
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
        app_instance = InternalAppClass()
        new_root = app_instance.build()
        
        # Get the current running app (The Installer)
        current_app = App.get_running_app()
        
        # Clear current screen and set new root
        from kivy.core.window import Window
        Window.remove_widget(current_app.root)
        Window.add_widget(new_root)
        current_app.root = new_root

class AllmaApp(App):
    def build(self):
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(SetupScreen(name='setup'))
        return sm

if __name__ == '__main__':
    try:
        AllmaApp().run()
    except Exception as e:
        # Emergency logging
        with open('crash.log', 'w') as f:
            f.write(traceback.format_exc())
        print(traceback.format_exc())
"""

def reconstruct():
    if not os.path.exists(MAIN_PATH):
        print(f"Error: {MAIN_PATH} does not exist.")
        return

    with open(MAIN_PATH, 'rb') as f:
        content = f.read()
    
    # Check if we already have the footer to avoid double appending
    if b'class SetupScreen(Screen):' in content:
        print("Logic mostly present. Checking if truncated.")
        if not content.strip().endswith(b'AllmaApp().run()\n    except Exception as e:\n        print(traceback.format_exc())'):
             # It might be present but modified? Or truncated inside.
             # Ideally we check the length or signature.
             pass
    
    # Check if ends with ZIP_DATA line (approximately)
    # The blob is huge, so we check the start of the last line?
    # Or just check if 'if __name__' is missing.
    
    encoded_footer = FOOTER_CODE.encode('utf-8')
    
    if b'if __name__ == ' not in content:
        print("Appending missing execution logic...")
        with open(MAIN_PATH, 'ab') as f:
            f.write(encoded_footer)
        print("Success: Appended logic to main.py")
    else:
        print("Info: execution block detected. No changes made.")

if __name__ == '__main__':
    reconstruct()
