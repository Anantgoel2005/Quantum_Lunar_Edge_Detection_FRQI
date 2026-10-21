"""Guard against seed pseudoreplication and optimizing before seed averaging."""
import unittest
import numpy as np
from experiments.bsds_offset20 import scores,paired


class OffsetStatistics(unittest.TestCase):
    def test_seed_curves_are_averaged_before_threshold_selection(self):
        a=np.tile([0,1,0,1],(31,1));b=a.copy()
        a[0]=[1,1,1,1];b[1]=[1,1,1,1]
        self.assertEqual(scores([a])['best_f1'],1)
        self.assertEqual(scores([b])['best_f1'],1)
        self.assertEqual(scores([a,b])['best_f1'],.5)

    def test_pairing_preserves_common_image_effect(self):
        baseline=np.arange(1,21,dtype=float)/32
        result=paired(baseline+.125,baseline)
        self.assertEqual(result['images'],20)
        self.assertEqual(result['improved_images'],20)
        self.assertEqual(result['mean_difference'],.125)
        self.assertEqual(result['ci95'],[.125,.125])

    def test_mismatched_or_seed_matrix_inputs_are_rejected(self):
        for a,b in [([],[]),([1],[1,2]),(np.ones((20,3)),np.ones((20,3)))]:
            with self.assertRaises(ValueError):paired(a,b)


if __name__=='__main__':unittest.main()
