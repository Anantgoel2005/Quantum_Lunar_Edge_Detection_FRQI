"""Run automatic quantum edge detection on a complete real SomBench tile."""
import argparse
import csv
import json
import sys
import time
from importlib.metadata import version
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from preprocessing.real_image import load_real_tiff
from preprocessing.annotation_rasteriser import rasterise_image_annotations
from quantum.full_image import run_full_image_qhed
from quantum.reconstruction import threshold_edge_map
from classical.sobel import sobel_edge_binary
from classical.canny import canny_edge_auto
from classical.robinson_compass import robinson_edge_binary
from classical.comparison import run_baselines,save_comparison
from evaluation.metrics import compute_all_metrics
from visualization.trace_store import write_json_atomic


def save_gray(path,values):
    Image.fromarray(np.asarray(values,dtype=np.uint8)).save(path)


def make_figure(output,image,gt,quantum_binary,quantum_strength,classical_binary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes = plt.subplots(2,3,figsize=(13,9),layout='constrained')
    panels = [(image,'Real WAC grayscale tile','gray'),
              (gt,'Catalog rim reference (approximate)','gray'),
              (quantum_strength,'QHED strength from circuit measurements','magma'),
              (quantum_binary,'Automatic QHED edges (Otsu threshold)','gray'),
              (classical_binary,'Sobel baseline on the same image','gray')]
    for axis,(values,title,cmap) in zip(axes.flat,panels):
        axis.imshow(values,cmap=cmap,vmin=0,vmax=1 if values.dtype.kind=='f' else 255)
        axis.set_title(title,fontsize=11)
        axis.set_axis_off()
    overlay = np.repeat(image[:,:,None],3,axis=2)
    overlay[gt>0] = [30,220,90]
    overlay[quantum_binary>0] = [235,75,180]
    overlay[(gt>0)&(quantum_binary>0)] = [255,225,45]
    axes.flat[-1].imshow(overlay)
    axes.flat[-1].set_title('Reference: green | quantum edges: magenta\nOverlap: yellow',fontsize=10)
    axes.flat[-1].set_axis_off()
    fig.suptitle('SomBench row 0: complete native-resolution tile',fontsize=15)
    fig.savefig(output/'comparison.png',dpi=150)
    plt.close(fig)
    Image.fromarray(overlay).save(output/'overlay.png')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case',type=Path,default=ROOT/'data/sombench/real_case/row0_case.json')
    parser.add_argument('--tile-size',type=int,default=16)
    parser.add_argument('--shots',type=int,default=8192)
    parser.add_argument('--batch-tiles',type=int,default=16)
    parser.add_argument('--band',default='mean')
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--image',type=Path)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    if args.image:
        manifest=None
        raw_path=args.image
        image=np.asarray(Image.open(raw_path).convert('L'))
        output=args.output or ROOT/'results/user_images/cli'
        prep_path=output/'preprocessing.json'
        loading=json.loads(prep_path.read_text(encoding='utf-8')) if prep_path.exists() else {'image_shape':list(image.shape),'band_count':1}
    else:
        manifest=json.loads(args.case.read_text(encoding='utf-8'))
        raw_path=ROOT/manifest['local_image']
        image,valid,loading=load_real_tiff(raw_path,band=args.band)
        if tuple(image.shape)!=(manifest['image_info']['height'],manifest['image_info']['width']):
            raise ValueError('TIFF dimensions do not match the annotation coordinate system')
        if not np.all(valid):
            raise ValueError('This case runner requires valid pixels across the whole tile')
        output=args.output or ROOT/'results/real_case'/f"row{manifest['metadata_row_index']}"
    output.mkdir(parents=True,exist_ok=True)
    save_gray(output/'input.png',image)
    save_gray(output/'live_strength.png',np.zeros_like(image))
    status_path = output/'progress.json'
    write_json_atomic(output/'gate_trace_latest.json',{'waiting':True})
    last_update = 0.
    def progress(done,total,circuits,elapsed):
        nonlocal last_update
        write_json_atomic(status_path,{'status':'running','completed_tiles':done,'total_tiles':total,
            'circuits_executed':circuits,'measurement_shots':circuits*args.shots,'elapsed_seconds':elapsed})
        if elapsed-last_update >= 10 or done == total:
            print(f'Quantum execution: {done}/{total} tiles; {circuits} circuits; {elapsed:.1f}s',flush=True)
            last_update = elapsed
    def snapshot(magnitude):
        maximum = magnitude.max()
        values = np.rint(magnitude/maximum*255).astype(np.uint8) if maximum else np.zeros_like(image)
        temporary = output/'live_strength.part.png'
        save_gray(temporary,values)
        temporary.replace(output/'live_strength.png')
    print(f"Running full tile {image.shape}, {loading.get('band_count',1)} input bands",flush=True)
    def gate_trace(packet):
        write_json_atomic(output/'gate_trace_latest.json',packet)
    maps,execution,representative = run_full_image_qhed(image,tile_size=args.tile_size,shots=args.shots,
        seed=args.seed,batch_tiles=args.batch_tiles,audit_path=output/'measurement_counts.jsonl.gz',progress=progress,snapshot=snapshot,
        gate_trace=gate_trace,trace_audit_path=output/'gate_trace.jsonl.gz')
    binary,threshold = threshold_edge_map(maps['strength'],'otsu')
    np.savez_compressed(output/'quantum_maps.npz',**maps)
    save_gray(output/'quantum_edges.png',binary)
    save_gray(output/'quantum_strength.png',np.rint(maps['strength']*255))
    baselines=run_baselines(image,output)
    comparison=save_comparison(image,binary,baselines,output)
    sobel,sobel_strength=baselines['Sobel']
    canny,_=baselines['Canny']
    robinson,rob_strength=baselines['Robinson']
    metrics=[]
    if manifest:
        gt=rasterise_image_annotations(manifest['annotations'],manifest['image_info']['id'],*image.shape,mode='rim',rim_width=1)
        save_gray(output/'catalog_rims.png',gt)
        metrics=[compute_all_metrics(pred,scores,gt,name) for name,pred,scores in [
            ('QPIE-QHED (measured)',binary,maps['strength']),('Sobel',sobel,sobel_strength),
            ('Canny',canny,canny),('Robinson',robinson,rob_strength)]]
        with (output/'metrics.csv').open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=list(metrics[0]))
            writer.writeheader();writer.writerows(metrics)
        make_figure(output,image,gt,binary,maps['strength'],sobel)
    else:
        preview=output/'original.png'
        overlay=np.asarray(Image.open(preview).convert('RGB')).copy() if preview.exists() else np.repeat(image[:,:,None],3,axis=2)
        overlay[binary>0]=[235,75,180]
        Image.fromarray(overlay).save(output/'overlay.png')
    from qiskit import transpile,qasm3
    compiled = transpile(representative,basis_gates=['u','cx'],optimization_level=0,seed_transpiler=args.seed)
    (output/'representative_circuit.qasm').write_text(qasm3.dumps(compiled),encoding='utf-8')
    (output/'representative_circuit.txt').write_text(str(representative.draw(output='text',fold=120)),encoding='utf-8')
    provenance = {key:manifest[key] for key in ['dataset','dataset_revision','metadata_row_index','annotation_split','metadata','source_urls','sha256','license','attribution','label_kind']} if manifest else {'kind':'user_upload','source':str(raw_path.name)}
    metadata = {'provenance':provenance,'loading':loading,'execution':execution,'threshold':threshold,'detector_comparison':comparison,
        'threshold_policy':'Otsu from measured full-image strengths; no label-based tuning',
        'annotated_craters':len(manifest['annotations']) if manifest else None,'rim_width_pixels':1,
        'quantum_edge_pixels':int(np.count_nonzero(binary)),
        'representative_primitive_gates':dict(compiled.count_ops()),
        'versions':{name:version(name) for name in ['qiskit','qiskit-aer','numpy','tifffile','opencv-python']}}
    (output/'run_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    write_json_atomic(status_path,{'status':'complete',**execution})
    if manifest:
        rows = ['# Real lunar tile: automatic quantum edge detection','',
            f"Tile: `{Path(raw_path).stem}`; viewer metadata row {manifest['metadata_row_index']}; annotation split `{manifest['annotation_split']}`.",'',
            f"Processed all {image.shape[0]}x{image.shape[1]} pixels using {execution['circuits_executed']:,} Qiskit circuits and {execution['measurement_shots']:,} measurement shots.",
            f"Elapsed circuit workload: {execution['elapsed_seconds']:.1f} seconds. No manual region selection was used.",'',
            'Every detected edge is reconstructed from Aer circuit counts. The full-image output does not use the analytical shortcut or a classical edge detector.',
            'Classical processing prepares grayscale intensities, subtracts each tile minimum to improve amplitude contrast, calibrates measured probabilities, stitches halos and thresholds the final map.',
            'Aer is an ideal local statevector simulator; this is not quantum hardware execution. Image preparation is executed with Aer\'s supported Initialize instruction. A decomposed preparation example is saved as QASM.','',
            '## Metrics against catalog-derived approximate rims','',
            '| Method | Exact F1 | 1px F1 | 2px F1 | Average precision |','| --- | ---: | ---: | ---: | ---: |']
        rows += [f"| {m['method']} | {m['f1_exact']:.4f} | {m['f1_1px']:.4f} | {m['f1_2px']:.4f} | {m['pr_auc']:.4f} |" for m in metrics]
        rows += ['', 'Labels are circular catalog approximations, not pixel-perfect image-traced boundaries. This is a single train-split demonstration, not a held-out crater detection benchmark.',
            'Outputs are edge maps, not detected crater bounding boxes. Illumination, texture, catalog incompleteness and finite shot noise affect the results.','',
            '![Full image comparison](comparison.png)','',
            'Source: https://huggingface.co/datasets/nasa-ibm-ai4science/Sombench-WAC-Crater-Detection','']
    else:
        rows=['# Uploaded image: live quantum edge detection','',
              f'Working image: {image.shape[1]}x{image.shape[0]} pixels.',
              f"Executed {execution['circuits_executed']:,} Qiskit circuits and {execution['measurement_shots']:,} shots.",'',
              'Preprocessing completes before QPIE encoding. Quantum edges come from actual circuit measurements.',
              'No ground-truth labels were supplied, so accuracy metrics are unavailable.',
              'Execution uses the local ideal Aer simulator. Gate animation uses actual saved checkpoints.','',
              '![Quantum edges](quantum_edges.png)']
    rows+=['','## Detector comparison on the same working input','',
           '| Method | Edge pixels | Coverage |','| --- | ---: | ---: |']
    rows+=[f"| {r['method']} | {r['edge_pixels']:,} | {r['edge_coverage_percent']:.2f}% |" for r in comparison['methods']]
    rows+=['','Coverage measures how many pixels are marked as edges; it does not measure accuracy.',
           'Sobel and Robinson use Otsu thresholds; Canny uses automatic median thresholds.',
           '', '![Sobel](sobel_edges.png)', '![Canny](canny_edges.png)', '![Robinson](robinson_edges.png)']
    (output/'report.md').write_text('\n'.join(rows),encoding='utf-8')
    print(json.dumps({'output':str(output),'execution':execution,'metrics':metrics},indent=2),flush=True)


if __name__ == '__main__':
    main()
