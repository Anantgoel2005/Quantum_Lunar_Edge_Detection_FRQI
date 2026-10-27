/* Ideal statevector simulation. Basis labels use Qiskit's |q(n-1)...q0> order. */
(function(root) {
  'use strict';
  const presets = {
    bell: {name:'Bell pair', n:2, description:'Two qubits. One shared outcome. Watch entanglement form, then measure each qubit.', gates:[{type:'H',target:0},{type:'CX',control:0,target:1}]},
    ghz: {name:'GHZ state', n:3, description:'Extend a Bell pair to three qubits and explore their correlated measurements.', gates:[{type:'H',target:0},{type:'CX',control:0,target:1},{type:'CX',control:1,target:2}]},
    phase: {name:'Phase interference', n:1, description:'A rotation changes relative phase. A final Hadamard turns phase into measurable probability.', gates:[{type:'H',target:0},{type:'RZ',target:0,angle:Math.PI/2},{type:'H',target:0}]},
    qhed: {name:'QPIE edge detection', n:3, description:'A 2 × 4 image becomes eight amplitudes. Shift the column register, then interfere neighboring pixels with H(q0). This is the horizontal offset-1 pass from the project.', gates:[{type:'PREP',values:[0,0,1,1,0,0,1,1]},{type:'CX',control:0,target:1},{type:'X',target:0},{type:'H',target:0}]},
    teleport: {name:'Quantum teleportation', n:3, description:'Advanced · 15 operations. Transfer a complex state from Alice (q0) to Bob (q2) using an entangled pair, two classical bits, and conditional corrections. Finally, undo the original preparation on Bob: his verification bit must be 0.', gates:[
      {type:'RY',target:0,angle:Math.PI*0.7,note:'Prepare Alice’s message: choose an unequal superposition on q0.'},
      {type:'RZ',target:0,angle:Math.PI/3,note:'Add relative phase to Alice’s message. Both its probabilities and its phase must survive teleportation. Compare this q0 Bloch vector with q2 after step 10.'},
      {type:'H',target:1,note:'Create the shared resource: put q1 into superposition.'},
      {type:'CX',control:1,target:2,note:'Entangle q1 and q2 into a Bell pair. Alice holds q0 and q1; Bob holds q2.'},
      {type:'CX',control:0,target:1,note:'Start Alice’s Bell-basis transformation: couple the message q0 to her half of the entangled pair.'},
      {type:'H',target:0,note:'Complete the Bell-basis transformation. Alice can now measure q0 and q1 in the ordinary computational basis.'},
      {type:'M',target:0,note:'Alice records the first classical message bit c0. It will decide whether Bob needs a Z correction.'},
      {type:'M',target:1,note:'Alice records c1. Bob’s qubit is now pure, but it may need X and Z corrections. The two classical bits are needed to recover the original state.'},
      {type:'X',target:2,condition:1,note:'Classical feed-forward: apply X to Bob only if Alice measured c1 = 1.'},
      {type:'Z',target:2,condition:0,note:'Apply Z only if c0 = 1. Teleportation is complete: q2 now has exactly the Bloch vector Alice’s q0 had after step 2. Alice’s original state has been measured.'},
      {type:'RZ',target:2,angle:-Math.PI/3,note:'Verification, part 1: undo the original relative-phase rotation on Bob’s received state.'},
      {type:'RY',target:2,angle:-Math.PI*0.7,note:'Verification, part 2: undo the original superposition rotation. Bob must now be in |0⟩. His final measurement is deterministically 0, for all four of Alice’s outcomes.'}
    ]}
  };
  function validate(n,gates) {
    if(!Number.isInteger(n)||n<1||n>6) throw Error('Choose between 1 and 6 qubits.');
    for(const g of gates) {
      if(!['H','X','Y','Z','S','T','RX','RY','RZ','CX','CZ','M','PREP'].includes(g.type)) throw Error('Unsupported gate.');
      if(g.type==='PREP') {
        if(!Array.isArray(g.values)||g.values.length!==2**n||g.values.some(x=>!Number.isFinite(x))||!g.values.some(x=>x!==0)) throw Error('Preparation needs a nonzero finite amplitude vector.');
        continue;
      }
      if(!Number.isInteger(g.target)||g.target<0||g.target>=n) throw Error('Target is outside the register.');
      if(g.condition!==undefined&&(!['X','Z'].includes(g.type)||!Number.isInteger(g.condition)||g.condition<0||g.condition>=n)) throw Error('A classical condition needs a valid bit and an X or Z correction.');
      if(['CX','CZ'].includes(g.type)&&(!Number.isInteger(g.control)||g.control<0||g.control>=n||g.control===g.target)) throw Error('Control and target must be different qubits.');
      if(['RX','RY','RZ'].includes(g.type)&&!Number.isFinite(g.angle)) throw Error('Rotation angle must be finite.');
    }
  }
  function matrix(type,a=0) {
    const h=Math.SQRT1_2,c=Math.cos(a/2),s=Math.sin(a/2),z=[0,0],one=[1,0];
    return {H:[[h,0],[h,0],[h,0],[-h,0]], X:[z,one,one,z],Y:[z,[0,-1],[0,1],z],Z:[one,z,z,[-1,0]],S:[one,z,z,[0,1]],T:[one,z,z,[Math.SQRT1_2,Math.SQRT1_2]],RX:[[c,0],[0,-s],[0,-s],[c,0]],RY:[[c,0],[-s,0],[s,0],[c,0]],RZ:[[c,-s],z,z,[c,s]],CX:[z,one,one,z],CZ:[one,z,z,[-1,0]]}[type];
  }
  function apply(re,im,g) {
    const m=matrix(g.type,g.angle),mask=1<<g.target;
    for(let i=0;i<re.length;i++) if(!(i&mask)&&(!g.type.startsWith('C')||(i&(1<<g.control)))) {
      const j=i|mask,ar=re[i],ai=im[i],br=re[j],bi=im[j];
      re[i]=m[0][0]*ar-m[0][1]*ai+m[1][0]*br-m[1][1]*bi;
      im[i]=m[0][0]*ai+m[0][1]*ar+m[1][0]*bi+m[1][1]*br;
      re[j]=m[2][0]*ar-m[2][1]*ai+m[3][0]*br-m[3][1]*bi;
      im[j]=m[2][0]*ai+m[2][1]*ar+m[3][0]*bi+m[3][1]*br;
    }
  }
  function shot(n,gates,random=Math.random) {
    validate(n,gates);
    let re=Array(2**n).fill(0),im=Array(2**n).fill(0),bits=Array(n).fill(null),frames=[];
    re[0]=1;
    const save=(gate,event=null)=>frames.push({gate,event,re:[...re],im:[...im],bits:[...bits]});
    save(null);
    gates.forEach(g=>{
      let event=null;
      if(g.condition!==undefined){
        if(bits[g.condition]===null)throw Error('Measure the classical control bit before using it.');
        event={condition:g.condition,bit:bits[g.condition],applied:bits[g.condition]===1};
        if(event.applied)apply(re,im,g);
        save({...g},event);return;
      }
      if(g.type==='PREP') {const norm=Math.hypot(...g.values);re=g.values.map(v=>v/norm);im.fill(0);}
      else if(g.type==='M') {
        let p1=0;re.forEach((r,i)=>{if(i&(1<<g.target))p1+=r*r+im[i]*im[i];});
        p1=Math.max(0,Math.min(1,p1));
        const draw=random(),value=p1>=1-1e-14?1:p1<=1e-14?0:draw<p1?1:0;
        const probability=value?p1:1-p1,scale=1/Math.sqrt(probability);
        re=re.map((r,i)=>Boolean(i&(1<<g.target))===Boolean(value)?r*scale:0);
        im=im.map((v,i)=>Boolean(i&(1<<g.target))===Boolean(value)?v*scale:0);
        bits[g.target]=value;event={value,probability,draw,target:g.target};
      } else apply(re,im,g);
      save({...g},event);
    });
    return frames;
  }
  function reduced(frame,q) {
    let p0=0,p1=0,x=0,y=0;const mask=1<<q;
    frame.re.forEach((r,i)=>{const p=r*r+frame.im[i]**2;if(i&mask)p1+=p;else {p0+=p;const j=i|mask;x+=2*(r*frame.re[j]+frame.im[i]*frame.im[j]);y+=2*(r*frame.im[j]-frame.im[i]*frame.re[j]);}});
    return {p0,p1,x,y,z:p0-p1,purity:(1+x*x+y*y+(p0-p1)**2)/2};
  }
  const api={presets,validate,shot,reduced};
  if(typeof module!=='undefined') module.exports=api;else root.QuantumSim=api;
})(typeof window==='undefined'?globalThis:window);
