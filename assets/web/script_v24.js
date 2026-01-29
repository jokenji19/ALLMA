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

// Expose
window.openPanel = function (panelName) {
    console.log("Opening panel: " + panelName);
    toggleSidebar();
    if (panelName === 'voice') {
        openVoiceMode();
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

// Initialize on Load
document.addEventListener("DOMContentLoaded", () => {
    try {
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
