package org.allma.voice;

import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.function.BooleanSupplier;

/** Bounded producer/consumer bridge; no Android dependency or personal data. */
public final class VoiceAudioBuffer {
    private final ArrayBlockingQueue<float[]> chunks = new ArrayBlockingQueue<>(4);
    private volatile boolean finished;
    private volatile Throwable failure;
    public boolean put(float[] samples, BooleanSupplier active) throws InterruptedException {
        if (samples.length == 0) return active.getAsBoolean();
        float[] owned = samples.clone();
        while (!finished && active.getAsBoolean()) {
            if (chunks.offer(owned, 50, TimeUnit.MILLISECONDS)) return true;
        }
        return false;
    }
    public float[] take(BooleanSupplier active) throws InterruptedException {
        while (active.getAsBoolean()) {
            float[] chunk = chunks.poll(50, TimeUnit.MILLISECONDS);
            if (chunk != null) return chunk;
            if (finished && chunks.isEmpty()) return null;
        }
        return null;
    }
    public synchronized void finish(Throwable error) { if (failure == null && error != null) failure = error; finished = true; }
    public Throwable failure() { return failure; }
}
