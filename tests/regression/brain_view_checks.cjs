/* Exercise lifecycle and the native-message contract without external packages. */
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
class Element {
    constructor(id=''){this.id=id;this.children=[];this.dataset={};this.hidden=false;this.attrs={};this.listeners={};this.value='';this.firstChild={textContent:''};}
    append(...items){for(const i of items)this.children.push(...(i.fragment?i.children:[i]));}
    replaceChildren(...items){this.children=[];this.append(...items);}
    setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k];}
    addEventListener(k,fn){this.listeners[k]=fn;}
    contains(el){return this===el||this.children.some(c=>c.contains?.(el));}
    focus(){document.activeElement=this;}blur(){document.activeElement=null;}
    getBoundingClientRect(){return {width:360,height:340,left:0,top:0};}
    getClientRects(){return this.hidden?[]:[{}];}
    setPointerCapture(){}
    querySelectorAll(){return [];}
}
const elements=new Map();
const document={hidden:false,activeElement:null,listeners:{},
    querySelectorAll(){return [];},
    getElementById(id){if(!elements.has(id))elements.set(id,new Element(id));return elements.get(id);},
    createElement(){return new Element();},createDocumentFragment(){const el=new Element();el.fragment=true;return el;},
    addEventListener(k,fn){this.listeners[k]=fn;}};
let now=0,next=1,draws=0,labelDraws=[];const frames=new Map(),timers=new Map(),messages=[],sent=[];
const ctx=new Proxy({measureText:text=>({width:text.length*5}),clearRect:()=>{draws++;labelDraws=[];},fillText:(text,x,y)=>labelDraws.push({left:x,right:x+text.length*5,top:y-10,bottom:y+2})}, {get:(o,k)=>o[k]||(()=>{})});
document.getElementById('brain-canvas').getContext=()=>ctx;
const window={document,devicePixelRatio:3,matchMedia:()=>({matches:false}),listeners:{},
    addEventListener(k,f){this.listeners[k]=f;},pyBridge:{postMessage:s=>messages.push(JSON.parse(s))},
    brainChatBusy:()=>false,brainCanCancel:()=>true,submitBrainQuestion:text=>{sent.push(text);return true;}};
const sandbox={window,document,performance:{now:()=>now},console,setTimeout,clearTimeout,
    ResizeObserver:class{observe(){}disconnect(){}},
    requestAnimationFrame:fn=>{const id=next++;frames.set(id,fn);return id;},cancelAnimationFrame:id=>frames.delete(id),
    setInterval:fn=>{const id=next++;timers.set(id,fn);return id;},clearInterval:id=>timers.delete(id)};
vm.runInNewContext(fs.readFileSync('assets/web/brain_view.js','utf8'),sandbox);
assert.equal(timers.size,0);assert.equal(frames.size,0);
window.brainView.open();assert.equal(document.getElementById('brain-explorer').hidden,false);
assert.equal(messages.at(-1).action,'brain_activity');assert.equal(timers.size,1);
assert.equal(document.getElementById('brain-inspector').hidden,false,'The brain opens directly without an avatar or choice');
window.receiveBrainActivity({available:true,seq:0,turn:0,nodes:[],events:[]});
window.brainView.zoom();assert.equal(document.getElementById('brain-canvas').dataset.zoom,'1.25');
const node=(id,label,position)=>({id,label,position,group:'Memoria',description:'Descrizione',state:{phase:'completed'}});
window.receiveBrainActivity({available:true,seq:3,turn:1,active:false,status:'completed',model:'example.gguf',
    nodes:[node('input','Domanda',[-.2,.2,0]),node('memory','<script>unsafe</script>',[.2,-.2,0]),node('model','Modello linguistico',[.21,-.19,0])],
    events:[{seq:2,turn:1,module:'input',phase:'completed',at_ms:0},{seq:3,turn:1,module:'memory',phase:'completed',at_ms:1,from:'input'}]});
assert.equal(document.getElementById('brain-modules').children.length,3);
assert.equal(document.getElementById('brain-modules').children[1].children[1].children[0].textContent,'<script>unsafe</script>');
for(let i=0;i<labelDraws.length;i++)for(let j=i+1;j<labelDraws.length;j++){const a=labelDraws[i],b=labelDraws[j];assert.ok(!(a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top));}
assert.ok(draws>0);assert.equal(document.getElementById('brain-canvas').dataset.observedLinks,'1','Only the observed input to memory connection is drawn');assert.equal(document.getElementById('brain-replay').disabled,false);
window.brainView.replay();assert.equal(document.getElementById('brain-live').textContent,'Riproduzione del percorso');
window.receiveBrainActivity({available:true,seq:4,turn:1,active:false,status:'completed',
    nodes:[node('personality_style','Personalità',[0,0,0])],events:[],
    personality_development:{declared:0,integrated:0,suspended:0,assessments:3,courtesy:1,
        growth:['risposte essenziali nelle spiegazioni: 3 riscontri positivi; consolidata']}});
document.getElementById('brain-modules').children[0].onclick();
assert.ok(document.getElementById('brain-detail-text').textContent.includes('Riscontri specifici: 3'));
assert.ok(document.getElementById('brain-detail-text').textContent.includes('non consolidano il carattere'));
assert.ok(document.getElementById('brain-detail-text').textContent.includes('nelle spiegazioni'));

window.brainView.toggleMotion();assert.equal(frames.size,0);assert.equal(document.getElementById('brain-replay').disabled,true);
document.getElementById('brain-question').value='Quanto fa 18 + 24?';
document.getElementById('brain-form').listeners.submit({preventDefault(){}});assert.deepEqual(sent,['Quanto fa 18 + 24?']);
window.brainView.answer('<b>42</b>');assert.equal(document.getElementById('brain-answer').textContent,'<b>42</b>');
window.brainVisibility(false);assert.equal(timers.size,0);assert.equal(frames.size,0);
window.brainVisibility(true);assert.equal(timers.size,1);
document.hidden=true;document.listeners.visibilitychange();assert.equal(timers.size,0);assert.equal(frames.size,0);
document.hidden=false;document.listeners.visibilitychange();assert.equal(timers.size,1);
window.brainView.close();assert.equal(timers.size,0);assert.equal(frames.size,0);
assert.equal(document.getElementById('view-chat').inert,false);
window.receiveBrainActivity({available:false});assert.equal(document.getElementById('brain-explorer').hidden,true);
const before=messages.length;window.brainView.open();assert.equal(messages.length,before+1);assert.equal(timers.size,1);
window.brainView.open();assert.equal(timers.size,1);window.brainView.close();
console.log('PASS: hidden idle, 3D draw, snapshots, replay, reduced activity, safe text, single submission, visibility and reopen cleanup');
