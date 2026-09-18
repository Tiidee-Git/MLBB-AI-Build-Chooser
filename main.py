import os
import threading
import time
from typing import List

from kivy.app import App
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout

try:
    from jnius import autoclass, PythonJavaClass, java_method
except ImportError:  # pragma: no cover
    autoclass = None
    PythonJavaClass = object
    java_method = lambda *args, **kwargs: (lambda func: func)


Builder.load_string(
    """
<MLBBOverlayRoot>:
    orientation: 'vertical'
    padding: dp(18)
    spacing: dp(12)
    canvas.before:
        Color:
            rgba: (0.04, 0.07, 0.11, 0.95)
        Rectangle:
            pos: self.pos
            size: self.size

    Label:
        text: 'MLBB AI Build Chooser'
        font_size: '24sp'
        bold: True
        color: (0.82, 1.0, 0.82, 1)
        size_hint_y: None
        height: dp(42)

    Label:
        text: 'System Telemetry'
        font_size: '17sp'
        bold: True
        color: (0.90, 0.96, 1.0, 1)
        size_hint_y: None
        height: dp(28)

    GridLayout:
        cols: 1
        spacing: dp(6)
        size_hint_y: None
        height: dp(180)

        Label:
            text: 'Target: Mobile Legends: Bang Bang'
            halign: 'left'
            valign: 'middle'
            text_size: self.size
            color: (0.82, 0.91, 1.0, 1)
        Label:
            text: 'Threat Matrix: High Priority'
            halign: 'left'
            valign: 'middle'
            text_size: self.size
            color: (0.82, 0.91, 1.0, 1)
        Label:
            text: 'Overlay State: Ready'
            halign: 'left'
            valign: 'middle'
            text_size: self.size
            color: (0.82, 0.91, 1.0, 1)
        Label:
            text: 'Recommended Tactics: Anti-Engage / Burst Counter'
            halign: 'left'
            valign: 'middle'
            text_size: self.size
            color: (0.82, 0.91, 1.0, 1)

    Button:
        id: activate_button
        text: 'Activate Overlay'
        bold: True
        size_hint_y: None
        height: dp(60)
        background_color: (0.14, 0.86, 0.40, 1.0)
        color: (1, 1, 1, 1)
        on_release: root.activate_overlay()
"""
)


class ThreatMatrix:
    def __init__(self):
        self.vectors = [
            {'enemy': 'Lunox', 'priority': 94, 'text': 'Sea Halberd (Anti-Regen)'},
            {'enemy': 'Valir', 'priority': 88, 'text': "Athena's Shield (Magic Burst Counter)"},
            {'enemy': 'Masha', 'priority': 72, 'text': 'Oracle (Sustain + Team Peel)'},
            {'enemy': 'Chou', 'priority': 81, 'text': 'Radiant Armor (Anti-Engage Burst)'},
            {'enemy': 'Kagura', 'priority': 90, 'text': 'Dominance Ice (Utility Slow Counter)'},
            {'enemy': 'Balmond', 'priority': 76, 'text': 'Brute Force Breastplate (Frontline Counter)'},
        ]

    def current_recommendation(self, tick_index: int):
        ordered = sorted(self.vectors, key=lambda item: item['priority'], reverse=True)
        return ordered[tick_index % len(ordered)]['text']


class OverlayTouchListener(PythonJavaClass):
    __javainterfaces__ = ['android/view/View$OnTouchListener']

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        self.last_x = 0.0
        self.last_y = 0.0

    @java_method('(Landroid/view/View;Landroid/view/MotionEvent;)Z')
    def onTouch(self, view, event):
        action = event.getActionMasked()
        raw_x = event.getRawX()
        raw_y = event.getRawY()

        if action == 0:
            self.last_x = raw_x
            self.last_y = raw_y
            return True

        if action == 2:
            dx = raw_x - self.last_x
            dy = raw_y - self.last_y
            self.last_x = raw_x
            self.last_y = raw_y
            self.bridge.move_overlay(dx, dy)
            return True

        if action == 1:
            return True

        return False


class AndroidOverlayBridge:
    def __init__(self):
        self.running = False
        self.activity = None
        self.window_manager = None
        self.overlay_container = None
        self.overlay_hud = None
        self.overlay_params = None
        self.threat_matrix = ThreatMatrix()
        self.drag_offset_x = 0.0
        self.drag_offset_y = 0.0
        self._thread = None

    def attach_activity(self):
        if autoclass is None:
            return
        activity_cls = autoclass('org.kivy.android.PythonActivity')
        self.activity = activity_cls.mActivity

    def request_overlay_permission(self):
        if autoclass is None or self.activity is None:
            return
        permission = 'android.permission.SYSTEM_ALERT_WINDOW'
        try:
            if self.activity.checkSelfPermission(permission) != 0:
                self.activity.requestPermissions([permission], 101)
        except Exception:
            pass

    def start(self):
        if self.running:
            return
        self.running = True
        self.attach_activity()
        self._thread = threading.Thread(target=self._overlay_worker, daemon=True)
        self._thread.start()

    def _overlay_worker(self):
        self.request_overlay_permission()
        self._build_native_overlay()
        self._update_loop()

    def _build_native_overlay(self):
        if autoclass is None or self.activity is None:
            return

        try:
            window_service = self.activity.getSystemService('window')
            layout_params_class = autoclass('android.view.WindowManager$LayoutParams')
            gravity_class = autoclass('android.view.Gravity')
            color_class = autoclass('android.graphics.Color')
            pixel_format_class = autoclass('android.graphics.PixelFormat')
            linear_layout_class = autoclass('android.widget.LinearLayout')
            text_view_class = autoclass('android.widget.TextView')

            params = layout_params_class(
                getattr(layout_params_class, 'TYPE_APPLICATION_OVERLAY'),
                getattr(layout_params_class, 'FLAG_NOT_FOCUSABLE') | getattr(layout_params_class, 'FLAG_NOT_TOUCH_MODAL'),
                0
            )
            params.format = pixel_format_class.TRANSLUCENT
            params.gravity = gravity_class.TOP | gravity_class.START
            params.x = 80
            params.y = 120
            params.width = -2
            params.height = -2

            container = linear_layout_class(self.activity)
            container.setOrientation(1)
            container.setPadding(20, 12, 20, 12)
            container.setBackgroundColor(color_class.argb(140, 10, 25, 18))

            hud = text_view_class(self.activity)
            hud.setText('Sea Halberd (Anti-Regen)')
            hud.setTextColor(color_class.argb(255, 90, 255, 140))
            hud.setTextSize(18)
            hud.setShadowLayer(4.0, 0.0, 0.0, color_class.argb(255, 0, 255, 110))
            hud.setBackgroundColor(color_class.argb(120, 10, 25, 18))
            hud.setPadding(18, 10, 18, 10)
            hud.setSingleLine(False)
            hud.setTypeface(self._get_font())

            listener = OverlayTouchListener(self)
            hud.setOnTouchListener(listener)
            container.addView(hud)

            self.window_manager = window_service
            self.overlay_container = container
            self.overlay_hud = hud
            self.overlay_params = params

            self.activity.runOnUiThread(lambda: self.window_manager.addView(self.overlay_container, self.overlay_params))
            self._apply_text('Sea Halberd (Anti-Regen)')
        except Exception:
            pass

    def _get_font(self):
        try:
            if autoclass is None:
                return None
            typeface_class = autoclass('android.graphics.Typeface')
            return typeface_class.create('monospace', typeface_class.BOLD)
        except Exception:
            return None

    def _apply_text(self, value):
        if self.overlay_hud is None or self.activity is None:
            return

        def ui_update():
            try:
                self.overlay_hud.setText(value)
            except Exception:
                pass

        self.activity.runOnUiThread(ui_update)

    def move_overlay(self, dx, dy):
        if self.overlay_params is None or self.window_manager is None:
            return

        self.overlay_params.x += int(dx)
        self.overlay_params.y += int(dy)

        def update_layout():
            try:
                self.window_manager.updateViewLayout(self.overlay_container, self.overlay_params)
            except Exception:
                pass

        if self.activity is not None:
            self.activity.runOnUiThread(update_layout)

    def _update_loop(self):
        tick = 0
        while self.running:
            text = self.threat_matrix.current_recommendation(tick)
            self._apply_text(text)
            tick += 1
            time.sleep(5)

    def stop(self):
        self.running = False
        if self.window_manager is not None and self.overlay_container is not None:
            try:
                self.window_manager.removeView(self.overlay_container)
            except Exception:
                pass


class MLBBOverlayRoot(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._overlay_started = False
        self.overlay_bridge = AndroidOverlayBridge()

    def activate_overlay(self):
        if self._overlay_started:
            return
        self._overlay_started = True
        self.ids.activate_button.text = 'Overlay Active'
        self.ids.activate_button.disabled = True
        threading.Thread(target=self.overlay_bridge.start, daemon=True).start()


class MLBBAIChooserApp(App):
    def build(self):
        if self._is_android_runtime():
            self._request_overlay_permission_immediately()
        return MLBBOverlayRoot()

    def _is_android_runtime(self):
        return os.name == 'posix' and os.environ.get('KIVY_BUILD') == 'android'

    def _request_overlay_permission_immediately(self):
        try:
            if autoclass is None:
                return
            activity_cls = autoclass('org.kivy.android.PythonActivity')
            activity = activity_cls.mActivity
            if activity is None:
                return
            permission = 'android.permission.SYSTEM_ALERT_WINDOW'
            if activity.checkSelfPermission(permission) != 0:
                activity.requestPermissions([permission], 101)
        except Exception:
            pass


if __name__ == '__main__':
    MLBBAIChooserApp().run()
