"""Frozen QPIE offset follow-up; leaves the original BSDS pilot untouched.

Run/resume: python experiments/bsds_offset20.py
Replay/report only: python experiments/bsds_offset20.py --verify-only
"""
import argparse
import gzip
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OLD=ROOT/'results/bsds_pilot'
OUT=ROOT/'results/bsds_qpie_offset20'
SEEDS=(42,4242,424242)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.part')
    temporary.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    temporary.replace(path)


def scores(curves):
    curve=np.mean(np.asarray(curves,dtype=float),axis=0)
    recall=curve[:,0]/np.maximum(curve[:,1],1)
    precision=curve[:,2]/np.maximum(curve[:,3],1)
    f=2*recall*precision/np.maximum(recall+precision,1e-30)
    return {'best_f1':float(f.max()),'best_threshold':float((f.argmax()+1)/32),
            'boundary_ap101':float(np.mean([precision[recall>=r].max(initial=0) for r in np.linspace(0,1,101)]))}


def paired(a,b):
    a,b=np.asarray(a,float),np.asarray(b,float)
    if a.ndim!=1 or a.shape!=b.shape or not len(a):raise ValueError('Paired image vectors required')
    difference=a-b
    rng=np.random.default_rng(20261019)
    means=difference[rng.integers(0,len(a),(10000,len(a)))].mean(axis=1)
    return {'baseline_mean':float(b.mean()),'offset_mean':float(a.mean()),
            'mean_difference':float(difference.mean()),'ci95':np.quantile(means,[.025,.975]).tolist(),
            'images':len(a),'improved_images':int((difference>0).sum()),
            'unchanged_images':int((difference==0).sum())}


def prepare():
    original=read(OLD/'protocol.json');manifest=read(OLD/'dataset.json')
    assert read(OLD/'verification.json')['status']=='passed'
    assert read(OLD/'summary_verification.json')['status']=='passed'
    assert manifest['protocol_sha256']==sha(OLD/'protocol.json')
    cases=[c['id'] for c in manifest['cases']]
    protocol={'schema':1,'parent_protocol_sha256':sha(OLD/'protocol.json'),
              'driver_sha256':sha(__file__),'cases':cases,'initial5':cases[:5],
              'remaining15':cases[5:],'seeds':list(SEEDS),'tile':16,'shots':8192,
              'comparison':'QPIE16-offset minus QPIE16; only block-minimum subtraction changes',
              'new_runs':45,'reused_offset_runs':15,'reused_baseline_runs':60,
              'statistical_plan':'Image-level paired bootstrap10000,seed20261019; two-sided percentile95%; F1 primary,RMSE mechanistic secondary,AP101 descriptive; remaining15 separately; no multiplicity adjustment',
              'scope':'Development follow-up chosen after first5 results; all20 are validation, not independent test. Per-image optimum F1 after averaging seed count curves. No official BSDS scores or hardware advantage.',
              'source_hashes':original['source_hashes'],'pilot_hashes':original['pilot_hashes'],
              'versions':original['versions'],
              'replay_sha256':sha(ROOT/'experiments/verify_encoding_counts.py'),
              'frozen_parent_files':{name:sha(OLD/name) for name in ('protocol.json','dataset.json','summary.json','verification.json','summary_verification.json','report.md')},
              'input_files':{str(p.relative_to(ROOT)):sha(p) for c in cases for p in (OLD/'cases'/c/'input.png',OLD/'cases'/c/'references.npz')}}
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/'protocol.json'
    if path.exists():
        if read(path)!=protocol:raise ValueError('Frozen extension protocol/source drift')
    else:write(path,protocol)
    for case in cases:
        folder=OUT/'cases'/case;folder.mkdir(parents=True,exist_ok=True)
        for name in ('input.png','references.npz'):
            destination=folder/name
            if not destination.exists():shutil.copyfile(OLD/'cases'/case/name,destination)
            assert sha(destination)==sha(OLD/'cases'/case/name)
    return protocol


def ledger(protocol):
    rows=[]
    for case in protocol['cases']:
        for config in ('QPIE16','QPIE16-offset'):
            source=OLD if config=='QPIE16' or case in protocol['initial5'] else OUT
            for seed in SEEDS:
                rows.append({'case':case,'config':config,'seed':seed,
                             'path':str((source/'runs'/f'{case}_{config}_{seed}').relative_to(ROOT))})
    return rows


def run(protocol):
    todo=[r for r in ledger(protocol) if r['path'].startswith(str(OUT.relative_to(ROOT)))]
    np.random.default_rng(20261019).shuffle(todo)
    for number,row in enumerate(todo,1):
        path=ROOT/row['path']/'result.json'
        if not path.exists():
            result=subprocess.run([sys.executable,str(Path(__file__)), '--worker',row['case'],str(row['seed'])],
                                  cwd=ROOT,capture_output=True,text=True)
            with (OUT/'execution.log').open('a',encoding='utf-8') as log:
                log.write(result.stdout+result.stderr)
            if result.returncode:raise RuntimeError(result.stderr)
        assert read(path)['protocol_sha256']==sha(OUT/'protocol.json')
        print(f'Completed {number}/45 new offset runs',flush=True)


def verify(protocol):
    from evaluation.bsds_boundary import evaluate_curve
    from experiments.verify_encoding_counts import replay
    for relative,value in protocol['source_hashes'].items():assert sha(ROOT.parent/relative)==value
    for relative,value in protocol['pilot_hashes'].items():assert sha(ROOT/relative)==value
    for package,value in protocol['versions'].items():assert version(package)==value
    for name,value in protocol['frozen_parent_files'].items():assert sha(OLD/name)==value
    for name,value in protocol['input_files'].items():assert sha(ROOT/name)==value
    assert sha(ROOT/'experiments/verify_encoding_counts.py')==protocol['replay_sha256']
    rows=ledger(protocol);write(OUT/'run_ledger.json',rows)
    assert len(rows)==120 and len({(r['case'],r['config'],r['seed']) for r in rows})==120
    assert len(list((OUT/'runs').glob('*/result.json')))==45
    collected={};circuits=shots=0;maximum=0.
    for number,row in enumerate(rows,1):
        folder=ROOT/row['path'];record=read(folder/'result.json')
        new=folder.parent.parent==OUT
        assert record['protocol_sha256']==(sha(OUT/'protocol.json') if new else protocol['parent_protocol_sha256'])
        for key in ('case','config','seed'):assert record[key]==row[key]
        offset=row['config'].endswith('offset')
        assert record['method']=='QPIE' and record['tile_size']==16 and record['shots_per_circuit']==8192
        assert record['subtract_tile_min']==offset and record['execution']['qubits_per_circuit']==8
        image=np.array(Image.open(OLD/'cases'/row['case']/'input.png'))
        assert hashlib.sha256(image.tobytes()).hexdigest()==record['input_pixel_sha256']
        refs=np.load(OLD/'cases'/row['case']/'references.npz')['boundaries']
        with gzip.open(folder/'counts.jsonl.gz','rt',encoding='utf8') as handle:audit=[json.loads(line) for line in handle]
        keys={(a['tile_y'],a['tile_x'],a['direction'],a['pair_offset']) for a in audit}
        expected={(y,x,d,o) for y in range(0,128,14) for x in range(0,128,14) for d in ('horizontal','vertical') for o in (0,1)}
        assert keys==expected and len(audit)==400
        padded=np.pad(image,((1,16),(1,16)),mode='edge').astype(float)
        for a in audit:
            assert a['shots']==8192 and sum(a['counts'].values())==8192
            assert all(isinstance(n,int) and n>=0 for n in a['counts'].values())
            patch=padded[a['tile_y']:a['tile_y']+16,a['tile_x']:a['tile_x']+16]
            minimum=float(patch.min()) if offset else 0.
            assert a['preparation_offset']==minimum
            assert np.isclose(a['preparation_norm_squared'],np.sum((patch-minimum)**2),rtol=1e-13,atol=1e-10)
        magnitude=replay(audit,'QPIE')
        maps=np.load(folder/'maps.npz')
        maximum=max(maximum,float(np.max(np.abs(magnitude-maps['magnitude']))))
        np.testing.assert_allclose(magnitude,maps['magnitude'],atol=1e-12,rtol=1e-12)
        strength=magnitude/magnitude.max() if magnitude.max() else magnitude
        np.testing.assert_allclose(strength,maps['strength'],atol=1e-12,rtol=1e-12)
        counts=evaluate_curve(maps['strength'][2:-2,2:-2],refs[:,2:-2,2:-2])
        np.testing.assert_array_equal(counts,record['boundary_counts'])
        for key,value in scores([counts]).items():assert np.isclose(value,record['metrics'][key],atol=1e-12,rtol=1e-12)
        dx=np.zeros(image.shape);dy=dx.copy();dx[:,1:]=np.diff(image.astype(float),axis=1);dy[1:,:]=np.diff(image.astype(float),axis=0)
        rmse=float(np.sqrt(np.mean((magnitude[2:-2,2:-2]-np.hypot(dx,dy)[2:-2,2:-2])**2)))
        assert np.isclose(rmse,record['metrics']['operator_rmse'],atol=1e-12,rtol=1e-12)
        collected.setdefault((row['case'],row['config']),[]).append(record)
        circuits+=len(audit);shots+=len(audit)*8192
        if number%15==0:print(f'Verified {number}/120 paired records',flush=True)
    per_image={}
    for (case,config),records in collected.items():
        assert len(records)==3 and {r['seed'] for r in records}==set(SEEDS)
        metrics=scores([r['boundary_counts'] for r in records])
        metrics['operator_rmse']=float(np.mean([r['metrics']['operator_rmse'] for r in records]))
        per_image.setdefault(case,{})[config]=metrics
    comparisons={}
    for label,ids in [('all20',protocol['cases']),('initial5',protocol['initial5']),('remaining15',protocol['remaining15'])]:
        comparisons[label]={key:paired([per_image[i]['QPIE16-offset'][key] for i in ids],
                                      [per_image[i]['QPIE16'][key] for i in ids])
                            for key in ('best_f1','operator_rmse','boundary_ap101')}
    write(OUT/'summary.json',{'per_image':per_image,'comparisons':comparisons})
    write(OUT/'verification.json',{'status':'passed','paired_records':len(rows),'new_runs':45,
          'circuits_replayed':circuits,'shots_replayed':shots,'max_magnitude_error':maximum,
          'parent_files_unchanged':True,'new_downloads':0,'test_content_accessed':False,
          'checks':['source/version/input hashes','complete matrix','audit grid and totals','preparation offset/norm',
                    'independent bit-level magnitude replay','all31 boundary-count curves','operator RMSE','seed curves averaged before scoring']})


def report(protocol):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    d=read(OUT/'summary.json');v=read(OUT/'verification.json')
    fig,axes=plt.subplots(1,2,figsize=(11,5),layout='constrained')
    ids=protocol['cases']
    for ax,key,title in zip(axes,('best_f1','operator_rmse'),('Image-optimal boundary F1 (higher is better)','Gradient RMSE (lower is better)')):
        for i in ids:
            y=[d['per_image'][i][c][key] for c in ('QPIE16','QPIE16-offset')]
            ax.plot([0,1],y,color='#94a3b8' if i in protocol['initial5'] else '#2563eb',alpha=.6,marker='o',markersize=3)
        ax.set_xticks([0,1],['Baseline','Block-minimum subtraction']);ax.set_title(title,fontsize=11)
        ax.grid(axis='y',alpha=.2)
    fig.suptitle('QPIE: paired follow-up on 20 BSDS validation crops',fontweight='bold')
    fig.supxlabel('Blue: remaining 15 images; gray: initial five. Three seeds per image; same shots and blocks.',fontsize=10)
    fig.savefig(OUT/'paired_results.png',dpi=170);fig.savefig(OUT/'paired_results.pdf');plt.close(fig)
    lines=['# QPIE block-minimum subtraction: 20-image follow-up','',
           'This extends the original five-image experiment to all 20 fixed BSDS500 validation crops. '
           'It adds 45 quantum runs and reuses 60 baseline and 15 existing offset runs. '
           'The original pilot files and detector defaults are unchanged.','',
           '## Paired results','',
           '| Images | Metric | Baseline | Subtraction | Difference (subtraction − baseline) | Paired 95% interval |',
           '|---|---|---:|---:|---:|---|']
    for group in ('all20','remaining15','initial5'):
        for key in ('best_f1','operator_rmse','boundary_ap101'):
            s=d['comparisons'][group][key]
            lines.append(f"| {group} | {key} | {s['baseline_mean']:.4f} | {s['offset_mean']:.4f} | {s['mean_difference']:+.4f} | [{s['ci95'][0]:+.4f}, {s['ci95'][1]:+.4f}] |")
    lines+=['','![Paired results](paired_results.png)','','## Protocol and interpretation','',
            'The first five images motivated this follow-up. The remaining 15 are reported separately to assess '
            'whether the original pattern extends beyond those cases. All 20 are development validation data, '
            'not an independent test set. F1 is the primary boundary endpoint; gradient RMSE is a mechanistic '
            'secondary endpoint and AP101 is descriptive. Intervals are exploratory and unadjusted for multiple comparisons.','',
            'Each comparison uses 16×16 blocks, 8,192 shots per circuit, 400 circuits per image and seeds '
            '42, 4242 and 424242. The only detector option changed is block-minimum subtraction. Native 128×128 '
            'crops, separate human annotations, a two-pixel excluded border, per-map maximum normalization, '
            '31 thresholds, Guo–Hall thinning and one-to-one BSDS-style matching are unchanged. '
            'These are crop-scale diagnostics, not official full-image BSDS scores.','',
            'Per-image F1 and AP101 are computed after averaging matching-count curves across seeds; RMSE is '
            'averaged over seeds. Paired 95% percentile intervals use 10,000 image resamples with seed 20261019. '
            'Simulator seeds are not treated as independent images. Positive F1/AP differences favor subtraction; '
            'negative RMSE differences favor subtraction. All methods still use ideal simulator state preparation; '
            'no runtime or hardware advantage is inferred.','',
            '## Verification','',
            f"All {v['paired_records']} paired records were checked: {v['circuits_replayed']:,} circuits and "
            f"{v['shots_replayed']:,} shots independently replayed. Maximum magnitude discrepancy "
            f"{v['max_magnitude_error']:.3g}. Source/package/input hashes, audit identities, shot totals, "
            'preparation offsets and norms, all boundary-count curves, encoding qubits and RMSE agree. '
            'No new data were downloaded or test contents accessed.','',
            'See [verification](verification.json), [summary](summary.json), [protocol](protocol.json), '
            '[run ledger](run_ledger.json) and [quality checkpoints](quality_review.md).','',
            'Reproduce from the FRQI repository with `.venv/Scripts/python.exe experiments/bsds_offset20.py`. '
            'Use `--verify-only` to replay and regenerate the report without simulations. '
            'Dependencies and dataset attribution are inherited from the [original pilot](../bsds_pilot/report.md).','']
    (OUT/'report.md').write_text('\n'.join(lines),encoding='utf8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker',nargs=2,metavar=('CASE','SEED'))
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    if args.worker:
        from experiments import bsds_pilot
        bsds_pilot.OUTPUT=OUT
        bsds_pilot.worker('QPIE16-offset',args.worker[0],int(args.worker[1]))
    else:
        protocol=prepare()
        if not args.verify_only:run(protocol)
        verify(protocol);report(protocol)
        print('Completed and verified: '+str(OUT/'report.md'),flush=True)
