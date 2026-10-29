package org.allma.runtime;

import android.app.ActivityManager;
import android.app.Application;
import android.app.ApplicationExitInfo;
import android.content.Context;
import android.content.pm.PackageInfo;
import android.os.Build;
import android.os.Process;
import android.os.SystemClock;
import android.webkit.WebView;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import org.json.JSONArray;
import org.json.JSONObject;

/** No personal data: a per-process random token binds markers to exit records. */
public final class NativeProcessHealth {
    private static String cachedOwner;
    private static long lastPublished = -1000;
    private NativeProcessHealth() {}

    public static synchronized String ownerForOperation(Context context, boolean fresh) throws Exception {
        if (cachedOwner == null) {
            JSONObject value = new JSONObject();
            value.put("pid", Process.myPid());
            value.put("package", context.getPackageName());
            value.put("process", Build.VERSION.SDK_INT >= 28
                    ? Application.getProcessName() : context.getPackageName());
            PackageInfo info = context.getPackageManager().getPackageInfo(context.getPackageName(), 0);
            value.put("build", Build.VERSION.SDK_INT >= 28 ? info.getLongVersionCode() : info.versionCode);
            if (Build.VERSION.SDK_INT >= 30) {
                value.put("token", "allma-native-v2-" + UUID.randomUUID().toString().replace("-", ""));
            }
            cachedOwner = value.toString();
        }
        long now = SystemClock.elapsedRealtime();
        if (Build.VERSION.SDK_INT >= 30 && (fresh || now - lastPublished >= 1000)) {
            String token = new JSONObject(cachedOwner).getString("token");
            // This slot is also used by Chromium. Refresh at the actual native
            // operation, not at a one-shot page-start event. Fast Decider calls
            // coalesce; infrequent model load/generation begins request fresh.
            String version = "unknown";
            try {
                PackageInfo webView = WebView.getCurrentWebViewPackage();
                if (webView != null) version = webView.versionName;
            } catch (Exception ignored) {}
            if (version == null || !version.matches("[A-Za-z0-9._-]{1,48}")) version = "unknown";
            String state = token + "|wv=" + version;
            ActivityManager manager = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
            manager.setProcessStateSummary(state.getBytes(StandardCharsets.US_ASCII));
            lastPublished = now;
        }
        return cachedOwner;
    }

    public static String exits(Context context, int pid) throws Exception {
        JSONArray values = new JSONArray();
        if (Build.VERSION.SDK_INT < 30 || pid <= 0) return values.toString();
        ActivityManager manager = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
        String process = context.getPackageName();
        for (ApplicationExitInfo info : manager.getHistoricalProcessExitReasons(process, pid, 32)) {
            if (info.getPid() != pid || !process.equals(info.getProcessName())) continue;
            JSONObject value = new JSONObject();
            value.put("pid", info.getPid());
            value.put("process", info.getProcessName());
            value.put("timestamp_ms", info.getTimestamp());
            value.put("reason", info.getReason());
            byte[] state = info.getProcessStateSummary();
            if (state != null) {
                String summary = new String(state, StandardCharsets.US_ASCII);
                if (summary.matches("allma-native-v2-[0-9a-f]{32}\\|wv=[A-Za-z0-9._-]{1,48}")) {
                    value.put("token", summary.substring(0, summary.indexOf('|')));
                    value.put("webview_version", summary.substring(summary.indexOf("|wv=") + 4));
                } else {
                    value.put("token", summary);
                }
            }
            values.put(value);
        }
        return values.toString();
    }
}
