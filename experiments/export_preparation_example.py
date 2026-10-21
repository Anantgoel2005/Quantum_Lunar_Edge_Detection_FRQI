"""Export the default image's first preparation without running full detection."""
from pathlib import Path
import sys
import numpy as np
from PIL import Image
from qiskit import transpile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from visualization.real_case_server import OUTPUT
from visualization.state_preparation import export_preparation

if __name__=='__main__':
    encoding=ROOT.name.rsplit('_',1)[-1]
    if encoding=='QPIE':from quantum.qhed_circuit import build_qhed_circuit as build
    else:
        from quantum.variant_circuit import build_variant_circuit as build,ENCODING
        assert ENCODING==encoding
    image=np.array(Image.open(OUTPUT/'input.png'),dtype=float)
    tile=np.pad(image,((1,16),(1,16)),mode='edge')[:16,:16]
    if encoding=='QPIE':tile-=tile.min()
    native,_,_=build(tile,'horizontal',0)
    compiled=transpile(native,basis_gates=['u','cx'],optimization_level=0,seed_transpiler=42)
    info=export_preparation(compiled,OUTPUT,{'encoding':encoding,'tile_size':16,
                                         'subtract_tile_min':encoding=='QPIE','example_only':True})
    print(f"{encoding}: {info['qubits']} qubits, {info['instruction_count']} preparation instructions")
