"""Scientific invariants for the development boundary matcher and pilot split."""
import unittest
import numpy as np
from scipy.optimize import linear_sum_assignment
from evaluation.bsds_boundary import match_pixels, boundary_counts, evaluate_curve, curve_summary
from experiments.bsds_pilot import tasks_for, download


class BoundaryMatching(unittest.TestCase):
    def test_exact_identity_empty_and_no_possible_matches(self):
        a=np.eye(4,dtype=bool)
        p,g=match_pixels(a,a,.5)
        np.testing.assert_array_equal(p,np.flatnonzero(a));np.testing.assert_array_equal(g,p)
        self.assertEqual(len(match_pixels(a,np.zeros_like(a),2)[0]),0)
        b=np.zeros_like(a);b[0,3]=1
        c=np.zeros_like(a);c[3,0]=1
        self.assertEqual(len(match_pixels(b,c,1)[0]),0)

    def test_random_small_assignments_match_independent_dense_solver(self):
        rng=np.random.default_rng(82)
        for _ in range(50):
            a,b=np.zeros((5,5),bool),np.zeros((5,5),bool)
            a.flat[rng.choice(25,4,replace=False)]=True;b.flat[rng.choice(25,4,replace=False)]=True
            p,g=match_pixels(a,b,1.5)
            pp=np.argwhere(a);gg=np.argwhere(b)
            distances=np.linalg.norm(pp[:,None]-gg[None,:],axis=2)
            dense=np.full((4,8),1000.)
            dense[:,:4]=np.where(distances<=1.5,distances+1,1e9)
            ri,ci=linear_sum_assignment(dense)
            valid=ci<4
            self.assertEqual(len(p),int(valid.sum()))
            actual=np.linalg.norm(np.column_stack(np.unravel_index(p,a.shape))-np.column_stack(np.unravel_index(g,a.shape)),axis=1).sum()
            expected=distances[ri[valid],ci[valid]].sum()
            self.assertAlmostEqual(actual,expected,places=10)
            self.assertEqual(len(np.unique(p)),len(p));self.assertEqual(len(np.unique(g)),len(g))

    def test_one_to_one_matching_does_not_count_both_nearby_predictions(self):
        pred=np.zeros((8,8),bool);pred[3,3]=pred[3,4]=True
        gt=np.zeros((1,8,8),bool);gt[0,3,3]=True
        cr,sr,cp,sp=boundary_counts(pred,gt,max_distance=.1,apply_thinning=False)
        self.assertEqual((cr,sr,cp,sp),(1,1,1,2))

    def test_precision_union_and_recall_sum_over_annotators(self):
        pred=np.zeros((8,8),bool);pred[2,2]=pred[5,5]=True
        gt=np.zeros((2,8,8),bool);gt[0,2,2]=True;gt[1,5,5]=True
        np.testing.assert_array_equal(boundary_counts(pred,gt,max_distance=.01,apply_thinning=False),[2,2,2,2])
        gt[1]=gt[0]
        np.testing.assert_array_equal(boundary_counts(pred,gt,max_distance=.01,apply_thinning=False),[2,2,1,2])

    def test_perfect_and_empty_curves_are_bounded(self):
        image=np.zeros((16,16));image[3:12,8]=1
        reference=image[None].astype(bool)
        for values,expected in [(image,1.),(np.zeros_like(image),0.)]:
            curve=evaluate_curve(values,reference)
            self.assertEqual(curve.shape,(31,4))
            result=curve_summary(curve)
            self.assertEqual(result['best_f1'],expected)
            self.assertEqual(result['boundary_ap101'],expected)
        with self.assertRaises(ValueError):evaluate_curve(np.full((16,16),np.nan),reference)

    def test_frozen_task_matrix_and_no_test_download(self):
        cases=[{'id':str(i)} for i in range(20)]
        tasks=tasks_for(cases)
        self.assertEqual(len(tasks),240)
        self.assertEqual(len(set(tasks)),240)
        self.assertFalse(any(case=='19' and config.endswith('8') for case,config,seed in tasks))
        with self.assertRaises(ValueError):download('BSDS500/data/images/test/1.jpg')


if __name__=='__main__':unittest.main()
