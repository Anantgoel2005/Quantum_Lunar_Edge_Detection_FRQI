import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from preprocessing.upload_image import preprocess_upload


class UploadPreprocessingTests(unittest.TestCase):
    def test_alpha_resize_and_stage_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            pixels=np.zeros((300,900,4),dtype=np.uint8)
            pixels[:,450:]=[100,150,200,255]
            Image.fromarray(pixels).save(root/'input.png')
            info=preprocess_upload(root/'input.png',root/'out')
            self.assertEqual(info['working_size'],[512,171])
            self.assertEqual(Image.open(root/'out/original.png').getpixel((0,0)),(255,255,255))
            for name in ('grayscale','normalized','preprocessed'):
                with Image.open(root/f'out/{name}.png') as result:
                    self.assertEqual(result.size,(512,171))
                    self.assertEqual(result.mode,'L')

    def test_flat_image_stays_flat(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            Image.new('RGB',(16,20),(75,75,75)).save(root/'image.png')
            preprocess_upload(root/'image.png',root/'out')
            self.assertTrue(np.all(np.asarray(Image.open(root/'out/preprocessed.png'))==75))

    def test_orientation_correction(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            exif=Image.Exif();exif[274]=6
            Image.new('RGB',(30,20),'red').save(root/'image.jpg',exif=exif)
            info=preprocess_upload(root/'image.jpg',root/'out')
            self.assertEqual(info['original_size'],[20,30])

    def test_reject_invalid_and_too_small(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'invalid').write_bytes(b'not an image')
            with self.assertRaises(ValueError):preprocess_upload(root/'invalid',root/'out')
            Image.new('L',(1,20)).save(root/'tiny.png')
            with self.assertRaises(ValueError):preprocess_upload(root/'tiny.png',root/'out')

    def test_float_tiff(self):
        import tifffile
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            tifffile.imwrite(root/'image.tif',np.arange(400,dtype=np.float32).reshape(20,20))
            info=preprocess_upload(root/'image.tif',root/'out')
            self.assertEqual(info['source']['band_count'],1)
            self.assertEqual(info['working_size'],[20,20])

    def test_sixteen_bit_tiff_preserves_contrast(self):
        import tifffile
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            tifffile.imwrite(root/'image.tif',np.linspace(1000,4000,400).astype(np.uint16).reshape(20,20))
            info=preprocess_upload(root/'image.tif',root/'out')
            self.assertEqual(info['source']['raw_dtype'],'uint16')
            prepared=np.asarray(Image.open(root/'out/preprocessed.png'))
            self.assertGreater(int(prepared.max())-int(prepared.min()),200)


if __name__=='__main__':unittest.main()
