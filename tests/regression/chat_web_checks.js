// Browser fixture: exercise production functions against the actual DOM.
async function runChatChecks() {
    const result = document.getElementById('test-results');
    const checks = [];
    function check(ok, name) {
        if (!ok) throw new Error(name);
        checks.push(name);
        result.textContent = checks.map(x => 'PASS: ' + x).join('\n');
    }
    try {
        window.newChatReady();
        check(!!chatContainer.querySelector('.empty-chat'), 'Schermata iniziale ripristinata');
        window.msgQueue.length = 0;
        messageInput.value = 'Messaggio di prova';
        sendMessage();
        messageInput.value = 'Doppio invio';
        sendMessage();
        check(window.msgQueue.length === 1 && messageInput.disabled, 'Doppio invio bloccato');
        check(!chatContainer.querySelector('.empty-chat'), 'Schermata iniziale rimossa al primo messaggio');
        check(document.getElementById('send-btn').hidden, 'Invio sostituito da Interrompi durante elaborazione');
        window.startStream(101);
        window.streamChunk('Dettagli di prova', true, 101);
        const details = chatContainer.querySelector('.reasoning-container');
        const header = details.querySelector('.reasoning-header');
        check(!details.classList.contains('open') && header.getAttribute('aria-expanded') === 'false', 'Dettagli chiusi durante lo streaming');
        toggleReasoning(header);
        check(details.classList.contains('open') && header.getAttribute('aria-expanded') === 'true', 'Dettagli apribili da pulsante accessibile');
        toggleReasoning(header);
        window.streamChunk('Bozza provvisoria lunga', false, 101);
        window.endStream('**Risposta finale**', 101);
        check(chatContainer.textContent.includes('Risposta finale') && !chatContainer.textContent.includes('Bozza'), 'Testo finale autorevole');
        check(messageInput.disabled, 'Invio attende il rilascio del backend');
        window.turnFinished(101);
        check(!messageInput.disabled, 'Invio riabilitato dopo fine turno');
        window.streamChunk('TOKEN OBSOLETO', false, 101);
        check(!chatContainer.textContent.includes('TOKEN OBSOLETO'), 'Token tardivi ignorati');
        messageInput.value = 'Seconda richiesta';
        sendMessage();
        window.startStream(102);
        window.streamChunk('Risposta da annullare', false, 102);
        startNewChat();
        check(!document.getElementById('sidebar').classList.contains('active'), 'Nuova chat dalla testata non apre il menu');
        check(newChatPending && messageInput.disabled && chatContainer.textContent.includes('Messaggio di prova'), 'Nuova chat attende conferma');
        window.endStream('Risposta interrotta.', 102);
        window.turnFinished(102);
        check(messageInput.disabled, 'Nessun invio tra annullamento e nuova chat');
        window.newChatReady();
        window.streamChunk('VECCHIA CHAT', false, 102);
        await new Promise(resolve => setTimeout(resolve, 70));
        check(!chatContainer.textContent.includes('VECCHIA CHAT') && chatContainer.querySelectorAll('.message-wrapper').length === 0, 'Nuova chat pulita senza code residue');
        const target = document.createElement('div');
        renderSafeMarkdown(target, '<img src=x onerror="alert(1)"><script>alert(1)</script>[bad](javascript:alert(1)) **testo**');
        check(!target.querySelector('img,script,[onerror],a[href^="javascript:"]') && target.querySelector('strong'), 'Markdown privo di tag e link eseguibili');
        messageInput.value = 'Verifica interruzione';
        sendMessage();
        window.startStream(103);
        window.cancelGeneration();
        check(JSON.parse(window.msgQueue.at(-1)).action === 'cancel_generation', 'Pulsante Interrompi invia il comando');
        window.endStream('Risposta interrotta.', 103);
        window.turnFinished(103);
        result.textContent += '\nTUTTI I CONTROLLI PASSATI';
    } catch (error) {
        result.textContent += '\nFAIL: ' + error.message;
        throw error;
    }
}
