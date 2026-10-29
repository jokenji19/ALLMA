const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element {
    constructor(){this.children=[];this.textContent='';this.listeners={};this.dataset={};}
    append(...nodes){this.children.push(...nodes);}
    querySelector(){return null;}
    setAttribute(k,v){this[k]=v;}
    addEventListener(k,v){this.listeners[k]=v;}
}
const toggle=new Element(),status=new Element(),network=new Element(),networkText=new Element(),sent=[];
network.querySelector=()=>networkText;
const document={getElementById:id=>id==='web-access-toggle'?toggle:id==='web-access-status'?status:id==='network-activity'?network:null,createElement:()=>new Element()};
const window={pyBridge:{postMessage:message=>sent.push(JSON.parse(message))}};
const context={document,window,URL,setTimeout:()=>1,clearTimeout:()=>{}};
vm.createContext(context);vm.runInContext(fs.readFileSync('assets/web/web_reference_ui.js','utf8'),context);
window.webReferenceUI.refresh();assert.equal(sent[0].action,'web_status');
window.webReferenceUI.update({enabled:false});assert.equal(toggle.checked,false);
window.webReferenceUI.configure(true);assert.equal(toggle.checked,false);assert.equal(toggle.disabled,true);
assert.equal(sent[1].action,'set_web_access');assert.equal(sent[1].enabled,true);
window.webReferenceUI.update({enabled:true});assert.equal(toggle.checked,true);
window.webReferenceUI.configure(false);window.webReferenceUI.update({enabled:false});assert.equal(toggle.checked,false);
vm.runInContext(fs.readFileSync('assets/web/learning_ui.js','utf8'),context);
function render(url){const wrapper=new Element();window.learningUI.attachOrigin(wrapper,{label:'Fonte',detail:'Estratto',citation:{url,title:'<img onerror=alert(1)>',revision:123}});return wrapper.children.find(n=>n.className==='message-origin');}
const safe=render('https://it.wikipedia.org/wiki/Bussola');
assert.equal(safe.children[2].children[0].href,'https://it.wikipedia.org/wiki/Bussola?oldid=123');
assert.equal(safe.children[2].children[0].textContent,'<img onerror=alert(1)> · Wikipedia');
for(const unsafe of ['javascript:alert(1)','https://it.wikipedia.org.evil.test/wiki/A','https://u:p@it.wikipedia.org/wiki/A','https://it.wikipedia.org/wiki/A?q=secret'])assert.equal(render(unsafe).children.length,2);
const html=fs.readFileSync('assets/web/index.html','utf8');
assert.match(html,/data-settings-page="internet"/);assert.match(html,/src="web_reference_ui.js"/);
assert.doesNotMatch(html,/<input[^>]*id="web-access-toggle"[^>]*checked(?:\s|>)/);
window.referenceActivity.begin(1);assert.equal(networkText.textContent,'Locale');
window.receiveReferenceActivity({state:'searching'},1);assert.equal(network.dataset.state,'online');
window.referenceActivity.begin(2);window.receiveReferenceActivity({state:'searching'},1);assert.equal(network.dataset.state,'local');
window.receiveReferenceActivity({state:'searching'},2);window.referenceActivity.finish(1);assert.equal(network.dataset.state,'online');
window.receiveReferenceActivity({state:'cached'},2);assert.equal(network.dataset.state,'local');
window.receiveReferenceActivity({state:'searching'},2);window.referenceActivity.finish(2);assert.equal(network.dataset.state,'local');
const chat=fs.readFileSync('assets/web/script_v24.js','utf8');
assert.doesNotMatch(chat,/showDreamToast|dream-toast/);
assert.match(chat.slice(chat.indexOf('window.startStream ='),chat.indexOf('window.streamChunk =')),/referenceActivity\?\.begin\(requestId\)/);
const begin=chat.indexOf('window.endStream =');
const end=chat.indexOf('\n};',begin)+4;
function finalScroll(top,request=1){
    const container={scrollHeight:1000,scrollTop:top,clientHeight:400};
    const ctx={window:{updateVoiceAnswer(){}},activeRequestId:1,
        currentStreamBubble:{content:{closest(){}},timerFrozen:true},chatContainer:container,
        thoughtBuffer:'',responseBuffer:'preview',isBackendFinished:false,timerInterval:null,streamStartTime:0,
        renderSafeMarkdown(){container.scrollHeight=1800;},attachPlanReview(){},
        finishStreamUI(){container.scrollHeight+=40;},scrollToBottom(){container.scrollTop=container.scrollHeight;}};
    vm.createContext(ctx);vm.runInContext(chat.slice(begin,end),ctx);ctx.window.endStream('Testo completo',request);
    return container;
}
assert.equal(finalScroll(600).scrollTop,1840); // Instant answer follows existing bottom intent.
assert.equal(finalScroll(50).scrollTop,50); // Reading older messages is respected.
assert.equal(finalScroll(600,2).scrollHeight,1000); // Stale completion cannot move the chat.
console.log('Web consent and citation checks passed');
