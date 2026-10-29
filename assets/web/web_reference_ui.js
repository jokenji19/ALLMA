/* This preference is owned by the local core, never by browser storage. */
(() => {
    'use strict';
    let enabled=false, pending=null;
    function update(data) {
        clearTimeout(pending);pending=null;
        const toggle=document.getElementById('web-access-toggle');
        const status=document.getElementById('web-access-status');
        if(!toggle || !status)return;
        enabled=data?.enabled===true;
        toggle.checked=enabled;toggle.disabled=false;
        status.textContent=data?.error || (enabled
            ? 'Ricerche consentite. ALLMA può consultare Wikipedia per gli argomenti generali riconosciuti.'
            : 'Modalità locale. Le ricerche online sono disattivate.');
    }
    function send(action,value) {
        if(pending)return;
        const toggle=document.getElementById('web-access-toggle');
        if(toggle){toggle.checked=enabled;toggle.disabled=true;}
        const status=document.getElementById('web-access-status');
        if(status)status.textContent='Controllo la preferenza…';
        pending=setTimeout(()=>update({enabled,error:'Non ho ricevuto conferma. Riapri questa pagina per controllare la preferenza.'}),8000);
        if(window.pyBridge)window.pyBridge.postMessage(JSON.stringify({type:'action',action,enabled:value}));
        else update({enabled,error:'La preferenza è disponibile nell’app ALLMA.'});
    }
    window.webReferenceUI={update,refresh:()=>send('web_status'),configure:value=>send('set_web_access',value)};
    let activeRequest=null;
    function paint(searching=false) {
        const node=document.getElementById('network-activity');
        if(!node)return;
        node.dataset.state=searching?'online':'local';
        node.setAttribute('aria-busy',String(searching));
        node.querySelector('span').textContent=searching?'Ricerca su Internet…':'Locale';
        node.title=searching?'ALLMA sta consultando una fonte pubblica.':'In questo momento ALLMA non sta cercando online.';
    }
    window.referenceActivity={
        begin(id){activeRequest=id;paint();},
        receive(data,id){if(id!==activeRequest || !data)return;paint(data.state==='searching');},
        finish(id){if(id!==activeRequest)return;activeRequest=null;paint();}
    };
    window.receiveReferenceActivity=(data,id)=>window.referenceActivity.receive(data,id);
})();
