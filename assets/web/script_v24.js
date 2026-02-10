// Python Bridge Interface v24
// Architecture: Flexbox Layout + Safe Timer

const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');

// --- MESSAGING ---
function sendMessage() {
    const text = messageInput.value.trim();
    if (text) {
        addMessage(text, 'user', null);
        messageInput.value = '';
        messageInput.blur(); // Keep keyboard open? Usually prefer to close or keep. User preference.
        // If we keep it open, Flexbox handles it.

        if (window.pyBridge) {
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

function scrollToBottom() {
    // Scroll to the very bottom of the chat container
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

messageInput.addEventListener('focus', () => {
    setTimeout(scrollToBottom, 100);
    setTimeout(scrollToBottom, 300);
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
    scrollToBottom();
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
    setTimeout(scrollToBottom, 300);
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


// --- STREAMING & TIMER v24 (Text Based) ---
let currentStreamBubble = null;
let streamStartTime = 0;
let timerInterval = null;

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
window.openVoiceMode = function () {
    console.log("Opening Voice Mode");
    const overlay = document.getElementById('voice-overlay');
    if (overlay) {
        overlay.classList.add('active');
        document.getElementById('voice-text').textContent = "Parla ora...";
        document.getElementById('voice-circle').classList.add('listening');

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
        document.getElementById('voice-circle').classList.remove('listening');

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
        // Show settings panel
        const panel = document.getElementById('panel-settings');
        if (panel) {
            panel.classList.remove('hidden');
            // Start temperature monitoring
            startTemperatureMonitoring();
        }
    } else if (panelName === 'memory') {
        const panel = document.getElementById('panel-memory');
        if (panel) {
            panel.classList.remove('hidden');
        }
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
});

// ---------------------------
window.startStream = function () {
    const template = document.getElementById('tmpl-bot');
    const clone = template.content.cloneNode(true);
    const contentSpan = clone.querySelector('.content');
    contentSpan.textContent = '';

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
    scrollToBottom();

    currentStreamBubble = {
        content: contentSpan,
        reasoning: reasoningContent,
        reasoningContainer: reasoningContainer,
        timer: timerDiv
    };

    streamStartTime = Date.now();

    // Real-time Update
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(() => {
        if (streamStartTime > 0) {
            const duration = (Date.now() - streamStartTime) / 1000;
            const textSpan = currentStreamBubble.timer.querySelector('.timer-text');
            if (textSpan) textSpan.textContent = duration.toFixed(1) + "s";
        }
    }, 100);
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

    } else {
        currentStreamBubble.content.textContent += text;
    }
    scrollToBottom();
};

window.endStream = function () {
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = null;

    if (currentStreamBubble && streamStartTime > 0) {
        const duration = (Date.now() - streamStartTime) / 1000;
        const textSpan = currentStreamBubble.timer.querySelector('.timer-text');
        if (textSpan) textSpan.textContent = duration.toFixed(2) + "s";
    }
    currentStreamBubble = null;
    streamStartTime = 0;
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
window.updateStatus = function (key, active) {
    if (key === 'dreaming') {
        const indicator = document.getElementById('dream-indicator');
        if (indicator) {
            if (active) {
                indicator.classList.remove('hidden');
                indicator.classList.add('active');
                console.log("Dream Mode: ACTIVE 🌙");
            } else {
                indicator.classList.remove('active');
                // Optional: keep it visible but dim, or hide completely
                // Let's hide it after transition
                setTimeout(() => {
                    if (!indicator.classList.contains('active')) {
                        indicator.classList.add('hidden');
                    }
                }, 500); // match transition
                console.log("Dream Mode: INACTIVE");
            }
        }
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

        // 2. Soul
        if (stats.soul) {
            const statusEl = document.getElementById('soul-status-text');
            if (statusEl) statusEl.textContent = `Stato: ${stats.soul.state_label || 'Active'}`;

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
