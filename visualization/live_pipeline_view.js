/* Upload preprocessing completes before the existing measured QHED runner starts. */
(() => {
 const get=id=>document.getElementById(id),run=get('run'),upload=get('upload'),send=get('upload-run'),label=get('status');
 let previous=null,pending=false,context={kind:'sombench',metrics_available:true},active=false;
 const reset=()=>window.dispatchEvent(new Event('quantum:reset-trace'));
 const image=(id,path)=>{get(id).src=`${path}?t=${Date.now()}`;};
 function controls(){run.disabled=pending||active;upload.disabled=pending||active;send.disabled=pending||active;}
 function applyContext(c){
  context=c;const custom=c.kind==='upload',shape=c.image_shape;
  get('context-label').textContent=custom?`${c.name} · full working image ${shape[1]} × ${shape[0]}`:'SomBench metadata row 0 · M1290203799CE_r5872_c1112 · complete 512 × 512 tile';
  get('preprocessing').hidden=!custom;get('benchmark').hidden=!c.metrics_available;get('dataset-credit').hidden=custom;
  get('source-caption').textContent=custom?'Preprocessed quantum input':'Original grayscale image · mean of five TIFF bands';
  get('overlay-caption').textContent=custom?'Measured quantum edges · magenta':'Catalog reference: green · measured edges: magenta · overlap: yellow';
  document.querySelector('.block-overlay').setAttribute('viewBox',`0 0 ${shape[1]} ${shape[0]}`);
  if(custom){image('source-preview','input.png');image('live','live_strength.png');}
  if(custom){
   const p=c.preprocessing;
   get('preprocessing-note').textContent=`${p.original_size.join(' × ')} → ${p.working_size.join(' × ')} pixels. Orientation correction, white transparency background, grayscale, 2–98 percentile contrast normalization, and Gaussian noise reduction (σ = 0.8).`;
   image('original-preview','original.png');image('prepared-preview','preprocessed.png');
  }
 }
 async function update(){
  if(pending)return;
  if(location.protocol==='file:'){run.disabled=true;send.disabled=true;label.textContent='Start the local server to upload or rerun';return;}
  try{
   const response=await fetch('/api/status',{cache:'no-store'});if(!response.ok)throw Error('status');
   const s=await response.json();active=['queued','running','finishing'].includes(s.status);controls();
   run.textContent=active?'Quantum circuits are running…':'Run quantum detection on the full image';
   label.textContent=s.status==='running'?`${s.completed_tiles} / ${s.total_tiles} blocks completed`:s.status==='failed'?'Run failed · see run.log':s.status==='queued'?'Starting Qiskit circuits':s.status==='finishing'?'Saving measured results':s.status==='preprocessed'?'Preprocessing complete · ready to run':s.status==='complete'?'Complete':'Ready';
   get('circuits').textContent=`${(s.circuits_executed||0).toLocaleString()} circuits`;
   get('shots').textContent=`${(s.measurement_shots||0).toLocaleString()} shots`;
   get('elapsed').textContent=`${(s.elapsed_seconds||0).toFixed(1)} s`;
   const percentage=s.status==='complete'?100:s.total_tiles?100*s.completed_tiles/s.total_tiles:0;
   get('bar').style.width=`${percentage}%`;document.querySelector('.progress').setAttribute('aria-valuenow',percentage.toFixed(0));
   get('finished').hidden=s.status!=='complete';
   if(s.status==='running'||previous!==s.status&&s.status==='complete')image('live','live_strength.png');
   if(s.status==='running'&&previous!=='running')image('source-preview','input.png');
   if(previous!==s.status&&s.status==='complete'){
    image('source-preview','input.png');
    image('edges','quantum_edges.png');image('overlay','overlay.png');
    for(const name of ['quantum','sobel','canny','robinson'])image(`compare-${name}`,`${name}_edges.png`);
    const comparisonResponse=await fetch('detector_comparison.json',{cache:'no-store'});
    if(comparisonResponse.ok){
     const comparison=await comparisonResponse.json(),body=get('comparison-stats');body.replaceChildren();
     for(const row of comparison.methods){const tr=document.createElement('tr');
      for(const value of [row.method,row.edge_pixels.toLocaleString(),`${row.edge_coverage_percent.toFixed(2)}%`]){const td=document.createElement('td');td.textContent=value;tr.appendChild(td);}body.appendChild(tr);}
    }
    if(context.metrics_available){
     const csv=await(await fetch('metrics.csv',{cache:'no-store'})).text();
     const lines=csv.trim().split(/\r?\n/).map(line=>line.split(',')),keys=lines.shift(),body=get('metrics');body.replaceChildren();
     for(const row of lines){const tr=document.createElement('tr');for(const key of ['method','f1_exact','f1_1px','f1_2px']){const td=document.createElement('td'),value=row[keys.indexOf(key)];td.textContent=key==='method'?value:Number(value).toFixed(3);tr.appendChild(td);}body.appendChild(tr);}
    }
   }
   previous=s.status;
  }catch(error){label.textContent='Live backend unavailable';run.disabled=true;send.disabled=true;}
 }
 async function start(){
  reset();get('finished').hidden=true;
  const response=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
  if(!response.ok)throw Error((await response.json()).error||'Unable to start detection');
  previous='queued';active=true;
 }
 run.addEventListener('click',async()=>{
  if(pending||active)return;pending=true;controls();
  try{await start();}catch(error){label.textContent=error.message;}finally{pending=false;controls();await update();}
 });
 send.addEventListener('click',async()=>{
  const file=upload.files[0];if(!file){label.textContent='Choose an image first';return;}
  if(file.size>20*1024*1024){label.textContent='Upload an image smaller than 20 MB';return;}
  if(pending||active)return;pending=true;controls();label.textContent='Uploading and preprocessing image…';
  try{
   const response=await fetch('/api/upload',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-File-Name':encodeURIComponent(file.name)},body:file});
   const c=await response.json();if(!response.ok)throw Error(c.error||'Upload failed');
   reset();applyContext(c);get('finished').hidden=true;label.textContent='Preprocessing complete · starting quantum pipeline';
   await Promise.all(['original-preview','prepared-preview'].map(id=>get(id).decode().catch(()=>{})));
   await start();
  }catch(error){label.textContent=error.message;}
  finally{pending=false;controls();if(active)await update();}
 });
 async function initialize(){if(location.protocol!=='file:'){try{applyContext(await(await fetch('/api/context',{cache:'no-store'})).json());}catch(error){label.textContent='Unable to load image context';}}await update();}
 initialize();setInterval(update,1000);
})();
