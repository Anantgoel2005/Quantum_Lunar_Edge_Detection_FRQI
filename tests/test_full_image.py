"""Tests for the measurement-based full-image path and multispectral loader."""
import gzip
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import tifffile
from quantum.qpie_full_image import run_full_image_qhed
from classical.finite_difference import forward_gradient
from preprocessing.real_image import load_real_tiff


class FullImageQuantum(unittest.TestCase):
    def test_full_shape_halos_and_auditable_shots(self):
        image = np.random.default_rng(42).integers(0,256,(9,11),dtype=np.uint8)
        with tempfile.TemporaryDirectory() as folder:
            audit = Path(folder)/'counts.jsonl.gz'
            maps,meta,_ = run_full_image_qhed(image,tile_size=8,shots=65536,batch_tiles=4,audit_path=audit)
            with gzip.open(audit,'rt') as handle:
                records = [json.loads(line) for line in handle]
        self.assertEqual(maps['strength'].shape,image.shape)
        values = image.astype(float)
        gx,gy = np.zeros_like(values),np.zeros_like(values)
        gx[:,1:] = np.diff(values,axis=1)
        gy[1:,:] = np.diff(values,axis=0)
        expected_squared = gx*gx+gy*gy
        norm_map = np.zeros(image.shape)
        for record in records:
            y,x = record['tile_y'],record['tile_x']
            norm_map[y:y+6,x:x+6] = record['preparation_norm_squared']
        # Conservative six-sigma bound for the sum of independent binomial
        # directional estimates; accounts for finite-shot measurement error.
        bound = 6*np.sqrt(2*norm_map*expected_squared/65536)+1e-7
        self.assertTrue(np.all(np.abs(maps['magnitude']**2-expected_squared)<=bound))
        self.assertEqual(meta['circuits_executed'],16)
        self.assertEqual(meta['measurement_shots'],16*65536)
        self.assertEqual(len(records),16)
        self.assertTrue(all(sum(row['counts'].values())==65536 for row in records))
        self.assertEqual(meta['output_source'],'measured circuit counts')

    def test_uniform_input_no_tile_boundary_edges(self):
        maps,_,_ = run_full_image_qhed(np.full((13,19),123,dtype=np.uint8),tile_size=8,shots=512)
        self.assertFalse(np.any(maps['strength']))

    def test_same_configuration_repeats_counts(self):
        image = np.arange(64).reshape(8,8).astype(np.uint8)
        one,_,_ = run_full_image_qhed(image,tile_size=8,shots=512,seed=42)
        two,_,_ = run_full_image_qhed(image,tile_size=8,shots=512,seed=42)
        np.testing.assert_array_equal(one['strength'],two['strength'])

    def test_actual_multispectral_axes(self):
        raw = np.stack([np.arange(64).reshape(8,8)+shift for shift in (0,10,20,30,40)],axis=2).astype(np.float32)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'five_bands.tif'
            tifffile.imwrite(path,raw,metadata={'axes':'YXS'},photometric='minisblack',planarconfig='contig')
            image,valid,info = load_real_tiff(path,percentiles=(0,100))
        self.assertEqual(info['band_count'],5)
        self.assertTrue(valid.all())
        self.assertEqual(image.shape,(8,8))
        self.assertEqual(image[0,0],0)
        self.assertEqual(image[-1,-1],255)


if __name__ == '__main__':
    unittest.main()
