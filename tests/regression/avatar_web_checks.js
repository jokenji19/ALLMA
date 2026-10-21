async function runAvatarChecks() {
    const results=[],check=(ok,label)=>{if(!ok)throw Error(label);results.push('PASS '+label);};
    const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
    const until=async predicate=>{for(let i=0;i<120;i++){if(predicate())return;await wait(25);}throw Error('Attesa del profilo o renderer scaduta');};
    const $=id=>document.getElementById(id),inputs=()=>[...document.querySelectorAll('input[name="avatar-presentation"]')];
    const originalRAF=window.requestAnimationFrame,originalCancel=window.cancelAnimationFrame,frames=new Set();
    const originalDraw=AllmaAvatar.Portrait.prototype.draw,samples=[];
    const originalPost=window.pyBridge.postMessage;
    AllmaAvatar.Portrait.prototype.draw=function(...args){const at=performance.now();const result=originalDraw.apply(this,args);if(result)samples.push(performance.now()-at);return result;};
    window.requestAnimationFrame=fn=>{let id=originalRAF(t=>{frames.delete(id);fn(t);});frames.add(id);return id;};
    window.cancelAnimationFrame=id=>{frames.delete(id);originalCancel(id);};
    try {
        avatarFixture.avatar.configured=false;avatarFixture.avatar.presentation=null;
        brainView.open();await until(()=>inputs().every(i=>!i.disabled));
        check(!$('avatar-setup').hidden&&$('brain-stage').hidden,'Scelta prima del ritratto, anche per un’impronta esistente');
        check(inputs().length===3&&inputs().every(i=>!i.checked),'Tre opzioni senza preselezione');
        check($('avatar-create').disabled&&frames.size===0,'Nessuna animazione o conferma prima della scelta');
        brainView.zoom();check($('brain-stage').hidden,'Lo zoom non aggira la scelta');
        inputs().find(i=>i.value==='neutral').click();$('avatar-create').click();
        check($('brain-stage').hidden,'Il ritratto attende il salvataggio confermato');
        receiveAvatarConfiguration({ok:true,presentation:'masculine',request_id:'obsolete'});
        check($('brain-stage').hidden,'Conferme obsolete ignorate');
        await until(()=>!$('brain-stage').hidden&&['webgl','canvas2d'].includes($('avatar-canvas').dataset.renderer));
        check($('brain-stage').dataset.view==='avatar'&&$('brain-inspector').hidden,'Il ritratto precede il cervello');
        const points=Number($('avatar-canvas').dataset.points),renderer=$('avatar-canvas').dataset.renderer;
        check(renderer==='webgl'?points>=80000&&points<=150000:points>=2000&&points<=8000,'Ritratto denso, con alternativa leggera senza WebGL');
        check($('avatar-canvas').dataset.renderStyle==='particles','Volto formato da particelle, senza pelle solida');
        check($('avatar-canvas').dataset.lighting==='luminous-contours','Luce concentrata sui contorni e riflessi stellari');
        if(renderer==='webgl'){
            const gl=$('avatar-canvas').getContext('webgl');check(gl.getError()===gl.NO_ERROR,'Passaggi grafici senza errori WebGL');
        }
        const ratio=Math.min(window.devicePixelRatio||1,1.5);
        check(Math.abs($('avatar-canvas').width-$('brain-stage').clientWidth*ratio)<1&&Math.abs($('brain-canvas').width-$('brain-stage').clientWidth*ratio)<1,'Risoluzione corretta anche durante lo zoom');
        check($('avatar-age-label').textContent.includes('8 anni'),'Età visiva di otto anni dichiarata');
        check(!$('avatar-presence-status').textContent.includes('non disponibile'),'Ritratto pronto senza errori');
        const angles=[];
        for(let i=0;i<110;i++){$('avatar-canvas').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));angles.push(Number($('avatar-canvas').dataset.yaw));}
        check(angles.some(a=>a>6.1)&&angles.some(a=>a<.2),'Rotazione completa a 360°, oltre il retro e senza blocchi');
        $('avatar-reset').click();
        check(!$('brain-stage').hidden,'Vista frontale disponibile');
        brainView.editAppearance();check(!$('avatar-setup').hidden&&$('brain-stage').hidden&&frames.size===0,'Modifica sospende il ritratto');
        const seed=avatarFixture.avatar.seed;
        for(const presentation of ['feminine','masculine','neutral']) {
            inputs().find(i=>i.value===presentation).click();$('avatar-create').click();await until(()=>!$('brain-stage').hidden);
            check(avatarFixture.avatar.presentation===presentation&&avatarFixture.avatar.seed===seed,'Aspetto '+presentation+' senza perdere l’impronta');
            check($('avatar-canvas').dataset.hairStyle===({feminine:'long',masculine:'short-dense',neutral:'medium'})[presentation]&&Number($('avatar-canvas').dataset.hairPoints)>0,'Capigliatura effettiva per '+presentation);
            if(presentation!=='neutral')brainView.editAppearance();
        }
        brainView.editAppearance();
        window.pyBridge.postMessage=function(text){const m=JSON.parse(text);if(m.action==='avatar_configure')setTimeout(()=>receiveAvatarConfiguration({ok:false,request_id:m.request_id}),20);else originalPost(text);};
        inputs()[0].click();$('avatar-create').click();await until(()=>!$('avatar-create').disabled);
        check(!$('avatar-setup').hidden&&$('brain-stage').hidden&&$('avatar-setup-status').textContent.includes('Riprova'),'Errore di salvataggio visibile, nessun falso successo');
        window.pyBridge.postMessage=originalPost;handleAndroidBack();
        check($('avatar-setup').hidden&&!$('brain-stage').hidden,'Indietro annulla la modifica senza cancellare il volto');
        brainView.zoom();await wait(80);
        check($('brain-stage').dataset.view==='brain'&&!$('brain-inspector').hidden,'Zoom apre il cervello esistente');
        check($('brain-modules').children.length===24,'Tutti i moduli esistenti conservati');
        check($('avatar-canvas').getAttribute('aria-hidden')==='true','Ritratto escluso dall’accessibilità nello zoom');
        check(!$('brain-replay').disabled,'Riproduzione del percorso osservato conservata');
        handleAndroidBack();check($('brain-stage').dataset.view==='avatar'&&!$('brain-explorer').hidden,'Indietro torna al ritratto');
        brainView.toggleMotion();await wait(60);check(frames.size===0,'Pausa ferma tutti i fotogrammi');
        const next=JSON.parse(JSON.stringify(avatarFixture));next.avatar.expression.smile=0;next.avatar.expression.concern=.4;receiveBrainActivity(next);
        check($('avatar-expression-label').textContent==='Attenta','Espressione negativa distinta da esperienza di ALLMA');
        check(frames.size===0,'I dati aggiornati rispettano la pausa');
        brainView.toggleMotion();await wait(1100);check(frames.size>0,'Animazione riattivabile');
        const times=samples.slice(-10).sort((a,b)=>a-b);
        check(times.length>0&&times.every(Number.isFinite),'Campioni reali della preparazione dei fotogrammi');
        results.push('MEASURE '+points+' punti, invio frame CPU: mediana '+times[Math.floor(times.length/2)].toFixed(3)+' ms; non misura GPU, batteria o Android');
        brainVisibility(false);check(frames.size===0,'Background sospende il rendering');
        receiveBrainActivity(avatarFixture);
        check(frames.size===0,'Risposte native tardive non riattivano il rendering in background');
        brainVisibility(true);await wait(70);check(frames.size>0,'Primo piano riprende il rendering');
        brainView.close();check(frames.size===0,'Chiusura senza fotogrammi residui');
        brainView.open();await until(()=>!$('brain-stage').hidden);
        check($('avatar-setup').hidden&&$('brain-stage').dataset.view==='avatar','Riapertura usa la scelta salvata');
        brainView.close();check(frames.size===0,'Riaperture senza doppi cicli');
        const fallbackCanvas=document.createElement('canvas'),getContext=fallbackCanvas.getContext.bind(fallbackCanvas);
        fallbackCanvas.getContext=(type,...args)=>type==='webgl'?null:getContext(type,...args);
        const fallbackPortrait=new AllmaAvatar.Portrait(fallbackCanvas);
        try{
            fallbackPortrait.resize(300,360,1);fallbackPortrait.update(avatarFixture.avatar);fallbackPortrait.draw(performance.now(),false);
            const pixels=getContext('2d').getImageData(0,0,300,360).data;let lit=0,white=true;
            for(let i=0;i<pixels.length;i+=4)if(pixels[i+3]>20){lit++;if(pixels[i]<pixels[i+1]||pixels[i+1]<pixels[i+2])white=false;}
            check(fallbackCanvas.dataset.renderer==='canvas2d'&&lit>100&&white,'Alternativa Canvas reale: contorni chiari senza superficie blu');
        }finally{fallbackPortrait.dispose();}
        check($('brain-explorer').hidden,'Il collaudo lascia chiuso l’osservatorio prima delle altre prove');
        return results;
    } finally {
        brainView.close();window.pyBridge.postMessage=originalPost;window.requestAnimationFrame=originalRAF;window.cancelAnimationFrame=originalCancel;AllmaAvatar.Portrait.prototype.draw=originalDraw;
        check($('brain-explorer').hidden,'La pulizia finale nasconde l’osservatorio anche se una prova fallisce');
    }
}
