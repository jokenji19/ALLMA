const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const window={},sandbox={window,console,atob:s=>Buffer.from(s,'base64').toString('binary')};vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('assets/web/brain_geometry.js','utf8'),sandbox);
vm.runInContext(fs.readFileSync('assets/web/brain_anatomy.js','utf8'),sandbox);
const {geometry,Renderer}=window.AllmaBrainAnatomy,m=geometry();
assert.equal(m,geometry(),'Anatomy is decoded once');
assert.ok(m.count>6000&&m.count<8000&&m.points.length===m.count);
assert.ok(m.edges.length>15000&&m.edges.length<22000);
assert.ok(m.curves.length>150&&m.curves.length<250,'Contours preserve real cortical folds');
const groups=new Map(),seen=new Set();let longest=0;
for(const p of m.points){
    assert.ok(p.position.length===3&&p.position.every(Number.isFinite));
    const [x,y,z]=p.position;assert.ok(Math.abs(x)<1&&y>-1.1&&y<.85&&Math.abs(z)<1.1);
    assert.ok(p.ridge>=0&&p.ridge<=1);groups.set(p.region,(groups.get(p.region)||0)+1);
}
assert.ok(groups.get('left')>2500&&groups.get('right')>2500&&groups.get('cerebellum')>1000&&groups.get('stem')>200);
for(const e of m.edges){
    assert.ok(e.a>=0&&e.a<m.count&&e.b>=0&&e.b<m.count&&e.a!==e.b);
    const key=Math.min(e.a,e.b)+':'+Math.max(e.a,e.b);assert.ok(!seen.has(key));seen.add(key);
    longest=Math.max(longest,Math.hypot(...m.points[e.a].position.map((v,k)=>v-m.points[e.b].position[k])));
    assert.equal(m.points[e.a].region,m.points[e.b].region,'Structural edges do not invent inter-module links');
}
assert.ok(longest<.40,'No long lines across the cortex');
for(const path of m.curves)assert.ok(path.length>=6&&path.every(p=>p.length===3&&p.every(Number.isFinite)));
let clears=0,strokes=0,dots=0,filledSurfaces=0;
const finite=(...v)=>assert.ok(v.every(Number.isFinite),'Projection is finite');
const context={setTransform(){},clearRect(){clears++;},beginPath(){},moveTo:finite,lineTo:finite,quadraticCurveTo:finite,stroke(){strokes++;},arc(...v){finite(...v);dots++;},fill(){},fillRect(){filledSurfaces++;}};
const canvas={dataset:{},getContext(type){assert.equal(type,'2d');return context;}};
const renderer=new Renderer(canvas);renderer.resize(390,420,1.5);
assert.equal(canvas.dataset.surface,'transparent');assert.equal(canvas.dataset.anatomy,'folded-cortex');
renderer.draw({yaw:-1.08,pitch:.1});assert.ok(strokes>300&&strokes<500);assert.ok(dots>500);assert.equal(filledSurfaces,0);
const first=clears;renderer.draw({yaw:-1.08,pitch:.1});assert.equal(clears,first,'Pulse frames reuse the static anatomy');
for(let i=0;i<12;i++)renderer.draw({yaw:i*Math.PI/6,pitch:i%2?.4:-.4,zoom:1.25,hotspots:[{position:[.2,0,.3],power:1,color:[.2,.6,1]}]});
assert.equal(filledSurfaces,0);assert.equal(clears,first+12);
renderer.resize(360,500,1);renderer.draw({yaw:0,pitch:0});assert.equal(clears,first+13,'Resizing invalidates the cached drawing');
renderer.dispose();const before=dots;renderer.draw({yaw:0,pitch:0});assert.equal(dots,before,'Disposed views never draw again');
console.log('PASS: folded anatomy, cortical contours, finite 360-degree projection, transparent rendering, cache and disposal');
console.log('GEOMETRY '+JSON.stringify({points:m.count,edges:m.edges.length,curves:m.curves.length,longest,regions:Object.fromEntries(groups)}));
