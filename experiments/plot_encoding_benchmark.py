"""Export a static research figure from seed-averaged image benchmark results."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    output = Path(__file__).resolve().parents[1] / 'results/encoding_benchmark'
    data = json.loads((output / 'summary.json').read_text())['per_image']
    methods = ['QPIE', 'FRQI', 'NEQR', 'Sobel', 'Canny', 'Robinson',
               'Exact-gradient', 'Exact-NEQR-inequality']
    labels = ['QPIE', 'FRQI', 'NEQR', 'Sobel', 'Canny', 'Robinson',
              'Exact\ngradient', 'Exact\ninequality']
    colors = ['#2563eb', '#7c3aed', '#0891b2'] + ['#94a3b8'] * 3 + ['#d97706'] * 2
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), sharey=True, layout='constrained')
    for axis, shots in zip(axes, (1024, 8192)):
        values = [[case['pr_auc'] for case in data[f'{method}:{shots if method in methods[:3] else 0}'].values()]
                  for method in methods]
        means = [np.mean(value) for value in values]
        axis.bar(range(len(methods)), means, color=colors, width=.65, alpha=.85)
        for i, value in enumerate(values):
            jitter = np.linspace(-.18, .18, len(value))
            axis.scatter(i + jitter, value, color='#0f172a', alpha=.6, s=14, zorder=3)
        axis.set_xticks(range(len(methods)), labels)
        axis.tick_params(axis='x', labelsize=9)
        axis.set_title(f'{shots:,} shots per quantum circuit', fontweight='bold')
        axis.grid(axis='y', alpha=.2)
        axis.set_axisbelow(True)
        axis.set_ylim(bottom=0)
    axes[0].set_ylabel('Average precision against approximate catalog rims')
    fig.suptitle('Matched encoding benchmark: eight native 128x128 test crops', fontsize=15, fontweight='bold')
    fig.supxlabel('Bars: image macro means; dots: individual image means over three seeds. One empty-reference crop retained.', fontsize=10)
    fig.savefig(output / 'average_precision.png', dpi=180)
    fig.savefig(output / 'average_precision.pdf')
    plt.close(fig)
    print(output / 'average_precision.png')


if __name__ == '__main__':
    main()
