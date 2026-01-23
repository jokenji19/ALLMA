from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.label import Label
from kivy.properties import BooleanProperty, StringProperty, ObjectProperty, NumericProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.clock import Clock
from kivy.lang import Builder
from threading import Thread
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.metrics import dp

# Import Theme
from allma_model.ui.theme import Theme
from allma_model.core.allma_core import ALLMACore

# Register Theme for KV
from kivy.factory import Factory
Factory.register('Theme', cls=Theme)

Builder.load_string('''
#:import Theme allma_model.ui.theme.Theme
#:import Factory kivy.factory.Factory

<GradientBackground@Widget>:
    canvas.before:
        Rectangle:
            pos: self.pos
            size: self.size
            texture: Theme.get_vertical_gradient_texture(Theme.bg_start, Theme.bg_end)

<MessageBubble>:
    size_hint_y: None
    height: self.texture_size[1] + 24
    text_size: self.width - 40, None
    padding: 20, 12
    background_color: [0, 0, 0, 0] # Transparent for custom drawing
    # Font Removed to use System Default
    color: Theme.text_light if self.is_user else Theme.text_primary
    canvas.before:
        Color:
            rgba: Theme.bubble_user_bg if self.is_user else Theme.bubble_bot_bg
        RoundedRectangle:
            pos: self.pos
            size: self.size
            # Soft corners: User (Right), Bot (Left)
            radius: [18, 18, 0, 18] if self.is_user else [18, 18, 18, 0]
        # Subtle Shadow
        Color:
            rgba: (0, 0, 0, 0.05) if not self.is_user else (0, 0, 0, 0)
        RoundedRectangle:
            pos: self.pos[0] + 2, self.pos[1] - 2
            size: self.size
            radius: [18, 18, 18, 0]

<SidebarItem@Button>:
    background_color: (0,0,0,0)
    color: Theme.text_primary
    # Font Removed
    font_size: '16sp'
    size_hint_y: None
    height: dp(50)
    text_size: self.width, None
    halign: 'left'
    valign: 'middle'
    padding_x: dp(20)
    canvas.before:
        Color:
            rgba: (0,0,0, 0.05) if self.state == 'down' else (0,0,0,0)
        Rectangle:
            pos: self.pos
            size: self.size

<ChatView>:
    # Main Container
    FloatLayout:
        # Gradient Background
        GradientBackground:
        
        # CHAT AREA (Header + List)
        # We adjust bottom padding or height to accommodate input area + keyboard
        BoxLayout:
            id: chat_container
            orientation: 'vertical'
            pos_hint: {'x': 0, 'top': 1}
            # Height is essentially window height. 
            # We use bottom padding to "push" the list up above the input area.
            # Initial padding_bottom = 80dp (Input) + 0 (Keyboard)
            padding: [0, 0, 0, dp(80)]
            
            # Header
            BoxLayout:
                size_hint_y: None
                height: dp(60)
                padding: dp(15)
                spacing: dp(15)
                canvas.before:
                    Color:
                        rgba: (1, 1, 1, 0.0) 
                    Rectangle:
                        pos: self.pos
                        size: self.size

                # Menu Button
                Button:
                    text: "=" 
                    font_size: '24sp'
                    bold: True
                    size_hint_x: None
                    width: dp(40)
                    background_color: (0,0,0,0)
                    color: Theme.primary
                    on_release: root.toggle_sidebar()

                Label:
                    text: "ALLMA"
                    # Font Removed
                    bold: True
                    font_size: '20sp'
                    color: Theme.primary
                    size_hint_x: None
                    width: self.texture_size[0]
                    halign: 'left'
                
                Widget: # Spacer
                
            # Chat List
            RecycleView:
                id: rv
                scroll_type: ['bars', 'content']
                scroll_wheel_distance: dp(114)
                bar_width: dp(4)
                bar_color: Theme.primary
                bar_inactive_color: (0, 0, 0, 0)
                viewclass: 'MessageBubble'
                # Track scroll position
                on_scroll_y: root.on_scroll(self.scroll_y)
                
                RecycleBoxLayout:
                    default_size: None, dp(56)
                    default_size_hint: 1, None
                    size_hint_y: None
                    height: self.minimum_height
                    orientation: 'vertical'
                    spacing: dp(12)
                    padding: dp(20)

        # INPUT AREA (Detached for Floating Animation)
        BoxLayout:
            id: input_area
            size_hint_y: None
            height: dp(80)
            # Position manually managed (y)
            pos_hint: {'x': 0}
            y: 0 # Start at bottom
            
            padding: [dp(20), dp(10), dp(20), dp(20)]
            spacing: dp(10)
            canvas.before:
                Color:
                    rgba: (1, 1, 1, 0.8) # Glassy white bottom
                Rectangle:
                    pos: self.pos
                    size: self.size
            
            # Input Wrapper
            BoxLayout:
                canvas.before:
                    Color:
                        rgba: Theme.input_border
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [24,]
                    Color:
                        rgba: Theme.input_bg
                    RoundedRectangle:
                        pos: self.x + 1, self.y + 1
                        size: self.width - 2, self.height - 2
                        radius: [23,]
                
                TextInput:
                    id: input_field
                    multiline: False
                    hint_text: "Scrivi un messaggio..."
                    hint_text_color: Theme.text_secondary
                    background_color: (0, 0, 0, 0)
                    foreground_color: Theme.text_primary
                    cursor_color: Theme.primary
                    padding_y: [self.height / 2.0 - (self.line_height / 2.0) * len(self._lines), 0]
                    padding_x: [15, 15]
                    # Font Removed
                    font_size: '16sp'
                    write_tab: False 
                    on_text_validate: root.send_message()

            Button:
                text: ">"
                font_size: '24sp'
                bold: True
                size_hint_x: None
                width: dp(50)
                background_color: (0,0,0,0)
                color: (1,1,1,1)
                on_release: root.send_message()
                canvas.before:
                    Color:
                        rgba: Theme.primary
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [25,] 
        
        # Scroll Down Button
        Button:
            id: scroll_btn
            text: "⬇"
            font_size: '20sp'
            size_hint: None, None
            size: dp(40), dp(40)
            pos_hint: {'right': 0.95, 'y': 0.15}
            background_color: (0, 0, 0, 0)
            opacity: 0
            disabled: True
            on_release: root.scroll_to_bottom(force=True)
            canvas.before:
                Color:
                    rgba: Theme.secondary
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [20,]

        # OVERLAY
        Button:
            id: overlay
            background_color: (0, 0, 0, 0.4)
            pos_hint: {'x': -2, 'y': -2}
            size_hint: (1, 1)
            opacity: 0
            on_release: root.toggle_sidebar()

        # SIDEBAR
        BoxLayout:
            id: sidebar
            orientation: 'vertical'
            size_hint: (None, 1)
            width: dp(280)
            x: -self.width # Start off-screen
            canvas.before:
                Color:
                    rgba: (1, 1, 1, 1) # White bg
                Rectangle:
                    pos: self.pos
                    size: self.size

            # Sidebar Header
            BoxLayout:
                size_hint_y: None
                height: dp(150)
                orientation: 'vertical'
                padding: dp(20)
                spacing: dp(10)
                canvas.before:
                    Color:
                        rgba: Theme.bg_start
                    Rectangle:
                        pos: self.pos
                        size: self.size

                Label:
                    text: "👤" 
                    font_size: '40sp'
                    size_hint: None, None
                    size: dp(60), dp(60)

                Label:
                    text: "Utente"
                    bold: True
                    font_size: '18sp'
                    color: Theme.primary
                    size_hint_y: None
                    height: dp(30)
                    halign: 'left'
                    text_size: self.width, None

            # Menu Items
            BoxLayout:
                orientation: 'vertical'
                padding: dp(0)
                spacing: dp(2)
                
                SidebarItem:
                    text: "💬  Nuova Chat"
                    on_release: root.clear_history()

                SidebarItem:
                    text: "🧠  Memoria (SQL)"

                SidebarItem:
                    text: "⚙️  Impostazioni"

                Widget: 

''')

class MessageBubble(RecycleDataViewBehavior, Label):
    is_user = BooleanProperty(False)
    index = None

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        self.is_user = data.get('is_user', False)
        return super(MessageBubble, self).refresh_view_attrs(rv, index, data)

class ChatView(Screen):
    sidebar_open = BooleanProperty(False)
    is_at_bottom = BooleanProperty(True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.core = None
        self.history = []

    def on_enter(self):
        if not self.core:
            try:
                from allma_model.utils.model_downloader import ModelDownloader
                downloader = ModelDownloader()
                models_dir = downloader.models_dir
                
                self.core = ALLMACore(models_dir=models_dir)
                self.user_id = "user_mobile"
                self.conversation_id = self.core.start_conversation(self.user_id)
                self.add_message("👋 Ciao! Sono ALLMA. Come stai oggi?", False)
            except Exception as e:
                self.add_message(f"Errore inizializzazione core: {e}", False)
        
        Window.bind(on_keyboard_height=self.on_keyboard_height)

    def on_leave(self):
        Window.unbind(on_keyboard_height=self.on_keyboard_height)

    def on_keyboard_height(self, window, height):
        # Determine target Y for input area
        # height is keyboard height in pixels
        
        # We animate the input area moving up
        anim_duration = 0.2
        
        # Input Area Y: simply 'height' (msg bar rides on top of keyboard)
        target_y = height
        
        # Chat Container Padding:
        # Needs to be InputHeight (dp(80) approx 160-200px) + Keyboard Height
        # We need to convert dp(80) to pixels to be precise, usually ~ 2.5/3x on modern phones
        # Using self.ids.input_area.height is reliable
        input_h = self.ids.input_area.height
        target_padding = height + input_h
        
        # Animate Input Area Position
        anim_input = Animation(y=target_y, duration=anim_duration, t='out_cubic')
        anim_input.start(self.ids.input_area)
        
        # Animate Chat Container Padding (Only bottom component)
        # We can't animate list directly, so we use a property or just set it?
        # Animation doesn't support list elements natively easily.
        # But we can animate numeric property if we bound it.
        # For simplicity/robustness, let's just SET padding for now, or use Clock for smooth steps if tricky.
        # Wait, Animation DOES support properties. But 'padding' is ReferenceListProperty.
        # We can try animating `height` of a spacer? No.
        
        # Let's set padding immediately. The input area animation covers the visual transition.
        # If user finds it "janky", we can refine.
        self.ids.chat_container.padding = [0, 0, 0, target_padding]
        
        # Scroll to bottom if opening
        if height > 0:
            Clock.schedule_once(lambda dt: self.scroll_to_bottom(force=True), 0.1)

    def on_scroll(self, scroll_y):
        if scroll_y < 0.05:
            self.is_at_bottom = True
            self.ids.scroll_btn.opacity = 0
            self.ids.scroll_btn.disabled = True
        else:
            self.is_at_bottom = False
            self.ids.scroll_btn.opacity = 1
            self.ids.scroll_btn.disabled = False
    
    def toggle_sidebar(self):
        self.sidebar_open = not self.sidebar_open
        
        target_x = 0 if self.sidebar_open else -self.ids.sidebar.width
        anim = Animation(x=target_x, duration=0.3, t='out_cubic')
        anim.start(self.ids.sidebar)
        
        overlay = self.ids.overlay
        if self.sidebar_open:
            overlay.pos_hint = {'x': 0, 'y': 0}
            anim_overlay = Animation(opacity=1, duration=0.3)
        else:
            anim_overlay = Animation(opacity=0, duration=0.3)
            def on_anim_complete(a, w):
                w.pos_hint = {'x': -2, 'y': -2}
            
            anim_overlay.bind(on_complete=on_anim_complete)
            
        anim_overlay.start(overlay)

        if self.sidebar_open:
             overlay.pos_hint = {'x': 0, 'y': 0}

    def clear_history(self):
        self.history = []
        self.ids.rv.data = []
        self.toggle_sidebar()
        self.add_message("🧹 Chat pulita. Di cosa vuoi parlare?", False)

    def send_message(self):
        text = self.ids.input_field.text.strip()
        if not text:
            return

        self.add_message(text, True)
        self.ids.input_field.text = ""
        Clock.schedule_once(lambda dt: self.add_message("Sto pensando... 💭", False, temp=True), 0.1)
        Thread(target=self._process_message, args=(text,)).start()

    def _process_message(self, text):
        try:
            if self.core:
                result = self.core.process_message(
                    user_id=self.user_id,
                    conversation_id=self.conversation_id,
                    message=text
                )
                response = result.content if hasattr(result, 'content') else str(result)
            else:
                response = "Core non inizializzato."
        except Exception as e:
            response = f"Errore interno: {e}"

        Clock.schedule_once(lambda dt: self._update_response(str(response)))

    def _update_response(self, response_text):
        if self.history and self.history[-1].get('temp', False):
            self.history.pop()
        
        self.history.append({'text': response_text, 'is_user': False})
        self.ids.rv.data = list(self.history)
        self.scroll_to_bottom(force=self.is_at_bottom)

    def add_message(self, text, is_user, temp=False):
        self.history.append({'text': text, 'is_user': is_user, 'temp': temp})
        self.ids.rv.data = list(self.history)
        if is_user:
            self.scroll_to_bottom(force=True)
        else:
            self.scroll_to_bottom(force=self.is_at_bottom)

    def scroll_to_bottom(self, force=False):
        if force:
            # Scroll to 0 (bottom in Kivy ScrollView/RecycleView)
            Clock.schedule_once(lambda dt: setattr(self.ids.rv, 'scroll_y', 0), 0.1)
