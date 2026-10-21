window.runBrainChecks=async function(){
    const rows=[],check=(ok,label)=>{if(!ok)throw Error(label);rows.push('PASS '+label);};
    const $=id=>document.getElementById(id),wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
    const until=async fn=>{for(let i=0;i<100;i++){if(fn())return;await wait(30);}throw Error('Attesa dello stato del cervello scaduta');};
    const originalRAF=window.requestAnimationFrame,originalCancel=window.cancelAnimationFrame,frames=new Set();
    window.requestAnimationFrame=fn=>{let id=originalRAF(t=>{frames.delete(id);fn(t);});frames.add(id);return id;};
    window.cancelAnimationFrame=id=>{frames.delete(id);originalCancel(id);};
    try{
        delete avatarFixture.avatar;
        brainView.open();await until(()=>$('brain-modules').children.length===24);
        check(!$('brain-stage').hidden&&!$('brain-inspector').hidden,'Apertura diretta sul cervello, senza configurazione di un avatar');
        check(!$('avatar-canvas')&&!$('avatar-setup')&&!window.AllmaAvatar,'Ritratto e relativa libreria non caricati');
        const anatomy=$('brain-anatomy-canvas'),ctx=anatomy.getContext('2d');
        check(anatomy.dataset.geometry==='human-brain-network'&&anatomy.dataset.renderer==='canvas2d'&&anatomy.dataset.surface==='transparent','Rete 3D trasparente senza superficie piena');
        check(anatomy.dataset.anatomy==='folded-cortex'&&AllmaBrainAnatomy.geometry().curves.length>150,'Forma anatomica e filamenti lungo le pieghe corticali');
        const pixels=ctx.getImageData(0,0,anatomy.width,anatomy.height).data;let lit=0;for(let i=3;i<pixels.length;i+=4)if(pixels[i])lit++;check(lit>1000,'Punti e collegamenti strutturali effettivamente disegnati');
        const expected=new Set(avatarFixture.events.filter(e=>e.from).map(e=>e.from+':'+e.module));check(Number($('brain-canvas').dataset.observedLinks)===expected.size&&expected.size>0,'Collegamenti osservati visibili e distinti dalla struttura simbolica');
        check($('brain-modules').children.length===24,'Tutti i sistemi osservabili conservati');
        check($('brain-canvas').width===anatomy.width&&anatomy.width>300,'Superficie e attività condividono la risoluzione');
        $('brain-zoom').click();check($('brain-canvas').dataset.zoom==='1.25','Zoom reale del cervello');
        $('brain-reset').click();check($('brain-canvas').dataset.zoom==='1','Centratura ripristina la vista');
        const angles=[];
        for(let i=0;i<65;i++){$('brain-canvas').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));angles.push(Number($('brain-canvas').dataset.yaw));}
        check(angles.some(a=>a>6)&&angles.some(a=>a<.2),'Rotazione completa oltre il retro');
        $('brain-reset').click();
        document.querySelector('#brain-modules [data-node="memory"]').click();
        check($('brain-detail-title').textContent==='Memoria','Selezione del modulo e spiegazione sincronizzate');
        if($('brain-motion').getAttribute('aria-pressed')==='true')brainView.toggleMotion();
        brainView.replay();await wait(90);
        check($('brain-live').textContent==='Riproduzione del percorso','Riproduzione degli eventi osservati disponibile');
        brainView.toggleMotion();await wait(50);
        check(frames.size===0&&$('brain-replay').disabled,'Pausa senza fotogrammi residui');
        receiveBrainActivity(avatarFixture);await wait(40);
        check(frames.size===0,'Aggiornare gli stati non riattiva l’animazione in pausa');
        brainView.toggleMotion();brainVisibility(false);
        check(frames.size===0,'Rendering sospeso in background');
        receiveBrainActivity(avatarFixture);check(frames.size===0,'Risposta tardiva non riattiva la pagina nascosta');
        brainVisibility(true);await wait(60);
        check(!$('brain-explorer').hidden,'Ritorno in primo piano senza configurazioni aggiuntive');
        const submit=window.submitBrainQuestion,sent=[];window.submitBrainQuestion=text=>{sent.push(text);return true;};
        try{$('brain-question').value='Domanda sintetica';$('brain-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));check(sent.length===1&&sent[0]==='Domanda sintetica','Una sola domanda dal cervello verso la chat');}
        finally{window.submitBrainQuestion=submit;}
        brainView.answer('<script>test</script>');check($('brain-answer').textContent==='<script>test</script>'&&!$('brain-answer').children.length,'Risposta visualizzata come testo sicuro');
        handleAndroidBack();await wait(50);
        check($('brain-explorer').hidden&&frames.size===0,'Un solo Indietro torna alla chat e ferma il rendering');
        brainView.open();await until(()=>$('brain-modules').children.length===24);brainView.close();await wait(40);
        check($('brain-explorer').hidden&&frames.size===0,'Riapertura e chiusura senza doppi cicli');
        const fallbackCanvas=document.createElement('canvas'),get=fallbackCanvas.getContext.bind(fallbackCanvas);
        fallbackCanvas.getContext=(type,...args)=>type==='webgl'?null:get(type,...args);
        const fallback=new AllmaBrainAnatomy.Renderer(fallbackCanvas);
        try{fallback.resize(300,360,1);fallback.draw({yaw:-.6,pitch:.28});const pixels=get('2d').getImageData(0,0,300,360).data;let lit=0;for(let i=3;i<pixels.length;i+=4)if(pixels[i])lit++;check(lit>1000,'Forma del cervello disponibile anche senza WebGL');}
        finally{fallback.dispose();}
        return rows;
    }finally{brainView.close();window.requestAnimationFrame=originalRAF;window.cancelAnimationFrame=originalCancel;for(const id of frames)originalCancel(id);}
}
