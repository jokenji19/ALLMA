const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('assets/web/script_v24.js','utf8');
const nodes=new Map();function get(id){if(!nodes.has(id))nodes.set(id,{value:'',textContent:'',disabled:false,hidden:true});return nodes.get(id);}
const buttons=[{},{}],sent=[];
const context={Date,window:{pyBridge:{postMessage:x=>sent.push(JSON.parse(x))}},document:{getElementById:get,querySelectorAll:()=>buttons}};
vm.createContext(context);vm.runInContext(source.slice(source.indexOf('window.backupUI = {')),context);
const ui=context.window.backupUI;
get('backup-password').value='short';ui.transfer('backup_export');assert.equal(sent.length,0);assert.equal(get('backup-password').value,'');
get('backup-password').value='secret-password-123';ui.transfer('backup_export');assert.equal(sent[0].password,'secret-password-123');assert.equal(get('backup-password').value,'');
ui.update({available:true,enabled:true,busy:true,count:1,latest:{created:'2026-10-17T18:00:00+00:00'}});
assert(buttons.every(x=>x.disabled));assert(get('backup-auto').checked);
ui.update({busy:false,preview:{created:'2026-10-17T18:00:00+00:00',files:7}});assert(!get('backup-preview').hidden);assert(get('backup-preview-text').textContent.includes('7'));
ui.update({busy:false,restart_required:true});assert(get('backup-preview').hidden);assert(buttons.every(x=>x.disabled));
ui.update({busy:false});assert(buttons.every(x=>x.disabled));
console.log('12 backup action checks passed');
