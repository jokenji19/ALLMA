// Pure unit tests: no browser navigation, device connection or model generation.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('assets/web/script_v24.js', 'utf8');
const start = source.indexOf('function attachCompletionAction(');
const end = source.indexOf('\nwindow.endStream', start);
class Element {
    constructor() { this.children=[]; this.listeners={}; this.textContent=''; }
    querySelector(selector) { return this.children.find(e=>'.'+e.className===selector)||null; }
    append(...children) { this.children.push(...children); }
    appendChild(child) { this.append(child); }
    addEventListener(name, fn) { this.listeners[name]=fn; }
}
let sent=0, notices=0;
const context={document:{createElement:()=>new Element()},chatBusy:false,newChatPending:false,
    lastRequestId:5,messageInput:{value:''},window:{chatNotice:()=>notices++},sendMessage:()=>sent++};
vm.createContext(context);vm.runInContext(source.slice(start,end),context);
const wrapper=new Element(); context.attachCompletionAction(wrapper,5);
assert.equal(sent,0,'No automatic continuation');
assert.equal(wrapper.children.length,1);
context.attachCompletionAction(wrapper,5);assert.equal(wrapper.children.length,1,'No duplicate notice');
const row=wrapper.children[0],button=row.children[1];
assert.match(row.children[0].textContent,/limite/);
context.messageInput.value='Bozza personale';button.listeners.click();
assert.equal(sent,0);assert.equal(context.messageInput.value,'Bozza personale');assert.equal(notices,1);
context.messageInput.value='';context.chatBusy=true;button.listeners.click();assert.equal(sent,0);
context.chatBusy=false;context.lastRequestId=6;button.listeners.click();assert.equal(sent,0,'Stale action blocked');
context.lastRequestId=5;button.listeners.click();assert.equal(sent,1);assert.match(context.messageInput.value,/Completa/);
console.log('11 completion action checks passed');
