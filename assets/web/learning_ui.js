/* Learning and saved sources. Source text is rendered as text, never HTML. */
(() => {
    'use strict';
    let request = null;
    let nextRequest = 0;
    let pageRequest = 0;
    let pageOffset = 0;
    const pageSize = 10;
    const pending = new Map();
    const identifierPattern = /^[0-9a-f]{32}$/;

    function send(action, fields, done) {
        const id = ++nextRequest;
        const timer = setTimeout(() => {
            if (pending.delete(id)) done({ok:false});
        }, action === 'response_feedback' ? 25000 : 10000);
        pending.set(id, {action, done, timer});
        try {
            window.pyBridge.postMessage(JSON.stringify({type:'action', action, request:id, ...fields}));
        } catch (_) {
            clearTimeout(timer);
            pending.delete(id);
            done({ok:false});
        }
    }

    window.receiveSavedReferences = result => {
        const entry = pending.get(result?.request);
        if (!entry || entry.action !== result.action) return;
        clearTimeout(entry.timer);
        pending.delete(result.request);
        entry.done(result);
    };

    function updateBookmark(button, saved) {
        button.setAttribute('aria-pressed', String(saved));
        const label = saved ? 'Rimuovi dalle informazioni salvate' : 'Ricorda questa informazione con le fonti';
        button.title = label;
        button.setAttribute('aria-label', label);
    }

    function attachSaveButton(wrapper, row) {
        const id = wrapper.referenceSaveId;
        if (!row || !identifierPattern.test(id) || row.querySelector('.message-bookmark')) return;
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'message-bookmark';
        button.dataset.referenceId = id;
        button.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" aria-hidden="true"><path d="M7 4h10a1 1 0 0 1 1 1v15l-6-4-6 4V5a1 1 0 0 1 1-1Z"/></svg>';
        updateBookmark(button, false);
        const feedback = document.createElement('span');
        feedback.className = 'bookmark-status';
        feedback.setAttribute('role', 'status');
        let clearFeedback = null;
        button.addEventListener('click', () => {
            if (button.disabled) return;
            const saved = button.getAttribute('aria-pressed') !== 'true';
            clearTimeout(clearFeedback);
            feedback.textContent = '';
            button.disabled = true;
            send('save_reference', {id, saved}, result => {
                button.disabled = false;
                if (result.ok && result.id === id && result.saved === saved) {
                    updateBookmark(button, saved);
                    feedback.textContent = saved ? 'Salvato' : 'Rimosso';
                } else {
                    feedback.textContent = result.error || 'Modifica non completata. Riprova.';
                }
                clearFeedback = setTimeout(() => { feedback.textContent = ''; }, 5000);
            });
        });
        row.append(button, feedback);
    }

    function attachResponseFeedback(wrapper, row) {
        const id = wrapper.responseFeedbackId;
        if (!row || !identifierPattern.test(id) || row.querySelector('.message-thumb')) return;
        const makeButton = (label, down = false) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'message-bookmark message-thumb';
            button.title = label;
            button.setAttribute('aria-label', label);
            button.setAttribute('aria-pressed', 'false');
            const path = '<path d="M7 10v11H3V10h4Zm0 0 5-7a2 2 0 0 1 2 2l-1 5h6a2 2 0 0 1 2 2l-1.5 7a2 2 0 0 1-2 2H7"/>';
            button.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" aria-hidden="true">'
                + (down ? '<g transform="rotate(180 12 12)">' + path + '</g>' : path) + '</svg>';
            return button;
        };
        const up = makeButton('Salva e impara');
        const down = makeButton('Controlla la risposta', true);
        const status = document.createElement('span');
        status.className = 'bookmark-status';
        status.setAttribute('role', 'status');
        const panel = document.createElement('div');
        panel.className = 'message-feedback-panel';
        panel.hidden = true;
        const review = document.createElement('div');
        const form = document.createElement('form');
        form.hidden = true;
        const label = document.createElement('label');
        label.textContent = 'Cosa va corretto?';
        const field = document.createElement('textarea');
        field.rows = 2;
        field.maxLength = 1000;
        field.required = true;
        label.append(field);
        const save = document.createElement('button');
        save.type = 'submit';
        save.className = 'learning-refresh';
        save.textContent = 'Salva correzione';
        form.append(label, save);
        panel.append(review, form);
        wrapper.append(panel);
        row.append(up, down, status);
        let state = {};
        let busy = false;

        function render() {
            const disputed = state.vote === 'down';
            up.setAttribute('aria-pressed', String(state.vote === 'up' || state.status === 'review_approved'));
            down.setAttribute('aria-pressed', String(disputed && state.status !== 'review_approved'));
            const upLabel = disputed ? 'Salva l’esito della verifica' : 'Salva e impara';
            const downLabel = disputed ? 'Indica una correzione' : 'Controlla la risposta';
            up.setAttribute('aria-label', upLabel);
            down.setAttribute('aria-label', downLabel);
            up.title = upLabel;
            down.title = downLabel;
            up.disabled = busy || (disputed && (!state.check?.text || state.status === 'review_disputed'));
            down.disabled = busy;
            field.disabled = busy;
            save.disabled = busy;
            const bookmark = row.querySelector('.message-bookmark:not(.message-thumb)');
            if (bookmark && disputed) {
                updateBookmark(bookmark, false);
                bookmark.hidden = true;
                bookmark.disabled = true;
            } else if (bookmark && state.saved) {
                updateBookmark(bookmark, true);
            }
        }

        function showReview(check) {
            review.replaceChildren();
            if (!check) return;
            const titles = {
                corrected: 'Ho trovato un dato da correggere.',
                supported: 'Il controllo conferma il punto verificato.',
                same_source: 'Ritrovo lo stesso dato nella fonte già citata.',
                identity: 'Ho trovato un passaggio sul soggetto indicato.',
                evidence: 'Ho trovato un passaggio da confrontare.',
                updated: 'Ho recuperato una rilevazione più recente.',
                conflicting: 'Le fonti riportano dati diversi su questo punto.',
                offline: 'Per approfondire serve una fonte online. Puoi anche indicare tu la correzione.',
                unresolved: 'Non riesco a verificare questo punto. Puoi indicare tu cosa correggere.'
            };
            const heading = document.createElement('p');
            heading.textContent = titles[check.status] || titles.unresolved;
            review.append(heading);
            const passages = check.alternatives || (check.text ? [check] : []);
            for (const result of passages) {
                const group = document.createElement('section');
                const passage = document.createElement('div');
                passage.className = 'content';
                if (typeof renderSafeMarkdown === 'function') renderSafeMarkdown(passage, result.text);
                else passage.textContent = result.text;
                group.append(passage);
                attachOrigin(group, result.origin);
                review.append(group);
            }
            panel.hidden = false;
        }

        function submit(vote, note) {
            if (busy) return;
            busy = true;
            render();
            status.textContent = vote === 'down' && state.vote !== 'down' ? 'Verifico…' : 'Registro…';
            send('response_feedback', {id, vote, note}, reply => {
                busy = false;
                if (!reply.ok || reply.id !== id || !reply.feedback) {
                    status.textContent = reply.error || 'Operazione non completata. Riprova.';
                    render();
                    return;
                }
                state = reply.feedback;
                render();
                showReview(state.check);
                if (vote === 'correction') {
                    form.hidden = true;
                    panel.hidden = true;
                    status.textContent = 'Correzione registrata';
                } else if (vote === 'up' || vote === 'review_up') {
                    form.hidden = true;
                    status.textContent = state.saved ? 'Salvato con la fonte' : 'Riscontro registrato';
                } else {
                    status.textContent = '';
                    if (!state.check || state.status === 'review_disputed') {
                        panel.hidden = false;
                        form.hidden = false;
                        field.value = state.note || '';
                        field.focus();
                    }
                }
            });
        }

        up.addEventListener('click', () => submit(state.vote === 'down' ? 'review_up' : 'up'));
        down.addEventListener('click', () => {
            if (state.vote === 'down' && state.status !== 'review_approved') {
                panel.hidden = false;
                form.hidden = false;
                field.value = state.note || '';
                field.focus();
            } else {
                submit(state.status === 'review_approved' ? 'review_down' : 'down');
            }
        });
        form.addEventListener('submit', event => {
            event.preventDefault();
            if (field.value.trim()) submit('correction', field.value.trim());
        });
    }

    function showSavedReferences(offset = 0) {
        const root = document.getElementById('saved-references-content');
        const status = document.getElementById('saved-references-status');
        if (!root || !status) return;
        const revision = ++pageRequest;
        status.textContent = 'Caricamento…';
        send('list_saved_references', {offset}, result => {
            if (revision !== pageRequest) return;
            root.replaceChildren();
            if (!result.ok || result.offset !== offset || !Array.isArray(result.items)) {
                status.textContent = result.error || 'Non riesco a leggere le fonti salvate. Riprova.';
                return;
            }
            if (offset && !result.items.length) {
                showSavedReferences(Math.max(0, offset - pageSize));
                return;
            }
            pageOffset = offset;
            status.textContent = result.items.length ? '' : 'Usa il segnalibro accanto a una risposta con fonti per ritrovarla qui.';
            for (const item of result.items) {
                if (!identifierPattern.test(item.id)) continue;
                const card = document.createElement('article');
                card.className = 'learning-item saved-reference-item';
                const details = document.createElement('details');
                const title = document.createElement('summary');
                title.textContent = item.title;
                const text = document.createElement('div');
                text.className = 'saved-reference-text';
                if (typeof renderSafeMarkdown === 'function') renderSafeMarkdown(text, item.answer);
                else text.textContent = item.answer;
                details.append(title, text);
                const date = document.createElement('p');
                date.className = 'section-desc';
                date.textContent = 'Salvata il ' + new Date(item.saved_at * 1000).toLocaleDateString('it-IT');
                details.append(date);
                attachOrigin(details, item.origin);
                const remove = document.createElement('button');
                remove.type = 'button';
                remove.className = 'learning-refresh';
                remove.textContent = 'Rimuovi';
                remove.setAttribute('aria-label', 'Rimuovi ' + item.title);
                remove.addEventListener('click', () => {
                    if (remove.disabled) return;
                    remove.disabled = true;
                    send('save_reference', {id:item.id, saved:false}, reply => {
                        remove.disabled = false;
                        if (reply.ok && reply.id === item.id && reply.saved === false) {
                            const bookmark = document.querySelector(`.message-bookmark[data-reference-id="${item.id}"]`);
                            if (bookmark) updateBookmark(bookmark, false);
                            showSavedReferences(pageOffset);
                        } else {
                            status.textContent = reply.error || 'Rimozione non completata. Riprova.';
                        }
                    });
                });
                details.append(remove);
                card.append(details);
                root.append(card);
            }
            const navigation = document.createElement('div');
            navigation.className = 'saved-reference-navigation';
            for (const [enabled, label, target] of [[offset > 0, 'Precedenti', offset - pageSize],
                [result.has_more, 'Successive', offset + pageSize]]) {
                if (!enabled) continue;
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'learning-refresh';
                button.textContent = label;
                button.addEventListener('click', () => showSavedReferences(target));
                navigation.append(button);
            }
            if (navigation.children.length) root.append(navigation);
        });
    }

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
        showSavedReferences();
        if (request) return;
        const root = document.getElementById('learning-content');
        if (root) root.textContent = 'Leggo le esperienze conservate…';
        request = setTimeout(() => render(null), 10000);
        if (window.pyBridge) window.pyBridge.postMessage('__REQUEST_LEARNING_UPDATE__');
        else render(null);
    }
    function external(anchor) {
        anchor.target = '_blank';
        anchor.rel = 'noopener noreferrer';
        anchor.addEventListener('click', event => {
            if (window.pyBridge) {
                event.preventDefault();
                window.pyBridge.postMessage(JSON.stringify({type: 'action', action: 'open_reference', url: anchor.href}));
            }
        });
    }
    function citationLink(citation) {
        if (!citation || typeof citation.title !== 'string') return null;
        let url;
        try {
            if (typeof citation.url !== 'string' || citation.url.length > 2048 || /[\x00-\x20\x7f\\]/.test(citation.url)) return null;
            const rawPath = citation.url.match(/^https:\/\/[^/?#]+(\/[^?#]*)/i)?.[1];
            if (!rawPath) return null;
            const decoded = decodeURIComponent(rawPath);
            if (/[\x00-\x1f\x7f\\]|%[\da-f]{2}/i.test(decoded) || decoded.split('/').some(part => part === '.' || part === '..')) return null;
            url = new URL(citation.url);
        } catch (_) { return null; }
        if (url.protocol !== 'https:' || url.username || url.password || url.port || url.search || url.hash) return null;
        const wiki = /^(?:it|en|es|fr|de|pt|ru|ar|zh|ja)\.wikipedia\.org$/.test(url.hostname)
            && url.pathname.startsWith('/wiki/') && Number.isSafeInteger(citation.revision) && citation.revision > 0;
        const nasa = citation.provider === 'nasa' && citation.revision === 0 && url.hostname === 'science.nasa.gov'
            && ['/mission/europa-clipper/why-europa-europa-up-close/', '/saturn/moons/enceladus/',
                '/earth/explore/earth-indicators/sea-leve/'].includes(url.pathname);
        const esa = citation.provider === 'esa' && citation.revision === 0 && url.hostname === 'www.esa.int'
            && ['/articles/about-us/directorates/science/juice/juice-factsheet',
                '/articles/about-us/meet-us/sites-and-establishments/esa-esac/sampling-the-ocean-on-enceladus'].includes(url.pathname);
        const noaa = citation.provider === 'noaa' && citation.revision === 0 && url.hostname === 'www.climate.gov'
            && url.pathname === '/news-features/understanding-climate/climate-change-global-sea-level';
        if (!wiki && !nasa && !esa && !noaa) return null;
        if (wiki) url.searchParams.set('oldid', String(citation.revision));
        const provider = nasa ? 'NASA Science' : esa ? 'ESA' : noaa ? 'NOAA' : 'Wikipedia';
        const link = document.createElement('a');
        link.href = url.href;
        const title = citation.title === 'Global sea level' ? 'Livello globale del mare' : citation.title;
        link.textContent = (esa && title === 'Europa' ? 'Scheda della missione Juice' : title) + ' · ' + provider;
        external(link);
        return {link, provider, wiki, nasa};
    }
    function attachOrigin(wrapper, origin) {
        if (!wrapper || !origin || typeof origin.label !== 'string' || typeof origin.detail !== 'string') return;
        wrapper.referenceSaveId = origin.save_id;
        wrapper.responseFeedbackId = origin.feedback_id;
        wrapper.querySelector('.message-origin')?.remove();
        wrapper.querySelector('.message-reference-badge')?.remove();
        const details = document.createElement('details'); details.className = 'message-origin';
        const summary = document.createElement('summary'), text = document.createElement('p');
        summary.textContent = 'Origine'; summary.setAttribute('aria-label', 'Origine: ' + origin.label);
        text.textContent = origin.label + '. ' + origin.detail;
        details.append(summary, text);
        if (origin.kind === 'weather' || origin.kind === 'web_search') {
            const badge=document.createElement('span');badge.className='message-reference-badge';
            badge.textContent=origin.label;wrapper.append(badge);
            const sources = origin.kind==='weather' ? [origin.citation] : origin.sources;
            for (const [index, row] of (Array.isArray(sources)?sources.slice(0,3):[]).entries()) {
                if (!row || typeof row.title !== 'string' || typeof row.url !== 'string') continue;
                let url;
                try { url = new URL(row.url); } catch (_) { continue; }
                if (url.protocol!=='https:' || url.username || url.password || url.port || url.hash
                    || (origin.kind==='weather' && url.href!=='https://open-meteo.com/')) continue;
                const source=document.createElement('p'), link=document.createElement('a');
                link.href=url.href;
                link.textContent=(origin.kind==='web_search'?'['+(index+1)+'] ':'')+row.title;
                external(link);source.append(link);
                if (origin.kind==='web_search') {
                    const body = wrapper.querySelector('.content') || wrapper.querySelector('.saved-reference-text');
                    const marker = '['+(index+1)+']';
                    const paragraph = body && Array.from(body.children).find(node =>
                        node.tagName==='P' && node.lastChild?.nodeType===3 && node.lastChild.textContent.endsWith(marker));
                    if (paragraph) {
                        const inline = link.cloneNode(false);
                        inline.textContent = marker;
                        inline.className = 'inline-source';
                        inline.setAttribute('aria-label', 'Fonte '+(index+1)+' · '+row.title);
                        paragraph.lastChild.textContent = paragraph.lastChild.textContent.slice(0,-marker.length);
                        paragraph.append(inline);
                        external(inline);
                    }
                }
                if (row.data_label || row.date) {
                    const date=document.createElement('span');
                    date.textContent=' · '+String(row.data_label || row.date);
                    source.append(date);
                }
                details.append(source);
            }
        } else if (origin.kind === 'reference_comparison' && Array.isArray(origin.sources)) {
            const badge = document.createElement('span'); badge.className = 'message-reference-badge';
            badge.textContent = {agreement: 'Fonti concordi', disagreement: 'Fonti divergenti', insufficient: 'Confronto incompleto',
                parallel_reading: 'Voci collegate di Wikipedia'}[origin.outcome] || 'Confronto tra fonti';
            wrapper.append(badge);
            for (const row of origin.sources.slice(0, 2)) {
                const source = citationLink(row?.citation);
                if (!source) continue;
                const heading = document.createElement('p');
                heading.append(source.link);
                const provenance = document.createElement('span');
                const consulted = Number.isFinite(row.citation.fetched_at) && row.citation.fetched_at > 0
                    ? ' il ' + new Date(row.citation.fetched_at * 1000).toLocaleDateString('it-IT') : '';
                provenance.textContent = (row.via === 'cached' ? ' · copia locale' : ' · consultata online') + consulted;
                heading.append(provenance);
                details.append(heading);
                if (typeof row.excerpt === 'string') {
                    const excerpt = document.createElement('blockquote');
                    excerpt.lang = 'en';
                    excerpt.textContent = row.excerpt.slice(0, 900);
                    details.append(excerpt);
                }
            }
        } else {
            const citation = origin.citation;
            const sourceLink = citationLink(citation);
            if (sourceLink) {
                const {provider, nasa, link} = sourceLink;
                const badge=document.createElement('span');badge.className='message-reference-badge';
                const scope = {history:' · già consultata', cache:' · copia locale'};
                badge.textContent=provider+(origin.saved_reference?' · salvata':scope[origin.via] || ' · fonte online');
                if(origin.coverage==='one_subject') badge.textContent+=' · confronto parziale';
                wrapper.append(badge);
                const source=document.createElement('p');
                source.append(link);details.append(source);
                if(Number.isFinite(citation.fetched_at) && citation.fetched_at>0) {
                    const consulted=document.createElement('p');
                    consulted.textContent='Consultata il '+new Date(citation.fetched_at*1000).toLocaleDateString('it-IT');
                    details.append(consulted);
                }
                const license=document.createElement('p'),licenseLink=document.createElement('a');
                licenseLink.href=nasa?'https://www.nasa.gov/nasa-brand-center/images-and-media/':'https://creativecommons.org/licenses/by-sa/4.0/';
                licenseLink.textContent=nasa?'NASA · condizioni di utilizzo':'CC BY-SA 4.0 · attribuzione agli autori della pagina';
                licenseLink.target='_blank';licenseLink.rel='noopener noreferrer';license.append(licenseLink);details.append(license);
                external(licenseLink);
            }
        }
        wrapper.append(details);
    }
    window.learningUI = {refresh, render, attachOrigin, attachSaveButton, attachResponseFeedback};
    window.learningUIResult = render;
})();
