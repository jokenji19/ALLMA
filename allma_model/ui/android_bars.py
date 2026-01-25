from kivy.utils import platform
from kivy.clock import Clock

print(f"!!!! [AndroidBars] MODULE IMPORTED. Platform: {platform} !!!!")

class AndroidBars:
    @staticmethod
    def configure_bars():
        """Called once, initiates the retry loop"""
        print(f"!!!! [AndroidBars] configure_bars called. Platform: {platform} !!!!")
        
        if platform != 'android':
            print(f"!!!! [AndroidBars] ABORTING: Platform is {platform}, not 'android' !!!!")
            return
        
        # Try immediately and schedule retries
        AndroidBars._attempt_set_bars(0)
        Clock.schedule_once(lambda dt: AndroidBars._attempt_set_bars(1), 0.5)
        Clock.schedule_once(lambda dt: AndroidBars._attempt_set_bars(2), 1.5)
        Clock.schedule_once(lambda dt: AndroidBars._attempt_set_bars(3), 3.0)

    @staticmethod
    def _attempt_set_bars(attempt):
        print(f"!!!! [AndroidBars] _attempt_set_bars attempt {attempt} starting !!!!")
        try:
            from jnius import autoclass
            from android.runnable import run_on_ui_thread

            Color = autoclass("android.graphics.Color")
            WindowManager = autoclass("android.view.WindowManager")
            View = autoclass("android.view.View")
            Build = autoclass("android.os.Build") 
            
            @run_on_ui_thread
            def _set_bars_ui():
                try:
                    print(f"!!!! [AndroidBars] UI Thread - Attempt {attempt} executing !!!!")
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    activity = PythonActivity.mActivity
                    window = activity.getWindow()
                    decor_view = window.getDecorView()

                    # 1. HANDLE CUTOUT (NOTCH) - API 28+
                    if Build.VERSION.SDK_INT >= 28:
                        params = window.getAttributes()
                        params.layoutInDisplayCutoutMode = 1 
                        window.setAttributes(params)
                        print(f"[AndroidBars] Cutout mode set to SHORT_EDGES")

                    # 2. VISIBILITY FLAGS
                    new_flags = decor_view.getSystemUiVisibility()
                    new_flags |= 0x00002000 # Light Status
                    if Build.VERSION.SDK_INT >= 26:
                        new_flags |= 0x00000010 # Light Nav
                    
                    decor_view.setSystemUiVisibility(new_flags)

                    # 3. WINDOW FLAGS
                    window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
                    window.clearFlags(WindowManager.LayoutParams.FLAG_TRANSLUCENT_STATUS)
                    window.clearFlags(WindowManager.LayoutParams.FLAG_TRANSLUCENT_NAVIGATION)
                    
                    # 4. SET COLORS (WHITE)
                    white = Color.parseColor("#FFFFFF")
                    window.setStatusBarColor(white)
                    window.setNavigationBarColor(white)
                    
                    # 5. Nav Bar Divider
                    if Build.VERSION.SDK_INT >= 28:
                        window.setNavigationBarDividerColor(Color.parseColor("#00FFFFFF"))

                    print(f"!!!! [AndroidBars] Attempt {attempt}: SUCCESS !!!!")
                    
                except Exception as inner_e:
                    print(f"!!!! [AndroidBars] Attempt {attempt} INNER ERROR: {inner_e} !!!!")

            _set_bars_ui()

        except Exception as e:
            print(f"!!!! [AndroidBars] scheduling error: {e} !!!!")
