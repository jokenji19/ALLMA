async function runNavigationChecks() {
    const results=[];
    const check=(value,name)=> { if(!value)throw new Error(name);results.push(name); };
    const tick=()=>new Promise(resolve=>setTimeout(resolve,60));
    const back=async()=> {
        const previous=appNav.current;appNav.back();
        // history.back() finishes on popstate; a fixed 60 ms is not its contract.
        for(let i=0;i<40&&appNav.current===previous;i++)await tick();
    };
    const shown=()=>[...document.querySelectorAll('.app-view')].filter(node=>getComputedStyle(node).display!=='none');
    const visiblePage=(id)=>check(shown().length===1 && shown()[0].id===id,'Una sola schermata visibile: '+id);
    const fullPage=(id)=> {
        const node=document.getElementById(id),rect=node.getBoundingClientRect(),style=getComputedStyle(node);
        check(Math.abs(rect.left)<1 && Math.abs(rect.top)<1 && Math.abs(rect.width-innerWidth)<1 && Math.abs(rect.height-innerHeight)<1,'Pagina intera: '+id);
        check(style.transform==='none' && style.position!=='fixed' && style.borderRadius==='0px','Nessuna geometria da popup: '+id);
    };
    const ids=[...document.querySelectorAll('[id]')].map(node=>node.id);
    check(new Set(ids).size===ids.length,'ID univoci dopo lo spostamento dei controlli');
    check(!document.querySelector('.sidebar-panel,.modal-backdrop'),'Nessun contenitore popup nelle destinazioni della sidebar');
    messageInput.value='Bozza di prova da conservare';
    toggleSidebar();openPanel('settings');await tick();
    visiblePage('panel-settings');fullPage('panel-settings');
    check(!document.getElementById('sidebar').classList.contains('active'),'Sidebar chiusa quando si entra in una pagina');
    check(document.getElementById('sidebar').inert,'Menu chiuso escluso dalla navigazione accessibile');
    check(document.getElementById('settings-home').hidden===false && document.getElementById('model-settings').closest('[hidden]'),'Indice separato dai controlli');
    check(document.querySelectorAll('.settings-link').length===7,'Sette categorie ordinate e accessibili');
    window.msgQueue.length=0;
    appNav.go('settings/model');await tick();
    check(document.getElementById('settings-title').textContent==='Modello di ALLMA','Titolo della sottopagina aggiornato');
    check(window.msgQueue.some(v=>JSON.parse(v).action==='list_models'),'Modelli richiesti entrando nella pagina corretta');
    const before=window.msgQueue.length;appNav.go('settings/model');check(window.msgQueue.length===before,'Nessun caricamento duplicato sulla stessa pagina');
    await back();check(appNav.current==='settings' && !document.getElementById('settings-home').hidden,'Indietro dalla sottopagina torna all’indice');
    appNav.go('settings/chat');setAppearance('dark');
    check(document.body.classList.contains('dark-mode') && document.querySelector('[data-appearance="dark"]').getAttribute('aria-pressed')==='true','Tema scuro selezionabile nella pagina Aspetto');
    setAppearance('light');check(!document.body.classList.contains('dark-mode'),'Tema chiaro ripristinato');
    await back();
    appNav.go('settings/data');document.getElementById('backup-password').value='synthetic-password';await back();
    check(document.getElementById('backup-password').value==='','Password del backup rimossa quando si lascia la pagina');
    appNav.go('settings/notifications');check(!document.getElementById('notification-settings').closest('[hidden]'),'Controlli notifiche raggiungibili');await back();
    appNav.go('settings/dreams');check(!document.getElementById('dream-mode-toggle').closest('[hidden]'),'Controlli sogni raggiungibili');await back();
    const settingsContent=document.querySelector('#panel-settings .screen-content');settingsContent.scrollTop=200;const position=settingsContent.scrollTop;
    appNav.go('profile');await tick();visiblePage('user-modal');fullPage('user-modal');
    check(!document.getElementById('user-modal').querySelector('[role="dialog"],[aria-modal="true"]'),'Profilo interno, senza dialogo e senza focus trap');
    await back();check(Math.abs(settingsContent.scrollTop-position)<1,'Posizione dell’indice conservata al ritorno');
    appNav.go('diagnostics');await tick();visiblePage('view-diagnostics');fullPage('view-diagnostics');
    check(document.getElementById('benchmark-start').closest('#view-diagnostics') && !document.getElementById('benchmark-start').closest('[hidden]'),'Benchmark direttamente nella Diagnostica');
    const select=document.getElementById('benchmark-profile');
    check(Math.abs(select.getBoundingClientRect().width-select.parentElement.getBoundingClientRect().width)<2,'Scelta del benchmark leggibile su tutta la larghezza');
    check(diagInterval!==null && temperatureUpdateInterval!==null,'Monitor attivi solo nella Diagnostica');
    await back();check(diagInterval===null && temperatureUpdateInterval===null,'Monitor interrotti appena si esce');
    await back();visiblePage('view-chat');
    check(messageInput.value==='Bozza di prova da conservare','Bozza della chat conservata');
    for(const name of ['memory','dream']) {
        window.msgQueue.length=0;openPanel(name);await tick();visiblePage('panel-'+name);fullPage('panel-'+name);
        check(window.msgQueue.includes(name==='memory'?'__REQUEST_MEMORY_UPDATE__':'__REQUEST_DREAM_HISTORY__'),'Dati richiesti per '+name);
        await back();visiblePage('view-chat');
    }
    window.msgQueue.length=0;openVoiceMode();await tick();visiblePage('voice-overlay');fullPage('voice-overlay');
    check(VoiceFX.isActive(),'Voce attiva nella propria pagina');
    appNav.go('voice');
    check(window.msgQueue.filter(v=>{try{return JSON.parse(v).action==='set_voice_mode'&&JSON.parse(v).enabled;}catch{return false;}}).length===1,'Voce abilitata una volta sola');
    handleAndroidBack();await tick();visiblePage('view-chat');
    check(!VoiceFX.isActive() && window.msgQueue.some(v=>{try{return JSON.parse(v).action==='set_voice_mode'&&JSON.parse(v).enabled===false;}catch{return false;}}),'Indietro Android ferma microfono, voce ed effetti');
    openPanel('settings');appNav.go('settings/model');startNewChat();await tick();
    check(appNav.current==='chat' && appNav.depth===0,'Nuova chat torna alla pagina principale e azzera il percorso');
    window.newChatReady();messageInput.value='';
    appNav.go('not-a-page');visiblePage('view-chat');
    handleAndroidBack();
    check(JSON.parse(window.msgQueue.at(-1)).action==='navigation_exit','Indietro alla radice restituisce il controllo ad Android');
    return results;
}
