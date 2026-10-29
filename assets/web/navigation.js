/* One page is visible at a time. Controls stay mounted, preserving chat/drafts. */
(() => {
    'use strict';
    const pages = {
        chat: 'view-chat', settings: 'panel-settings', memory: 'panel-memory', dream: 'panel-dream',
        learning: 'panel-learning', profile: 'user-modal', voice: 'voice-overlay', diagnostics: 'view-diagnostics'
    };
    const titles = {chat:'Chat',settings:'Impostazioni',memory:'Memoria',dream:'Diario dei sogni',
        learning:'Cosa imparo', profile:'Il tuo profilo',voice:'Voce',diagnostics:'Diagnostica',
        'settings/model':'Modello di ALLMA','settings/chat':'Aspetto e chat',
        'settings/notifications':'Notifiche','settings/internet':'Internet e fonti','settings/dreams':'Sogni e iniziativa','settings/data':'Dati e backup'};
    let stack = [{route:'chat',scroll:0}], cursor = 0, current = 'chat', waitingBack = false;
    const session = 'allma-pages-' + Date.now() + '-' + Math.random().toString(36).slice(2);
    let browserHistory = true;
    const pageName = route => route.startsWith('settings/') ? 'settings' : route;
    const elementFor = route => document.getElementById(pages[pageName(route)]);
    const contentFor = route => elementFor(route)?.querySelector('.screen-content');

    function rememberScroll() {
        const content=contentFor(current);
        stack[cursor].scroll=content ? content.scrollTop : 0;
    }
    function closeDrawer() {
        if(document.getElementById('sidebar')?.classList.contains('active')) toggleSidebar();
    }
    function stopPolling() {
        stopDiagnostics(); stopTemperatureMonitoring();
        if(window._diagPending) { clearTimeout(window._diagPending);window._diagPending=null; }
    }
    function syncPolling() {
        stopPolling();
        if(!document.hidden && current==='diagnostics') {
            startDiagnostics(); startTemperatureMonitoring();
        }
    }
    function send(value) { if(window.pyBridge) window.pyBridge.postMessage(value); }
    function enter(route,previous) {
        if(route==='voice' && previous!=='voice') window.enterVoiceScreen();
        if(route==='profile' && previous!=='profile') window.prepareProfileFields();
        if(route==='memory') send('__REQUEST_MEMORY_UPDATE__');
        if(route==='learning') window.learningUI?.refresh();
        if(route==='dream') send('__REQUEST_DREAM_HISTORY__');
        if(route==='settings/model') { window.modelUI?.refresh();window.deciderUI?.refresh(); }
        if(route==='settings/data') window.backupUI?.refresh();
        if(route==='settings/notifications') window.notificationUI?.refresh();
        if(route==='settings/internet') window.webReferenceUI?.refresh();
        if(route==='settings/dreams') window.refreshDreamSettings?.();
    }
    function render(route,{restore=false}={}) {
        const previous=current;
        if(previous==='voice' && route!=='voice') window.leaveVoiceScreen();
        if(previous==='settings/data' && route!==previous) document.getElementById('backup-password').value='';
        current=route;
        console.info('ALLMA_SCREEN '+route);
        closeDrawer();
        const target=elementFor(route);
        const active=document.activeElement;
        if(active && active!==document.body && !target?.contains(active)) active.blur();
        for(const [name,id] of Object.entries(pages)) {
            const node=document.getElementById(id); if(!node)continue;
            const visible=name===pageName(route);
            node.classList.toggle('active',visible);node.classList.toggle('hidden',!visible);
            node.hidden=!visible;
        }
        document.body.classList.toggle('internal-screen',route!=='chat');
        const settings=pageName(route)==='settings';
        document.getElementById('settings-home').hidden=!settings || route!=='settings';
        document.querySelectorAll('[data-settings-page]').forEach(group=> {
            group.hidden=!settings || route!=='settings/'+group.dataset.settingsPage;
        });
        document.getElementById('settings-title').textContent=titles[route] || 'Impostazioni';
        const backLabel=cursor>0 ? titles[stack[cursor-1].route] : 'Chat';
        target?.querySelectorAll('[data-back-label]').forEach(label=>label.textContent=backLabel || 'Indietro');
        document.title=(route==='chat'?'ALLMA':titles[route]+' · ALLMA');
        syncPolling();
        if(previous!==route) enter(route,previous);
        const content=contentFor(route);if(content)content.scrollTop=restore?stack[cursor].scroll:0;
        const heading=target?.querySelector('[data-screen-heading]');
        if(heading)heading.focus({preventScroll:true});
        else if(route==='chat') document.getElementById('menu-btn')?.focus({preventScroll:true});
        document.dispatchEvent(new CustomEvent('allma:screen',{detail:{route,previous}}));
    }
    function saveHistory(replace=false) {
        if(!browserHistory)return;
        try {
            history[replace?'replaceState':'pushState']({allmaPage:session,route:current,cursor},'',
                location.pathname+location.search+'#/'+(current==='chat'?'chat':current));
        } catch(_) { browserHistory=false; }
    }
    function go(route,options={}) {
        if(!Object.prototype.hasOwnProperty.call(titles,route))return false;
        if(waitingBack)return false;
        closeDrawer();
        if(route===current && !options.reset)return true;
        rememberScroll();
        if(options.reset) { stack=[{route,scroll:0}];cursor=0; }
        else { stack=stack.slice(0,cursor+1);stack.push({route,scroll:0});cursor++; }
        render(route);saveHistory(!!options.reset);return true;
    }
    function back() {
        const brain=document.getElementById('brain-explorer');
        if(brain && !brain.hidden) { window.brainView?.back();return true; }
        if(document.getElementById('sidebar')?.classList.contains('active')) { closeDrawer();return true; }
        if(waitingBack)return true;
        if(cursor===0)return false;
        rememberScroll();
        if(browserHistory && history.state?.allmaPage===session && history.state.cursor===cursor) {
            waitingBack=true;history.back();
        } else { cursor--;render(stack[cursor].route,{restore:true}); }
        return true;
    }
    window.addEventListener('popstate',event=> {
        waitingBack=false;
        const state=event.state;
        if(state?.allmaPage!==session || !Object.prototype.hasOwnProperty.call(titles,state.route))return;
        rememberScroll();
        if(!Number.isInteger(state.cursor) || state.cursor<0)return;
        // Old forward entries after a new-chat reset must not resurrect a page.
        if(state.cursor>=stack.length || stack[state.cursor].route!==state.route) {
            saveHistory(true);return;
        }
        cursor=state.cursor;render(state.route,{restore:true});
    });
    document.addEventListener('keydown',event=> {
        if(event.key==='Escape' && back()) { event.preventDefault();event.stopPropagation(); }
    });
    document.addEventListener('visibilitychange',syncPolling);
    window.appNav={go,back,get current(){return current;},get depth(){return cursor;}};
    window.handleAndroidBack=()=> {
        if(!back()) send(JSON.stringify({type:'action',action:'navigation_exit'}));
    };
    window.setAppearance=mode=> {
        if(!['light','dark'].includes(mode))return;
        if(document.body.classList.contains('dark-mode')!==(mode==='dark')) toggleTheme();
    };
    saveHistory(true);
})();
