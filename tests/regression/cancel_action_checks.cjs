// Pure production-function checks: no browser or device connection.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('assets/web/script_v24.js','utf8');
const elements=new Map();
for(const name of ['chat-container','message-input','send-btn','voice-mode-btn','chat-status','cancel-generation-btn'])
 elements.set(name,{innerHTML:'',value:'x',style:{},scrollHeight:46,addEventListener(){}});
const messages=[];
const ctx={window:{pyBridge:{postMessage:m=>messages.push(JSON.parse(m))}},
 document:{getElementById:name=>elements.get(name)},currentStreamBubble:null};
vm.createContext(ctx);vm.runInContext(source.slice(0,source.indexOf('// --- MESSAGING ---')),ctx);
const run=s=>vm.runInContext(s,ctx);
run('setChatBusy(true)');
assert.equal(elements.get('cancel-generation-btn').disabled,true,'No stop until request has an owner');
run('window.cancelGeneration({detail:0})');assert.equal(messages.length,0);
run('activeRequestId=1; setChatBusy(true)');
run('window.cancelGeneration({detail:1})');assert.equal(messages.length,0,'Send gesture cannot activate Stop');
run('window.armCancelGeneration(); window.cancelGeneration({detail:1})');
assert.equal(messages.length,1);assert.equal(messages[0].request_id,1);
run('setChatBusy(true)');assert.equal(elements.get('cancel-generation-btn').disabled,true);
run('window.armCancelGeneration(); window.cancelGeneration({detail:1})');assert.equal(messages.length,1,'Idempotent cancellation');
run('activeRequestId=2; cancelIssuedRequestId=null; window.armCancelGeneration(); activeRequestId=3; window.cancelGeneration({detail:1})');
assert.equal(messages.length,1,'Stale pointer cannot cancel newer request');
run('window.armCancelGeneration(); window.disarmCancelGeneration(); window.cancelGeneration({detail:1})');assert.equal(messages.length,1);
run('window.cancelGeneration({detail:0})');assert.equal(messages.length,2,'Keyboard/accessibility can stop');
assert.equal(messages[1].request_id,3);
run('activeRequestId=4; cancelIssuedRequestId=null; newChatPending=true; window.armCancelGeneration(); window.cancelGeneration({detail:0})');
assert.equal(messages.length,2,'No cancellation while opening a conversation');
console.log('11 cancellation checks passed');
