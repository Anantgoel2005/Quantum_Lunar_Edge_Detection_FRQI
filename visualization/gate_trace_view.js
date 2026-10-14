/* Render and animate backend checkpoints; no quantum evolution is computed here. */
(() => {
  const root=document.getElementById('gate-trace-panel');
  if(!root)return;
  const q=name=>root.querySelector(`[data-trace="${name}"]`);
  const diagram=q('diagram'),stateSvg=q('state');
  let latest=null,current=null,frame=0,frames=[],paused=false,timer=null;
  let sequence=-1,runId=null,polling=false,playing=false,lastLabel='';
  const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  const text=(name,value)=>{q(name).textContent=value;};
  const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function circuitTitle(c){return `${c.metadata.direction==='horizontal'?'Horizontal':'Vertical'} · ${c.metadata.pair_offset?'shifted':'even'} pairs`;}
  function stageName(gate){
    if(!gate)return 'Initial |0…0⟩';
    if(gate.name==='initialize')return 'QPIE state preparation';
    if(gate.name==='measure')return 'Measurement counts returned';
    if(gate.name==='h')return `Hadamard interference on q${gate.target}`;
    const controls=gate.controls||[];
    return controls.length?`${controls.length===1?'CX':controls.length===2?'CCX':'MCX'} · ${controls.map(x=>'q'+x).join(', ')} → q${gate.target}`:`X on q${gate.target}`;
  }
  function drawDiagram(circuit,activeGate){
    const width=Math.max(diagram.clientWidth,280),n=circuit.qubits,height=32+n*29;
    const left=70,right=width-12,spacing=(right-left)/(circuit.gates.length+1);
    diagram.setAttribute('viewBox',`0 0 ${width} ${height}`);
    diagram.style.height=`${height}px`;
    let output='<title>Actual QHED circuit gates for the automatically processed image block</title>';
    for(let bit=0;bit<n;bit++){
      const y=20+bit*29;
      output+=`<text x="0" y="${y+4}">q${bit} ${bit<n/2?'col':'row'}</text><line x1="${left}" x2="${right}" y1="${y}" y2="${y}" stroke="var(--line)"/>`;
    }
    const cursorX=activeGate<0?left:left+(activeGate+1)*spacing;
    output+=`<rect x="${cursorX-17}" y="5" width="34" height="${n*29}" fill="var(--accent)" opacity=".10" rx="4"/>`;
    circuit.gates.forEach((gate,index)=>{
      const x=left+(index+1)*spacing,active=index===activeGate,fill=active?'var(--accent)':'var(--surface)',ink=active?'var(--gate-ink)':'var(--fg)';
      const title=escape(stageName(gate));
      output+=`<g data-gate-index="${index}" class="${active?'gate-active':''}"><title>${title}</title>`;
      if(gate.name==='initialize'){
        output+=`<rect x="${x-15}" y="7" width="30" height="${(n-1)*29+26}" rx="3" fill="${fill}"/><text x="${x}" y="${20+(n-1)*14.5}" text-anchor="middle" style="fill:${ink}">Init</text>`;
      }else if(gate.name==='measure'){
        for(const bit of gate.qubits){const y=20+bit*29;output+=`<rect x="${x-11}" y="${y-11}" width="22" height="22" rx="3" fill="${fill}"/><text x="${x}" y="${y+5}" text-anchor="middle" style="fill:${ink}">M</text>`;}
      }else{
        const y=20+gate.target*29,controls=gate.controls||[];
        if(controls.length){
          const min=Math.min(gate.target,...controls),max=Math.max(gate.target,...controls);
          output+=`<line x1="${x}" x2="${x}" y1="${20+min*29}" y2="${20+max*29}" stroke="var(--fg)"/>`;
          controls.forEach(bit=>{output+=`<circle cx="${x}" cy="${20+bit*29}" r="3.5" fill="var(--fg)"/>`;});
          output+=`<circle cx="${x}" cy="${y}" r="10" fill="${fill}" stroke="var(--fg)"/><path d="M${x-6} ${y}h12 M${x} ${y-6}v12" stroke="${ink}"/>`;
        }else{
          output+=`<rect x="${x-11}" y="${y-11}" width="22" height="22" rx="3" fill="${fill}"/><text x="${x}" y="${y+5}" text-anchor="middle" style="fill:${ink}">${gate.name==='h'?'H':'X'}</text>`;
        }
      }
      output+='</g>';
    });
    diagram.innerHTML=output;
    diagram.setAttribute('data-active-gate',activeGate);
    diagram.setAttribute('data-circuit-name',circuit.name);
  }
  function drawState(circuit,point,measurement){
    const count=1<<circuit.qubits,side=Math.sqrt(count),values=[],probabilities=[];
    if(measurement){
      for(let i=0;i<count;i++){
        const key=i.toString(2).padStart(circuit.qubits,'0'),p=(circuit.counts[key]||0)/circuit.shots;
        values.push(p);probabilities.push(p);
      }
      text('state-label','Observed measurement probabilities');
      text('norm',`Probability sum: ${probabilities.reduce((a,b)=>a+b,0).toFixed(6)}`);
      text('measurement',`${circuit.shots.toLocaleString()} actual shots · ${Object.keys(circuit.counts).length} observed states`);
    }else{
      for(let i=0;i<count;i++){values.push(point.real[i]);probabilities.push(point.real[i]**2+point.imag[i]**2);}
      text('state-label','Saved real amplitudes after this gate');
      text('norm',`State norm: ${point.norm.toFixed(6)}`);
      text('measurement','Statevector checkpoint from this inference circuit');
    }
    const maximum=Math.max(...values.map(Math.abs),1e-20),cell=16,size=side*cell;
    stateSvg.setAttribute('viewBox',`0 0 ${size} ${size}`);
    let markup='<title>Actual saved computational-basis state or measured outcome probabilities</title>';
    values.forEach((value,i)=>{
      const x=(i%side)*cell,y=Math.floor(i/side)*cell,opacity=Math.abs(value)/maximum;
      const key=i.toString(2).padStart(circuit.qubits,'0');
      const detail=measurement?`|${key}⟩: ${(circuit.counts[key]||0)} shots, p=${probabilities[i].toFixed(6)}`:`|${key}⟩: amplitude ${point.real[i].toFixed(6)} + ${point.imag[i].toFixed(6)}i, p=${probabilities[i].toFixed(6)}`;
      markup+=`<g><title>${escape(detail)}</title><rect x="${x}" y="${y}" width="15" height="15" fill="var(--surface)"/><rect x="${x}" y="${y}" width="15" height="15" fill="${!measurement&&value<0?'var(--negative)':'var(--accent)'}" opacity="${opacity}"/></g>`;
    });
    stateSvg.innerHTML=markup;
    stateSvg.setAttribute('data-display-mode',measurement?'measurements':'statevector');
    const candidates=probabilities.map((probability,index)=>({probability,index})).sort((a,b)=>b.probability-a.probability).slice(0,3);
    text('outcomes',candidates.map(item=>`|${item.index.toString(2).padStart(circuit.qubits,'0')}⟩ ${(100*item.probability).toFixed(1)}%`).join(' · '));
  }
  function display(item){
    if(!current||!item)return;
    const circuit=current.circuits[item.circuit],gate=circuit.gates[item.gate_index];
    text('pass',`${item.circuit+1}/4 · ${circuitTitle(circuit)}`);
    text('gate-label',stageName(gate));
    root.setAttribute('data-trace-run',current.run_id);root.setAttribute('data-trace-sequence',current.sequence);
    drawDiagram(circuit,item.gate_index);
    drawState(circuit,item.snapshot,item.measurement);
    const region=document.getElementById('active-block');
    if(region){region.setAttribute('x',current.tile_x);region.setAttribute('y',current.tile_y);region.setAttribute('width',Math.min(current.core_size,(current.image_width||512)-current.tile_x));region.setAttribute('height',Math.min(current.core_size,(current.image_height||512)-current.tile_y));region.style.display='block';}
    text('block',`Block (${current.tile_x}, ${current.tile_y}) · batch ${current.sequence} · ${current.circuits[0].qubits} qubits`);
    text('timing',`Backend batch: ${current.batch_execution_seconds.toFixed(2)} s · checkpoints arrived at ${current.completed_elapsed_seconds.toFixed(1)} s`);
    lastLabel=stageName(gate);
  }
  function stop(){clearTimeout(timer);timer=null;playing=false;}
  function next(){
    if(paused||!current){playing=false;return;}
    display(frames[frame]);frame++;
    if(frame<frames.length){
      const slow=root.classList.contains('trace-replaying');
      const interval=slow?450:Math.max(55,Math.min(180,current.batch_execution_seconds*1000/frames.length));
      timer=setTimeout(next,interval);
    }else{
      playing=false;root.classList.remove('trace-replaying');
      if(latest&&latest.sequence!==current.sequence){play(latest);}
    }
  }
  function play(packet,replay=false){
    if(!packet||!packet.circuits||!packet.circuits.length)return;
    stop();current=packet;frames=[];frame=0;
    packet.circuits.forEach((circuit,index)=>{
      circuit.snapshots.forEach(snapshot=>frames.push({circuit:index,gate_index:snapshot.gate_index,snapshot,measurement:false}));
      frames.push({circuit:index,gate_index:circuit.gates.length-1,measurement:true});
    });
    root.classList.toggle('trace-replaying',replay);
    text('source','Actual backend gate checkpoints · animated circuit playback');
    q('replay').disabled=false;q('pause').disabled=false;
    if(reduced&&!replay){display(frames[frames.length-1]);return;}
    playing=true;next();
  }
  async function poll(){
    if(location.protocol==='file:'||polling)return;
    polling=true;
    try{
      const response=await fetch(`/api/trace?after=${sequence}&run=${runId||''}`,{cache:'no-store'});
      if(!response.ok)throw Error('trace');
      const packet=await response.json();
      if(packet.waiting){return;}
      if(packet.run_id!==runId){stop();runId=packet.run_id;sequence=-1;current=null;latest=null;}
      if(packet.sequence===sequence)return;
      sequence=packet.sequence;latest=packet;
      if(!paused&&!playing)play(packet);
      text('incoming',`Latest received checkpoint batch ${sequence} · playback timing is independent of detector timing`);
    }catch(error){text('incoming','Waiting for the live gate trace');}
    finally{polling=false;}
  }
  q('pause').addEventListener('click',()=>{
    paused=!paused;q('pause').textContent=paused?'Resume animation':'Pause animation';
    if(paused){stop();text('source','Animation paused · detector progress is unaffected');}
    else if(latest)play(latest);
  });
  q('replay').addEventListener('click',()=>{paused=false;q('pause').textContent='Pause animation';play(latest,true);});
  function reset(){stop();latest=null;current=null;sequence=-1;runId=null;paused=false;diagram.replaceChildren();stateSvg.replaceChildren();document.getElementById('active-block').style.display='none';q('pause').disabled=true;q('replay').disabled=true;q('pause').textContent='Pause animation';text('source','Waiting for checkpoints from the new run');}
  window.addEventListener('quantum:reset-trace',reset);
  new ResizeObserver(()=>{if(current&&frames.length){const item=frames[Math.max(0,frame-1)];drawDiagram(current.circuits[item.circuit],item.gate_index);}}).observe(diagram);
  root.traceInspector={state:()=>({sequence,runId,paused,playing,frame,currentCircuit:current&&frames.length?current.circuits[frames[Math.max(0,frame-1)].circuit].name:null,gateLabel:lastLabel}),poll};
  poll();setInterval(poll,500);
})();

