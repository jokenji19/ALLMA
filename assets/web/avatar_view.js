/* ALLMA · dense luminous particle portrait. Hidden depth surface, no painted skin. */
(() => {
    'use strict';
    const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
    const gaussian=(v,s)=>Math.exp(-v*v/(s*s));
    function random(seed) {
        let s=2166136261;for(const c of String(seed))s=Math.imul(s^c.charCodeAt(0),16777619);
        return ()=>{s^=s<<13;s^=s>>>17;s^=s<<5;return (s>>>0)/4294967296;};
    }
    let anatomical=null;
    function anatomy() {
        if(anatomical)return anatomical;
        const data=window.AllmaPortraitMesh;
        if(!data||data.version!==3||!Number.isInteger(data.count)||data.count<80000||data.count>150000)throw Error('Portrait asset unavailable');
        const decode=value=>Uint8Array.from(atob(value),c=>c.charCodeAt(0));
        const unpack=value=>{
            const bytes=decode(value),view=new DataView(bytes.buffer),positions=new Float32Array(bytes.length/11*8);
            for(let i=0;i<bytes.length/11;i++) {
                for(let k=0;k<3;k++)positions[i*8+k]=view.getInt16(i*11+k*2,true)/4096;
                for(let k=0;k<3;k++)positions[i*8+3+k]=view.getInt8(i*11+6+k)/127;
                positions[i*8+6]=view.getInt8(i*11+9);positions[i*8+7]=view.getUint8(i*11+10)/255;
            }return positions;
        };
        const unpackIndices=value=>{const bytes=decode(value),view=new DataView(bytes.buffer),indices=new Uint16Array(bytes.length/2);
            for(let i=0;i<indices.length;i++)indices[i]=view.getUint16(i*2,true);return indices;};
        const positions=unpack(data.points),edges=unpackIndices(data.edges),surface=unpack(data.surface),triangles=unpackIndices(data.triangles);
        anatomical={positions,edges,surface,triangles,count:data.count};return anatomical;
    }
    function hairGeometry(skin,seed,presentation,low) {
        const rng=random(seed+':hair:'+presentation),long=presentation==='feminine',short=presentation==='masculine';
        const style=long?'long':short?'short-dense':'medium';
        // Fit a spherical scalp map to this actual head, not a floating wig.
        // It is built once with the portrait, then stays entirely on the GPU.
        const columns=96,rows=48,maxPhi=2.12,cy=.22,cz=-.04;
        const radius=new Float32Array(columns*rows),cost=new Float32Array(columns*rows).fill(Infinity);
        for(let i=0;i<skin.length;i+=11){
            const x=skin[i],y=skin[i+1]-cy,z=skin[i+2]-cz;
            if(skin[i+1]<-.18)continue;
            const phi=Math.atan2(Math.hypot(x,z),y);if(phi>maxPhi)continue;
            const theta=(Math.atan2(x,z)+Math.PI*2)%(Math.PI*2),col=Math.round(theta/(Math.PI*2)*columns)%columns;
            const row=Math.min(rows-1,Math.round(phi/maxPhi*(rows-1))),index=row*columns+col;
            const delta=Math.min(Math.abs(theta-col/columns*Math.PI*2),Math.PI*2-Math.abs(theta-col/columns*Math.PI*2));
            const distance=delta*delta*Math.sin(phi)**2+(phi-row/(rows-1)*maxPhi)**2;
            if(distance<cost[index]){cost[index]=distance;radius[index]=Math.hypot(x,y,z);}
        }
        for(let pass=0;pass<12&&radius.some(v=>v===0);pass++){
            const previous=radius.slice();
            for(let row=0;row<rows;row++)for(let col=0;col<columns;col++){
                const index=row*columns+col;if(previous[index])continue;
                const near=[previous[row*columns+(col+1)%columns],previous[row*columns+(col+columns-1)%columns],
                    row?previous[index-columns]:0,row+1<rows?previous[index+columns]:0].filter(v=>v>0);
                if(near.length)radius[index]=near.reduce((a,b)=>a+b)/near.length;
            }
        }
        const radial=(theta,phi)=>{
            const x=((theta/(Math.PI*2)*columns)%columns+columns)%columns,y=clamp(phi/maxPhi*(rows-1),0,rows-1);
            const a=Math.floor(x),b=Math.min(rows-2,Math.floor(y)),u=x-a,v=y-b;
            const r=(row,col)=>radius[row*columns+col%columns]||.63;
            return (r(b,a)*(1-u)+r(b,a+1)*u)*(1-v)+(r(b+1,a)*(1-u)+r(b+1,a+1)*u)*v;
        };
        const unit=(x,y,z)=>{const l=Math.hypot(x,y,z)||1;return [x/l,y/l,z/l];};
        const capEnd=theta=>{
            const front=((1+Math.cos(theta))*.5)**3;
            return long?1.53-.48*front:short?2.02-.97*front:1.72-.67*front;
        };
        const scalp=(theta,phi,lift)=>{
            const dx=Math.sin(phi)*Math.sin(theta),dy=Math.cos(phi),dz=Math.sin(phi)*Math.cos(theta);
            const r=radial(theta,phi)+lift,n=unit(dx/.55,dy/.69,dz/.62);
            return {p:[dx*r,cy+dy*r,cz+dz*r],n};
        };
        const curtain=(theta,u,lift,endY)=>{
            const {p}=scalp(theta,capEnd(theta),lift),side=Math.sin(theta);
            return {p:[p[0]*(1+.08*u)+side*.022*Math.sin(u*7+theta*3)*u,
                p[1]+(endY-p[1])*u,p[2]-.035*u+.018*Math.sin(u*8+theta*4)*u],n:unit(side,.04,Math.cos(theta))};
        };
        const vertices=[],threads=[],surface=[],triangles=[];
        const strands=low?90:long?1200:short?1600:1200,steps=low?12:long?32:short?18:24;
        for(let i=0;i<strands;i++){
            const theta=(i+rng()*.8)/strands*Math.PI*2,phase=rng()*Math.PI*2,layer=rng(),end=capEnd(theta);
            const start=Math.acos(1-rng()*(1-Math.cos(end*.94)));
            const falls=!short&&Math.cos(theta)<.56,endY=(long?-.96:-.36)+rng()*.10,spacing=(rng()-.5)*.90;
            const records=[];
            for(let j=0;j<steps;j++){
                const t=j===0?0:j===steps-1?1:(j+spacing)/(steps-1),angle=theta+.035*Math.sin(t*3+phase)*Math.sin(t*Math.PI);
                let point;
                if(falls&&t>.56){point=curtain(angle,(t-.56)/.44,.055+layer*.035,endY);}
                else {
                    const progress=falls?t/.56:t;
                    const phi=short?Math.min(end,start+(.16+layer*.22)*progress):start+(end-start)*progress;
                    const lift=.036+layer*.05+(short?.065:.025)*Math.sin(progress*Math.PI)
                        +.008*Math.sin(progress*10+phase)*Math.sin(progress*Math.PI);
                    point=scalp(angle,phi,lift);
                }
                const fade=.95-.35*Math.max(0,(t-.86)/.14),noise=(i*.61803398875+layer*.15)%1;
                const record=[...point.p,...point.n,6,.70+layer*.45,.40+rng()*.40,noise,fade];
                vertices.push(...record);records.push(record);
            }
            // A few continuous guide strands reinforce the point texture.
            if(!low&&i%Math.ceil(strands/88)===0)for(let j=1;j<records.length;j++)threads.push(...records[j-1],...records[j]);
        }
        if(!low){
            const addGrid=(cols,levels,point)=>{
                const offset=surface.length/11;
                for(let y=0;y<=levels;y++)for(let x=0;x<=cols;x++){
                    const {p,n}=point(x/cols,y/levels);surface.push(...p,...n,6,1,.5,.5,1);
                    if(y&&x){const a=offset+(y-1)*(cols+1)+x-1,b=a+1,c=a+cols+1,d=c+1;triangles.push(a,c,b,b,c,d);}
                }
            };
            addGrid(96,22,(u,v)=>{const theta=u*Math.PI*2;return scalp(theta,.008+v*(capEnd(theta)-.008),.021);});
            if(!short){
                const opening=Math.acos(.56);
                addGrid(80,12,(u,v)=>curtain(opening+u*(Math.PI*2-opening*2),v,.026,long?-.92:-.32));
            }
        }
        return {vertices:new Float32Array(vertices),threads:new Float32Array(threads),
            surface:new Float32Array(surface),triangles:new Uint16Array(triangles),style,count:strands*steps};
    }
    function geometry(seed,shape={},low=false,presentation='neutral') {
        const source=anatomy(),rng=random(seed),stride=low?Math.ceil(source.count/6500):1;
        const safe=(key,base,lo=.8,hi=1.2)=>typeof shape[key]==='number'&&Number.isFinite(shape[key])?clamp(shape[key],lo,hi):base;
        const jaw=safe('jaw',1),cheeks=safe('cheeks',1),nose=safe('nose',1),eyes=safe('eyes',1);
        const softness=safe('softness',0,0,.06),openness=safe('openness',0,0,.04),brow=safe('brow',0,-.02,.02);
        // Three subtle child presentations, with no adult secondary characteristics.
        const style=presentation==='feminine'?-1:presentation==='masculine'?1:0;
        const transform=(input,stride,surface=false)=>{const vertices=[];
            for(let i=0;i<input.length/8;i+=stride) {
                let [x,y,z,nx,ny,nz,material,fade]=input.subarray(i*8,i*8+8);
                const front=clamp((z-.25)*3,0,1),head=clamp((y+.65)*4,0,1);
                const eye=gaussian(Math.abs(x)-.223,.12)*gaussian(y-.112,.10)*front;
                if(!material) {
                    x*=1+((jaw-1)*.45+style*.014)*gaussian(y+.30,.23)*head+(cheeks-1)*.45*gaussian(y+.08,.25)*head;
                    z+=(nose-1)*.08*gaussian(x,.10)*gaussian(y+.01,.16)*front;
                    z+=softness*.25*gaussian(Math.abs(x)-.29,.14)*gaussian(y+.10,.25)*front;
                    y+=(brow-style*.005)*gaussian(y-.28,.06)*gaussian(Math.abs(x)-.223,.14)*front;
                    x+=Math.sign(x)*(eyes-1)*.015*eye;
                    y+=openness*.20*gaussian(y-.28,.08)*front;
                }
                const jitter=surface?0:(rng()-.5)*.0008;x+=nx*jitter;y+=ny*jitter;z+=nz*jitter;
                const region=y<-.66?1:eye>.3?2:Math.abs(y-.28)<.07&&front>.6?3:Math.abs(y+.34)<.06&&Math.abs(x)<.23&&front>.5?4:0;
                const lidU=clamp((Math.abs(x)-.223)/.15,-1,1);
                const foldY=.108+.025*lidU*lidU;
                const lidShadow=.45*gaussian(y-foldY,.013)*gaussian(Math.abs(x)-.223,.12)*front;
                const browShadow=.12*gaussian(y-.275,.025)*gaussian(Math.abs(x)-.223,.13)*front;
                const materialLight=1-lidShadow-browShadow;
                vertices.push(x,y,z,nx,ny,nz,region,materialLight,.45+rng()*.55,rng(),fade);
            }return new Float32Array(vertices);
        };
        const skin=transform(source.positions,stride),hair=hairGeometry(skin,seed,presentation,low),threads=[],stars=[];
        const join=(a,b)=>{const out=new a.constructor(a.length+b.length);out.set(a);out.set(b,a.length);return out;};
        const vertices=join(skin,hair.vertices),skinSurface=low?new Float32Array():transform(source.surface,1,true);
        if(!low) {
            // Reuse the sampled anatomy: luminous threads and lens glints stay
            // attached to this same face, including when the user rotates it.
            for(const i of source.edges)for(let k=0;k<11;k++)threads.push(vertices[i*11+k]);
            for(let i=0;i<vertices.length;i+=11) {
                const x=vertices[i],y=vertices[i+1],z=vertices[i+2],noise=vertices[i+9];
                if(noise>.9975&&y>-.70&&vertices[i+10]>.75&&stars.length<144*11) {
                    const anchor=Array.from(vertices.subarray(i,i+11));
                    anchor[9]=(noise*7919)%1;stars.push(...anchor);
                }
            }
        }
        const hairIndices=Uint16Array.from(hair.triangles,v=>v+skinSurface.length/11);
        return {vertices,surface:join(skinSurface,hair.surface),
            triangles:low?new Uint16Array():join(source.triangles,hairIndices),edges:low?new Uint16Array():source.edges,
            threads:join(new Float32Array(threads),hair.threads),stars:new Float32Array(stars),
            count:vertices.length/11,skinCount:skin.length/11,hairCount:hair.count,hairStyle:hair.style};
    }
    const vertex=`
        attribute vec3 aPosition; attribute vec3 aNormal; attribute float aRegion;
        attribute float aMaterial; attribute float aSize; attribute float aNoise; attribute float aFade;
        uniform vec2 uViewport; uniform vec2 uCamera; uniform float uTime;
        uniform vec4 uExpression; uniform vec3 uPulse; uniform float uRatio; uniform float uDepthBias; uniform mediump float uPoints;
        varying float vLight; varying float vNoise; varying float vEnergy; varying float vFade; varying float vDust;
        varying float vGlint;
        float g(float d,float s){return exp(-d*d/(s*s));}
        vec3 turn(vec3 p,float a,float b){
            vec3 q=vec3(p.x*cos(a)+p.z*sin(a),p.y,-p.x*sin(a)+p.z*cos(a));
            return vec3(q.x,q.y*cos(b)-q.z*sin(b),q.y*sin(b)+q.z*cos(b));
        }
        void main(){
            vec3 p=aPosition,n=normalize(aNormal);float front=smoothstep(0.25,0.55,p.z);
            float hair=step(5.5,aRegion);
            float mouth=g(p.y+0.34,0.085)*g(p.x,0.25)*front*(1.0-hair);
            p.y+=mouth*(uExpression.x*0.035*pow(abs(p.x)/0.20,1.3)-uExpression.w*0.008);
            float brow=g(p.y-0.28,0.06)*g(abs(p.x)-0.223,0.14)*front;
            p.y+=brow*(uExpression.y*0.010+uExpression.w*0.014*g(p.x,0.25));
            // The eyelids are sculpted softly closed. No glass spheres or staring pupils.
            float breath=sin(uTime*0.63)*0.004;
            p.y+=breath;if(aRegion>0.5&&aRegion<1.5)p.x*=1.0+breath*0.65;
            float dust=0.0;
            if(uPoints>0.5){
                vec3 tangent=normalize(cross(n,vec3(0.12,1.0,0.18)));
                float phase=aNoise*6.2831853;
                float flow=sin(uTime*0.55+p.y*5.0+phase)*0.0048*(1.0+dot(uPulse,vec3(0.15)));
                p+=tangent*flow+n*(0.0032+sin(uTime*0.44+p.x*4.0+phase)*0.0012);
                dust=step(0.987,aNoise)*smoothstep(0.30,0.58,abs(p.x))*(1.0-hair);
                p+=n*dust*(0.025+0.11*(0.5+0.5*sin(uTime*0.31+phase*9.0)));
            }
            float yaw=uCamera.x+sin(uTime*0.19)*0.014;
            float pitch=uCamera.y+sin(uTime*0.23)*0.006;
            vec3 q=turn(p,yaw,pitch),normal=turn(n,yaw,pitch);
            float perspective=4.2/(4.2-q.z);
            float aspect=uViewport.x/uViewport.y;float scale=min(0.78,1.04*aspect/1.12);
            gl_Position=vec4(q.x*perspective*scale/aspect,(q.y-0.04)*perspective*scale,-q.z*0.22-uDepthBias,1.0);
            gl_PointSize=clamp(uRatio*(1.05+aSize*1.10)*perspective,1.0,4.0);
            float key=max(0.0,dot(normal,normalize(vec3(-0.45,0.65,1.0))));
            float fill=max(0.0,dot(normal,normalize(vec3(0.8,0.15,0.5))));
            float edge=1.0-abs(normal.z);
            float rim=pow(edge,3.1);
            // The luminous silhouette does the modelling; the centre stays dark.
            float wave=0.78+0.22*sin(p.y*21.0+p.x*9.0+uTime*0.30);
            vLight=(0.008+0.026*key+0.012*fill+1.28*rim*wave)*aMaterial;
            if(hair>0.5)vLight=(0.035+0.085*key+0.035*fill+1.15*rim*wave)*aMaterial;
            float twinkle=pow(0.5+0.5*sin(uTime*0.48+aNoise*37.0),3.0);
            vGlint=smoothstep(0.18,0.66,edge)*smoothstep(-0.025,0.10,normal.z)*(0.025+2.1*twinkle*twinkle);
            if(uPoints>1.5&&uPoints<2.5){
                vLight*=1.2+smoothstep(0.33,0.70,p.y)*0.8;
                if(hair>0.5)vLight=max(vLight,0.045+0.85*pow(edge,2.0));
            }
            if(uPoints>2.5){
                gl_PointSize=clamp(uRatio*(35.0+aSize*58.0)*perspective,20.0,128.0);
                if(vGlint<0.018)gl_Position=vec4(3.0,3.0,0.0,1.0);
            }
            vFade=aFade*smoothstep(-1.14,-0.97,p.y);
            vEnergy=(uPulse.x*g(p.x+0.23,0.25)*g(p.y-0.43,0.4)
                    +uPulse.y*g(p.x-0.23,0.25)*g(p.y-0.25,0.4)
                    +uPulse.z*g(p.x,0.30)*g(p.y-0.86,0.3))*front;
            vNoise=aNoise;vDust=dust;
        }`;
    const fragment=`precision mediump float;
        varying float vLight; varying float vNoise; varying float vEnergy; varying float vFade; varying float vDust;
        varying float vGlint;
        uniform mediump float uPoints;
        void main(){
            float alpha=vFade*vLight;vec3 color=vec3(1.0,0.995,0.985);
            if(uPoints>2.5){
                vec2 uv=(gl_PointCoord-vec2(0.5))*2.0;
                float angle=-0.62+vNoise*0.12,c=cos(angle),s=sin(angle);
                vec2 q=vec2(uv.x*c-uv.y*s,uv.x*s+uv.y*c);
                float r=length(q);
                float streakX=exp(-abs(q.y)*65.0)*pow(max(0.0,1.0-abs(q.x)),1.55);
                float streakY=exp(-abs(q.x)*95.0)*pow(max(0.0,1.0-abs(q.y)),2.4)*0.60;
                float core=exp(-r*r*220.0),halo=exp(-r*r*19.0)*0.045;
                alpha=vFade*vGlint*(core+streakX*0.85+streakY*0.55+halo);
                // Restrained prismatic fringes on lens rays, never blue skin.
                vec3 fringe=mix(vec3(1.0,0.62,0.47),vec3(0.66,0.61,1.0),smoothstep(-0.7,0.7,q.x));
                color=mix(vec3(1.0),fringe,smoothstep(0.12,0.85,r)*0.32);
            }else if(uPoints>0.5&&uPoints<1.5){
                float d=length(gl_PointCoord-vec2(0.5));if(d>0.5)discard;
                float core=exp(-d*d*26.0)+0.11*exp(-d*d*6.0);
                float sparkle=0.58+vNoise*0.62+step(0.965,vNoise)*0.40;
                alpha*=2.55*core*sparkle*(1.0-vDust*0.68)*(1.0+vEnergy*0.25);
            }else if(uPoints>1.5){alpha*=0.20;}
            gl_FragColor=vec4(color,min(0.96,alpha));
        }`;
    class Portrait {
        constructor(canvas) {
            this.canvas=canvas;this.data=null;this.mesh=null;this.key='';this.lastTime=null;
            this.clock=0;this.width=0;this.height=0;this.ratio=1;this.yaw=-.48;this.pitch=.02;
            this.expression=[0,.12,.12,0];this.pulse=[0,0,0];this.seq=-1;this.eventCursor=-1;this.pulseAt=0;this.suspended=true;
            this.lost=false;this.gl=null;this.fallback=null;
            this.contextLost=e=>{e.preventDefault();this.lost=true;};
            this.contextRestored=()=>{this.lost=false;this.initGL();this.key='';this.update(this.data);this.onRestore?.();};
            canvas.addEventListener('webglcontextlost',this.contextLost);
            canvas.addEventListener('webglcontextrestored',this.contextRestored);
        }
        initGL() {
            const gl=this.canvas.getContext('webgl',{alpha:true,antialias:false,depth:true,stencil:false,preserveDrawingBuffer:false,powerPreference:'low-power'});
            if(!gl){this.fallback=this.canvas.getContext('2d');this.canvas.dataset.renderer=this.fallback?'canvas2d':'unavailable';this.canvas.dataset.renderStyle='particles';this.canvas.dataset.lighting='luminous-contours';return;}
            const compile=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)){const detail=gl.getShaderInfoLog(s);gl.deleteShader(s);throw Error('Portrait shader unavailable: '+detail);}return s;};
            let vs,fs,program;
            try {
                vs=compile(gl.VERTEX_SHADER,vertex);fs=compile(gl.FRAGMENT_SHADER,fragment);program=gl.createProgram();
                gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);
                if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error('Portrait program unavailable: '+gl.getProgramInfoLog(program));
                this.program=program;this.gl=gl;this.buffer=gl.createBuffer();this.edges=gl.createBuffer();this.surfaceBuffer=gl.createBuffer();this.trianglesBuffer=gl.createBuffer();this.starBuffer=gl.createBuffer();this.uniforms={};this.attributes={};
                ['Viewport','Camera','Time','Expression','Pulse','Ratio','Points','DepthBias'].forEach(n=>this.uniforms[n]=gl.getUniformLocation(program,'u'+n));
                ['aPosition','aNormal','aRegion','aMaterial','aSize','aNoise','aFade'].forEach(n=>this.attributes[n]=gl.getAttribLocation(program,n));
                gl.useProgram(program);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);
                this.error=false;this.canvas.dataset.renderer='webgl';this.canvas.dataset.renderStyle='particles';this.canvas.dataset.lighting='luminous-contours';
            } catch(error) {if(program)gl.deleteProgram(program);this.error=true;this.canvas.dataset.renderer='unavailable';console.warn('ALLMA portrait: '+error.message);}
            finally {if(vs)gl.deleteShader(vs);if(fs)gl.deleteShader(fs);}
        }
        update(data) {
            this.data=data;
            if(!data?.available || data.configured!==true || !['feminine','masculine','neutral'].includes(data.presentation) || typeof data.seed!=='string'){this.clear();return;}
            if(!this.gl&&!this.fallback&&!this.error)this.initGL();
            const key=data.seed+data.presentation+JSON.stringify(data.shape);
            if(key!==this.key) {
                this.key=key;this.mesh=geometry(data.seed,data.shape,!!this.fallback,data.presentation);
                this.canvas.dataset.points=String(this.mesh.count);
                this.canvas.dataset.hairStyle=this.mesh.hairStyle;this.canvas.dataset.hairPoints=String(this.mesh.hairCount);
                if(this.gl&&!this.lost) {
                    this.gl.bindBuffer(this.gl.ARRAY_BUFFER,this.buffer);this.gl.bufferData(this.gl.ARRAY_BUFFER,this.mesh.vertices,this.gl.STATIC_DRAW);
                    this.gl.bindBuffer(this.gl.ARRAY_BUFFER,this.edges);this.gl.bufferData(this.gl.ARRAY_BUFFER,this.mesh.threads,this.gl.STATIC_DRAW);
                    this.gl.bindBuffer(this.gl.ARRAY_BUFFER,this.starBuffer);this.gl.bufferData(this.gl.ARRAY_BUFFER,this.mesh.stars,this.gl.STATIC_DRAW);
                    this.gl.bindBuffer(this.gl.ARRAY_BUFFER,this.surfaceBuffer);this.gl.bufferData(this.gl.ARRAY_BUFFER,this.mesh.surface,this.gl.STATIC_DRAW);
                    this.gl.bindBuffer(this.gl.ELEMENT_ARRAY_BUFFER,this.trianglesBuffer);this.gl.bufferData(this.gl.ELEMENT_ARRAY_BUFFER,this.mesh.triangles,this.gl.STATIC_DRAW);
                }
            }
        }
        activity(events,seq,now) {
            if(seq===this.seq)return;this.seq=seq;
            const fresh=(events||[]).filter(e=>Number.isFinite(e.seq)&&e.seq>this.eventCursor);
            if(fresh.length)this.eventCursor=Math.max(this.eventCursor,...fresh.map(e=>e.seq));
            const real=fresh.filter(e=>['running','completed','observed','guidance'].includes(e.phase));
            this.pulse=[real.some(e=>['memory','storage'].includes(e.module))?.8:0,
                        real.some(e=>['emotion','coalescence','personality_style'].includes(e.module))?.8:0,
                        real.some(e=>['model','understanding','decider'].includes(e.module))?.8:0];
            this.pulseAt=now;
        }
        resize(width,height,ratio) {
            this.width=width;this.height=height;this.ratio=ratio;
            this.canvas.width=Math.round(width*ratio);this.canvas.height=Math.round(height*ratio);
        }
        suspend(){this.suspended=true;this.lastTime=null;}
        clear() {
            this.suspend();this.mesh=null;this.data=null;this.key='';this.seq=-1;this.eventCursor=-1;
            if(this.gl&&!this.lost){this.gl.colorMask(true,true,true,true);this.gl.clear(this.gl.COLOR_BUFFER_BIT);}
            if(this.fallback)this.fallback.clearRect(0,0,this.canvas.width,this.canvas.height);
        }
        dispose() {
            this.suspend();if(this.gl&&!this.lost){this.gl.deleteBuffer(this.buffer);this.gl.deleteBuffer(this.edges);this.gl.deleteBuffer(this.surfaceBuffer);this.gl.deleteBuffer(this.trianglesBuffer);this.gl.deleteBuffer(this.starBuffer);this.gl.deleteProgram(this.program);}
            this.canvas.removeEventListener('webglcontextlost',this.contextLost);
            this.canvas.removeEventListener('webglcontextrestored',this.contextRestored);
            this.mesh=null;this.gl=null;this.fallback=null;
        }
        draw(now,motion=true) {
            if(!this.mesh||!this.width||this.lost||this.error)return false;
            const dt=this.lastTime===null?0:clamp((now-this.lastTime)/1000,0,.12);this.lastTime=now;
            if(motion)this.clock+=dt;this.suspended=false;
            const e=this.data.expression||{},target=[e.smile||0,e.attention||0,e.energy||0,e.concern||0];
            const blend=motion?1-Math.exp(-dt*1.8):1;
            this.expression=this.expression.map((v,i)=>v+(clamp(target[i],0,1)-v)*blend);
            const pulse=this.pulse.map(v=>v*Math.max(0,1-(now-this.pulseAt)/2200));
            const gl=this.gl;
            if(gl) {
                gl.viewport(0,0,this.canvas.width,this.canvas.height);gl.clearColor(0,0,0,0);gl.depthMask(true);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
                gl.useProgram(this.program);
                const attributes=buffer=>{gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
                    ['aPosition','aNormal','aRegion','aMaterial','aSize','aNoise','aFade'].forEach((name,i)=>{const a=this.attributes[name];if(a<0)return;gl.enableVertexAttribArray(a);gl.vertexAttribPointer(a,i<2?3:1,gl.FLOAT,false,44,[0,12,24,28,32,36,40][i]);});};
                gl.uniform2f(this.uniforms.Viewport,this.width,this.height);gl.uniform2f(this.uniforms.Camera,this.yaw,this.pitch);
                gl.uniform1f(this.uniforms.Time,this.clock);
                gl.uniform4fv(this.uniforms.Expression,this.expression);gl.uniform3fv(this.uniforms.Pulse,pulse);gl.uniform1f(this.uniforms.Ratio,this.ratio);
                gl.uniform1f(this.uniforms.Points,0);gl.uniform1f(this.uniforms.DepthBias,0);
                attributes(this.surfaceBuffer);gl.colorMask(false,false,false,false);
                gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,this.trianglesBuffer);gl.drawElements(gl.TRIANGLES,this.mesh.triangles.length,gl.UNSIGNED_SHORT,0);
                gl.colorMask(true,true,true,true);gl.depthMask(false);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);attributes(this.buffer);
                gl.uniform1f(this.uniforms.Points,2);
                gl.uniform1f(this.uniforms.DepthBias,.003);attributes(this.edges);gl.drawArrays(gl.LINES,0,this.mesh.threads.length/11);
                attributes(this.buffer);gl.uniform1f(this.uniforms.Points,1);gl.uniform1f(this.uniforms.DepthBias,.004);gl.drawArrays(gl.POINTS,0,this.mesh.count);
                // Optical glare is a small screen-space layer, with front-facing
                // anchors selected by the same view normals as the portrait.
                gl.disable(gl.DEPTH_TEST);attributes(this.starBuffer);gl.uniform1f(this.uniforms.Points,3);
                gl.drawArrays(gl.POINTS,0,this.mesh.stars.length/11);gl.enable(gl.DEPTH_TEST);
            } else if(this.fallback)this.drawFallback();
            return true;
        }
        drawFallback() {
            const c=this.fallback;c.setTransform(this.ratio,0,0,this.ratio,0,0);c.clearRect(0,0,this.width,this.height);
            const scale=Math.min(this.width*.39,this.height*.31),verts=this.mesh.vertices;
            const cy=Math.cos(this.yaw),sy=Math.sin(this.yaw),cp=Math.cos(this.pitch),sp=Math.sin(this.pitch);
            const flares=[];c.globalCompositeOperation='lighter';
            for(let i=0;i<verts.length;i+=11) {
                let x=verts[i],z=verts[i+2],y=verts[i+1];
                const wave=Math.sin(this.clock*.55+y*5+verts[i+9]*Math.PI*2)*.0026;
                x+=verts[i+3]*.0032+wave;y+=verts[i+4]*.0032+Math.sin(this.clock*.63)*.004;z+=verts[i+5]*.0032;
                const hair=verts[i+6]>5.5,front=clamp((z-.05)/.27,0,1),mouth=hair?0:gaussian(y+.34,.085)*gaussian(x,.25)*front;
                y+=mouth*(this.expression[0]*.035*Math.pow(Math.abs(x)/.20,1.3)-this.expression[3]*.008);
                y+=gaussian(y-.28,.06)*gaussian(Math.abs(x)-.223,.14)*front*this.expression[1]*.010;
                const xx=x*cy+z*sy,zz=-x*sy+z*cy,yy=y*cp-zz*sp,depth=y*sp+zz*cp;
                const nz0=-verts[i+3]*sy+verts[i+5]*cy,nz=verts[i+4]*sp+nz0*cp;
                if(nz<.015)continue;
                const rim=Math.pow(1-Math.abs(nz),4),perspective=4.2/(4.2-depth);
                const px=this.width/2+xx*scale*perspective,py=this.height/2-(yy-.04)*scale*perspective;
                const fade=verts[i+10]*clamp((y+1.14)/.17,0,1);
                c.globalAlpha=clamp(((hair?.045:.016)+rim*1.9)*fade,0,1);c.fillStyle='#fffefa';c.beginPath();
                c.arc(px,py,Math.max(.5,verts[i+8]*.9),0,Math.PI*2);c.fill();
                if(verts[i+9]>.996&&rim>.2&&flares.length<10){
                    const intensity=Math.pow(.5+.5*Math.sin(this.clock*.48+verts[i+9]*7919),5);
                    if(intensity>.15)flares.push([px,py,intensity*fade]);
                }
            }
            c.strokeStyle='#fffefa';c.lineWidth=.65;
            for(const [x,y,alpha] of flares){
                c.globalAlpha=alpha;c.beginPath();c.moveTo(x-10,y+7);c.lineTo(x+10,y-7);c.moveTo(x-4,y-6);c.lineTo(x+4,y+6);c.stroke();
            }
            c.globalAlpha=1;c.globalCompositeOperation='source-over';
        }
    }
    window.AllmaAvatar={Portrait,geometry};
})();
