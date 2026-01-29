// Python Bridge Interface
// Expects 'pyBridge' object to be injected by Android WebView

const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');

function sendMessage() {
    const text = messageInput.value.trim();
    if (text) {
        // Add User Message Locally
        addMessage(text, 'user', null);

        // Clear Input
        messageInput.value = '';
        messageInput.blur(); // Dismiss keyboard if needed

        // Send to Python
        if (window.pyBridge) {
            window.pyBridge.postMessage(text);
        } else {
            console.warn("Python Bridge not found. Running in standalone mode.");
            // Mock Response for Debugging
            setTimeout(() => {
                addMessage("Sto pensando...", 'bot', "Questa è una traccia di ragionamento simulata.\nAnalisi contesto: OK.\nGenerazione risposta: In corso...");
            }, 1000);
        }
    }
}

// Function callable from Python
function addMessage(text, sender, thoughtText) {
    const template = document.getElementById(sender === 'user' ? 'tmpl-user' : 'tmpl-bot');
    const clone = template.content.cloneNode(true);

    // Set Text
    const contentSpan = clone.querySelector('.content');
    contentSpan.textContent = text;

    // Set Thought (Bot Only)
    if (sender === 'bot' && thoughtText) {
        const reasoningContainer = clone.querySelector('.reasoning-container');
        const reasoningContent = clone.querySelector('.reasoning-content');

        if (reasoningContainer && reasoningContent) {
            reasoningContainer.classList.remove('hidden');
            reasoningContent.textContent = thoughtText;
        }
    }

    // Append to Chat
    const wrapper = clone.querySelector('.message-wrapper');
    chatContainer.appendChild(wrapper);

    // Scroll to bottom
    scrollToBottom();
}

function toggleReasoning(header) {
    const container = header.parentElement;
    container.classList.toggle('open');
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Allow Enter key to send
messageInput.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Expose critical functions to global scope for Python to call
window.addMessage = addMessage;

// --- STREAMING SUPPORT ---
let currentStreamBubble = null;
let streamStartTime = 0;
let timerInterval = null;

// FIX: Keyboard Overlap - DUAL STRATEGY
// Strategy 1: VisualViewport (Modern Android)
// FIX: Keyboard Overlap - TRIPLE STRATEGY
// Strategy 1: CSS Viewport Units (handled by meta tag interactive-widget)
// Strategy 2: VisualViewport API to manually lift input
const inputArea = document.getElementById('input-area');

if (window.visualViewport) {
    function handleViewportResize() {
        // Calculate offset (if any) if the browser doesn't resize layout
        const layoutHeight = document.documentElement.clientHeight;
        const visualHeight = window.visualViewport.height;
        const offset = Math.max(0, layoutHeight - visualHeight);

        // If offset is significant (keyboard open?), lift the input
        // Note: With 'interactive-widget=resizes-content', usually layout shrinks, so offset is 0.
        // But if that fails, this manual lift helps.

        // However, if we are NOT using adjustResize in Android manifest (we are), this calculation differs.
        // Let's rely on scrolling to bottom primarily, but also check for bottom spacing.

        // Force scroll to keep input in view? No, fixed elements stay.
        // If fixed element is covered, it means layout didn't shrink.

        // Fallback: Set bottom offset if visual viewport is smaller than window
        if (offset > 0) {
            inputArea.style.bottom = `${offset}px`;
        } else {
            inputArea.style.bottom = '0';
        }

        setTimeout(scrollToBottom, 100);
    }
    window.visualViewport.addEventListener('resize', handleViewportResize);
    window.visualViewport.addEventListener('scroll', handleViewportResize);
}

// Strategy 3: Focus listener
messageInput.addEventListener('focus', () => {
    setTimeout(scrollToBottom, 300);
});

window.startStream = function () {
    // Create an empty bot message
    const template = document.getElementById('tmpl-bot');
    const clone = template.content.cloneNode(true);

    // Clear placeholders
    const contentSpan = clone.querySelector('.content');
    contentSpan.textContent = '';

    // Thought container starts hidden
    const reasoningContainer = clone.querySelector('.reasoning-container');
    const reasoningContent = clone.querySelector('.reasoning-content');
    reasoningContent.textContent = '';

    // Create Timer Element
    const timerDiv = document.createElement('div');
    timerDiv.className = 'generation-timer';

    // INLINE SVG ICON (No Network Dependency)
    // Sparkles icon replacement
    const sparkleSvg = `<svg xmlns="http://www.w3.org/2000/svg" class="generation-spinner" width="14" height="14" viewBox="0 0 512 512" style="fill:none; stroke:currentColor; stroke-width:32; stroke-linecap:round; stroke-linejoin:round;"><path d="M256 48C256 48 304 160 416 192C304 224 256 336 256 336C256 336 208 224 96 192C208 160 256 48 256 48Z" /></svg>`;

    // Force styles inline to bypass CSS opacity issues
    timerDiv.style.opacity = "1";
    timerDiv.style.display = "flex";

    timerDiv.innerHTML = `${sparkleSvg} <span class="timer-text" style="margin-left:4px;">0.0s</span>`;
    timerDiv.classList.add('visible');

    // Append to wrapper
    const wrapper = clone.querySelector('.message-wrapper');
    wrapper.appendChild(timerDiv);

    chatContainer.appendChild(wrapper);
    scrollToBottom();

    // Track current bubble
    currentStreamBubble = {
        content: contentSpan,
        reasoning: reasoningContent,
        reasoningContainer: reasoningContainer,
        timer: timerDiv
    };

    streamStartTime = Date.now();

    // START REAL-TIME TIMER
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(() => {
        if (streamStartTime > 0) {
            const duration = (Date.now() - streamStartTime) / 1000;
            const textSpan = currentStreamBubble.timer.querySelector('.timer-text');
            if (textSpan) {
                textSpan.textContent = duration.toFixed(1) + "s";
            }
        }
    }, 100);
};

window.streamChunk = function (text, isThought) {
    if (!currentStreamBubble) {
        window.startStream();
    }

    if (isThought) {
        // Ensure container is visible
        if (currentStreamBubble.reasoningContainer.classList.contains('hidden')) {
            currentStreamBubble.reasoningContainer.classList.remove('hidden');
        }
        // Append text
        currentStreamBubble.reasoning.textContent += text;
    } else {
        // Append content
        currentStreamBubble.content.textContent += text;
    }
    scrollToBottom();
};

window.endStream = function () {
    // Stop Real-time Timer
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = null;

    if (currentStreamBubble && streamStartTime > 0) {
        const duration = (Date.now() - streamStartTime) / 1000;
        // Final update
        const textSpan = currentStreamBubble.timer.querySelector('.timer-text');
        if (textSpan) {
            textSpan.textContent = duration.toFixed(2) + "s";
        } else {
            // Fallback if structure changed
            currentStreamBubble.timer.textContent = duration.toFixed(2) + "s";
        }
        currentStreamBubble.timer.classList.add('visible');
    }
    currentStreamBubble = null;
    streamStartTime = 0;
};
