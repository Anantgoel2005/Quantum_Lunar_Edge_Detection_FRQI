"""Export the actual primitive preparation prefix for a representative block."""
import hashlib
import json
import math
from pathlib import Path
from qiskit import qasm3


def export_preparation(compiled,output,execution):
    output=Path(output)
    end=next((i for i,item in enumerate(compiled.data) if item.operation.name=='barrier'),None)
    if end is None:raise ValueError('Preparation boundary missing from compiled inference circuit')
    preparation=compiled.copy();preparation.data=preparation.data[:end]
    gates=[]
    for item in preparation.data:
        name=item.operation.name
        if name not in ('u','cx','reset'):raise ValueError('Unexpected preparation primitive: '+name)
        gates.append([name,[preparation.find_bit(q).index for q in item.qubits],[float(p) for p in item.operation.params]])
    n=preparation.num_qubits;tile=execution['tile_size'];position=int(math.log2(tile*tile))
    bits=int(math.log2(tile));roles=['column '+str(i) for i in range(bits)]+['row '+str(i) for i in range(bits)]
    encoding=execution.get('encoding','QPIE')
    roles+=['brightness angle'] if encoding=='FRQI' else ['brightness bit '+str(i) for i in range(n-position)]
    qasm=qasm3.dumps(preparation)
    # Keep the download byte-identical to its recorded digest on Windows too.
    (output/'state_preparation.qasm').write_bytes(qasm.encode('utf8'))
    data={'encoding':encoding,'qubits':n,'position_qubits':position,'brightness_qubits':n-position,
          'roles':roles,'tile_size':tile,'block_xy':[0,0],
          'subtract_tile_min':execution.get('subtract_tile_min',False),
          'example_only':execution.get('example_only',False),
          'input_png_sha256':hashlib.sha256((output/'input.png').read_bytes()).hexdigest(),
          'instruction_count':len(gates),'counts':dict(preparation.count_ops()),'depth':preparation.depth(),
          'basis':'U(theta, phi, lambda), CX and reset; optimization level 0',
          'semantics':'Equivalent primitive decomposition of the actual first Initialize instruction. Gates after its first barrier, including edge H/shift and measurements, are excluded. Not per-gate hardware telemetry.',
          'qasm_sha256':hashlib.sha256(qasm.encode()).hexdigest(),'gates':gates}
    (output/'state_preparation.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
    return data
