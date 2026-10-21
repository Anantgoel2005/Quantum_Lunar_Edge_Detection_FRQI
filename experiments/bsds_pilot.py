"""Frozen BSDS500 validation-only pilot, using existing measured detectors.

Prepare: python experiments/bsds_pilot.py --prepare-only
Run/resume: python experiments/bsds_pilot.py
Verify: python experiments/bsds_pilot.py --verify-only
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.benchmark_encodings import digest, write_json

REVISION = 'a04b7c6c3a9f0ace74bf205c72a43d32e1c72722'
OUTPUT = ROOT / 'results/bsds_pilot'
CACHE = ROOT / 'data/bsds500'
SEEDS = (42, 4242, 424242)
CONFIGS = {
    'QPIE16': ('QPIE', 16, 8192, False),
    'FRQI16': ('FRQI', 16, 8192, False),
    'NEQR16': ('NEQR', 16, 8192, False),
    'QPIE8': ('QPIE', 8, 1692, False),
    'FRQI8': ('FRQI', 8, 1692, False),
    'NEQR8': ('NEQR', 8, 1692, False),
    'QPIE16-offset': ('QPIE', 16, 8192, True),
}


def download(path):
    if '/test/' in path:
        raise ValueError('Test image/annotation downloads are forbidden in this development pilot')
    destination = CACHE / path
    if destination.exists():
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = f'https://raw.githubusercontent.com/BIDS/BSDS500/{REVISION}/{path}'
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Quantum-edge-development-pilot'})
            with urllib.request.urlopen(request, timeout=45) as response:
                data = response.read()
            temporary = destination.with_suffix(destination.suffix + '.part')
            temporary.write_bytes(data)
            temporary.replace(destination)
            return destination
        except Exception:
            if attempt == 2:
                raise


def selected_cases(tree):
    paths = {entry['path'] for entry in tree['tree']}
    images = [p for p in paths if p.startswith('BSDS500/data/images/val/') and p.endswith('.jpg')]
    images.sort(key=lambda p: hashlib.sha256(('20261019:' + p).encode()).hexdigest())
    if len(images) != 100:
        raise ValueError('Expected 100 official validation images')
    cases = []
    for path in images[:20]:
        annotation = path.replace('/images/', '/groundTruth/').replace('.jpg', '.mat')
        if annotation not in paths:
            raise ValueError('Missing corresponding annotation path')
        cases.append({'id': Path(path).stem, 'split': 'val', 'image': path, 'annotations': annotation})
    return cases


def tasks_for(cases):
    extras = {c['id'] for c in cases[:5]}
    return [(c['id'], config, seed) for c in cases for config in CONFIGS
            if config.endswith('16') or c['id'] in extras for seed in SEEDS]


def load_boundaries(path):
    import numpy as np
    from scipy.io import loadmat
    cells = np.atleast_1d(loadmat(path, squeeze_me=True, struct_as_record=False)['groundTruth'])
    result = []
    for cell in cells.flat:
        mask = cell.Boundaries
        if hasattr(mask, 'toarray'):
            mask = mask.toarray()
        result.append(np.asarray(mask, dtype=bool))
    return np.stack(result)


def prepare():
    import numpy as np
    from PIL import Image
    from experiments.benchmark_encodings import source_hashes
    tree = json.loads((CACHE / 'tree.json').read_text())
    if tree['sha'] != REVISION:
        raise ValueError('BSDS mirror inventory revision differs')
    cases = selected_cases(tree)
    protocol = {
        'schema': 1, 'dataset': 'BSDS500', 'source': 'https://github.com/BIDS/BSDS500',
        'source_revision': REVISION, 'split': 'val', 'cases': cases,
        'selection': 'SHA256 rank of validation image paths with prefix20261019; 20 cases; labels unopened at selection',
        'crop': 'Fixed native128x128center; PillowL grayscale; no resizing, contrast stretch or smoothing',
        'annotations': 'All human boundary masks retained separately; same native crop',
        'seeds': list(SEEDS), 'configs': {k: list(v) for k, v in CONFIGS.items()},
        'primary': 'Three encodings, tile16,8192shots/circuit,20images,3seeds=180runs',
        'efficiency_subset': [c['id'] for c in cases[:5]],
        'efficiency': 'First5preselectedcases; tile8at1692shots/circuit, plusQPIE16minimumsubtraction,3seeds=60additionalruns',
        'budget': {'tile16': 400*8192, 'tile8': 1936*1692, 'relative_shortfall_tile8': 1088/(400*8192)},
        'thresholds': (np.arange(1, 32)/32).tolist(), 'max_distance': .0075,
        'distance_reference': 'diagonal of scored124x124nativecrop (2pxborder excluded)',
        'matching': 'SciPy sparse maximum-cardinality then minimum-Euclidean-distance one-to-one assignment',
        'thinning': 'scikit-image Guo-Hall thin; precision matches any annotator; recall sums over annotators',
        'ap': '101point interpolated boundaryAP; NOT pixelAP or certified MATLAB BSDS AP',
        'scope': 'Validation-only nativecrop development pilot,31thresholds; NO official full-image BSDS500 score',
        'test_policy': 'Do not download or read test image/annotation contents',
        'f1_summary': 'Per-image threshold curve averaged across seeds; primarymacro-bestF1 andAP. Also report pooled counts maxF1(ODS-style) and meanimagebestF1(OIS-style). Development optima, not locked test operating points.',
        'source_hashes': source_hashes(),
        'pilot_hashes': {p: digest(ROOT / p) for p in ('experiments/bsds_pilot.py', 'evaluation/bsds_boundary.py')},
        'versions': {p: version(p) for p in ('qiskit','qiskit-aer','numpy','scipy','scikit-image','Pillow')},
        'attribution': 'P. Arbelaez, M. Maire, C. Fowlkes, J. Malik: Contour Detection and Hierarchical Image Segmentation, TPAMI2011',
        'terms': 'Refer to original Berkeley dataset terms; no new dataset license asserted',
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / 'protocol.json'
    if path.exists() and json.loads(path.read_text()) != protocol:
        raise ValueError('Frozen protocol/source/environment differs; use an independently versioned pilot')
    write_json(path, protocol)
    print('Frozen20validationIDs before loading annotations; test content forbidden', flush=True)
    paths = [case[key] for case in cases for key in ('image','annotations')]
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(download, paths))
    inventory = {entry['path']: entry for entry in tree['tree']}
    records = []
    for case in cases:
        for key in ('image','annotations'):
            source = CACHE / case[key]
            data = source.read_bytes()
            git_blob = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
            if git_blob != inventory[case[key]]['sha']:
                raise ValueError('Downloaded file differs from pinned Git blob')
        image = np.array(Image.open(CACHE / case['image']).convert('L'))
        boundaries = load_boundaries(CACHE / case['annotations'])
        if boundaries.shape[1:] != image.shape or min(image.shape) < 128:
            raise ValueError('Image/annotation coordinate mismatch')
        h, w = image.shape
        y, x = (h-128)//2, (w-128)//2
        crop = image[y:y+128, x:x+128].copy()
        references = boundaries[:, y:y+128, x:x+128].copy()
        folder = OUTPUT / 'cases' / case['id']
        folder.mkdir(parents=True, exist_ok=True)
        Image.fromarray(crop).save(folder / 'input.png')
        np.savez_compressed(folder / 'references.npz', boundaries=references)
        records.append({**case, 'crop_xywh': [x,y,128,128], 'original_shape': [h,w],
                        'annotators': len(references), 'reference_pixels': [int(g[2:-2,2:-2].sum()) for g in references],
                        'source_image_sha256': digest(CACHE / case['image']),
                        'source_annotations_sha256': digest(CACHE / case['annotations']),
                        'input_pixel_sha256': hashlib.sha256(crop.tobytes()).hexdigest(),
                        'references_pixel_sha256': hashlib.sha256(references.tobytes()).hexdigest()})
    manifest = {'protocol_sha256': digest(path), 'cases': records}
    write_json(OUTPUT / 'dataset.json', manifest)
    print('Prepared20nativecrops withallhumanannotations', flush=True)
    return manifest


def exact(image, inequality=False):
    import numpy as np
    values = np.floor(image.astype(float)/255*15) if inequality else image.astype(float)
    dx, dy = np.zeros(image.shape), np.zeros(image.shape)
    x, y = np.diff(values,axis=1), np.diff(values,axis=0)
    dx[:,1:] = (x!=0) if inequality else x
    dy[1:,:] = (y!=0) if inequality else y
    return np.hypot(dx,dy)


def evaluate(strength, references):
    from evaluation.bsds_boundary import evaluate_curve, curve_summary
    counts = evaluate_curve(strength[2:-2,2:-2], references[:,2:-2,2:-2])
    return counts, curve_summary(counts)


def worker(config, case_id, seed):
    # Bind the shared evaluation package before choosing the NEQR quantum repo.
    # The sibling repository has no BSDS evaluator module.
    from evaluation.bsds_boundary import evaluate_curve
    method, tile, shots, offset = CONFIGS[config]
    repo = ROOT.parent / 'Quantum_Lunar_Edge_Detection_NEQR' if method=='NEQR' else ROOT
    sys.path.insert(0,str(repo))
    import numpy as np
    from PIL import Image
    if method=='QPIE':
        from quantum.qpie_full_image import run_full_image_qhed
    else:
        from quantum.variant_circuit import ENCODING
        if ENCODING != method:
            raise ValueError('Wrong encoding imported')
        from quantum.full_image import run_full_image_qhed
    case = OUTPUT / 'cases' / case_id
    image = np.array(Image.open(case/'input.png'))
    references = np.load(case/'references.npz')['boundaries']
    folder = OUTPUT / 'runs' / f'{case_id}_{config}_{seed}'
    folder.mkdir(parents=True,exist_ok=True)
    maps, execution, _ = run_full_image_qhed(image,tile_size=tile,shots=shots,seed=seed,
        batch_tiles=16,subtract_tile_min=offset,audit_path=folder/'counts.jsonl.gz')
    started = time.perf_counter()
    counts, metrics = evaluate(maps['strength'],references)
    target = exact(image,method=='NEQR')
    metrics.update(operator_rmse=float(np.sqrt(np.mean((maps['magnitude'][2:-2,2:-2]-target[2:-2,2:-2])**2))))
    metrics['evaluation_seconds'] = time.perf_counter()-started
    np.savez_compressed(folder/'maps.npz',**maps)
    write_json(folder/'result.json',{'case':case_id,'config':config,'method':method,'seed':seed,
        'tile_size':tile,'shots_per_circuit':shots,'subtract_tile_min':offset,
        'execution':execution,'metrics':metrics,'boundary_counts':counts.tolist(),
        'input_pixel_sha256':hashlib.sha256(image.tobytes()).hexdigest(),
        'protocol_sha256':digest(OUTPUT/'protocol.json')})


def serve(method):
    for line in sys.stdin:
        task = json.loads(line)
        try:
            if CONFIGS[task['config']][0] != method:
                raise ValueError('Cross-encoding persistent worker task')
            worker(task['config'],task['case'],task['seed'])
            print(json.dumps({'ok':True}),flush=True)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            print(json.dumps({'ok':False}),flush=True)


def classical(manifest):
    import numpy as np
    from PIL import Image
    from classical.sobel import sobel_edge
    from classical.canny import canny_edge_auto
    from classical.robinson_compass import robinson_edge
    records = []
    for case in manifest['cases']:
        folder = OUTPUT/'cases'/case['id']
        image = np.array(Image.open(folder/'input.png'))
        references = np.load(folder/'references.npz')['boundaries']
        for name, detector in {'Sobel':lambda:sobel_edge(image), 'Canny':lambda:canny_edge_auto(image),
            'Robinson':lambda:robinson_edge(image)[0], 'Exact-gradient':lambda:exact(image),
            'Exact-inequality':lambda:exact(image,True)}.items():
            path = folder/(name+'.json')
            if path.exists():
                record = json.loads(path.read_text())
                if record['protocol_sha256'] != digest(OUTPUT/'protocol.json'):
                    raise ValueError('Stale classical result')
            else:
                strength = detector().astype(float)
                if strength.max(): strength /= strength.max()
                counts, metrics = evaluate(strength,references)
                np.savez_compressed(folder/(name+'.npz'),strength=strength)
                record = {'case':case['id'],'config':name,'method':name,'seed':None,
                          'metrics':metrics,'boundary_counts':counts.tolist(),
                          'protocol_sha256':digest(OUTPUT/'protocol.json')}
                write_json(path,record)
            records.append(record)
    print('100classical/controlrecords evaluated',flush=True)
    return records


def summary_records(records, ids):
    import numpy as np
    from evaluation.bsds_boundary import curve_summary
    by_config = {}
    for record in records:
        if record['case'] in ids:
            by_config.setdefault(record['config'],{}).setdefault(record['case'],[]).append(record)
    result, per_image = [], {}
    for config, cases in sorted(by_config.items()):
        details, mean_counts = {}, []
        for case_id, runs in cases.items():
            counts = np.mean([r['boundary_counts'] for r in runs],axis=0)
            detail = curve_summary(counts)
            detail['operator_rmse'] = float(np.mean([r['metrics']['operator_rmse'] for r in runs])) if 'operator_rmse' in runs[0]['metrics'] else None
            details[case_id] = detail
            mean_counts.append(counts)
        pooled = curve_summary(np.sum(mean_counts,axis=0))
        item = {'config':config,'images':len(cases),'runs':sum(map(len,cases.values())),
                'macro_best_f1':float(np.mean([d['best_f1'] for d in details.values()])),
                'macro_boundary_ap101':float(np.mean([d['boundary_ap101'] for d in details.values()])),
                'pooled_best_f1':pooled['best_f1'],'pooled_threshold':pooled['best_threshold'],
                'macro_operator_rmse':float(np.mean([d['operator_rmse'] for d in details.values()])) if details[next(iter(details))]['operator_rmse'] is not None else None}
        result.append(item)
        per_image[config] = details
    return {'summary':result,'per_image':per_image}


def write_report(records, manifest):
    import numpy as np
    primary_ids = [c['id'] for c in manifest['cases']]
    tuning_ids = primary_ids[:5]
    primary_configs = {'QPIE16','FRQI16','NEQR16','Sobel','Canny','Robinson','Exact-gradient','Exact-inequality'}
    primary = summary_records([r for r in records if r['config'] in primary_configs],primary_ids)
    tuning = summary_records(records,tuning_ids)
    paired = []
    for smaller,base in [('QPIE8','QPIE16'),('FRQI8','FRQI16'),('NEQR8','NEQR16'),('QPIE16-offset','QPIE16')]:
        delta = np.array([tuning['per_image'][smaller][i]['best_f1']-tuning['per_image'][base][i]['best_f1'] for i in tuning_ids])
        rng = np.random.default_rng(20261019)
        bootstrap = delta[rng.integers(0,len(delta),(10000,len(delta)))].mean(axis=1)
        paired.append({'a':smaller,'b':base,'metric':'seed-averaged-curve image bestF1','mean_difference':float(delta.mean()),
                       'ci95':np.quantile(bootstrap,[.025,.975]).tolist(),'images':len(delta)})
    write_json(OUTPUT/'summary.json',{'primary20':primary,'efficiency5':tuning,'paired_efficiency':paired})
    flat = []
    for r in records:
        flat.append({'case':r['case'],'config':r['config'],'seed':r['seed'],**r['metrics'],
                     'circuits':r.get('execution',{}).get('circuits_executed',0),
                     'measurement_shots':r.get('execution',{}).get('measurement_shots',0)})
    with (OUTPUT/'runs.csv').open('w',newline='',encoding='utf-8') as handle:
        writer = csv.DictWriter(handle,fieldnames=sorted(set().union(*(r.keys() for r in flat))))
        writer.writeheader(); writer.writerows(flat)
    rows = ['# BSDS500 validation-only quantum development pilot','',
            'Twenty deterministic validation images, one native128x128center crop per image; all human boundary masks retained separately. '
            'No test image or annotation content was downloaded or evaluated. This is not an official full-image BSDS500 score.','',
            'Images use the same Pillow grayscale conversion without contrast stretching, smoothing or resizing. '
            'Primary runs use tile16,8192shots/circuit,seeds42/4242/424242. '
            'Five images selected before labels additionally test tile8 at1692shots/circuit and QPIE16 block-minimum subtraction. '
            'Tile16 uses3,276,800shots/image; tile8 uses3,275,712(0.0332%less). No label-based allocation.','',
            '## Evaluation','',
            'Predictions are thresholded at31fixed levels1/32..31/32 and Guo-Hall thinned. '
            'One-to-one matching maximizes cardinality then minimizes Euclidean distance. '
            'Tolerance is0.0075times the diagonal of the scored124x124crop(2pxborder excluded). '
            'Precision counts predicted pixels matched by any annotator; recall sums matched/positive pixels over annotators. '
            'The matcher is independently implemented with SciPy, not the official MATLAB binary. '
            'Higra was investigated but its native matcher terminated on minimal fixtures in this environment, so it is not used.','',
            'Macro bestF1 averages each image optimum after averaging count curves over seeds. '
            'Pooled bestF1 maximizes F1 after pooling image counts (ODS-style, grid-only). '
            'Boundary AP101 averages the precision envelope on101recall levels; it differs from pixel average precision '
            'in the previous SomBench study and is not certified identical to official MATLAB AP. '
            'All threshold optima are development diagnostics, not frozen test operating points.','',
            '## Primary20-image results','',
            '| Configuration | Images | Macro bestF1 | Pooled bestF1 | Macro boundaryAP101 | Operator RMSE |',
            '|---|---:|---:|---:|---:|---:|']
    for s in primary['summary']:
        rmse = '-' if s['macro_operator_rmse'] is None else f"{s['macro_operator_rmse']:.4f}"
        rows.append(f"| {s['config']} | {s['images']} | {s['macro_best_f1']:.4f} | {s['pooled_best_f1']:.4f} | {s['macro_boundary_ap101']:.4f} | {rmse} |")
    rows += ['','## Matched-budget efficiency5-image subset','',
             '| Configuration | Macro bestF1 | Macro boundaryAP101 | Operator RMSE |','|---|---:|---:|---:|']
    for s in tuning['summary']:
        rmse = '-' if s['macro_operator_rmse'] is None else f"{s['macro_operator_rmse']:.4f}"
        rows.append(f"| {s['config']} | {s['macro_best_f1']:.4f} | {s['macro_boundary_ap101']:.4f} | {rmse} |")
    rows += ['','## Paired efficiency effects','',
             'Exploratory10,000image-level paired bootstrap resamples,95%percentile intervals, seed20261019. '
             'Only5images; no multiplicity correction; repeated simulator seeds are not independent images.','',
             '| A | B | Difference in image bestF1 | 95% interval |','|---|---|---:|---|']
    rows += [f"| {p['a']} | {p['b']} | {p['mean_difference']:.4f} | [{p['ci95'][0]:.4f},{p['ci95'][1]:.4f}] |" for p in paired]
    quantum = [r for r in records if r['seed'] is not None]
    rows += ['','## Execution and limitations','',
             f"Completed{len(quantum)}quantumruns and100classical/controlrecords, "
             f"{sum(r['execution']['circuits_executed'] for r in quantum):,}circuits and "
             f"{sum(r['execution']['measurement_shots'] for r in quantum):,}idealAer simulator shots.", '',
             'QPIE and FRQI estimate calibrated brightness gradients. NEQR uses4bit intensity inequality; '
             'its exact control and RMSE units differ. Native Initialize state preparation is a simulation convenience, '
             'not constant-time hardware image loading. Timings include compressed audit writes and are not a hardware-speed benchmark.','',
             'Cropped validation data, a31point threshold grid and a SciPy matching implementation limit comparison '
             'with published full-image BSDS500 scores. Natural-image semantic boundaries are not all photometric gradients. '
             'Do not interpret higher boundaryF1 as proof of quantum advantage.','',
             '## Reproducibility','',
             f'Source: [BIDS BSDS500 mirror](https://github.com/BIDS/BSDS500), revision`{REVISION}`. '
             'Reference: Arbelaez etal., Contour Detection and Hierarchical Image Segmentation, TPAMI2011. '
             '[Official dataset guidelines](https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/grouping/resources.html).','',
             'Run`python experiments/bsds_pilot.py`; resume requires identical frozen source and environment. '
             'Run`python experiments/bsds_pilot.py --verify-only` for independent count replay and evaluation recomputation. '
             'See`protocol.json`,`dataset.json`,`summary.json`,`runs.csv`,`verification.json` and`quality_review.md`.','']
    (OUTPUT/'report.md').write_text('\n'.join(rows),encoding='utf-8')


def verify(records, manifest):
    import numpy as np
    from PIL import Image
    from experiments.verify_encoding_counts import replay
    expected = set(tasks_for(manifest['cases']))
    quantum = [r for r in records if r['seed'] is not None]
    observed = {(r['case'],r['config'],r['seed']) for r in quantum}
    if expected!=observed or len(quantum)!=240 or len(records)!=340:
        raise ValueError('Incomplete or duplicate matrix')
    sources = json.loads((OUTPUT/'protocol.json').read_text())
    for relative, sha in sources['source_hashes'].items():
        if digest(ROOT.parent/relative)!=sha: raise ValueError('Live source drift')
    for relative,sha in sources['pilot_hashes'].items():
        if digest(ROOT/relative)!=sha: raise ValueError('Pilot source drift')
    max_error, circuits, total_shots = 0.,0,0
    for number,r in enumerate(records,1):
        case = OUTPUT/'cases'/r['case']
        image = np.array(Image.open(case/'input.png'))
        references = np.load(case/'references.npz')['boundaries']
        if r['protocol_sha256']!=digest(OUTPUT/'protocol.json'): raise ValueError('Protocol mismatch')
        if r['seed'] is not None:
            method,tile,shots,offset = CONFIGS[r['config']]
            folder = OUTPUT/'runs'/f"{r['case']}_{r['config']}_{r['seed']}"
            with gzip.open(folder/'counts.jsonl.gz','rt',encoding='utf-8') as handle:
                audit = [json.loads(line) for line in handle]
            core=tile-2
            expected_keys={(y,x,d,o) for y in range(0,128,core) for x in range(0,128,core)
                           for d in ('horizontal','vertical') for o in (0,1)}
            keys={(a['tile_y'],a['tile_x'],a['direction'],a['pair_offset']) for a in audit}
            if keys!=expected_keys or len(keys)!=len(audit): raise ValueError('Audit matrix mismatch')
            pad=np.pad(image,((1,tile),(1,tile)),mode='edge')
            for a in audit:
                if a['shots']!=shots or sum(a['counts'].values())!=shots: raise ValueError('Shot mismatch')
                y,x=a['tile_y'],a['tile_x']
                patch=pad[y:y+tile,x:x+tile].astype(float)
                expected_offset=float(patch.min()) if offset else 0.
                if a['preparation_offset']!=expected_offset: raise ValueError('Preparation mismatch')
                if not np.isclose(a['preparation_norm_squared'],np.sum((patch-expected_offset)**2)): raise ValueError('Preparation norm mismatch')
            maps=np.load(folder/'maps.npz')
            magnitude=replay(audit,method,tile_size=tile)
            max_error=max(max_error,float(np.max(np.abs(magnitude-maps['magnitude']))))
            np.testing.assert_allclose(magnitude,maps['magnitude'],atol=1e-12,rtol=1e-12)
            normalized=magnitude/magnitude.max() if magnitude.max() else magnitude
            np.testing.assert_allclose(normalized,maps['strength'],atol=1e-12,rtol=1e-12)
            expected_qubits=int(np.log2(tile*tile))+{'QPIE':0,'FRQI':1,'NEQR':4}[method]
            if r['execution']['qubits_per_circuit']!=expected_qubits: raise ValueError('Wrong encoding')
            if r['input_pixel_sha256']!=hashlib.sha256(image.tobytes()).hexdigest(): raise ValueError('Input mismatch')
            circuits+=len(audit);total_shots+=sum(sum(a['counts'].values()) for a in audit)
            target=exact(image,method=='NEQR')
            rmse=float(np.sqrt(np.mean((maps['magnitude'][2:-2,2:-2]-target[2:-2,2:-2])**2)))
            if not np.isclose(rmse,r['metrics']['operator_rmse'],atol=1e-12): raise ValueError('RMSE mismatch')
        else:
            maps=np.load(case/(r['config']+'.npz'))
        counts,metrics=evaluate(maps['strength'],references)
        np.testing.assert_array_equal(counts,np.asarray(r['boundary_counts']))
        for key,value in metrics.items():
            if not np.isclose(value,r['metrics'][key],atol=1e-12): raise ValueError('Metric mismatch')
        if number%20==0: print(f'Verified{number}/{len(records)}maps',flush=True)
    downloaded=list((CACHE/'BSDS500/data').rglob('*'))
    if any('/test/' in str(p).replace('\\','/') and p.is_file() for p in downloaded): raise ValueError('Unexpected test data')
    write_json(OUTPUT/'verification.json',{'status':'passed','quantum_runs':len(quantum),
        'records_recomputed':len(records),'circuits_replayed':circuits,'shots_replayed':total_shots,
        'max_magnitude_error':max_error,'test_image_annotation_files_downloaded':0,
        'checks':['frozen sources','complete matrix','unique audit identities','shot totals','preparation offsets/norms',
                  'independent bit-level replay','encoding qubits','input hashes','operator RMSE',
                  'all31threshold count curves and summary metrics recomputed']})


def load_records(manifest):
    classical_records=[json.loads(p.read_text()) for c in manifest['cases'] for p in (OUTPUT/'cases'/c['id']).glob('*.json')]
    quantum=[json.loads(p.read_text()) for p in (OUTPUT/'runs').glob('*/result.json')]
    return classical_records+quantum


def run(manifest):
    import numpy as np
    records=classical(manifest)
    tasks=tasks_for(manifest['cases'])
    np.random.default_rng(20261019).shuffle(tasks)
    workers={}
    options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    try:
        for number,(case,config,seed) in enumerate(tasks,1):
            path=OUTPUT/'runs'/f'{case}_{config}_{seed}'/'result.json'
            if not path.exists():
                method=CONFIGS[config][0]
                if method not in workers:
                    workers[method]=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'--serve',method],
                        stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,cwd=ROOT,**options)
                process=workers[method]
                process.stdin.write(json.dumps({'case':case,'config':config,'seed':seed})+'\n');process.stdin.flush()
                response=process.stdout.readline()
                if not response or not json.loads(response)['ok']: raise RuntimeError('Worker failed:'+method)
            record=json.loads(path.read_text())
            if record['protocol_sha256']!=digest(OUTPUT/'protocol.json'): raise ValueError('Stale result')
            records.append(record)
            print(f"{number}/240{config}case{case}seed{seed}:F1={record['metrics']['best_f1']:.4f} "
                  f"sim={record['execution']['elapsed_seconds']:.1f}s eval={record['metrics']['evaluation_seconds']:.1f}s",flush=True)
        # Preliminary report is saved before the expensive full independent replay.
        write_report(records,manifest)
        verify(records,manifest)
        print('Completed and verified:'+str(OUTPUT/'report.md'),flush=True)
    finally:
        for p in workers.values(): p.stdin.close()
        for p in workers.values():
            try:p.wait(timeout=30)
            except subprocess.TimeoutExpired:p.kill();p.wait()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--verify-only',action='store_true')
    parser.add_argument('--serve',choices=('QPIE','FRQI','NEQR'))
    args=parser.parse_args()
    if args.serve: serve(args.serve);return
    if args.verify_only:
        manifest=json.loads((OUTPUT/'dataset.json').read_text());verify(load_records(manifest),manifest);return
    manifest=prepare()
    if not args.prepare_only:run(manifest)


if __name__=='__main__':main()
