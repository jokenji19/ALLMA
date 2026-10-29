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

let chatBusy = false;
let backendBusy = false;
let newChatPending = false;
let activeRequestId = null;
let lastRequestId = 0;
let drainTimer = null;
let cancelPressRequestId = null;
let cancelIssuedRequestId = null;

const emptyChatMarkup = chatContainer.innerHTML;
function updateComposer() {
    document.getElementById('send-btn').disabled = chatBusy || !messageInput.value.trim();
    document.getElementById('send-btn').hidden = chatBusy;
    document.getElementById('voice-mode-btn').hidden = chatBusy;
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(140, Math.max(46, messageInput.scrollHeight)) + 'px';
}
messageInput.addEventListener('input', updateComposer);
function prepareConversation() {
    const empty = chatContainer.querySelector('.empty-chat');
    if (empty) empty.remove();
}

function setChatBusy(busy) {
    chatBusy = busy;
    if (window.brainView) window.brainView.setBusy(busy);
    messageInput.disabled = busy;
    document.getElementById('chat-status').textContent = busy ? (newChatPending ? 'Nuova conversazione…' : 'Sto rispondendo…') : '';
    updateComposer();
    const stop = document.getElementById('cancel-generation-btn');
    if (stop) {
        stop.hidden = !busy;
        stop.disabled = newChatPending || activeRequestId === null || cancelIssuedRequestId === activeRequestId;
        stop.textContent = cancelIssuedRequestId !== null && cancelIssuedRequestId === activeRequestId ? 'Interruzione…' : 'Interrompi';
    }
}

window.chatNotice = function (text) {
    const notice = document.getElementById('chat-notice');
    if (notice) notice.textContent = text;
};

window.turnFinished = function (requestId) {
    if (requestId !== lastRequestId) return;
    backendBusy = false;
    setChatBusy(newChatPending || currentStreamBubble !== null);
};

// Pointer activation must begin on Stop for this exact backend request.
// A gesture started on Send cannot be retargeted to its replacement.
window.armCancelGeneration = function () {
    cancelPressRequestId = !newChatPending && chatBusy ? activeRequestId : null;
};
window.disarmCancelGeneration = function () { cancelPressRequestId = null; };
window.cancelGeneration = function (event) {
    const requestId = activeRequestId;
    const armed = cancelPressRequestId;
    cancelPressRequestId = null;
    if (!chatBusy || newChatPending || requestId === null || cancelIssuedRequestId === requestId) return;
    // Keyboard and accessibility activation use detail=0, without a pointer.
    if (event && event.detail > 0 && armed !== requestId) return;
    cancelIssuedRequestId = requestId;
    const stop = document.getElementById('cancel-generation-btn');
    if (stop) { stop.disabled = true; stop.textContent = 'Interruzione…'; }
    window.pyBridge.postMessage(JSON.stringify({type: 'action', action: 'cancel_generation', request_id:requestId}));
};

window.newChatReady = function () {
    backendBusy = false;
    cancelPressRequestId = null;
    cancelIssuedRequestId = null;
    responseBuffer = '';
    thoughtBuffer = '';
    finishStreamUI();
    activeRequestId = null;
    newChatPending = false;
    chatContainer.innerHTML = emptyChatMarkup;
    window.chatNotice('');
    setChatBusy(false);
};

window.newChatFailed = function () {
    backendBusy = false;
    newChatPending = false;
    setChatBusy(false);
    window.chatNotice('Non è stato possibile aprire una nuova chat. Riprova.');
};

// --- MESSAGING ---
function sendMessage() {
    if (window._nativeUpdateReply && window._nativeUpdateReply.reserved) return;
    if (chatBusy || newChatPending) return;
    window.chatNotice('');
    const text = messageInput.value.trim();
    if (text) {
        const envelope = JSON.stringify({type: 'chat', text});
        if (envelope.length > 128 * 1024) {
            window.chatNotice('Il messaggio è troppo lungo. Dividilo in più parti.');
            return;
        }
        addMessage(text, 'user', null);
        messageInput.value = '';
        messageInput.blur();

        if (window.pyBridge) {
            // Mostra la bolla con i pallini animati prima del primo token
            window.startStream();
            window.pyBridge.postMessage(envelope);
        } else {
            console.warn("No PyBridge");
            setTimeout(() => addMessage("Test response", 'bot', "Thinking..."), 1000);
        }
    }
}

window.chatRejected = function (text) {
    if (activeRequestId !== null) return;
    if (currentStreamBubble) currentStreamBubble.content.closest('.message-wrapper')?.remove();
    backendBusy = false;
    finishStreamUI();
    if (!messageInput.value && typeof text === 'string') messageInput.value = text;
    updateComposer();
    window.chatNotice('Messaggio non inviato. Puoi riprovare.');
};

// Only inert formatting is allowed in generated Markdown, including streamed text.
function renderSafeMarkdown(target, text) {
    if (typeof marked === 'undefined') {
        target.textContent = text;
        return;
    }
    const template = document.createElement('template');
    // A standalone numeric answer such as "87." is text, not an empty list.
    const markdown = String(text).replace(/^(\s*\d{1,9})\.(\s*)$/gm, '$1\\.$2');
    template.innerHTML = marked.parse(markdown);
    const allowed = new Set(['P', 'BR', 'STRONG', 'EM', 'DEL', 'S', 'CODE', 'PRE',
        'BLOCKQUOTE', 'UL', 'OL', 'LI', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6',
        'HR', 'TABLE', 'THEAD', 'TBODY', 'TR', 'TH', 'TD', 'A']);
    function clean(parent) {
        for (const node of Array.from(parent.childNodes)) {
            if (node.nodeType === 3) continue;
            if (node.nodeType !== 1 || !allowed.has(node.tagName)) {
                node.remove();
                continue;
            }
            const href = node.tagName === 'A' ? node.getAttribute('href') : null;
            const start = node.tagName === 'OL' ? node.getAttribute('start') : null;
            for (const attr of Array.from(node.attributes)) node.removeAttribute(attr.name);
            if (start && /^\d{1,9}$/.test(start)) node.setAttribute('start', start);
            if (href) {
                try {
                    const url = new URL(href); // Absolute links only; never javascript/data/file.
                    if (['https:', 'http:'].includes(url.protocol)) {
                        node.setAttribute('href', url.href);
                        node.setAttribute('rel', 'noopener noreferrer');
                    }
                } catch (_) { /* Leave unsafe/relative links as plain text. */ }
            }
            clean(node);
        }
    }
    clean(template.content);
    target.replaceChildren(template.content);
}

// Copy only the message body; reasoning and interface labels are excluded.
const pendingCopies = new Map();
let copySequence = 0;
window.messageCopyResult = function (id, success) {
    const pending = pendingCopies.get(id);
    if (!pending) return;
    clearTimeout(pending.timer);
    pendingCopies.delete(id);
    success ? pending.resolve() : pending.reject(new Error('Clipboard unavailable'));
};
async function writeMessageClipboard(text) {
    if (window.allmaNativeClipboard) {
        return new Promise((resolve, reject) => {
            const id = 'copy-' + (++copySequence);
            const timer = setTimeout(() => window.messageCopyResult(id, false), 5000);
            pendingCopies.set(id, {resolve, reject, timer});
            try {
                window.pyBridge.postMessage(JSON.stringify({type:'action', action:'copy_message', id, text}));
            } catch (_) { window.messageCopyResult(id, false); }
        });
    }
    if (navigator.clipboard && window.isSecureContext) {
        try { await navigator.clipboard.writeText(text); return; } catch (_) { /* Browser fallback below. */ }
    }
    const focused = document.activeElement;
    const area = document.createElement('textarea');
    area.value = text;
    area.readOnly = true;
    area.style.cssText = 'position:fixed;left:-9999px;top:0;font-size:16px';
    document.body.appendChild(area);
    try {
        area.select();
        if (!document.execCommand('copy')) throw new Error('Clipboard unavailable');
    } finally {
        area.remove();
        if (focused && focused.isConnected) focused.focus({preventScroll:true});
    }
}
function attachMessageCopy(wrapper, text = null) {
    wrapper.copyText = typeof text === 'string' ? text : '';
    let button = wrapper.querySelector('.message-copy');
    if (!button) {
        const row = document.createElement('div');
        row.className = 'message-actions';
        button = document.createElement('button');
        button.type = 'button';
        button.className = 'message-copy';
        button.title = 'Copia messaggio';
        button.setAttribute('aria-label', 'Copia messaggio');
        button.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="8" y="8" width="12" height="13" rx="2"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h3"/></svg><span aria-live="polite">Copia</span>';
        button.addEventListener('click', async () => {
            if (!wrapper.copyText || button.disabled) return;
            button.disabled = true;
            const label = button.querySelector('span');
            try {
                await writeMessageClipboard(wrapper.copyText);
                label.textContent = 'Copiato';
                button.classList.add('copied');
            } catch (_) { label.textContent = 'Riprova'; }
            finally {
                button.disabled = false;
                clearTimeout(button.copyReset);
                button.copyReset = setTimeout(() => {
                    label.textContent = 'Copia'; button.classList.remove('copied');
                }, 2000);
            }
        });
        row.appendChild(button);
        wrapper.appendChild(row);
    }
    button.hidden = !wrapper.copyText.trim();
}

function attachPlanReview(wrapper, review) {
    if (!wrapper || !review || review.source !== 'host_count_coverage_v1'
        || !['needs_review', 'not_automatically_checkable'].includes(review.status)) return;
    const findings = Array.isArray(review.findings) ? review.findings : [];
    const finding = findings.find(item => item && Number.isInteger(item.required) && Number.isInteger(item.guaranteed)
        && item.guaranteed >= 0 && item.required > item.guaranteed && item.required <= 999);
    if ((review.status === 'needs_review' && !finding) || wrapper.querySelector('.message-plan-review')) return;
    const notice = document.createElement('div');
    notice.className = 'message-plan-review';
    notice.setAttribute('role', 'note');
    notice.textContent = review.status === 'needs_review'
        ? `Da rivedere: il criterio richiede ${finding.required} elementi controllati; un controllo nel piano ne garantisce ${finding.guaranteed}. Chiedimi una proposta corretta.`
        : 'Questo piano richiede una tua valutazione: il controllo automatico non copre tutti i requisiti.';
    wrapper.appendChild(notice);
}

function addMessage(text, sender, thoughtText, planReview = null, origin = null) {
    if (sender === 'bot') window.updateVoiceAnswer(text);
    const template = document.getElementById(sender === 'user' ? 'tmpl-user' : 'tmpl-bot');
    const clone = template.content.cloneNode(true);

    const contentSpan = clone.querySelector('.content');
    if (typeof marked !== 'undefined' && sender === 'bot') {
        renderSafeMarkdown(contentSpan, text);
    } else {
        contentSpan.textContent = text;
    }

    if (sender === 'bot' && thoughtText) {
        const reasoningContainer = clone.querySelector('.reasoning-container');
        const reasoningContent = clone.querySelector('.reasoning-content');
        if (reasoningContainer && reasoningContent) {
            reasoningContainer.classList.remove('hidden');
            reasoningContent.textContent = thoughtText;
        }
    }

    const wrapper = clone.querySelector('.message-wrapper');
    if (sender === 'bot' && !String(text || '').trim()) attachUnresolvedTurn(wrapper, origin);
    if (sender === 'bot') { attachPlanReview(wrapper, planReview); window.learningUI?.attachOrigin(wrapper, origin); }
    attachMessageCopy(wrapper, text);
    prepareConversation();
    chatContainer.appendChild(wrapper);
    scrollToBottom();
}

function toggleReasoning(header) {
    const expanded = header.parentElement.classList.toggle('open');
    header.setAttribute('aria-expanded', String(expanded));
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
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== 229) {
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
        updateComposer();
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

// Render only on incoming data, at most ten updates per second.
// No artificial typing delay and no polling while the model is silent.
let thoughtBuffer = "";
let lastStreamRender = 0;

function scheduleStreamRender() {
    if (drainTimer || document.hidden || !currentStreamBubble) return;
    const delay = Math.max(0, 100 - (performance.now() - lastStreamRender));
    drainTimer = setTimeout(drainBuffer, delay);
    isDraining = true;
}

function drainBuffer() {
    drainTimer = null;
    isDraining = false;
    if (!currentStreamBubble || !currentStreamBubble.content || document.hidden) return;
    const changed = !!(responseBuffer || thoughtBuffer);
    const needsScroll = !!responseBuffer || (thoughtBuffer && currentStreamBubble.reasoningContainer.classList.contains('open'));
    if (thoughtBuffer) {
        currentStreamBubble.reasoning.textContent += thoughtBuffer;
        thoughtBuffer = "";
    }
    if (responseBuffer) {
        currentStreamBubble.rawFullText = (currentStreamBubble.rawFullText || "") + responseBuffer;
        responseBuffer = "";
        renderSafeMarkdown(currentStreamBubble.content, currentStreamBubble.rawFullText);
    }
    if (changed) {
        lastStreamRender = performance.now();
        if (needsScroll) scrollToBottom();
    }
}

document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        if (drainTimer) clearTimeout(drainTimer);
        drainTimer = null;
        isDraining = false;
    } else if (responseBuffer || thoughtBuffer) {
        scheduleStreamRender();
    }
});

function finishStreamUI() {
    if (drainTimer) clearTimeout(drainTimer);
    drainTimer = null;
    isDraining = false;
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = null;

    if (currentStreamBubble && streamStartTime > 0 && !currentStreamBubble.timerFrozen) {
        const duration = (Date.now() - streamStartTime) / 1000;
        const textSpan = currentStreamBubble.timer.querySelector('.timer-text');
        if (textSpan) textSpan.textContent = duration.toFixed(2) + "s (UI Finish)";
    }
    if (currentStreamBubble) {
        attachMessageCopy(currentStreamBubble.content.closest('.message-wrapper'), currentStreamBubble.rawFullText || '');
    }
    currentStreamBubble = null;
    streamStartTime = 0;
    window.referenceActivity?.finish(activeRequestId);
    activeRequestId = null;
    setChatBusy(newChatPending || backendBusy);
}

// --- SIDEBAR LOGIC (v0.47) ---
function toggleSidebar() {
    console.log("Toggle Sidebar Executed");
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');

    sidebar.classList.toggle('active');
    sidebar.inert = !sidebar.classList.contains('active');
    sidebar.setAttribute('aria-hidden', String(sidebar.inert));
    backdrop.classList.toggle('active');
}

function startNewChat() {
    if (newChatPending) return;
    if (window.appNav) window.appNav.go('chat', {reset:true});
    newChatPending = true;
    setChatBusy(true);
    if (document.getElementById('sidebar').classList.contains('active')) toggleSidebar();
    window.chatNotice('Apertura nuova chat…');
    window.pyBridge.postMessage(JSON.stringify({type: 'action', action: 'new_chat'}));
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
    let lastRender = 0;
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
            for (let i = 0; i < 28; i++) {
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
            const count = 120;
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
            dpr = Math.min(1.5, Math.max(1, window.devicePixelRatio || 1));
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
            label.textContent = statusLabel(state);
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
        const now = performance.now();
        const interval = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 200 : state === 'thinking' ? 50 : 33;
        if (document.hidden || now - lastRender < interval) {
            raf = requestAnimationFrame(frame);
            return;
        }
        lastRender = now;
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
        lastRender = 0;
        quality = 1;
        qualityTarget = 1;
        if (!overlay.classList.contains('voice-glass') && !raf) raf = requestAnimationFrame(frame);
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

window.enterVoiceScreen = function () {
    console.log("Opening Voice Mode");
    const overlay = document.getElementById('voice-overlay');
    if (overlay) {
        overlay.classList.add('active');
        VoiceFX.activate();
        VoiceFX.setState('idle');
        VoiceFX.setMicRequested(false);
        const transcript = document.getElementById('voice-text');
        if (transcript) transcript.textContent = "";
        window.updateVoiceAnswer('Sono qui. Tocca il microfono e parliamo.');

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

window.leaveVoiceScreen = function () {
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

window.updateVoiceAnswer = function (text) {
    if (!document.getElementById('voice-overlay')?.classList.contains('active')) return;
    const target = document.getElementById('voice-answer');
    if (target) renderSafeMarkdown(target, String(text || ''));
};

window.updateVoiceText = function (text) {
    const el = document.getElementById('voice-text');
    if (el) el.textContent = text;
    if (text && VoiceFX.isActive()) window.updateVoiceAnswer('Ti ascolto. La risposta apparirà qui.');
    if (VoiceFX.isActive()) {
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
    VoiceFX.bump(0.45);
};

// Override toggleMic to open this mode
window.toggleMic = function () {
    openVoiceMode();
};

// --- PANEL MANAGEMENT ---

// Compatibility entry points: every sidebar destination uses internal navigation.
window.closePanel = function () { if (window.appNav) window.appNav.back(); };
window.openPanel = function (name) { if (window.appNav) window.appNav.go(name); };
window.openVoiceMode = function () { if (window.appNav) window.appNav.go('voice'); };
window.closeVoiceMode = function () { if (window.appNav && window.appNav.current === 'voice') window.appNav.back(); };

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
        console.log("Memory view updated");
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
    if (icon) icon.innerHTML = isDark
        ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></svg>'
        : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M20 13A8 8 0 0 1 11 4a8 8 0 1 0 9 9Z"/></svg>';
    if (text) text.textContent = 'Aspetto';
    document.querySelectorAll('[data-appearance]').forEach(button =>
        button.setAttribute('aria-pressed', String(button.dataset.appearance === (isDark ? 'dark' : 'light'))));
    if (window.pyBridge) window.pyBridge.postMessage(JSON.stringify({type:'action', action:'set_theme', dark:isDark}));
}

// Load Theme on Init
(function initTheme() {
    let savedTheme = null;
    try { savedTheme = localStorage.getItem('theme'); } catch (_) { /* Native offline document may restrict storage. */ }
    const isDark = savedTheme === 'dark';
    document.body.classList.toggle('dark-mode', isDark);
    updateThemeUI(isDark);
})();

// Profile fields live on an internal page; no dialog or focus trap.
window.prepareProfileFields = function () {
    try {
        document.getElementById('input-name').value = localStorage.getItem('allma_username') || '';
        document.getElementById('input-age').value = localStorage.getItem('allma_userage') || '';
    } catch (_) { /* Native profile synchronization still remains available. */ }
};
function openUserModal() { if (window.appNav) window.appNav.go('profile'); }
function closeUserModal() { if (window.appNav) window.appNav.back(); }

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
        console.log("User profile saved");

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
                console.log("Profile update sent to core");
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
    window.voiceControls?.render(status);
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
window.startStream = function (requestId = null) {
    if (requestId !== null) {
        if (requestId <= lastRequestId) return;
        if (activeRequestId !== null && activeRequestId !== requestId) return;
        backendBusy = true;
        cancelPressRequestId = null;
        cancelIssuedRequestId = null;
        activeRequestId = requestId;
        lastRequestId = requestId;
    }
    setChatBusy(true);
    window.referenceActivity?.begin(requestId);
    if (typeof VoiceFX !== 'undefined' && VoiceFX.isActive && VoiceFX.isActive()) {
        VoiceFX.setState('thinking');
        VoiceFX.bump(0.35);
    }
    document.querySelectorAll('.message-continue').forEach(button => button.hidden = true);
    // Bind the optimistic bubble to its real request before subsequent events.
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
    timerDiv.innerHTML = '<span>Elaborazione ·</span> <span class="timer-text">0.0s</span>';

    const wrapper = clone.querySelector('.message-wrapper');
    reasoningContainer.appendChild(timerDiv);

    prepareConversation();
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
    thoughtBuffer = "";
    lastStreamRender = 0;
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
    }, 500);
};

window.streamChunk = function (text, isThought, requestId = null) {
    if (requestId !== null && requestId !== activeRequestId) return;
    if (!currentStreamBubble) window.startStream();
    if (isThought) {
        if (currentStreamBubble.reasoningContainer.classList.contains('hidden')) {
            currentStreamBubble.reasoningContainer.classList.remove('hidden');
            // The user chooses whether to expand response details.
        }
        thoughtBuffer += text;
        scheduleStreamRender();
    } else {
        if (typeof VoiceFX !== 'undefined' && VoiceFX.isActive && VoiceFX.isActive()) {
            if (VoiceFX.getState && VoiceFX.getState() !== 'speaking') {
                VoiceFX.setState('thinking');
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
                if (textSpan) textSpan.textContent = duration.toFixed(2) + " s";
            }
        }

        responseBuffer += text;
        scheduleStreamRender();
    }
};

window.streamBatch = function (events) {
    if (!Array.isArray(events)) return;
    for (const event of events) {
        if (Array.isArray(event) && typeof event[0] === 'string') {
            window.streamChunk(event[0], event[1] === true, event[2]);
        }
    }
};

function attachUnresolvedTurn(wrapper, origin = null) {
    if (!wrapper || wrapper.querySelector('.turn-unresolved')) return;
    // An execution outcome belongs to UI, not to ALLMA's spoken answer.
    const content = wrapper.querySelector('.content');
    if (content) { content.textContent = ''; content.hidden = true; }
    const state = document.createElement('div'); state.className = 'turn-unresolved';
    state.setAttribute('role', 'status');
    const label = document.createElement('span');
    label.textContent = origin?.kind === 'incomplete' && typeof origin.label === 'string'
        ? origin.label.slice(0, 120) : 'Risposta non completata';
    if (origin?.kind === 'incomplete' && typeof origin.detail === 'string') label.title = origin.detail.slice(0, 600);
    const edit = document.createElement('button'); edit.type = 'button'; edit.textContent = 'Modifica domanda';
    edit.addEventListener('click', () => {
        if (chatBusy || newChatPending || messageInput.value.trim()) return;
        let previous = wrapper.previousElementSibling;
        while (previous && !previous.classList.contains('user')) previous = previous.previousElementSibling;
        const question = previous?.querySelector('.content, .message-bubble');
        if (question) { messageInput.value = question.textContent; messageInput.focus(); }
    });
    state.append(label, edit); wrapper.appendChild(state);
}

function attachCompletionAction(wrapper, requestId) {
    if (!wrapper.querySelector('.message-completion')) {
        const notice = document.createElement('div'); notice.className = 'message-completion';
        const label = document.createElement('span'); label.textContent = 'Risposta interrotta al limite di elaborazione.';
        const button = document.createElement('button'); button.type = 'button';
        button.className = 'message-continue'; button.textContent = 'Continua';
        button.addEventListener('click', () => {
            if (chatBusy || newChatPending || (requestId !== null && requestId !== lastRequestId)) return;
            if (messageInput.value.trim()) { window.chatNotice('Conserva o invia prima il messaggio che stai scrivendo.'); return; }
            messageInput.value = 'Completa la risposta precedente dal punto in cui si è interrotta, senza ripetere la parte già scritta.';
            sendMessage();
        });
        notice.append(label, button); wrapper.appendChild(notice);
    }
}

window.endStream = function (finalContent, requestId = null, status = null, planReview = null, origin = null) {
    if (requestId !== null && requestId !== activeRequestId) return;
    const followFinal = !!currentStreamBubble && chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight < 140;
    window.updateVoiceAnswer(finalContent);
    if (window.brainView) window.brainView.answer(finalContent);
    if (currentStreamBubble && thoughtBuffer) {
        currentStreamBubble.reasoning.textContent += thoughtBuffer;
        thoughtBuffer = '';
    }
    if (typeof finalContent === 'string' && currentStreamBubble) {
        responseBuffer = '';
        currentStreamBubble.rawFullText = finalContent;
        // Final text is authoritative even if the token stream was revised.
        renderSafeMarkdown(currentStreamBubble.content, finalContent);
        if (!finalContent.trim()) attachUnresolvedTurn(currentStreamBubble.content.closest('.message-wrapper'), origin);
    }
    if (status === 'truncated_answer' && currentStreamBubble && finalContent && finalContent.trim()) {
        attachCompletionAction(currentStreamBubble.content.closest('.message-wrapper'), requestId);
    }
    if (currentStreamBubble) attachPlanReview(currentStreamBubble.content.closest('.message-wrapper'), planReview);
    if (currentStreamBubble) window.learningUI?.attachOrigin(currentStreamBubble.content.closest('.message-wrapper'), origin);
    isBackendFinished = true;
    if (typeof VoiceFX !== 'undefined' && VoiceFX.isActive && VoiceFX.isActive()) {
        // Native recognizer and playback callbacks own the voice state.
        VoiceFX.bump(0.25);
    }

    // Stop the running timer update, as backend is done
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = null;

    // Update timer text to show Backend finish time
    if (currentStreamBubble && streamStartTime > 0) {
        const duration = (Date.now() - streamStartTime) / 1000;
        const textSpan = currentStreamBubble.timer.querySelector('.timer-text');
        if (textSpan) textSpan.textContent = duration.toFixed(2) + " s";
        currentStreamBubble.timerFrozen = true;
    }

    // The validated final response replaces the preview immediately.
    if (responseBuffer.length === 0) {
        finishStreamUI();
    }
    if (followFinal) scrollToBottom(true);
};

// --- SYNERGY GRAPH UPDATE ---
window.updateAllmaStatus = function (percentage, statusText) {
    const circle = document.getElementById('synergy-circle-path');
    const text = document.getElementById('synergy-percent');

    if (circle) {
        if (!Number.isFinite(percentage)) circle.setAttribute('stroke-dasharray', '0, 100');
        // Stroke dasharray: 100.
        // percentage maps directly to dasharray value (0-100)
        if (Number.isFinite(percentage)) circle.setAttribute('stroke-dasharray', `${percentage}, 100`);
    }

    if (text) {
        text.textContent = Number.isFinite(percentage) ? `${percentage}%` : statusText;
    }
};

// --- SETTINGS LOGIC (Dream Mode) ---
// The native archive is the sole authority. Never replay a browser preference.
let dreamSettingsKnown = false;
let dreamSettingsEnabled = false;
let dreamSettingsTimer = null;
window.receiveDreamSettings = function (state) {
    if (!state || typeof state.enabled !== 'boolean') return;
    clearTimeout(dreamSettingsTimer);
    dreamSettingsKnown = true;
    dreamSettingsEnabled = state.enabled;
    const toggle = document.getElementById('dream-mode-toggle');
    if (toggle) { toggle.checked = state.enabled; toggle.disabled = false; }
    const notice = document.getElementById('dream-settings-status');
    if (notice) notice.textContent = state.error || '';
};
window.refreshDreamSettings = function () {
    if (window.pyBridge) window.pyBridge.postMessage(JSON.stringify({type:'action',action:'dream_status'}));
};
window.toggleDreamMode = function (checkbox) {
    const wanted = checkbox.checked;
    checkbox.disabled = true;
    if (!dreamSettingsKnown || !window.pyBridge) {
        checkbox.checked = dreamSettingsEnabled;
        checkbox.disabled = !dreamSettingsKnown;
        window.refreshDreamSettings();
        return;
    }
    dreamSettingsTimer = setTimeout(() => {
        checkbox.checked = dreamSettingsEnabled;
        checkbox.disabled = false;
        const notice = document.getElementById('dream-settings-status');
        if (notice) notice.textContent = 'Conferma non ricevuta. Aggiorna le impostazioni.';
        window.refreshDreamSettings();
    }, 10000);
    window.pyBridge.postMessage(JSON.stringify({type:'action',action:'toggle_dream_mode',enabled:wanted}));
};
(function initSettings() {
    const toggle = document.getElementById('dream-mode-toggle');
    if (toggle) { toggle.checked = false; toggle.disabled = true; window.refreshDreamSettings(); }
})();

// --- STATUS INDICATORS (Phase 17) ---
window.updateStatus = function (key, active) {
    if (key === 'dreaming') {
        const indicator = document.getElementById('dream-indicator');
        if (active) {
            if (indicator) {
                indicator.classList.remove('hidden');
                indicator.classList.add('active', 'pulsing');
            }
        } else {
            if (indicator) {
                indicator.classList.remove('active', 'pulsing');
                setTimeout(() => {
                    if (!indicator.classList.contains('active')) {
                        indicator.classList.add('hidden');
                    }
                }, 500);
            }
        }
    }
};

// --- DREAM JOURNAL ---
const DREAM_PHASE_ICONS = {
    'start': '🌙',
    'memory': '💾',
    'tot': '🌳',
    'insight': '💡',
    'hypothesis': '💭',
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
    const safePhase = Object.prototype.hasOwnProperty.call(DREAM_PHASE_ICONS, phase) ? phase : 'default';
    entry.className = `dream-entry dream-entry--${safePhase}`;
    entry.innerHTML = `
        <span class="dream-entry-icon">${icon}</span>
        <div class="dream-entry-content">
            <span class="dream-entry-text"></span>
            <span class="dream-entry-time">${time}</span>
        </div>`;

    entry.querySelector('.dream-entry-text').textContent = String(text);
    container.appendChild(entry);
    while (container.children.length > 50) container.firstElementChild.remove();
    // Scroll in fondo
    container.scrollTop = container.scrollHeight;
}

const dreamReviewDrafts = new Map();
let dreamReviewBusy = false;
let dreamReviewTimer = null;
let dreamReviewItems = [];
let dreamReviewShowRejected = false;

function dreamReviewNotice(text) {
    const notice = document.getElementById('dream-review-notice');
    if (notice) notice.textContent = text || '';
}

function sendDreamReview(item, decision, correction = '', note = '') {
    if (dreamReviewBusy) return;
    const message = JSON.stringify({type: 'action', action: 'review_dream_hypothesis',
        id: item.id, revision: item.revision, decision, correction, note});
    if (!window.pyBridge && !window.msgQueue) {
        dreamReviewNotice('Collegamento non disponibile. La revisione non è stata salvata.');
        return;
    }
    dreamReviewBusy = true;
    document.querySelectorAll('#dream-review-items button').forEach(button => { button.disabled = true; });
    dreamReviewNotice('Salvataggio della revisione…');
    dreamReviewTimer = setTimeout(() => {
        dreamReviewBusy = false;
        document.querySelectorAll('#dream-review-items button').forEach(button => { button.disabled = false; });
        dreamReviewNotice('Conferma di salvataggio non ricevuta. Aggiorna il diario o riprova.');
    }, 15000);
    if (window.pyBridge) window.pyBridge.postMessage(message);
    else window.msgQueue.push(message);
}

window.restoreDreamReviews = function (state) {
    const container = document.getElementById('dream-review-items');
    if (!container) return;
    dreamReviewItems = Array.isArray(state.items) ? state.items : [];
    container.replaceChildren();
    const count = document.getElementById('dream-review-count');
    const pending = dreamReviewItems.filter(item => item.status === 'unverified').length;
    if (count) count.textContent = pending ? (pending === 1 ? '1 riflessione da valutare' : pending + ' riflessioni da valutare') : 'Nessuna nuova riflessione da valutare';
    const rejectedCount = dreamReviewItems.filter(item => item.status === 'rejected').length;
    if (rejectedCount) {
        const toggle = document.createElement('button');
        toggle.type = 'button'; toggle.className = 'dream-review-archive-toggle';
        toggle.disabled = dreamReviewBusy;
        toggle.setAttribute('aria-expanded', String(dreamReviewShowRejected));
        toggle.textContent = (dreamReviewShowRejected ? 'Nascondi scartate' : 'Mostra scartate') + ' (' + rejectedCount + ')';
        toggle.addEventListener('click', () => {
            dreamReviewShowRejected = !dreamReviewShowRejected;
            window.restoreDreamReviews({items: dreamReviewItems});
        });
        container.append(toggle);
    } else {
        dreamReviewShowRejected = false;
    }
    const visibleItems = dreamReviewItems.filter(item => dreamReviewShowRejected || item.status !== 'rejected');
    if (!visibleItems.length) {
        const empty = document.createElement('p');
        empty.className = 'dream-review-explanation';
        empty.textContent = rejectedCount ? 'Nessuna ipotesi attiva. Le scartate sono conservate nella cronologia.' : 'Nessuna ipotesi da valutare.';
        container.append(empty);
        return;
    }
    const labels = {unverified: 'Da verificare', user_confirmed: 'Confermata da te',
        user_corrected: 'Corretta da te', rejected: 'Scartata — esclusa dalle risposte'};
    visibleItems.forEach(item => {
        const card = document.createElement('article');
        card.className = 'dream-review-card';
        const status = document.createElement('p');
        status.className = 'dream-review-status';
        status.textContent = labels[item.status] || 'Da verificare';
        const text = document.createElement('p');
        text.className = 'dream-review-text';
        text.textContent = item.text;
        card.append(status, text);
        const details = document.createElement('details');
        const summary = document.createElement('summary');
        summary.textContent = 'Origine e revisione';
        const origin = document.createElement('p');
        origin.textContent = 'Ipotesi originale: ' + item.original_text;
        const evidence = document.createElement('p');
        evidence.textContent = item.evidence && item.evidence.text ? 'Dal tuo messaggio: ' + item.evidence.text : 'Messaggio di origine non disponibile per questa ipotesi precedente.';
        const revision = document.createElement('p');
        revision.textContent = 'Revisione ' + item.revision + (item.reviewed_at ? ' · ' + new Date(item.reviewed_at).toLocaleString('it-IT') : '');
        if (item.review_note) revision.textContent += ' · ' + item.review_note;
        details.append(summary, origin, evidence, revision);
        if (Array.isArray(item.review_history) && item.review_history.length) {
            const history = document.createElement('ul');
            history.setAttribute('aria-label', 'Ultime cinque revisioni');
            item.review_history.forEach(event => {
                const line = document.createElement('li');
                const decisions = {confirm: 'Confermata', correct: 'Corretta', reject: 'Scartata'};
                line.textContent = 'Revisione ' + event.revision + ': ' + (decisions[event.decision] || event.decision) +
                    ' · ' + new Date(event.reviewed_at).toLocaleString('it-IT');
                if (event.text) line.textContent += ' · ' + event.text;
                if (event.note) line.textContent += ' · ' + event.note;
                history.append(line);
            });
            details.append(history);
        }
        card.append(details);
        const actions = document.createElement('div');
        actions.setAttribute('aria-label', 'Scegli cosa fare con questa riflessione');
        actions.className = 'dream-review-actions';
        function button(label, action) {
            const el = document.createElement('button');
            el.type = 'button'; el.textContent = label; el.disabled = dreamReviewBusy;
            el.addEventListener('click', action);
            actions.append(el);
            return el;
        }
        const editor = document.createElement('div');
        editor.className = 'dream-review-editor';
        editor.hidden = !dreamReviewDrafts.has(item.id);
        const correction = document.createElement('textarea');
        correction.setAttribute('aria-label', 'Correzione dell’ipotesi');
        correction.maxLength = 2000;
        correction.value = dreamReviewDrafts.get(item.id)?.correction ?? item.text;
        const note = document.createElement('textarea');
        note.setAttribute('aria-label', 'Motivo della correzione, facoltativo');
        note.placeholder = 'Motivo della correzione (facoltativo)'; note.maxLength = 2000;
        note.value = dreamReviewDrafts.get(item.id)?.note ?? '';
        const save = document.createElement('button');
        save.type = 'button'; save.textContent = 'Salva correzione'; save.disabled = dreamReviewBusy;
        const draft = () => dreamReviewDrafts.set(item.id, {correction: correction.value, note: note.value});
        correction.addEventListener('input', draft); note.addEventListener('input', draft);
        save.addEventListener('click', () => {
            if (!correction.value.trim()) { dreamReviewNotice('Scrivi una correzione prima di salvarla.'); return; }
            draft(); sendDreamReview(item, 'correct', correction.value, note.value);
        });
        editor.append(correction, note, save);
        button(item.status === 'user_corrected' ? 'Conferma l’originale' : 'Conferma', () => sendDreamReview(item, 'confirm')).classList.add('dream-confirm-action');
        const editButton = button('Correggi', () => {
            editor.hidden = !editor.hidden;
            editButton.setAttribute('aria-expanded', String(!editor.hidden));
            if (!editor.hidden) correction.focus();
        });
        editButton.setAttribute('aria-expanded', String(!editor.hidden));
        button('Scarta', () => sendDreamReview(item, 'reject'));
        card.append(actions, editor);
        container.append(card);
    });
};

window.dreamReviewResult = function (result) {
    clearTimeout(dreamReviewTimer); dreamReviewTimer = null;
    dreamReviewBusy = false;
    if (result.ok && result.reviewed_id) dreamReviewDrafts.delete(result.reviewed_id);
    if (Array.isArray(result.items)) window.restoreDreamReviews(result);
    else document.querySelectorAll('#dream-review-items button').forEach(button => { button.disabled = false; });
    const discarded = result.ok && Array.isArray(result.items) && result.items.some(item =>
        item.id === result.reviewed_id && item.status === 'rejected');
    dreamReviewNotice(result.ok ? (discarded ? 'Ipotesi scartata ed esclusa dalle risposte. La cronologia resta disponibile in Mostra scartate.' :
        'Revisione salvata. Puoi modificarla o revocarla.') : result.error || 'Salvataggio non riuscito. Riprova.');
};

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
    if (['done', 'paused', 'error'].includes(phase) && !dreamReviewBusy &&
            !document.getElementById('panel-dream')?.classList.contains('hidden')) {
        if (window.pyBridge) window.pyBridge.postMessage('__REQUEST_DREAM_HISTORY__');
        else if (window.msgQueue) window.msgQueue.push('__REQUEST_DREAM_HISTORY__');
    }

    // Aggiorna badge stato
    const badge = document.getElementById('dream-status-badge');
    if (badge) {
        const labels = {done: 'Da verificare', hypothesis: 'Ipotesi da verificare', paused: 'In pausa', error: 'Errore'};
        badge.textContent = labels[phase] || 'Riflessione in corso';
        badge.className = 'dream-badge ' + (['done', 'paused', 'error'].includes(phase) ? 'dream-badge--idle' : 'dream-badge--active');
    }
};

// --- DIAGNOSTICS PANEL LOGIC (v0.56) ---

function updateBar(idPrefix, value, unit, max) {
    const valEl = document.getElementById(idPrefix + '-val');
    const barEl = document.getElementById(idPrefix + '-bar');
    const available = typeof value === 'number' && Number.isFinite(value);
    if (valEl) valEl.textContent = available ? Math.round(value) + unit : 'N/D';
    if (barEl) {
        const pct = available ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
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
    setDiagStatus("Verifico lo stato…", "var(--text-secondary)");

    if (diagInterval) clearInterval(diagInterval);

    // Immediate Request
    requestDiagnostics();

    // Loop every 1s
    diagInterval = setInterval(requestDiagnostics, 1000);
}

function stopDiagnostics() {
    console.log("Diagnostics: Stopping loop.");
    setDiagStatus("Monitoraggio in pausa", "var(--text-secondary)");
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
            setDiagStatus("Aggiornamento in corso…", "var(--text-secondary)");
        }, 150);
        window.pyBridge.postMessage("__REQUEST_DIAGNOSTICS_UPDATE__");
    } else {
        console.warn("Diagnostics: No pyBridge found!");
        setDiagStatus("Collegamento non disponibile", "var(--primary-color)");
        window.updateDiagnostics({resources: {cpu: null, ram: null, temp: null}, logs: []});
        setDiagStatus('Non collegato', 'var(--text-secondary)');
    }
}

// Global exposure for Bridge
window.updateDiagnostics = function (input) {
    if (window._diagPending) clearTimeout(window._diagPending);
    setDiagStatus("Dati aggiornati", "var(--text-secondary)");

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

        if (stats.backends) {
            const names = {opencl: 'GPU · OpenCL', hexagon: 'NPU · Hexagon', cpu: 'CPU', not_loaded: 'non caricato'};
            const reasons = {previous_gpu_operation_incomplete: 'protezione attiva dopo un’operazione GPU interrotta',
                previous_npu_operation_incomplete: 'protezione attiva dopo un’operazione NPU interrotta',
                package_update_recovered: 'ripristinato dopo un aggiornamento verificato',
                measured_profile: 'profilo verificato', measured_decider_profile: 'profilo verificato',
                unmeasured_soc: 'accelerazione non ancora verificata su questo dispositivo',
                unmeasured_driver: 'driver non ancora verificato', not_loaded: 'si collega quando serve'};
            for (const [key, label] of [['qwen', 'Conversazione'], ['decider', 'Decisore']]) {
                const item = stats.backends[key] || {};
                const target = document.getElementById(`diag-${key}-backend`);
                if (target) target.textContent = `${label}: ${names[item.kind] || 'stato non disponibile'}${item.reason ? ' · ' + (reasons[item.reason] || item.reason) : ''}`;
            }
        }

        if (stats.resources) {
            updateBar('diag-cpu', stats.resources.cpu, '%', 100);
            updateBar('diag-ram', stats.resources.ram, ' MB', 4000);
            updateBar('diag-temp', stats.resources.temp, '°C', 80);
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
            setSoulBar('entropy', stats.soul.entropy ?? 0);
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
                    const time = document.createElement('span');
                    time.className = 'log-time';
                    time.textContent = log.time || '';
                    const message = document.createElement('span');
                    message.className = 'log-msg';
                    message.style.color = color;
                    message.textContent = String(log.msg || '');
                    div.append(time, message);
                    logContainer.appendChild(div);
                });
                logContainer.scrollTop = logContainer.scrollHeight;
            }
        }
    } catch (e) {
        console.error("Diagnostics logic Error:", e);
    }
};

// Public alias retained for native callbacks and older diagnostic entry points.
window.switchView = function (viewName) { if (window.appNav) window.appNav.go(viewName); };

window.updateVoiceState = function(payload) {
    if (!VoiceFX.isActive()) return;
    const actual = payload?.state || 'idle';
    const visual = {permission:'idle', starting:'idle', recognizing:'thinking', error:'idle', ready:'idle'}[actual] || actual;
    VoiceFX.setState(visual);
    VoiceFX.setMicRequested(actual === 'listening' || actual === 'starting');
    const label = document.getElementById('voice-status');
    if (label) label.textContent = payload?.message || {idle:'Tocca il microfono per parlare.', listening:'Ti ascolto…', starting:'Attivo il microfono…', thinking:'Sto elaborando…', speaking:'Sto parlando…', recognizing:'Trascrivo…'}[actual] || 'Attendi…';
    const footer = document.querySelector('#voice-overlay .voice-footer');
    if (footer) footer.textContent = actual === 'listening' ? 'Tocca per terminare l’ascolto' :
        (actual === 'thinking' || actual === 'speaking') ? 'Tocca per interrompere' : 'Tocca il microfono per parlare';
    const button = document.getElementById('voice-mic-btn');
    if (button) {
        button.disabled = actual === 'permission' || actual === 'recognizing';
        button.classList.toggle('is-stop', actual === 'thinking' || actual === 'speaking');
        button.setAttribute('aria-label', actual === 'thinking' || actual === 'speaking' ? 'Interrompi' : 'Microfono');
    }
};
window.updateVoiceLevel = function(level) { if (VoiceFX.isActive()) VoiceFX.bump(Math.max(0, Math.min(1, Number(level)))); };
window.hideVoiceMode = function() {
    if (window.appNav && window.appNav.current === 'voice') window.appNav.back();
    else VoiceFX.deactivate();
};

function syncAmbientMotion() {
    document.body.classList.toggle('motion-paused', document.hidden);
}
document.addEventListener('visibilitychange', syncAmbientMotion);
syncAmbientMotion();

// One benchmark configuration shared by settings and diagnostics.
// Maintenance is local and transient. The native gate is the authority;
// disabling input here only keeps the installation state clear to the user.
window.nativeUpdateState = function (state) {
    window._nativeUpdateReply = state;
    const input = document.getElementById('message-input');
    if (input && state.reserved) {
        input.disabled = true;
        input.placeholder = 'Aggiornamento in preparazione…';
    } else if (input && !chatBusy && !newChatPending) {
        input.disabled = false;
        input.placeholder = 'Scrivi ad ALLMA…';
    }
};

window.openBenchmarkSettings = function () {
    if (window.appNav) window.appNav.go('diagnostics');
};

// The native model is replaceable; personal history belongs to ALLMA.
window.modelUI = {
    models: [], busy: false, selectionRequired: false, selectionMessage: '', recoveryShown: false,
    refresh() {
        if (!this.busy) window.pyBridge.postMessage(JSON.stringify({type:'action',action:'list_models'}));
    },
    select() {
        const key = document.getElementById('model-choice').value;
        const model = this.models.find(m => m.key === key);
        const button = document.getElementById('model-apply');
        button.disabled = this.busy || !model || model.active;
        button.textContent = !model ? 'Verifico i modelli…' : model.active ? 'Modello in uso' : model.available ? 'Verifica e usa' : 'Scarica e usa';
        if (!this.busy && model) document.getElementById('model-status').textContent =
            `${model.active ? 'In uso' : model.available ? (model.verified ? 'Verificato' : 'Installato · verifica prima dell’uso') : 'Da scaricare'} · ${(model.size_bytes/1e9).toFixed(2)} GB · ${model.quantization} · ragionamento disponibile`;
        if (!this.busy && this.selectionRequired) document.getElementById('model-status').textContent = this.selectionMessage;
    },
    apply() {
        if (this.busy) return;
        const key = document.getElementById('model-choice').value;
        if (!this.models.some(m => m.key === key && !m.active)) return;
        this.busy = true;
        document.getElementById('model-choice').disabled = true;
        this.select();
        document.getElementById('model-status').textContent = 'Preparo il modello. Mantieni ALLMA aperta.';
        window.pyBridge.postMessage(JSON.stringify({type:'action', action:'apply_model', key}));
    },
    update(data) {
        const choice = document.getElementById('model-choice');
        const status = document.getElementById('model-status');
        const progress = document.getElementById('model-progress');
        if (!choice) return;
        if (data.phase === 'ready') {
            const previous = choice.value;
            const previousActive = (this.models.find(m => m.active) || {}).key;
            this.models = data.models || [];
            this.busy = !!data.busy;
            this.selectionRequired = data.selection_required === true;
            this.selectionMessage = data.selection_message || 'Scegli un modello per riprendere la conversazione.';
            choice.replaceChildren(...this.models.map(model => {
                const option = document.createElement('option');
                option.value = model.key;
                option.textContent = model.name + (model.active ? ' · in uso' : '');
                return option;
            }));
            const active = this.models.find(m => m.active);
            const modelLabel = document.getElementById('composer-model-name');
            if (modelLabel) modelLabel.textContent = active ? active.name : 'Modello locale';
            choice.value = this.models.some(m => m.key === previous) && (!active || active.key === previousActive) ? previous : (active || this.models[0] || {}).key || '';
            choice.disabled = this.busy;
            progress.hidden = true;
            this.select();
            if (this.selectionRequired && !this.recoveryShown && window.appNav) {
                this.recoveryShown = true;
                window.appNav.go('settings/model');
            }
            if (!this.selectionRequired) this.recoveryShown = false;
        } else if (data.phase === 'error') {
            this.busy = false;
            choice.disabled = false;
            progress.hidden = true;
            this.select();
            status.textContent = data.error || 'Cambio non riuscito. Riprova.';
        } else {
            this.busy = true;
            choice.disabled = true;
            this.select();
            progress.hidden = false;
            if (data.phase === 'loading' || data.phase === 'verifying') {
                progress.removeAttribute('value');
                status.textContent = data.phase === 'verifying' ? 'Verifico il file prima di usarlo…' : 'Collego il nuovo modello ad ALLMA…';
            } else {
                progress.value = Math.max(0, Math.min(1, data.progress || 0));
                status.textContent = `Download e verifica · ${Math.round(progress.value*100)}%`;
            }
        }
    }
};

// Populate the composer immediately; inventory never hashes GGUF files.
window.modelUI.refresh();

window.deciderUI = {
    refresh() { window.pyBridge.postMessage(JSON.stringify({type:'action',action:'decider_status'})); },
    configure(enabled) {
        document.getElementById('decider-toggle').disabled = true;
        window.pyBridge.postMessage(JSON.stringify({type:'action',action:'set_decider',enabled}));
    },
    update(data) {
        const toggle = document.getElementById('decider-toggle');
        toggle.disabled = false;
        if (typeof data.enabled === 'boolean') toggle.checked = data.enabled;
        if (data.error) { document.getElementById('decider-status').textContent = data.error; return; }
        toggle.checked = !!data.enabled;
        document.getElementById('decider-status').textContent = !data.enabled ? 'Disattivato. ALLMA usa il percorso ordinario.'
            : !data.available ? 'Modello assente: installalo con «Prova del decisore» in Diagnostica.'
            : data.last_status === 'thermal_pause' ? 'In pausa per temperatura. ALLMA continua con il percorso ordinario.'
            : data.loaded ? 'Operativo · modello caricato. Le decisioni incerte restano ad ALLMA.'
            : 'Abilitato · viene caricato quando serve. Può aggiungere attesa e consumo.';
    }
};

window.notificationUI = {
    refresh() { window.pyBridge.postMessage(JSON.stringify({type:'action',action:'notification_status'})); },
    setEnabled(enabled) {
        document.getElementById('notification-toggle').disabled = true;
        document.getElementById('notification-status').textContent = enabled ? 'Attendo la tua scelta su Android…' : 'Disattivo le notifiche…';
        window.pyBridge.postMessage(JSON.stringify({type:'action',action:'set_notifications',enabled}));
    },
    test() { window.pyBridge.postMessage(JSON.stringify({type:'action',action:'test_notification'})); },
    openSettings() { window.pyBridge.postMessage(JSON.stringify({type:'action',action:'notification_settings'})); },
    update(data) {
        const toggle = document.getElementById('notification-toggle');
        const status = document.getElementById('notification-status');
        toggle.disabled = data.supported === false;
        if (data.error) { status.textContent = data.error; return; }
        toggle.checked = !!data.enabled;
        document.getElementById('notification-test').disabled = !data.active;
        document.getElementById('notification-system-settings').hidden = !data.supported || data.allowed;
        status.textContent = data.test_sent === true ? 'Prova inviata: controlla le notifiche del telefono.'
            : data.test_sent === false ? 'Prova non inviata. Controlla il consenso e le impostazioni Android.'
            : !data.supported ? 'Le notifiche di sistema sono disponibili nell’app Android.'
            : data.active ? 'Attive. Puoi disattivarle in qualsiasi momento.'
            : data.enabled ? 'Bloccate da Android. Controlla le impostazioni del telefono.'
            : 'Disattivate. ALLMA non invia notifiche.';
    }
};
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && window.appNav?.current === 'settings/notifications') window.notificationUI.refresh();
});

// The explorer submits through the same admission, conversation and cancel path.
window.submitBrainQuestion = function(text) {
    if (chatBusy || newChatPending || !String(text || '').trim()) return false;
    messageInput.value = String(text);
    sendMessage();
    return true;
};
window.brainChatBusy = () => chatBusy;

window.brainCanCancel = () => chatBusy && !newChatPending && activeRequestId !== null && cancelIssuedRequestId !== activeRequestId;

// Backup passwords live only in the pending native action; never in storage.
window.backupUI = {
    send(action, fields = {}) {
        window.pyBridge.postMessage(JSON.stringify({type:'action',action,...fields}));
    },
    refresh() { this.send('backup_status'); },
    configure(enabled) { this.send('backup_configure',{enabled}); },
    transfer(action) {
        const input=document.getElementById('backup-password');
        const password=input.value; input.value='';
        if (password.length<12) {
            document.getElementById('backup-message').textContent='Usa almeno 12 caratteri e conserva la password.';
            return;
        }
        this.send(action,{password});
    },
    update(data) {
        const busy=!!data.busy || !!this.restartRequired;
        document.querySelectorAll('[data-backup-action]').forEach(button=>button.disabled=busy);
        const toggle=document.getElementById('backup-auto');
        toggle.disabled=busy || data.available===false;
        if (typeof data.enabled==='boolean') toggle.checked=data.enabled;
        const latest=data.latest;
        document.getElementById('backup-status').textContent=latest
            ? 'Copie private: '+data.count+' · ultima '+new Date(latest.created).toLocaleString('it-IT')
            : 'Nessuna copia privata verificata disponibile.';
        if(data.error || data.message) document.getElementById('backup-message').textContent=data.error || data.message;
        if(Object.prototype.hasOwnProperty.call(data,'preview')) {
            document.getElementById('backup-preview').hidden=!data.preview;
            if(data.preview) document.getElementById('backup-preview-text').textContent=
                'Copia del '+new Date(data.preview.created).toLocaleString('it-IT')+' · '+data.preview.files+' archivi verificati.';
        }
        if(data.restart_required) {
            this.restartRequired=true;
            document.getElementById('backup-preview').hidden=true;
            document.querySelectorAll('[data-backup-action]').forEach(button=>button.disabled=true);
        }
    }
};
