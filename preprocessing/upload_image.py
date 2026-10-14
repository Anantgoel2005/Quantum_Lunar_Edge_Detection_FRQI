"""Prepare user images for the same measurement-based quantum pipeline."""
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageOps
from preprocessing.real_image import load_real_tiff

MAX_BYTES=20*1024*1024
MAX_PIXELS=16_000_000
FORMATS={'PNG','JPEG','WEBP','BMP','TIFF'}


def preprocess_upload(path,output,max_side=512):
    path,output=Path(path),Path(output)
    if path.stat().st_size>MAX_BYTES:
        raise ValueError('Please upload an image smaller than 20 MB')
    tiff=path.read_bytes()[:4] in (b'II*\x00',b'MM\x00*',b'II+\x00',b'MM\x00+')
    scientific=None
    if tiff:
        import tifffile
        with tifffile.TiffFile(path) as handle:
            series=handle.series[0]
            if np.prod(series.shape)>MAX_PIXELS:
                raise ValueError('Decoded TIFF exceeds the 16-million-sample limit')
            scientific=(series.ndim==3 and series.shape[-1]>4) or series.dtype.kind=='f' or series.dtype.itemsize>1
    if scientific:
        gray,valid,source=load_real_tiff(path)
        if not valid.all():
            raise ValueError('TIFF contains invalid or negative pixels')
        original=Image.fromarray(gray).convert('RGB')
        file_format='TIFF'
    else:
        try:
            with Image.open(path) as opened:
                file_format=opened.format
                if file_format not in FORMATS:
                    raise ValueError('Supported formats: PNG, JPEG, WebP, BMP and TIFF')
                if opened.width*opened.height>MAX_PIXELS:
                    raise ValueError('Image exceeds the 16-million-pixel limit')
                opened.load()
                oriented=ImageOps.exif_transpose(opened)
                if 'A' in oriented.getbands() or 'transparency' in oriented.info:
                    rgba=oriented.convert('RGBA')
                    background=Image.new('RGBA',rgba.size,(255,255,255,255))
                    original=Image.alpha_composite(background,rgba).convert('RGB')
                else:
                    original=oriented.convert('RGB')
        except (OSError,Image.DecompressionBombError) as error:
            raise ValueError('This file could not be decoded as a supported image') from error
        source={'format':file_format,'orientation':'EXIF corrected','alpha_background':'white'}
    width,height=original.size
    if min(width,height)<2:
        raise ValueError('The image must be at least 2 pixels in each dimension')
    ratio=min(1,max_side/max(width,height))
    working=(max(2,round(width*ratio)),max(2,round(height*ratio)))
    if working!=original.size:
        original=original.resize(working,Image.Resampling.LANCZOS)
    gray=np.asarray(ImageOps.grayscale(original))
    low,high=np.percentile(gray,[2,98])
    normalized=np.rint(np.clip((gray.astype(float)-low)/(high-low)*255,0,255)).astype(np.uint8) if high>low else gray.copy()
    prepared=cv2.GaussianBlur(normalized,(3,3),0.8)
    output.mkdir(parents=True,exist_ok=True)
    original.save(output/'original.png')
    Image.fromarray(gray).save(output/'grayscale.png')
    Image.fromarray(normalized).save(output/'normalized.png')
    Image.fromarray(prepared).save(output/'preprocessed.png')
    Image.fromarray(prepared).save(output/'input.png')
    Image.fromarray(np.zeros_like(prepared)).save(output/'live_strength.png')
    info={'original_size':[width,height],'working_size':list(working),'image_shape':[working[1],working[0]],
        'format':file_format,'source':source,'resized':working!= (width,height),'max_side':max_side,
        'contrast_percentiles':[2,98],'contrast_limits':[float(low),float(high)],'gaussian_sigma':0.8,
        'steps':['Decode and correct orientation','Composite transparency on white','Fit within 512 pixels, preserving aspect ratio',
                 'Convert to grayscale','Global percentile contrast normalization','Light Gaussian noise reduction'],
        'output':'preprocessed.png'}
    (output/'preprocessing.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    return info
