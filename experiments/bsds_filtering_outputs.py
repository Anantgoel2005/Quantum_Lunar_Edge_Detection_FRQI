"""Figures and interpretation for the verified fixed-grid filtering experiment."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/bsds_filtering'


def main():
    d=json.loads((OUT/'summary.json').read_text());v=json.loads((OUT/'verification.json').read_text())
    assert v['status']=='passed'
    configs=['QPIE16','QPIE16-offset','Exact-gradient']
    colors=['#2563eb','#7c3aed','#d97706']
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    keys=['best_f1','boundary_ap101','matched_rmse','raw_rmse']
    titles=['Image-optimal boundary F1 ↑','Boundary AP101 ↑','Matched filtered-target RMSE ↓','Original raw-target RMSE ↓']
    for axis,key,title in zip(axes.flat,keys,titles):
        for config,color in zip(configs,colors):
            rows=sorted([r for r in d['means'] if r['config']==config],key=lambda r:r['sigma'])
            axis.plot([r['sigma'] for r in rows],[r[key] for r in rows],marker='o',label=config,color=color)
        if key in ('best_f1','boundary_ap101'):
            reference_key='macro_best_f1' if key=='best_f1' else 'macro_boundary_ap101'
            for r,color,style in zip(d['references'],['#475569','#94a3b8'],['--',':']):
                axis.axhline(r[reference_key],label=r['config']+' (unchanged)',color=color,linestyle=style)
            axis.set_ylim(0,1)
        else:axis.set_ylim(bottom=0)
        axis.set_title(title);axis.set_xticks([0,.5,1]);axis.set_xlabel('Gaussian output σ (native pixels)');axis.grid(alpha=.2)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='outside lower center',ncol=3,fontsize=10)
    fig.suptitle('Matched output filtering: 20 BSDS validation crops',fontweight='bold')
    fig.savefig(OUT/'filter_grid.png',dpi=170);fig.savefig(OUT/'filter_grid.pdf');plt.close(fig)
    excess=[e for e in d['effects'] if e['kind']=='excess_gain' and e['metric']=='best_f1']
    fig,axis=plt.subplots(figsize=(10,4.5),layout='constrained')
    means=np.array([e['mean_difference'] for e in excess]);low=np.array([e['ci95'][0] for e in excess]);high=np.array([e['ci95'][1] for e in excess])
    axis.errorbar(means,range(4),xerr=[means-low,high-means],fmt='o',capsize=5,color='#2563eb')
    axis.axvline(0,color='#64748b',linestyle='--')
    axis.set_yticks(range(4),[f"{e['config']}, σ={e['sigma']:g}" for e in excess])
    axis.set_xlabel('(QPIE filtered − raw F1) − (exact filtered − raw F1)')
    axis.set_title('Does filtering help QPIE beyond the exact control?',fontweight='bold')
    fig.supxlabel('Paired image bootstrap 95% intervals; exploratory and unadjusted for multiple comparisons.',fontsize=10)
    fig.savefig(OUT/'excess_gain.png',dpi=170);plt.close(fig)
    best=max([r for r in d['means'] if r['config']!='Exact-gradient'],key=lambda r:r['best_f1'])
    supported=[e for e in excess if e['ci95'][0]>0]
    inference=('Some grid settings have positive excess-F1 intervals; these are development signals that need confirmation on untouched images.'
               if supported else 'No tested setting has a wholly positive excess-F1 interval; this experiment does not establish an extra F1 benefit specific to QPIE.')
    lines=['# Controlled output filtering: QPIE and exact-gradient controls','',
           f"The highest observed quantum mean image-optimal F1 in this grid is **{best['best_f1']:.4f}** "
           f"for **{best['config']}, σ={best['sigma']:g}**. This is a development-grid observation, not a frozen test result.",'',
           '## Fixed experiment','',
           'All 20 existing native 128×128 BSDS500 validation crops are retained. QPIE baseline and block-minimum '
           'subtraction each use the same three saved seeds, 16×16 blocks and original 8,192-shot circuits. '
           'No additional quantum simulation or data download was performed. '
           'The original lunar benchmark, BSDS pilot, offset follow-up and detector defaults are unchanged.','',
           'The grid was frozen before evaluation: Gaussian σ=0, 0.5 and 1 native pixel, radius=ceil(3σ), '
           'half-sample reflective boundaries. Filtering acts on each full output magnitude map, '
           'not on the input image or signed gradient components. The exact-gradient magnitude receives '
           'the identical filter. Each result is then normalized by its own maximum; zero maps remain zero. '
           'Sobel and Robinson remain unchanged references. No directional non-maximum suppression was added.','',
           'Boundary evaluation retains all separate human annotations, the 124×124 interior, 31 fixed thresholds, '
           'Guo–Hall thinning and one-to-one BSDS-style matching. These are custom validation-crop metrics, '
           'not official full-image BSDS500 ODS/OIS/AP scores. AP101 differs from the lunar pixel-AP metric.','',
           '## Full grid','',
           '| Output | σ | Mean image-optimal F1 | Boundary AP101 | Matched-target RMSE | Raw-target RMSE |',
           '|---|---:|---:|---:|---:|---:|']
    for config in configs:
        for r in [r for r in d['means'] if r['config']==config]:
            lines.append(f"| {r['config']} | {r['sigma']:g} | {r['best_f1']:.4f} | {r['boundary_ap101']:.4f} | {r['matched_rmse']:.4f} | {r['raw_rmse']:.4f} |")
    for r in d['references']:
        lines.append(f"| {r['config']} (unchanged) | — | {r['macro_best_f1']:.4f} | {r['macro_boundary_ap101']:.4f} | — | — |")
    lines+=['','Matched-target RMSE compares the filtered estimate with the equally filtered exact-gradient magnitude. '
            'Raw-target RMSE compares it with the original exact-gradient magnitude, retaining smoothing bias. '
            'The exact control has zero matched-target error by definition; its raw-target error quantifies filter bias. '
            'Neither RMSE alone measures human boundary quality.','',
            '![Full filtering grid](filter_grid.png)','','## Paired F1 effects','',
            '| Output | σ | Mean F1 change from raw | Paired 95% interval |','|---|---:|---:|---|']
    for e in d['effects']:
        if e['kind']=='change' and e['metric']=='best_f1':
            lines.append(f"| {e['config']} | {e['sigma']:g} | {e['mean_difference']:+.4f} | [{e['ci95'][0]:+.4f}, {e['ci95'][1]:+.4f}] |")
    lines+=['','For a QPIE-specific filtering effect, subtract the exact control’s own gain on the same image. '
            'Positive excess gain means QPIE benefits more than the matched deterministic control.','',
            '| QPIE output | σ | Excess F1 gain | Paired 95% interval |','|---|---:|---:|---|']
    for e in excess:
        lines.append(f"| {e['config']} | {e['sigma']:g} | {e['mean_difference']:+.4f} | [{e['ci95'][0]:+.4f}, {e['ci95'][1]:+.4f}] |")
    lines+=['','![Excess filtering gain](excess_gain.png)','','## Decision and limits','',inference,'',
            'Both nonzero blur settings lower the observed mean F1 and AP101 for each quantum configuration '
            'and for the exact control. The σ=1 F1-change intervals are wholly negative for all three outputs; '
            'the σ=0.5 F1-change intervals span zero. Mild smoothing reduces gradient RMSE, but this does not '
            'translate into a boundary-score improvement. Keep Gaussian output blur disabled.','',
            'The next useful step is a separately frozen evaluation of the unblurred baseline and subtraction '
            'configurations on additional untouched images, retaining the exact-gradient and classical references. '
            'This experiment supports stopping this output-blur tuning direction; it does not rule out input-image '
            'smoothing, component filtering or different edge-localization operators, which were not tested.','',
            'Report the whole grid. Do not change defaults or claim a confirmed best filter from these same validation images. '
            'Choose a small candidate configuration only for a separately frozen evaluation on untouched images. '
            'Natural-image results do not establish lunar-rim accuracy; independently traced lunar boundaries remain needed.','',
            'Image-optimal F1 is the primary boundary endpoint. AP101 is descriptive; both RMSE targets diagnose estimation '
            'and filtering effects. Count curves are averaged across seeds before image scoring; RMSE is averaged across seeds. '
            'Intervals use 10,000 paired image resamples, bootstrap seed 20261019, with no multiplicity adjustment. '
            'The three seeds do not increase the independent image count beyond 20. Grid selection, prior use of these '
            'validation crops and a custom evaluator limit inference. This is entirely classical postprocessing of '
            'ideal simulator measurements; no quantum or timing advantage is inferred.','',
            '## Verification and reproduction','',
            f"Verified **{v['map_records']} map records**, including {v['zero_sigma_parent_records_reproduced']} zero-filter "
            f"records reproducing the parent curves. Independent dense 2D convolution differs from separable filtering "
            f"by at most {v['max_dense_filter_error']:.3g}. All threshold-count curves, per-image metrics, "
            f"{v['summary_metric_cells']} summary cells and {v['paired_bootstrap_intervals']} paired intervals were checked. "
            f"All {v['input_files_unchanged']} frozen input files retained their hashes. "
            'The verifier shares the previously tested boundary matcher; it does not certify equivalence to Berkeley’s MATLAB implementation.','',
            'See [protocol](protocol.json), [summary](summary.json), [verification](verification.json), '
            '[test log](tests.log) and [quality review](quality_review.md).','',
            'From the FRQI repository:', '',
            '```powershell',r'.\.venv\Scripts\python.exe experiments/bsds_filtering.py',
            r'.\.venv\Scripts\python.exe experiments/verify_bsds_filtering.py',
            r'.\.venv\Scripts\python.exe experiments/bsds_filtering_outputs.py','```','',
            'Input identities and original dataset attribution remain in the '
            '[BSDS pilot](../bsds_pilot/report.md) and [offset follow-up](../bsds_qpie_offset20/report.md).','']
    (OUT/'report.md').write_text('\n'.join(lines),encoding='utf8')
    print(OUT/'report.md')


if __name__=='__main__':main()
