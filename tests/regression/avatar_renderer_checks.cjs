/* Renderer contract without a GPU: real geometry, WebGL calls and lifecycle.
 * Shader compilation and visual quality are verified separately in a real browser.
 */
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const window={},sandbox={window,console,Float32Array,Uint16Array,Uint8Array,DataView,atob};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('assets/web/avatar_mesh.js','utf8'),sandbox);
vm.runInContext(fs.readFileSync('assets/web/avatar_view.js','utf8'),sandbox);
const {Portrait}=window.AllmaAvatar;

function mockGL() {
    let next=1;
    const gl={uploads:[],draws:[],deleted:[],uniformValues:{},mask:[true,true,true,true],depthWrites:true,shaders:[],
        createShader(type){const s={id:next++,type};this.shaders.push(s);return s;},
        shaderSource(shader,source){shader.source=source;},compileShader(){},getShaderParameter(){return true;},
        createProgram(){return {id:next++};},attachShader(){},linkProgram(){},getProgramParameter(){return true;},
        createBuffer(){return {id:next++};},bindBuffer(target,buffer){this.bound??={};this.bound[target]=buffer;},
        bufferData(target,data,usage){this.uploads.push({target,buffer:this.bound[target],length:data.length,usage});},
        getUniformLocation(_program,name){return name;},
        getAttribLocation(_program,name){return ['aPosition','aNormal','aRegion','aMaterial','aSize','aNoise','aFade'].indexOf(name);},
        uniform1f(name,value){this.uniformValues[name]=value;},
        uniform2f(name,...values){this.uniformValues[name]=values;},
        uniform3fv(name,values){this.uniformValues[name]=Array.from(values);},
        uniform4fv(name,values){this.uniformValues[name]=Array.from(values);},
        colorMask(...mask){this.mask=mask;},depthMask(value){this.depthWrites=value;},
        drawElements(mode,count,type,offset){this.draws.push({mode,count,type,offset,mask:[...this.mask],depth:this.depthWrites,pass:this.uniformValues.uPoints,depthTest:this.depthTest});},
        drawArrays(mode,start,count){this.draws.push({mode,start,count,mask:[...this.mask],depth:this.depthWrites,pass:this.uniformValues.uPoints,depthTest:this.depthTest});},
        deleteBuffer(buffer){this.deleted.push(['buffer',buffer]);},deleteProgram(program){this.deleted.push(['program',program]);},
        deleteShader(){},useProgram(){},enable(cap){if(cap===this.DEPTH_TEST)this.depthTest=true;},disable(cap){if(cap===this.DEPTH_TEST)this.depthTest=false;},blendFunc(){},depthFunc(){},viewport(){},clearColor(){},clear(){},
        enableVertexAttribArray(){},vertexAttribPointer(){},
    };
    ['VERTEX_SHADER','FRAGMENT_SHADER','COMPILE_STATUS','LINK_STATUS','ARRAY_BUFFER','ELEMENT_ARRAY_BUFFER',
     'STATIC_DRAW','BLEND','SRC_ALPHA','ONE','ONE_MINUS_SRC_ALPHA','DEPTH_TEST','LEQUAL','FLOAT','TRIANGLES',
     'UNSIGNED_SHORT','LINES','POINTS','COLOR_BUFFER_BIT','DEPTH_BUFFER_BIT'].forEach((name,i)=>gl[name]=i+1);
    return gl;
}
function canvasFor(gl) {
    const fallback={clearRect(){},setTransform(){},beginPath(){},arc(){},fill(){},moveTo(){},lineTo(){},stroke(){}};
    return {dataset:{},listeners:new Map(),contexts:[],width:0,height:0,
        addEventListener(name,fn){this.listeners.set(name,fn);},
        removeEventListener(name,fn){if(this.listeners.get(name)===fn)this.listeners.delete(name);},
        getContext(name,options){this.contexts.push({name,options});return name==='webgl'?gl:fallback;},
        fire(name,event={}){this.listeners.get(name)?.(event);},
    };
}
const data={available:true,configured:true,presentation:'neutral',seed:'renderer-synthetic-seed',shape:{},
    expression:{smile:.2,attention:.3,energy:.1,concern:0}};
const gl=mockGL(),canvas=canvasFor(gl),p=new Portrait(canvas);
assert.equal(p.draw(0),false,'No portrait before an explicit saved choice');
p.update({...data,configured:false});assert.equal(gl.uploads.length,0);
p.resize(390,420,1.5);p.update(data);
assert.equal(canvas.dataset.renderer,'webgl');assert.equal(canvas.dataset.renderStyle,'particles');
assert.equal(canvas.dataset.hairStyle,'medium');assert.ok(Number(canvas.dataset.hairPoints)>20000);
const options=canvas.contexts.find(c=>c.name==='webgl').options;
assert.equal(options.powerPreference,'low-power');assert.equal(options.preserveDrawingBuffer,false);
assert.equal(options.antialias,false);assert.equal(options.depth,true);
assert.ok(p.mesh.count>=80000&&p.mesh.count<=150000);
const uploadCount=gl.uploads.length;
assert.ok(uploadCount>=2&&uploadCount<=5,'A bounded set of static vertex and depth buffers');
p.update({...data,expression:{...data.expression,smile:.4}});
assert.equal(gl.uploads.length,uploadCount,'New expressions never rebuild the dense mesh');
assert.equal(p.draw(100,true),true);assert.equal(p.draw(200,true),true);
assert.equal(gl.uploads.length,uploadCount,'Per-frame animation never uploads the particle buffer');
const draws=gl.draws.slice(gl.draws.findLastIndex(d=>d.mode===gl.TRIANGLES));
const depth=draws.filter(d=>d.mode===gl.TRIANGLES),points=draws.filter(d=>d.mode===gl.POINTS&&d.pass===1),flares=draws.filter(d=>d.mode===gl.POINTS&&d.pass===3);
assert.equal(depth.length,1);assert.ok(depth[0].mask.every(v=>v===false),'Hidden triangles only prevent seeing through the head');
assert.equal(depth[0].depth,true);assert.equal(depth[0].type,gl.UNSIGNED_SHORT);
assert.equal(points.length,1,'All particles are drawn in one GPU submission');
assert.equal(points[0].count,p.mesh.count);assert.equal(points[0].start,0);
assert.ok(points[0].mask.every(Boolean));assert.equal(points[0].depth,false);assert.equal(points[0].depthTest,true);
assert.equal(flares.length,1);assert.ok(flares[0].count>0&&flares[0].count<=144);assert.equal(flares[0].depthTest,false);
assert.equal(gl.depthTest,true,'The optical glare layer restores depth testing for the next frame');
assert.equal(canvas.dataset.lighting,'luminous-contours');
assert.ok(draws.filter(d=>d.mode===gl.LINES).every(d=>d.count<=12000),'Optional threads cannot turn into an unbounded network');
const clock=p.clock,motion=gl.uniformValues.uMotion;
p.draw(1200,false);p.draw(2200,false);
assert.equal(p.clock,clock,'Paused frames freeze the animation clock');
assert.equal(gl.uniformValues.uTime,clock);
assert.equal(gl.uniformValues.uMotion,motion,'Pausing cannot switch off the current breath, blink or drift pose');
p.suspend();p.draw(900000,true);assert.equal(p.clock,clock,'Resume never integrates time spent in the background');
p.draw(900100,true);assert.ok(p.clock>clock&&p.clock-clock<=.12);

p.activity([{seq:1,module:'memory',phase:'completed'},{seq:2,module:'model',phase:'running'}],2,0);
assert.deepEqual(Array.from(p.pulse),[.8,0,.8]);
p.activity([{seq:1,module:'memory',phase:'completed'},{seq:2,module:'model',phase:'completed'},
    {seq:3,module:'emotion',phase:'observed'}],3,100);
assert.deepEqual(Array.from(p.pulse),[0,.8,0],'Old snapshot events do not reactivate unrelated modules');
p.activity([{seq:3,module:'memory',phase:'completed'}],3,200);
assert.deepEqual(Array.from(p.pulse),[0,.8,0],'Repeated snapshots cannot restart a pulse');
p.activity([{seq:4,module:'memory',phase:'idle'},{seq:5,module:'model',phase:'disabled'}],5,300);
assert.deepEqual(Array.from(p.pulse),[0,0,0],'Idle and disabled modules have no invented activity');

let prevented=false,restored=0;p.onRestore=()=>restored++;
canvas.fire('webglcontextlost',{preventDefault(){prevented=true;}});
assert.equal(prevented,true);const beforeLost=gl.draws.length;
assert.equal(p.draw(900200),false);assert.equal(gl.draws.length,beforeLost);
canvas.fire('webglcontextrestored');assert.equal(restored,1);assert.equal(p.lost,false);
assert.ok(gl.uploads.length>uploadCount,'A restored context receives fresh GPU buffers');
assert.equal(p.draw(900300),true);
p.clear();assert.equal(p.mesh,null);assert.equal(p.draw(900400),false);
p.update(data);assert.equal(p.draw(900500),true);
p.dispose();assert.equal(canvas.listeners.size,0);assert.equal(p.gl,null);assert.equal(p.mesh,null);
assert.ok(gl.deleted.filter(([kind])=>kind==='buffer').length>=2);
assert.ok(gl.deleted.some(([kind])=>kind==='program'));

const canvas2D=canvasFor(null),fallback=new Portrait(canvas2D);
fallback.resize(390,420,1);fallback.update(data);
assert.equal(canvas2D.dataset.renderer,'canvas2d');assert.equal(canvas2D.dataset.renderStyle,'particles');
assert.ok(fallback.mesh.count>=2000&&fallback.mesh.count<=8000);
assert.equal(fallback.draw(100,true),true);fallback.dispose();
assert.equal(canvas2D.listeners.size,0);
console.log('PASS: depth-only surface, single dense point draw with bounded optical glints, cached GPU buffers, frozen pause, event provenance, context recovery and low-cost fallback');
