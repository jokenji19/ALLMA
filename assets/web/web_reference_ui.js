/* This preference is owned by the local core, never by browser storage. */
(() => {
    'use strict';
    const globe = document.getElementById('composer-internet');
    const toggle = document.getElementById('web-access-toggle');
    const expandedToggle = document.getElementById('web-expanded-toggle');
    const status = document.getElementById('web-access-status');
    const errorNote = document.getElementById('composer-internet-error');
    let enabled = null, expanded = false, pending = null, request = 0, awaitingWrite = false;

    function render(error = '') {
        const active = enabled === true;
        const state = active ? 'Internet attivo' : 'Internet disattivato';
        const waiting = pending !== null;
        if (toggle) {
            toggle.checked = active;
            toggle.disabled = waiting || enabled === null;
        }
        if (expandedToggle) {
            expandedToggle.checked = expanded;
            expandedToggle.disabled = waiting || enabled === null;
        }
        if (globe) {
            globe.disabled = waiting;
            globe.setAttribute('aria-pressed', String(active));
            globe.setAttribute('aria-busy', String(waiting));
            globe.title = waiting ? 'Controllo la preferenza Internet…' : enabled === null
                ? 'Controlla lo stato di Internet' : `${state}. Tocca per ${active ? 'disattivarlo' : 'attivarlo'}.`;
        }
        if (status) status.textContent = error || (waiting ? 'Controllo la preferenza…' : active
            ? 'Ricerche consentite. ALLMA può consultare fonti pubbliche e meteo.'
            : 'Modalità locale. Le ricerche online sono disattivate.');
        if (errorNote) errorNote.textContent = error;
        if (typeof updateComposer === 'function') updateComposer();
    }

    function update(data,id=null) {
        if (id !== request || pending === null) return;
        clearTimeout(pending.timer);
        pending = null;
        enabled = typeof data?.enabled === 'boolean' ? data.enabled : null;
        if (enabled !== null) {
            expanded = data.expanded === true;
            awaitingWrite = false;
        }
        render(data?.error);
    }

    function send(action,value) {
        if (pending !== null) return;
        const id = ++request;
        if (action === 'set_web_access' || action === 'set_expanded_search') awaitingWrite = true;
        const timer = setTimeout(() => update({error:'Stato Internet non confermato. Tocca il globo per controllarlo.'}, id), 8000);
        pending = {timer};
        render();
        if (window.pyBridge) window.pyBridge.postMessage(JSON.stringify({type:'action', action, enabled:value, request:id}));
        else update({error:'La preferenza è disponibile nell’app ALLMA.'}, id);
    }

    function attachChoices(wrapper, origin, onSearch, animate = false) {
        if (origin?.kind !== 'research_choices' || !Array.isArray(origin.choices)
                || wrapper.querySelector('.research-choices')) return;
        const group = document.createElement('div');
        group.className = animate ? 'research-choices research-choices-enter' : 'research-choices';
        group.setAttribute('role', 'group');
        const prompt = wrapper.querySelector('.content')?.textContent?.trim();
        if (prompt) group.setAttribute('aria-label', prompt.slice(0, 160));
        for (const item of origin.choices.slice(0, 4)) {
            if (typeof item?.label !== 'string' || !item.label.trim() || item.label.length > 48
                    || typeof item.query !== 'string' || !item.query.trim() || item.query.length > 180) continue;
            const button = document.createElement('button');
            button.className = 'research-choice';
            button.type = 'button';
            button.textContent = item.label;
            button.addEventListener('click', () => {
                if (pending !== null || awaitingWrite) return;
                if (enabled !== true) {
                    window.chatNotice?.(typeof origin.offline === 'string' ? origin.offline.slice(0, 160) : '');
                    return;
                }
                onSearch(item.query);
            });
            group.append(button);
        }
        if (group.childElementCount) wrapper.append(group);
    }

    window.webReferenceUI = {
        update,
        attachChoices,
        refresh: () => send('web_status'),
        configure: value => send('set_web_access', value),
        configureExpanded: value => send('set_expanded_search', value),
        get writePending() { return awaitingWrite; }
    };
    globe?.addEventListener('click', () => {
        if (enabled === null) window.webReferenceUI.refresh();
        else window.webReferenceUI.configure(!enabled);
    });
    if (globe) window.webReferenceUI.refresh();

    let activeRequest=null;
    function paint(searching=false) {
        const node=document.getElementById('network-activity');
        if(!node)return;
        node.dataset.state=searching?'online':'local';
        node.setAttribute('aria-busy',String(searching));
        node.textContent = searching ? 'Ricerca su Internet…' : '';
    }
    window.referenceActivity={
        begin(id){activeRequest=id;paint();},
        receive(data,id){if(id!==activeRequest || !data)return;paint(data.state==='searching');},
        finish(id){if(id!==activeRequest)return;activeRequest=null;paint();}
    };
    window.receiveReferenceActivity=(data,id)=>window.referenceActivity.receive(data,id);
})();
