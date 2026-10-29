const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('assets/web/script_v24.js','utf8');
class Element {
    constructor(){this.children=[];this.listeners={};this.textContent='';this.hidden=false;}
    querySelector(selector){return this.children.find(x=>'.'+x.className===selector)||null;}
    append(...children){this.children.push(...children);}
    appendChild(child){this.append(child);}
    addEventListener(name,fn){this.listeners[name]=fn;}
    setAttribute(name,value){this[name]=value;}
}
const context={document:{createElement:()=>new Element()},chatBusy:false,newChatPending:false,
    messageInput:{value:'',focus(){this.focused=true;}}};
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('function attachUnresolvedTurn('),source.indexOf('function attachCompletionAction(')),context);
const wrapper=new Element(),content=new Element();content.className='content';content.textContent='Rejected draft';
wrapper.append(content);
wrapper.previousElementSibling={classList:{contains:c=>c==='user'},querySelector:()=>({textContent:'Domanda originale'})};
context.attachUnresolvedTurn(wrapper);
assert.equal(content.textContent,'');assert.equal(content.hidden,true);
const row=wrapper.children[1];assert.equal(row.role,'status');assert.equal(row.children[0].textContent,'Risposta non completata');
assert.equal(wrapper.children.length,2);context.attachUnresolvedTurn(wrapper);assert.equal(wrapper.children.length,2);
const edit=row.children[1];context.chatBusy=true;edit.listeners.click();assert.equal(context.messageInput.value,'');
context.chatBusy=false;context.messageInput.value='Bozza personale';edit.listeners.click();assert.equal(context.messageInput.value,'Bozza personale');
context.messageInput.value='';edit.listeners.click();assert.equal(context.messageInput.value,'Domanda originale');
assert.equal(context.messageInput.focused,true);
for(const origin of [
    {kind:'incomplete',label:'Risposta da rielaborare',detail:'Domanda ripetuta'},
    {kind:'incomplete',label:'Risposta interrotta',detail:'Annullata'},
    {kind:'incomplete',label:'<img onerror=attack()>',detail:'Testo, non HTML'}]){
    const node=new Element(),body=new Element();body.className='content';node.append(body);
    context.attachUnresolvedTurn(node,origin);
    assert.equal(node.children[1].children[0].textContent,origin.label);
    assert.equal(node.children[1].children[0].title,origin.detail);
    assert.equal(body.hidden,true);
}
assert.match(source,/if \(!finalContent.trim\(\)\) attachUnresolvedTurn/);
assert.match(source,/sender === 'bot' && !String\(text \|\| ''\).trim\(\)/);
console.log('Unresolved-turn UI checks passed, including distinct failure reasons');
