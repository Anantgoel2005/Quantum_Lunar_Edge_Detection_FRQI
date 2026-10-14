"""Integration check: the view starts the real full-image Qiskit workload."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'results/variants/frqi/row0'
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel='msedge',headless=True)
    page = browser.new_page(viewport={'width':1100,'height':1000})
    errors = []
    page.on('pageerror',lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8768/')
    page.wait_for_function("document.getElementById('status').textContent === 'Complete'")
    assert page.locator('select,canvas').count() == 0
    assert page.locator('input[type=file]').count() == 1
    page.locator('#run').click()
    page.wait_for_function("document.getElementById('status').textContent.includes('blocks completed')",timeout=60000)
    first = page.request.get('http://127.0.0.1:8768/api/status').json()
    assert first['status'] == 'running' and first['circuits_executed'] > 0
    assert page.locator('#run').is_disabled()
    page.screenshot(path=str(OUTPUT/'live_execution_preview.png'),full_page=True)
    page.wait_for_function("document.getElementById('status').textContent === 'Complete'",timeout=600000)
    final = page.request.get('http://127.0.0.1:8768/api/status').json()
    assert final['circuits_executed'] == 5476
    assert final['measurement_shots'] == 44859392
    assert final['output_source'] == 'measured circuit counts'
    page.wait_for_timeout(500)
    assert page.locator('#finished').is_visible()
    assert not errors,errors
    page.screenshot(path=str(OUTPUT/'viewer_preview.png'),full_page=True)
    page.set_viewport_size({'width':360,'height':1000})
    page.wait_for_timeout(100)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(OUTPUT/'viewer_mobile.png'),full_page=True)
    result = {'browser_errors':errors,'automatic_full_tile_run':True,'image_upload_controls':1,'region_selection_controls':0,
        'observed_running_circuits':first['circuits_executed'],'completed_circuits':final['circuits_executed'],
        'measured_shots':final['measurement_shots'],'mobile_overflow':False}
    (OUTPUT/'viewer_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    browser.close()
