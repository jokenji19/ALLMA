/* Real foreground observations; symbolic 3D geometry, no model or network library. */
(() => {
    'use strict';
    const $ = id => document.getElementById(id);
    const panel = $('brain-explorer'), canvas = $('brain-canvas');
    if (!panel || !canvas) return;
    const context = canvas.getContext('2d');
    let anatomy=null;
    const phases = {idle:'A riposo',running:'In esecuzione',completed:'Eseguito',no_output:'Nessun output',failed:'Non riuscito',
        cancelled:'Interrotto',not_relevant:'Non selezionato',disabled:'Disattivato',budget_skipped:'Budget insufficiente',
        observed:'Contributo osservativo',guidance:'Indicazioni per la risposta'};
    const colors = {Memoria:'#8ab8db',Emozioni:'#c4a0ce',Evoluzione:'#93bba5',Linguaggio:'#d6b18c',Direzione:'#b5b9d8',Identità:'#dfb998',Ingresso:'#e8c8ac',Uscita:'#e8c8ac'};
    const state = {open:false,visible:true,nodes:[],events:[],seq:0,turn:0,active:false,selected:null,
        packets:[],yaw:-1.08,pitch:.10,zoom:1,clock:0,lastDraw:null,raf:0,timer:0,pending:false,requestAt:0,lastFrame:0,
        paused:window.matchMedia('(prefers-reduced-motion: reduce)').matches,replaying:false,busy:false};
    let size={width:0,height:0}, projected=[], drag=null, previousFocus=null, observer=null;
    function phase(node) {
        if(node.available === false) return 'Modulo non disponibile';
        if(node.enabled === false) return 'Disattivato';
        return phases[node.state?.phase] || 'Non osservato in questo turno';
    }
    function project(point) {
        const [x,y,z]=point, a=state.yaw,b=state.pitch;
        const xx=x*Math.cos(a)+z*Math.sin(a), zz=-x*Math.sin(a)+z*Math.cos(a);
        const yy=y*Math.cos(b)-zz*Math.sin(b), depth=y*Math.sin(b)+zz*Math.cos(b);
        const perspective=3.5/(3.5-depth), scale=Math.min(size.width*.44,size.height*.39)*state.zoom;
        return {x:size.width*.5+xx*scale*perspective,y:size.height*.50-yy*scale*perspective,z:depth,s:perspective};
    }
    function control(a,b){const dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1,bend=Math.min(24,d*.15);return {x:(a.x+b.x)/2-dy/d*bend,y:(a.y+b.y)/2+dx/d*bend};}
    function line(a,b,color,width=1) {
        const q=control(a,b);context.beginPath();context.moveTo(a.x,a.y);context.quadraticCurveTo(q.x,q.y,b.x,b.y);context.strokeStyle=color;context.lineWidth=width;context.stroke();
    }
    function draw(now=performance.now()) {
        if(!context || !state.open || state.foreground===false || document.hidden || !size.width) return;
        const dt=state.lastDraw===null?0:Math.min(.12,Math.max(0,(now-state.lastDraw)/1000));
        state.lastDraw=now;if(!state.paused)state.clock+=dt;
        const rgb=hex=>[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255);
        const hot=state.nodes.filter(n=>n.id===state.selected||((state.active||n.id==='dreams'&&state.dreaming)&&n.state?.phase==='running'))
            .sort((a,b)=>(b.id===state.selected)-(a.id===state.selected)).slice(0,3)
            .map(n=>({position:n.position,power:n.id===state.selected?.85:1,color:rgb(colors[n.group]||'#c4b7e4')}));
        anatomy?.draw({yaw:state.yaw,pitch:state.pitch,zoom:state.zoom,time:state.clock,hotspots:hot});
        context.clearRect(0,0,size.width,size.height);
        projected=state.nodes.map(n=>({...project(n.position),node:n}));
        const byId=Object.fromEntries(projected.map(p=>[p.node.id,p]));
        const turnLinks=new Set();
        state.events.forEach(e=>{
            if(!e.from || !byId[e.from] || !byId[e.module]) return;
            const key=e.from+':'+e.module;if(turnLinks.has(key))return;turnLinks.add(key);
            const a=byId[e.from],b=byId[e.module],selected=[e.from,e.module].includes(state.selected);
            line(a,b,selected?'rgba(235,207,177,.85)':'rgba(205,177,151,.57)',selected?1.45:1.0);
            // Direction remains readable after the travelling pulse has ended.
            const q=control(a,b),t=.67,x=(1-t)**2*a.x+2*(1-t)*t*q.x+t*t*b.x,y=(1-t)**2*a.y+2*(1-t)*t*q.y+t*t*b.y;
            const dx=2*(1-t)*(q.x-a.x)+2*t*(b.x-q.x),dy=2*(1-t)*(q.y-a.y)+2*t*(b.y-q.y),d=Math.hypot(dx,dy)||1;
            context.strokeStyle=selected?'#ebcfb1cc':'#cdb19799';context.lineWidth=1;context.beginPath();
            context.moveTo(x-dx/d*4-dy/d*2.7,y-dy/d*4+dx/d*2.7);context.lineTo(x,y);context.lineTo(x-dx/d*4+dy/d*2.7,y-dy/d*4-dx/d*2.7);context.stroke();
        });
        canvas.dataset.observedLinks=String(turnLinks.size);
        state.packets.forEach(p=>{
            const t=(state.clock*1000-p.born)/1800, from=byId[p.from],to=byId[p.to];
            if(t<0 || t>1 || !from || !to) return;
            const color=colors[to.node.group] || '#d6b18c';
            line(from,to,color+'aa',1.4);
            const q=control(from,to),x=(1-t)**2*from.x+2*(1-t)*t*q.x+t*t*to.x,y=(1-t)**2*from.y+2*(1-t)*t*q.y+t*t*to.y;
            context.shadowBlur=8;context.shadowColor=color;context.fillStyle=color;
            context.beginPath();context.arc(x,y,2.3,0,Math.PI*2);context.fill();context.shadowBlur=0;
        });
        const labels=[];
        projected.slice().sort((a,b)=>a.z-b.z).forEach(p=>{
            const n=p.node, selected=n.id===state.selected, running=n.state?.phase==='running';
            const observed=n.state && !['not_relevant','disabled','budget_skipped','idle'].includes(n.state.phase);
            const color=colors[n.group] || '#d6b18c';
            context.globalAlpha=selected||running?1:observed ? .83 : .38;
            if(running || selected) {
                context.strokeStyle=color+'65';context.lineWidth=1;
                context.beginPath();context.arc(p.x,p.y,(selected?10:8)+(state.paused?0:1.5*Math.sin(state.clock*3)),0,Math.PI*2);context.stroke();
            }
            context.fillStyle=color;context.beginPath();context.arc(p.x,p.y,(selected?4.5:3)*p.s,0,Math.PI*2);context.fill();
            if(selected || running || ['memory','model','emotion'].includes(n.id)) {
                labels.push({p,text:n.id==='model'&&!selected?'Modello':n.label,priority:selected?2:running?1:0});
            }
            context.globalAlpha=1;
        });
        // Place labels after projection, giving selection and live work priority.
        const occupied=[];context.font='10px Inter, sans-serif';
        labels.sort((a,b)=>b.priority-a.priority).forEach(({p,text,priority})=>{
            const width=context.measureText(text).width;
            const choices=[[p.x+10,p.y-7],[p.x-width-10,p.y-7],[p.x-width/2,p.y-20],
                           [p.x-width/2,p.y+23],[p.x+12,p.y+15],[p.x-width-12,p.y+15]];
            for(const [rawX,rawY] of choices) {
                const x=Math.max(10,Math.min(size.width-width-10,rawX));
                const y=Math.max(58,Math.min(size.height-47,rawY));
                const box={left:x-3,right:x+width+3,top:y-12,bottom:y+4};
                if(occupied.some(b=>box.left<b.right&&box.right>b.left&&box.top<b.bottom&&box.bottom>b.top))continue;
                context.globalAlpha=priority?1:.85;context.fillStyle='#071018ce';context.fillRect(x-5,y-12,width+10,18);context.fillStyle='#f0e5da';context.fillText(text,x,y);
                context.globalAlpha=1;occupied.push(box);break;
            }
        });
    }
    function tick(now) {
        state.raf=0;
        if(!state.open || state.foreground===false || document.hidden || state.paused || $('brain-stage').hidden) return;
        const fps=24;
        if(now-state.lastFrame>=1000/fps) {state.lastFrame=now;draw(now);}
        state.packets=state.packets.filter(p=>state.clock*1000-p.born<1800);
        if(state.active||state.packets.length) state.raf=requestAnimationFrame(tick);
        else if(state.replaying) {state.replaying=false;updateBadge();}
    }
    function wake() {draw();if(!state.paused && !state.raf && state.open && state.foreground!==false && !$('brain-stage').hidden && !document.hidden) state.raf=requestAnimationFrame(tick);}
    function resize() {
        const stage=$('brain-stage'),rect=canvas.getBoundingClientRect(), ratio=Math.min(window.devicePixelRatio||1,1.5);
        // CSS zoom must never determine either canvas's backing resolution.
        size={width:stage.clientWidth||rect.width,height:stage.clientHeight||rect.height};
        canvas.width=Math.round(size.width*ratio);canvas.height=Math.round(size.height*ratio);
        anatomy?.resize(size.width,size.height,ratio);
        context?.setTransform(ratio,0,0,ratio,0,0);wake();
    }
    function updateBadge() {
        $('brain-live').textContent=state.replaying?'Riproduzione del percorso':state.active?'Attività in corso':state.dreaming?'Motore onirico in attività':state.turn?'Ultimo turno osservato':'In attesa di attività';
        $('brain-live').dataset.active=String((state.active||state.dreaming)&&!state.replaying);
    }
    function select(id) {state.selected=id;renderDetail();renderModules();wake();}
    function renderDetail() {
        const n=state.nodes.find(n=>n.id===state.selected);if(!n)return;
        $('brain-detail-group').textContent=n.group;$('brain-detail-title').textContent=n.label;
        $('brain-detail-text').textContent=n.description;
        if(n.id==='personality_style' && state.personality) {
            const p=state.personality;
            $('brain-detail-text').textContent+=` Preferenze esplicite: ${p.declared}. Tendenze consolidate: ${p.integrated}; ancora in formazione: ${p.suspended}.`;
            if(p.assessments || p.courtesy) {
                $('brain-detail-text').textContent+=` Riscontri specifici: ${p.assessments||0}. Ringraziamenti: ${p.courtesy||0} (non consolidano il carattere).`;
            }
            if(Array.isArray(p.growth) && p.growth.length) $('brain-detail-text').textContent+=' '+p.growth.join('. ')+'.';
        }
        const ms=n.state?.duration_ms;
        $('brain-detail-state').textContent=phase(n)+(typeof ms==='number'?` · ${ms<1?'<1':ms.toFixed(1)} ms`:'');
    }
    function renderModules() {
        const container=$('brain-modules'),fragment=document.createDocumentFragment();
        const focused=container.contains(document.activeElement)?document.activeElement.dataset.node:null;
        state.nodes.forEach(n=>{
            const b=document.createElement('button');b.type='button';b.className='brain-module'+(n.id===state.selected?' selected':'');
            b.dataset.node=n.id;b.dataset.phase=n.state?.phase || 'idle';b.setAttribute('aria-pressed',String(n.id===state.selected));
            const dot=document.createElement('i');dot.setAttribute('aria-hidden','true');
            const content=document.createElement('span'),label=document.createElement('b'),status=document.createElement('small');
            label.textContent=n.label;status.textContent=phase(n);content.append(label,status);b.append(dot,content);
            b.onclick=()=>select(n.id);fragment.append(b);
        });container.replaceChildren(fragment);
        if(focused)[...container.children].find(b=>b.dataset.node===focused)?.focus({preventScroll:true});
        const observed=state.nodes.filter(n=>n.state&&!['not_relevant','disabled','budget_skipped','idle'].includes(n.state.phase)).length;
        $('brain-observed').textContent=`${observed} sistemi osservati`;
    }
    function request() {
        if(!state.open || state.foreground===false || document.hidden) return;
        const now=performance.now();
        if(state.pending) {if(now-state.requestAt>6000)$('brain-live').textContent='In attesa del collegamento…';return;}
        state.pending=true;state.requestAt=now;
        window.pyBridge?.postMessage(JSON.stringify({type:'action',action:'brain_activity',after:state.seq}));
    }
    function suspend() {clearInterval(state.timer);state.timer=0;cancelAnimationFrame(state.raf);state.raf=0;state.pending=false;state.lastDraw=null;}
    function resume() {if(!state.open || state.foreground===false || document.hidden)return;request();state.timer=setInterval(request,950);wake();}
    window.brainVisibility=function(foreground) {
        state.foreground=foreground===true;suspend();if(state.foreground)resume();
    };
    window.receiveBrainActivity=function(data) {
        if(!state.open) return;
        state.pending=false;
        if(!data || data.available!==true) {$('brain-live').textContent='Collegamento al cervello non disponibile';state.active=false;state.nodes=[];state.events=[];state.packets=[];renderModules();wake();return;}
        if(!Array.isArray(data.nodes) || !Array.isArray(data.events) || data.seq<state.seq)return;
        const changed=state.seq!==data.seq || state.turn!==data.turn || state.nodes.length===0 || state.dreaming!==(data.dreaming===true);
        if(state.turn!==data.turn) {state.events=[];state.packets=[];state.replaying=false;}
        state.turn=data.turn;state.seq=data.seq;state.active=data.active===true;state.dreaming=data.dreaming===true;
        state.personality=data.personality_development||null;
        state.nodes=data.nodes.filter(n=>n&&typeof n.id==='string'&&Array.isArray(n.position)&&n.position.length===3&&n.position.every(Number.isFinite));
        if(changed) {
            const known=new Set(state.events.map(e=>e.seq));
            data.events.filter(e=>!known.has(e.seq)).forEach(e=>{
                state.events.push(e);
                if(e.from)state.packets.push({from:e.from,to:e.module,born:state.clock*1000});
            });
            state.events=state.events.slice(-96);state.packets=state.packets.slice(-48);
            renderModules();renderDetail();
            const list=$('brain-events');list.replaceChildren();
            const stages=new Map();
            state.events.forEach(e=>{
                const first=stages.get(e.module);
                stages.set(e.module,{...e,at_ms:first?.at_ms??e.at_ms});
            });
            [...stages.values()].sort((a,b)=>a.at_ms-b.at_ms).forEach(e=>{
                const li=document.createElement('li'),n=state.nodes.find(n=>n.id===e.module);
                li.textContent=`${(e.at_ms/1000).toFixed(2)} s · ${n?.label||e.module} · ${phases[e.phase]||e.phase}`;list.append(li);
            });
        }
        $('brain-turn').textContent=state.turn?`Domanda ${state.turn} · ${state.active?'in elaborazione':data.status==='completed'?'conclusa':data.status==='cancelled'?'interrotta':'risposta non completata'}`:'Nessuna domanda osservata';
        $('brain-engine').textContent=data.model?data.model.replace(/\.gguf$/i,''):'Modello non ancora caricato';
        $('brain-replay').disabled=!state.events.some(e=>e.from)||state.active||state.paused;
        updateBadge();wake();
    };
    window.brainView={
        open() {
            if(state.open)return;previousFocus=document.activeElement;state.open=true;panel.hidden=false;
            $('brain-stage').hidden=false;$('brain-inspector').hidden=false;
            if(window.AllmaBrainAnatomy&&!anatomy){anatomy=new AllmaBrainAnatomy.Renderer($('brain-anatomy-canvas'));}
            ['view-chat','top-header'].forEach(id=>{if($(id))$(id).inert=true;});
            $('message-input')?.blur();$('brain-close').focus();
            this.setBusy(window.brainChatBusy?.()||false);
            observer=new ResizeObserver(resize);observer.observe($('brain-stage'));resize();resume();
        },
        close() {
            if(!state.open)return;state.open=false;suspend();state.packets=[];state.replaying=false;anatomy?.dispose();anatomy=null;observer?.disconnect();observer=null;panel.hidden=true;
            ['view-chat','top-header'].forEach(id=>{if($(id))$(id).inert=false;});previousFocus?.focus();
        },
        setBusy(busy) {state.busy=busy;$('brain-send').hidden=busy;$('brain-send').disabled=busy;$('brain-stop').hidden=!busy;$('brain-stop').disabled=!busy||!window.brainCanCancel?.();$('brain-question').disabled=busy;},
        answer(text) {if(typeof text==='string'){$('brain-answer').textContent=text;$('brain-answer-box').hidden=!text.trim();}},
        zoom() {state.zoom=state.zoom===1?1.25:1;$('brain-zoom').textContent=state.zoom===1?'Avvicina +':'Allontana −';canvas.dataset.zoom=String(state.zoom);wake();},
        resetPose() {state.yaw=-1.08;state.pitch=.10;state.zoom=1;$('brain-zoom').textContent='Avvicina +';canvas.dataset.zoom='1';wake();},
        back() {this.close();},
        toggleMotion() {state.lastDraw=null;state.paused=!state.paused;$('brain-motion').textContent=state.paused?'Attiva animazioni':'Pausa animazioni';$('brain-motion').setAttribute('aria-pressed',String(state.paused));if(state.paused){cancelAnimationFrame(state.raf);state.raf=0;state.replaying=false;updateBadge();}$('brain-replay').disabled=state.paused||state.active||!state.events.some(e=>e.from);wake();},
        replay() {if(state.active||state.paused)return;state.replaying=true;state.packets=state.events.filter(e=>e.from).slice(-32).map((e,i)=>({from:e.from,to:e.module,born:state.clock*1000+i*110}));updateBadge();wake();}
    };
    $('brain-motion').textContent=state.paused?'Attiva animazioni':'Pausa animazioni';$('brain-motion').setAttribute('aria-pressed',String(state.paused));
    $('brain-form').addEventListener('submit',e=>{
        e.preventDefault();const input=$('brain-question');
        if(!input.value.trim()){$('brain-notice').textContent='Scrivi una domanda per osservare il percorso.';return;}
        if(window.submitBrainQuestion?.(input.value)) {input.value='';input.blur();$('brain-answer-box').hidden=true;$('brain-notice').textContent='La risposta viene salvata nella chat corrente.';request();}
        else $('brain-notice').textContent='Attendi la risposta corrente prima di inviarne un’altra.';
    });
    function rotate(dx,dy) {
        state.yaw=((state.yaw+dx)%(Math.PI*2)+Math.PI*2)%(Math.PI*2);
        state.pitch=Math.max(-1.2,Math.min(1.2,state.pitch+dy));canvas.dataset.yaw=String(state.yaw);
        wake();
    }
    for(const surface of [canvas]) {
    surface.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY};surface.setPointerCapture(e.pointerId);});
    surface.addEventListener('pointermove',e=>{if(!drag)return;rotate((e.clientX-drag.x)*.008,(e.clientY-drag.y)*.006);drag.x=e.clientX;drag.y=e.clientY;});
    surface.addEventListener('pointerup',e=>{
        if(drag&&Math.hypot(e.clientX-drag.startX,e.clientY-drag.startY)<8) {
            const rect=canvas.getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top;
            const node=projected.map(p=>({p,d:Math.hypot(p.x-x,p.y-y)})).sort((a,b)=>a.d-b.d)[0];
            if(node?.d<28)select(node.p.node.id);
        }drag=null;
    });
    surface.addEventListener('pointercancel',()=>{drag=null;});
    surface.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();rotate(e.key==='ArrowLeft'?-.12:e.key==='ArrowRight'?.12:0,e.key==='ArrowUp'?.12:e.key==='ArrowDown'?-.12:0);});
    }
    panel.addEventListener('keydown',e=>{
        if(e.key==='Escape'){e.preventDefault();e.stopPropagation();window.brainView.back();return;}
        if(e.key!=='Tab')return;
        const focus=[...panel.querySelectorAll('button:not([disabled]),input:not([disabled]),canvas,summary')].filter(el=>!el.hidden&&el.getAttribute('aria-hidden')!=='true'&&el.getClientRects().length);
        const first=focus[0],last=focus.at(-1);
        if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}
        if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}
    });
    document.addEventListener('visibilitychange',()=>{suspend();if(!document.hidden)resume();});
    window.addEventListener('pagehide',suspend);
    window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener?.('change',e=>{if(e.matches&&!state.paused)window.brainView.toggleMotion();});
})();
