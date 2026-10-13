package org.allma.voice;

import android.speech.tts.UtteranceProgressListener;

/** Adapt the Android abstract listener to an interface supported by PyJNIus. */
public final class TtsProgressListener extends UtteranceProgressListener {
    public interface Events {
        void onStart(String id);
        void onDone(String id);
        void onError(String id, int code);
    }
    private final Events events;
    public TtsProgressListener(Events events) { this.events = events; }
    @Override public void onStart(String id) { events.onStart(id); }
    @Override public void onDone(String id) { events.onDone(id); }
    @Override public void onError(String id) { events.onError(id, -1); }
    @Override public void onError(String id, int code) { events.onError(id, code); }
}
