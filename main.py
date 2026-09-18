import os
import threading
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout

try:
    from jnius import autoclass
except ImportError:  # pragma: no cover
    autoclass = None


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


class MLBBOverlayRoot(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._overlay_active = False
        self._overlay_thread = None
        self._overlay_window = None

    def activate_overlay(self):
        if self._overlay_active:
            return

        self._overlay_active = True
        self.ids.activate_button.text = 'Overlay Active'
        self.ids.activate_button.disabled = True

        self._overlay_thread = threading.Thread(target=self._launch_overlay, daemon=True)
        self._overlay_thread.start()

    def _launch_overlay(self):
        if self._is_android():
            self._request_system_overlay_permission()
        self._create_native_hud()

    def _is_android(self):
        return os.name == 'posix' and os.environ.get('KIVY_BUILD') == 'android'

    def _request_system_overlay_permission(self):
        try:
            if autoclass is None:
                return
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            if activity is None:
                return
            permission = 'android.permission.SYSTEM_ALERT_WINDOW'
            if activity.checkSelfPermission(permission) != 0:
                activity.requestPermissions([permission], 101)
        except Exception:
            pass

    def _create_native_hud(self):
        if autoclass is None:
            return

        try:
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            if activity is None:
                return

            window_service = activity.getSystemService('window')
            layout_params = autoclass('android.view.WindowManager$LayoutParams')
            gravity = autoclass('android.view.Gravity')
            color = autoclass('android.graphics.Color')
            text_view = autoclass('android.widget.TextView')
            linear_layout = autoclass('android.widget.LinearLayout')
            type_value = getattr(layout_params, 'TYPE_APPLICATION_OVERLAY')
            flag_not_focusable = getattr(layout_params, 'FLAG_NOT_FOCUSABLE')
            flag_not_touch_modal = getattr(layout_params, 'FLAG_NOT_TOUCH_MODAL')
            params = layout_params(
                type_value,
                flag_not_focusable | flag_not_touch_modal,
                0
            )
            params.format = getattr(layout_params, 'FORMAT_TRANSLUCENT')
            params.gravity = gravity.TOP | gravity.START
            params.x = 80
            params.y = 80
            params.width = -2
            params.height = -2

            container = linear_layout(activity)
            container.setOrientation(1)
            container.setPadding(18, 10, 18, 10)
            container.setBackgroundColor(color.argb(140, 10, 32, 18))

            hud = text_view(activity)
            hud.setText('Sea Halberd (Anti-Regen)')
            hud.setTextColor(color.argb(255, 90, 255, 140))
            hud.setTextSize(18)
            hud.setShadowLayer(2.5, 0, 0, color.argb(255, 0, 255, 120))
            hud.setTypeface(self._get_typeface())
            hud.setPadding(18, 10, 18, 10)
            hud.setBackgroundColor(color.argb(120, 5, 20, 18))
            hud.setSingleLine(False)

            container.addView(hud)
            window_service.addView(container, params)

            self._overlay_window = container
            self._overlay_hud = hud
            self._overlay_params = params
            self._overlay_window_manager = window_service
            self._start_hud_updater(hud)
        except Exception:
            pass

    def _get_typeface(self):
        try:
            if autoclass is None:
                return None
            typeface = autoclass('android.graphics.Typeface')
            return typeface.create('monospace', typeface.BOLD)
        except Exception:
            return None

    def _start_hud_updater(self, hud):
        recommendations = [
            'Sea Halberd (Anti-Regen)',
            "Athena's Shield (Magic Burst Counter)",
            'Oracle (Sustain + Team Peel)',
            'Radiant Armor (Anti-Spell Burst)',
            'Dominance Ice (Utility Slow Counter)',
            'Brute Force Breastplate (Frontline Counter)',
        ]

        def update_loop():
            while self._overlay_active:
                index = int(time.time() // 5) % len(recommendations)
                next_text = recommendations[index]
                Clock.schedule_once(lambda dt, text=next_text: self._safe_ui_text_update(hud, text), 0)
                time.sleep(5)

        self._updater_thread = threading.Thread(target=update_loop, daemon=True)
        self._updater_thread.start()

    def _safe_ui_text_update(self, view, text):
        try:
            if view is None:
                return
            view.setText(text)
        except Exception:
            pass


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
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            permission = 'android.permission.SYSTEM_ALERT_WINDOW'
            if activity is not None and activity.checkSelfPermission(permission) != 0:
                activity.requestPermissions([permission], 101)
        except Exception:
            pass


if __name__ == '__main__':
    MLBBAIChooserApp().run()
