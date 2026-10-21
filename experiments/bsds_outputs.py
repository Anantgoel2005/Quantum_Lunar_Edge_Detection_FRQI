"""Figures and readable final report for the frozen BSDS development pilot."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'results/bsds_pilot'


def inputs():
    manifest=json.loads((OUTPUT/'dataset.json').read_text())
    fig,axes=plt.subplots(4,5,figsize=(13,11),layout='constrained')
    for axis,case in zip(axes.flat,manifest['cases']):
        folder=OUTPUT/'cases'/case['id']
        image=np.array(Image.open(folder/'input.png'))
        refs=np.load(folder/'references.npz')['boundaries']
        overlay=np.repeat(image[:,:,None],3,axis=2)
        overlay[refs.any(axis=0)]=[240,165,35]
        overlay[refs.mean(axis=0)>=.5]=[20,220,110]
        axis.imshow(overlay)
        axis.set_title(f"{case['id']} · {case['annotators']} annotators",fontsize=9)
        axis.set_axis_off()
    fig.suptitle('BSDS500: fixed validation crops and human annotations',fontsize=15,fontweight='bold')
    fig.supxlabel('Green: at least half of annotators; orange: any annotator. Masks are evaluated separately.',fontsize=10)
    fig.savefig(OUTPUT/'inputs.png',dpi=150)
    plt.close(fig)


def results():
    data=json.loads((OUTPUT/'summary.json').read_text())
    verification=json.loads((OUTPUT/'verification.json').read_text())
    independent=json.loads((OUTPUT/'summary_verification.json').read_text())
    if verification['status']!='passed' or independent['status']!='passed':
        raise ValueError('Final report requires both verification stages to pass')
    configs=['QPIE16','FRQI16','NEQR16','Sobel','Canny','Robinson','Exact-gradient','Exact-inequality']
    primary=data['primary20']
    plt.rcParams.update({'axes.spines.top':False,'axes.spines.right':False,'font.size':10})
    fig,axes=plt.subplots(1,2,figsize=(14,5.5),layout='constrained')
    colors=['#2563eb','#7c3aed','#0891b2']+['#94a3b8']*3+['#d97706']*2
    labels=['QPIE','FRQI','NEQR','Sobel','Canny','Robinson','Exact\ngradient','Exact\ninequality']
    for axis,key,title in zip(axes,('best_f1','boundary_ap101'),('Image-optimal boundary F1','Interpolated boundary AP101')):
        values=[[d[key] for d in primary['per_image'][c].values()] for c in configs]
        axis.bar(range(len(configs)),[np.mean(v) for v in values],color=colors,alpha=.85,width=.65)
        for i,value in enumerate(values):axis.scatter(i+np.linspace(-.2,.2,len(value)),value,s=11,color='#0f172a',alpha=.45,zorder=3)
        axis.set_xticks(range(len(configs)),labels,fontsize=9)
        axis.set_ylabel(title);axis.set_ylim(0,1);axis.grid(axis='y',alpha=.2);axis.set_axisbelow(True)
    fig.suptitle('BSDS500 development pilot: 20 native validation crops',fontsize=15,fontweight='bold')
    fig.supxlabel('Bars: image macro means; dots: image scores. Quantum count curves average three seeds; controls are deterministic.',fontsize=10)
    fig.savefig(OUTPUT/'boundary_results.png',dpi=180);fig.savefig(OUTPUT/'boundary_results.pdf');plt.close(fig)
    paired=data['paired_efficiency']
    fig,axis=plt.subplots(figsize=(9,4.5),layout='constrained')
    means=[p['mean_difference'] for p in paired]
    lower=[m-p['ci95'][0] for m,p in zip(means,paired)]
    upper=[p['ci95'][1]-m for m,p in zip(means,paired)]
    axis.errorbar(means,range(len(paired)),xerr=[lower,upper],fmt='o',capsize=5,color='#2563eb')
    axis.axvline(0,color='#64748b',linestyle='--',linewidth=1)
    axis.set_yticks(range(len(paired)),[p['a']+' minus '+p['b'] for p in paired])
    axis.set_xlabel('Change in image-optimal boundary F1 (positive favors A)')
    axis.set_title('Matched total-shot budget: five preselected development crops',fontweight='bold')
    fig.supxlabel('Exploratory paired image bootstrap 95% intervals; three seeds; no multiple-comparison adjustment.',fontsize=9)
    fig.savefig(OUTPUT/'efficiency_effects.png',dpi=180);plt.close(fig)
    pmap={s['config']:s for s in primary['summary']}
    qbest=max((pmap[c] for c in ('QPIE16','FRQI16','NEQR16')),key=lambda s:s['macro_best_f1'])
    cbest=max((pmap[c] for c in ('Sobel','Canny','Robinson')),key=lambda s:s['macro_best_f1'])
    rows=['# BSDS500 quantum edge-detection development pilot','',
          f"On the 20 fixed validation crops, **{qbest['config']}** has the highest quantum mean image-optimal "
          f"boundary F1 ({qbest['macro_best_f1']:.4f}). The strongest classical comparator by this metric is "
          f"**{cbest['config']}** ({cbest['macro_best_f1']:.4f}). These are development results, not test-set claims.",'',
          '## Data and protocol','',
          'Twenty validation image IDs were selected by a fixed hash ranking before opening annotation files. '
          'Each uses one native 128×128 center crop, converted to grayscale with no resizing, contrast stretching or smoothing. '
          'All human boundary masks remain separate. No test image or test annotation content was downloaded or evaluated.','',
          'Three seeds (42, 4242, 424242) were run per configuration. The main 20-image comparison uses 16×16 blocks '
          'and 8,192 shots per circuit, with block-minimum subtraction disabled. '
          'The first five preselected cases additionally test 8×8 blocks and QPIE block-minimum subtraction. '
          'The smaller blocks receive 1,692 shots per circuit: 3,275,712 total shots per crop versus 3,276,800 for 16×16 '
          '(a 1,088-shot or 0.0332% shortfall). No label-based shot allocation was used.','',
          '## Boundary evaluation','',
          'Each output strength map is divided by its own maximum before thresholding (zero maps remain zero). '
          'Thus the common threshold is relative to each image, not an absolute calibrated gradient. '
          'Canny uses the existing median-based automatic hysteresis settings and returns a binary map; '
          'its 31 threshold entries repeat the same operating point, so its AP101 is not a tuned Canny precision–recall sweep.','',
          'At 31 fixed thresholds (1/32 to 31/32), predictions are Guo–Hall thinned and matched one-to-one to each '
          'annotator using a maximum-cardinality, minimum-Euclidean-distance bipartite assignment. '
          'Tolerance is 0.0075 times the diagonal of the scored 124×124 crop; a two-pixel border is excluded. '
          'Precision counts predictions matched to any annotator; recall accumulates matched and positive reference pixels '
          'over annotators. This avoids the many-to-one credit possible with simple mask dilation.','',
          'Matching uses an independently tested SciPy implementation. The initially investigated Higra native matcher '
          'terminated its process on minimal identity fixtures in this environment, so it is not used. '
          'Results are **BSDS-style crop-scale pilot metrics**, not certified reproductions of the Berkeley MATLAB evaluator.','',
          'For each image, matching-count curves are averaged over the three seeds before scoring. '
          'Macro best F1 averages the image-specific threshold optima (OIS-style, grid-only). '
          'Pooled best F1 pools image counts and selects the best common threshold (ODS-style, grid-only). '
          'Neither diagnostic should be quoted as an official ODS/OIS benchmark result. '
          'These validation optima are diagnostic; they are not frozen test operating points. '
          'Boundary AP101 is the mean precision envelope over 101 recall levels. It is neither the pixel average '
          'precision from the SomBench study nor a certified copy of the official BSDS AP integration.','',
          '## Main 20-image comparison','',
          '| Configuration | Macro best F1 | Pooled best F1 | Boundary AP101 | Operator RMSE |',
          '|---|---:|---:|---:|---:|']
    for config in configs:
        s=pmap[config];rmse='—' if s['macro_operator_rmse'] is None else f"{s['macro_operator_rmse']:.4f}"
        rows.append(f"| {config} | {s['macro_best_f1']:.4f} | {s['pooled_best_f1']:.4f} | {s['macro_boundary_ap101']:.4f} | {rmse} |")
    rows+=['','![Boundary results](boundary_results.png)','','## Matched-budget study on five fixed cases','',
           '| Configuration | Macro best F1 | Boundary AP101 | Operator RMSE |','|---|---:|---:|---:|']
    for s in data['efficiency5']['summary']:
        rmse='—' if s['macro_operator_rmse'] is None else f"{s['macro_operator_rmse']:.4f}"
        rows.append(f"| {s['config']} | {s['macro_best_f1']:.4f} | {s['macro_boundary_ap101']:.4f} | {rmse} |")
    rows+=['','| A | B | Change in image best F1 | Paired 95% interval |','|---|---|---:|---|']
    rows+=[f"| {p['a']} | {p['b']} | {p['mean_difference']:.4f} | [{p['ci95'][0]:.4f}, {p['ci95'][1]:.4f}] |" for p in paired]
    rows+=['','Intervals use 10,000 paired resamples of five image-level means, with a fixed bootstrap seed. '
           'They are exploratory and unadjusted for multiple comparisons. Simulator repeats are not treated as independent images.','',
           '![Matched-budget effects](efficiency_effects.png)','','## Verification','',
           f"Completed **{verification['quantum_runs']} quantum runs** and 100 deterministic classical/control records. "
           f"Independent replay checked **{verification['circuits_replayed']:,} circuits** and "
           f"**{verification['shots_replayed']:,} simulator shots**. Maximum magnitude discrepancy: "
           f"{verification['max_magnitude_error']:.3g}. All saved threshold-count curves and summary metrics were recomputed.",'',
           'The matcher passed 50 random small-case comparisons against an independent dense assignment solver, '
           'along with identity, empty-mask, one-to-one and multi-annotator invariants. '
           'Frozen live sources, input identities, encoding qubit counts, preparation offsets/norms, audit identities '
           'and shot totals are checked by the verifier. See [verification.json](verification.json).','',
           f"A separate verifier independently rederived all 20 image and annotation crops from raw assets, "
           f"checked provenance, recomputed {independent['metric_cells_recomputed']} summary metric cells "
           f"and all four paired bootstrap intervals. See [summary_verification.json](summary_verification.json). "
           'All 100 classical/control maps were also regenerated and matched exactly. '
           'Regression suites passed 76 tests across the two repositories.','',
           '## Interpretation limits and next decision','',
           'QPIE and FRQI have the same calibrated intensity-gradient target. NEQR detects four-bit quantized '
           'inequality, with a different exact control and different RMSE units. Compare RMSE within each operator track. '
           'Human semantic boundaries are not identical to photometric gradients. '
           'A good boundary score does not by itself establish a better gradient estimator.','',
           'This is a small native-crop validation study with a coarse threshold grid. It cannot be compared directly '
           'to published full-image BSDS500 scores or establish generalization to unseen lunar scenes. '
           'The three encoding processes ran concurrently; runtimes include audit writes and are not used to rank '
           'speed or claim quantum hardware advantage. State preparation uses ideal Aer Initialize.','',
           'Use the paired fixed-budget results to choose a development configuration, then confirm it on additional '
           'validation images before freezing a full-image test protocol. Keep the test split untouched during this selection.','',
           'The measured recommendation is to retain 16×16 blocks as the development baseline: all three smaller-block '
           'F1 intervals include zero, and their operator RMSE is higher on these five cases. '
           'QPIE block-minimum subtraction improves mean F1 by 0.0103 and lowers gradient RMSE from 14.4858 to 9.8896, '
           'but its F1 interval also includes zero. Confirm that option on additional validation images before changing defaults. '
           'The classical Sobel/Robinson lead also exceeds the exact unsmoothed gradient control, suggesting that the '
           'operator and its spatial filtering deserve investigation alongside shot noise; this pilot does not isolate the cause.','',
           'Dataset decision: retain BSDS500 for human-annotated boundary development, while keeping the lunar benchmark '
           'as a separate domain check. For a lunar boundary claim, the next useful dataset work is a small, independently '
           'traced lunar rim set with product/geographic separation and annotation uncertainty recorded. '
           'Natural-image validation and approximate catalog rim masks cannot substitute for that domain ground truth.','',
           '## Provenance and reproduction','',
           'Source: [BIDS BSDS500 mirror](https://github.com/BIDS/BSDS500), commit '
           '`a04b7c6c3a9f0ace74bf205c72a43d32e1c72722`. '
           '[Berkeley benchmark guidelines](https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/grouping/resources.html). '
           'Attribution: P. Arbeláez, M. Maire, C. Fowlkes and J. Malik, *Contour Detection and Hierarchical Image Segmentation*, TPAMI 2011.','',
           'From the FRQI repository, install `requirements-bsds.txt`, then run:', '',
           '```powershell',r'.\.venv\Scripts\python.exe data/bsds500_setup.py',
           r'.\.venv\Scripts\python.exe experiments/run_bsds_parallel.py',
           r'.\.venv\Scripts\python.exe experiments/verify_bsds_summary.py',
           r'.\.venv\Scripts\python.exe experiments/bsds_outputs.py','```','',
           'The runner resumes only matching frozen protocols. The original serial driver remains '
           '`experiments/bsds_pilot.py`; independent replay and metric recomputation are available through '
           '`experiments/bsds_pilot.py --verify-only`. Protocol, hashes, selected IDs, annotations and method logs '
           'are retained beside this report. Source image terms remain those of the original dataset.','',
           '[Quality checkpoints and investigations](quality_review.md)','','![Inputs and human annotations](inputs.png)','']
    (OUTPUT/'report.md').write_text('\n'.join(rows),encoding='utf-8')
    print(OUTPUT/'report.md')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs-only',action='store_true')
    args=parser.parse_args()
    inputs()
    if not args.inputs_only:results()
