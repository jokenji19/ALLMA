/* ALLMA · folded cortical filaments. Offline data, transparent surface. */
(() => {
    'use strict';
    const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
    const palette=['201,215,237','229,225,245','188,211,241','224,211,224'];
    let cached;
    function bytes(value){return Uint8Array.from(atob(value),c=>c.charCodeAt(0));}
    function geometry(){
        if(cached)return cached;
        const data=window.AllmaBrainGeometry;
        if(!data)return {points:[],edges:[],curves:[],count:0};
        const positions=new DataView(bytes(data.positions).buffer),links=new DataView(bytes(data.edges).buffer),ridge=bytes(data.ridge);
        const points=[],edges=[],regions=['left','right','cerebellum','stem'];
        let region=0,end=data.regions[0];
        for(let i=0;i<data.count;i++){
            while(i>=end){region++;end+=data.regions[region];}
            points.push({position:[0,1,2].map(k=>positions.getInt16((i*3+k)*2,true)/data.scale),region:regions[region],ridge:ridge[i]/255});
        }
        for(let i=0;i<data.edgeCount;i++)edges.push({a:links.getUint16(i*4,true),b:links.getUint16(i*4+2,true)});
        const curveData=new DataView(bytes(data.filaments).buffer),curves=[];let offset=0;
        for(const length of data.curveLengths){const path=[];for(let i=0;i<length;i++,offset++)path.push([0,1,2].map(k=>curveData.getInt16((offset*3+k)*2,true)/data.scale));curves.push(path);}
        cached={points,edges,curves,count:points.length};return cached;
    }
    class Renderer{
        constructor(canvas){
            this.canvas=canvas;this.context=canvas.getContext('2d');this.mesh=geometry();this.error=!this.context||!this.mesh.count;this.key='';
            canvas.dataset.renderer=this.context?'canvas2d':'unavailable';canvas.dataset.geometry=this.mesh.count?'human-brain-network':'unavailable';canvas.dataset.surface='transparent';
            canvas.dataset.anatomy='folded-cortex';
        }
        resize(width,height,ratio){this.width=width;this.height=height;this.ratio=ratio;this.canvas.width=Math.round(width*ratio);this.canvas.height=Math.round(height*ratio);this.key='';}
        draw({yaw,pitch,zoom=1,hotspots=[]}){
            const c=this.context;if(!c||!this.width||!this.mesh.count)return;
            // Static anatomy is redrawn only when the camera or a real module
            // highlight changes. Travelling pulses use the separate overlay.
            const key=JSON.stringify([yaw,pitch,zoom,hotspots]);if(key===this.key)return;this.key=key;
            c.setTransform(this.ratio,0,0,this.ratio,0,0);c.clearRect(0,0,this.width,this.height);
            const cy=Math.cos(yaw),sy=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch),scale=Math.min(this.width*.44,this.height*.39)*zoom;
            const project=position=>{const [x,y,z]=position,xx=x*cy+z*sy,zz=-x*sy+z*cy,yy=y*cp-zz*sp,depth=y*sp+zz*cp,p=3.5/(3.5-depth);return {x:this.width/2+xx*scale*p,y:this.height/2-yy*scale*p,z:depth,s:p};};
            const projected=this.mesh.points.map(point=>{
                let heat=0;
                for(const h of hotspots){const d=point.position.reduce((sum,v,k)=>sum+(v-h.position[k])**2,0);heat=Math.max(heat,Math.exp(-d*16)*h.power);}
                return {...project(point.position),ridge:point.ridge,heat};
            });
            // Batch the wire into depth/brightness bands instead of thousands
            // of independent strokes. No solid triangles or per-edge blur.
            const bands=Array.from({length:32},()=>[]),glow=[];
            this.mesh.edges.forEach((e,i)=>{
                const a=projected[e.a],b=projected[e.b],front=clamp(((a.z+b.z)/2+1)/2,0,1),ridge=(a.ridge+b.ridge)/2;
                const authored=this.mesh.points[e.a].region==='cerebellum'||this.mesh.points[e.a].region==='stem';
                const light=clamp(.025+front*front*(authored?.55:.18)*(.35+ridge)+Math.max(a.heat,b.heat)*.20,0,.83);
                const band=Math.min(7,Math.floor(light*10)),tone=i%17===0?3:i%11===0?2:i%7===0?1:0;
                bands[tone*8+band].push([a,b]);if(light>.40&&i%5===0)glow.push([a,b]);
            });
            bands.forEach((lines,i)=>{
                if(!lines.length)return;
                c.strokeStyle=`rgba(${palette[Math.floor(i/8)]},${.055+(i%8)*.075})`;c.lineWidth=.52;
                c.beginPath();for(const [a,b] of lines){c.moveTo(a.x,a.y);c.lineTo(b.x,b.y);}c.stroke();
            });
            c.strokeStyle='rgba(169,197,244,.045)';c.lineWidth=2.6;c.beginPath();
            for(const [a,b] of glow){c.moveTo(a.x,a.y);c.lineTo(b.x,b.y);}c.stroke();
            this.mesh.curves.forEach((path,i)=>{
                const row=path.map(project),front=clamp((row.reduce((sum,p)=>sum+p.z,0)/row.length+1)/2,0,1);
                const alpha=.10+front*front*.64;
                const trace=()=>{c.beginPath();c.moveTo(row[0].x,row[0].y);for(let j=1;j<row.length-1;j++){const p=row[j],q=row[j+1];c.quadraticCurveTo(p.x,p.y,(p.x+q.x)/2,(p.y+q.y)/2);}c.lineTo(row.at(-1).x,row.at(-1).y);};
                trace();c.strokeStyle=`rgba(${palette[i%4]},${alpha*.12})`;c.lineWidth=3;c.stroke();
                trace();c.strokeStyle=`rgba(${palette[i%4]},${alpha})`;c.lineWidth=.8;c.stroke();
            });
            const dots=Array.from({length:4},()=>[]);
            projected.forEach((p,i)=>{if(i%3===0&&p.z>-.6&&p.ridge>.25)dots[Math.min(3,Math.floor(clamp((p.z+1)/2,0,.99)*4))].push(p);});
            dots.forEach((rows,i)=>{
                c.fillStyle=`rgba(151,205,249,${.16+i*.16})`;c.beginPath();
                for(const p of rows){const r=(p.ridge>.68?.85:.50)*p.s;c.moveTo(p.x+r,p.y);c.arc(p.x,p.y,r,0,Math.PI*2);}c.fill();
            });
        }
        dispose(){this.context?.clearRect(0,0,this.canvas.width,this.canvas.height);this.context=null;this.key='';}
    }
    window.AllmaBrainAnatomy={geometry,Renderer};
})();
