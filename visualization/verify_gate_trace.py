"""Exercise live gate frames sourced from a complete actual inference run."""
import gzip
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'results/variants/frqi/row0'
with sync_playwright() as playwright:
    browser=playwright.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1180,'height':1000})
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:8768/')
    page.wait_for_function("document.getElementById('status').textContent === 'Complete'")
    assert page.locator('select,canvas').count()==0
    assert page.locator('input[type=file]').count()==1
    page.locator('#run').click()
    page.wait_for_function("document.querySelector('[data-trace=diagram]').getAttribute('data-circuit-name') !== null",timeout=60000)
    trace=page.request.get('http://127.0.0.1:8768/api/trace').json()
    assert len(trace['circuits'])==4
    assert all(c['shots']==8192 and c['measure_sampling'] for c in trace['circuits'])
    assert all(abs(s['norm']-1)<1e-9 for c in trace['circuits'] for s in c['snapshots'])
    page.wait_for_function("document.querySelector('[data-trace=diagram]').getAttribute('data-active-gate') !== '-1'")
    first=page.evaluate("document.getElementById('gate-trace-panel').traceInspector.state()")
    page.wait_for_timeout(300)
    moved=page.evaluate("document.getElementById('gate-trace-panel').traceInspector.state()")
    assert first['frame']!=moved['frame'] or first['sequence']!=moved['sequence'], 'Gate animation not advancing'
    page.locator('[data-trace=pause]').click()
    paused=page.evaluate("document.getElementById('gate-trace-panel').traceInspector.state()")
    before=page.request.get('http://127.0.0.1:8768/api/status').json()['circuits_executed']
    page.wait_for_timeout(2500)
    after=page.request.get('http://127.0.0.1:8768/api/status').json()['circuits_executed']
    held=page.evaluate("document.getElementById('gate-trace-panel').traceInspector.state()")
    assert held['frame']==paused['frame'] and held['paused']
    assert after>before, 'Pausing animation interrupted detector'
    page.locator('[data-trace=replay]').click()
    page.wait_for_function("document.querySelector('[data-trace=gate-label]').textContent.startsWith('MCX')",timeout=30000)
    page.screenshot(path=str(OUTPUT/'gate_animation_preview.png'),full_page=True)
    page.wait_for_function("document.querySelector('[data-trace=state]').getAttribute('data-display-mode') === 'measurements'",timeout=30000)
    assert 'actual shots' in page.locator('[data-trace=measurement]').text_content()
    page.wait_for_function("document.getElementById('status').textContent === 'Complete'",timeout=600000)
    complete=page.request.get('http://127.0.0.1:8768/api/status').json()
    assert complete['circuits_executed']==5476
    assert complete['gate_trace']['enabled']
    page.locator('[data-trace=pause]').click()
    page.set_viewport_size({'width':360,'height':1000})
    page.wait_for_timeout(100)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(OUTPUT/'gate_animation_mobile.png'),full_page=True)
    assert not errors,errors
    with gzip.open(OUTPUT/'gate_trace.jsonl.gz','rt',encoding='utf-8') as handle:
        packets=[json.loads(line) for line in handle]
    with gzip.open(OUTPUT/'measurement_counts.jsonl.gz','rt',encoding='utf-8') as handle:
        measurements=[json.loads(line) for line in handle]
    by_key={(r['job_id'],r['tile_y'],r['tile_x'],r['direction'],r['pair_offset']):r for r in measurements}
    for packet in packets:
        for circuit in packet['circuits']:
            record=by_key[(packet['job_id'],packet['tile_y'],packet['tile_x'],circuit['metadata']['direction'],circuit['metadata']['pair_offset'])]
            assert record['counts']==circuit['counts']
    result={'browser_errors':errors,'gate_animation_advances':True,'pause_preserves_backend_execution':True,
        'measurement_frames_from_actual_counts':True,'trace_batches':len(packets),'traced_inference_circuits':sum(len(p['circuits']) for p in packets),
        'checkpoint_norms_valid':True,'traces_match_inference_audit':True,'image_upload_controls':1,'region_selection_controls':0,'mobile_overflow':False}
    (OUTPUT/'gate_animation_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    browser.close()
