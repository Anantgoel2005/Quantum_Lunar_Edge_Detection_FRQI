"""Optional browser checks: pip install playwright; uses installed Edge."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width': 1000, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto((ROOT / 'index.html').as_uri())
    page.wait_for_selector('#lunar-quantum-live')
    fixtures = json.loads((ROOT / 'qiskit-fixtures.json').read_text())
    errors_by_fixture = page.evaluate('''fixtures => fixtures.map(f => {
      const sim = document.getElementById('lunar-quantum-live').quantumSimulator;
      const computed = sim.calculate(f.pass, f.pixels);
      return {
        amplitudes: Math.max(...computed.amplitudes.map((a,i)=>Math.abs(a-f.amplitudes[i]))),
        edges: Math.max(...computed.edge.map((a,i)=>Math.abs(a-f.edge[i])))
      };
    })''', fixtures)
    assert all(v['amplitudes'] < 1e-12 and v['edges'] < 1e-12 for v in errors_by_fixture), errors_by_fixture
    page.locator('[data-action="step"]').click()
    assert page.evaluate("document.getElementById('lunar-quantum-live').quantumSimulator.getState().gateIndex") == 0
    page.locator('[data-control="speed"]').select_option('100')
    page.locator('[data-control="shots"]').evaluate("element=>{element.value=256;element.dispatchEvent(new Event('input',{bubbles:true}));}")
    page.locator('[data-action="run"]').click()
    page.wait_for_function("document.getElementById('lunar-quantum-live').quantumSimulator.getState().measured === 256")
    completed = page.evaluate("document.getElementById('lunar-quantum-live').quantumSimulator.getState()")
    assert completed['accepted'] > 0
    assert abs(sum(a*a for a in completed['state'])-1) < 1e-12
    page.locator('[data-control="pass"]').select_option('2')
    assert page.evaluate("document.getElementById('lunar-quantum-live').quantumSimulator.getState().measured") == 0
    page.locator('[data-control="image"]').select_option('ramp')
    before = page.evaluate("document.getElementById('lunar-quantum-live').quantumSimulator.getState().pixels[0]")
    page.locator('[data-grid="image"] button').first.click()
    after = page.evaluate("document.getElementById('lunar-quantum-live').quantumSimulator.getState().pixels[0]")
    assert before != after
    page.screenshot(path=str(ROOT / 'preview-desktop.png'), full_page=True)
    page.set_viewport_size({'width': 360, 'height': 1000})
    page.wait_for_timeout(100)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile horizontal overflow'
    page.screenshot(path=str(ROOT / 'preview-mobile.png'), full_page=True)
    assert not errors, errors
    result = {'qiskit_fixtures': len(fixtures), 'maximum_amplitude_error': max(v['amplitudes'] for v in errors_by_fixture),
              'maximum_edge_error': max(v['edges'] for v in errors_by_fixture), 'browser_errors': errors,
              'completed_shots': completed['measured'], 'accepted_edge_outcomes': completed['accepted'],
              'mobile_overflow': False, 'interactions': ['gate step','run to shot limit','pass change','image change','pixel editing']}
    (ROOT/'verification.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    browser.close()
