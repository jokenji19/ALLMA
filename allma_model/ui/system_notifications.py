"""Opt-in local Android notifications, independent of model and personal memory."""
import json
import threading
import time
from pathlib import Path
from allma_model.utils.persistence import atomic_write_json


class AndroidNotificationBackend:
    supported = True
    channel_id = 'allma_updates_v1'

    def __init__(self):
        from jnius import autoclass, cast
        self.java, self.cast = autoclass, cast
        self.activity = autoclass('org.kivy.android.PythonActivity').mActivity
        self.manager = cast('android.app.NotificationManager', self.activity.getSystemService('notification'))
        self.sdk = autoclass('android.os.Build$VERSION').SDK_INT

    def channel(self):
        if self.sdk >= 26:
            ch = self.java('android.app.NotificationChannel')(self.channel_id, 'Aggiornamenti ALLMA', 3)
            ch.setDescription('Messaggi e attività completate di ALLMA, solo con il tuo consenso.')
            ch.setLockscreenVisibility(0)  # VISIBILITY_PRIVATE
            self.manager.createNotificationChannel(ch)

    def allowed(self):
        if self.sdk >= 33:
            from android.permissions import check_permission
            if not check_permission('android.permission.POST_NOTIFICATIONS'):
                return False
        if not self.manager.areNotificationsEnabled():
            return False
        channel = self.manager.getNotificationChannel(self.channel_id) if self.sdk >= 26 else None
        return channel is None or channel.getImportance() != 0

    def request(self, callback):
        if self.sdk < 33:
            callback(self.allowed())
            return
        from android.permissions import request_permissions
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def ask():
            request_permissions(['android.permission.POST_NOTIFICATIONS'],
                                lambda permissions, grants: callback(bool(grants) and all(grants)))
        ask()

    def open_settings(self):
        intent = self.java('android.content.Intent')('android.settings.APP_NOTIFICATION_SETTINGS')
        intent.putExtra('android.provider.extra.APP_PACKAGE', self.activity.getPackageName())
        self.activity.startActivity(intent)

    def cancel(self):
        for identifier in (7101, 7102, 7103, 7104):
            self.manager.cancel(identifier)

    def post(self, identifier, title, body):
        self.channel()
        Intent = self.java('android.content.Intent')
        PendingIntent = self.java('android.app.PendingIntent')
        intent = self.activity.getPackageManager().getLaunchIntentForPackage(self.activity.getPackageName())
        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP)
        pending = PendingIntent.getActivity(self.activity, identifier, intent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE)
        builder = self.java('android.app.Notification$Builder')(self.activity, self.channel_id) if self.sdk >= 26 else self.java('android.app.Notification$Builder')(self.activity)
        icon = self.activity.getResources().getIdentifier('ic_allma_notification', 'drawable', self.activity.getPackageName())
        if not icon:
            raise RuntimeError('ALLMA notification icon is missing from the APK')
        builder.setSmallIcon(icon)
        builder.setContentTitle(title)
        builder.setContentText(body)
        builder.setContentIntent(pending)
        builder.setAutoCancel(True)
        builder.setVisibility(0)
        builder.setOnlyAlertOnce(True)
        # Refresh existing ALLMA notices as well after an app update.
        self.manager.notify(identifier, builder.build())
        return True


class SystemNotifications:
    events = {
        'message': (7101, 'Un messaggio da ALLMA', 'Hai un nuovo messaggio. Apri ALLMA per leggerlo.'),
        'dream': (7102, 'Una nuova riflessione', 'ALLMA ha aggiornato il Diario dei sogni.'),
        'model': (7103, 'Modello pronto', 'Puoi tornare a parlare con ALLMA.'),
        'test': (7104, 'ALLMA · Notifica di prova', 'Le notifiche di ALLMA funzionano.'),
    }

    def __init__(self, path, backend=None, clock=time.time):
        self.path, self.clock = Path(path), clock
        self._lock = threading.RLock()
        self.enabled, self._request, self.last_sent = False, 0, {}
        if backend is None:
            from kivy.utils import platform
            backend = AndroidNotificationBackend() if platform == 'android' else None
        self.backend = backend
        try:
            data = json.loads(self.path.read_text())
            self.enabled = data.get('enabled') is True
            self.last_sent = {k: v for k, v in data.get('last_sent', {}).items()
                              if k in self.events and type(v) in (int, float)}
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def _save(self):
        atomic_write_json(self.path, {'version': 1, 'enabled': self.enabled, 'last_sent': self.last_sent})

    def status(self):
        supported = self.backend is not None
        allowed = bool(supported and self.backend.allowed())
        return {'supported': supported, 'enabled': self.enabled, 'allowed': allowed,
                'active': self.enabled and allowed}

    def configure(self, enabled, callback):
        if type(enabled) is not bool:
            raise ValueError('Il consenso deve essere esplicito')
        with self._lock:
            self._request += 1
            request = self._request
            if not enabled:
                self.enabled = False
                self._save()
                if self.backend:
                    self.backend.cancel()
                callback(self.status())
                return
            if not self.backend:
                callback(self.status())
                return
            def granted(ok):
                with self._lock:
                    if request != self._request:
                        return  # User switched off while the Android dialog was open.
                    self.enabled = bool(ok and self.backend.allowed())
                    if self.enabled:
                        self.backend.channel()
                    self._save()
                    callback(self.status())
            if self.backend.allowed():
                granted(True)
            else:
                self.backend.request(granted)

    def publish(self, kind, explicit_test=False):
        with self._lock:
            if kind not in self.events or not self.enabled or not self.backend or not self.backend.allowed():
                return False
            now = self.clock()
            last = self.last_sent.get(kind)
            if last is not None and not (explicit_test and kind == 'test') and now - last < 600:
                return False
            if not self.backend.post(*self.events[kind]):
                return False
            self.last_sent[kind] = now
            self._save()
            return True
