"""Lightweight native counterparts of the cosmic WebView design."""
from pathlib import Path
from kivy.core.text import LabelBase
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.properties import BooleanProperty, NumericProperty

FONT_DIR = Path(__file__).resolve().parents[2] / 'assets/web/fonts'
LabelBase.register(name='Inter', fn_regular=str(FONT_DIR / 'Inter-Regular.ttf'),
                   fn_bold=str(FONT_DIR / 'Inter-Semibold.ttf'))


def native_motion_allowed():
    from kivy.utils import platform
    if platform != 'android':
        return True
    try:
        from jnius import autoclass
        activity = autoclass('org.kivy.android.PythonActivity').mActivity
        settings = autoclass('android.provider.Settings$Global')
        return settings.getFloat(activity.getContentResolver(),'animator_duration_scale',1.0) > 0
    except Exception:
        return True


class CosmicProgress(Widget):
    max = NumericProperty(100)
    value = NumericProperty(0)
    indeterminate = BooleanProperty(False)
    phase = NumericProperty(0)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._activity_event = None
        self.bind(pos=self._draw,size=self._draw,value=self._draw,max=self._draw,phase=self._draw,
                  indeterminate=self._sync_activity,parent=self._sync_activity)
        self._sync_activity()

    def _sync_activity(self,*args):
        if self._activity_event is not None:
            self._activity_event.cancel()
            self._activity_event = None
        if self.indeterminate and self.parent is not None and native_motion_allowed():
            self._activity_event = Clock.schedule_interval(self._tick, .1)
        self._draw()

    def _tick(self,dt):
        self.phase = (self.phase + dt*.55) % 1


    def _draw(self, *args):
        h=dp(4)
        y=self.center_y-h/2
        if not hasattr(self,'_track'):
            with self.canvas:
                Color(.5,.75,.94,.14)
                self._track=RoundedRectangle(radius=[h/2])
                self._fill_color=Color(.22,.61,.85,1)
                self._fill=RoundedRectangle(radius=[h/2])
        self._track.pos=(self.x,y)
        self._track.size=(self.width,h)
        ratio=min(1,max(0,self.value/self.max)) if self.max else 0
        if self.indeterminate:
            span=self.width*.22
            offset=(self.width-span)*(1-abs(2*self.phase-1))
            self._fill.pos=(self.x+offset,y)
            self._fill.size=(span,h)
            self._fill_color.a=1
        else:
            self._fill.pos=(self.x,y)
            self._fill.size=(self.width*ratio,h)
            self._fill_color.a=1 if ratio else 0

from kivy.clock import Clock
from kivy.properties import BooleanProperty, NumericProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Rectangle, Ellipse
from allma_model.ui.theme import Theme


class StartupPanel(FloatLayout):
    """Native startup surface: real stage text, no estimated model percentage."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.busy = False
        self.background = Theme.get_vertical_gradient_texture((.79,.91,.99,1),(.95,.97,1,1))
        self.card = BoxLayout(orientation='vertical', padding=dp(26), spacing=dp(14), size_hint=(None,None))
        self.add_widget(self.card)
        def label(text, size, height, color):
            item=Label(text=text,font_name='Inter',font_size=size,color=color,size_hint_y=None,
                       height=dp(height),halign='center',valign='middle')
            def wrap(widget,value):
                widget.text_size=value
                widget.texture_update()
            item.bind(size=wrap)
            self.card.add_widget(item)
            return item
        label('A L L M A','15sp',30,(.17,.48,.69,1))
        label('Uno spazio per\npensare insieme.','29sp',106,(.12,.24,.32,1))
        label('Le tue parole, la nostra storia.','14sp',40,(.32,.43,.52,1))
        self.status_label=label('Preparo ALLMA…','16sp',54,(.14,.39,.55,1))
        self.progress_bar=CosmicProgress(max=100,size_hint_y=None,height=dp(20))
        self.card.add_widget(self.progress_bar)
        self.details_label=label('Un momento per preparare tutto.','12sp',64,(.32,.43,.52,1))
        self.steps_label=label('Verifica  ·  Modello  ·  Chat','11sp',28,(.32,.43,.52,1))
        self.bind(pos=self._layout,size=self._layout)
        self._layout()
        # Upload static text after the native surface's first layout/context.
        Clock.schedule_once(self._refresh_labels, .1)

    def _refresh_labels(self,dt):
        for child in self.card.children:
            if isinstance(child,Label):
                child.texture_update()

    def _layout(self,*args):
        width=min(max(dp(220),self.width-dp(40)),dp(390))
        self.card.size=(width,dp(492))
        self.card.pos=(self.center_x-width/2,self.center_y-dp(246))
        if self.height < dp(560):
            self.card.size=(width,dp(456))
            self.card.pos=(self.center_x-width/2,self.y+dp(16))
            self.card.spacing=dp(6)
        else:
            self.card.spacing=dp(14)
        if not hasattr(self,'_background_rect'):
            with self.canvas.before:
                Color(1,1,1,1)
                self._background_rect=Rectangle(texture=self.background)
                Color(.68,.84,.99,.25)
                self._blue=Ellipse()
                Color(.88,.87,.98,.3)
                self._lavender=Ellipse()
            with self.card.canvas.before:
                Color(1,1,1,.7)
                self._card_rect=RoundedRectangle(radius=[dp(36)])
        self._background_rect.pos=self.pos
        self._background_rect.size=self.size
        self._blue.pos=(self.x-self.width*.18,self.top-self.width*.8)
        self._blue.size=(self.width,self.width)
        self._lavender.pos=(self.center_x,self.y-self.width*.25)
        self._lavender.size=(self.width,self.width)
        self._card_rect.pos=self.card.pos
        self._card_rect.size=self.card.size

    def set_stage(self,title,detail,stage,*,busy=True):
        self.busy = busy
        self.status_label.text=title
        self.details_label.text=detail
        labels=['Verifica','Modello','Chat']
        self.steps_label.text='  ·  '.join(('● ' if i==stage else '✓ ' if i<stage else '')+text for i,text in enumerate(labels))
        self.progress_bar.indeterminate=busy
        for item in (self.status_label,self.details_label,self.steps_label):
            item.texture_update()

    def stop(self):
        self.progress_bar.indeterminate=False
