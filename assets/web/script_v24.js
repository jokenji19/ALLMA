// Python Bridge Interface v24
// Architecture: Flexbox Layout + Safe Timer

// --- BRIDGE POLYFILL (v0.80) ---
// Guarantee queueing even if Python evaluateJavascript is late
if (!window.msgQueue) window.msgQueue = [];
if (!window.pyBridge) {
    window.pyBridge = {
        postMessage: function (msg) {
            window.msgQueue.push(msg);
        }
    };
}

const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');

// --- MESSAGING ---
function sendMessage() {
    const text = messageInput.value.trim();
    if (text) {
        addMessage(text, 'user', null);
        messageInput.value = '';
        messageInput.blur();

        if (window.pyBridge) {
            // Mostra la bolla con i pallini animati prima del primo token
            window.startStream();
            window.pyBridge.postMessage(text);
        } else {
            console.warn("No PyBridge");
            setTimeout(() => addMessage("Test response", 'bot', "Thinking..."), 1000);
        }
    }
}

function addMessage(text, sender, thoughtText) {
    const template = document.getElementById(sender === 'user' ? 'tmpl-user' : 'tmpl-bot');
    const clone = template.content.cloneNode(true);

    const contentSpan = clone.querySelector('.content');
    contentSpan.textContent = text;

    if (sender === 'bot' && thoughtText) {
        const reasoningContainer = clone.querySelector('.reasoning-container');
        const reasoningContent = clone.querySelector('.reasoning-content');
        if (reasoningContainer && reasoningContent) {
            reasoningContainer.classList.remove('hidden');
            reasoningContent.textContent = thoughtText;
        }
    }

    const wrapper = clone.querySelector('.message-wrapper');
    chatContainer.appendChild(wrapper);
    scrollToBottom();
}

function toggleReasoning(header) {
    header.parentElement.classList.toggle('open');
}

function scrollToBottom(force = false) {
    const distanceFromBottom = chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight;
    if (!force && distanceFromBottom > 120) return;
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

messageInput.addEventListener('focus', () => {
    setTimeout(() => scrollToBottom(true), 100);
    setTimeout(() => scrollToBottom(true), 300);
});

// Explicit Key Handler (better for mobile)
window.handleInputKey = function (e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        sendMessage();
    }
};

// ROBUST VISUAL VIEWPORT HANDLING (v0.39) - THE "BLIND FALLBACK"
// If NO_LIMITS prevents the viewport from resizing, we manually add 
// massive padding to the bottom to simulate the keyboard.

function handleViewportResizing() {
    // Normal resize handling
    document.body.style.height = window.visualViewport.height + 'px';
    scrollToBottom(true);
    if (document.activeElement === messageInput) {
        messageInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// ROBUST VISUAL VIEWPORT HANDLING (v0.40) - CLEAN & NATIVE
// "Pan" mode will handle the heavy lifting. We just keep the body size synced.

if (window.visualViewport) {
    function handleViewportResizing() {
        // Just sync height. proper PAN mode will slide us up.
        // We use 100% logic to avoid layout breaking.
        // If PAN is active, viewport height might NOT change, which is fine.
        // We do minimal JS interference here.
    }
    // We actually DON'T want to aggressively resize body if we are Panning,
    // as it might cause double-jumps.
    // Let's rely purely on CSS 100% and Android's Pan.
}

// Focus handling - reduced to just scroll checks
messageInput.addEventListener('focus', () => {
    setTimeout(() => scrollToBottom(true), 300);
});

// Expose action for Python to set input text
window.setInputText = function (text) {
    const input = document.getElementById('message-input');
    if (input) {
        input.value = text;
        input.focus();
    }
};

window.toggleMic = function () {
    console.log("Mic Toggled");
    const btn = document.getElementById('mic-btn');
    btn.classList.toggle('listening'); // We can style this later (make it red)

    // Send to Python
    if (window.pyBridge) {
        // Send JSON action
        window.pyBridge.postMessage(JSON.stringify({
            type: 'action',
            action: 'toggle_mic'
        }));
    } else {
        console.warn("No PyBridge for Mic");
        // Mock
        setTimeout(() => window.setInputText("Ciao ALLMA (Mock)"), 1000);
    }
};

// Expose
window.addMessage = addMessage;


// --- STREAMING & TIMER v24 (Text Based & Sinuous Buffer V6.5) ---
let currentStreamBubble = null;
let streamStartTime = 0;
let timerInterval = null;

// Buffer variables for decoupled rendering
let responseBuffer = "";
let isDraining = false;
let isBackendFinished = true;

function drainBuffer() {
    if (!currentStreamBubble || !currentStreamBubble.content) {
        isDraining = false;
        return;
    }

    if (responseBuffer.length > 0) {
        // Dynamic chunk size: if buffer gets too large (backend is VERY fast), take more chars to catch up smoothly
        let charsToTake = 1;
        if (responseBuffer.length > 500) charsToTake = 6;
        else if (responseBuffer.length > 200) charsToTake = 3;
        else if (responseBuffer.length > 50) charsToTake = 2;

            const chunk = responseBuffer.substring(0, charsToTake);
            responseBuffer = responseBuffer.substring(charsToTake);
            currentStreamBubble.content.textContent += chunk;
            scrollToBottom();
    }

    if (responseBuffer.length === 0 && isBackendFinished) {
        finishStreamUI();
    } else {
        // Sinuous delay: ~15ms base + slight human randomizer
        let delay = Math.random() * 10 + 15;
        setTimeout(drainBuffer, delay);
    }
}

function finishStreamUI() {
    isDraining = false;
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = null;

    if (currentStreamBubble && streamStartTime > 0 && !currentStreamBubble.timerFrozen) {
        const duration = (Date.now() - streamStartTime) / 1000;
        const textSpan = currentStreamBubble.timer.querySelector('.timer-text');
        if (textSpan) textSpan.textContent = duration.toFixed(2) + "s (UI Finish)";
    }
    currentStreamBubble = null;
    streamStartTime = 0;
}

// --- SIDEBAR LOGIC (v0.47) ---
function toggleSidebar() {
    console.log("Toggle Sidebar Executed");
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');

    sidebar.classList.toggle('active');
    backdrop.classList.toggle('active');
}

function startNewChat() {
    console.log("New Chat Started");
    toggleSidebar();
    const chatContainer = document.getElementById('chat-container');
    chatContainer.innerHTML = '<div class="spacer-top"></div>';
}

// --- VOICE MODE (v0.55) ---
const VoiceFX = (() => {
    let overlay = null;
    let bgCanvas = null;
    let orbCanvas = null;
    let bgCtx = null;
    let orbCtx = null;
    let active = false;
    let state = 'idle';
    let micRequested = false;
    let raf = 0;
    let t = 0;
    let dt = 1;
    let lastTs = 0;
    let quality = 1;
    let qualityTarget = 1;
    let audio = 0;
    let smoothAudio = 0;
    let dpr = 1;
    const particles = [];
    const neurons = [];
    const internal = {
        emotion: 'neutral',
        intensity: 0.4,
        valence: 0.5,
        arousal: 0.5,
        dominance: 0.5,
        topic: null,
        memory_gate_status: null,
        memory_score: 0.0,
        intent: null,
        confidence: null
    };

    function statusLabel(s) {
        if (s === 'listening') return 'In ascolto...';
        if (s === 'thinking') return 'Sto pensando...';
        if (s === 'speaking') return 'Sto parlando...';
        return 'Tocca per parlare';
    }

    function clamp01(x) {
        const n = Number(x);
        if (!Number.isFinite(n)) return 0;
        return Math.max(0, Math.min(1, n));
    }

    function normalizeEmotion(e) {
        if (!e) return 'neutral';
        const s = String(e).toLowerCase().trim();
        if (s.includes('joy') || s.includes('happy') || s.includes('felic') || s.includes('gioia')) return 'joy';
        if (s.includes('sad') || s.includes('trist')) return 'sadness';
        if (s.includes('anger') || s.includes('rabb') || s.includes('frustr')) return 'anger';
        if (s.includes('fear') || s.includes('paur') || s.includes('anxi')) return 'fear';
        if (s.includes('curios')) return 'curiosity';
        if (s.includes('trust') || s.includes('fid')) return 'trust';
        if (s.includes('surpris') || s.includes('sorp')) return 'surprise';
        if (s.includes('disgust') || s.includes('disgus')) return 'disgust';
        if (s.includes('confus')) return 'confusion';
        if (s.includes('hope') || s.includes('sper')) return 'hope';
        return 'neutral';
    }

    function mix(a, b, t) {
        return Math.round(a + (b - a) * t);
    }

    function mixPalette(p1, p2, t) {
        return {
            primary: [mix(p1.primary[0], p2.primary[0], t), mix(p1.primary[1], p2.primary[1], t), mix(p1.primary[2], p2.primary[2], t)],
            secondary: [mix(p1.secondary[0], p2.secondary[0], t), mix(p1.secondary[1], p2.secondary[1], t), mix(p1.secondary[2], p2.secondary[2], t)],
            tertiary: [mix(p1.tertiary[0], p2.tertiary[0], t), mix(p1.tertiary[1], p2.tertiary[1], t), mix(p1.tertiary[2], p2.tertiary[2], t)]
        };
    }

    function emotionPalette(emotion) {
        const e = normalizeEmotion(emotion);
        if (e === 'joy') return { primary: [16, 185, 129], secondary: [52, 211, 153], tertiary: [110, 231, 183] };
        if (e === 'sadness') return { primary: [59, 130, 246], secondary: [37, 99, 235], tertiary: [147, 197, 253] };
        if (e === 'anger') return { primary: [239, 68, 68], secondary: [244, 63, 94], tertiary: [253, 164, 175] };
        if (e === 'fear') return { primary: [245, 158, 11], secondary: [251, 191, 36], tertiary: [252, 211, 77] };
        if (e === 'curiosity') return { primary: [99, 102, 241], secondary: [139, 92, 246], tertiary: [192, 132, 252] };
        if (e === 'trust') return { primary: [34, 211, 238], secondary: [56, 189, 248], tertiary: [125, 211, 252] };
        if (e === 'surprise') return { primary: [236, 72, 153], secondary: [217, 70, 239], tertiary: [244, 114, 182] };
        if (e === 'disgust') return { primary: [34, 197, 94], secondary: [16, 185, 129], tertiary: [134, 239, 172] };
        if (e === 'confusion') return { primary: [167, 139, 250], secondary: [139, 92, 246], tertiary: [216, 180, 254] };
        if (e === 'hope') return { primary: [125, 211, 252], secondary: [56, 189, 248], tertiary: [186, 230, 253] };
        return { primary: [148, 163, 184], secondary: [100, 116, 139], tertiary: [203, 213, 225] };
    }

    function stateColors(s) {
        const base = emotionPalette(internal.emotion);
        const thinking = { primary: [245, 158, 11], secondary: [251, 191, 36], tertiary: [252, 211, 77] };
        const speaking = { primary: [16, 185, 129], secondary: [52, 211, 153], tertiary: [110, 231, 183] };
        if (s === 'thinking') return mixPalette(base, thinking, 0.65);
        if (s === 'speaking') return mixPalette(base, speaking, 0.55);
        if (s === 'listening') return base;
        return mixPalette(base, { primary: [148, 163, 184], secondary: [100, 116, 139], tertiary: [203, 213, 225] }, 0.35);
    }

    function ensureInit() {
        if (overlay) return;
        overlay = document.getElementById('voice-overlay');
        bgCanvas = document.getElementById('voice-bg-canvas');
        orbCanvas = document.getElementById('neural-canvas');
        if (bgCanvas) bgCtx = bgCanvas.getContext('2d');
        if (orbCanvas) orbCtx = orbCanvas.getContext('2d');

        if (particles.length === 0) {
            for (let i = 0; i < 50; i++) {
                particles.push({
                    x: Math.random(),
                    y: Math.random(),
                    vx: (Math.random() - 0.5) * 0.00018,
                    vy: (Math.random() - 0.5) * 0.00018,
                    size: Math.random() * 1.5 + 0.5,
                    alpha: Math.random() * 0.12 + 0.04,
                    phase: Math.random() * Math.PI * 2
                });
            }
        }

        if (neurons.length === 0) {
            const count = 170;
            for (let i = 0; i < count; i++) {
                const angle = Math.random() * Math.PI * 2;
                const rFactor = Math.sqrt(Math.random());
                const baseRadius = rFactor;
                const layer = rFactor < 0.35 ? 0 : rFactor < 0.7 ? 1 : 2;
                neurons.push({
                    x: 0,
                    y: 0,
                    baseAngle: angle,
                    baseRadius,
                    vx: (Math.random() - 0.5) * 0.3,
                    vy: (Math.random() - 0.5) * 0.3,
                    radius: layer === 0 ? 1.7 + Math.random() * 2 : layer === 1 ? 1.2 + Math.random() * 1.6 : 0.9 + Math.random() * 1.1,
                    baseAlpha: layer === 0 ? 0.7 + Math.random() * 0.25 : layer === 1 ? 0.45 + Math.random() * 0.25 : 0.25 + Math.random() * 0.2,
                    orbitSpeed: (0.002 + Math.random() * 0.006) * (Math.random() > 0.5 ? 1 : -1),
                    orbitAmplitude: 2 + Math.random() * 8,
                    phase: Math.random() * Math.PI * 2,
                    layer,
                    pulseSpeed: 0.02 + Math.random() * 0.04
                });
            }
        }

        function onResize() {
            dpr = Math.max(1, window.devicePixelRatio || 1);
            if (bgCanvas) {
                const w = window.innerWidth;
                const h = window.innerHeight;
                bgCanvas.width = Math.floor(w * dpr);
                bgCanvas.height = Math.floor(h * dpr);
                bgCanvas.style.width = w + "px";
                bgCanvas.style.height = h + "px";
                if (bgCtx) bgCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
            }
            if (orbCanvas) {
                const rect = orbCanvas.getBoundingClientRect();
                const w = Math.max(260, Math.floor(rect.width));
                const h = Math.max(260, Math.floor(rect.height));
                orbCanvas.width = Math.floor(w * dpr);
                orbCanvas.height = Math.floor(h * dpr);
                if (orbCtx) orbCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
            }
        }

        window.addEventListener('resize', onResize);
        setTimeout(onResize, 0);
    }

    function setState(next) {
        state = next || 'idle';
        if (overlay) overlay.setAttribute('data-voice-state', state);
        const label = document.getElementById('voice-status');
        if (label) {
            const e = normalizeEmotion(internal.emotion);
            const tpc = internal.topic ? String(internal.topic) : '';
            const suffix = tpc ? `${e} • ${tpc}` : e;
            label.textContent = state === 'idle' ? statusLabel(state) : `${statusLabel(state)} • ${suffix}`;
        }
    }

    function setInternalState(payload) {
        if (!payload || typeof payload !== 'object') return;
        if (payload.emotion !== undefined) internal.emotion = payload.emotion;
        if (payload.intensity !== undefined) internal.intensity = clamp01(payload.intensity);
        if (payload.valence !== undefined) internal.valence = clamp01(payload.valence);
        if (payload.arousal !== undefined) internal.arousal = clamp01(payload.arousal);
        if (payload.dominance !== undefined) internal.dominance = clamp01(payload.dominance);
        if (payload.topic !== undefined) internal.topic = payload.topic;
        if (payload.memory_gate_status !== undefined) internal.memory_gate_status = payload.memory_gate_status;
        if (payload.memory_score !== undefined) internal.memory_score = Number(payload.memory_score) || 0.0;
        if (payload.intent !== undefined) internal.intent = payload.intent;
        if (payload.confidence !== undefined) internal.confidence = payload.confidence;
        setState(state);
        bump(0.15 + internal.intensity * 0.2);
    }

    function bump(level) {
        const v = typeof level === 'number' ? level : 0.25;
        audio = Math.min(1, audio + v);
    }

    function drawBackground() {
        if (!bgCanvas || !bgCtx) return;
        const w = window.innerWidth;
        const h = window.innerHeight;
        bgCtx.clearRect(0, 0, w, h);

        const colors = stateColors(state).primary;
        const intensityBoost = 0.75 + clamp01(internal.intensity) * 0.85;
        const gateBoost = internal.memory_gate_status === 'LEVEL_3' ? 1.15 : internal.memory_gate_status === 'LEVEL_2' ? 1.0 : 0.85;
        const speedMultiplier = (state === 'listening' ? 1 + smoothAudio * 2 : state === 'speaking' ? 1.2 : state === 'thinking' ? 0.8 : 0.45) * intensityBoost * gateBoost;

        const q = Math.max(0.35, Math.min(1, quality));
        const pCount = Math.max(18, Math.floor(particles.length * q));
        for (let i = 0; i < pCount; i++) {
            const p = particles[i];
            p.phase += 0.01 * dt;
            p.x += p.vx * speedMultiplier * dt + Math.sin(t * 0.003 + p.phase) * 0.00025 * dt;
            p.y += p.vy * speedMultiplier * dt + Math.cos(t * 0.004 + p.phase) * 0.00025 * dt;
            if (p.x < 0) p.x = 1;
            if (p.x > 1) p.x = 0;
            if (p.y < 0) p.y = 1;
            if (p.y > 1) p.y = 0;

            const px = p.x * w;
            const py = p.y * h;
            const a = p.alpha + (state === 'listening' ? smoothAudio * 0.15 : 0);
            bgCtx.beginPath();
            bgCtx.arc(px, py, p.size, 0, Math.PI * 2);
            bgCtx.fillStyle = `rgba(${colors[0]}, ${colors[1]}, ${colors[2]}, ${a})`;
            bgCtx.fill();
        }

        const maxDist = 130 * (0.75 + q * 0.25);
        const stride = q < 0.7 ? 2 : 1;
        for (let i = 0; i < pCount; i += stride) {
            for (let j = i + 1; j < pCount; j += stride) {
                const dx = (particles[i].x - particles[j].x) * w;
                const dy = (particles[i].y - particles[j].y) * h;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < maxDist) {
                    const a = 0.03 * (1 - dist / maxDist);
                    bgCtx.beginPath();
                    bgCtx.moveTo(particles[i].x * w, particles[i].y * h);
                    bgCtx.lineTo(particles[j].x * w, particles[j].y * h);
                    bgCtx.strokeStyle = `rgba(${colors[0]}, ${colors[1]}, ${colors[2]}, ${a})`;
                    bgCtx.lineWidth = 0.4;
                    bgCtx.stroke();
                }
            }
        }
    }

    function drawOrb() {
        if (!orbCanvas || !orbCtx) return;
        const rect = orbCanvas.getBoundingClientRect();
        const w = Math.max(260, rect.width);
        const h = Math.max(260, rect.height);
        const cx = w / 2;
        const cy = h / 2;
        const radius = Math.min(w, h) * 0.36;

        orbCtx.clearRect(0, 0, w, h);

        const colors = stateColors(state);
        const smoothK = 1 - Math.pow(1 - 0.12, dt);
        smoothAudio += (audio - smoothAudio) * smoothK;
        audio *= Math.pow(0.92, dt);

        const breathScale =
            state === 'idle' ? 1 + Math.sin(t * 0.015) * 0.04 :
            state === 'thinking' ? 1 + Math.sin(t * 0.04) * 0.08 :
            state === 'listening' ? 1 + smoothAudio * 0.3 + Math.sin(t * 0.02) * 0.05 :
            1 + smoothAudio * 0.2 + Math.sin(t * 0.025) * 0.04;

        const glowRadius = radius * (1 + smoothAudio * 0.5) * breathScale;
        const bgGlow = orbCtx.createRadialGradient(cx, cy, 0, cx, cy, glowRadius * 1.6);
        const glowAlpha = state === 'idle' ? 0.03 : 0.06 + smoothAudio * 0.08;
        bgGlow.addColorStop(0, `rgba(${colors.primary[0]}, ${colors.primary[1]}, ${colors.primary[2]}, ${glowAlpha})`);
        bgGlow.addColorStop(0.5, `rgba(${colors.primary[0]}, ${colors.primary[1]}, ${colors.primary[2]}, ${glowAlpha * 0.3})`);
        bgGlow.addColorStop(1, `rgba(${colors.primary[0]}, ${colors.primary[1]}, ${colors.primary[2]}, 0)`);
        orbCtx.beginPath();
        orbCtx.arc(cx, cy, glowRadius * 1.6, 0, Math.PI * 2);
        orbCtx.fillStyle = bgGlow;
        orbCtx.fill();

        const baseSpeed =
            state === 'listening' ? 1.5 + smoothAudio * 3 :
            state === 'speaking' ? 1.2 + smoothAudio * 2 :
            state === 'thinking' ? 2.5 :
            0.5;
        const speedMultiplier = baseSpeed * (0.85 + clamp01(internal.intensity) * 0.9) * (internal.memory_gate_status === 'LEVEL_3' ? 1.2 : internal.memory_gate_status === 'LEVEL_2' ? 1.05 : 0.9);

        const q = Math.max(0.35, Math.min(1, quality));
        const nCount = Math.max(90, Math.floor(neurons.length * q));

        for (let idx = 0; idx < nCount; idx++) {
            const n = neurons[idx];
            if (!n.__init) {
                n.x = cx + Math.cos(n.baseAngle) * (n.baseRadius * radius);
                n.y = cy + Math.sin(n.baseAngle) * (n.baseRadius * radius);
                n.__init = 1;
            }
            n.baseAngle += n.orbitSpeed * speedMultiplier * dt;
            n.phase += n.pulseSpeed * dt;

            let extraRadius = 0;
            if (state === 'thinking') extraRadius = Math.sin(t * 0.03 + n.phase) * 0.15;

            const currentR = (n.baseRadius + extraRadius) * radius * breathScale;
            const wobbleX = Math.sin(t * 0.01 + n.phase) * n.orbitAmplitude * speedMultiplier;
            const wobbleY = Math.cos(t * 0.013 + n.phase * 1.3) * n.orbitAmplitude * speedMultiplier;
            const targetX = cx + Math.cos(n.baseAngle) * currentR + wobbleX;
            const targetY = cy + Math.sin(n.baseAngle) * currentR + wobbleY;

            const ease = 0.03 + smoothAudio * 0.03;
            n.vx += (targetX - n.x) * ease * dt;
            n.vy += (targetY - n.y) * ease * dt;

            if (state === 'listening' && smoothAudio > 0.08) {
                const dx = n.x - cx;
                const dy = n.y - cy;
                const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                const impulse = smoothAudio * 0.8;
                n.vx += (dx / dist) * impulse * Math.sin(t * 0.1 + n.phase);
                n.vy += (dy / dist) * impulse * Math.cos(t * 0.1 + n.phase);
            }

            const damp = Math.pow(0.88, dt);
            n.vx *= damp;
            n.vy *= damp;
            n.x += n.vx * dt;
            n.y += n.vy * dt;

            const dx2 = n.x - cx;
            const dy2 = n.y - cy;
            const dist2 = Math.sqrt(dx2 * dx2 + dy2 * dy2);
            const maxR = radius * breathScale * 1.2;
            if (dist2 > maxR) {
                const f = maxR / dist2;
                n.x = cx + dx2 * f;
                n.y = cy + dy2 * f;
                n.vx *= 0.5;
                n.vy *= 0.5;
            }
        }

        const doConnections = !((q < 0.78) && (state === 'thinking' || dt > 1.2) && (Math.floor(t) % 2 === 1));
        if (doConnections) {
            const connDist = (44 + smoothAudio * 20 + clamp01(internal.memory_score) * 18) * (0.75 + q * 0.25);
            const gridSize = connDist;
            const grid = new Map();
            for (let i = 0; i < nCount; i++) {
                const gx = Math.floor(neurons[i].x / gridSize);
                const gy = Math.floor(neurons[i].y / gridSize);
                const key = `${gx},${gy}`;
                if (!grid.has(key)) grid.set(key, []);
                grid.get(key).push(i);
            }

            const maxConnections = q < 0.7 ? 3 : 5;
            const connectionCounts = new Uint8Array(nCount);

            for (let i = 0; i < nCount; i++) {
                if (connectionCounts[i] >= maxConnections) continue;
                const ni = neurons[i];
                const gx = Math.floor(ni.x / gridSize);
                const gy = Math.floor(ni.y / gridSize);

                for (let ox = -1; ox <= 1; ox++) {
                    for (let oy = -1; oy <= 1; oy++) {
                        const key = `${gx + ox},${gy + oy}`;
                        const cell = grid.get(key);
                        if (!cell) continue;
                        for (const j of cell) {
                            if (j <= i) continue;
                            if (connectionCounts[i] >= maxConnections || connectionCounts[j] >= maxConnections) continue;
                            const nj = neurons[j];
                            const ddx = ni.x - nj.x;
                            const ddy = ni.y - nj.y;
                            const d = Math.sqrt(ddx * ddx + ddy * ddy);
                            if (d < connDist) {
                                connectionCounts[i]++;
                                connectionCounts[j]++;
                                const alpha = (1 - d / connDist) * 0.32;
                                const pulse = Math.sin(t * 0.03 + (ni.phase + nj.phase) * 0.5) * 0.5 + 0.5;
                                const finalAlpha = alpha * (0.5 + pulse * 0.5) * (state === 'idle' ? 0.5 : 1);

                                const grad = orbCtx.createLinearGradient(ni.x, ni.y, nj.x, nj.y);
                                const c1 = ni.layer === 0 ? colors.tertiary : ni.layer === 1 ? colors.secondary : colors.primary;
                                const c2 = nj.layer === 0 ? colors.tertiary : nj.layer === 1 ? colors.secondary : colors.primary;
                                grad.addColorStop(0, `rgba(${c1[0]}, ${c1[1]}, ${c1[2]}, ${finalAlpha})`);
                                grad.addColorStop(1, `rgba(${c2[0]}, ${c2[1]}, ${c2[2]}, ${finalAlpha})`);
                                orbCtx.beginPath();
                                orbCtx.moveTo(ni.x, ni.y);
                                orbCtx.lineTo(nj.x, nj.y);
                                orbCtx.strokeStyle = grad;
                                orbCtx.lineWidth = 0.5 + alpha * 1.4;
                                orbCtx.stroke();
                            }
                        }
                    }
                }
            }
        }

        for (let idx = 0; idx < nCount; idx++) {
            const n = neurons[idx];
            const pulse = Math.sin(n.phase) * 0.3 + 0.7;
            const c = n.layer === 0 ? colors.tertiary : n.layer === 1 ? colors.secondary : colors.primary;

            const glowR = n.radius * (2 + smoothAudio * 2);
            const neuronGlow = orbCtx.createRadialGradient(n.x, n.y, 0, n.x, n.y, glowR);
            const glowA = n.baseAlpha * pulse * (state === 'idle' ? 0.18 : 0.42 + smoothAudio * 0.28);
            neuronGlow.addColorStop(0, `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${glowA})`);
            neuronGlow.addColorStop(1, `rgba(${c[0]}, ${c[1]}, ${c[2]}, 0)`);
            orbCtx.beginPath();
            orbCtx.arc(n.x, n.y, glowR, 0, Math.PI * 2);
            orbCtx.fillStyle = neuronGlow;
            orbCtx.fill();

            const coreAlpha = n.baseAlpha * pulse * (state === 'idle' ? 0.6 : 0.8 + smoothAudio * 0.2);
            const coreRadius = n.radius * (0.85 + pulse * 0.25 + smoothAudio * 0.35);
            orbCtx.beginPath();
            orbCtx.arc(n.x, n.y, coreRadius, 0, Math.PI * 2);
            orbCtx.fillStyle = `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${coreAlpha})`;
            orbCtx.fill();
        }

        const ringGrad = orbCtx.createRadialGradient(cx, cy, radius * breathScale * 0.9, cx, cy, radius * breathScale * 1.25);
        const ringAlpha = state === 'idle' ? 0.04 : 0.06 + smoothAudio * 0.06;
        ringGrad.addColorStop(0, `rgba(${colors.primary[0]}, ${colors.primary[1]}, ${colors.primary[2]}, 0)`);
        ringGrad.addColorStop(0.5, `rgba(${colors.primary[0]}, ${colors.primary[1]}, ${colors.primary[2]}, ${ringAlpha})`);
        ringGrad.addColorStop(1, `rgba(${colors.primary[0]}, ${colors.primary[1]}, ${colors.primary[2]}, 0)`);
        orbCtx.beginPath();
        orbCtx.arc(cx, cy, radius * breathScale * 1.25, 0, Math.PI * 2);
        orbCtx.fillStyle = ringGrad;
        orbCtx.fill();
    }

    function frame() {
        if (!active) return;
        dt = 1;
        if (typeof performance !== 'undefined' && typeof performance.now === 'function') {
            const ts = performance.now();
            if (lastTs > 0) {
                const raw = (ts - lastTs) / 16.6667;
                dt = Math.max(0.25, Math.min(2.5, raw));
            }
            lastTs = ts;
        }
        t += dt;

        qualityTarget = 1;
        if (state === 'thinking') qualityTarget *= 0.7;
        if (dt > 1.7) qualityTarget *= 0.55;
        else if (dt > 1.35) qualityTarget *= 0.7;
        else if (dt > 1.15) qualityTarget *= 0.85;
        qualityTarget = Math.max(0.35, Math.min(1, qualityTarget));
        const qk = 1 - Math.pow(1 - 0.08, dt);
        quality += (qualityTarget - quality) * qk;

        drawBackground();
        drawOrb();

        if (state === 'listening') bump((0.02 + Math.random() * 0.02) * dt);
        if (state === 'speaking') bump((0.01 + Math.random() * 0.015) * dt);
        if (state === 'thinking') bump((0.015 + Math.random() * 0.02) * dt);

        raf = requestAnimationFrame(frame);
    }

    function activate() {
        ensureInit();
        if (!overlay) return;
        active = true;
        overlay.classList.add('active');
        overlay.setAttribute('data-voice-state', state);
        lastTs = 0;
        quality = 1;
        qualityTarget = 1;
        if (!raf) raf = requestAnimationFrame(frame);
    }

    function deactivate() {
        if (!overlay) ensureInit();
        active = false;
        if (raf) cancelAnimationFrame(raf);
        raf = 0;
        lastTs = 0;
        quality = 1;
        qualityTarget = 1;
        micRequested = false;
        setState('idle');
    }

    function setMicRequested(v) {
        micRequested = !!v;
    }

    function getMicRequested() {
        return micRequested;
    }

    function isActive() {
        return !!(overlay && overlay.classList.contains('active'));
    }

    function getState() {
        return state;
    }

    return { activate, deactivate, setState, bump, isActive, getState, setMicRequested, getMicRequested, setInternalState };
})();

window.openVoiceMode = function () {
    console.log("Opening Voice Mode");
    const overlay = document.getElementById('voice-overlay');
    if (overlay) {
        overlay.classList.add('active');
        VoiceFX.activate();
        VoiceFX.setState('listening');
        VoiceFX.setMicRequested(true);
        const transcript = document.getElementById('voice-text');
        if (transcript) transcript.textContent = "";

        // Also ensure Mic is active on Python side if not already
        if (window.pyBridge) {
            window.pyBridge.postMessage(JSON.stringify({
                type: 'action',
                action: 'set_voice_mode',
                enabled: true
            }));
        }
    }
};

window.closeVoiceMode = function () {
    console.log("Closing Voice Mode");
    const overlay = document.getElementById('voice-overlay');
    if (overlay) {
        overlay.classList.remove('active');
        VoiceFX.deactivate();
        const transcript = document.getElementById('voice-text');
        if (transcript) transcript.textContent = "";

        if (window.pyBridge) {
            window.pyBridge.postMessage(JSON.stringify({
                type: 'action',
                action: 'set_voice_mode',
                enabled: false
            }));
        }
    }
};

window.updateVoiceText = function (text) {
    const el = document.getElementById('voice-text');
    if (el) el.textContent = text;
    if (VoiceFX.isActive()) {
        VoiceFX.setState('listening');
        VoiceFX.bump(0.35);
    }
};

window.updateVoiceInternalState = function (payload) {
    if (typeof VoiceFX !== 'undefined' && VoiceFX.setInternalState) {
        VoiceFX.setInternalState(payload);
    }
};

window.voiceToggleListening = function () {
    if (!VoiceFX.isActive()) {
        openVoiceMode();
        return;
    }
    if (window.pyBridge) {
        window.pyBridge.postMessage(JSON.stringify({
            type: 'action',
            action: 'toggle_mic'
        }));
    }
    const next = VoiceFX.getMicRequested() ? 'idle' : 'listening';
    VoiceFX.setMicRequested(!VoiceFX.getMicRequested());
    VoiceFX.setState(next);
    VoiceFX.bump(0.45);
};

// Override toggleMic to open this mode
window.toggleMic = function () {
    openVoiceMode();
};

// --- PANEL MANAGEMENT ---

// Close any open panel
window.closePanel = function (panelName) {
    const panel = document.getElementById(`panel-${panelName}`);
    if (panel) {
        panel.classList.add('hidden');
    }

    // Stop temperature monitoring when closing settings
    if (panelName === 'settings') {
        stopTemperatureMonitoring();
    }
};

// Open panel (enhanced version)
window.openPanel = function (panelName) {
    console.log("Opening panel: " + panelName);
    toggleSidebar();

    if (panelName === 'voice') {
        openVoiceMode();
    } else if (panelName === 'settings') {
        const panel = document.getElementById('panel-settings');
        if (panel) {
            panel.classList.remove('hidden');
            startTemperatureMonitoring();
        }
    } else if (panelName === 'memory') {
        const panel = document.getElementById('panel-memory');
        if (panel) {
            panel.classList.remove('hidden');
            if (window.pyBridge) {
                window.pyBridge.postMessage("__REQUEST_MEMORY_UPDATE__");
            } else if (window.msgQueue) {
                window.msgQueue.push("__REQUEST_MEMORY_UPDATE__");
            }
        }
    } else if (panelName === 'dream') {
        const panel = document.getElementById('panel-dream');
        if (panel) {
            panel.classList.remove('hidden');
            if (window.pyBridge) {
                window.pyBridge.postMessage("__REQUEST_DREAM_HISTORY__");
            } else if (window.msgQueue) {
                window.msgQueue.push("__REQUEST_DREAM_HISTORY__");
            }
        }

    } else {
        // Fallback generico per pannelli futuri
        const panel = document.getElementById(`panel-${panelName}`);
        if (panel) panel.classList.remove('hidden');
    }
};

// --- TEMPERATURE MONITORING SYSTEM ---

let temperatureUpdateInterval = null;

function startTemperatureMonitoring() {
    console.log("Starting temperature monitoring...");

    // Request temperature update from Python
    if (window.msgQueue) {
        window.msgQueue.push("__REQUEST_TEMPERATURE_UPDATE__");
    }

    // Immediate first update
    updateTemperature();

    // Update every 2 seconds
    if (!temperatureUpdateInterval) {
        temperatureUpdateInterval = setInterval(() => {
            // Request fresh data from Python
            if (window.msgQueue) {
                window.msgQueue.push("__REQUEST_TEMPERATURE_UPDATE__");
            }
            updateTemperature();
        }, 2000);
    }
}

window.updateMemory = function (dataStr) {
    try {
        console.log("updateMemory called with data:", dataStr);
        let data = dataStr;
        if (typeof data === 'string') {
            data = JSON.parse(data);
        }

        const factsContainer = document.getElementById('memory-user-facts');
        const logsContainer = document.getElementById('memory-logs');

        if (!factsContainer || !logsContainer) return;

        // 1. Render User Facts
        factsContainer.innerHTML = '';
        if (data.facts && Object.keys(data.facts).length > 0) {
            for (const [key, val] of Object.entries(data.facts)) {
                // Ignore internal metadata keys if any
                if (key.startsWith('_')) continue;

                const card = document.createElement('div');
                card.className = 'memory-fact-card';
                card.innerHTML = `
                    <div class="mem-key">${escapeHtml(key)}</div>
                    <div class="mem-val">${escapeHtml(String(val))}</div>
                `;
                factsContainer.appendChild(card);
            }
        } else {
            factsContainer.innerHTML = '<div class="memory-empty-state">Nessun dato permanente appreso.</div>';
        }

        // 2. Render Logs (Timeline)
        logsContainer.innerHTML = '';
        if (data.logs && data.logs.length > 0) {
            // Logs are usually oldest first from backend, we might want to reverse them here if preferred,
            // but let's assume they are chronologically ordered.
            data.logs.forEach(msg => {
                const item = document.createElement('div');
                item.className = 'memory-log-item';

                const roleClass = msg.role === 'user' ? 'user' : 'bot';
                const roleName = msg.role === 'user' ? 'Tu' : 'ALLMA';

                // Format Timestamp (approximate if full ISO)
                let timeStr = "";
                if (msg.timestamp) {
                    try {
                        const d = new Date(msg.timestamp);
                        timeStr = d.getHours().toString().padStart(2, '0') + ":" +
                            d.getMinutes().toString().padStart(2, '0');
                    } catch (e) { timeStr = msg.timestamp; }
                }

                let contentClass = 'mem-content';
                let displayedContent = msg.content;

                // Highlight thought blocks
                if (msg.is_thought || (msg.content && msg.content.includes('[[TH:'))) {
                    contentClass += ' is-thought';
                }

                item.innerHTML = `
                    <div class="memory-log-header">
                        <span class="mem-role ${roleClass}">${roleName}</span>
                        <span class="mem-timestamp">${timeStr}</span>
                    </div>
                    <div class="${contentClass}">${escapeHtml(displayedContent)}</div>
                `;
                logsContainer.appendChild(item);
            });

            // Auto scroll to bottom of logs
            setTimeout(() => {
                logsContainer.scrollTop = logsContainer.scrollHeight;
            }, 100);
        } else {
            logsContainer.innerHTML = '<div class="memory-empty-state">Nessuna conversazione registrata.</div>';
        }

    } catch (e) {
        console.error("Error updating memory UI:", e);
    }
};

// Ensure escapeHtml exists
function escapeHtml(unsafe) {
    if (!unsafe) return "";
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function stopTemperatureMonitoring() {
    console.log("Stopping temperature monitoring...");
    if (temperatureUpdateInterval) {
        clearInterval(temperatureUpdateInterval);
        temperatureUpdateInterval = null;
    }
}

function updateTemperature() {
    // The temperature data is injected by Python via inject_temperature_to_js()
    // which updates window.pyBridge.getTemperature() to return fresh data

    if (window.pyBridge && typeof window.pyBridge.getTemperature === 'function') {
        try {
            const tempData = window.pyBridge.getTemperature();
            if (tempData && (tempData.cpu || tempData.battery)) {
                displayTemperature(tempData);
                return;
            }
        } catch (e) {
            console.error("Error getting temperature:", e);
        }
    }

    // Fallback: simulate temperature for testing
    const mockData = {
        cpu: Math.random() * 30 + 35,  // 35-65°C
        battery: Math.random() * 20 + 30  // 30-50°C
    };
    displayTemperature(mockData);
}

function displayTemperature(tempData) {
    // Update CPU temperature
    if (tempData.cpu !== undefined) {
        const cpuTemp = Math.round(tempData.cpu);
        document.getElementById('temp-cpu').textContent = `${cpuTemp}°C`;

        // Update CPU bar (0-100°C scale)
        const cpuPercent = Math.min(100, (cpuTemp / 100) * 100);
        const cpuBar = document.getElementById('temp-cpu-bar');
        if (cpuBar) {
            cpuBar.style.width = `${cpuPercent}%`;
            // Color based on temperature
            if (cpuTemp > 70) {
                cpuBar.style.backgroundColor = '#ef4444'; // Red
            } else if (cpuTemp > 50) {
                cpuBar.style.backgroundColor = '#f59e0b'; // Orange
            } else {
                cpuBar.style.backgroundColor = '#10b981'; // Green
            }
        }
    }

    // Update Battery temperature
    if (tempData.battery !== undefined) {
        const batteryTemp = Math.round(tempData.battery);
        document.getElementById('temp-battery').textContent = `${batteryTemp}°C`;

        // Update Battery bar
        const batteryPercent = Math.min(100, (batteryTemp / 100) * 100);
        const batteryBar = document.getElementById('temp-battery-bar');
        if (batteryBar) {
            batteryBar.style.width = `${batteryPercent}%`;
            // Color based on temperature
            if (batteryTemp > 45) {
                batteryBar.style.backgroundColor = '#ef4444'; // Red
            } else if (batteryTemp > 35) {
                batteryBar.style.backgroundColor = '#f59e0b'; // Orange
            } else {
                batteryBar.style.backgroundColor = '#10b981'; // Green
            }
        }
    }

    // Update overall status
    updateTemperatureStatus(tempData);
}

function updateTemperatureStatus(tempData) {
    const statusDot = document.querySelector('#temp-status .status-dot');
    const statusText = document.getElementById('temp-status-text');

    const maxTemp = Math.max(tempData.cpu || 0, tempData.battery || 0);

    if (maxTemp > 70) {
        statusDot.style.backgroundColor = '#ef4444';
        statusText.textContent = '⚠️ Temperatura Alta';
        statusText.style.color = '#ef4444';
    } else if (maxTemp > 50) {
        statusDot.style.backgroundColor = '#f59e0b';
        statusText.textContent = '⚡ Temperatura Elevata';
        statusText.style.color = '#f59e0b';
    } else {
        statusDot.style.backgroundColor = '#10b981';
        statusText.textContent = '✅ Temperatura Normale';
        statusText.style.color = '#10b981';
    }
}


// --- USER PROFILE & CLOCK (v0.48) ---

// 1. Clock Logic
function updateTime() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const timeString = `${hours}:${minutes}`;

    const timeDisplay = document.getElementById('user-time-display');
    if (timeDisplay) {
        timeDisplay.innerText = timeString;
    }
}
// Start ticker
setInterval(updateTime, 1000); // Every second (for precision)
updateTime(); // Run immediately

// --- THEME LOGIC (Dark Mode) ---
function toggleTheme() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateThemeUI(isDark);
}

function updateThemeUI(isDark) {
    const icon = document.getElementById('theme-icon');
    const text = document.getElementById('theme-text');
    if (icon) icon.textContent = isDark ? '☀️' : '🌙';
    if (text) text.textContent = isDark ? 'Light Mode' : 'Dark Mode';
}

// Load Theme on Init
(function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        updateThemeUI(true);
    }
})();

// 2. User Profile Logic
function openUserModal() {
    // 1. CONFIRM EXECUTION
    // alert("DEBUG: Modal Clicked!"); 
    console.log("EXEC: openUserModal() called");

    let name = '';
    let age = '';

    // 2. SAFE STORAGE ACCESS
    try {
        name = localStorage.getItem('allma_username') || '';
        age = localStorage.getItem('allma_userage') || '';
    } catch (e) {
        console.error("Storage Error:", e);
        // alert("Storage Error: " + e.message);
    }

    const nameInput = document.getElementById('input-name');
    const ageInput = document.getElementById('input-age');

    if (nameInput) nameInput.value = name;
    if (ageInput) ageInput.value = age;

    const modal = document.getElementById('user-modal');
    if (modal) {
        modal.classList.add('active');
        console.log("Modal opened.");
    } else {
        alert("CRITICAL: Modal ID not found!");
    }
}

function closeUserModal() {
    const modal = document.getElementById('user-modal');
    if (modal) modal.classList.remove('active');
}

function saveUserProfile() {
    const name = document.getElementById('input-name').value.trim();
    const age = document.getElementById('input-age').value.trim();

    if (name) {
        try {
            localStorage.setItem('allma_username', name);
            localStorage.setItem('allma_userage', age);
        } catch (e) {
            console.error("Save Error:", e);
            alert("Errore salvataggio: " + e.message);
        }

        updateUserUI(name);
        closeUserModal();
        console.log(`User Profile Saved: ${name}, ${age}`);

        // Sync with Python Core
        try {
            if (window.pyBridge) {
                const payload = JSON.stringify({
                    type: 'system',
                    action: 'update_profile',
                    name: name,
                    age: age
                });
                window.pyBridge.postMessage(payload);
                console.log("Sent profile update to Core:", payload);
            } else {
                console.warn("pyBridge not found");
            }
        } catch (e) {
            console.error("Bridge Error:", e);
        }
    } else {
        alert("Inserisci almeno un nome!");
    }
}

function updateUserUI(name) {
    const display = document.getElementById('user-name-display');
    const avatar = document.getElementById('user-avatar');

    if (name) {
        if (display) display.innerText = name;
        if (avatar) avatar.innerText = name.charAt(0).toUpperCase();
    } else {
        if (display) display.innerText = "Ospite";
        if (avatar) avatar.innerText = "?";
    }
}

window.updateVoiceStackStatus = function (status) {
    const stt = document.getElementById('status-stt');
    const tts = document.getElementById('status-tts');
    const llm = document.getElementById('status-llm');
    if (!stt || !tts || !llm) return;

    const setChip = (el, label, ok) => {
        el.classList.remove('status-ok', 'status-ko', 'status-unknown');
        if (ok === true) {
            el.classList.add('status-ok');
            el.textContent = `${label} OK`;
        } else if (ok === false) {
            el.classList.add('status-ko');
            el.textContent = `${label} KO`;
        } else {
            el.classList.add('status-unknown');
            el.textContent = label;
        }
    };

    setChip(stt, 'STT', status?.stt);
    setChip(tts, 'TTS', status?.tts);
    setChip(llm, 'LLM', status?.llm);
};

function flushAllmaQueue() {
    const q = window.__allmaQueue;
    if (!Array.isArray(q) || q.length === 0) return;
    const pending = [];
    for (const item of q) {
        try {
            const fn = window[item.fn];
            if (typeof fn === 'function') {
                fn.apply(null, Array.isArray(item.args) ? item.args : []);
            } else {
                pending.push(item);
            }
        } catch (e) {
            pending.push(item);
        }
    }
    window.__allmaQueue = pending;
}

// Initialize on Load
document.addEventListener("DOMContentLoaded", () => {
    try {
        document.body.classList.add('pro-mode');
        const splash = document.getElementById('boot-splash');
        if (splash) {
            requestAnimationFrame(() => {
                setTimeout(() => {
                    document.body.classList.remove('boot-loading');
                    splash.classList.add('hidden');
                }, 300);
            });
        }
        const savedName = localStorage.getItem('allma_username');
        const savedAge = localStorage.getItem('allma_userage');
        if (savedName) {
            updateUserUI(savedName);
            // Sync on load
            if (window.pyBridge) {
                const payload = JSON.stringify({
                    type: 'system',
                    action: 'update_profile',
                    name: savedName,
                    age: savedAge
                });
                // Wait a bit for bridge using setTimeout to be safe
                setTimeout(() => window.pyBridge.postMessage(payload), 1000);
            }
        }
    } catch (e) {
        console.error("Init Storage Error:", e);
    }
    updateTime();
    flushAllmaQueue();
});

// ---------------------------
window.startStream = function () {
    if (typeof VoiceFX !== 'undefined' && VoiceFX.isActive && VoiceFX.isActive()) {
        VoiceFX.setState('thinking');
        VoiceFX.bump(0.35);
    }
    // Se c'è già una bolla attiva (creata da sendMessage), non duplicare
    if (currentStreamBubble) return;
    const template = document.getElementById('tmpl-bot');
    const clone = template.content.cloneNode(true);
    const contentSpan = clone.querySelector('.content');
    contentSpan.textContent = '';

    // Inietta i pallini animati stile ChatGPT
    const typingDots = document.createElement('span');
    typingDots.className = 'typing-dots';
    typingDots.innerHTML = '<span></span><span></span><span></span>';
    contentSpan.appendChild(typingDots);

    // Setup Thinking
    const reasoningContainer = clone.querySelector('.reasoning-container');
    const reasoningContent = clone.querySelector('.reasoning-content');
    if (reasoningContent) reasoningContent.textContent = '';

    // Create Timer
    const timerDiv = document.createElement('div');
    timerDiv.className = 'generation-timer';
    timerDiv.innerHTML = '<span>⚡</span> <span class="timer-text">0.0s</span>';

    const wrapper = clone.querySelector('.message-wrapper');
    wrapper.appendChild(timerDiv);

    chatContainer.appendChild(wrapper);
    scrollToBottom(true);

    currentStreamBubble = {
        content: contentSpan,
        reasoning: reasoningContent,
        reasoningContainer: reasoningContainer,
        timer: timerDiv,
        dotsCleared: false,
        timerFrozen: false
    };

    streamStartTime = Date.now();
    responseBuffer = "";
    isDraining = false;
    isBackendFinished = false;

    // Real-time Update
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(() => {
        if (streamStartTime > 0) {
            const duration = (Date.now() - streamStartTime) / 1000;
            const textSpan = currentStreamBubble.timer.querySelector('.timer-text');
            if (textSpan) textSpan.textContent = duration.toFixed(1) + "s";
        }
    }, 200);
};

window.streamChunk = function (text, isThought) {
    if (!currentStreamBubble) window.startStream();
    if (isThought) {
        if (currentStreamBubble.reasoningContainer.classList.contains('hidden')) {
            currentStreamBubble.reasoningContainer.classList.remove('hidden');
            // Auto-open while streaming to show progress
            currentStreamBubble.reasoningContainer.classList.add('open');
        }
        currentStreamBubble.reasoning.textContent += text;
        scrollToBottom();
    } else {
        if (typeof VoiceFX !== 'undefined' && VoiceFX.isActive && VoiceFX.isActive()) {
            if (VoiceFX.getState && VoiceFX.getState() !== 'speaking') {
                VoiceFX.setState('speaking');
            }
            VoiceFX.bump(0.08);
        }
        // Primo token reale in risposta: rimuovi i pallini animati
        if (!currentStreamBubble.dotsCleared) {
            const dots = currentStreamBubble.content.querySelector('.typing-dots');
            if (dots) dots.remove();
            currentStreamBubble.dotsCleared = true;
        }
        if (!currentStreamBubble.timerFrozen) {
            currentStreamBubble.timerFrozen = true;
            if (timerInterval) clearInterval(timerInterval);
            timerInterval = null;
            if (currentStreamBubble && streamStartTime > 0) {
                const duration = (Date.now() - streamStartTime) / 1000;
                const textSpan = currentStreamBubble.timer.querySelector('.timer-text');
                if (textSpan) textSpan.textContent = duration.toFixed(2) + "s (Thought End)";
            }
        }

        // Add text to the sinuous buffer instead of DOM
        responseBuffer += text;

        // Start draining if not already running
        if (!isDraining) {
            isDraining = true;
            drainBuffer();
        }
    }
};

window.endStream = function () {
    isBackendFinished = true;
    if (typeof VoiceFX !== 'undefined' && VoiceFX.isActive && VoiceFX.isActive()) {
        VoiceFX.setState(VoiceFX.getMicRequested && VoiceFX.getMicRequested() ? 'listening' : 'idle');
        VoiceFX.bump(0.25);
    }

    // Stop the running timer update, as backend is done
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = null;

    // Update timer text to show Backend finish time
    if (currentStreamBubble && streamStartTime > 0 && !currentStreamBubble.timerFrozen) {
        const duration = (Date.now() - streamStartTime) / 1000;
        const textSpan = currentStreamBubble.timer.querySelector('.timer-text');
        if (textSpan) textSpan.textContent = duration.toFixed(2) + "s (Core Done)";
    }

    // If the buffer is already empty and draining finished, clean up UI instantly.
    // Otherwise, drainBuffer() will take care of finishStreamUI() when it hits 0.
    if (responseBuffer.length === 0) {
        finishStreamUI();
    }
};

// --- SYNERGY GRAPH UPDATE ---
window.updateAllmaStatus = function (percentage, statusText) {
    const circle = document.getElementById('synergy-circle-path');
    const text = document.getElementById('synergy-percent');

    if (circle) {
        // Stroke dasharray: 100.
        // percentage maps directly to dasharray value (0-100)
        circle.setAttribute('stroke-dasharray', `${percentage}, 100`);
    }

    if (text) {
        text.textContent = `${percentage}%`;
    }
};

// --- SETTINGS LOGIC (Dream Mode) ---
window.toggleDreamMode = function (checkbox) {
    const isEnabled = checkbox.checked;
    console.log("Dream Mode Toggled:", isEnabled);

    // 1. Persistence
    localStorage.setItem('dream_mode_enabled', isEnabled);

    // 2. Helper Text Update (Optional feedback)

    // 3. Send to Python
    if (window.pyBridge) {
        window.pyBridge.postMessage(JSON.stringify({
            type: 'action',
            action: 'toggle_dream_mode',
            enabled: isEnabled
        }));
    }
};

// Initialize Settings State
(function initSettings() {
    // Dream Mode
    const savedDream = localStorage.getItem('dream_mode_enabled');
    const dreamToggle = document.getElementById('dream-mode-toggle');
    if (dreamToggle) {
        // Default to false if not set, or true if saved 'true'
        dreamToggle.checked = (savedDream === 'true');

        // Sync with Python on load (in case app restarted)
        if (savedDream === 'true' && window.pyBridge) {
            setTimeout(function () {
                window.pyBridge.postMessage(JSON.stringify({
                    type: 'action',
                    action: 'toggle_dream_mode',
                    enabled: true
                }));
            }, 1500);
        }
    }
})();

// --- STATUS INDICATORS (Phase 17) ---
function showDreamToast(message, emoji) {
    // Rimuovi toast esistente se c'è
    const existing = document.getElementById('dream-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'dream-toast';
    toast.innerHTML = `<span class="dream-toast-emoji">${emoji}</span> ${message}`;
    document.body.appendChild(toast);

    // Triggera animazione entrata
    requestAnimationFrame(() => {
        requestAnimationFrame(() => toast.classList.add('visible'));
    });

    // Auto-dismiss dopo 4s
    setTimeout(() => {
        toast.classList.remove('visible');
        setTimeout(() => toast.remove(), 400);
    }, 4000);
}

window.updateStatus = function (key, active) {
    if (key === 'dreaming') {
        const indicator = document.getElementById('dream-indicator');
        if (active) {
            if (indicator) {
                indicator.classList.remove('hidden');
                indicator.classList.add('active', 'pulsing');
            }
            showDreamToast('ALLMA sta sognando e imparando...', '🌙');
        } else {
            if (indicator) {
                indicator.classList.remove('active', 'pulsing');
                setTimeout(() => {
                    if (!indicator.classList.contains('active')) {
                        indicator.classList.add('hidden');
                    }
                }, 500);
            }
            showDreamToast('Sogno completato. ALLMA si è evoluta.', '☀️');
        }
    }
};

// --- DREAM JOURNAL ---
const DREAM_PHASE_ICONS = {
    'start': '🌙',
    'memory': '💾',
    'tot': '🌳',
    'insight': '💡',
    'refine': '✨',
    'curiosity': '❓',
    'done': '☀️',
    'paused': '⏸️',
    'error': '❌',
    'default': '🔮',
};

window.restoreDreamHistory = function (history) {
    const container = document.getElementById('dream-journal-entries');
    if (!container) return;

    // Rimuovi tutte le entry attuali (tranne empty state se serve)
    container.innerHTML = '';

    if (!history || history.length === 0) {
        container.innerHTML = '<div class="dream-empty-state">Nessun sogno recente.<br>ALLMA svelerà i suoi pensieri qui.</div>';
        return;
    }

    // Aggiungi le entry storiche
    history.forEach(entry => {
        appendDreamEntry(entry.text, entry.phase, entry.timestamp);
    });
};

function appendDreamEntry(text, phase, timestampOverride = null) {

    const container = document.getElementById('dream-journal-entries');
    if (!container) return;

    // Rimuovi empty state se presente
    const empty = container.querySelector('.dream-empty-state');
    if (empty) empty.remove();

    const icon = DREAM_PHASE_ICONS[phase] || DREAM_PHASE_ICONS['default'];
    let timeObj = new Date();
    if (timestampOverride) {
        timeObj = new Date(timestampOverride);
    }
    const time = timeObj.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    const entry = document.createElement('div');
    entry.className = `dream-entry dream-entry--${phase || 'default'}`;
    entry.innerHTML = `
        <span class="dream-entry-icon">${icon}</span>
        <div class="dream-entry-content">
            <span class="dream-entry-text">${text}</span>
            <span class="dream-entry-time">${time}</span>
        </div>`;

    container.appendChild(entry);
    // Scroll in fondo
    container.scrollTop = container.scrollHeight;
}

window.clearDreamJournal = function () {
    const container = document.getElementById('dream-journal-entries');
    if (!container) return;
    container.innerHTML = `<div class="dream-empty-state"><span>🌙</span><p>Nessun sogno registrato.</p></div>`;
    const badge = document.getElementById('dream-status-badge');
    if (badge) { badge.textContent = 'In attesa...'; badge.className = 'dream-badge dream-badge--idle'; }
};

window.handleDreamLog = function (data) {
    // data = { text: "...", phase: "tot" }
    const text = data.text || data.content || String(data);
    const phase = data.phase || 'default';
    appendDreamEntry(text, phase);

    // Aggiorna badge stato
    const badge = document.getElementById('dream-status-badge');
    if (badge) {
        badge.textContent = '🌙 Sognando...';
        badge.className = 'dream-badge dream-badge--active';
    }
};

// --- DIAGNOSTICS PANEL LOGIC (v0.56) ---

let diagUpdateInterval = null;

function startDiagnostics() {
    console.log("Starting Diagnostics Monitoring...");
    if (diagUpdateInterval) clearInterval(diagUpdateInterval);

    // Immediate Request
    requestDiagnostics();

    // Poll every 1s
    diagUpdateInterval = setInterval(requestDiagnostics, 1000);
}

function stopDiagnostics() {
    console.log("Stopping Diagnostics.");
    if (diagUpdateInterval) {
        clearInterval(diagUpdateInterval);
        diagUpdateInterval = null;
    }
}

function requestDiagnostics() {
    if (window.msgQueue) {
        window.msgQueue.push("__REQUEST_DIAGNOSTICS_UPDATE__");
    } else if (window.pyBridge) {
        // Direct call if queue unavailable (should rely on bridge usually)
        // Check if we can post directly? No, usually handled by bridge queue consumer
        // Mock fallback for testing if no backend
        // displayDiagnostics(generateMockDiagnostics()); 
    }
}

// Called by Python via bridge: window.updateDiagnostics(jsonString)
window.updateDiagnostics = function (jsonStats) {
    try {
        const stats = (typeof jsonStats === 'string') ? JSON.parse(jsonStats) : jsonStats;
        displayDiagnostics(stats);
    } catch (e) {
        console.error("Diag Update Failed:", e);
    }
};

function displayDiagnostics(stats) {
    // 1. Resources
    if (stats.resources) {
        const cpu = stats.resources.cpu || 0;
        const ram = stats.resources.ram || 0; // MB
        const temp = stats.resources.temp || 0;

        updateBar('diag-cpu', cpu, '%', 100);

        // RAM max estimate? Say 4GB for phone logic or just raw MB
        const ramPercent = Math.min(100, (ram / 6000) * 100); // Assume 6GB soft cap for visualizations
        updateBar('diag-ram', ram, ' MB', 6000);

        updateBar('diag-temp', temp, '°C', 100);
    }

    // 2. Soul
    if (stats.soul) {
        setSoulBar('energy', stats.soul.energy);
        setSoulBar('chaos', stats.soul.chaos);
        setSoulBar('entropy', stats.soul.entropy);

        const statusEl = document.getElementById('soul-status-text');
        if (statusEl) statusEl.textContent = `Stato: ${stats.soul.state_label || 'Unknown'}`;
    }

    // 3. Log Trace
    if (stats.logs && Array.isArray(stats.logs)) {
        const logContainer = document.getElementById('diag-logs');
        if (logContainer) {
            // Log Buffer Strategy: Append ONLY new logs
            // The backend flushes its buffer on read, so whatever we get is new.

            stats.logs.forEach(log => {
                const div = document.createElement('div');
                div.className = 'log-entry';
                // Colorize based on level
                let color = '#D4D4D4'; // Default
                if (log.msg.includes('ERROR')) color = '#EF4444'; // Red
                if (log.msg.includes('WARN')) color = '#F59E0B'; // Orange
                if (log.msg.includes('LLM')) color = '#3B82F6'; // Blue
                if (log.msg.includes('SYSTEM')) color = '#10B981'; // Green
                if (log.msg.includes('INPUT')) color = '#A78BFA'; // Purple

                div.innerHTML = `<span class="log-time" style="opacity:0.5; font-size:10px; margin-right:6px;">${log.time || ''}</span><span class="log-msg" style="color:${color}">${log.msg}</span>`;
                logContainer.appendChild(div);
            });

            // Auto-scroll if near bottom
            logContainer.scrollTop = logContainer.scrollHeight;

            // Optional: Limit total DOM elements to avoid lag
            while (logContainer.children.length > 100) {
                logContainer.removeChild(logContainer.firstChild);
            }
        }
    }
}

function updateBar(idPrefix, value, unit, max) {
    const valEl = document.getElementById(idPrefix + '-val');
    const barEl = document.getElementById(idPrefix + '-bar');
    if (valEl) valEl.textContent = Math.round(value) + unit;
    if (barEl) {
        const pct = Math.min(100, (value / max) * 100);
        barEl.style.width = pct + '%';
        // Color logic
        if (pct > 80) barEl.style.backgroundColor = '#EF4444';
        else if (pct > 50) barEl.style.backgroundColor = '#F59E0B';
        else barEl.style.backgroundColor = '#3B82F6';
    }
}

function setSoulBar(type, value0to1) {
    const bar = document.getElementById(`soul-${type}-bar`);
    if (bar) {
        const pct = Math.min(100, Math.max(0, value0to1 * 100));
        bar.style.width = pct + '%';
    }
}


// --- VIEW MANAGEMENT (v0.57) ---
// --- DIAGNOSTICS LOGIC (v2 - Debug Enhanced) ---
let diagInterval = null;

function setDiagStatus(msg, color) {
    const el = document.getElementById('diag-conn-status');
    if (el) {
        el.innerText = msg;
        el.style.color = color;
    }
}

function startDiagnostics() {
    console.log("Diagnostics: Starting loop...");
    setDiagStatus("Starting...", "orange");

    if (diagInterval) clearInterval(diagInterval);

    // Immediate Request
    requestDiagnostics();

    // Loop every 1s
    diagInterval = setInterval(requestDiagnostics, 1000);
}

function stopDiagnostics() {
    console.log("Diagnostics: Stopping loop.");
    setDiagStatus("Stopped", "gray");
    if (diagInterval) {
        clearInterval(diagInterval);
        diagInterval = null;
    }
}

function requestDiagnostics() {
    if (window.pyBridge) {
        // Set a small delay before showing "Requesting" to avoid flicker on fast responses
        if (window._diagPending) clearTimeout(window._diagPending);
        window._diagPending = setTimeout(() => {
            setDiagStatus("Requesting...", "yellow");
        }, 150);
        window.pyBridge.postMessage("__REQUEST_DIAGNOSTICS_UPDATE__");
    } else {
        console.warn("Diagnostics: No pyBridge found!");
        setDiagStatus("No Bridge!", "red");
        updateDiagnostics(JSON.stringify(generateMockDiagnostics()));
    }
}

// Global exposure for Bridge
window.updateDiagnostics = function (input) {
    if (window._diagPending) clearTimeout(window._diagPending);
    setDiagStatus("Connected", "#10B981");

    try {
        let stats = input;
        if (typeof input === 'string') {
            try {
                stats = JSON.parse(input);
                if (typeof stats === 'string') stats = JSON.parse(stats);
            } catch (e) {
                console.error("Diag Parse Error:", e);
                return;
            }
        }

        if (!stats) return;

        // 1. Resources
        if (stats.resources) {
            const cpuVal = document.getElementById('diag-cpu-val');
            const cpuBar = document.getElementById('diag-cpu-bar');
            if (cpuVal) cpuVal.innerText = Math.round(stats.resources.cpu) + "%";
            if (cpuBar) cpuBar.style.width = Math.min(100, stats.resources.cpu) + "%";

            const ramVal = document.getElementById('diag-ram-val');
            const ramBar = document.getElementById('diag-ram-bar');
            if (ramVal) ramVal.innerText = Math.round(stats.resources.ram) + " MB";
            if (ramBar) {
                let ramPct = (stats.resources.ram / 4000) * 100; // Assume 4GB for mobile scaling
                ramBar.style.width = Math.min(100, ramPct) + "%";
            }

            const tempVal = document.getElementById('diag-temp-val');
            const tempBar = document.getElementById('diag-temp-bar');
            if (tempVal) tempVal.innerText = Math.round(stats.resources.temp) + "°C";
            if (tempBar) {
                let tempPct = (stats.resources.temp / 80) * 100;
                tempBar.style.width = Math.min(100, tempPct) + "%";
            }
        }

        // 2. Identity (V5) & Soul
        if (stats.soul) {
            const statusEl = document.getElementById('soul-status-text');
            let statusText = `Stato: ${stats.soul.state_label || 'Active'}`;

            // Append Neuro info if available
            if (stats.neuro && stats.neuro.active_rules !== undefined) {
                statusText += ` | Rules: ${stats.neuro.active_rules}`;
            }

            if (statusEl) statusEl.textContent = statusText;

            setSoulBar('energy', stats.soul.energy);
            setSoulBar('chaos', stats.soul.chaos);
            setSoulBar('entropy', stats.soul.entropy || 0.1);
        }

        // 3. Log Trace
        if (stats.logs && Array.isArray(stats.logs)) {
            const logContainer = document.getElementById('diag-logs');
            if (logContainer) {
                // Clear existing (we get a refresh)
                logContainer.innerHTML = '';
                stats.logs.forEach(log => {
                    const div = document.createElement('div');
                    div.className = 'log-entry';
                    let color = '#D4D4D4';
                    if (log.msg.includes('ERROR')) color = '#EF4444';
                    if (log.msg.includes('USER')) color = '#3B82F6';
                    if (log.msg.includes('BOT')) color = '#10B981';
                    div.innerHTML = `<span class="log-time" style="opacity:0.5; font-size:10px; margin-right:6px;">${log.time || ''}</span><span class="log-msg" style="color:${color}">${log.msg}</span>`;
                    logContainer.appendChild(div);
                });
                logContainer.scrollTop = logContainer.scrollHeight;
            }
        }
    } catch (e) {
        console.error("Diagnostics logic Error:", e);
    }
};

// --- VIEW MANAGEMENT (v0.58 Hardened) ---
window.switchView = function (viewName) {
    console.log("Switching view to:", viewName);

    // Safety: ensure elements exist
    const viewChat = document.getElementById('view-chat');
    const viewDiag = document.getElementById('view-diagnostics');
    const topHeader = document.getElementById('top-header');

    // FORCE DISPLAY MODES
    if (viewName === 'diagnostics') {
        if (viewChat) {
            viewChat.classList.remove('active');
            viewChat.classList.add('hidden');
            viewChat.style.display = 'none'; // HARD FORCE
        }
        if (viewDiag) {
            viewDiag.classList.add('active');
            viewDiag.classList.remove('hidden');
            viewDiag.style.display = 'flex'; // HARD FORCE
        }
        if (topHeader) topHeader.style.display = 'none';

        startDiagnostics();
    }
    else {
        // Chat Mode
        if (viewDiag) {
            viewDiag.classList.remove('active');
            viewDiag.classList.add('hidden');
            viewDiag.style.display = 'none'; // HARD FORCE
        }
        if (viewChat) {
            viewChat.classList.add('active');
            viewChat.classList.remove('hidden');
            viewChat.style.display = 'flex'; // HARD FORCE
        }
        if (topHeader) topHeader.style.display = 'flex';

        stopDiagnostics();
    }
};
