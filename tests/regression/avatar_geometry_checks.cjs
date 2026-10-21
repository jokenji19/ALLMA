/* Real bundled geometry: density, valid 360° occlusion mesh and bounded fallback. */
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const window={},sandbox={window,console,Float32Array,Uint16Array,Uint8Array,DataView,atob};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('assets/web/avatar_mesh.js','utf8'),sandbox);
vm.runInContext(fs.readFileSync('assets/web/avatar_view.js','utf8'),sandbox);
const {geometry}=window.AllmaAvatar,asset=window.AllmaPortraitMesh;
const a=geometry('synthetic-alpha'),b=geometry('synthetic-alpha'),c=geometry('synthetic-beta');
assert.deepEqual(a.vertices,b.vertices,'A stable identity keeps its sampled portrait');
assert.notDeepEqual(a.vertices,c.vertices,'Different identities vary without changing the source anatomy');
assert.ok(a.count>=80000&&a.count<=150000,'Dense points stay inside the mobile budget');
assert.equal(a.skinCount,asset.count,'No skin truncation above the WebGL1 16-bit index boundary');
assert.equal(a.count,a.skinCount+a.hairCount,'Hair is included in the actual particle count');
assert.equal(a.vertices.length,a.count*11,'Every particle includes position, normal and appearance attributes');
const packed=Buffer.from(asset.points,'base64');
assert.equal(packed.byteLength,a.skinCount*11,'Packed skin particle payload is complete');
const unique=new Set();
for(let i=0;i<a.skinCount;i++){
    unique.add([0,1,2].map(k=>packed.readInt16LE(i*11+k*2)).join(','));
    const normal=[0,1,2].reduce((sum,k)=>sum+(packed.readInt8(i*11+6+k)/127)**2,0);
    assert.ok(normal>.9&&normal<1.1,'Surface lighting has a real, normalized direction at every particle');
}
assert.ok(unique.size>=a.skinCount*.99,'Skin density comes from distinct positions, not many coincident copies');
// A dense global count hid a real sampling failure: tiny eyelid triangles had
// received no particles, leaving black eye holes. Check local coverage as well.
const eyelids=[];
for(const side of [-1,1]){
    const centerX=side*.223,cells=Array(6).fill(0);let count=0,seam=0;
    for(let i=0;i<a.skinCount;i++){
        const x=packed.readInt16LE(i*11)/4096,y=packed.readInt16LE(i*11+2)/4096,z=packed.readInt16LE(i*11+4)/4096;
        if(Math.abs(x-centerX)>=.04||Math.abs(y-.112)>=.03||z<=.5)continue;
        count++;
        const column=Math.min(2,Math.floor((x-centerX+.04)/(.08/3)));
        cells[column+(y>.112?3:0)]++;
        if(Math.abs(x-centerX)<.025&&Math.abs(y-.112)<.008)seam++;
    }
    assert.ok(count>=40,'Each eyelid has actual particle coverage rather than a dark empty patch');
    assert.ok(cells.every(n=>n>=4),'Both halves of each eyelid remain covered across the eye width');
    assert.ok(seam>=6,'The closure itself has particles, not only a bright border around a hole');
    eyelids.push({side,count,cells,seam});
}
assert.ok(a.vertices.every(Number.isFinite));
assert.ok(a.threads.length>0&&a.threads.length/11<=12000&&a.threads.length%22===0,'Bounded paired vertices for fine curved light threads');
assert.ok(a.threads.every(Number.isFinite));assert.ok(a.stars.length>0&&a.stars.length/11<=144&&a.stars.length%11===0,'Few static star anchors');
assert.ok(a.stars.every(Number.isFinite));
assert.deepEqual(a.threads,b.threads);assert.deepEqual(a.stars,b.stars);
assert.ok(a.edges.length<=12000&&a.edges.length%2===0,'Only a bounded number of fine filaments');
assert.ok(a.edges.every(v=>v<a.count));
assert.ok(a.surface.length>0&&a.surface.length%11===0);
assert.ok(a.surface.every(Number.isFinite));
assert.ok(a.surface.length/11<65536,'Depth surface remains compatible with WebGL1');
assert.ok(a.triangles.length>0&&a.triangles.length%3===0);
assert.ok(a.triangles.every(v=>v<a.surface.length/11),'Depth triangles cannot access outside their own vertex buffer');
let front=0,back=0,left=0,right=0;
for(let i=0;i<a.vertices.length;i+=11){
    if(a.vertices[i+2]>.20)front++;
    if(a.vertices[i+2]<-.20)back++;
    if(a.vertices[i]<-.20)left++;
    if(a.vertices[i]>.20)right++;
}
assert.ok(front>a.count*.10&&back>a.count*.10&&left>a.count*.10&&right>a.count*.10,
    'Particles form a full head and shoulders rather than a front-only image');
for(const shape of [{jaw:1.2,nose:.8,softness:.06,openness:.04},{jaw:NaN,nose:Infinity},{eyes:.8,cheeks:1.2}]) {
    const m=geometry('synthetic-alpha',shape);assert.ok(m.vertices.every(Number.isFinite));
    for(let i=0;i<m.vertices.length;i+=11){assert.ok(Math.abs(m.vertices[i])<1.5);assert.ok(Math.abs(m.vertices[i+1])<1.5);assert.ok(Math.abs(m.vertices[i+2])<1);}
}
const fallback=geometry('synthetic-alpha',{},true);
assert.ok(fallback.count>=2000&&fallback.count<=8000&&fallback.count<a.count/8,
    'Devices without WebGL receive a genuinely lighter point portrait');
assert.equal(fallback.threads.length,0);assert.equal(fallback.stars.length,0);assert.equal(fallback.surface.length,0);assert.equal(fallback.triangles.length,0);assert.equal(fallback.edges.length,0);
assert.equal(asset.life_stage,'child');assert.equal(asset.visual_age_months,96);
assert.equal(Object.keys(asset.target_sha256).length,12,'Eight-year geometry uses both baby and child source targets');
assert.ok(Math.abs(asset.age_target_blend.child-7/9)<1e-12);
const hairExtents={};
for(const p of ['feminine','masculine','neutral']){
    const m=geometry('synthetic-alpha',{},false,p);
    assert.equal(m.skinCount,a.skinCount);assert.ok(m.count<=150000&&m.count>m.skinCount+20000);assert.ok(m.vertices.every(Number.isFinite));
    const hair=m.vertices.subarray(m.skinCount*11);let minY=Infinity,maxY=-Infinity,left=0,right=0,back=0;
    for(let i=0;i<hair.length;i+=11){minY=Math.min(minY,hair[i+1]);maxY=Math.max(maxY,hair[i+1]);if(hair[i]<-.15)left++;if(hair[i]>.15)right++;if(hair[i+2]<-.15)back++;}
    assert.ok(left>1000&&right>1000&&back>1000,'Hairstyle has real volume on both sides and behind the head');
    assert.ok(m.surface.length/11<65536&&m.triangles.every(i=>i<m.surface.length/11));
    const light=geometry('synthetic-alpha',{},true,p);assert.ok(light.count<=8000&&light.hairCount>500,'Fallback retains a bounded version of the chosen hair');
    hairExtents[p]={minY,maxY,count:m.hairCount,style:m.hairStyle};
}
assert.ok(hairExtents.feminine.minY<-.8&&hairExtents.masculine.minY>-.3,'Long female hair and short male hair differ in geometry, not just labels');
assert.ok(hairExtents.neutral.minY>hairExtents.feminine.minY&&hairExtents.neutral.minY<hairExtents.masculine.minY);
assert.notDeepEqual(geometry('synthetic-alpha',{},false,'feminine').vertices,geometry('synthetic-alpha',{},false,'masculine').vertices);
console.log('PASS: dense deterministic portrait, complete 360° geometry, valid depth indices, distinct identities and bounded 2D fallback');
console.log('ASSET '+JSON.stringify({version:asset.version,count:a.count,unique:unique.size,
    surface_vertices:a.surface.length/11,triangles:a.triangles.length/3,
    visual_age_months:asset.visual_age_months,eyelids,hairExtents}));
