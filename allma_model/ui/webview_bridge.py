from kivy.utils import platform
from kivy.clock import Clock
import json
import logging
import re
import threading
import time
from allma_model.ui.temperature_monitor import TemperatureMonitor

class WebViewBridge:
    def __init__(self, message_callback, core=None, startup_error=None):
        self.webview = None
        self.message_callback = message_callback
        self.core = core
        self.startup_error = startup_error
        self.is_android = platform == 'android'
        self.running = True
        self._closed = False
        self._poll_event = None
        self._poll_inflight = False
        from allma_model.ui.stream_delivery import StreamDelivery
        self._stream_delivery = StreamDelivery(
            lambda batch: self.call_js_function('streamBatch', json.dumps(batch)),
            Clock.schedule_once)
        self._startup_ready = False
        self._startup_revealed = False
        self._startup_reveal_event = None
        
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
                self.bridge._poll_inflight = False
                if self.bridge._closed or not self.bridge.running:
                    return
                # value is a JSON string from JS, e.g., '"Hello"' or 'null'
                # print(f"POLL RESULT: {value}")
                if value and value != 'null' and value != 'None':
                    try:
                        from allma_model.ui.bridge_protocol import decode_poll
                        clean_val = decode_poll(value)
                        if clean_val:
                            effective_val = clean_val
                            if isinstance(effective_val, dict) and effective_val.get('type') == 'chat':
                                self.callback(effective_val)
                                return
                            if isinstance(effective_val, dict) and effective_val.get('type') == 'action':
                                action = effective_val.get('action')
                                if action == 'startup_ready':
                                    self.bridge.reveal_startup()
                                    return
                                if action in ('backup_status','backup_configure','backup_create','backup_verify','backup_repair',
                                              'backup_export','backup_import','backup_confirm_restore','backup_cancel_restore'):
                                    if not hasattr(self.bridge,'backup_controller'):
                                        from allma_model.ui.backup_controller import BackupController
                                        self.bridge.backup_controller=BackupController(self.bridge)
                                    self.bridge.backup_controller.handle(action,effective_val)
                                    return
                                if action == 'navigation_exit':
                                    self.bridge.background_app()
                                    return
                                if action == 'brain_activity':
                                    self.bridge.handle_brain_activity(effective_val.get('after', 0))
                                    return
                                if action == 'avatar_configure':
                                    self.bridge.handle_avatar_configuration(effective_val.get('presentation'), effective_val.get('request_id'))
                                    return
                                if action in ('decider_status', 'set_decider'):
                                    self.bridge.handle_decider_action(action, effective_val.get('enabled'))
                                    return
                                if action in ('web_status', 'set_web_access'):
                                    self.bridge.handle_web_action(action, effective_val.get('enabled'))
                                    return
                                if action == 'open_reference':
                                    self.bridge.open_reference(effective_val.get('url'))
                                    return
                                if action in ('notification_status', 'set_notifications', 'test_notification', 'notification_settings'):
                                    self.bridge.handle_notification_action(action, effective_val.get('enabled'))
                                    return
                                if action == 'copy_message':
                                    self.bridge.copy_message(effective_val.get('id'), effective_val.get('text'))
                                    return
                                if action in ('list_models', 'apply_model'):
                                    self.bridge.handle_model_action(action, effective_val.get('key'))
                                    return
                                if action == 'cancel_benchmark':
                                    bench = getattr(self.bridge, 'active_benchmark', None)
                                    if bench is not None:
                                        bench.cancel_event.set()
                                    return
                                if action == 'run_benchmark':
                                    if getattr(self.bridge, 'benchmark_running', False):
                                        return
                                    self.bridge.benchmark_running = True
                                    profile = effective_val.get('profile', 'quick')
                                    if profile not in ('quick', 'historical', 'extended', 'comparison', 'reasoning', 'support', 'support_roles', 'support_reasoning', 'support_natural', 'operational', 'tool_learning', 'relational', 'perception', 'context_fit', 'context_inference', 'reasoning_diagnostic', 'reasoning_followup', 'reasoning_validation', 'learning_evolution', 'long_session', 'runtime_followup', 'turn_reasoning', 'turn_revision', 'checkin', 'public_references', 'internet_chat', 'memory_recovery', 'recall_storage', 'incremental_storage', 'long_history', 'preservation', 'idle_runtime', 'learning_storage', 'goal_continuity', 'goal_planning', 'plan_experience', 'plan_transfer', 'plan_review', 'plan_comparison', 'dialogue_recovery', 'dialogue', 'growth', 'decider', 'memory', 'memory_contract', 'memory_recall', 'memory_lifecycle', 'memory_personal', 'memory_dialogue', 'greeting', 'greeting_closure', 'personality', 'personality_feedback'):
                                        profile = 'quick'
                                    print("🧪 UI Trigger: Starting Benchmark...")
                                    
                                    # TOAST FEEDBACK
                                    from kivy.app import App
                                    app = App.get_running_app()
                                    app = getattr(app, 'internal_app', app)
                                    if hasattr(app, 'show_toast'):
                                        app.show_toast("Benchmark Richiesto... 🚀")
                                    
                                    def run_bench():
                                        bench = None
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
                                            
                                            brain_ref = self.bridge.core
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

                                            if profile == 'relational':
                                                from reliability_android import AndroidRelationalRun
                                                bench = AndroidRelationalRun()
                                            elif profile == 'perception':
                                                from reliability_android import AndroidPerceptionRun
                                                bench = AndroidPerceptionRun()
                                            elif profile == 'context_fit':
                                                from allma_model.llm.context_diagnostics import ContextFitRun
                                                bench = ContextFitRun()
                                            elif profile == 'context_inference':
                                                from allma_model.llm.context_inference import ContextInferenceRun
                                                bench = ContextInferenceRun()
                                            elif profile == 'reasoning_diagnostic':
                                                from allma_model.llm.reasoning_diagnostics import ReasoningDiagnosticRun
                                                bench = ReasoningDiagnosticRun()
                                            elif profile == 'reasoning_followup':
                                                from allma_model.llm.reasoning_diagnostics import ReasoningFollowupRun
                                                bench = ReasoningFollowupRun()
                                            elif profile == 'reasoning_validation':
                                                from allma_model.llm.reasoning_diagnostics import ReasoningValidationRun
                                                bench = ReasoningValidationRun()
                                            elif profile == 'learning_evolution':
                                                from reliability_android import AndroidLearningEvolutionRun
                                                bench = AndroidLearningEvolutionRun()
                                            elif profile == 'internet_chat':
                                                from allma_model.llm.internet_chat_diagnostics import InternetChatRun
                                                bench = InternetChatRun()
                                            elif profile == 'public_references':
                                                from allma_model.llm.public_reference_diagnostics import PublicReferenceRun
                                                bench = PublicReferenceRun()
                                            elif profile == 'turn_revision':
                                                from allma_model.llm.dialogue_reasoning_diagnostics import RevisionRecoveryRun
                                                bench = RevisionRecoveryRun()
                                            elif profile == 'turn_reasoning':
                                                from allma_model.llm.dialogue_reasoning_diagnostics import DialogueReasoningRun
                                                bench = DialogueReasoningRun()
                                            elif profile == 'checkin':
                                                from allma_model.llm.checkin_diagnostics import CheckinRun
                                                bench = CheckinRun()
                                            elif profile == 'runtime_followup':
                                                from allma_model.llm.cancellation_diagnostics import RuntimeFollowupRun
                                                bench = RuntimeFollowupRun()
                                                bench.voice_probe = getattr(getattr(app, 'chat_screen', None), 'tts', None)
                                            elif profile == 'long_session':
                                                from allma_model.llm.endurance import LongSessionRun
                                                bench = LongSessionRun()
                                                bench.voice_probe = getattr(getattr(app, 'chat_screen', None), 'tts', None)
                                            elif profile == 'tool_learning':
                                                from reliability_android import AndroidToolLearningRun
                                                bench = AndroidToolLearningRun()
                                            elif profile == 'decider':
                                                from allma_model.agency_system.decision_diagnostics import DecisionDiagnosticRun
                                                bench = DecisionDiagnosticRun()
                                            elif profile == 'operational':
                                                from reliability_android import AndroidReliabilityRun
                                                bench = AndroidReliabilityRun()
                                            elif profile == 'incremental_storage':
                                                from reliability_android import AndroidIncrementalStorageRun
                                                bench = AndroidIncrementalStorageRun()
                                            elif profile == 'recall_storage':
                                                from reliability_android import AndroidRecallStorageRun
                                                bench = AndroidRecallStorageRun()
                                            elif profile == 'memory_recovery':
                                                from reliability_android import AndroidMemoryRecoveryRun
                                                bench = AndroidMemoryRecoveryRun()
                                            elif profile == 'preservation':
                                                from reliability_android import AndroidPreservationRun
                                                bench = AndroidPreservationRun()
                                            elif profile == 'idle_runtime':
                                                from reliability_android import AndroidIdleWorkRun
                                                bench = AndroidIdleWorkRun()
                                            elif profile == 'goal_planning':
                                                from allma_model.agency_system.plan_diagnostics import PlanDiagnosticRun
                                                bench = PlanDiagnosticRun()
                                            elif profile == 'plan_review':
                                                from reliability_android import AndroidPlanReviewRun
                                                bench = AndroidPlanReviewRun()
                                            elif profile == 'plan_comparison':
                                                from allma_model.agency_system.plan_comparison import PlanReviewComparisonRun
                                                bench = PlanReviewComparisonRun()
                                            elif profile == 'dialogue_recovery':
                                                from allma_model.utils.dialogue_diagnostics import DialogueRecoveryRun
                                                bench = DialogueRecoveryRun()
                                            elif profile == 'plan_experience':
                                                from reliability_android import AndroidPlanExperienceRun
                                                bench = AndroidPlanExperienceRun()
                                            elif profile == 'plan_transfer':
                                                from allma_model.agency_system.plan_diagnostics import PlanExperienceModelRun
                                                bench = PlanExperienceModelRun()
                                            elif profile == 'goal_continuity':
                                                from reliability_android import AndroidGoalContinuityRun
                                                bench = AndroidGoalContinuityRun()
                                            elif profile == 'learning_storage':
                                                from reliability_android import AndroidLearningStorageRun
                                                bench = AndroidLearningStorageRun()
                                            elif profile == 'long_history':
                                                from reliability_android import AndroidLongHistoryRun
                                                bench = AndroidLongHistoryRun()
                                            else:
                                                bench = CognitiveBenchmark(profile=profile)
                                            self.bridge.active_benchmark = bench
                                            
                                            def on_progress(curr, tot, txt):
                                                self.bridge.update_benchmark_ui(curr, tot, txt)
                                                
                                            bench.setup_brain(existing_brain=brain_ref)
                                            bench.run_tests(progress_callback=on_progress)
                                            
                                            print("✅ Benchmark Completed via UI Trigger")
                                            # Completion Toast
                                            completion = ("Telefono caldo; prova fermata e report salvato" if bench.manifest.get('stop_reason') == 'thermal_pause' else "Benchmark interrotto; report parziale salvato" if bench.manifest.get('cancelled') else "Benchmark completato; valuta le risposte nel report")
                                            Clock.schedule_once(lambda dt, msg=completion: app.show_toast(msg))
                                            
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
                                            self.bridge.update_benchmark_ui(100, 100, "Fermato per temperatura" if bench.manifest.get('stop_reason') == 'thermal_pause' else "Interrotto" if bench.manifest.get('cancelled') else "Completato!")
                                            Clock.schedule_once(lambda dt: self.bridge.execute_js("if(window.benchmarkUI) window.benchmarkUI.close()"), 2.0)
                                            
                                        except Exception as e:
                                            err_msg = f"ERR: {str(e)[:60]}"
                                            print(f"❌ {err_msg}")
                                            import traceback
                                            traceback.print_exc()
                                            Clock.schedule_once(lambda dt, msg=err_msg: app.show_toast(msg))
                                            # Close UI on Error
                                            Clock.schedule_once(lambda dt: self.bridge.execute_js("if(window.benchmarkUI) window.benchmarkUI.close()"), 3.0)
                                        finally:
                                            try:
                                                if bench is not None:
                                                    bench.close()
                                            finally:
                                                self.bridge.active_benchmark = None
                                                self.bridge.benchmark_running = False
                                            
                                    threading.Thread(target=run_bench, daemon=True).start()
                                    return

                            self.callback(clean_val)
                    except Exception as e:
                        print(f"Bridge Decode Error: {type(e).__name__}")
                        # A malformed/failed control must never fall through as chat.

        @run_on_ui_thread
        def create_webview_ui():
            if self._closed:
                return
            try:
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                self.webview = WebView(activity)
                self._install_back_handler(activity)
                # USB-authorized WebView inspection only in debuggable APKs.
                info = activity.getApplicationInfo()
                if info.flags & autoclass('android.content.pm.ApplicationInfo').FLAG_DEBUGGABLE:
                    WebView.setWebContentsDebuggingEnabled(True)
                
                # Settings
                settings = self.webview.getSettings()
                from allma_model.ui.web_assets import configure_webview
                configure_webview(settings)
                
                self.webview.setBackgroundColor(Color.parseColor("#FAF9F5"))
                self.webview.setAlpha(0.0)
                
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
                            
                            # Keep the WebView inside system bars and resize for IME.
                            # NO_LIMITS forced Android to pan the entire header offscreen.
                            activity_window.clearFlags(LayoutParams.FLAG_LAYOUT_NO_LIMITS | LayoutParams.FLAG_FULLSCREEN)
                            activity_window.setSoftInputMode(LayoutParams.SOFT_INPUT_ADJUST_RESIZE)
                            if Version.SDK_INT >= 30:
                                activity_window.setDecorFitsSystemWindows(True)
                            activity_window.addFlags(-2147483648)  # DRAWS_SYSTEM_BAR_BACKGROUNDS
                            from allma_model.ui.android_bars import AndroidBars
                            bar_color = AndroidBars.color_hex()
                            activity_window.setStatusBarColor(Color.parseColor(bar_color))
                            activity_window.setNavigationBarColor(Color.parseColor(bar_color))
                            decorView = activity_window.getDecorView()
                            sys_flags = decorView.getSystemUiVisibility()
                            sys_flags &= ~(512 | 1024 | 4 | 2 | 2048 | 4096)
                            sys_flags |= 256
                            if AndroidBars.dark:
                                sys_flags &= ~(8192 | 16)
                            else:
                                sys_flags |= 8192 | 16
                            decorView.setSystemUiVisibility(sys_flags)
                            AndroidBars.hide_navigation(activity_window)

                            # 6. FORCE LAYOUT
                            decorView.requestLayout()
                            log("System bars and keyboard resize applied.")

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
                settings_css = ""
                js = ""
                
                with open(os.path.join(base_path, 'index.html'), 'r') as f:
                    html = f.read()
                with open(os.path.join(base_path, 'style_v24.css'), 'r') as f:
                    css = f.read()
                settings_path = os.path.join(base_path, 'settings_ui.css')
                if os.path.exists(settings_path):
                    with open(settings_path, 'r') as f:
                        settings_css = f.read()

                # Load marked.js
                marked_js = ""
                marked_path = os.path.join(base_path, 'marked.min.js')
                if os.path.exists(marked_path):
                    with open(marked_path, 'r') as f:
                        marked_js = f.read()

                with open(os.path.join(base_path, 'startup_transition.js'), 'r') as f:
                    js = f.read()
                with open(os.path.join(base_path, 'script_v24.js'), 'r') as f:
                    js += '\n' + f.read()
                with open(os.path.join(base_path, 'voice_controls.js'), 'r') as f:
                    js += '\n' + f.read()
                with open(os.path.join(base_path, 'brain_geometry.js'), 'r') as f:
                    js += '\n' + f.read()
                with open(os.path.join(base_path, 'brain_anatomy.js'), 'r') as f:
                    js += '\n' + f.read()
                with open(os.path.join(base_path, 'brain_view.js'), 'r') as f:
                    js += '\n' + f.read()
                with open(os.path.join(base_path, 'learning_ui.js'), 'r') as f:
                    js += '\n' + f.read()
                with open(os.path.join(base_path, 'web_reference_ui.js'), 'r') as f:
                    js += '\n' + f.read()
                with open(os.path.join(base_path, 'navigation.js'), 'r') as f:
                    js += '\n' + f.read()

                # Patch JS for polling
                js_patch = """
                console.log("ALLMA_DEBUG: Starting Bridge Patch...");
                window.msgQueue = window.msgQueue || [];
                window.allmaNativeClipboard = true;
                window.allmaNativeStartup = true;
                // API called by UI
                function sendMessage(text) {
                     window.msgQueue.push(text);
                     // Visual confirmation
                     // console.log("ALLMA_DEBUG: Enqueue " + text);
                }
                window.pyBridge = {
                    postMessage: function(text) {
                        window.msgQueue.push(text);
                        console.log("Buffered UI event");
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
                            action: 'run_benchmark',
                            profile: (document.getElementById('benchmark-profile') || {}).value || 'quick'
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
                        this.overlay.style.cssText = "position:fixed; bottom:20px; left:5%; width:90%; background:var(--modal-bg); border:1px solid var(--border-color); border-radius:24px; color:var(--text-primary); padding:15px; z-index:9999; box-shadow:0 10px 30px rgba(0,0,0,0.5); font-family:sans-serif; transition: opacity 0.5s ease;";
                        this.overlay.id = "benchmark-overlay";
                        
                        // Title
                        var title = document.createElement('div');
                        title.innerText = "🧠 Benchmark Cognitivo in Corso...";
                        title.style.cssText = "color:var(--text-primary); font-size:14px; font-weight:bold; margin-bottom:10px;";
                        this.overlay.appendChild(title);
                        
                        // Progress Container
                        var progressBg = document.createElement('div');
                        progressBg.style.cssText = "width:100%; height:8px; background:var(--subtle); border-radius:4px; overflow:hidden;";
                        
                        // Progress Bar
                        this.bar = document.createElement('div');
                        this.bar.style.cssText = "width:0%; height:100%; background:var(--primary-color); transition: width 0.3s ease;";
                        progressBg.appendChild(this.bar);
                        this.overlay.appendChild(progressBg);
                        
                        // Status Text
                        this.text = document.createElement('div');
                        this.text.innerText = "Avvio...";
                        this.text.style.cssText = "color:var(--text-secondary); font-size:12px; margin-top:8px; text-align:right;";
                        this.overlay.appendChild(this.text);
                        var cancel = document.createElement('button');
                        cancel.innerText = 'Interrompi e salva';
                        cancel.style.cssText = 'margin-top:10px;padding:8px 12px;border:0;border-radius:12px;background:var(--subtle);color:var(--text-primary);';
                        cancel.onclick = function() {
                            if (window.pyBridge) window.pyBridge.postMessage(JSON.stringify({type:'action',action:'cancel_benchmark'}));
                            cancel.disabled = true;
                            cancel.innerText = 'Interruzione in corso…';
                        };
                        this.overlay.appendChild(cancel);
                        
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
                
                from allma_model.ui.web_assets import inline_stylesheets
                html = inline_stylesheets(html, base_path)

                # INLINE REPLACEMENT
                # CRITICAL FIX: Do NOT use f-strings for CSS/JS as they contain curly braces!
                # Robust Injection Strategy:
                # 1. Remove existing link/script tags to avoid double loading
                html = re.sub(r'<link[^>]+rel=["\']stylesheet["\'][^>]*>', '', html, flags=re.IGNORECASE)
                html = re.sub(r'<script[^>]+src=["\'][^"\']+["\'][^>]*></script>', '', html, flags=re.IGNORECASE)
                
                # Global Error Handler
                error_handler = """
                window.onerror = function(msg, url, line, col, error) {
                    var extra = !col ? '' : '\\ncolumn: ' + col;
                    extra += !error ? '' : '\\nerror: ' + error;
                    console.error("Error: " + msg + "\\nurl: " + url + "\\nline: " + line + extra);
                    return true;
                };
                """
                
                full_js = error_handler + "\n" + marked_js + "\n" + js_patch + "\n" + js
                
                # 2. Inject CSS/JS into head/body explicitly
                # Native window now reserves system bars; avoid double CSS insets.
                style_tag = '<style>:root{--native-top:0px;--native-bottom:0px;}</style>'
                script_tag = '<script>' + full_js + '</script>'
                
                html = html.replace('</head>', style_tag + '</head>')
                html = html.replace('</body>', script_tag + '</body>')
                
                # Load Data with Fake Origin to fix CORS/Security restrictions
                # Using https://app.allma/ allows local storage and secure context features
                from allma_model.ui.web_assets import isolate_document
                html = isolate_document(html)
                self.webview.loadDataWithBaseURL("https://app.allma/", html, "text/html", "utf-8", None)
                print("WebView Loaded with Robust Inlining & Fake Origin.")
                
                # Layout Params
                LayoutParams = autoclass('android.view.ViewGroup$LayoutParams')
                params = LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT)
                
                # Add to Activity
                activity.addContentView(self.webview, params)
                self._startup_reveal_event = Clock.schedule_once(lambda dt:self.reveal_startup(),5)
                
                # Start Polling Loop
                self._start_polling()
                
            except Exception as e:
                print(f"Error initializing WebView: {e}")
                import traceback
                traceback.print_exc()
                self.running = False
                if self.webview is not None:
                    self.webview.destroy()
                    self.webview = None
                callback = getattr(self, 'startup_error', None)
                if callback is not None:
                    Clock.schedule_once(lambda dt: callback('Non riesco ad aprire la chat in sicurezza. Riapri ALLMA.'), 0)

        create_webview_ui()

    def reveal_startup(self):
        """Blend the first painted document over the native startup panel once."""
        self._startup_ready = True
        event = getattr(self, '_startup_reveal_event', None)
        if event:
            event.cancel()
            self._startup_reveal_event = None
        if self._closed or self._startup_revealed or not self.running:
            return
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def reveal():
            if self._closed or self._startup_revealed or not self.running or self.webview is None:
                return
            from startup_ui import native_motion_allowed
            motion = native_motion_allowed()
            self._startup_revealed = True
            if motion:
                self.webview.animate().alpha(1.0).setDuration(320).start()
            else:
                self.webview.setAlpha(1.0)
            self._evaluate_js('window.allmaStartup && window.allmaStartup.reveal('+
                              json.dumps({'native':True,'motion':motion})+')',None)
            print('ALLMA startup transition ready.')
        reveal()

    def background_app(self):
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def minimize():
            if not self._closed:
                from jnius import autoclass
                autoclass('org.kivy.android.PythonActivity').mActivity.moveTaskToBack(True)
        minimize()

    def _install_back_handler(self, activity):
        """Called on Android UI thread; IME handles its own Back first."""
        from jnius import autoclass, PythonJavaClass, java_method
        bridge=self
        class BackKey(PythonJavaClass):
            __javacontext__='app'
            __javainterfaces__=['android/view/View$OnKeyListener']
            @java_method('(Landroid/view/View;ILandroid/view/KeyEvent;)Z')
            def onKey(self,view,code,event):
                if code!=4:return False
                if event.getAction()==1:
                    bridge.execute_js('window.handleAndroidBack && window.handleAndroidBack()')
                return True
        self._back_key=BackKey()
        self.webview.setOnKeyListener(self._back_key)
        if autoclass('android.os.Build$VERSION').SDK_INT>=33:
            class BackGesture(PythonJavaClass):
                __javacontext__='app'
                __javainterfaces__=['android/window/OnBackInvokedCallback']
                @java_method('()V')
                def onBackInvoked(self):
                    bridge.execute_js('window.handleAndroidBack && window.handleAndroidBack()')
            self._back_callback=BackGesture()
            self._back_dispatcher=activity.getOnBackInvokedDispatcher()
            self._back_dispatcher.registerOnBackInvokedCallback(0,self._back_callback)

    def _start_polling(self):
        if self.running and not self._closed and self._poll_event is None:
            self._poll_event = Clock.schedule_interval(self._poll_js, 0.35)

    def pause(self):
        if self.is_android and self.webview is not None:
            self.call_js_function('brainVisibility', 'false')
        self.running = False
        self._poll_inflight = False
        self._stream_delivery.clear()
        if self._poll_event is not None:
            self._poll_event.cancel()
            self._poll_event = None

    def resume(self):
        if not self._closed:
            self.running = True
            if getattr(self,'_startup_ready',False) and not getattr(self,'_startup_revealed',False):
                self.reveal_startup()
            if self.is_android and self.webview is not None:
                self.call_js_function('brainVisibility', 'true')
                self._start_polling()

    def close(self):
        if self._closed:
            return
        self.pause()
        event = getattr(self, '_startup_reveal_event', None)
        if event:
            event.cancel()
            self._startup_reveal_event = None
        if getattr(self,'backup_controller',None):self.backup_controller.close()
        self._closed = True
        if self.is_android:
            from android.runnable import run_on_ui_thread
            @run_on_ui_thread
            def destroy():
                dispatcher=getattr(self,'_back_dispatcher',None)
                if dispatcher is not None:
                    dispatcher.unregisterOnBackInvokedCallback(self._back_callback)
                    self._back_dispatcher=None
                view, self.webview = self.webview, None
                if view is not None:
                    view.stopLoading()
                    parent = view.getParent()
                    if parent is not None:
                        parent.removeView(view)
                    view.destroy()
            destroy()
        else:
            self.webview = None

    def _evaluate_js(self, code, callback):
        if not self._closed and self.webview is not None:
            self.webview.evaluateJavascript(code, callback)

    def _poll_js(self, dt):
        if not self.running or not self.webview or not self.poll_callback or self._poll_inflight:
            return
        self._poll_inflight = True
            
        from android.runnable import run_on_ui_thread
        
        @run_on_ui_thread
        def run_poll():
            if not self.running or self._closed or self.webview is None:
                self._poll_inflight = False
                return
            # fetchPending() returns the string or null
            try:
                self._evaluate_js("window.fetchPending()", self.poll_callback)
            except Exception:
                self._poll_inflight = False
                logging.exception('WebView polling failed')
            
        run_poll()

    def send_message_to_js(self, text, sender='bot', thought_text=None):
        if not self.webview:
            print(f"Mock Send to JS sender={sender}")
            return
            
        # Escape strings for JS
        safe_text = json.dumps(text)
        safe_sender = json.dumps(sender)
        safe_thought = json.dumps(thought_text) if thought_text else "null"
        
        js_code = (
            "(function(){"
            "try{"
            "window.__allmaQueue=window.__allmaQueue||[];"
            "var fn=window.addMessage;"
            "var args=[" + safe_text + "," + safe_sender + "," + safe_thought + "];"
            "if(typeof fn==='function'){fn.apply(null,args);}else{window.__allmaQueue.push({fn:'addMessage',args:args});}"
            "}catch(e){try{console.warn('ALLMA bridge addMessage failed',e);}catch(_){}}"
            "})();"
        )
        
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def run_js():
            self._evaluate_js(js_code, None)
            
        run_js()

    def call_js_function(self, fn_name: str, args_js: str = ""):
        if not self.webview:
            return
        import json
        safe_fn = json.dumps(fn_name)
        args_part = args_js.strip()
        args_array = "[]" if not args_part else f"[{args_part}]"
        js_code = (
            "(function(){"
            "try{"
            "window.__allmaQueue=window.__allmaQueue||[];"
            f"var fnName={safe_fn};"
            f"var args={args_array};"
            "var fn=window[fnName];"
            "if(typeof fn==='function'){fn.apply(null,args);}else{window.__allmaQueue.push({fn:fnName,args:args});}"
            "}catch(e){try{console.warn('ALLMA bridge call failed',e);}catch(_){}}"
            "})();"
        )
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def run_js():
            self._evaluate_js(js_code, None)
        run_js()

    def handle_avatar_configuration(self, presentation, request_id=None):
        # Ownership comes from the active native session, never the WebView.
        owner = getattr(self.core, '_current_user_id', None) or 'user_default'
        try:
            if not hasattr(self, '_avatar_presence'):
                from allma_model.utils.avatar_presence import AvatarPresence
                self._avatar_presence = AvatarPresence(getattr(self.core, 'db_path', None))
            self._avatar_presence.appearance(owner, presentation)
            if presentation is None:
                raise ValueError('Explicit choice required')
            result = {'ok': True, 'presentation': presentation}
        except Exception:
            result = {'ok': False, 'message': 'Non è stato possibile salvare l’aspetto. Riprova.'}
        result['request_id'] = request_id if isinstance(request_id, str) and len(request_id) <= 100 else None
        self.call_js_function('receiveAvatarConfiguration', json.dumps(result))
        if result['ok']:
            self.handle_brain_activity()

    def handle_brain_activity(self, after=0):
        activity = getattr(self.core, 'brain_activity', None)
        if activity is None:
            payload = {'available': False}
        else:
            payload = activity.snapshot(after)
            payload['available'] = True
            dream_manager = getattr(self.core, 'dream_manager', None)
            dreaming = bool(dream_manager and dream_manager.is_dreaming)
            payload['dreaming'] = dreaming
            for node in payload['nodes']:
                if node['id'] == 'dreams':
                    node['available'] = dream_manager is not None
                    node['state'] = {'phase':'running' if dreaming else 'idle'}
            registered = getattr(getattr(self.core, 'module_orchestrator', None), 'modules', {})
            adapters = {'curiosity','emotional_adaptation','creativity','planning','perception',
                        'language_processing','personality_style','meta_learning','cognitive_tracking'}
            for node in payload['nodes']:
                if node['id'] in adapters:
                    config = registered.get(node['id'])
                    node['available'] = config is not None
                    node['enabled'] = bool(config and config.enabled)
            engine = getattr(self.core, '_llm', None)
            from pathlib import Path
            name = getattr(engine, 'model_path', None)
            payload['model'] = Path(name).name if isinstance(name, (str, Path)) else None
            personality = getattr(self.core, 'coalescence_processor', None)
            owner = getattr(self.core, '_current_user_id', None) or 'user_default'
            if personality is not None:
                expression = personality.expression_view(owner)
                outcomes = expression.get('outcome_learning',{})
                contexts = {'general':'nel dialogo generale','explanation':'nelle spiegazioni','support':'nel sostegno emotivo'}
                labels = {'brief':'risposte essenziali','detailed':'risposte approfondite',
                          'gentle':'delicatezza','direct':'franchezza','formal':'tono formale','informal':'tono informale',
                          'light':'umorismo leggero','serious':'tono serio','restrained':'meno domande aggiuntive','exploratory':'domande di approfondimento'}
                payload['personality_development'] = {
                    'declared':len(expression['preferences']),
                    'integrated':sum(item['stage']=='integrated' for item in expression['tendencies'].values()),
                    'suspended':sum(item['stage']=='suspended' for item in expression['tendencies'].values()),
                    'assessments':outcomes.get('strong_feedback',0),
                    'courtesy':outcomes.get('weak_feedback',0),
                    'growth':[f"{labels[item['value']]} {contexts[context]}: "
                              f"{item['positive']} riscontri positivi, {item['negative']} negativi; "
                              + ('consolidata' if item['stage']=='integrated' else 'in osservazione')
                              for context,axes in outcomes.get('contexts',{}).items() for item in axes.values()]}
        self.call_js_function('receiveBrainActivity', json.dumps(payload))

    def start_stream(self, request_id=None):
        self._stream_delivery.start(request_id)
        self.call_js_function("startStream", json.dumps(request_id))

    def stream_chunk(self, text, is_thought=False, request_id=None):
        self._stream_delivery.push(text, is_thought, request_id)

    def reference_activity(self, payload, request_id=None):
        self.call_js_function('receiveReferenceActivity',json.dumps(payload)+', '+json.dumps(request_id))

    def end_stream(self, final_content=None, request_id=None, generation=None, plan_review=None, origin=None):
        self._stream_delivery.finish(request_id)
        status = (generation or {}).get('status')
        self.call_js_function("endStream", f"{json.dumps(final_content)}, {json.dumps(request_id)}, {json.dumps(status)}, {json.dumps(plan_review)}, {json.dumps(origin)}")

    def update_voice_internal_state(self, payload):
        if not self.webview:
            return
        import json
        safe_payload = json.dumps(payload if payload is not None else {})
        self.call_js_function("updateVoiceInternalState", safe_payload)

    def _notifications(self):
        if not hasattr(self, '_notification_manager'):
            from pathlib import Path
            from allma_model.ui.system_notifications import SystemNotifications
            self._notification_manager = SystemNotifications(Path(self.core.db_path).resolve().parent/'notifications.json')
        return self._notification_manager

    def handle_decider_action(self, action, enabled=None):
        runtime = None
        try:
            runtime = getattr(self.core, 'decision_runtime', None)
            payload = ({'error':'Attendi il caricamento di ALLMA.'} if runtime is None else
                       runtime.configure(enabled) if action == 'set_decider' else runtime.status())
        except Exception:
            payload = dict(runtime.status() if runtime is not None else {},
                           error='Non sono riuscita a salvare la preferenza del decisore.')
        self.execute_js('window.deciderUI && window.deciderUI.update(' + json.dumps(payload) + ')')

    def open_reference(self, url):
        from allma_model.utils.public_references import reference_link_allowed
        if not self.is_android or not reference_link_allowed(url):
            return False
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def open_link():
            try:
                from jnius import autoclass
                intent=autoclass('android.content.Intent')('android.intent.action.VIEW',
                    autoclass('android.net.Uri').parse(url))
                autoclass('org.kivy.android.PythonActivity').mActivity.startActivity(intent)
            except Exception:
                logging.warning('Public reference link unavailable')
        open_link()
        return True

    def handle_web_action(self, action, enabled=None):
        service=getattr(self.core,'public_references',None)
        def work():
            try:
                payload=({'enabled':False,'error':'Attendi il caricamento di ALLMA.'} if service is None else
                    service.configure(enabled) if action=='set_web_access' else service.status())
            except Exception:
                payload=dict(service.status() if service else {'enabled':False},
                    error='Non riesco a salvare la preferenza Internet.')
            if not self._closed:
                Clock.schedule_once(lambda dt:self.execute_js('window.webReferenceUI && window.webReferenceUI.update('
                    +json.dumps(payload)+')'))
        threading.Thread(target=work,daemon=True,name='WebPreference').start()

    def handle_notification_action(self, action, enabled=None):
        def update(payload):
            if not self._closed:
                self.execute_js('window.notificationUI && window.notificationUI.update(' + json.dumps(payload) + ')')
        try:
            manager = self._notifications()
            if action == 'set_notifications':
                manager.configure(enabled, update)
            else:
                extra = {}
                if action == 'test_notification':
                    extra['test_sent'] = manager.publish('test', explicit_test=True)
                elif action == 'notification_settings' and manager.backend:
                    manager.backend.open_settings()
                update(dict(manager.status(), **extra))
        except Exception:
            update({'error': 'Notifiche non disponibili. Riprova dalle impostazioni Android.'})

    def notify_event(self, kind):
        try:
            return self._notifications().publish(kind)
        except Exception:
            logging.warning('System notification unavailable')
            return False

    def handle_model_action(self, action, key=None):
        """Never hash/download/load a GGUF on the UI thread."""
        from kivy.app import App
        app = App.get_running_app()
        app = getattr(app, 'internal_app', app)
        screen = getattr(app, 'chat_screen', None)
        if screen is None and hasattr(app, 'sm') and app.sm.has_screen('chat'):
            screen = app.sm.get_screen('chat')
        core = self.core if self.core is not None else getattr(screen, 'core', None)
        if core is None:
            return
        if not hasattr(self, '_model_manager'):
            from allma_model.llm.model_manager import ModelManager
            self._model_manager = ModelManager(core)
        def notify(payload):
            if self._closed:
                return
            js = 'if(window.modelUI) window.modelUI.update(' + json.dumps(payload, ensure_ascii=False) + ')'
            Clock.schedule_once(lambda dt: self.execute_js(js))
        def work():
            last_progress = [0.]
            def progress(payload):
                now = time.monotonic()
                if payload.get('phase') != 'download' or now-last_progress[0] >= .25 or payload.get('progress') == 1:
                    last_progress[0] = now
                    notify(payload)
            try:
                if action == 'apply_model':
                    self._model_manager.apply(key, progress)
                    self.notify_event('model')
                notify(dict(phase='ready', **self._model_manager.snapshot()))
            except Exception as exc:
                notify({'phase':'error', 'error': str(exc)})
        threading.Thread(target=work, daemon=True, name='ModelChoice').start()

    def update_benchmark_ui(self, current, total, text):
        """Aggiorna l'overlay di progresso del benchmark."""
        if not self.webview: return
        import json
        safe_text = json.dumps(text)
        js_cmd = f"if(window.benchmarkUI) window.benchmarkUI.update({current}, {total}, {safe_text})"
        
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def run_js():
            self._evaluate_js(js_cmd, None)
        run_js()


    def update_synergy(self, percentage: int, status_text: str):
        """Aggiorna il grafico di sinergia/apprendimento."""
        if not self.webview:
            print(f"[WebViewBridge] Synergy update (No WebView): {percentage}% - {status_text}")
            return
            
        js_cmd = "updateAllmaStatus(" + json.dumps(percentage) + "," + json.dumps(status_text) + ")"
        
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def run_js():
            self._evaluate_js(js_cmd, None)
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
            self._evaluate_js(js_cmd, None)
        run_js()

    def update_voice_text(self, text):
        """Aggiorna il testo nell'overlay vocale."""
        if not self.webview: return
        # Log to verify attempting update
        print("Bridge: Voice transcript updated")
        
        import json
        safe_text = json.dumps(text)
        js_cmd = f"window.updateVoiceText({safe_text})"
        
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def run_js():
            self._evaluate_js(js_cmd, None)
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
            self._evaluate_js(js_cmd, None)
        run_js()

    def copy_message(self, request_id, text):
        """Explicit user copy, confirmed only after Android accepts the clip."""
        if not isinstance(request_id, str) or not re.fullmatch(r'copy-\d{1,12}', request_id):
            return
        def done(success):
            self.execute_js('window.messageCopyResult && window.messageCopyResult(' +
                            json.dumps(request_id) + ',' + json.dumps(success) + ')')
        if not isinstance(text, str) or not text.strip() or len(text.encode('utf-8')) > 500000:
            done(False)
            return
        from jnius import autoclass, cast
        from android.runnable import run_on_ui_thread

        @run_on_ui_thread
        def copy_ui():
            try:
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                clipboard = cast('android.content.ClipboardManager', activity.getSystemService('clipboard'))
                clip = autoclass('android.content.ClipData').newPlainText('ALLMA', text)
                clipboard.setPrimaryClip(clip)
                done(True)
            except Exception:
                done(False)
        copy_ui()

    def share_text_content(self, text, subject="ALLMA Benchmark Result"):
        """Apre il menu di condivisione nativo Android con il testo fornito."""
        if not self.is_android:
            print("[SHARE] Text sharing unavailable on this platform")
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

    def execute_js(self, js_code):
        """
        Esegue codice JS arbitrario.
        NECESSARIO per ChatView che chiama questo metodo per status update e thought bubbles.
        """
        if not self.webview: return
        
        from android.runnable import run_on_ui_thread
        @run_on_ui_thread
        def run_js():
            wrapped = "(function(){try{" + str(js_code) + "}catch(e){try{console.warn('ALLMA execute_js failed',e);}catch(_){}}})();"
            self._evaluate_js(wrapped, None)
        run_js()
