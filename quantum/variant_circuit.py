"""FRQI angle-state / NEQR binary-state quantum neighbor interference.

The live backend selects ENCODING. Edge evidence comes from position-register
Hadamard measurements, marginalizing the brightness register. No classical
gradient or reconstructed intensity image supplies the edge output.
"""
import math
import numpy as np
from qiskit import QuantumCircuit
from quantum.simulation import validate_image
from quantum.qhed_circuit import qhed_counts_to_edge_map

ENCODING='FRQI'
INTENSITY_BITS=4


def build_variant_circuit(image,direction='horizontal',pair_offset=0):
    image=validate_image(image,power_of_two=True)
    if np.any(image>255):raise ValueError('Expected grayscale intensities in 0..255')
    if direction not in ('horizontal','vertical') or pair_offset not in (0,1):
        raise ValueError('Invalid direction or pair offset')
    height,width=image.shape
    col_bits,row_bits=width.bit_length()-1,height.bit_length()-1
    n_pos=col_bits+row_bits
    selected=list(range(col_bits)) if direction=='horizontal' else list(range(col_bits,n_pos))
    if not selected:raise ValueError('Selected direction must have at least two pixels')
    n_int=1 if ENCODING=='FRQI' else INTENSITY_BITS
    n_qubits=n_pos+n_int
    vector=np.zeros(1<<n_qubits,dtype=float)
    positions=np.arange(image.size)
    flat=image.ravel().astype(float)
    if ENCODING=='FRQI':
        angles=flat/255*math.pi/2
        vector[positions]=np.cos(angles)/math.sqrt(image.size)
        vector[(1<<n_pos)+positions]=np.sin(angles)/math.sqrt(image.size)
    else:
        levels=np.floor(flat/255*((1<<n_int)-1)).astype(int)
        vector[(levels<<n_pos)+positions]=1/math.sqrt(image.size)
    qc=QuantumCircuit(n_qubits,n_qubits,name=f'{ENCODING}_{direction}_{pair_offset}')
    # Native Initialize prepares the exact named image state in ideal Aer.
    # The exported primitive QASM includes a decomposition of this preparation.
    qc.initialize(vector,range(n_qubits));qc.barrier()
    if pair_offset:
        for bit in range(len(selected)-1,0,-1):
            if bit==1:qc.cx(selected[0],selected[bit])
            else:qc.mcx(selected[:bit],selected[bit])
        qc.x(selected[0]);qc.barrier()
    qc.h(selected[0]);qc.barrier()
    qc.measure(range(n_qubits),range(n_qubits))
    roles=['column']*col_bits+['row']*row_bits+(['brightness angle'] if ENCODING=='FRQI' else [f'intensity bit {bit}' for bit in range(n_int)])
    qc.metadata={'direction':direction,'pair_offset':pair_offset,'image_shape':list(image.shape),
                 'encoding':ENCODING,'position_qubits':n_pos,'intensity_qubits':n_int,'qubit_roles':roles,
                 'edge_operator':'Hadamard angle difference' if ENCODING=='FRQI' else 'Hadamard intensity inequality'}
    return qc,n_qubits,selected[0]


def variant_counts_to_edge_map(counts,image_shape,direction,pair_offset=0):
    n_pos=int(math.log2(np.prod(image_shape)))
    marginal={}
    for key,value in counts.items():
        position=int(key.replace(' ',''),2)&((1<<n_pos)-1)
        encoded=format(position,f'0{n_pos}b')
        marginal[encoded]=marginal.get(encoded,0)+value
    return qhed_counts_to_edge_map(marginal,image_shape,direction,pair_offset)


def measured_response_squared(probability,pixel_count):
    if ENCODING=='FRQI':
        # p=(1-cos(theta_a-theta_b))/N after summing both color outcomes.
        angle_difference=2*np.arcsin(np.sqrt(np.clip(pixel_count*probability,0,1)/2))
        return (angle_difference*255*2/math.pi)**2
    # Orthogonal binary color states interfere only when intensities agree:
    # p=0 for equal quantized values, p=1/N otherwise. Finite shots estimate it.
    return pixel_count*probability


def variant_description():
    return ('FRQI brightness-angle interference calibrated to absolute intensity differences'
            if ENCODING=='FRQI' else
            f'NEQR quantum inequality between neighboring {INTENSITY_BITS}-bit intensities; not a gradient magnitude')
