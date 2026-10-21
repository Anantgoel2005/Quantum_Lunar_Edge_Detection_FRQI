"""Independent summary arithmetic and frozen provenance check for the BSDS pilot.

Imports neither the pilot aggregation functions nor the boundary evaluator.
"""
from collections import defaultdict
import hashlib
from importlib.metadata import version
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OUT=ROOT/'results/bsds_pilot'
CACHE=ROOT/'data/bsds500'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def metrics(curve):
    curve=np.asarray(curve,dtype=float)
    recall=curve[:,0]/np.maximum(curve[:,1],1)
    precision=curve[:,2]/np.maximum(curve[:,3],1)
    f1=2*precision*recall/np.maximum(precision+recall,1e-30)
    best=int(f1.argmax())
    area=sum(max((p for p,r in zip(precision,recall) if r>=q),default=0.)
             for q in np.linspace(0,1,101))/101
    return {'best_f1':float(f1[best]),'boundary_ap101':float(area),
            'best_threshold':float((best+1)/32)}


def main():
    from scipy.io import loadmat
    from classical.sobel import sobel_edge
    from classical.canny import canny_edge_auto
    from classical.robinson_compass import robinson_edge
    protocol=json.loads((OUT/'protocol.json').read_text())
    manifest=json.loads((OUT/'dataset.json').read_text())
    summary=json.loads((OUT/'summary.json').read_text())
    assert manifest['protocol_sha256']==sha(OUT/'protocol.json')
    for relative,value in protocol['source_hashes'].items():assert sha(ROOT.parent/relative)==value
    for relative,value in protocol['pilot_hashes'].items():assert sha(ROOT/relative)==value
    for package,value in protocol['versions'].items():assert version(package)==value
    for case in manifest['cases']:
        assert case['split']=='val' and '/val/' in case['image'] and '/val/' in case['annotations']
        assert sha(CACHE/case['image'])==case['source_image_sha256']
        assert sha(CACHE/case['annotations'])==case['source_annotations_sha256']
        image=np.array(Image.open(OUT/'cases'/case['id']/'input.png'))
        refs=np.load(OUT/'cases'/case['id']/'references.npz')['boundaries']
        assert hashlib.sha256(image.tobytes()).hexdigest()==case['input_pixel_sha256']
        assert hashlib.sha256(refs.tobytes()).hexdigest()==case['references_pixel_sha256']
        raw_image=np.array(Image.open(CACHE/case['image']).convert('L'))
        x,y,w,h=case['crop_xywh']
        assert (w,h)==(128,128) and x==(raw_image.shape[1]-128)//2 and y==(raw_image.shape[0]-128)//2
        np.testing.assert_array_equal(image,raw_image[y:y+h,x:x+w])
        raw=loadmat(CACHE/case['annotations'],simplify_cells=True)['groundTruth']
        cells=[raw] if isinstance(raw,dict) else list(np.atleast_1d(raw).flat)
        masks=[]
        for cell in cells:
            mask=cell['Boundaries']
            if hasattr(mask,'toarray'):mask=mask.toarray()
            masks.append(np.asarray(mask,dtype=bool)[y:y+h,x:x+w])
        np.testing.assert_array_equal(refs,np.stack(masks))
        def exact_control(inequality=False):
            values=np.floor(image.astype(float)*15/255) if inequality else image.astype(float)
            dx=np.zeros(image.shape);dy=np.zeros(image.shape)
            horizontal=np.diff(values,axis=1);vertical=np.diff(values,axis=0)
            dx[:,1:]=(horizontal!=0) if inequality else horizontal
            dy[1:,:]=(vertical!=0) if inequality else vertical
            return np.hypot(dx,dy)
        controls={'Sobel':sobel_edge(image),'Canny':canny_edge_auto(image),
                  'Robinson':robinson_edge(image)[0],
                  'Exact-gradient':exact_control(),'Exact-inequality':exact_control(True)}
        for name,strength in controls.items():
            strength=strength.astype(float)
            if strength.max():strength/=strength.max()
            np.testing.assert_array_equal(strength,np.load(OUT/'cases'/case['id']/(name+'.npz'))['strength'])
    driver=json.loads((OUT/'execution_driver.json').read_text())
    assert sha(ROOT/'experiments'/driver['driver'])==driver['sha256']
    records=[json.loads(p.read_text()) for p in (OUT/'runs').glob('*/result.json')]
    records += [json.loads(p.read_text()) for p in (OUT/'cases').glob('*/*.json')]
    assert len(records)==340
    checked=0
    independent={}
    for name,ids in [('primary20',{c['id'] for c in manifest['cases']}),
                     ('efficiency5',set(protocol['efficiency_subset']))]:
        independent[name]={}
        for row in summary[name]['summary']:
            config=row['config']
            groups=defaultdict(list)
            for r in records:
                if r['config']==config and r['case'] in ids:groups[r['case']].append(r)
            assert len(groups)==row['images']
            data={}
            curves=[]
            for case_id,runs in groups.items():
                expected=3 if config in protocol['configs'] else 1
                assert len(runs)==expected
                if expected==3:assert {r['seed'] for r in runs}==set(protocol['seeds'])
                curve=sum((np.asarray(r['boundary_counts'],float) for r in runs))/len(runs)
                assert curve.shape==(31,4)
                actual=metrics(curve);data[case_id]=actual;curves.append(curve)
                saved=summary[name]['per_image'][config][case_id]
                for key,value in actual.items():
                    assert np.isclose(value,saved[key],atol=1e-12,rtol=1e-12),(name,config,case_id,key)
                    checked+=1
            pooled=metrics(sum(curves))
            actual_summary={'macro_best_f1':float(np.mean([r['best_f1'] for r in data.values()])),
                            'macro_boundary_ap101':float(np.mean([r['boundary_ap101'] for r in data.values()])),
                            'pooled_best_f1':pooled['best_f1'],'pooled_threshold':pooled['best_threshold']}
            for key,value in actual_summary.items():
                assert np.isclose(value,row[key],atol=1e-12,rtol=1e-12),(name,config,key)
                checked+=1
            rmses=[r['metrics']['operator_rmse'] for runs in groups.values() for r in runs
                   if 'operator_rmse' in r['metrics']]
            if rmses:
                assert np.isclose(np.mean(rmses),row['macro_operator_rmse'],atol=1e-12,rtol=1e-12)
                checked+=1
            else:assert row['macro_operator_rmse'] is None
            independent[name][config]=data
    for effect in summary['paired_efficiency']:
        ids=protocol['efficiency_subset']
        difference=np.array([independent['efficiency5'][effect['a']][i]['best_f1']-
                             independent['efficiency5'][effect['b']][i]['best_f1'] for i in ids])
        rng=np.random.default_rng(20261019)
        samples=difference[rng.integers(0,len(ids),(10000,len(ids)))].mean(axis=1)
        assert np.isclose(difference.mean(),effect['mean_difference'],atol=1e-12)
        np.testing.assert_allclose(np.quantile(samples,[.025,.975]),effect['ci95'],atol=1e-12,rtol=1e-12)
    result={'status':'passed','records_checked':len(records),'metric_cells_recomputed':checked,
            'classical_control_maps_freshly_recomputed':100,
            'paired_bootstrap_intervals_recomputed':len(summary['paired_efficiency']),
            'raw_asset_hashes':40,'input_reference_pixel_hashes':40,
            'raw_image_and_MAT_crops_independently_rederived':20,
            'frozen_live_sources':len(protocol['source_hashes']),
            'frozen_pilot_sources':len(protocol['pilot_hashes']),
            'execution_driver_hash':driver['sha256'],
            'verifier_sha256':sha(__file__),
            'independence':'Separate summary arithmetic, imports neither pilot aggregation nor boundary matching code'}
    (OUT/'summary_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
