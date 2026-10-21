/* One bounded crossfade after the local artwork, font and document are ready. */
(() => {
    'use strict';
    let started=false,finished=false,revealTimer=0,guardTimer=0;
    const splash=()=>document.getElementById('boot-splash');
    const reduced=()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches||document.body.classList.contains('motion-paused');
    function cleanup(){
        if(finished)return;finished=true;clearTimeout(revealTimer);clearTimeout(guardTimer);
        document.body.classList.remove('boot-loading','boot-revealing');
        const view=splash();if(view){view.classList.add('hidden');view.inert=true;view.setAttribute('aria-hidden','true');}
        document.removeEventListener('visibilitychange',onVisibility);
    }
    function onVisibility(){if(started&&document.hidden)cleanup();}
    window.allmaStartup={
        reveal(options={}){
            if(started||finished)return;started=true;clearTimeout(guardTimer);
            if(!splash()||options.motion===false||reduced()||document.hidden){cleanup();return;}
            // Android first blends in its already-painted WebView. Then the
            // document dissolves into the chat, without extending model loading.
            revealTimer=setTimeout(()=>{
                if(finished)return;
                const view=splash();
                document.body.classList.remove('boot-loading');document.body.classList.add('boot-revealing');
                view.inert=true;view.setAttribute('aria-hidden','true');
                view.addEventListener('transitionend',event=>{if(event.target===view&&event.propertyName==='opacity')cleanup();});
                guardTimer=setTimeout(cleanup,1050);
            },options.native?340:140);
        }
    };
    document.addEventListener('visibilitychange',onVisibility);
    document.addEventListener('DOMContentLoaded',async()=>{
        const view=splash();if(!view){cleanup();return;}
        const art=view.querySelector('.boot-art');
        const assets=Promise.allSettled([document.fonts?.ready,art?.decode?.()]);
        let timeout;await Promise.race([assets,new Promise(resolve=>{timeout=setTimeout(resolve,650);})]);clearTimeout(timeout);
        const progress=view.querySelector('.boot-progress');
        if(progress){progress.style.setProperty('--boot-progress','1');progress.setAttribute('aria-valuenow','100');}
        const percent=view.querySelector('.boot-percent');if(percent)percent.textContent='100%';
        requestAnimationFrame(()=>requestAnimationFrame(()=>{
            if(window.allmaNativeStartup&&window.pyBridge){
                window.pyBridge.postMessage(JSON.stringify({type:'action',action:'startup_ready'}));
                if(!started)guardTimer=setTimeout(()=>window.allmaStartup.reveal(),2400);
            }else window.allmaStartup.reveal();
        }));
    });
})();
