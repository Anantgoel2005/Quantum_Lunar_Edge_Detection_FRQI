(() => {
  'use strict';
  const $=id=>document.getElementById(id),sim=QuantumSim;
  let n=2,gates=[],frames=[],step=0,shotNumber=1,preset='bell',counts={},counted=false,timer=null;
  const bits=i=>i.toString(2).padStart(n,'0'),pct=p=>`${(p*100).toFixed(1)}%`;
  const pretty=x=>(Math.abs(x)<1e-9?0:x).toFixed(3);
  const gateName=g=>g.type==='PREP'?'Prepare':g.type==='M'?`Measure q${g.target}`:`${g.type}${g.angle!==undefined?`(${(g.angle/Math.PI).toFixed(2)}π)`:''} · q${g.target}${g.control!==undefined?` ← q${g.control}`:''}${g.condition!==undefined?` if c${g.condition}=1`:''}`;
  function notify(message){$('status').textContent=message;$('status').classList.add('visible');clearTimeout(notify.timeout);notify.timeout=setTimeout(()=>$('status').classList.remove('visible'),3500);}
  function pause(){if(timer)clearInterval(timer);timer=null;$('play').textContent='▶ Play shot';}
  function sequence(){return [...gates,...Array.from({length:n},(_,target)=>({type:'M',target,terminal:true}))];}
  function makeShot(){pause();frames=sim.shot(n,sequence());step=0;counted=false;$('step').max=frames.length-1;render();}
  function resetExperiment(){counts={};shotNumber=1;makeShot();}
  function loadPreset(key){preset=key;const p=sim.presets[key];n=p.n;gates=structuredClone(p.gates);$('qubits').value=n;updateTargets();resetExperiment();}
  function updateTargets(){for(const id of ['target','control']){$(id).replaceChildren(...Array.from({length:n},(_,i)=>new Option(`q${i}`,i)));}if(n>1)$('control').value=1;}
  function move(next){step=Math.max(0,Math.min(frames.length-1,next));if(step===frames.length-1&&!counted){const key=[...frames[step].bits].reverse().join('');counts[key]=(counts[key]||0)+1;counted=true;}if(step===frames.length-1)pause();render();}
  function play(){if(timer){pause();return;}if(step===frames.length-1)move(0);$('play').textContent='Ⅱ Pause';timer=setInterval(()=>move(step+1),Number($('speed').value));}
  function drawCircuit(){
    const seq=sequence(),spacing=76,left=80,width=Math.max(540,left+seq.length*spacing+35),height=65+n*62;
    let svg=`<rect x="${left+step*spacing-spacing/2}" y="12" width="${spacing}" height="${height-27}" rx="9" fill="#eef5e9"/><text x="${left}" y="21" text-anchor="middle" font-size="8" fill="#7e9577">INIT</text>`;
    for(let q=0;q<n;q++){const y=52+q*62;svg+=`<text x="4" y="${y+4}" font-size="12" fill="#4d6c59">q${q}</text><text x="34" y="${y+4}" font-size="11" fill="#94a88f">|0⟩</text><line x1="60" y1="${y}" x2="${width-18}" y2="${y}" stroke="#cbd9c6"/>`;}
    seq.forEach((g,i)=>{
      const x=left+(i+1)*spacing,y=52+(g.target||0)*62,active=step===i+1,fill=active?'#2e654b':g.type==='M'?'#fcf5e8':'#eff6ed',stroke=active?'#2e654b':g.type==='M'?'#e8d7b6':'#c8ddc7',ink=active?'white':'#47694b';
      svg+=`<g class="gate-box" data-index="${i+1}"><title>Step ${i+1}: ${gateName(g)}</title><text x="${x}" y="21" text-anchor="middle" font-size="8" fill="#8a9c83">${String(i+1).padStart(2,'0')}</text>`;
      if(g.type==='PREP')svg+=`<rect x="${x-22}" y="33" width="44" height="${(n-1)*62+38}" rx="5" fill="${fill}" stroke="${stroke}"/><text x="${x}" y="${52+(n-1)*31}" text-anchor="middle" fill="${ink}" font-size="10" transform="rotate(-90 ${x} ${52+(n-1)*31})">QPIE</text>`;
      else {
        if(g.control!==undefined){const cy=52+g.control*62;svg+=`<line x1="${x}" y1="${cy}" x2="${x}" y2="${y}" stroke="#5f875e" stroke-width="1.5"/><circle cx="${x}" cy="${cy}" r="4" fill="#5f875e"/>`;}
        if(g.condition!==undefined){const cy=52+g.condition*62;svg+=`<line x1="${x-2}" y1="${cy}" x2="${x-2}" y2="${y-20}" stroke="#ac8c52" stroke-dasharray="3 3"/><line x1="${x+2}" y1="${cy}" x2="${x+2}" y2="${y-20}" stroke="#ac8c52" stroke-dasharray="3 3"/><text x="${x}" y="${cy-8}" text-anchor="middle" fill="#9a7d49" font-size="8">c${g.condition}=1</text>`;}
        svg+=`<rect x="${x-19}" y="${y-19}" width="38" height="38" rx="6" fill="${fill}" stroke="${stroke}"/><text x="${x}" y="${y+5}" text-anchor="middle" fill="${ink}" font-size="${g.type.length>1?11:15}">${g.type==='CX'?'⊕':g.type==='CZ'?'Z':g.type==='M'?'↗':g.type}</text>`;
        if(g.angle!==undefined)svg+=`<text x="${x}" y="${y+31}" text-anchor="middle" font-size="8" fill="#83957c">${(g.angle/Math.PI).toFixed(2)}π</text>`;
        if(g.type==='M'&&step>=i+1){const event=frames[i+1].event;svg+=`<text x="${x}" y="${y+32}" text-anchor="middle" fill="#6b855b" font-size="10">c${g.target}=${event.value}</text>`;}
        if(g.condition!==undefined&&step>=i+1)svg+=`<text x="${x}" y="${y+32}" text-anchor="middle" fill="#9a7d49" font-size="8">${frames[i+1].event.applied?'APPLIED':'SKIPPED'}</text>`;
      }svg+='</g>';
    });
    $('circuit').setAttribute('viewBox',`0 0 ${width} ${height}`);$('circuit').style.width=`${width}px`;$('circuit').setAttribute('height',height);$('circuit').innerHTML=svg;
    const scroller=$('circuit').parentElement;
    if(scroller.scrollWidth>scroller.clientWidth)scroller.scrollLeft=Math.max(0,left+step*spacing-scroller.clientWidth/2);
    $('circuit').querySelectorAll('[data-index]').forEach(el=>el.addEventListener('click',()=>{pause();move(Number(el.dataset.index));}));
  }
  function describe(f){
    const g=f.gate;
    $('stage-label').textContent=!g?'INITIAL STATE':g.type==='M'?'MEASUREMENT & COLLAPSE':g.condition!==undefined?'CLASSICAL FEED-FORWARD':`GATE ${step} / ${frames.length-1}`;
    $('step-icon').textContent=!g?'ψ':g.type==='M'?f.event.value:g.type==='PREP'?'ψ':g.type;
    $('step-title').textContent=!g?`Everything begins at |${'0'.repeat(n)}⟩`:gateName(g);
    let text='Every qubit starts in |0⟩. The register has one nonzero amplitude and no uncertainty.';
    if(g){const t=`q${g.target}`;text=({H:`Hadamard mixes the |0⟩ and |1⟩ amplitudes of ${t}. Their signs and phases determine whether they reinforce or cancel.`,X:`X swaps the |0⟩ and |1⟩ amplitudes of ${t}: a quantum bit flip.`,Y:`Y flips ${t} and adds opposite complex phases to its two basis states.`,Z:`Z adds a phase of π to the |1⟩ component of ${t}. Probabilities do not change yet.`,S:`S rotates the |1⟩ component of ${t} by π/2.`,T:`T rotates the |1⟩ component of ${t} by π/4.`,CX:`Flip ${t} only where q${g.control} is |1⟩. With a superposed control, this can create entanglement.`,CZ:`Add a phase of π only where q${g.control} and ${t} are both |1⟩.`,RX:`Rotate ${t} around the Bloch sphere’s X axis by ${(g.angle/Math.PI).toFixed(2)}π.`,RY:`Rotate ${t} around the Bloch sphere’s Y axis by ${(g.angle/Math.PI).toFixed(2)}π.`,RZ:`Rotate the relative phase of ${t} around Z by ${(g.angle/Math.PI).toFixed(2)}π.`,PREP:'Normalize the image [0, 0, 1, 1; 0, 0, 1, 1] and encode its intensities as real amplitudes. Preparation is shown as one block, as in the project.',M:`${t} returned ${f.event?.value}. This branch had ${pct(f.event?.probability||0)} probability immediately before measurement. The incompatible amplitudes are removed and the remaining state is normalized.`})[g.type];}
    if(g?.note)text+=` ${g.note}`;
    if(g?.condition!==undefined)text=`c${g.condition} = ${f.event.bit}: ${f.event.applied?'correction applied':'correction skipped; quantum state unchanged'}. ${g.note||''}`;
    $('step-explanation').textContent=text;
  }
  function drawState(f){
    const norm=f.re.reduce((s,r,i)=>s+r*r+f.im[i]**2,0);$('norm').textContent=`Σp = ${norm.toFixed(3)}`;
    $('amplitudes').innerHTML=f.re.map((r,i)=>{const im=f.im[i],p=r*r+im*im,phase=p<1e-16?0:Math.atan2(im,r),hue=(155+phase/Math.PI*180+360)%360;
      return `<div class="amplitude" tabindex="0" aria-label="Basis ${bits(i)}, probability ${pct(p)}, amplitude ${pretty(r)} plus ${pretty(im)} i" title="|${bits(i)}⟩\nα = ${pretty(r)} ${im<0?'−':'+'} ${pretty(Math.abs(im))}i\nP = ${pct(p)}\nPhase = ${pretty(phase/Math.PI)}π"><div class="bar-slot"><div class="bar" style="height:${p*100}%;background:hsl(${hue},30%,57%)"><span class="bar-value">${p>.0005?pct(p):'0'}</span></div></div><div class="basis">|${bits(i)}⟩</div><div class="phase-dial" style="--phase:${-phase}rad;opacity:${p>1e-12?1:.25}"></div></div>`;}).join('');
    $('qubit-states').innerHTML=Array.from({length:n},(_,q)=>{const r=sim.reduced(f,q),vx=35+r.x*24-r.y*10,vy=35-r.z*24+r.y*8,len=Math.hypot(r.x,r.y,r.z),mixed=r.purity<1-1e-8;
      return `<div class="qubit-card"><svg class="bloch" viewBox="0 0 70 70" role="img" aria-label="q${q} Bloch vector length ${pretty(len)}"><circle cx="35" cy="35" r="25" fill="#f5f8f0" stroke="#d8e3cf"/><ellipse cx="35" cy="35" rx="25" ry="8" fill="none" stroke="#d6e2ce"/><ellipse cx="35" cy="35" rx="9" ry="25" fill="none" stroke="#e0e8d9"/><path d="M35 7V63 M8 35H62" stroke="#cfdcc5" stroke-dasharray="2 3"/><text x="39" y="10" font-size="7" fill="#8da080">0</text><text x="39" y="67" font-size="7" fill="#8da080">1</text><line x1="35" y1="35" x2="${vx}" y2="${vy}" stroke="#58845a" stroke-width="2"/><circle cx="${vx}" cy="${vy}" r="3" fill="#58845a"/></svg><div class="qubit-details"><div class="qubit-title">q${q}<span class="qubit-kind">${mixed?'MIXED':'PURE'}</span></div><div class="qubit-prob"><span>0 · ${pct(r.p0)}</span><span>1 · ${pct(r.p1)}</span></div><div class="prob-track"><i style="width:${r.p0*100}%"></i></div><div class="qubit-coordinates">x ${pretty(r.x)} · y ${pretty(r.y)} · z ${pretty(r.z)}</div></div></div>`;}).join('');
    $('classical').innerHTML=[...f.bits].reverse().map((b,i)=>`<div class="classical-bit">${b===null?'–':b}<small>c${n-1-i}</small></div>`).join('');
    $('measurement-note').textContent=f.bits.every(b=>b===null)?'No measurement yet. Gates change the quantum state; classical bits stay unset.':f.bits.every(b=>b!==null)?`Recorded bits: ${[...f.bits].reverse().join('')}. Later gates may still change the quantum state.`:'Partial readout. Unmeasured bits remain unset.';
  }
  function drawHistogram(){const total=Object.values(counts).reduce((a,b)=>a+b,0);$('total').textContent=total;$('histogram').innerHTML=total?Object.entries(counts).sort((a,b)=>b[1]-a[1]).map(([key,count])=>`<div class="hist-row"><span>${key}</span><div class="hist-track"><i style="width:${100*count/total}%"></i></div><span class="hist-count">${count} · ${Math.round(100*count/total)}%</span></div>`).join(''):'<div class="empty-hist">Finish a shot to collect its outcome.</div>';}
  function render(){
    $('step').value=step;$('step-label').textContent=`STEP ${String(step).padStart(2,'0')} / ${frames.length-1}`;$('shot-number').textContent=`SHOT ${String(shotNumber).padStart(3,'0')}`;$('back').disabled=step===0;$('next').disabled=step===frames.length-1;$('undo').disabled=!gates.length;
    $('circuit-name').textContent=preset?sim.presets[preset].name:'Your circuit';$('description').textContent=preset?sim.presets[preset].description:'An ideal quantum register, your gates, and a final measurement of every qubit.';$('gate-count').textContent=`${n} QUBITS / ${sequence().length} OPERATIONS`;
    document.querySelectorAll('.preset').forEach(b=>b.classList.toggle('active',b.dataset.preset===preset));drawCircuit();describe(frames[step]);drawState(frames[step]);drawHistogram();
  }
  const icons={bell:'⟷',ghz:'⋈',phase:'◌',qhed:'▦',teleport:'⇢'},subtitles={bell:'Superposition → entanglement',ghz:'Three-qubit correlation',phase:'From phase to probability',qhed:'From the original project',teleport:'Advanced · classical feed-forward'};
  $('presets').innerHTML=Object.entries(sim.presets).map(([key,p])=>`<button class="preset" data-preset="${key}"><span class="preset-icon">${icons[key]}</span><span>${p.name}<small>${subtitles[key]}</small></span><span class="arrow">›</span></button>`).join('');
  document.querySelectorAll('.preset').forEach(b=>b.addEventListener('click',()=>loadPreset(b.dataset.preset)));
  $('qubits').addEventListener('change',()=>{const next=Number($('qubits').value);gates=gates.filter(g=>g.type!=='PREP'&&g.target<next&&(g.control===undefined||g.control<next)&&(g.condition===undefined||g.condition<next));n=next;preset=null;updateTargets();resetExperiment();notify('Register resized. Gates outside the register were removed.');});
  $('gate').addEventListener('change',()=>{$('control-field').hidden=!['CX','CZ'].includes($('gate').value);$('angle-field').hidden=!['RX','RY','RZ'].includes($('gate').value);});
  $('add').addEventListener('click',()=>{const type=$('gate').value,g={type,target:Number($('target').value)};if(['CX','CZ'].includes(type))g.control=Number($('control').value);if(['RX','RY','RZ'].includes(type))g.angle=Number($('angle').value)*Math.PI;try{sim.validate(n,[g]);gates.push(g);preset=null;resetExperiment();}catch(e){notify(e.message);}});
  $('undo').addEventListener('click',()=>{gates.pop();preset=null;resetExperiment();});
  $('reset').addEventListener('click',()=>{pause();move(0);});$('back').addEventListener('click',()=>{pause();move(step-1);});$('next').addEventListener('click',()=>{pause();move(step+1);});$('play').addEventListener('click',play);$('speed').addEventListener('change',()=>{if(timer){pause();play();}});$('step').addEventListener('input',()=>{pause();move(Number($('step').value));});
  $('new-shot').addEventListener('click',()=>{shotNumber++;makeShot();});$('clear').addEventListener('click',()=>{counts={};drawHistogram();});
  $('sample').addEventListener('click',()=>{pause();for(let i=0;i<256;i++){const f=sim.shot(n,sequence()).at(-1),key=[...f.bits].reverse().join('');counts[key]=(counts[key]||0)+1;}drawHistogram();notify('256 independent shots added. The inspected shot is preserved.');});
  $('export').addEventListener('click',()=>{const blob=new Blob([JSON.stringify({format:'quantum-studio-shot-v1',simulator:'ideal statevector',bit_order:'q(n-1)...q0',qubits:n,shot:shotNumber,operations:sequence(),frames,displayed_step:step,completed_counts:counts},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`quantum-shot-${shotNumber}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notify('Shot exported with all gate checkpoints and sampled outcomes.');});
  document.addEventListener('keydown',e=>{if(['INPUT','SELECT','TEXTAREA','BUTTON','A'].includes(document.activeElement.tagName))return;if(e.key==='ArrowRight'){e.preventDefault();pause();move(step+1);}if(e.key==='ArrowLeft'){e.preventDefault();pause();move(step-1);}if(e.code==='Space'){e.preventDefault();play();}});
  const requestedPreset=new URLSearchParams(location.search).get('preset');
  loadPreset(Object.hasOwn(sim.presets,requestedPreset)?requestedPreset:'bell');
})();
