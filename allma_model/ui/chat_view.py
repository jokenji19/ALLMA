from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDIconButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineIconListItem, IconLeftWidget, MDList
from kivymd.uix.navigationdrawer import MDNavigationLayout, MDNavigationDrawer
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.recycleview import MDRecycleView
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

<MessageBubble>:
    orientation: 'vertical'
    size_hint_y: None
    height: self.minimum_height
    padding: [dp(10), dp(5)]
    spacing: dp(2)
    adaptive_height: True
    
    # Thought Section
    MDBoxLayout:
        orientation: 'vertical'
        adaptive_height: True
        size_hint_y: None
        height: self.minimum_height if root.thought_text else 0
        opacity: 1 if root.thought_text else 0
        padding: [dp(20), 0, 0, dp(5)]
        
        MDIconButton:
            icon: "thought-bubble-outline" if not root.thought_visible else "thought-bubble"
            theme_text_color: "Custom"
            text_color: (0.5, 0.5, 0.5, 1)
            on_release: root.toggle_thought()
            size_hint: None, None
            size: dp(30), dp(30)
            user_font_size: "20sp"
            pos_hint: {'left': 1}
            opacity: 1 if root.thought_text else 0

        MDLabel:
            text: root.thought_text
            adaptive_height: True
            opacity: 1 if root.thought_visible else 0
            size_hint_y: None
            height: self.texture_size[1] if root.thought_visible else 0
            color: (0.4, 0.4, 0.4, 1)
            font_style: "Caption"
            italic: True
            padding: [dp(5), dp(5)]
            text_size: root.width * 0.85, None

    # Message Bubble
    AnchorLayout:
        anchor_x: 'right' if root.is_user else 'left'
        size_hint_y: None
        height: card.height
        
        MDCard:
            id: card
            size_hint: None, None
            size: lbl.size[0] + dp(30), lbl.size[1] + dp(20)
            radius: [dp(20), dp(20), dp(5), dp(20)] if root.is_user else [dp(20), dp(20), dp(20), dp(5)]
            md_bg_color: (0.2, 0.6, 1, 0.9) if root.is_user else (0.92, 0.92, 0.93, 1)
            elevation: 0
            padding: dp(15)
            
            Label:
                id: lbl
                text: root.text
                size_hint: None, None
                text_size: (root.width * 0.75, None)
                size: self.texture_size
                color: (1, 1, 1, 1) if root.is_user else (0.1, 0.1, 0.1, 1)
                font_size: '16sp'
                valign: 'middle'
                halign: 'left'

<ChatView>:
    MDNavigationLayout:
        
        # Main Screen Content Wrapper
        MDScreenManager:
            MDScreen:
                # Main Chat Interface
                MDBoxLayout:
                    orientation: 'vertical'
                    md_bg_color: (0.98, 0.98, 0.99, 1)
                    
                    # Header
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(70)
                        padding: [dp(20), dp(10)]
                        md_bg_color: (1, 1, 1, 0)
                        
                        MDIconButton:
                            icon: "menu"
                            theme_text_color: "Custom"
                            text_color: (0.2, 0.2, 0.2, 1)
                            on_release: root.toggle_sidebar()
                            pos_hint: {'center_y': 0.5}

                        MDLabel:
                            text: "ALLMA"
                            bold: True
                            font_style: "H5"
                            theme_text_color: "Custom"
                            text_color: (0.1, 0.1, 0.1, 1) 
                            pos_hint: {'center_y': 0.5}
                            halign: 'center'
                            size_hint_x: 1
                        
                        Widget:
                            size_hint_x: None
                            width: dp(48)
                    
                    # Chat Area
                    ScrollView:
                        id: scroll_view
                        scroll_type: ['bars', 'content']
                        scroll_wheel_distance: dp(114)
                        bar_width: dp(0)
                        on_scroll_y: root.on_scroll(self.scroll_y)
                        
                        MDBoxLayout:
                            id: chat_list
                            orientation: 'vertical'
                            adaptive_height: True
                            padding: [dp(20), dp(10), dp(20), dp(20)]
                            spacing: dp(18)

                    # Input Area
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(90)
                        padding: [dp(15), dp(10), dp(15), dp(15)]
                        md_bg_color: (0,0,0,0)
                        
                        MDCard:
                            radius: [dp(25),] 
                            md_bg_color: (1, 1, 1, 1)
                            elevation: 4
                            shadow_softness: 8
                            shadow_offset: (0, 2)
                            padding: [dp(15), dp(5), dp(5), dp(5)]
                            
                            MDTextField:
                                id: input_field
                                hint_text: "Scrivi..."
                                mode: "line"
                                # Set line colors to White (same as card) to hide them
                                line_color_normal: (1, 1, 1, 1)
                                line_color_focus: (1, 1, 1, 1)
                                text_color_normal: (0.2, 0.2, 0.2, 1)
                                hint_text_color_normal: (0.6, 0.6, 0.6, 1)
                                multiline: False
                                on_text_validate: root.send_message()
                                size_hint_x: 1
                                pos_hint: {'center_y': 0.5}
                                font_size: '16sp'

                            MDIconButton:
                                icon: "arrow-up-circle"
                                theme_text_color: "Custom"
                                text_color: (0.2, 0.6, 1, 1)
                                user_font_size: "36sp"
                                on_release: root.send_message()
                                pos_hint: {'center_y': 0.5}
                
                # Scroll FAB Overlay
                MDFloatLayout:
                    size_hint: None, None
                    size: 0, 0 
                    
                    MDIconButton:
                        id: scroll_btn
                        icon: "arrow-down-drop-circle"
                        user_font_size: "40sp"
                        theme_text_color: "Custom"
                        text_color: (0.5, 0.5, 0.5, 0.8)
                        pos_hint: {'right': 0.95, 'y': 0.15}
                        opacity: 0
                        disabled: True
                        on_release: root.scroll_to_bottom(force=True)

        # Native Sidebar Drawer
        MDNavigationDrawer:
            id: nav_drawer
            radius: (0, dp(16), dp(16), 0)
            
            MDBoxLayout:
                orientation: 'vertical'
                padding: 0
                spacing: 0
                
                # Drawer Header
                MDBoxLayout:
                    size_hint_y: None
                    height: dp(180)
                    orientation: 'vertical'
                    padding: dp(24)
                    md_bg_color: app.theme_cls.primary_color
                    
                    MDIcon:
                        icon: "account-circle"
                        font_size: dp(64)
                        theme_text_color: "Custom"
                        text_color: (1, 1, 1, 1)
                    
                    MDLabel:
                        text: "Utente"
                        font_style: "H5"
                        theme_text_color: "Custom"
                        text_color: (1, 1, 1, 1)
                        size_hint_y: None
                        height: self.texture_size[1]
                    
                    MDLabel:
                        text: "Allma Core v0.3"
                        font_style: "Caption"
                        theme_text_color: "Custom"
                        text_color: (1, 1, 1, 0.7)
                
                # Menu Items
                MDScrollView:
                    MDList:
                        OneLineIconListItem:
                            text: "Nuova Chat"
                            on_release: root.clear_history()
                            IconLeftWidget:
                                icon: "message-plus"
                        
                        OneLineIconListItem:
                            text: "La mia Memoria"
                            on_release: root.show_memory()
                            IconLeftWidget:
                                icon: "brain"
                                
                        OneLineIconListItem:
                            text: "Impostazioni"
                            on_release: root.show_settings()
                            IconLeftWidget:
                                icon: "cog"
                
''')

class MessageBubble(MDBoxLayout):
    text = StringProperty("")
    thought_text = StringProperty("")
    is_user = BooleanProperty(False)
    thought_visible = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = kwargs.get('text', '')
        self.is_user = kwargs.get('is_user', False)
        self.thought_text = kwargs.get('thought_text', '')
        self.thought_visible = kwargs.get('thought_visible', False)

    def toggle_thought(self):
        self.thought_visible = not self.thought_visible

class ChatView(MDScreen):
    sidebar_open = BooleanProperty(False)
    is_at_bottom = BooleanProperty(True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.core = None
        self.history = []
        self.dialog = None

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
        if height > 0:
            Clock.schedule_once(lambda dt: self.scroll_to_bottom(force=True), 0.2)

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
        self.ids.nav_drawer.set_state("toggle")

    def show_memory(self):
        """Show accumulated memory in a dialog"""
        if self.ids.nav_drawer.state == "open":
            self.ids.nav_drawer.set_state("close")
            
        memory_text = "Nessun ricordo trovato..."
        
        if self.core and hasattr(self.core, 'incremental_learner'):
            facts = []
            kb = self.core.incremental_learner.knowledge_base
            for topic, units in kb.items():
                if units:
                    latest = units[-1]
                    facts.append(f"• [b]{topic.upper()}[/b]: {latest.content[:60]}...")
            
            if facts:
                memory_text = "\n\n".join(facts)
        
        self.dialog = MDDialog(
            title="🧠 Memoria di ALLMA",
            text=memory_text,
            radius=[20, 20, 20, 20],
            buttons=[
                MDFlatButton(
                    text="CHIUDI",
                    theme_text_color="Custom",
                    text_color=self.theme_cls.primary_color,
                    on_release=lambda x: self.dialog.dismiss()
                )
            ],
        )
        self.dialog.open()

    def show_settings(self):
        """Show settings dialog"""
        if self.ids.nav_drawer.state == "open":
            self.ids.nav_drawer.set_state("close")

        # Basic Info
        version = "v0.3.1 (Mobile)"
        model_name = "Gemma 2 2B (4-bit)"
        
        # Prepare content
        content = MDList()
        
        # Info Item
        item_info = OneLineIconListItem(text=f"ALLMA {version}")
        item_info.add_widget(IconLeftWidget(icon="information"))
        content.add_widget(item_info)

        item_model = OneLineIconListItem(text=f"Modello: {model_name}")
        item_model.add_widget(IconLeftWidget(icon="robot"))
        content.add_widget(item_model)

        # Clear Memory Item
        item_clear = OneLineIconListItem(text="Elimina Tutta la Memoria", on_release=self.clear_all_memory)
        item_clear.add_widget(IconLeftWidget(icon="delete-forever", theme_text_color="Custom", text_color=(1, 0, 0, 1)))
        content.add_widget(item_clear)

        self.dialog = MDDialog(
            title="⚙️ Impostazioni",
            type="custom",
            content_cls=content,
            radius=[20, 20, 20, 20],
            buttons=[
                MDFlatButton(
                    text="CHIUDI",
                    theme_text_color="Custom",
                    text_color=self.theme_cls.primary_color,
                    on_release=lambda x: self.dialog.dismiss()
                )
            ],
        )
        self.dialog.open()

    def clear_all_memory(self, *args):
        """Clear all memory databases"""
        self.dialog.dismiss()
        
        # Confirmation Dialog
        self.dialog = MDDialog(
            title="⚠️ Sei sicuro?",
            text="Questa azione eliminerà tutti i ricordi e le conoscenze apprese da ALLMA. Non si può annullare.",
            radius=[20, 20, 20, 20],
            buttons=[
                MDFlatButton(
                    text="ANNULLA",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDFlatButton(
                    text="ELIMINA TUTTO",
                    theme_text_color="Custom",
                    text_color=(1, 0, 0, 1),
                    on_release=self._perform_memory_wipe
                )
            ]
        )
        self.dialog.open()

    def _perform_memory_wipe(self, *args):
        self.dialog.dismiss()
        try:
            if self.core:
                # 1. Clear SQL Knowledge
                import sqlite3
                if hasattr(self.core, 'knowledge_memory') and self.core.knowledge_memory:
                    with sqlite3.connect(self.core.knowledge_memory.db_path) as conn:
                        conn.execute("DELETE FROM knowledge")
                        conn.commit()
                
                # 2. Clear Runtime Knowledge
                if hasattr(self.core, 'incremental_learner'):
                    self.core.incremental_learner.knowledge_base.clear()
                    self.core.incremental_learner.knowledge_states.clear()
                
                # 3. Clear History
                self.history = []
                self.ids.rv.data = []
                
                self.add_message("🗑️ Memoria completamente formattata. Sono come nuova.", False)
        except Exception as e:
            self.add_message(f"Errore durante la pulizia: {e}", False)

    def clear_history(self):
        self.history = []
        self.ids.chat_list.clear_widgets()
        self.add_message("🧹 Chat pulita. Di cosa vuoi parlare?", False)
        if self.ids.nav_drawer.state == "open":
            self.ids.nav_drawer.set_state("close")

    def send_message(self):
        text = self.ids.input_field.text.strip()
        if not text:
            return

        self.add_message(text, True)
        self.ids.input_field.text = ""
        # Initialize with empty text but visible thought
        Clock.schedule_once(lambda dt: self.add_message("", False, temp=True, thought_visible=True), 0.1)
        Thread(target=self._process_message, args=(text,)).start()

    def _process_message(self, text):
        # Container for streaming text
        stream_data = {'text': "", 'thought': ""}
        
        # Throttled UI Updater (Direct Widget Update)
        def update_ui(dt):
            current_text = stream_data['text']
            current_thought = stream_data['thought']
            
            # Find the last bubble widget
            # In Kivy BoxLayout, children[0] is the LAST added widget (visually at bottom)
            if self.ids.chat_list.children:
                last_bubble = self.ids.chat_list.children[0]
                
                # Verify it is our bot bubble (temp check removed, we assume logic flow)
                if hasattr(last_bubble, 'is_user') and not last_bubble.is_user:
                     if last_bubble.text != current_text: 
                         last_bubble.text = current_text
                     
                     if current_thought:
                         last_bubble.thought_text = current_thought
                         last_bubble.thought_visible = True
                     
                     if self.is_at_bottom:
                         self.scroll_to_bottom(force=False)
            
            # Stop if streaming done? No mechanism here, rely on final update
            
        ui_event = Clock.schedule_interval(update_ui, 0.05)
        
        def on_token(token_data):
            if isinstance(token_data, dict):
                msg_type = token_data.get('type', 'answer')
                content = token_data.get('content', '')
                if msg_type == 'thought':
                    stream_data['thought'] += content
                else:
                    stream_data['text'] += content
            else:
                stream_data['text'] += token_data

        try:
            if self.core:
                result = self.core.process_message(
                    user_id=self.user_id,
                    conversation_id=self.conversation_id,
                    message=text,
                    stream_callback=on_token
                )
                response = result.content if hasattr(result, 'content') else str(result)
                thought = result.thought_trace if hasattr(result, 'thought_trace') else None
            else:
                response = "Core non inizializzato."
                thought = None
        except Exception as e:
            response = f"Errore interno: {e}"
            thought = None
        finally:
             ui_event.cancel()

        Clock.schedule_once(lambda dt: self._update_final(str(response), thought))

    def _update_final(self, response, thought):
         # Make sure final state is consistent
         if self.ids.chat_list.children:
             last_bubble = self.ids.chat_list.children[0]
             last_bubble.text = response
             if thought:
                 last_bubble.thought_text = thought.get('raw_thought', '')
                 last_bubble.thought_visible = False # Collapse after done, or keep open? User preference. User said "when finishes it is stable", implying they see it?
                 # User Request: "che venga fatto vedere tutto il pensiero...".
                 # If I collapse it, they lose it?
                 # Let's keep it visible IF it was populated.
                 # Wait, user said "but when it finishes it is stable".
                 # I'll default to visible=False (collapsed) but with button available to re-open?
                 # Or keep open if user opened it?
                 # For now, let's keep it visible=False (collapsed) to show clean answer, user can expand.
                 # BUT while streaming it was visible!
                 # If I collapse it now, it jumps.
                 # Let's LEAVE IT as is (don't set thought_visible=False).
                 pass
         self.scroll_to_bottom(force=True)

    def _update_response(self, response_text, thought_trace=None):
        # Legacy method refactored into _update_final logic
        pass

    def add_message(self, text, is_user, temp=False, thought_visible=False):
        # Create Widget
        bubble = MessageBubble(
            text=text,
            is_user=is_user,
            thought_text="Inizio analisi..." if temp and not is_user else "",
            thought_visible=thought_visible
        )
        self.ids.chat_list.add_widget(bubble)
        self.history.append({'text': text, 'is_user': is_user}) # Keep simple history for consistency
        
        self.scroll_to_bottom(force=True)

    def scroll_to_bottom(self, force=False):
        # For ScrollView, scroll_y=0 is bottom
        Clock.schedule_once(lambda dt: setattr(self.ids.scroll_view, 'scroll_y', 0), 0.1)

    def on_scroll(self, scroll_y):
        self.is_at_bottom = scroll_y <= 0.05
