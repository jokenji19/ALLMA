from kivy.utils import platform
from kivy.clock import Clock
import json
import logging
import threading
import time
from allma_model.ui.temperature_monitor import TemperatureMonitor

class WebViewBridge:
    def __init__(self, message_callback):
        self.webview = None
        self.message_callback = message_callback
        self.is_android = platform == 'android'
        self.running = True
        
        # Initialize temperature monitor
        self.temperature_monitor = TemperatureMonitor()
        
        if self.is_android:
            self._init_android_webview()
        else:
            logging.warning("WebViewBridge: Not on Android. Webview will not be valid.")

    def _init_android_webview(self):
        from jnius import autoclass, PythonJavaClass, java_method
        from android.runnable import run_on_ui_thread
        import os

        # Android Classes
        WebView = autoclass('android.webkit.WebView')
        WebSettings = autoclass('android.webkit.WebSettings')
        Color = autoclass('android.graphics.Color')
        
        # ------------------------------------------------------------------
        # BRIDGE STRATEGY: POLLING via evaluateJavascript
        # We cannot use addJavascriptInterface due to missing @Annotation support in PyJNIus
        # We cannot use WebViewClient.shouldOverrideUrlLoading because it's a Class, not Interface
        # SOLUTION: ValueCallback IS an Interface. We can implement it!
        # ------------------------------------------------------------------
        
        class ResultCallback(PythonJavaClass):
            __javacontext__ = 'app'
            __javainterfaces__ = ['android/webkit/ValueCallback']

            def __init__(self, callback, bridge):
                super().__init__()
                self.callback = callback
                self.bridge = bridge

            @java_method('(Ljava/lang/Object;)V')
            def onReceiveValue(self, value):
                # value is a JSON string from JS, e.g., '"Hello"' or 'null'
                # print(f"POLL RESULT: {value}")
                if value and value != 'null' and value != 'None':
                    try:
                        # CRITICAL FIX: Use json.loads to unescape the string (hanlde \" inside)
                        # strip('"') was leaving backslashes, breaking downstream JSON parsing
                        import json
                        clean_val = json.loads(value)
                        
                        if clean_val:
                            # FIX 0.57: Double-decode if it's a string (Bridge sends JSON strings)
                            effective_val = clean_val
                            if isinstance(clean_val, str) and clean_val.strip().startswith('{'):
                                try:
                                    decoded = json.loads(clean_val)
                                    if isinstance(decoded, dict):
                                        effective_val = decoded
                                except:
                                    pass # Not JSON, treat as plain text
                            # Check for System/Action Messages using the potentially decoded dict
                            # SECURITY: Validate structure before processing
                            if isinstance(effective_val, dict):
                                # Whitelist allowed keys to prevent object pollution if we were using unsafe loads (we aren't, but good practice)
                                # For now, just ensuring it's a dict is enough since logic below checks specific keys
                                pass
                            elif isinstance(effective_val, str):
                                # Text message
                                pass
                            else:
                                # Reject unknown types (lists, numbers) as top-level messages
                                print(f"⚠️ WebViewBridge: Rejected invalid message type: {type(effective_val)}")
                                return
                            if isinstance(effective_val, dict) and effective_val.get('type') == 'action':
                                action = effective_val.get('action')
                                if action == 'run_benchmark':
                                    print("🧪 UI Trigger: Starting Benchmark...")
                                    
                                    # TOAST FEEDBACK
                                    from kivy.app import App
                                    app = App.get_running_app()
                                    if hasattr(app, 'show_toast'):
                                        app.show_toast("Benchmark Richiesto... 🚀")
                                    
                                    def run_bench():
                                        try:
                                            # Toast inside thread might need UI thread dispatch, 
                                            # but app.show_toast usually handles standard android toast which is thread-safe on some versions,
                                            # or implementation handles it. looking at app_entry.py, show_toast uses run_on_ui_thread implicitly?
                                            # No, it uses autoclass directly. It might crash from thread.
                                            # Safer to just log or try strict dispatch if needed.
                                            # But at least the START toast above is on main thread.
                                            
                                            import sys
                                            sys.path.append(os.getcwd())
                                            from benchmark_iq import CognitiveBenchmark
                                            
                                            brain_ref = None
                                            # Try 1: Direct Access
                                            if hasattr(app, 'chat_screen'):
                                                if hasattr(app.chat_screen, 'core'):
                                                    brain_ref = app.chat_screen.core
                                                elif hasattr(app.chat_screen, 'brain'):
                                                    brain_ref = app.chat_screen.brain
                                            
                                            # Try 2: Via ScreenManager (if Try 1 failed)
                                            if not brain_ref and hasattr(app, 'sm') and app.sm.has_screen('chat'):
                                                 chat_scr = app.sm.get_screen('chat')
                                                 if hasattr(chat_scr, 'core'):
                                                     brain_ref = chat_scr.core
                                                 elif hasattr(chat_scr, 'brain'):
                                                     brain_ref = chat_scr.brain
                                            
                                            # CRITICAL ABORT
                                            if not brain_ref:
                                                err_msg = "ERR: Brain NOT FOUND (checked .core & .brain)"
                                                print(f"❌ {err_msg}")
                                                Clock.schedule_once(lambda dt: app.show_toast(err_msg))
                                                return

                                            bench = CognitiveBenchmark()
                                            
                                            def on_progress(curr, tot, txt):
                                                self.bridge.update_benchmark_ui(curr, tot, txt)
                                                
                                            bench.setup_brain(existing_brain=brain_ref)
                                            bench.run_tests(progress_callback=on_progress)
                                            
                                            print("✅ Benchmark Completed via UI Trigger")
                                            # Completion Toast
                                            Clock.schedule_once(lambda dt: app.show_toast("Benchmark Completato! ✅"))
                                            
                                            # SHARE REPORT (Instead of Chat)
                                            try:
                                                with open(bench.report_path, 'r', encoding='utf-8') as f:
                                                    report_content = f.read()
                                                
                                                short_summary = "📊 **Benchmark Cognitivo ALLMA**\n\n" + report_content
                                                
                                                # Trigger Native Share Sheet
                                                Clock.schedule_once(lambda dt: self.bridge.share_text_content(short_summary), 1.0)
                                                
                                            except Exception as read_e:
                                                print(f"Failed to read/share report: {read_e}")
                                            
                                            # Close UI (fade out)
                                            self.bridge.update_benchmark_ui(100, 100, "Completato!")
                                            Clock.schedule_once(lambda dt: self.bridge.webview.evaluateJavascript("if(window.benchmarkUI) window.benchmarkUI.close()", None), 2.0)
                                            
                                        except Exception as e:
                                            err_msg = f"ERR: {str(e)[:60]}"
                                            print(f"❌ {err_msg}")
                                            import traceback
                                            traceback.print_exc()
                                            Clock.schedule_once(lambda dt: app.show_toast(err_msg))
                                            # Close UI on Error
                                            Clock.schedule_once(lambda dt: self.bridge.webview.evaluateJavascript("if(window.benchmarkUI) window.benchmarkUI.close()", None), 3.0)
                                            
                                    threading.Thread(target=run_bench, daemon=True).start()
                                    return

                            self.callback(clean_val)
                    except Exception as e:
                        print(f"Bridge Decode Error: {e} for value: {value}")
                        # Fallback for simple strings if not valid JSON?
                        # Usually evaluateJavascript returns valid JSON string
                        simple_clean = value.strip('"')
                        if simple_clean:
                            self.callback(simple_clean)

        @run_on_ui_thread
        def create_webview_ui():
            try:
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                self.webview = WebView(activity)
                
                # Settings
                settings = self.webview.getSettings()
                settings.setJavaScriptEnabled(True)
                settings.setDomStorageEnabled(True)
                settings.setAllowFileAccess(True)
                settings.setAllowContentAccess(True)
                
                # Transparent Background
                self.webview.setBackgroundColor(Color.TRANSPARENT)
                
                # --- EDGE-TO-EDGE CONFIGURATION (v0.39: NO LIMITS + JS FALLBACK) ---
                
                        # --- DIAGNOSTIC CONFIGURATION (v0.45: HYBRID FORCE KICK) ---

                def apply_edge_to_edge(dt):
                    from android.runnable import run_on_ui_thread
                    
                    @run_on_ui_thread
                    def _apply_ui_changes():
                        try:
                            def log(msg):
                                print(f"DEBUG_ALLMA: {msg}")

                            # 1. Imports
                            Build = autoclass('android.os.Build')
                            Version = autoclass('android.os.Build$VERSION')
                            log(f"Starting Edge-to-Edge v0.55 (Robust) on SDK: {Version.SDK_INT}")
                            
                            activity_window = activity.getWindow()
                            WindowManager = autoclass('android.view.WindowManager')
                            LayoutParams = autoclass('android.view.WindowManager$LayoutParams')
                            
                            # 2. SANITIZATION (Clear Legacy Flags)
                            FLAG_TRANSLUCENT_STATUS = 67108864
                            FLAG_TRANSLUCENT_NAVIGATION = 134217728
                            activity_window.clearFlags(FLAG_TRANSLUCENT_STATUS)
                            activity_window.clearFlags(FLAG_TRANSLUCENT_NAVIGATION)
                            
                            # 3. APPLY NO_LIMITS (Visuals)
                            # This forces content to go behind bars
                            activity_window.setFlags(
                                LayoutParams.FLAG_LAYOUT_NO_LIMITS,
                                LayoutParams.FLAG_LAYOUT_NO_LIMITS
                            )

                            # 4. BACKGROUND & COLOR
                            FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS = -2147483648 # 0x80000000
                            activity_window.addFlags(FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
                            
                            # Use 0x01FFFFFF (Almost Transparent White) to force drawing
                            # Some OEMs ignore 0 (Transparent) and fall back to Black
                            ALMOST_TRANSPARENT = 0x01FFFFFF 
                            activity_window.setNavigationBarColor(ALMOST_TRANSPARENT)
                            activity_window.setStatusBarColor(ALMOST_TRANSPARENT)
                            
                            # 5. DECOR VIEW (Icons & Layout Force)
                            decorView = activity_window.getDecorView()
                            
                            # Light Status Bar (8192) + Light Nav Bar (16)
                            # This makes icons dark (for light backgrounds)
                            # We assume Light Mode default for now.
                            # TODO: Toggle this based on Theme in future!
                            # Light Status Bar (8192) + Light Nav Bar (16)
                            SYSTEM_UI_FLAG_LIGHT_STATUS_BAR = 8192
                            SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR = 16
                            
                            # CRITICAL: Flags to tell Layout to IGNORE bars (draw behind them)
                            SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION = 512
                            SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN = 1024
                            SYSTEM_UI_FLAG_LAYOUT_STABLE = 256
                            
                            sys_flags = decorView.getSystemUiVisibility()
                            sys_flags |= SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
                            sys_flags |= SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
                            sys_flags |= SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                            sys_flags |= SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                            sys_flags |= SYSTEM_UI_FLAG_LAYOUT_STABLE
                            decorView.setSystemUiVisibility(sys_flags)
                            
                            # 6. FORCE LAYOUT
                            decorView.requestLayout()
                            log("Edge-to-Edge v0.55 Applied (With LightBar Flags).")

                            # 7. DIVIDER
                            if Version.SDK_INT >= 28:
                                 activity_window.setNavigationBarDividerColor(0) # Transparent

                        except Exception as e:
                            print(f"DEBUG_ALLMA: CRITICAL ERROR: {e}")
                            import traceback
                            traceback.print_exc()
                            
                    _apply_ui_changes()

                # Run MULTIPLE TIMES to fight Kivy/SDL2 overrides
                Clock.schedule_once(apply_edge_to_edge, 0.1)
                Clock.schedule_once(apply_edge_to_edge, 1.0) # Retry
                Clock.schedule_once(apply_edge_to_edge, 3.0) # Retry final
                # ----------------------------------
                
                # Setup Polling Callback
                self.poll_callback = ResultCallback(self.message_callback, self)
                
                # LOAD CONTENT (INLINING)
                base_path = "assets/web"
                if not os.path.exists(base_path):
                    import sys
                    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../assets/web')
                
                print(f"Loading Web Assets from: {base_path}")
                
                html = ""
                css = ""
                js = ""
                
                with open(os.path.join(base_path, 'index.html'), 'r') as f:
                    html = f.read()
                with open(os.path.join(base_path, 'style_v24.css'), 'r') as f:
                    css = f.read()
                with open(os.path.join(base_path, 'script_v24.js'), 'r') as f:
                    js = f.read()

                # Patch JS for polling
                js_patch = """
                console.log("ALLMA_DEBUG: Starting Bridge Patch...");
                window.msgQueue = [];
                // API called by UI
                function sendMessage(text) {
                     window.msgQueue.push(text);
                     // Visual confirmation
                     // console.log("ALLMA_DEBUG: Enqueue " + text);
                }
                window.pyBridge = {
                    postMessage: function(text) {
                        window.msgQueue.push(text);
                        console.log("Buffered: " + text);
                    },
                    getTemperature: function() {
                        // This will be called from JavaScript
                        // Return value is handled by Python
                        return null;
                    }
                };
                
                window.fetchPending = function() {
                    return window.msgQueue.shift() || null;
                };
                
                // BENCHMARK TRIGGER (v0.58 DEBUG)
                window.startBenchmark = function() {
                    console.log("Run Benchmark Triggered");
                    // Visual feedback in console/logs
                    if (window.pyBridge) {
                        window.pyBridge.postMessage(JSON.stringify({
                            type: 'action',
                            action: 'run_benchmark'
                        }));
                    } else {
                        console.error("PyBridge not found!");
                    }
                };
                
                console.log("ALLMA_DEBUG: Bridge Patch Completed. fetchPending ready.");

                // --- BENCHMARK VISUAL OVERLAY (v0.61) ---
                window.benchmarkUI = {
                    overlay: null,
                    bar: null,
                    text: null,
                    
                    create: function() {
                        if (this.overlay) return;
                        
                        // Main Overlay
                        this.overlay = document.createElement('div');
                        this.overlay.style.cssText = "position:fixed; bottom:20px; left:5%; width:90%; background:rgba(20,20,30,0.95); border:1px solid #444; border-radius:12px; padding:15px; z-index:9999; box-shadow:0 10px 30px rgba(0,0,0,0.5); font-family:sans-serif; transition: opacity 0.5s ease;";
                        this.overlay.id = "benchmark-overlay";
                        
                        // Title
                        var title = document.createElement('div');
                        title.innerText = "🧠 Benchmark Cognitivo in Corso...";
                        title.style.cssText = "color:#fff; font-size:14px; font-weight:bold; margin-bottom:10px;";
                        this.overlay.appendChild(title);
                        
                        // Progress Container
                        var progressBg = document.createElement('div');
                        progressBg.style.cssText = "width:100%; height:8px; background:#333; border-radius:4px; overflow:hidden;";
                        
                        // Progress Bar
                        this.bar = document.createElement('div');
                        this.bar.style.cssText = "width:0%; height:100%; background:linear-gradient(90deg, #00d2ff, #3a7bd5); transition: width 0.3s ease;";
                        progressBg.appendChild(this.bar);
                        this.overlay.appendChild(progressBg);
                        
                        // Status Text
                        this.text = document.createElement('div');
                        this.text.innerText = "Avvio...";
                        this.text.style.cssText = "color:#aaa; font-size:12px; margin-top:8px; text-align:right;";
                        this.overlay.appendChild(this.text);
                        
                        document.body.appendChild(this.overlay);
                    },
                    
                    update: function(current, total, statusMsg) {
                        if (!this.overlay) this.create();
                        var pct = (current / total) * 100;
                        if (pct > 100) pct = 100;
                        
                        this.bar.style.width = pct + "%";
                        this.text.innerText = statusMsg + " (" + current + "/" + total + ")";
                    },
                    
                    close: function() {
                        if (this.overlay) {
                            this.overlay.style.opacity = '0';
                            setTimeout(() => {
                                if (this.overlay && this.overlay.parentNode) {
                                    this.overlay.parentNode.removeChild(this.overlay);
                                }
                                this.overlay = null;
                            }, 500);
                        }
                    }
                };
                """
                
                # INLINE REPLACEMENT
                # CRITICAL FIX: Do NOT use f-strings for CSS/JS as they contain curly braces!
                # Robust Injection Strategy:
                # 1. Remove existing link/script tags to avoid double loading
                html = html.replace('<link rel="stylesheet" href="style_v24.css">', '')
                html = html.replace('<script src="script_v24.js"></script>', '')
                
                # Global Error Handler
                error_handler = """
                window.onerror = function(msg, url, line, col, error) {
                    var extra = !col ? '' : '\\ncolumn: ' + col;
                    extra += !error ? '' : '\\nerror: ' + error;
                    console.error("Error: " + msg + "\\nurl: " + url + "\\nline: " + line + extra);
                    return true;
                };
                """
                
                full_js = error_handler + "\n" + js_patch + "\n" + js
                
                # 2. Inject CSS/JS into head/body explicitly
                style_tag = '<style>' + css + '</style>'
                script_tag = '<script>' + full_js + '</script>'
                
                html = html.replace('</head>', style_tag + '</head>')
                html = html.replace('</body>', script_tag + '</body>')
                
                # Load Data with Fake Origin to fix CORS/Security restrictions
                # Using https://app.allma/ allows local storage and secure context features
                self.webview.loadDataWithBaseURL("https://app.allma/", html, "text/html", "utf-8", None)
                print("WebView Loaded with Robust Inlining & Fake Origin.")
                
                # Layout Params
                LayoutParams = autoclass('android.view.ViewGroup$LayoutParams')
                params = LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT)
                
                # Add to Activity
                activity.addContentView(self.webview, params)
                
                # Start Polling Loop
                self._start_polling()
                
            except Exception as e:
                print(f"Error initializing WebView: {e}")
                import traceback
                traceback.print_exc()

        create_webview_ui()

    def _start_polling(self):
        # Poll every 200ms
        Clock.schedule_interval(self._poll_js, 0.2)

    def _poll_js(self, dt):
        if not self.webview or not self.poll_callback:
            return
            
        from android.runnable import run_on_ui_thread
        
        @run_on_ui_thread
        def run_poll():
            # fetchPending() returns the string or null
            self.webview.evaluateJavascript("window.fetchPending()", self.poll_callback)
            
        run_poll()

    def send_message_to_js(self, text, sender='bot', thought_text=None):
        if not self.webview:
            print(f"Mock Send to JS ({sender}): {text}")
            return
            
        # Escape strings for JS
        safe_text = json.dumps(text)
        safe_sender = json.dumps(sender)
        safe_thought = json.dumps(thought_text) if thought_text else "null"
        
        js_code = f"window.addMessage({safe_text}, {safe_sender}, {safe_thought})"
        
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def run_js():
            self.webview.evaluateJavascript(js_code, None)
            
        run_js()

    def start_stream(self):
        if not self.webview: return
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def run_js():
            self.webview.evaluateJavascript("window.startStream()", None)
        run_js()

    def stream_chunk(self, text, is_thought=False):
        if not self.webview: return
        safe_text = json.dumps(text)
        is_thought_js = "true" if is_thought else "false"
        js_code = f"window.streamChunk({safe_text}, {is_thought_js})"
        
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def run_js():
            self.webview.evaluateJavascript(js_code, None)
        run_js()

    def end_stream(self):
        if not self.webview: return
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def run_js():
            self.webview.evaluateJavascript("window.endStream()", None)
        run_js()

    def update_benchmark_ui(self, current, total, text):
        """Aggiorna l'overlay di progresso del benchmark."""
        if not self.webview: return
        import json
        safe_text = json.dumps(text)
        js_cmd = f"if(window.benchmarkUI) window.benchmarkUI.update({current}, {total}, {safe_text})"
        
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def run_js():
            self.webview.evaluateJavascript(js_cmd, None)
        run_js()


    def update_synergy(self, percentage: int, status_text: str):
        """Aggiorna il grafico di sinergia/apprendimento."""
        if not self.webview:
            print(f"[WebViewBridge] Synergy update (No WebView): {percentage}% - {status_text}")
            return
            
        js_cmd = f"updateAllmaStatus({percentage}, '{status_text}')"
        
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def run_js():
            self.webview.evaluateJavascript(js_cmd, None)
        run_js()

    def set_input_text(self, text):
        """Imposta il testo della casella di input Web."""
        if not self.webview: return
        import json
        safe_text = json.dumps(text)
        js_cmd = f"window.setInputText({safe_text})"
        
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def run_js():
            self.webview.evaluateJavascript(js_cmd, None)
        run_js()

    def update_voice_text(self, text):
        """Aggiorna il testo nell'overlay vocale."""
        if not self.webview: return
        # Log to verify attempting update
        print(f"Bridge: Updating Voice Text -> {text}")
        
        import json
        safe_text = json.dumps(text)
        js_cmd = f"window.updateVoiceText({safe_text})"
        
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def run_js():
            self.webview.evaluateJavascript(js_cmd, None)
        run_js()
    
    def get_device_temperature(self):
        """Get current device temperature for JavaScript."""
        temp_data = self.temperature_monitor.get_temperatures()
        return temp_data
    
    def inject_temperature_to_js(self):
        """Inject current temperature data into JavaScript."""
        if not self.webview:
            return
        
        temp_data = self.get_device_temperature()
        safe_data = json.dumps(temp_data)
        
        # Update pyBridge.getTemperature to return actual data
        js_cmd = f"""
        window.pyBridge.getTemperature = function() {{
            return {safe_data};
        }};
        """
        
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def run_js():
            self.webview.evaluateJavascript(js_cmd, None)
        run_js()

    def share_text_content(self, text, subject="ALLMA Benchmark Result"):
        """Apre il menu di condivisione nativo Android con il testo fornito."""
        if not self.is_android:
            print(f"[SHARE] Would share text: {text[:50]}...")
            return

        from jnius import autoclass, cast
        from android.runnable import run_on_ui_thread

        @run_on_ui_thread
        def _share():
            try:
                # Android Intents
                Intent = autoclass('android.content.Intent')
                String = autoclass('java.lang.String')
                
                sendIntent = Intent()
                sendIntent.setAction(Intent.ACTION_SEND)
                sendIntent.putExtra(Intent.EXTRA_TEXT, String(text))
                sendIntent.setType("text/plain")
                
                # Title
                sendIntent.putExtra(Intent.EXTRA_SUBJECT, String(subject))
                
                # Create Chooser
                chooser = Intent.createChooser(sendIntent, String("Salva Report con..."))
                
                # Start Activity
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                currentActivity = PythonActivity.mActivity
                
                currentActivity.startActivity(chooser)
                
            except Exception as e:
                print(f"Share Error: {e}")
                import traceback
                traceback.print_exc()

        _share()
