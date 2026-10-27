/* npm install playwright, then node verify-browser.cjs [URL]. Uses installed Edge. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(process.argv[2]||'http://127.0.0.1:8770/');
    const finish=()=>page.locator('#step').evaluate(el=>{el.value=el.max;el.dispatchEvent(new Event('input',{bubbles:true}));});
    const seek=value=>page.locator('#step').evaluate((el,v)=>{el.value=v;el.dispatchEvent(new Event('input',{bubbles:true}));},value);
    const exportShot=async()=>{
      const downloadPromise=page.waitForEvent('download');await page.locator('#export').click();
      const dl=await downloadPromise;return JSON.parse(fs.readFileSync(await dl.path(),'utf8'));
    };
    assert.equal(await page.locator('#step').inputValue(),'0');
    await page.locator('#next').click();assert.match(await page.locator('#step-title').textContent(),/H/);
    await page.locator('#next').click();assert.equal(await page.locator('.qubit-kind').first().textContent(),'MIXED');
    await page.screenshot({path:path.join(__dirname,'preview-desktop.png'),fullPage:true});
    await finish();assert.equal(await page.locator('#total').textContent(),'1');
    const first=await exportShot();assert.equal(first.frames.length,5);
    assert.ok(['00','11'].includes(first.frames.at(-1).bits.join('')));
    await seek(0);await finish();const replay=await exportShot();
    assert.deepEqual(first.frames,replay.frames);assert.equal(await page.locator('#total').textContent(),'1');
    await page.locator('#new-shot').click();assert.equal(await page.locator('#step').inputValue(),'0');
    await finish();assert.equal(await page.locator('#total').textContent(),'2');
    await page.locator('#sample').click();assert.equal(await page.locator('#total').textContent(),'258');
    const sampled=await exportShot();assert.ok(Object.keys(sampled.completed_counts).every(x=>x==='00'||x==='11'));
    await page.locator('#clear').click();assert.equal(await page.locator('#total').textContent(),'0');
    for(const preset of ['teleport','ghz','phase','qhed']){
      await page.locator(`[data-preset=${preset}]`).click();await finish();
      assert.equal(await page.locator('#total').textContent(),'1');assert.equal(await page.locator('#norm').textContent(),'Σp = 1.000');
      if(preset==='teleport'){
        assert.equal(await page.locator('#step').getAttribute('max'),'15');
        await seek(9);assert.equal(await page.locator('#stage-label').textContent(),'CLASSICAL FEED-FORWARD');
        assert.match(await page.locator('#step-explanation').textContent(),/correction (applied|skipped)/);
        await seek(10);assert.match(await page.locator('#step-explanation').textContent(),/Teleportation is complete/);
        const teleported=await exportShot();assert.equal(teleported.frames.at(-1).bits[2],0);
        await page.screenshot({path:path.join(__dirname,'preview-teleportation.png'),fullPage:true});
      }
    }
    await page.locator('#qubits').selectOption('3');assert.equal(await page.locator('#total').textContent(),'0');
    await page.locator('#gate').selectOption('CX');await page.locator('#control').selectOption('0');await page.locator('#target').selectOption('0');
    await page.locator('#add').click();assert.match(await page.locator('#status').textContent(),/different qubits/);
    await page.locator('#control').selectOption('1');await page.locator('#add').click();assert.equal(await page.locator('#circuit-name').textContent(),'Your circuit');
    await page.locator('#gate').selectOption('RZ');await page.locator('#angle').fill('0.25');await page.locator('#add').click();
    await page.locator('#gate').selectOption('M');await page.locator('#target').selectOption('1');await page.locator('#add').click();
    await finish();const custom=await exportShot();assert.equal(custom.operations.filter(g=>g.type==='M').length,4);
    assert.ok(custom.operations.some(g=>g.type==='RZ'&&g.angle===Math.PI/4));
    await page.locator('#undo').click();await page.locator('#qubits').selectOption('1');await finish();assert.equal(await page.locator('#classical .classical-bit').count(),1);
    await page.locator('[data-preset=bell]').click();await page.locator('#speed').selectOption('350');await page.locator('#play').click();
    await page.waitForFunction(()=>document.querySelector('#step').value==='4');assert.equal(await page.locator('#play').textContent(),'▶ Play shot');
    await page.locator('#reset').click();await page.locator('#circuit [data-index="2"]').click();assert.equal(await page.locator('#step').inputValue(),'2');
    await page.locator('h1').click();await page.keyboard.press('ArrowRight');assert.equal(await page.locator('#step').inputValue(),'3');
    await page.setViewportSize({width:390,height:844});await page.locator('[data-preset=qhed]').click();await seek(4);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile page overflows');
    await page.locator('#status').evaluate(el=>el.classList.remove('visible'));
    await page.screenshot({path:path.join(__dirname,'preview-mobile.png'),fullPage:true});
    await page.setViewportSize({width:360,height:800});await page.locator('#qubits').selectOption('6');await finish();
    assert.equal(await page.locator('#amplitudes .amplitude').count(),64);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Six-qubit page overflows');
    assert.deepEqual(errors,[]);
    await page.goto(new URL('?preset=teleport',process.argv[2]||'http://127.0.0.1:8770/').href);
    assert.equal(await page.locator('#circuit-name').textContent(),'Quantum teleportation');
    // file:// is the zero-install entry point and must work without a server.
    await page.goto(require('node:url').pathToFileURL(path.join(__dirname,'index.html')).href);
    await page.locator('#next').click();assert.equal(await page.locator('#step').inputValue(),'1');
    const result={browser:'Microsoft Edge',page_errors:errors,checks:['gate stepping','mixed local states','stable replay','one count per inspected shot','independent shot batches','all presets','teleportation conditional corrections and receiver verification','preset deep links','gate validation','rotation editing','intermediate measurement','undo and register resizing','playback','click-to-seek','keyboard stepping','390px and 360px responsive layouts','64 basis states','JSON export','offline file entry point']};
    fs.writeFileSync(path.join(__dirname,'verification.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
