"""Independent dense convolution, boundary replay and summary arithmetic checks."""
from concurrent.futures import ProcessPoolExecutor,as_completed
from importlib.metadata import version
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy.signal import convolve2d

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evaluation.bsds_boundary import evaluate_curve
OUT=ROOT/'results/bsds_filtering'
PILOT=ROOT/'results/bsds_pilot'
OFFSET=ROOT/'results/bsds_qpie_offset20'


def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dense_filter(array,sigma):
    if sigma==0:return array.copy()
    radius=int(np.ceil(3*sigma));x=np.arange(-radius,radius+1,dtype=float)
    weights=np.exp(-(x*x)/(2*sigma*sigma));weights/=weights.sum()
    return convolve2d(array,np.outer(weights,weights),mode='same',boundary='symm')


def scalar_scores(curve):
    curve=np.asarray(curve,float)
    r=curve[:,0]/np.maximum(curve[:,1],1);p=curve[:,2]/np.maximum(curve[:,3],1)
    f=2*r*p/np.maximum(r+p,1e-30);best=int(f.argmax())
    ap=sum(max((pp for pp,rr in zip(p,r) if rr>=q),default=0) for q in np.linspace(0,1,101))/101
    return {'best_f1':float(f[best]),'best_threshold':float((best+1)/32),
            'precision':float(p[best]),'recall':float(r[best]),'boundary_ap101':ap}


def verify_case(case):
    p=read(OUT/'protocol.json');info=read(OUT/'cases'/case/'results.json')
    assert info['protocol_sha256']==sha(OUT/'protocol.json')
    records=info['records'];maps=np.load(OUT/'cases'/case/'maps.npz')
    expected={(c,s,seed) for c in p['configs'] for s in p['sigmas']
              for seed in ([None] if c=='Exact-gradient' else p['seeds'])}
    assert len(records)==21 and {(r['config'],r['sigma'],r['seed']) for r in records}==expected
    pixels=np.array(Image.open(PILOT/'cases'/case/'input.png'),dtype=float)
    gx=np.zeros(pixels.shape);gy=gx.copy()
    gx[:,1:]=pixels[:,1:]-pixels[:,:-1];gy[1:,:]=pixels[1:,:]-pixels[:-1,:]
    target=np.sqrt(gx*gx+gy*gy)
    refs=np.load(PILOT/'cases'/case/'references.npz')['boundaries']
    ledger=[r for r in read(OFFSET/'run_ledger.json') if r['case']==case]
    raw={('Exact-gradient',None):target}
    parents={('Exact-gradient',None):read(PILOT/'cases'/case/'Exact-gradient.json')}
    for row in ledger:
        key=(row['config'],row['seed']);raw[key]=np.load(ROOT/row['path']/'maps.npz')['magnitude']
        parents[key]=read(ROOT/row['path']/'result.json')
    largest=0.;zero=0
    for r in records:
        assert r['case']==case
        key=r['array_key'];magnitude=maps[key+'_magnitude'];strength=maps[key+'_strength']
        independent=dense_filter(raw[(r['config'],r['seed'])],r['sigma'])
        largest=max(largest,float(np.max(np.abs(magnitude-independent))))
        np.testing.assert_allclose(magnitude,independent,rtol=1e-12,atol=5e-12)
        expected_strength=magnitude/magnitude.max() if magnitude.max() else magnitude
        np.testing.assert_array_equal(strength,expected_strength)
        counts=evaluate_curve(strength[2:-2,2:-2],refs[:,2:-2,2:-2])
        np.testing.assert_array_equal(counts,r['boundary_counts'])
        assert counts.shape==(31,4) and np.isfinite(counts).all()
        assert np.all(counts[:,0]<=counts[:,1]) and np.all(counts[:,2]<=counts[:,3])
        for name,value in scalar_scores(counts).items():assert np.isclose(value,r['metrics'][name],atol=1e-12,rtol=1e-12)
        filtered_target=dense_filter(target,r['sigma'])
        for name,reference in [('matched_rmse',filtered_target),('raw_rmse',target)]:
            value=float(np.sqrt(np.mean(np.square(independent[2:-2,2:-2]-reference[2:-2,2:-2]))))
            assert np.isclose(value,r[name],atol=5e-12,rtol=1e-12)
        if r['sigma']==0:
            np.testing.assert_array_equal(counts,parents[(r['config'],r['seed'])]['boundary_counts']);zero+=1
            if r['config']!='Exact-gradient':assert np.isclose(r['raw_rmse'],parents[(r['config'],r['seed'])]['metrics']['operator_rmse'],atol=1e-12)
    result={}
    for config in p['configs']:
        result[config]={}
        for sigma in p['sigmas']:
            chosen=[r for r in records if r['config']==config and r['sigma']==sigma]
            curve=sum((np.asarray(r['boundary_counts'],float) for r in chosen))/len(chosen)
            metrics=scalar_scores(curve)
            for key in ('matched_rmse','raw_rmse'):metrics[key]=sum(r[key] for r in chosen)/len(chosen)
            result[config][str(sigma)]=metrics
    return case,result,largest,zero


def main():
    p=read(OUT/'protocol.json');summary=read(OUT/'summary.json')
    for relative,value in p['computational_hashes'].items():assert sha(ROOT/relative)==value
    for relative,value in p['input_hashes'].items():assert sha(ROOT/relative)==value
    for relative,value in p['source_hashes'].items():assert sha(ROOT.parent/relative)==value
    for package,value in p['versions'].items():assert version(package)==value
    collected={};maximum=0.;zeros=0
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(verify_case,c) for c in p['cases']]
        for number,future in enumerate(as_completed(futures),1):
            case,metrics,error,zero=future.result();collected[case]=metrics
            maximum=max(maximum,error);zeros+=zero
            print(f'Independently verified {number}/20 cases',flush=True)
    cells=0
    for case,configs in collected.items():
        for config,grid in configs.items():
            for sigma,metrics in grid.items():
                for key,value in metrics.items():
                    assert np.isclose(value,summary['per_image'][case][config][sigma][key],atol=1e-12,rtol=1e-12);cells+=1
    assert len(summary['means'])==9
    for row in summary['means']:
        for key in ('best_f1','boundary_ap101','matched_rmse','raw_rmse'):
            expected=sum(collected[i][row['config']][str(row['sigma'])][key] for i in p['cases'])/20
            assert np.isclose(expected,row[key],atol=1e-12,rtol=1e-12);cells+=1
    assert len(summary['effects'])==32
    for row in summary['effects']:
        values=[]
        for i in p['cases']:
            grid=collected[i][row['config']]
            change=grid[str(row['sigma'])][row['metric']]-grid['0.0'][row['metric']]
            if row['kind']=='excess_gain':
                exact=collected[i]['Exact-gradient'];change-=exact[str(row['sigma'])][row['metric']]-exact['0.0'][row['metric']]
            else:assert row['kind']=='change'
            values.append(change)
        difference=np.array(values);rng=np.random.default_rng(20261019)
        indices=rng.integers(0,20,(10000,20))
        frequencies=np.stack([(indices==i).sum(axis=1) for i in range(20)],axis=1)
        draws=frequencies@difference/20
        assert np.isclose(difference.mean(),row['mean_difference'],atol=1e-12,rtol=1e-12)
        np.testing.assert_allclose(np.percentile(draws,[2.5,97.5]),row['ci95'],atol=1e-12,rtol=1e-12)
    reference_cells=0
    for row in summary['references']:
        data=[scalar_scores(read(PILOT/'cases'/i/(row['config']+'.json'))['boundary_counts']) for i in p['cases']]
        assert np.isclose(np.mean([d['best_f1'] for d in data]),row['macro_best_f1'])
        assert np.isclose(np.mean([d['boundary_ap101'] for d in data]),row['macro_boundary_ap101']);reference_cells+=2
    # Hash inputs again after evaluation to catch changes during the run.
    for relative,value in p['input_hashes'].items():assert sha(ROOT/relative)==value
    verification={'status':'passed','map_records':420,'independent_dense_convolutions':420,
                  'max_dense_filter_error':maximum,'zero_sigma_parent_records_reproduced':zeros,
                  'summary_metric_cells':cells,'paired_bootstrap_intervals':32,'reference_cells':reference_cells,
                  'input_files_unchanged':len(p['input_hashes']),'new_quantum_runs':0,
                  'test_content_accessed':False,'verifier_sha256':sha(__file__),
                  'limits':'Boundary matching is the tested shared crop evaluator, not independently certified Berkeley MATLAB code; alternative dense filtering checked within floating-point tolerance.'}
    (OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf8')
    print(json.dumps(verification,indent=2))


if __name__=='__main__':main()
