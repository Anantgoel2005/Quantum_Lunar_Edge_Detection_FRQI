"""Encoding and actual interference laws, including halo stitching and audit."""
import math
import unittest
import numpy as np
from qiskit.quantum_info import Statevector
from quantum.variant_circuit import (ENCODING,INTENSITY_BITS,build_variant_circuit,
    variant_counts_to_edge_map,measured_response_squared)
from quantum.full_image import run_full_image_qhed


class VariantCorrectness(unittest.TestCase):
    def test_exact_encoding(self):
        image=np.array([[0,51,102,153],[204,255,17,238]],dtype=np.uint8)
        circuit,qubits,_=build_variant_circuit(image)
        prep=circuit.copy();prep.data=prep.data[:1]
        actual=Statevector.from_instruction(prep).data
        expected=np.zeros_like(actual)
        for position,value in enumerate(image.flat):
            if ENCODING=='FRQI':
                angle=value/255*math.pi/2
                expected[position]=math.cos(angle)/math.sqrt(image.size)
                expected[image.size+position]=math.sin(angle)/math.sqrt(image.size)
            else:
                level=int(value)/255*((1<<INTENSITY_BITS)-1)
                expected[(int(level)<<3)+position]=1/math.sqrt(image.size)
        np.testing.assert_allclose(actual,expected,atol=1e-12)
        self.assertEqual(qubits,3+(1 if ENCODING=='FRQI' else INTENSITY_BITS))

    def test_all_neighbor_interference_exact(self):
        image=np.array([[0,51,51,255],[17,17,170,238],[255,204,102,0],[0,255,0,255]],dtype=np.uint8)
        if ENCODING=='NEQR':values=np.floor(image.astype(float)/255*((1<<INTENSITY_BITS)-1))
        else:values=image.astype(float)
        for direction,axis in [('horizontal',1),('vertical',0)]:
            expected=np.zeros(image.shape)
            differences=np.diff(values,axis=axis)
            response=differences*differences if ENCODING=='FRQI' else (differences!=0).astype(float)
            if axis:expected[:,1:]=response
            else:expected[1:,:]=response
            measured=[]
            for offset in (0,1):
                circuit,_,_=build_variant_circuit(image,direction,offset)
                state=Statevector.from_instruction(circuit.remove_final_measurements(inplace=False))
                probability=variant_counts_to_edge_map(state.probabilities_dict(),image.shape,direction,offset)
                measured.append(measured_response_squared(probability,image.size))
            np.testing.assert_allclose(np.maximum(*measured),expected,atol=1e-8)

    def test_actual_measurements_halos_qubits_and_repeatability(self):
        image=np.zeros((9,11),dtype=np.uint8);image[:,5:]=255
        packets=[]
        maps,metadata,_=run_full_image_qhed(image,tile_size=8,shots=4096,batch_tiles=2,gate_trace=packets.append)
        self.assertEqual(maps['strength'].shape,image.shape)
        self.assertEqual(metadata['encoding'],ENCODING)
        self.assertEqual(metadata['qubits_per_circuit'],6+(1 if ENCODING=='FRQI' else INTENSITY_BITS))
        self.assertEqual(metadata['circuits_executed'],16)
        self.assertFalse(np.any(maps['strength'][:,0]))
        self.assertFalse(np.any(maps['strength'][:,:5]))
        self.assertTrue(np.all(maps['strength'][:,5]>0))
        self.assertFalse(np.any(maps['strength'][:,6:]))
        self.assertTrue(packets)
        self.assertTrue(all(sum(c['counts'].values())==4096 for p in packets for c in p['circuits']))
        repeated,_,_=run_full_image_qhed(image,tile_size=8,shots=4096,batch_tiles=2)
        np.testing.assert_array_equal(maps['strength'],repeated['strength'])

    def test_equal_intensities_cancel(self):
        maps,_,_=run_full_image_qhed(np.full((13,19),127,dtype=np.uint8),tile_size=8,shots=1024)
        self.assertFalse(np.any(maps['strength']))


if __name__=='__main__':unittest.main()
