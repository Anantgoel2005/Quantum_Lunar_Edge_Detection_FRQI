const assert=require('node:assert/strict');
const {test}=require('node:test');
const sim=require('./simulator.js');
const close=(a,b)=>assert.ok(Math.abs(a-b)<1e-10,`${a} != ${b}`);
const end=(n,gates,r=()=>0.25)=>sim.shot(n,gates,r).at(-1);
test('Bell creation and sequential measurement preserve correlations in both branches',()=>{
  for(const draw of [0.1,0.9]){
    const f=sim.shot(2,[...sim.presets.bell.gates,{type:'M',target:0},{type:'M',target:1}],()=>draw);
    close(f[1].re[0],Math.SQRT1_2);close(f[1].re[1],Math.SQRT1_2);
    close(f[2].re[0],Math.SQRT1_2);close(f[2].re[3],Math.SQRT1_2);
    close(sim.reduced(f[2],0).purity,0.5);
    close(f[3].event.probability,0.5);close(f[4].event.probability,1);
    assert.deepEqual(f[4].bits,draw<0.5?[1,1]:[0,0]);
    close(sim.reduced(f[3],1).purity,1);
    f.forEach(s=>close(s.re.reduce((sum,r,i)=>sum+r*r+s.im[i]**2,0),1));
  }
});
test('complex phases, rotations and Bloch axes follow standard convention',()=>{
  const h={type:'H',target:0};
  const y=end(1,[{type:'Y',target:0}]);close(y.im[1],1);
  const s=end(1,[h,{type:'S',target:0}]);close(sim.reduced(s,0).y,1);
  const rx=end(1,[{type:'RX',target:0,angle:Math.PI/2}]);close(sim.reduced(rx,0).y,-1);
  const ry=end(1,[{type:'RY',target:0,angle:Math.PI/2}]);close(sim.reduced(ry,0).x,1);
  const rz=end(1,[h,{type:'RZ',target:0,angle:Math.PI/2}]);close(sim.reduced(rz,0).y,1);
  const phase=end(1,sim.presets.phase.gates);close(phase.re[0]**2+phase.im[0]**2,0.5);
});
test('gate inverses restore arbitrary complex state',()=>{
  const base=[{type:'H',target:0},{type:'T',target:0},{type:'RY',target:1,angle:.82}],initial=end(2,base);
  for(const type of ['H','X','Y','Z','CX','CZ','RX','RY','RZ']){
    const g={type,target:0,...(type.startsWith('C')?{control:1}:{}),...(['RX','RY','RZ'].includes(type)?{angle:1.37}:{})};
    const inv={...g,...(g.angle?{angle:-g.angle}:{})},f=end(2,[...base,g,inv]);
    f.re.forEach((r,i)=>{close(r,initial.re[i]);close(f.im[i],initial.im[i]);});
  }
  const t=end(1,[{type:'H',target:0},...Array.from({length:8},()=>({type:'T',target:0}))]);close(t.re[1],Math.SQRT1_2);close(t.im[1],0);
});
test('intermediate measurements allow subsequent gates and new measurements',()=>{
  const f=sim.shot(1,[{type:'H',target:0},{type:'M',target:0},{type:'X',target:0},{type:'M',target:0}],()=>0.1);
  assert.equal(f[2].bits[0],1);assert.equal(f[3].bits[0],1);close(f[3].re[0],1);assert.equal(f[4].bits[0],0);
  const before=JSON.stringify(f);sim.shot(1,[{type:'H',target:0},{type:'M',target:0}],()=>0.9);assert.equal(JSON.stringify(f),before);
});
test('GHZ shots sample only 000 and 111 with expected frequencies',()=>{
  let seed=8171,ones=0;const rand=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/2**32;};
  for(let i=0;i<4096;i++){
    const f=end(3,[...sim.presets.ghz.gates,...[0,1,2].map(target=>({type:'M',target}))],rand);
    assert.ok(f.bits.every(b=>b===f.bits[0]));ones+=f.bits[0];
  }assert.ok(ones>1900&&ones<2200,`${ones} ones`);
});
test('unshifted horizontal and vertical passes match existing Qiskit amplitude fixtures',()=>{
  const fixtures=require('../qiskit-fixtures.json').filter(f=>f.pass===0||f.pass===2);assert.ok(fixtures.length>=4);
  for(const fixture of fixtures){const f=end(6,[{type:'PREP',values:fixture.pixels},{type:'H',target:fixture.pass===0?0:3}]);f.re.forEach((r,i)=>{close(r,fixture.amplitudes[i]);close(f.im[i],0);});}
});
test('QPIE shifted-pair demo matches direct permutation and neighbor interference',()=>{
  const p=sim.presets.qhed,f=end(p.n,p.gates),v=p.gates[0].values,norm=Math.hypot(...v),shifted=Array(8).fill(0);
  v.forEach((x,i)=>shifted[(i&4)|((i+1)&3)]=x/norm);
  for(let i=0;i<8;i+=2){close(f.re[i],(shifted[i]+shifted[i+1])*Math.SQRT1_2);close(f.re[i+1],(shifted[i]-shifted[i+1])*Math.SQRT1_2);}
});
test('invalid circuits reject instead of silently producing invalid states',()=>{
  for(const [n,g] of [[0,[]],[7,[]],[2,[{type:'CX',target:0,control:0}]],[1,[{type:'H',target:1}]],[1,[{type:'RZ',target:0,angle:NaN}]],[1,[{type:'PREP',values:[0,0]}]]])assert.throws(()=>sim.shot(n,g));
});
test('teleportation recovers the complete complex state in all four measurement branches',()=>{
  const p=sim.presets.teleport;
  for(const c0 of [0,1])for(const c1 of [0,1]){
    const draws=[c0?0.1:0.9,c1?0.1:0.9];
    const frames=sim.shot(p.n,p.gates,()=>draws.shift());
    const source=sim.reduced(frames[2],0),receiver=sim.reduced(frames[10],2);
    for(const axis of ['x','y','z','purity'])close(source[axis],receiver[axis]);
    assert.deepEqual(frames[8].bits,[c0,c1,null]);
    close(frames[7].event.probability,0.5);close(frames[8].event.probability,0.5);
    assert.equal(frames[9].event.applied,c1===1);assert.equal(frames[10].event.applied,c0===1);
    close(sim.reduced(frames[12],2).p0,1);
    frames.forEach(f=>close(f.re.reduce((s,r,i)=>s+r*r+f.im[i]**2,0),1));
  }
});
test('teleportation verification always reads zero on the receiver',()=>{
  const p=sim.presets.teleport;
  for(let i=0;i<256;i++){
    const f=end(p.n,[...p.gates,...[0,1,2].map(target=>({type:'M',target}))],Math.random);
    assert.equal(f.bits[2],0);
  }
  assert.throws(()=>sim.shot(2,[{type:'X',target:1,condition:0}]),/Measure/);
  assert.throws(()=>sim.shot(2,[{type:'X',target:1,condition:3}]),/valid bit/);
});
