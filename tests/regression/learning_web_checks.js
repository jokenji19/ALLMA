async function runLearningChecks() {
    const result=[];
    const check=(v,name)=>{if(!v)throw Error(name);result.push(name);};
    appNav.go('learning');
    check(appNav.current==='learning'&&!document.getElementById('panel-learning').hidden,'Pagina interna raggiungibile');
    learningUIResult({status:'ok',sections:[{title:'Esperienze',items:[{text:'<img src=x onerror=alert(1)>',detail:'Generata dal modello'}]},{title:'Vuota',items:[],empty:'Nessun dato'}]});
    const root=document.getElementById('learning-content');
    check(!root.querySelector('img,[onerror]')&&root.textContent.includes('<img'),'Esperienze mostrate come testo');
    check(root.textContent.includes('Nessun dato'),'Nessuna esperienza inventata a pagina vuota');
    addMessage('42','bot',null,null,{label:'Calcolo verificato',detail:'<script>nessuna esecuzione</script>'});
    const wrapper=chatContainer.lastElementChild;
    check(wrapper.querySelector('.message-origin summary').textContent==='Origine','Provenienza discreta e apribile');
    check(!wrapper.querySelector('.message-origin script'),'Provenienza non eseguibile');
    learningUIResult({status:'busy',sections:[]});
    check(root.textContent.includes('sta rispondendo'),'Lettura rinviata durante un turno');
    learningUIResult({status:'unavailable'});
    check(root.textContent.includes('riprovare'),'Errore leggibile con recupero');
    messageInput.value='';
    appNav.go('chat',{reset:true});
    return result;
}
