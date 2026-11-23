const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element {
    constructor(){this.children=[];this.textContent='';this.listeners={};this.dataset={};}
    get childElementCount(){return this.children.length;}
    append(...nodes){this.children.push(...nodes);}
    querySelector(selector){
        const [name, excluded] = selector.replace(/^\./, '').split(':not(.');
        return this.children.find(child=>{
            const classes=(child.className || '').split(/\s+/);
            return classes.includes(name) && (!excluded || !classes.includes(excluded.slice(0,-1)));
        }) || null;
    }
    replaceChildren(){this.children=[];}
    setAttribute(k,v){this[k]=v;}
    getAttribute(k){return this[k];}
    addEventListener(k,v){this.listeners[k]=v;}
    focus(){this.focused=true;}
}
const toggle=new Element(),status=new Element(),globe=new Element(),errorNote=new Element(),network=new Element(),sent=[];
const savedList=new Element(), savedStatus=new Element();
const nodes={'web-access-toggle':toggle,'web-access-status':status,'network-activity':network,
    'composer-internet':globe,'composer-internet-error':errorNote,
    'saved-references-content':savedList,'saved-references-status':savedStatus};
const document={getElementById:id=>nodes[id] || null,createElement:()=>new Element(),querySelector:()=>null};
const window={pyBridge:{postMessage:message=>sent.push(message.startsWith('{')?JSON.parse(message):message)}};
let timeout;
const context={document,window,URL,setTimeout:callback=>{timeout=callback;return 1;},clearTimeout:()=>{timeout=null;}};
vm.createContext(context);vm.runInContext(fs.readFileSync('assets/web/web_reference_ui.js','utf8'),context);
assert.equal(sent[0].action,'web_status');
assert.equal(globe.disabled,true);
window.webReferenceUI.update({enabled:true},sent[0].request);
assert.equal(globe['aria-pressed'],'true');assert.equal(toggle.checked,true);
globe.listeners.click();
assert.equal(sent[1].action,'set_web_access');assert.equal(sent[1].enabled,false);
assert.equal(globe['aria-pressed'],'true');assert.equal(toggle.disabled,true);
assert.equal(window.webReferenceUI.writePending,true);
window.webReferenceUI.update({enabled:true},sent[0].request);assert.equal(globe.disabled,true);
window.webReferenceUI.update({enabled:false},sent[1].request);
assert.equal(globe['aria-pressed'],'false');assert.equal(toggle.checked,false);
assert.equal(window.webReferenceUI.writePending,false);
window.webReferenceUI.configure(true);
window.webReferenceUI.update({enabled:true},sent[2].request);
assert.equal(globe['aria-pressed'],'true');assert.equal(toggle.checked,true);
globe.listeners.click();timeout();
assert.match(errorNote.textContent,/non confermato/);
assert.equal(window.webReferenceUI.writePending,true);
globe.listeners.click();
assert.equal(sent.at(-1).action,'web_status');
window.webReferenceUI.update({enabled:false},sent.at(-1).request);
assert.equal(window.webReferenceUI.writePending,false);
assert.equal(errorNote.textContent,'');
const choiceOrigin = {kind:'research_choices', offline:'Attiva Internet dal globo.',
    choices:[{label:'<b>Battaglie</b>',query:'Cerca su Internet Napoleone battaglie'}]};
const wrapperWithChoices = new Element(), chosen = [], notices = [];
window.chatNotice = message => notices.push(message);
window.webReferenceUI.attachChoices(wrapperWithChoices, choiceOrigin, value => chosen.push(value), true);
window.webReferenceUI.attachChoices(wrapperWithChoices, choiceOrigin, value => chosen.push(value), true);
assert.equal(wrapperWithChoices.children.length, 1);
const choices = wrapperWithChoices.children[0];
assert.match(choices.className, /research-choices-enter/);
assert.equal(choices.children[0].textContent, '<b>Battaglie</b>');
window.webReferenceUI.configure(false);
choices.children[0].listeners.click();
assert.deepEqual(chosen, []);
window.webReferenceUI.update({enabled:false}, sent.at(-1).request);
choices.children[0].listeners.click();
assert.deepEqual(notices, ['Attiva Internet dal globo.']);
assert.deepEqual(chosen, []);
window.webReferenceUI.configure(true);
window.webReferenceUI.update({enabled:true}, sent.at(-1).request);
choices.children[0].listeners.click();
assert.deepEqual(chosen, ['Cerca su Internet Napoleone battaglie']);
vm.runInContext(fs.readFileSync('assets/web/learning_ui.js','utf8'),context);
function render(url){const wrapper=new Element();window.learningUI.attachOrigin(wrapper,{label:'Fonte',detail:'Estratto',citation:{url,title:'<img onerror=alert(1)>',revision:123}});return wrapper.children.find(n=>n.className==='message-origin');}
const safe=render('https://it.wikipedia.org/wiki/Bussola');
assert.equal(safe.children[2].children[0].href,'https://it.wikipedia.org/wiki/Bussola?oldid=123');
assert.equal(safe.children[2].children[0].textContent,'<img onerror=alert(1)> · Wikipedia');
for(const unsafe of ['javascript:alert(1)','https://it.wikipedia.org.evil.test/wiki/A','https://u:p@it.wikipedia.org/wiki/A','https://it.wikipedia.org/wiki/A?q=secret'])assert.equal(render(unsafe).children.length,2);
const nasaUrl='https://science.nasa.gov/mission/europa-clipper/why-europa-europa-up-close/';
function renderNasa(url) {
    const wrapper=new Element();
    window.learningUI.attachOrigin(wrapper,{label:'Fonte',detail:'Estratto',via:'internet',coverage:'one_subject',
        citation:{url,title:'Europa',revision:0,provider:'nasa',fetched_at:1780000000}});
    return wrapper;
}
assert.equal(renderNasa(nasaUrl).children[0].textContent,'NASA Science · fonte online · confronto parziale');
assert.equal(renderNasa(nasaUrl).children[1].children[2].children[0].href,nasaUrl);
assert.equal(renderNasa(nasaUrl+'?q=private').children.length,1);
assert.equal(renderNasa('https://science.nasa.gov/unrelated/').children.length,1);
const esaUrl='https://www.esa.int/articles/about-us/directorates/science/juice/juice-factsheet';
const comparison=new Element();
window.learningUI.attachOrigin(comparison,{kind:'reference_comparison',label:'Confronto tra fonti',detail:'Stessa affermazione',
    outcome:'disagreement',sources:[
        {via:'cached',excerpt:'<script>ignored as text</script>',citation:{url:nasaUrl,title:'Europa',revision:0,provider:'nasa'}},
        {via:'obtained',excerpt:'Second passage',citation:{url:esaUrl,title:'Europa',revision:0,provider:'esa'}}]});
assert.equal(comparison.children[0].textContent,'Fonti divergenti');
const sourcePanel=comparison.children[1];
assert.equal(sourcePanel.children[2].children[0].href,nasaUrl);
assert.equal(sourcePanel.children[2].children[1].textContent,' · copia locale');
assert.equal(sourcePanel.children[3].textContent,'<script>ignored as text</script>');
assert.equal(sourcePanel.children[4].children[0].href,esaUrl);
const bookmarkWrapper=new Element(), actions=new Element(), bookmarkId='a'.repeat(32);
window.learningUI.attachSaveButton(bookmarkWrapper,actions);
assert.equal(actions.children.length,0);
window.learningUI.attachOrigin(bookmarkWrapper,{kind:'reference',label:'Fonte',detail:'Estratto',save_id:bookmarkId});
window.learningUI.attachSaveButton(bookmarkWrapper,actions);
window.learningUI.attachSaveButton(bookmarkWrapper,actions);
assert.equal(actions.children.length,2);
const [bookmark,bookmarkFeedback]=actions.children;
assert.equal(bookmark.title,'Ricorda questa informazione con le fonti');
bookmark.listeners.click();
const save=sent.at(-1);
assert.deepEqual(save,{type:'action',action:'save_reference',request:1,id:bookmarkId,saved:true});
assert.equal(bookmark['aria-pressed'],'false');
window.receiveSavedReferences({action:save.action,request:save.request+1,ok:true,id:bookmarkId,saved:true});
assert.equal(bookmark.disabled,true);
window.receiveSavedReferences({action:save.action,request:save.request,ok:true,id:bookmarkId,saved:true});
assert.equal(bookmark['aria-pressed'],'true');
assert.equal(bookmarkFeedback.textContent,'Salvato');
bookmark.listeners.click();
const remove=sent.at(-1);
assert.equal(remove.saved,false);
window.receiveSavedReferences({action:remove.action,request:remove.request,ok:true,id:bookmarkId,saved:false});
assert.equal(bookmark['aria-pressed'],'false');
assert.equal(bookmarkFeedback.textContent,'Rimosso');
window.learningUI.refresh();
const list=sent.at(-2);
assert.equal(list.action,'list_saved_references');
const savedItem={id:bookmarkId,title:'Bussola',answer:'Estratto salvato',saved_at:1780000000,
    origin:{kind:'reference',label:'Dalle fonti salvate',detail:'Estratto recuperato',
        saved_reference:true,citation:{url:'https://it.wikipedia.org/wiki/Bussola',title:'Bussola',revision:123}}};
window.receiveSavedReferences({action:list.action,request:list.request,ok:true,offset:0,has_more:false,items:[savedItem]});
const savedDetails=savedList.children[0].children[0];
assert.equal(savedDetails.children[0].textContent,'Bussola');
assert.equal(savedDetails.children[1].textContent,'Estratto salvato');
assert.equal(savedDetails.children[3].textContent,'Wikipedia · salvata');
savedDetails.children.at(-1).listeners.click();
const removeFromList=sent.at(-1);
assert.equal(removeFromList.saved,false);
window.receiveSavedReferences({action:removeFromList.action,request:removeFromList.request,ok:true,id:bookmarkId,saved:false});
const reload=sent.at(-1);
window.receiveSavedReferences({action:reload.action,request:reload.request,ok:true,offset:0,has_more:false,items:[]});
assert.equal(savedList.children.length,0);
const html=fs.readFileSync('assets/web/index.html','utf8');
assert.match(html,/data-settings-page="internet"/);assert.match(html,/src="web_reference_ui.js"/);
assert.doesNotMatch(html,/<input[^>]*id="web-access-toggle"[^>]*checked(?:\s|>)/);
assert.match(html,/<button id="composer-internet"[^>]+aria-pressed="false"/);
window.referenceActivity.begin(1);assert.equal(network.textContent,'');
window.receiveReferenceActivity({state:'searching'},1);assert.equal(network.dataset.state,'online');
assert.equal(network.textContent,'Ricerca su Internet…');
window.referenceActivity.begin(2);window.receiveReferenceActivity({state:'searching'},1);assert.equal(network.dataset.state,'local');
window.receiveReferenceActivity({state:'searching'},2);window.referenceActivity.finish(1);assert.equal(network.dataset.state,'online');
window.receiveReferenceActivity({state:'cached'},2);assert.equal(network.dataset.state,'local');
window.receiveReferenceActivity({state:'searching'},2);window.referenceActivity.finish(2);assert.equal(network.dataset.state,'local');
assert.equal(network.textContent,'');
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
{
    const wrapper = new Element(), actions = new Element();
    const id = 'a'.repeat(32);
    window.learningUI.attachOrigin(wrapper, {label:'Origine', detail:'Generata', feedback_id:id});
    window.learningUI.attachResponseFeedback(wrapper, actions);
    window.learningUI.attachResponseFeedback(wrapper, actions);
    const [up, down, feedback] = actions.children;
    assert.equal(actions.children.length, 3);
    up.listeners.click();
    assert.equal(sent.at(-1).vote, 'up');
    assert.equal(sent.at(-1).id, id);
    const reply = result => window.receiveSavedReferences({
        action:'response_feedback', request:sent.at(-1).request, id, ok:true, feedback:result});
    reply({vote:'up', status:'approved', saved:false});
    assert.equal(up['aria-pressed'], 'true');
    down.listeners.click();
    assert.equal(sent.at(-1).vote, 'down');
    const check = {status:'corrected', text:'42', origin:{label:'Calcolo', detail:'Ricalcolato'}};
    reply({vote:'down', status:'reviewed', check});
    assert.equal(down['aria-pressed'], 'true');
    const panel = wrapper.children.find(node => node.className === 'message-feedback-panel');
    const [review, form] = panel.children;
    assert.equal(review.children[1].children[0].textContent, '42');
    assert.equal(form.hidden, true);
    const count = sent.length;
    down.listeners.click();
    assert.equal(sent.length, count);
    assert.equal(form.hidden, false);
    const field = form.children[0].children[0];
    field.value = 'Il valore richiesto era un altro.';
    form.listeners.submit({preventDefault(){}});
    assert.equal(sent.at(-1).vote, 'correction');
    assert.equal(sent.at(-1).note, field.value);
    reply({vote:'down', status:'user_correction', note:field.value});
    assert.equal(form.hidden, true);
    assert.equal(feedback.textContent, 'Correzione registrata');
}
{
    const wrapper = new Element(), actions = new Element();
    const id = 'b'.repeat(32);
    window.learningUI.attachOrigin(wrapper, {label:'Origine', detail:'Generata', feedback_id:id});
    window.learningUI.attachResponseFeedback(wrapper, actions);
    const [up, down] = actions.children;
    down.listeners.click();
    const request = sent.at(-1).request;
    const makeSource = (text, revision) => ({text, origin:{label:'Fonte', detail:'Passaggio',
        citation:{title:'Patto tripartito', url:'https://it.wikipedia.org/wiki/Patto_tripartito', revision}}});
    window.receiveSavedReferences({action:'response_feedback', request, id, ok:true,
        feedback:{vote:'down', status:'reviewed', check:{status:'conflicting',
            alternatives:[makeSource('Anno A',101), makeSource('Anno B',102)]}}});
    const panel = wrapper.children.find(node => node.className === 'message-feedback-panel');
    const review = panel.children[0];
    assert.match(review.children[0].textContent, /fonti riportano dati diversi/);
    assert.equal(review.children[1].children[0].textContent, 'Anno A');
    assert.equal(review.children[2].children[0].textContent, 'Anno B');
    assert.equal(up.disabled, true);
    down.listeners.click();
    assert.equal(panel.children[1].hidden, false);
}
console.log('Web consent and citation checks passed');
