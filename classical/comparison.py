"""Save classical baselines on the exact grayscale input used by QHED."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from classical.sobel import sobel_edge_binary
from classical.canny import canny_edge_auto
from classical.robinson_compass import robinson_edge_binary


def run_baselines(image,output):
    output=Path(output)
    sobel,sobel_strength=sobel_edge_binary(image)
    canny=canny_edge_auto(image)
    robinson,rob_strength,_=robinson_edge_binary(image)
    results={'Sobel':(sobel,sobel_strength),'Canny':(canny,canny),'Robinson':(robinson,rob_strength)}
    for name,(edges,strength) in results.items():
        Image.fromarray(edges).save(output/f'{name.lower()}_edges.png')
        if name!='Canny':Image.fromarray(strength).save(output/f'{name.lower()}_strength.png')
    return results


def save_comparison(image,quantum_edges,baselines,output):
    policies={'FRQI-QHED (measured)':'Otsu on measured quantum strength',
              'Sobel':'3x3 Sobel magnitude, global normalization, Otsu',
              'Canny':'Median-based automatic thresholds (sigma 0.33, minimum separation 20)',
              'Robinson':'Eight 3x3 compass responses, global normalization, Otsu'}
    maps={'FRQI-QHED (measured)':quantum_edges,**{name:values[0] for name,values in baselines.items()}}
    summary={'image_shape':list(image.shape),'input_sha256':hashlib.sha256(image.tobytes()).hexdigest(),
             'comparison_scope':'All four methods use the same grayscale working input; edge coverage is not accuracy.',
             'methods':[{'method':name,'edge_pixels':int(np.count_nonzero(edges)),
                         'edge_coverage_percent':float(100*np.count_nonzero(edges)/image.size),
                         'threshold_policy':policies[name]} for name,edges in maps.items()]}
    (Path(output)/'detector_comparison.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary
