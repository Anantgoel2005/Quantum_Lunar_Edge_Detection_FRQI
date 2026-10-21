"""Scientific guards for matched filtering, target bias and image-level scoring."""
import unittest
import numpy as np
from experiments.bsds_filtering import smooth,rmse,aggregate,interval
from experiments.verify_bsds_filtering import dense_filter


class FilteringInvariants(unittest.TestCase):
    def test_dense_and_separable_filters_agree_at_boundaries(self):
        rng=np.random.default_rng(190)
        for array in (rng.random((9,11)),np.eye(9),np.pad(np.ones((1,1)),((0,8),(0,10)))):
            for sigma in (0.,.5,1.):
                np.testing.assert_allclose(smooth(array,sigma),dense_filter(array,sigma),atol=1e-14,rtol=1e-13)

    def test_zero_identity_and_constant_maps(self):
        array=np.arange(99,dtype=float).reshape(9,11)
        np.testing.assert_array_equal(smooth(array,0),array)
        for sigma in (.5,1.):
            np.testing.assert_allclose(smooth(np.full((9,11),7.),sigma),7.,atol=1e-14)
            np.testing.assert_array_equal(smooth(np.zeros((9,11)),sigma),0.)
        with self.assertRaises(ValueError):smooth(array,.75)

    def test_matched_target_error_is_separate_from_smoothing_bias(self):
        exact=np.zeros((9,9));exact[4,4]=1
        filtered=smooth(exact,1.)
        self.assertEqual(rmse(filtered,filtered),0.)
        self.assertGreater(rmse(filtered,exact),0.)

    def test_seed_count_curves_are_averaged_before_image_optimum(self):
        a=np.tile([0,1,0,1],(31,1));b=a.copy()
        a[0]=[1,1,1,1];b[1]=[1,1,1,1]
        records=[{'boundary_counts':c,'matched_rmse':2.,'raw_rmse':4.} for c in (a,b)]
        result=aggregate(records)
        self.assertEqual(result['best_f1'],.5)
        self.assertEqual(result['matched_rmse'],2.)
        self.assertEqual(result['raw_rmse'],4.)

    def test_bootstrap_accepts_images_and_rejects_seed_pseudoreplication(self):
        result=interval(np.full(20,.125))
        self.assertEqual(result['ci95'],[.125,.125])
        self.assertEqual(result['mean_difference'],.125)
        for values in (np.ones((20,3)),np.ones(60),np.ones(19)):
            with self.assertRaises(ValueError):interval(values)


if __name__=='__main__':unittest.main()
