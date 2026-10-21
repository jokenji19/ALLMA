/* Native language inventory and optional offline voices; never contains transcripts. */
window.voiceControls = (() => {
    let latest = {};
    const el = id => document.getElementById(id);
    function send(action, fields = {}) {
        if (window.pyBridge) window.pyBridge.postMessage(JSON.stringify({ type: 'action', action, ...fields }));
    }
    function render(status) {
        latest = status || {};
        const language = el('voice-language'), voice = el('voice-speaker');
        if (!language || !voice) return;
        const options = latest.options || {}, pack = latest.voice_pack || {};
        language.value = options.language || 'it-IT';
        for (const option of voice.options) if (option.value !== 'android') option.disabled = !pack.ready;
        voice.value = options.voice || 'android';
        language.disabled = voice.disabled = !!latest.voice_busy;
        el('voice-preview').disabled = !!latest.voice_busy;
        el('voice-service-fallback').checked = options.allow_service_fallback === true;
        el('voice-service-fallback').disabled = !!latest.voice_busy;
        el('voice-preferences-summary').textContent = `${language.selectedOptions[0]?.textContent.split(' · ')[0] || 'Lingua'} · ${voice.value === 'if_sara' ? 'Sara' : voice.value === 'im_nicola' ? 'Nicola' : 'Android'}`;
        const support = latest.language_support || {};
        const installed = support.installed || [];
        el('voice-language-support').textContent = support.checked
            ? (installed.length ? `Lingue locali installate: ${installed.join(', ')}. L’automatismo dipende dal servizio Android.` : 'Android non ha indicato lingue locali installate. Puoi scegliere la lingua e installarne i dati nelle impostazioni Android.')
            : 'La disponibilità delle lingue viene verificata all’avvio del microfono. Se Android non la comunica, ALLMA segnala eventuali dati mancanti.';
        const button = el('voice-pack-download');
        button.hidden = !!pack.ready;
        button.disabled = !!pack.busy;
        button.textContent = pack.busy ? `Download ${pack.progress || 0}%` : 'Scarica voci naturali · 132 MB';
        el('voice-pack-status').textContent = pack.error || (pack.ready
            ? 'Sara e Nicola pronte · italiano. Nelle altre lingue viene usata la voce Android.'
            : pack.busy ? 'Download e verifica del pacchetto. Puoi continuare a usare la voce Android.'
                : 'Le voci naturali sono opzionali. Servono 700 MB liberi per prepararle; audio e testi restano sul telefono.');
    }
    function save() {
        send('set_voice_options', { language: el('voice-language').value, voice: el('voice-speaker').value,
            allow_service_fallback: el('voice-service-fallback').checked });
    }
    return { render, save, preview: () => send('preview_voice'), download: () => send('download_voice_pack') };
})();
