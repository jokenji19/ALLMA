"""Install only after ALLMA has atomically reserved an idle native runtime.

The old app must support prepare_native_update. No force-stop, no marker
deletion, no access to personal history. An install failure releases the gate.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'org.allma.allma_prime'


class Device:
    def __init__(self, serial, adb='adb', node='node'):
        self.args = [adb, '-s', serial]
        self.node = node
        self.port = None
        self.pid = None

    def adb(self, *args, timeout=30):
        return subprocess.check_output(self.args + list(args), text=True, timeout=timeout).strip()

    def connect(self):
        pid = self.adb('shell', 'pidof', PACKAGE).split()[0]
        self.pid = pid
        self.port = self.adb('forward', 'tcp:0', 'localabstract:webview_devtools_remote_' + pid)

    def js(self, expression):
        run = subprocess.run([self.node, str(ROOT / 'tools/android_webview_probe.mjs'),
            self.port, expression], capture_output=True, text=True, timeout=15, check=True)
        return json.loads(run.stdout)

    def request(self, action):
        self.js("window._nativeUpdateReply=null;window.pyBridge.postMessage(JSON.stringify({type:'action',action:"
                + json.dumps(action) + "}));true")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            result = self.js('window._nativeUpdateReply || null')
            if result is not None:
                return result
            time.sleep(.2)
        raise RuntimeError('ALLMA non ha confermato la preparazione: installazione annullata')

    def disconnect(self):
        if self.port:
            subprocess.run(self.args + ['forward', '--remove', 'tcp:' + self.port],
                           capture_output=True, timeout=10)

    def launch_after_install(self):
        # Package replacement can deliver a delayed force-stop after adb has
        # reported Success. A fire-and-forget start can therefore disappear.
        for attempt in range(3):
            self.adb('shell', 'am', 'start', '-W', '-n', PACKAGE + '/org.kivy.android.PythonActivity')
            try:
                pid = self.adb('shell', 'pidof', PACKAGE).split()[0]
                time.sleep(2)
                stable = self.adb('shell', 'pidof', PACKAGE).split()[0]
            except (subprocess.CalledProcessError, IndexError):
                pid, stable = None, None
            if pid and pid == stable:
                if pid == self.pid:
                    # An unchanged package may keep the old process. Do not
                    # leave its maintenance gate reserved indefinitely.
                    self.request('resume_native_update')
                return
            time.sleep(.4)
        raise RuntimeError('Android non ha mantenuto ALLMA aperta dopo l’aggiornamento')


def install(apk, device):
    requested, installed = False, False
    try:
        device.connect()
        ready = device.js("(() => {const i=document.getElementById('message-input');return !!i&&!document.hidden&&!i.value.trim()&&!chatBusy&&!newChatPending;})()")
        if not ready:
            raise RuntimeError('Lascia ALLMA visibile, senza messaggi o richieste in corso')
        requested = True
        status = device.request('prepare_native_update')
        reserved = status.get('reserved') is True
        if not reserved or status.get('ready') is not True or status.get('busy') is not False or status.get('active_operations') != 0:
            raise RuntimeError('Operazioni in corso: installazione annullata senza arrestare ALLMA')
        print('Runtime riservato; nessuna nuova operazione nativa può iniziare', flush=True)
        result = device.adb('install', '-r', str(apk), timeout=120)
        if 'Success' not in result:
            raise RuntimeError('Android non ha confermato l’installazione')
        installed = True
        device.launch_after_install()
        print('Aggiornamento installato; processo ALLMA avviato e stabile', flush=True)
    finally:
        if requested and not installed:
            try:
                device.request('resume_native_update')
            except Exception:
                print('Riavvia ALLMA per uscire dalla preparazione dell’aggiornamento', flush=True)
        device.disconnect()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk', type=Path)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--adb', default='adb')
    parser.add_argument('--node', default='node')
    args = parser.parse_args()
    if not args.apk.is_file():
        parser.error('APK non trovata')
    # Verify current code/assets before touching the running application.
    from verify_android_apk import verify_apk
    print(json.dumps(verify_apk(args.apk)), flush=True)
    install(args.apk.resolve(), Device(args.serial, args.adb, args.node))


if __name__ == '__main__':
    main()
