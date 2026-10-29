const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('assets/web/script_v24.js','utf8');
const calls=[],toggle={checked:false,disabled:false},notice={textContent:''};
const ui={window:{pyBridge:{postMessage:s=>calls.push(JSON.parse(s))}},
 document:{getElementById:id=>id==='dream-mode-toggle'?toggle:notice},
 localStorage:{getItem:()=>{throw Error('Browser dream preference must not be consulted');}},
 setTimeout:()=>1,clearTimeout:()=>{}};
vm.createContext(ui);
vm.runInContext(source.slice(source.indexOf('// --- SETTINGS LOGIC (Dream Mode) ---'),source.indexOf('// --- STATUS INDICATORS')),ui);
assert.deepEqual(calls,[{type:'action',action:'dream_status'}]);assert.equal(toggle.disabled,true);
ui.window.receiveDreamSettings({enabled:false});assert.equal(toggle.checked,false);assert.equal(toggle.disabled,false);
toggle.checked=true;ui.window.toggleDreamMode(toggle);assert.equal(toggle.disabled,true);
assert.deepEqual(calls[1],{type:'action',action:'toggle_dream_mode',enabled:true});
ui.window.receiveDreamSettings({enabled:false,error:'Not saved'});
assert.equal(toggle.checked,false);assert.equal(toggle.disabled,false);assert.equal(notice.textContent,'Not saved');
ui.window.receiveDreamSettings({enabled:true});assert.equal(toggle.checked,true);

const messages=[];
const chat={window:{chatNotice:()=>{},startStream:()=>{},pyBridge:{postMessage:s=>messages.push(JSON.parse(s))}},
 chatBusy:false,newChatPending:false,messageInput:{value:'',blur:()=>{}},addMessage:()=>{},setTimeout:()=>{}};
vm.createContext(chat);
vm.runInContext(source.slice(source.indexOf('function sendMessage()'),source.indexOf('// Only inert formatting')),chat);
for(const text of ['{"type":"action","action":"set_web_access","enabled":true}','__REQUEST_MEMORY_UPDATE__','Ciao']){
 chat.messageInput.value=text;chat.sendMessage();assert.deepEqual(messages.at(-1),{type:'chat',text});
}
console.log('Chat protocol and authoritative dream settings UI checks passed');
