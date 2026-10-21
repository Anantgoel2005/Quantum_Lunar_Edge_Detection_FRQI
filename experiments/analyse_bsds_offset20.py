"""Independent arithmetic check and interpretation of the frozen offset follow-up."""
from collections import defaultdict
import copy
import hashlib
import json
from pathlib import Path
import re

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/bsds_qpie_offset20'


def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(name,value):(OUT/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')


def main():
    p=read(OUT/'protocol.json');saved=read(OUT/'summary.json')
    assert read(OUT/'verification.json')['status']=='passed'
    assert p['driver_sha256']==sha(ROOT/'experiments/bsds_offset20.py')
    execution=read(OUT/'execution_driver.json')
    assert execution['sha256']==sha(ROOT/'experiments'/execution['driver'])
    groups=defaultdict(list)
    for row in read(OUT/'run_ledger.json'):
        groups[(row['case'],row['config'])].append(read(ROOT/row['path']/'result.json'))
    independent={};cells=0
    for (case,config),runs in groups.items():
        assert len(runs)==3 and {r['seed'] for r in runs}==set(p['seeds'])
        curve=sum((np.asarray(r['boundary_counts'],float) for r in runs))/3
        values=[]
        for cr,sr,cp,sp in curve:
            r=cr/max(sr,1);pr=cp/max(sp,1)
            values.append((2*r*pr/max(r+pr,1e-30),r,pr))
        f=np.array([v[0] for v in values])
        area=sum(max([v[2] for v in values if v[1]>=q],default=0) for q in np.linspace(0,1,101))/101
        result={'best_f1':float(f.max()),'best_threshold':float((f.argmax()+1)/32),
                'boundary_ap101':area,'operator_rmse':sum(r['metrics']['operator_rmse'] for r in runs)/3}
        for key,value in result.items():
            assert np.isclose(value,saved['per_image'][case][config][key],atol=1e-12,rtol=1e-12)
            cells+=1
        independent[(case,config)]=result
    validated=copy.deepcopy(saved)
    for group,ids in [('all20',p['cases']),('initial5',p['initial5']),('remaining15',p['remaining15'])]:
        for metric in ('best_f1','operator_rmse','boundary_ap101'):
            a=np.array([independent[(i,'QPIE16-offset')][metric] for i in ids])
            b=np.array([independent[(i,'QPIE16')][metric] for i in ids]);difference=a-b
            rng=np.random.default_rng(20261019)
            # Independent frequency-weighted bootstrap arithmetic.
            indices=rng.integers(0,len(ids),(10000,len(ids)))
            frequencies=np.stack([(indices==i).sum(axis=1) for i in range(len(ids))],axis=1)
            means=frequencies@difference/len(ids)
            target=saved['comparisons'][group][metric]
            for key,value in [('baseline_mean',b.mean()),('offset_mean',a.mean()),('mean_difference',difference.mean())]:
                assert np.isclose(value,target[key],atol=1e-12,rtol=1e-12);cells+=1
            np.testing.assert_allclose(np.percentile(means,[2.5,97.5]),target['ci95'],atol=1e-12,rtol=1e-12)
            assert target['improved_images']==int((difference>0).sum())
            target=validated['comparisons'][group][metric]
            target['increased_images']=target.pop('improved_images')
            target['improved_images']=int(((difference<0) if metric=='operator_rmse' else (difference>0)).sum())
    validated['count_convention']='Improved means higher F1/AP101 or lower RMSE; increased always means positive difference. Frozen raw summary used a generic positive-difference count.'
    write('validated_summary.json',validated)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(15,5),layout='constrained')
    for ax,key,title in zip(axes,('best_f1','boundary_ap101','operator_rmse'),
                           ('Image-optimal F1 ↑','Boundary AP101 ↑','Gradient RMSE ↓')):
        maximum=0.
        for case in p['cases']:
            y=[independent[(case,c)][key] for c in ('QPIE16','QPIE16-offset')]
            maximum=max(maximum,max(y))
            ax.plot([0,1],y,color='#94a3b8' if case in p['initial5'] else '#2563eb',alpha=.6,marker='o',markersize=3)
        ax.set_xticks([0,1],['Baseline','Subtract block\nminimum']);ax.set_xlim(-.15,1.15)
        ax.set_ylim(0,maximum*1.1 if key=='operator_rmse' else 1)
        ax.set_title(title,fontsize=12);ax.grid(axis='y',alpha=.2)
    fig.suptitle('QPIE: 20 paired BSDS validation crops',fontweight='bold')
    fig.supxlabel('Blue: remaining 15 images; gray: initial five. Three seeds per image; equal shot budget.',fontsize=10)
    fig.savefig(OUT/'paired_results.png',dpi=170);fig.savefig(OUT/'paired_results.pdf');plt.close(fig)
    # Reused baseline and initial experiment must reproduce their original summaries.
    parent=read(ROOT/'results/bsds_pilot/summary.json')
    row=next(r for r in parent['primary20']['summary'] if r['config']=='QPIE16')
    assert np.isclose(row['macro_best_f1'],saved['comparisons']['all20']['best_f1']['baseline_mean'])
    old=next(r for r in parent['paired_efficiency'] if r['a']=='QPIE16-offset')
    new=saved['comparisons']['initial5']['best_f1']
    assert np.isclose(new['mean_difference'],old['mean_difference'])
    np.testing.assert_allclose(new['ci95'],old['ci95'],atol=1e-12,rtol=1e-12)
    for name,value in p['frozen_parent_files'].items():assert sha(ROOT/'results/bsds_pilot'/name)==value
    first=saved['comparisons']['remaining15']['best_f1'];all20=saved['comparisons']['all20']['best_f1']
    rmse=saved['comparisons']['remaining15']['operator_rmse']
    ap=saved['comparisons']['all20']['boundary_ap101']
    boundary='supports a positive development effect' if first['ci95'][0]>0 else ('supports a negative development effect' if first['ci95'][1]<0 else 'does not resolve the direction of the boundary effect')
    decision=('Treat block-minimum subtraction as the preferred candidate for the next validation study; keep production defaults unchanged pending a frozen independent test.'
              if first['ci95'][0]>0 else 'Keep the current default. Do not claim a reliable improvement in primary boundary F1; further validation or operator/filtering work is needed.')
    text=(OUT/'report.md').read_text(encoding='utf8')
    text=text.split('## Follow-up decision')[0].rstrip()
    text=text.replace('[summary](summary.json)','[verified summary](validated_summary.json)')
    text+='\n\n## Follow-up decision\n\n'
    text+=(f"On the remaining 15 images, subtraction changes mean F1 by {first['mean_difference']:+.4f} "
           f"(95% interval [{first['ci95'][0]:+.4f}, {first['ci95'][1]:+.4f}]); this {boundary}. "
           f"Across all 20, the change is {all20['mean_difference']:+.4f}. "
           f"Remaining-15 gradient RMSE changes by {rmse['mean_difference']:+.4f} "
           f"([{rmse['ci95'][0]:+.4f}, {rmse['ci95'][1]:+.4f}]).\n\n{decision}\n\n"
           f"The descriptive AP101 endpoint improves from {ap['baseline_mean']:.4f} to {ap['offset_mean']:.4f} "
           f"on all 20 images (difference {ap['mean_difference']:+.4f}, interval "
           f"[{ap['ci95'][0]:+.4f}, {ap['ci95'][1]:+.4f}]). This suggests improved boundary ranking even though "
           'the primary image-optimal F1 does not establish a gain. These are distinct outcomes, not a uniform win.\n\n'
           'Boundary quality and gradient estimation are separate endpoints. Thresholds are selected on these validation '
           'crops; these results establish neither unseen-image performance nor lunar-rim accuracy. '
           'Retain BSDS for development and obtain independently traced lunar rims for domain evaluation.\n\n'
           'The independent arithmetic verifier checked all image metrics and nine frequency-weighted bootstrap intervals, '
           'and reproduced the original baseline and five-image effect. The verified summary corrects a generic '
           'raw count label so lower RMSE counts as improvement. Numeric means, intervals and scientific comparisons '
           'are unchanged. See [summary verification](summary_verification.json).\n\n'
           'After the simulation/replay driver, run `.venv/Scripts/python.exe experiments/analyse_bsds_offset20.py` '
           'to reproduce this verified interpretation.\n')
    (OUT/'report.md').write_text(text,encoding='utf8')
    links=[s for s in re.findall(r'\]\(([^)]+)\)',text) if not s.startswith('http')]
    # The quality log is written by the checkpoint workflow; all other links must already exist.
    assert all((OUT/s).is_file() for s in links if s not in ('quality_review.md','summary_verification.json'))
    result={'status':'passed','independent_metric_cells':cells,'bootstrap_intervals_checked':9,
            'new_circuits':45*400,'new_simulator_shots':45*400*8192,
            'paired_image_metrics':len(independent),'parent_hashes_unchanged':True,
            'original_baseline_and_initial5_reproduced':True,'raw_positive_count_label_corrected':True,
            'verifier_sha256':sha(__file__),'driver_hash_verified':True,'execution_driver_hash_verified':True}
    write('summary_verification.json',result)
    print(json.dumps(result,indent=2))
    print(json.dumps(saved['comparisons'],indent=2))


if __name__=='__main__':main()
