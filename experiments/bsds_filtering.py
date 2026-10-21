"""Frozen matched output-filtering experiment on existing BSDS validation maps."""
from concurrent.futures import ProcessPoolExecutor,as_completed
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evaluation.bsds_boundary import evaluate_curve,curve_summary

OUT=ROOT/'results/bsds_filtering'
PILOT=ROOT/'results/bsds_pilot'
OFFSET=ROOT/'results/bsds_qpie_offset20'
SIGMAS=(0.,.5,1.)
CONFIGS=('QPIE16','QPIE16-offset','Exact-gradient')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.part')
    temporary.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8');temporary.replace(path)


def exact(image):
    image=np.asarray(image,dtype=float);dx=np.zeros(image.shape);dy=dx.copy()
    dx[:,1:]=np.diff(image,axis=1);dy[1:,:]=np.diff(image,axis=0)
    return np.hypot(dx,dy)


def smooth(magnitude,sigma):
    if sigma not in SIGMAS:raise ValueError('Sigma is outside the frozen grid')
    return magnitude.copy() if sigma==0 else gaussian_filter(magnitude,sigma,mode='reflect',radius=int(np.ceil(3*sigma)))


def rmse(a,b):return float(np.sqrt(np.mean((a[2:-2,2:-2]-b[2:-2,2:-2])**2)))


def aggregate(records):
    metrics=curve_summary(np.mean([r['boundary_counts'] for r in records],axis=0))
    for key in ('matched_rmse','raw_rmse'):metrics[key]=float(np.mean([r[key] for r in records]))
    return metrics


def interval(values):
    values=np.asarray(values,float)
    if values.ndim!=1 or len(values)!=20:raise ValueError('Exactly twenty paired image differences required')
    rng=np.random.default_rng(20261019)
    samples=values[rng.integers(0,20,(10000,20))].mean(axis=1)
    return {'mean_difference':float(values.mean()),'ci95':np.quantile(samples,[.025,.975]).tolist(),'images':20}


def prepare():
    assert read(PILOT/'verification.json')['status']=='passed'
    assert read(OFFSET/'verification.json')['status']=='passed'
    parent=read(PILOT/'protocol.json');manifest=read(PILOT/'dataset.json')
    ledger=read(OFFSET/'run_ledger.json')
    files=[PILOT/name for name in ('protocol.json','dataset.json','summary.json','verification.json','summary_verification.json','report.md')]
    files += [OFFSET/name for name in ('protocol.json','run_ledger.json','validated_summary.json','verification.json','summary_verification.json','report.md')]
    for row in ledger:files.extend([ROOT/row['path']/'maps.npz',ROOT/row['path']/'result.json'])
    for case in manifest['cases']:
        files.extend([PILOT/'cases'/case['id']/name for name in ('input.png','references.npz','Exact-gradient.json','Sobel.json','Robinson.json')])
    protocol={'schema':1,'cases':[c['id'] for c in manifest['cases']], 'seeds':parent['seeds'],
              'configs':list(CONFIGS),'sigmas':list(SIGMAS),'maps':420,'new_quantum_runs':0,
              'filter':'Gaussian output magnitude; sigma in native pixels; radius=ceil(3*sigma); mode=reflect; full128map before per-map maximum normalization and124interior scoring',
              'operator':'Smooth magnitude, not input image or gradient components; no directional NMS added',
              'statistics':'F1 primary; AP101 descriptive; matched-target and raw-target RMSE separate. Average seed count curves before image optima; average seed RMSE. Paired10000imagebootstrap seed20261019,unadjusted percentile95%. Difference-in-differences forF1/AP: (Qfiltered-Qraw)-(exactfiltered-exactraw).',
              'scope':'Predefined full grid reported on development validation crops; no test tuning, default change, full-image BSDS certification or hardware claim',
              'reference_methods':['Sobel','Robinson'],
              'computational_hashes':{p:sha(ROOT/p) for p in ('experiments/bsds_filtering.py','experiments/verify_bsds_filtering.py','evaluation/bsds_boundary.py')},
              'source_hashes':parent['source_hashes'],'versions':parent['versions'],
              'input_hashes':{str(p.relative_to(ROOT)):sha(p) for p in files}}
    path=OUT/'protocol.json';OUT.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if read(path)!=protocol:raise ValueError('Frozen filtering protocol/source/input drift')
    else:write(path,protocol)
    return protocol


def check_hashes(p):
    for relative,value in p['computational_hashes'].items():assert sha(ROOT/relative)==value
    for relative,value in p['input_hashes'].items():assert sha(ROOT/relative)==value
    for relative,value in p['source_hashes'].items():assert sha(ROOT.parent/relative)==value
    for package,value in p['versions'].items():assert version(package)==value


def case_worker(case):
    p=read(OUT/'protocol.json');folder=OUT/'cases'/case;path=folder/'results.json'
    if path.exists():
        assert read(path)['protocol_sha256']==sha(OUT/'protocol.json')
        return case
    folder.mkdir(parents=True,exist_ok=True)
    image=np.array(Image.open(PILOT/'cases'/case/'input.png'))
    refs=np.load(PILOT/'cases'/case/'references.npz')['boundaries']
    target=exact(image);targets={s:smooth(target,s) for s in SIGMAS}
    ledger=[r for r in read(OFFSET/'run_ledger.json') if r['case']==case]
    arrays={};records=[]
    for ci,config in enumerate(CONFIGS):
        seeds=[None] if config=='Exact-gradient' else p['seeds']
        for seed in seeds:
            source=next((ROOT/r['path'] for r in ledger if r['config']==config and r['seed']==seed),None)
            raw=target if source is None else np.load(source/'maps.npz')['magnitude']
            parent=read(PILOT/'cases'/case/'Exact-gradient.json') if source is None else read(source/'result.json')
            for si,sigma in enumerate(SIGMAS):
                magnitude=smooth(raw,sigma)
                strength=magnitude/magnitude.max() if magnitude.max() else magnitude.copy()
                counts=np.array(parent['boundary_counts']) if sigma==0 else evaluate_curve(strength[2:-2,2:-2],refs[:,2:-2,2:-2])
                key=f'c{ci}_s{si}_{seed}'
                arrays[key+'_magnitude']=magnitude;arrays[key+'_strength']=strength
                records.append({'case':case,'config':config,'seed':seed,'sigma':sigma,'array_key':key,
                                'boundary_counts':counts.tolist(),'matched_rmse':rmse(magnitude,targets[sigma]),
                                'raw_rmse':rmse(magnitude,target),'metrics':curve_summary(counts)})
    np.savez_compressed(folder/'maps.npz',**arrays)
    write(path,{'protocol_sha256':sha(OUT/'protocol.json'),'records':records})
    return case


def summarize(p):
    per_image={};all_records=[]
    for case in p['cases']:
        records=read(OUT/'cases'/case/'results.json')['records'];all_records.extend(records)
        per_image[case]={}
        for config in CONFIGS:
            per_image[case][config]={}
            for sigma in SIGMAS:
                chosen=[r for r in records if r['config']==config and r['sigma']==sigma]
                assert len(chosen)==(1 if config=='Exact-gradient' else 3)
                per_image[case][config][str(sigma)]=aggregate(chosen)
    assert len(all_records)==420
    means=[];effects=[]
    for config in CONFIGS:
        for sigma in SIGMAS:
            metrics={k:float(np.mean([per_image[i][config][str(sigma)][k] for i in p['cases']]))
                     for k in ('best_f1','boundary_ap101','matched_rmse','raw_rmse')}
            means.append({'config':config,'sigma':sigma,**metrics})
            if sigma==0:continue
            for key in metrics:
                difference=np.array([per_image[i][config][str(sigma)][key]-per_image[i][config]['0.0'][key] for i in p['cases']])
                effects.append({'config':config,'sigma':sigma,'metric':key,'kind':'change',**interval(difference)})
                if config!='Exact-gradient' and key in ('best_f1','boundary_ap101'):
                    other=np.array([per_image[i]['Exact-gradient'][str(sigma)][key]-per_image[i]['Exact-gradient']['0.0'][key] for i in p['cases']])
                    effects.append({'config':config,'sigma':sigma,'metric':key,'kind':'excess_gain',**interval(difference-other)})
    refs=read(PILOT/'summary.json')['primary20']
    write(OUT/'summary.json',{'per_image':per_image,'means':means,'effects':effects,
          'references':[r for r in refs['summary'] if r['config'] in p['reference_methods']]})


if __name__=='__main__':
    p=prepare();check_hashes(p)
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(case_worker,c) for c in p['cases']]
        for number,future in enumerate(as_completed(futures),1):
            print(f'Evaluated {number}/20 cases: {future.result()}',flush=True)
    summarize(p);check_hashes(p)
    print('Filtering matrix complete; run verify_bsds_filtering.py next',flush=True)
