package org.allma.voice;

import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.speech.RecognitionSupport;
import android.speech.RecognitionSupportCallback;
import android.speech.SpeechRecognizer;
import org.json.JSONArray;
import org.json.JSONObject;

/** Language inventory only. Does not record audio or start a download. */
public final class SpeechSupport {
    public interface Events {
        void onSupport(String json);
        void onUnavailable(int code);
    }
    public static void check(Context context, SpeechRecognizer recognizer, Intent intent, Events events) {
        if (Build.VERSION.SDK_INT < 33) { events.onUnavailable(-1); return; }
        recognizer.checkRecognitionSupport(intent, context.getMainExecutor(), new RecognitionSupportCallback() {
            @Override public void onSupportResult(RecognitionSupport support) {
                try {
                    JSONObject result = new JSONObject();
                    result.put("installed", new JSONArray(support.getInstalledOnDeviceLanguages()));
                    result.put("supported", new JSONArray(support.getSupportedOnDeviceLanguages()));
                    result.put("pending", new JSONArray(support.getPendingOnDeviceLanguages()));
                    events.onSupport(result.toString());
                } catch (Exception e) { events.onUnavailable(-2); }
            }
            @Override public void onError(int code) { events.onUnavailable(code); }
        });
    }
    private SpeechSupport() {}
}
