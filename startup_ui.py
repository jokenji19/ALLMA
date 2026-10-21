"""Shared native loading surface, usable before the embedded app is unpacked."""
import math
from pathlib import Path

from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.graphics.texture import Texture
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.metrics import dp
from kivy.properties import BooleanProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.widget import Widget

ASSETS = Path(__file__).resolve().parent / 'assets/web'
FONT = 'Roboto'
if (ASSETS / 'fonts/Inter-Regular.ttf').exists():
    LabelBase.register(name='AllmaStartup', fn_regular=str(ASSETS / 'fonts/Inter-Regular.ttf'))
    FONT = 'AllmaStartup'


class FeatheredImage(Image):
    """Keep the artwork intact; blend only its outer edges into the paper."""
    _edge_textures = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if FeatheredImage._edge_textures is None:
            textures = []
            for vertical, reverse in [(False, False), (False, True), (True, False), (True, True)]:
                values = []
                for i in range(64):
                    t = i / 63
                    alpha = t * t * (3 - 2 * t)
                    if not reverse:
                        alpha = 1 - alpha
                    values.extend((255, 255, 255, round(255 * alpha)))
                data = bytes(values)
                texture = Texture.create(size=(1, 64) if vertical else (64, 1), colorfmt='rgba')
                texture.blit_buffer(data, colorfmt='rgba', bufferfmt='ubyte')
                texture.add_reload_observer(lambda tex, pixels=data: tex.blit_buffer(pixels, colorfmt='rgba', bufferfmt='ubyte'))
                textures.append(texture)
            FeatheredImage._edge_textures = textures
        with self.canvas.after:
            Color(.9804, .9765, .9608, 1)
            self._edges = [Rectangle(texture=texture) for texture in self._edge_textures]
        # Image/BoxLayout finish their own geometry on the next layout pass.
        # Coalesce changes so the masks follow the rendered image, not a stale
        # cached center from the middle of a size/position update.
        self._blend_trigger = Clock.create_trigger(self._blend_edges, -1)
        self.bind(pos=self._blend_trigger, size=self._blend_trigger,
                  texture=self._blend_trigger, norm_image_size=self._blend_trigger)
        self._blend_trigger()

    def _blend_edges(self, *args):
        width, height = self.norm_image_size
        x, y = self.center_x - width / 2, self.center_y - height / 2
        fade = min(width, height) * .14
        for rectangle, pos, size in zip(self._edges,
                [(x,y), (x+width-fade,y), (x,y), (x,y+height-fade)],
                [(fade,height), (fade,height), (width,fade), (width,fade)]):
            rectangle.pos, rectangle.size = pos, size


def native_motion_allowed():
    from kivy.utils import platform
    if platform != 'android':
        return True
    try:
        from jnius import autoclass
        activity = autoclass('org.kivy.android.PythonActivity').mActivity
        settings = autoclass('android.provider.Settings$Global')
        return settings.getFloat(activity.getContentResolver(), 'animator_duration_scale', 1.0) > 0
    except Exception:
        return True


class CircularProgress(Widget):
    max = NumericProperty(100)
    value = NumericProperty(0)
    indeterminate = BooleanProperty(False)
    suspended = BooleanProperty(False)
    phase = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._activity_event = None
        with self.canvas:
            Color(.28, .26, .23, .12)
            self._track = Line(circle=(0, 0, 1), width=dp(1.3))
            self._fill_color = Color(.60, .41, .31, 0)
            self._fill = Line(points=[0, 0, .01, .01], width=dp(1.5), cap='round')
            self._dot_color = Color(.60, .41, .31, 0)
            self._dot = Ellipse(size=(dp(3), dp(3)))
        self.bind(pos=self._draw, size=self._draw, value=self._draw, max=self._draw,
                  phase=self._draw, indeterminate=self._sync_activity, suspended=self._sync_activity, parent=self._sync_activity)

    def _sync_activity(self, *args):
        if self._activity_event:
            self._activity_event.cancel()
            self._activity_event = None
        if self.indeterminate and not self.suspended and self.parent is not None and native_motion_allowed():
            self._activity_event = Clock.schedule_interval(self._tick, 1 / 12)
        self._draw()

    def _tick(self, dt):
        self.phase = (self.phase + dt / 3) % 1

    def _draw(self, *args):
        radius = max(1, min(self.width, self.height) / 2 - dp(4))
        cx, cy = self.center
        self._track.circle = (cx, cy, radius)
        ratio = min(1, max(0, self.value / self.max)) if self.max else 0
        count = max(2, math.ceil(80 * ratio))
        self._fill.points = [v for i in range(count + 1) for v in (
            cx + math.sin(i / count * ratio * math.tau) * radius,
            cy + math.cos(i / count * ratio * math.tau) * radius)]
        self._fill_color.a = 1 if ratio else 0
        # A tiny orbit indicates activity; it never changes the completed arc
        # or the reported percentage when the native model is still loading.
        angle = self.phase * math.tau
        self._dot.pos = (cx + math.sin(angle) * radius - dp(1.5), cy + math.cos(angle) * radius - dp(1.5))
        self._dot_color.a = .65 if self.indeterminate and not self.suspended else 0


class StartupPanel(FloatLayout):
    """One minimal composition, with observed startup checkpoints or download bytes."""
    def __init__(self, value=0, **kwargs):
        super().__init__(**kwargs)
        self.busy = False
        with self.canvas.before:
            Color(.9804, .9765, .9608, 1)
            self._background = Rectangle(pos=self.pos, size=self.size)
        self.card = BoxLayout(orientation='vertical', spacing=dp(8), size_hint=(None, None))
        self.add_widget(self.card)
        def label(text, size, height, color):
            item = Label(text=text, font_name=FONT, font_size=size, color=color,
                         size_hint_y=None, height=dp(height), halign='center', valign='middle')
            item.bind(size=lambda widget, size: setattr(widget, 'text_size', size))
            self.card.add_widget(item)
            return item
        self.brand = label('ALLMA', '15sp', 30, (.22, .21, .19, 1))
        self.illustration = FeatheredImage(source=str(ASSETS / 'images/startup-connection.png'),
                                  fit_mode='contain', size_hint_y=None, height=dp(230))
        self.card.add_widget(self.illustration)
        self.title = label('Uno spazio per\npensare insieme.', '22sp', 64, (.24, .23, .21, 1))
        row = BoxLayout(size_hint_y=None, height=dp(60))
        self.progress_row = row
        row.add_widget(Widget())
        self.progress_bar = CircularProgress(value=value, size_hint=(None, None), size=(dp(52), dp(52)))
        row.add_widget(self.progress_bar)
        row.add_widget(Widget())
        self.card.add_widget(row)
        self.percent_label = label('', '14sp', 23, (.30, .28, .25, 1))
        self.status_label = label('Preparo ALLMA…', '12sp', 32, (.47, .45, .42, 1))
        self.details_label = label('', '11sp', 0, (.55, .43, .38, 1))
        self.details_label.bind(text=self._details_changed)
        self.progress_bar.bind(value=self._percent_changed, indeterminate=self._percent_changed)
        self.bind(pos=self._layout, size=self._layout)
        self._percent_changed()
        self._layout()

    def _percent_changed(self, *args):
        self.percent_label.text = f'{min(100, max(0, self.progress_bar.value)):.0f}%'

    def _details_changed(self, *args):
        self.details_label.height = dp(48) if self.details_label.text else 0
        self._layout()

    def _layout(self, *args):
        width = min(max(dp(200), self.width - dp(48)), dp(350))
        short = self.height < dp(570)
        self.brand.height = dp(26 if short else 30)
        self.title.height = dp(52 if short else 64)
        self.progress_row.height = dp(52 if short else 60)
        self.progress_bar.size = (dp(44 if short else 52),) * 2
        self.status_label.height = dp(28 if short else 32)
        self.card.spacing = dp(5 if short else 8)
        fixed = sum(child.height for child in self.card.children if child is not self.illustration) + self.card.spacing * (len(self.card.children) - 1)
        self.illustration.height = max(dp(32), min(dp(230), self.height * .30, self.height - dp(32) - fixed))
        height = sum(child.height for child in self.card.children) + self.card.spacing * (len(self.card.children) - 1)
        self.card.size = (width, height)
        self.card.pos = (self.center_x - width / 2, self.center_y - height / 2)
        self._background.pos = self.pos
        self._background.size = self.size
        self.card.do_layout()
        self.progress_row.do_layout()
        for child in self.card.children:
            if isinstance(child, Label):
                child.texture_update()

    def set_progress(self, value, title=None):
        self.progress_bar.value = min(100, max(self.progress_bar.value, float(value)))
        if title:
            self.status_label.text = title

    def set_stage(self, title, detail, stage, *, busy=True):
        self.busy = busy
        self.status_label.text = title
        self.details_label.text = detail if not busy and any(word in title.lower() for word in ('riuscito', 'disponibile', 'errore')) else ''
        self.set_progress((20, 40, 80)[max(0, min(2, stage))])
        self.progress_bar.indeterminate = busy

    def stop(self):
        self.progress_bar.suspended = True
        self.progress_bar.indeterminate = False

    def resume(self):
        self.progress_bar.suspended = False
        self.progress_bar.indeterminate = self.busy
