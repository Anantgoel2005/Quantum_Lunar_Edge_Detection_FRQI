"""Extract actual gate checkpoints from the circuits used for edge detection."""
import time
import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer.library import SaveStatevector


def instrument_circuit(circuit):
    """Insert nondestructive simulator saves before final measurements.

    No save is inserted after measurement: that would disable Aer's efficient
    terminal-measurement sampling. The final display uses actual get_counts().
    """
    traced = QuantumCircuit(circuit.num_qubits,circuit.num_clbits,name=circuit.name)
    traced.metadata = dict(circuit.metadata or {})
    traced.append(SaveStatevector(circuit.num_qubits,label='trace_initial'),range(circuit.num_qubits))
    gates,checkpoints = [],[{'label':'trace_initial','gate_index':-1}]
    measurement_qubits = []
    for instruction in circuit.data:
        operation = instruction.operation
        qubits = [circuit.find_bit(q).index for q in instruction.qubits]
        clbits = [circuit.find_bit(c).index for c in instruction.clbits]
        traced.append(operation,qubits,clbits)
        if operation.name == 'barrier':
            continue
        if operation.name == 'measure':
            measurement_qubits.extend(qubits)
            continue
        gate = {'name':operation.name,'qubits':qubits,'gate_index':len(gates)}
        if operation.name in ('x','cx','ccx','mcx'):
            gate.update(target=qubits[-1],controls=qubits[:-1])
        elif operation.name == 'h':
            gate['target'] = qubits[0]
        gates.append(gate)
        label = f'trace_gate_{len(gates)-1}'
        traced.append(SaveStatevector(circuit.num_qubits,label=label),range(circuit.num_qubits))
        checkpoints.append({'label':label,'gate_index':len(gates)-1})
    if measurement_qubits:
        gates.append({'name':'measure','qubits':measurement_qubits,'gate_index':len(gates)})
    return traced,{'name':circuit.name,'qubits':circuit.num_qubits,
        'gates':gates,'checkpoints':checkpoints,'metadata':traced.metadata}


def extract_trace(result,index,description):
    data = result.data(index)
    snapshots = []
    for point in description['checkpoints']:
        vector = np.asarray(data[point['label']],dtype=complex)
        snapshots.append({'gate_index':point['gate_index'],
            'real':np.round(vector.real,10).tolist(),'imag':np.round(vector.imag,10).tolist(),
            'norm':float(np.vdot(vector,vector).real)})
    counts = dict(result.get_counts(index))
    return {key:description[key] for key in ['name','qubits','gates','metadata']} | {
        'snapshots':snapshots,'counts':counts,'shots':sum(counts.values()),
        'measure_sampling':bool(result.results[index].metadata.get('measure_sampling')),
        'source':'Aer save_statevector checkpoints and get_counts from this inference circuit'}


def make_trace_packet(result,descriptions,run_id,batch_number,job_id,tile_y,tile_x,tile_size,
                      started,batch_started,batch_completed):
    return {'run_id':run_id,'sequence':batch_number+1,'job_id':job_id,
        'tile_y':tile_y,'tile_x':tile_x,'tile_size':tile_size,'core_size':tile_size-2,
        'completed_elapsed_seconds':batch_completed-started,
        'batch_execution_seconds':batch_completed-batch_started,
        'captured_at_unix':time.time(),'display_semantics':'Playback of actual checkpoints from the latest completed batch',
        'circuits':[extract_trace(result,index,description) for index,description in descriptions]}
