/* Read-only learning view. All source text is rendered as text, never HTML. */
(() => {
    'use strict';
    let request = null;
    function render(data) {
        if (request) clearTimeout(request);
        request = null;
        const root = document.getElementById('learning-content');
        if (!root) return;
        root.replaceChildren();
        if (!data || data.status !== 'ok' || !Array.isArray(data.sections)) {
            const p = document.createElement('p');
            p.className = 'memory-empty-state';
            p.textContent = data?.status === 'busy'
                ? 'ALLMA sta rispondendo. Aggiorna quando ha terminato.'
                : 'Non riesco a leggere l’apprendimento in questo momento. Puoi riprovare con Aggiorna.';
            root.append(p); return;
        }
        for (const group of data.sections.slice(0, 6)) {
            const section = document.createElement('section');
            section.className = 'learning-section';
            const heading = document.createElement('h2');
            heading.textContent = String(group.title || 'Esperienza');
            section.append(heading);
            const items = Array.isArray(group.items) ? group.items.slice(0,12) : [];
            if (!items.length) {
                const empty = document.createElement('p'); empty.className = 'section-desc';
                empty.textContent = String(group.empty || 'Nessuna esperienza disponibile.'); section.append(empty);
            }
            for (const item of items) {
                const card = document.createElement('article'); card.className = 'learning-item';
                const text = document.createElement('p'), detail = document.createElement('p');
                text.textContent = String(item.text || '');
                detail.textContent = String(item.detail || ''); detail.className = 'section-desc';
                card.append(text, detail); section.append(card);
            }
            root.append(section);
        }
    }
    function refresh() {
        if (request) return;
        const root = document.getElementById('learning-content');
        if (root) root.textContent = 'Leggo le esperienze conservate…';
        request = setTimeout(() => render(null), 10000);
        if (window.pyBridge) window.pyBridge.postMessage('__REQUEST_LEARNING_UPDATE__');
        else render(null);
    }
    function attachOrigin(wrapper, origin) {
        if (!wrapper || !origin || typeof origin.label !== 'string' || typeof origin.detail !== 'string') return;
        wrapper.querySelector('.message-origin')?.remove();
        wrapper.querySelector('.message-reference-badge')?.remove();
        const details = document.createElement('details'); details.className = 'message-origin';
        const summary = document.createElement('summary'), text = document.createElement('p');
        summary.textContent = 'Origine'; summary.setAttribute('aria-label', 'Origine: ' + origin.label);
        text.textContent = origin.label + '. ' + origin.detail;
        details.append(summary, text);
        const citation=origin.citation;
        if(citation && typeof citation.title==='string' && Number.isSafeInteger(citation.revision) && citation.revision>0) {
            let url;
            try {url=new URL(citation.url);} catch(_) {}
            if(url && url.protocol==='https:' && ['it.wikipedia.org','en.wikipedia.org'].includes(url.hostname)
                    && !url.username && !url.password && !url.port && !url.search && !url.hash && url.pathname.startsWith('/wiki/')) {
                const badge=document.createElement('span');badge.className='message-reference-badge';
                badge.textContent=origin.via==='cache'?'Wikipedia · copia locale':'Wikipedia · fonte online';
                wrapper.append(badge);
                const source=document.createElement('p'),link=document.createElement('a');
                // Open the revision actually read, rather than silently linking
                // a possibly changed current page.
                url.searchParams.set('oldid',String(citation.revision));
                link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';
                const external=anchor=>anchor.addEventListener('click',event=> {
                    if(window.pyBridge) {
                        event.preventDefault();
                        window.pyBridge.postMessage(JSON.stringify({type:'action',action:'open_reference',url:anchor.href}));
                    }
                });
                external(link);
                link.textContent=citation.title+' · Wikipedia';
                source.append(link);details.append(source);
                const license=document.createElement('p'),licenseLink=document.createElement('a');
                licenseLink.href='https://creativecommons.org/licenses/by-sa/4.0/';
                licenseLink.textContent='CC BY-SA 4.0 · attribuzione agli autori della pagina';
                licenseLink.target='_blank';licenseLink.rel='noopener noreferrer';license.append(licenseLink);details.append(license);
                external(licenseLink);
            }
        }
        wrapper.append(details);
    }
    window.learningUI = {refresh, render, attachOrigin};
    window.learningUIResult = render;
})();
