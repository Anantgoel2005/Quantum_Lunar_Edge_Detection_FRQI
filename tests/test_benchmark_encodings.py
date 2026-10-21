"""Benchmark design safeguards, independent of downloading dataset assets."""
import unittest
import numpy as np
from experiments.benchmark_encodings import select_rows, aggregate, paired_bootstrap, exact_magnitude, measure
from experiments.analyse_encoding_benchmark import geographic_overlaps


class BenchmarkDesign(unittest.TestCase):
    def test_geographic_check_requires_positive_area_and_matching_projection(self):
        case = {'stem': 'NEW_r0', 'crop_xywh': [192, 192, 128, 128],
                'image_info': {'width': 512, 'height': 512},
                'metadata': {'LTM_CODE': 'zone', 'BOUNDS_XMIN': 0, 'BOUNDS_XMAX': 512,
                             'BOUNDS_YMIN': 0, 'BOUNDS_YMAX': 512}}
        common = {'LTM_CODE': 'zone', 'BOUNDS_YMIN': 0, 'BOUNDS_YMAX': 512}
        rows = [{**common, 'WAC_VIS_TILE': 'OVER_r0.nc', 'BOUNDS_XMIN': 0, 'BOUNDS_XMAX': 200},
                {**common, 'WAC_VIS_TILE': 'TOUCH_r0.nc', 'BOUNDS_XMIN': 320, 'BOUNDS_XMAX': 512},
                {**common, 'LTM_CODE': 'other', 'WAC_VIS_TILE': 'OTHER_r0.nc',
                 'BOUNDS_XMIN': 0, 'BOUNDS_XMAX': 512}]
        self.assertEqual(geographic_overlaps([case], rows, {'OVER_r0', 'TOUCH_r0', 'OTHER_r0'}),
                         [{'benchmark': 'NEW_r0', 'prior': 'OVER_r0'}])

    def test_selection_excludes_prior_products_and_duplicate_products(self):
        rows = [{'DATASET': split, 'PRODUCT_ID': product, 'WAC_VIS_TILE': tile}
                for split, product, tile in [('train', 'A', 'A_r0.nc'),
                                              ('test', 'OLD', 'OLD_r2.nc'),
                                              ('test', 'B', 'B_r0.nc'),
                                              ('test', 'B', 'B_r1.nc'),
                                              ('test', 'C', 'C_r0.nc')]]
        chosen = select_rows(rows, ['OLD_r0'], count=2)
        self.assertEqual({c['metadata']['PRODUCT_ID'] for c in chosen}, {'B', 'C'})
        self.assertEqual(chosen, select_rows(rows, ['OLD_r0'], count=2))
        with self.assertRaises(ValueError):
            select_rows(rows, ['OLD_r0'], count=3)

    def test_seed_repeats_are_not_independent_images(self):
        records = [{'method': 'QPIE', 'shots': 1024, 'stem': stem, 'pr_auc': ap}
                   for stem, ap in [('a', 0), ('a', 1), ('b', 1)]]
        summary, per_image = aggregate(records)
        self.assertAlmostEqual(summary[0]['pr_auc'], .75)
        self.assertEqual(summary[0]['images'], 2)
        self.assertAlmostEqual(per_image['QPIE:1024']['a']['pr_auc'], .5)

    def test_bootstrap_pairs_images_and_preserves_constant_difference(self):
        data = {'a': {'x': {'pr_auc': .3}, 'y': {'pr_auc': .6}},
                'b': {'x': {'pr_auc': .2}, 'y': {'pr_auc': .5}}}
        result = paired_bootstrap(data, 'a', 'b')
        self.assertAlmostEqual(result['mean_difference'], .1)
        self.assertAlmostEqual(result['ci95_low'], .1)
        self.assertAlmostEqual(result['ci95_high'], .1)
        data['b'].pop('x')
        with self.assertRaises(ValueError):
            paired_bootstrap(data, 'a', 'b')

    def test_exact_controls_distinguish_gradient_and_quantized_inequality(self):
        image = np.array([[0, 1, 255], [0, 1, 255]], dtype=np.uint8)
        np.testing.assert_array_equal(exact_magnitude(image), [[0, 1, 254], [0, 1, 254]])
        np.testing.assert_array_equal(exact_magnitude(image, True), [[0, 0, 1], [0, 0, 1]])

    def test_scoring_excludes_crop_border_without_dropping_empty_reference(self):
        scores = np.zeros((8, 8)); scores[0, :] = 1
        reference = np.zeros((8, 8), dtype=np.uint8)
        metrics, _ = measure(scores, reference)
        self.assertEqual(metrics['coverage'], 0)
        self.assertEqual(metrics['pr_auc'], 0)
        self.assertIsNone(metrics['chamfer'])


if __name__ == '__main__':
    unittest.main()
