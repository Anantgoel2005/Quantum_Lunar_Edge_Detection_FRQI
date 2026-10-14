"""
Analysis and Visualization -- Generates all figures and tables for the report.

Reads experiment CSV results and produces:
  - Comparison bar charts (quantum vs classical)
  - Shot sensitivity curves
  - Noise degradation plots
  - Geometry heatmaps
  - Resource scaling tables
  - Summary LaTeX-ready tables
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results" / "corrected" / "tables"
FIGURES_DIR = PROJECT_ROOT / "results" / "corrected" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Style settings
plt.rcParams.update({
    'font.size': 11,
    'figure.figsize': (10, 6),
    'figure.dpi': 150,
    'axes.grid': True,
    'grid.alpha': 0.3,
})
COLORS = {
    'Sobel': '#2196F3',
    'Canny': '#FF9800',
    'Robinson': '#4CAF50',
    'QPIE-QHED': '#E91E63',
    'NEQR-Gradient': '#9C27B0',
    'Forward-Gradient': '#607D8B',
    'Quantized-Gradient': '#795548',
}


def plot_experiment_1():
    """Bar chart: representation ablation (F1 per geometry per method)."""
    csv_path = RESULTS_DIR / "exp1_representation_ablation.csv"
    if not csv_path.exists():
        print("  exp1 not found, skipping")
        return

    df = pd.read_csv(csv_path)

    # Pivot: image x method -> F1
    pivot = df.pivot_table(index='image', columns='method', values='f1_exact_mean', aggfunc='first')

    fig, ax = plt.subplots(figsize=(12, 6))
    methods = ['Sobel', 'Canny', 'Robinson', 'QPIE-QHED', 'NEQR-Gradient']
    methods = [m for m in methods if m in pivot.columns]

    x = np.arange(len(pivot.index))
    width = 0.15

    for i, method in enumerate(methods):
        vals = pivot[method].values
        bars = ax.bar(x + i * width, vals, width, label=method,
                     color=COLORS.get(method, '#666'), edgecolor='white', linewidth=0.5)

    ax.set_xlabel('Edge Geometry')
    ax.set_ylabel('F1 Score (Exact Match)')
    ax.set_title('Experiment 1: Representation Ablation -- Quantum vs Classical')
    ax.set_xticks(x + width * (len(methods) - 1) / 2)
    ax.set_xticklabels(pivot.index, rotation=45, ha='right')
    ax.legend(loc='upper right')
    ax.set_ylim(0, 1.1)

    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "exp1_representation_ablation.png")
    plt.close()
    print("  Saved: exp1_representation_ablation.png")


def plot_experiment_2():
    """Line chart: F1 vs shot count for each quantum method."""
    csv_path = RESULTS_DIR / "exp2_shot_sensitivity.csv"
    if not csv_path.exists():
        print("  exp2 not found, skipping")
        return

    df = pd.read_csv(csv_path)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for i, method in enumerate(["QPIE-QHED", "NEQR-Gradient"]):
        ax = axes[i]
        method_df = df[df['method'] == method]

        for image in method_df['image'].unique():
            img_df = method_df[method_df['image'] == image].sort_values('shots')
            ax.errorbar(img_df['shots'], img_df['f1_exact_mean'],
                       yerr=img_df['f1_exact_std'],
                       marker='o', label=image, markersize=4, capsize=3)

        ax.set_xlabel('Number of Shots')
        ax.set_ylabel('F1 Score')
        ax.set_title(f'{method} -- Shot Sensitivity')
        ax.set_xscale('log', base=2)
        ax.legend(fontsize=8)
        ax.set_ylim(-0.05, 1.05)

    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "exp2_shot_sensitivity.png")
    plt.close()
    print("  Saved: exp2_shot_sensitivity.png")


def plot_experiment_5():
    """Heatmap: noise type x method -> F1."""
    csv_path = RESULTS_DIR / "exp5_noise_simulation.csv"
    if not csv_path.exists():
        print("  exp5 not found, skipping")
        return

    df = pd.read_csv(csv_path)

    pivot = df.pivot_table(index='noise', columns='method',
                           values='f1_exact_mean', aggfunc='mean')

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(pivot, annot=True, fmt='.3f', cmap='RdYlGn', ax=ax,
                vmin=0, vmax=0.6, linewidths=0.5)
    ax.set_title('Experiment 5: F1 Score Under Hardware Noise')
    ax.set_ylabel('Noise Configuration')
    ax.set_xlabel('Method')

    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "exp5_noise_simulation.png")
    plt.close()
    print("  Saved: exp5_noise_simulation.png")


def plot_experiment_6():
    """Heatmap: geometry x method -> F1."""
    csv_path = RESULTS_DIR / "exp6_geometry_ablation.csv"
    if not csv_path.exists():
        print("  exp6 not found, skipping")
        return

    df = pd.read_csv(csv_path)

    pivot = df.pivot_table(index='geometry', columns='method',
                           values='f1_exact_mean', aggfunc='first')

    methods_order = ['Sobel', 'Canny', 'Robinson', 'QPIE-QHED', 'NEQR-Gradient']
    methods_order = [m for m in methods_order if m in pivot.columns]
    pivot = pivot[methods_order]

    fig, ax = plt.subplots(figsize=(10, 7))
    sns.heatmap(pivot, annot=True, fmt='.3f', cmap='RdYlGn', ax=ax,
                vmin=0, vmax=1.0, linewidths=0.5)
    ax.set_title('Experiment 6: Edge Detection F1 by Geometry Type')
    ax.set_ylabel('Edge Geometry')
    ax.set_xlabel('Method')

    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "exp6_geometry_ablation.png")
    plt.close()
    print("  Saved: exp6_geometry_ablation.png")


def plot_experiment_4():
    """Grouped bar: degradation impact on each method."""
    csv_path = RESULTS_DIR / "exp4_image_degradation.csv"
    if not csv_path.exists():
        print("  exp4 not found, skipping")
        return

    df = pd.read_csv(csv_path)

    pivot = df.pivot_table(index='degradation', columns='method',
                           values='f1_exact_mean', aggfunc='mean')

    fig, ax = plt.subplots(figsize=(12, 6))
    pivot.plot(kind='bar', ax=ax, color=[COLORS.get(c, '#666') for c in pivot.columns],
               edgecolor='white', linewidth=0.5)
    ax.set_ylabel('F1 Score')
    ax.set_title('Experiment 4: Edge Detection Under Image Degradation')
    ax.set_xticklabels(pivot.index, rotation=45, ha='right')
    ax.legend(loc='upper right')
    ax.set_ylim(0, 1.1)

    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "exp4_image_degradation.png")
    plt.close()
    print("  Saved: exp4_image_degradation.png")


def generate_summary_table():
    """Generate a grand summary table across all experiments."""
    print("\n  Generating summary table...")

    # Collect overall mean F1 per method
    summary = {}
    experiments = {
        'exp1': 'Representation Ablation',
        'exp6': 'Geometry Ablation',
        'exp8': 'SomBench Benchmark',
    }

    for exp_key, exp_name in experiments.items():
        csv_path = RESULTS_DIR / f"{exp_key}_*.csv"
        matches = list(RESULTS_DIR.glob(f"{exp_key}_*.csv"))
        if not matches:
            continue

        df = pd.read_csv(matches[0])
        for method in df['method'].unique():
            if method not in summary:
                summary[method] = {}
            method_df = df[df['method'] == method]
            summary[method][exp_name] = method_df['f1_exact_mean'].mean()

    if summary:
        summary_df = pd.DataFrame(summary).T
        summary_df.index.name = 'Method'

        # Save
        summary_df.to_csv(RESULTS_DIR / "grand_summary.csv")
        print(f"  Saved: grand_summary.csv")
        print(summary_df.round(4).to_string())


def main():
    print("=" * 60)
    print("ANALYSIS AND VISUALIZATION")
    print("=" * 60)

    plot_experiment_1()
    plot_experiment_2()
    plot_experiment_4()
    plot_experiment_5()
    plot_experiment_6()
    generate_summary_table()

    print(f"\n  All figures saved to: {FIGURES_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
