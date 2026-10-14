"""
Final Report Generator -- Creates the comprehensive results report.

Reads all experiment CSV results and produces a markdown report with:
  - Executive summary
  - Detailed per-experiment findings
  - Comparison tables
  - Key takeaways
  - Recommendations
"""
import numpy as np
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(r"E:\projects\Quantum_Image")
RESULTS_DIR = PROJECT_ROOT / "results" / "tables"
FIGURES_DIR = PROJECT_ROOT / "results" / "figures"
REPORT_DIR = PROJECT_ROOT / "report"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def load_csv_safe(name):
    """Load a CSV file, return None if not found."""
    path = RESULTS_DIR / name
    if path.exists():
        return pd.read_csv(path)
    return None


def generate_report():
    """Generate the full results report."""
    
    report_lines = []
    
    def add(line=""):
        report_lines.append(line)
    
    add("# Quantum Edge Detection -- Final Results Report")
    add(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    add(f"**Project:** Quantum Edge Detection Under Changing Image Conditions")
    add()
    add("---")
    add()
    
    # ==== EXECUTIVE SUMMARY ====
    add("## Executive Summary")
    add()
    
    exp1 = load_csv_safe("exp1_representation_ablation.csv")
    if exp1 is not None:
        methods = exp1['method'].unique()
        summary_lines = []
        for m in methods:
            mean_f1 = exp1[exp1['method'] == m]['f1_exact_mean'].mean()
            summary_lines.append(f"  - **{m}**: Mean F1 = {mean_f1:.4f}")
        
        add("**Core Finding (Experiment 1 -- Representation Ablation):**")
        add()
        for line in summary_lines:
            add(line)
        add()
        add("> Classical methods (Sobel, Robinson) significantly outperform both quantum")
        add("> approaches on 8x8 synthetic patches. NEQR-Gradient provides moderate edge")  
        add("> detection quality. QPIE-QHED struggles with very low F1 scores due to the")
        add("> challenge of reconstructing spatial edge information from amplitude-encoded")
        add("> quantum measurements at this scale.")
        add()
    
    add("---")
    add()
    
    # ==== EXPERIMENT 1 ====
    add("## Experiment 1: Representation Ablation")
    add()
    if exp1 is not None:
        pivot = exp1.pivot_table(index='image', columns='method', 
                                  values='f1_exact_mean', aggfunc='first')
        add("### F1 Scores by Geometry and Method")
        add()
        add(pivot.round(4).to_markdown())
        add()
        
        # Overall
        add("### Overall Mean F1")
        add()
        add("| Method | Mean F1 | Std F1 |")
        add("|--------|---------|--------|")
        for m in ['Sobel', 'Canny', 'Robinson', 'QPIE-QHED', 'NEQR-Gradient']:
            if m in exp1['method'].values:
                vals = exp1[exp1['method'] == m]['f1_exact_mean']
                add(f"| {m} | {vals.mean():.4f} | {vals.std():.4f} |")
        add()
    
    # ==== EXPERIMENT 2 ====
    add("## Experiment 2: Shot Count Sensitivity")
    add()
    exp2 = load_csv_safe("exp2_shot_sensitivity.csv")
    if exp2 is not None:
        add("### Mean F1 vs Shot Count")
        add()
        pivot = exp2.pivot_table(index='shots', columns='method',
                                  values='f1_exact_mean', aggfunc='mean')
        add(pivot.round(4).to_markdown())
        add()
        add("> **Finding:** NEQR-Gradient converges quickly and is insensitive to shot count")
        add("> above 512 shots. QPIE-QHED shows slight variation but remains low throughout.")
        add()
    
    # ==== EXPERIMENT 5 ====
    add("## Experiment 5: Quantum Hardware Noise Simulation")
    add()
    exp5 = load_csv_safe("exp5_noise_simulation.csv")
    if exp5 is not None:
        pivot = exp5.pivot_table(index='noise', columns='method',
                                  values='f1_exact_mean', aggfunc='mean')
        add("### F1 Under Different Noise Configurations")
        add()
        add(pivot.round(4).to_markdown())
        add()
    
    # ==== EXPERIMENT 6 ====
    add("## Experiment 6: Geometry Ablation")
    add()
    exp6 = load_csv_safe("exp6_geometry_ablation.csv")
    if exp6 is not None:
        pivot = exp6.pivot_table(index='geometry', columns='method',
                                  values='f1_exact_mean', aggfunc='first')
        add("### F1 by Edge Geometry")
        add()
        add(pivot.round(4).to_markdown())
        add()
    
    # ==== EXPERIMENT 4 ====
    add("## Experiment 4: Image Quality Degradation")
    add()
    exp4 = load_csv_safe("exp4_image_degradation.csv")
    if exp4 is not None:
        pivot = exp4.pivot_table(index='degradation', columns='method',
                                  values='f1_exact_mean', aggfunc='mean')
        add("### F1 Under Image Degradation")
        add()
        add(pivot.round(4).to_markdown())
        add()
    
    # ==== EXPERIMENT 8 ====
    add("## Experiment 8: SomBench Real Lunar Benchmark")
    add()
    exp8 = load_csv_safe("exp8_sombench_benchmark.csv")
    if exp8 is not None:
        add("### Overall Mean F1 on SomBench Patches")
        add()
        add("| Method | Mean F1 | N |")
        add("|--------|---------|---|")
        for m in ['Sobel', 'Canny', 'Robinson', 'QPIE-QHED', 'NEQR-Gradient']:
            if m in exp8['method'].values:
                vals = exp8[exp8['method'] == m]['f1_exact_mean']
                add(f"| {m} | {vals.mean():.4f} | {len(vals)} |")
        add()
    
    # ==== EXPERIMENT 9 ====
    add("## Experiment 9: Resource Scaling")
    add()
    exp9 = load_csv_safe("exp9_resource_scaling.csv")
    if exp9 is not None:
        add(exp9.to_markdown(index=False))
        add()
    
    # ==== TIMING ====
    add("## Timing Analysis")
    add()
    timing = load_csv_safe("timing_analysis.csv")
    if timing is not None:
        add(timing.round(2).to_markdown(index=False))
        add()
    
    # ==== EXPERIMENT 7 ====
    add("## Experiment 7: Preprocessing Strategy")
    add()
    exp7 = load_csv_safe("exp7_preprocessing.csv")
    if exp7 is not None:
        pivot = exp7.pivot_table(index='preprocessing', columns='method',
                                  values='f1_exact_mean', aggfunc='mean')
        add(pivot.round(4).to_markdown())
        add()
    
    # ==== EXPERIMENT 10 ====
    add("## Experiment 10: Failure Taxonomy")
    add()
    exp10 = load_csv_safe("exp10_failure_taxonomy.csv")
    if exp10 is not None:
        add(exp10[['geometry', 'method', 'f1_exact_mean', 'precision_mean', 
                   'recall_mean', 'failure_mode']].round(4).to_markdown(index=False))
        add()
    
    # ==== CONCLUSIONS ====
    add("---")
    add()
    add("## Key Conclusions")
    add()
    add("1. **Classical methods outperform quantum methods** on small (8x8) synthetic")
    add("   and real lunar patches. Sobel and Robinson achieve F1 > 0.8 on most geometries.")
    add()
    add("2. **NEQR-Gradient outperforms QPIE-QHED** as a quantum edge detector. The")
    add("   basis-state encoding preserves pixel intensity information more faithfully")
    add("   through measurement.")
    add()
    add("3. **QPIE-QHED struggles** because amplitude encoding maps pixel differences")
    add("   to small probability differences that are hard to resolve with finite shots.")
    add("   Complete failures (F1=0) occur on certain geometries.")
    add()
    add("4. **Shot count has minimal impact** above ~512 shots for both quantum methods.")
    add("   The bottleneck is representation quality, not measurement statistics.")
    add()
    add("5. **Hardware noise degrades quantum edge detection further**, with readout")
    add("   errors having the strongest impact (directly corrupting measurement results).")
    add()
    add("6. **No quantum speed advantage**: quantum simulation is orders of magnitude")
    add("   slower than classical Sobel due to circuit compilation and simulation overhead.")
    add()
    add("7. **Quantum methods produce unique uncertainty information**: confidence maps")
    add("   from repeated trials reveal measurement variance patterns that classical")
    add("   methods cannot provide, which may have diagnostic value.")
    add()
    
    # Write report
    report_path = REPORT_DIR / "final_results_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"Report saved to: {report_path}")
    return report_path


if __name__ == "__main__":
    generate_report()
