"""Automatic full-image QHED from actual Aer circuit measurement counts.

Each haloed image block is encoded into FRQI, executes both offsets along
both axes, and is measured. No analytical gradient supplies the output.
Aer retains its supported Initialize instruction in ideal execution.
"""
import gzip
import json
import math
import time
import uuid
from pathlib import Path
import numpy as np
from qiskit_aer import AerSimulator
from quantum.variant_circuit import (build_variant_circuit as build_qhed_circuit,
    variant_counts_to_edge_map as qhed_counts_to_edge_map,measured_response_squared,ENCODING,INTENSITY_BITS,variant_description)
from quantum.simulation import validate_image
from quantum.gate_trace import instrument_circuit, make_trace_packet


def run_full_image_qhed(image, tile_size=16, shots=8192, seed=42, batch_tiles=16,
                        subtract_tile_min=False, audit_path=None, progress=None, snapshot=None,
                        gate_trace=None, trace_audit_path=None):
    image = validate_image(image)
    if not isinstance(tile_size,int) or tile_size < 4 or tile_size & (tile_size-1):
        raise ValueError('tile_size must be a power of two of at least 4')
    if tile_size > 64:
        raise ValueError('Local full-image execution supports tile sizes up to 64')
    if not isinstance(shots,int) or shots < 1 or not isinstance(batch_tiles,int) or batch_tiles < 1:
        raise ValueError('shots and batch_tiles must be positive integers')
    height,width = image.shape
    core = tile_size-2
    padded = np.pad(image,((1,tile_size),(1,tile_size)),mode='edge')
    positions = [(y,x) for y in range(0,height,core) for x in range(0,width,core)]
    h_squared,v_squared = np.zeros(image.shape),np.zeros(image.shape)
    h_probability,v_probability = np.zeros(image.shape),np.zeros(image.shape)
    simulator = AerSimulator(method='statevector',max_parallel_threads=1,max_parallel_experiments=1)
    supported = set(simulator.configuration().basis_gates) | {'measure','barrier'}
    totals = {'measurement_shots':0,'accepted_edge_outcomes':0,'circuits_executed':0}
    audit = None
    trace_audit = None
    run_id = uuid.uuid4().hex
    started = time.perf_counter()
    if audit_path:
        Path(audit_path).parent.mkdir(parents=True,exist_ok=True)
        audit = gzip.open(audit_path,'wt',encoding='utf-8')
    if trace_audit_path:
        Path(trace_audit_path).parent.mkdir(parents=True,exist_ok=True)
        trace_audit = gzip.open(trace_audit_path,'wt',encoding='utf-8')
    representative = None
    simulator_metadata = None
    try:
        for batch_number,start in enumerate(range(0,len(positions),batch_tiles)):
            circuits,descriptors,trace_descriptions = [],[],[]
            batch_positions = positions[start:start+batch_tiles]
            for y,x in batch_positions:
                patch = padded[y:y+tile_size,x:x+tile_size].astype(float)
                offset = float(patch.min()) if subtract_tile_min else 0.
                encoded = patch-offset
                norm_squared = float(np.sum(encoded*encoded))
                for direction in ('horizontal','vertical'):
                    for pair_offset in (0,1):
                        qc,_,_ = build_qhed_circuit(encoded,direction,pair_offset)
                        qc.name = f'QHED_y{y}_x{x}_{direction}_{pair_offset}'
                        if not set(qc.count_ops()).issubset(supported):
                            raise ValueError('Circuit contains instructions unsupported by this simulator')
                        circuits.append(qc)
                        descriptors.append((y,x,offset,norm_squared,direction,pair_offset))
                        if representative is None:
                            representative = qc.copy()
                        if (gate_trace or trace_audit) and (y,x) == batch_positions[0]:
                            traced,description = instrument_circuit(qc)
                            trace_descriptions.append((len(circuits)-1,description))
                            circuits[-1] = traced
            # All edge evidence is obtained from these quantum circuit results.
            batch_started = time.perf_counter()
            job = simulator.run(circuits,shots=shots,seed_simulator=seed+batch_number)
            result = job.result()
            batch_completed = time.perf_counter()
            if not result.success:
                raise RuntimeError(f'Quantum simulation failed: {result.status}')
            simulator_metadata = result.results[0].metadata
            if trace_descriptions:
                tile_y,tile_x = batch_positions[0]
                packet = make_trace_packet(result,trace_descriptions,run_id,batch_number,job.job_id(),
                    tile_y,tile_x,tile_size,started,batch_started,batch_completed)
                packet.update(image_height=height,image_width=width)
                if trace_audit:
                    trace_audit.write(json.dumps(packet,separators=(',',':'))+'\n')
                if gate_trace:
                    gate_trace(packet)
            for index,(y,x,offset,norm,direction,pair_offset) in enumerate(descriptors):
                counts = dict(result.get_counts(index))
                measured = sum(counts.values())
                if measured != shots:
                    raise RuntimeError('Simulator did not return the requested number of shots')
                probability = qhed_counts_to_edge_map(counts,(tile_size,tile_size),direction,pair_offset)
                block_height,block_width = min(core,height-y),min(core,width-x)
                crop = np.s_[1:1+block_height,1:1+block_width]
                target = np.s_[y:y+block_height,x:x+block_width]
                if direction == 'horizontal':
                    if x == 0: probability[:,1] = 0
                    h_probability[target] = np.maximum(h_probability[target],probability[crop])
                    h_squared[target] = np.maximum(h_squared[target],measured_response_squared(probability[crop],tile_size*tile_size))
                else:
                    if y == 0: probability[1,:] = 0
                    v_probability[target] = np.maximum(v_probability[target],probability[crop])
                    v_squared[target] = np.maximum(v_squared[target],measured_response_squared(probability[crop],tile_size*tile_size))
                totals['measurement_shots'] += measured
                totals['accepted_edge_outcomes'] += int(round(probability.sum()*measured))
                totals['circuits_executed'] += 1
                if audit:
                    audit.write(json.dumps({'tile_y':y,'tile_x':x,'direction':direction,'pair_offset':pair_offset,
                        'preparation_offset':offset,'preparation_norm_squared':norm,'encoding':ENCODING,'intensity_bits':None if ENCODING=='FRQI' else INTENSITY_BITS,'shots':measured,
                        'batch_seed':seed+batch_number,'job_id':job.job_id(),'counts':counts})+'\n')
            if progress:
                progress(start+len(batch_positions),len(positions),totals['circuits_executed'],time.perf_counter()-started)
            if snapshot and (batch_number % 4 == 0 or start+len(batch_positions) == len(positions)):
                snapshot(np.sqrt(h_squared+v_squared))
    finally:
        if audit: audit.close()
        if trace_audit: trace_audit.close()
    magnitude = np.sqrt(h_squared+v_squared)
    maximum = float(magnitude.max())
    strength = magnitude/maximum if maximum else magnitude
    metadata = {**totals,'tiles':len(positions),'tile_size':tile_size,'core_size':core,
        'qubits_per_circuit':int(math.log2(tile_size*tile_size))+(1 if ENCODING=='FRQI' else INTENSITY_BITS),
        'encoding':ENCODING,'intensity_bits':None if ENCODING=='FRQI' else INTENSITY_BITS,'edge_operator':variant_description(),'shots_per_circuit':shots,
        'batch_tiles':batch_tiles,'seed_start':seed,'subtract_tile_min':subtract_tile_min,
        'elapsed_seconds':time.perf_counter()-started,'backend':'Qiskit AerSimulator',
        'method':'statevector','ideal_simulation':True,'output_source':'measured circuit counts',
        'normalization':variant_description()+'; combine directional responses and scale globally',
        'maximum_measured_gradient':maximum,'initialization':f'Aer-supported Initialize of the exact {ENCODING} state',
        'measurement_sampling_enabled':bool(simulator_metadata.get('measure_sampling')) if simulator_metadata else None}
    metadata['gate_trace'] = {'enabled':bool(gate_trace or trace_audit_path),
        'representative_blocks':math.ceil(len(positions)/batch_tiles) if gate_trace or trace_audit_path else 0,
        'run_id':run_id,'source':'Checkpoints on the first actual image block of each circuit batch'}
    return {'strength':strength,'magnitude':magnitude,'horizontal_probability':h_probability,
        'vertical_probability':v_probability},metadata,representative
