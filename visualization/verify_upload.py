"""Verify upload → preprocessing → actual measured QHED and live gate playback."""
import argparse
import gzip
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser()
parser.add_argument('--url',default='http://127.0.0.1:8766')
URL=parser.parse_args().url.rstrip('/')
ROOT=Path(__file__).resolve().parents[1]
CHECK=ROOT/'results/upload_verification'
CHECK.mkdir(parents=True,exist_ok=True)
fixture=Image.new('RGBA',(96,64),(20,30,40,255))
draw=ImageDraw.Draw(fixture)
draw.ellipse((12,8,70,58),fill=(170,160,140,255),outline=(255,255,255,255),width=3)
draw.rectangle((76,0,95,63),fill=(0,0,0,0))
fixture.save(CHECK/'fixture.png')
with sync_playwright() as playwright:
    browser=playwright.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1180,'height':1000})
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(URL+'/')
    page.wait_for_function("!document.getElementById('upload-run').disabled")
    page.locator('#upload').set_input_files(str(CHECK/'fixture.png'))
    page.locator('#upload-run').click()
    page.wait_for_function("!document.getElementById('preprocessing').hidden")
    page.wait_for_function("document.getElementById('prepared-preview').naturalWidth===96")
    assert page.locator('#benchmark').is_hidden()
    page.wait_for_function("document.querySelector('[data-trace=diagram]').getAttribute('data-circuit-name') !== null",timeout=60000)
    page.wait_for_function("document.getElementById('status').textContent==='Complete'",timeout=60000)
    trace=page.request.get(URL+'/api/trace').json()
    assert trace['image_width']==96 and trace['image_height']==64
    assert all(sum(c['counts'].values())==8192 for c in trace['circuits'])
    assert page.locator('#overlay-caption').text_content()=='Measured quantum edges · magenta'
    assert page.locator('#finished').is_visible()
    page.wait_for_function("document.querySelectorAll('#comparison-stats tr').length===4")
    for name in ('quantum','sobel','canny','robinson'):
        page.wait_for_function(f"document.getElementById('compare-{name}').naturalWidth===96")
    page.locator('[data-trace=replay]').click()
    page.wait_for_function("document.querySelector('[data-trace=gate-label]').textContent.startsWith('MCX')",timeout=30000)
    page.screenshot(path=str(CHECK/'upload_live_preview.png'),full_page=True)
    page.set_viewport_size({'width':360,'height':1000})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(CHECK/'upload_mobile_preview.png'),full_page=True)
    # Reload retains the uploaded context, then bad uploads leave it untouched.
    page.reload();page.wait_for_function("document.getElementById('status').textContent==='Complete'")
    before=page.request.get(URL+'/api/context').json()
    bad=page.request.post(URL+'/api/upload',headers={'Content-Type':'application/octet-stream'},data=b'bad image')
    assert bad.status==400
    assert page.request.get(URL+'/api/context').json()==before
    assert not errors,errors
    browser.close()
output=max((ROOT/'results/user_images').glob('*/run_metadata.json'),key=lambda p:p.stat().st_mtime).parent
metadata=json.loads((output/'run_metadata.json').read_text())
assert metadata['execution']['circuits_executed']==140
assert metadata['execution']['measurement_shots']==140*8192
maps=np.load(output/'quantum_maps.npz')
assert maps['strength'].shape==(64,96) and np.count_nonzero(maps['strength'])>0
with gzip.open(output/'measurement_counts.jsonl.gz','rt') as handle:
    audit=[json.loads(line) for line in handle]
with gzip.open(output/'gate_trace.jsonl.gz','rt') as handle:
    packets=[json.loads(line) for line in handle]
assert packets and audit
for packet in packets:
    for circuit in packet['circuits']:
        matching=next(record for record in audit if record['tile_y']==packet['tile_y']
                      and record['tile_x']==packet['tile_x']
                      and record['direction']==circuit['metadata']['direction']
                      and record['pair_offset']==circuit['metadata']['pair_offset'])
        assert matching['counts']==circuit['counts'] and matching['job_id']==packet['job_id']
assert np.array_equal(np.asarray(Image.open(output/'preprocessed.png')),np.asarray(Image.open(output/'input.png')))
import sys
sys.path.insert(0,str(ROOT))
from classical.sobel import sobel_edge_binary
from classical.canny import canny_edge_auto
from classical.robinson_compass import robinson_edge_binary
with Image.open(output/'input.png') as source: input_image=np.asarray(source)
expected={'sobel':sobel_edge_binary(input_image)[0],'canny':canny_edge_auto(input_image),
          'robinson':robinson_edge_binary(input_image)[0]}
for name,values in expected.items():
    with Image.open(output/f'{name}_edges.png') as source: actual=np.asarray(source)
    assert np.array_equal(actual,values),f'{name} comparison does not match the working input'
comparison=json.loads((output/'detector_comparison.json').read_text())
assert len(comparison['methods'])==4
assert all(row['edge_pixels']==int(np.count_nonzero(np.asarray(Image.open(output/f"{('quantum' if row['method'].startswith('QPIE') else row['method'].lower())}_edges.png")))) for row in comparison['methods'])
result={'output':str(output),'circuits':140,'shots':140*8192,'image_shape':[64,96],'browser_errors':errors,'invalid_upload_preserves_context':True}
(CHECK/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
