package org.allma.voice;

import android.media.AudioAttributes;
import android.media.AudioFormat;
import android.media.AudioTrack;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Log;
import com.k2fsa.sherpa.onnx.*;
import java.util.ArrayDeque;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.BooleanSupplier;

/** Separate inference and playback so playing a sentence never stalls the next. */
public final class KokoroVoice {
    public interface Events { void onState(int request, String state, long millis, String message); }
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final ExecutorService audioWorker = Executors.newSingleThreadExecutor();
    private final AtomicInteger epoch = new AtomicInteger();
    private final Handler handler = new Handler(Looper.getMainLooper());
    private volatile boolean closed;
    private volatile AudioTrack player;
    private OfflineTts engine;
    private String directory;
    private final Runnable idleRelease = () -> {
        synchronized (KokoroVoice.this) {
            if (!closed) worker.execute(() -> { if (player == null) releaseEngine(); });
        }
    };
    private void releaseEngine() {
        if (engine != null) { engine.release(); engine = null; directory = null; }
    }
    private void initialize(String folder) {
        if (engine != null && folder.equals(directory)) return;
        releaseEngine();
        OfflineTtsKokoroModelConfig kokoro = new OfflineTtsKokoroModelConfig();
        kokoro.setModel(folder + "/model.int8.onnx");
        kokoro.setVoices(folder + "/voices.bin");
        kokoro.setTokens(folder + "/tokens.txt");
        kokoro.setDataDir(folder + "/espeak-ng-data");
        kokoro.setLang("it");
        OfflineTtsModelConfig model = new OfflineTtsModelConfig();
        model.setKokoro(kokoro); model.setNumThreads(2); model.setProvider("cpu"); model.setDebug(false);
        OfflineTtsConfig config = new OfflineTtsConfig();
        config.setModel(model); config.setMaxNumSentences(1);
        engine = new OfflineTts(null, config);
        directory = folder;
    }
    public synchronized void speak(String folder, String text, int speaker, float speed, int request, Events events) {
        if (closed) return;
        stop();
        final int token = epoch.get();
        handler.removeCallbacks(idleRelease);
        worker.execute(() -> {
            BooleanSupplier active = () -> !closed && epoch.get() == token;
            if (!active.getAsBoolean()) return;
            long began = SystemClock.elapsedRealtime();
            VoiceAudioBuffer queue = new VoiceAudioBuffer();
            boolean audioScheduled = false;
            try {
                events.onState(request, "starting", 0, "Preparo la voce naturale…");
                initialize(folder);
                synchronized (KokoroVoice.this) {
                    if (!active.getAsBoolean()) return;
                    final int rate = engine.sampleRate();
                    audioWorker.execute(() -> play(queue, rate, speaker, request, token, began, events));
                    audioScheduled = true;
                }
                final long[] previous = {SystemClock.elapsedRealtime()};
                engine.generateWithCallback(text, speaker, speed, new kotlin.jvm.functions.Function1<float[], Integer>() {
                    // JNI requires this typed overload, not erased invoke(Object).
                    @Override public Integer invoke(float[] samples) {
                        if (!active.getAsBoolean()) return 0;
                        long now = SystemClock.elapsedRealtime();
                        Log.i("ALLMA-Kokoro", "chunk speaker="+speaker+" generation_ms="+(now-previous[0])+" frames="+samples.length);
                        try {
                            boolean queued = queue.put(samples, active);
                            previous[0] = SystemClock.elapsedRealtime();
                            return queued ? 1 : 0;
                        } catch (InterruptedException error) { Thread.currentThread().interrupt(); return 0; }
                    }
                });
            } catch (Exception | LinkageError error) {
                queue.finish(error);
                if (active.getAsBoolean()) {
                    Log.e("ALLMA-Kokoro", "native_voice_failure", error);
                    if (!audioScheduled) events.onState(request,"error",SystemClock.elapsedRealtime()-began,"Voce naturale non disponibile. Seleziona Voce Android.");
                }
                releaseEngine();
            } finally {
                // Preserve an error already stored by the generator.
                queue.finish(queue.failure());
                if (!audioScheduled && !closed) handler.postDelayed(idleRelease,45000);
            }
        });
    }
    private void play(VoiceAudioBuffer queue, int rate, int speaker, int request, int token, long began, Events events) {
        BooleanSupplier active = () -> !closed && epoch.get() == token;
        AudioTrack track = null;
        long frames = 0;
        try {
            // Avoid saying a tiny heading/number then waiting for its sentence.
            // Normal first sentences already exceed this reserve: no extra wait.
            ArrayDeque<float[]> primed = new ArrayDeque<>();
            int reserve = 0;
            while (reserve < rate*2 && active.getAsBoolean()) {
                float[] first = queue.take(active);
                if (first == null) break;
                primed.add(first); reserve += first.length;
            }
            if (!active.getAsBoolean()) return;
            if (primed.isEmpty()) {
                events.onState(request,"error",SystemClock.elapsedRealtime()-began,"La voce naturale non ha prodotto audio.");
                return;
            }
            int bytes = Math.max(rate / 2 * 4, AudioTrack.getMinBufferSize(rate,AudioFormat.CHANNEL_OUT_MONO,AudioFormat.ENCODING_PCM_FLOAT));
            track = new AudioTrack.Builder().setAudioAttributes(new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ASSISTANCE_ACCESSIBILITY).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build())
                .setAudioFormat(new AudioFormat.Builder().setSampleRate(rate).setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                .setEncoding(AudioFormat.ENCODING_PCM_FLOAT).build()).setBufferSizeInBytes(bytes).setTransferMode(AudioTrack.MODE_STREAM).build();
            player = track;
            boolean started = false;
            long maxGap = 0;
            while (active.getAsBoolean()) {
                long waiting = SystemClock.elapsedRealtime();
                float[] chunk = !primed.isEmpty() ? primed.removeFirst() : queue.take(active);
                if (chunk == null) break;
                if (started && Integer.toUnsignedLong(track.getPlaybackHeadPosition()) >= frames)
                    maxGap = Math.max(maxGap,SystemClock.elapsedRealtime()-waiting);
                int offset = 0;
                while (offset < chunk.length && active.getAsBoolean()) {
                    int length = Math.min(2048,chunk.length-offset);
                    int written = track.write(chunk,offset,length,AudioTrack.WRITE_BLOCKING);
                    if (written <= 0) throw new IllegalStateException("Audio write failed");
                    offset += written; frames += written;
                    if (!started) {
                        if (!active.getAsBoolean()) return;
                        track.play(); started = true;
                        events.onState(request,"speaking",SystemClock.elapsedRealtime()-began,"Sto parlando…");
                    }
                }
            }
            if (active.getAsBoolean()) {
                long until = SystemClock.elapsedRealtime()+2500;
                while (Integer.toUnsignedLong(track.getPlaybackHeadPosition())<frames && active.getAsBoolean() && SystemClock.elapsedRealtime()<until)
                    Thread.sleep(20);
                if (active.getAsBoolean()) {
                    int underruns = track.getUnderrunCount();
                    boolean failed = queue.failure()!=null;
                    events.onState(request,failed?"error":"idle",SystemClock.elapsedRealtime()-began,
                                   failed?"La generazione della voce è stata interrotta.":"Tocca il microfono per parlare.");
                    Log.i("ALLMA-Kokoro","completed speaker="+speaker+" elapsed_ms="+(SystemClock.elapsedRealtime()-began)
                          +" frames="+frames+" underruns="+underruns+" max_gap_ms="+maxGap);
                }
            }
        } catch (Exception error) {
            if (active.getAsBoolean()) {
                // Unblock a generator waiting on a full queue after playback failure.
                queue.finish(error);
                events.onState(request,"error",SystemClock.elapsedRealtime()-began,"Riproduzione interrotta. Tocca per riprovare.");
                Log.e("ALLMA-Kokoro","audio_playback_failure",error);
            }
        } finally {
            if (player == track) player = null;
            if (track != null) { try { track.pause();track.flush();track.release(); } catch (Exception ignored) {} }
            if (!closed) handler.postDelayed(idleRelease,45000);
        }
    }
    public void stop() {
        epoch.incrementAndGet();
        AudioTrack owned = player;
        if (owned != null) { try { owned.pause();owned.flush(); } catch (Exception ignored) {} }
    }
    public synchronized void close() {
        if (closed) return;
        closed = true;stop();handler.removeCallbacks(idleRelease);
        worker.execute(this::releaseEngine);worker.shutdown();audioWorker.shutdown();
    }
}
