"""Load actual WAC TIFF axes and scale one global grayscale image."""
import numpy as np
import tifffile


def load_real_tiff(path, band='mean', percentiles=(2,98)):
    with tifffile.TiffFile(path) as handle:
        series = handle.series[0]
        raw, axes = series.asarray(), series.axes
    if raw.ndim == 2:
        values = raw.astype(float)
        band_count = 1
    elif raw.ndim == 3 and 'Y' in axes and 'X' in axes:
        arranged = np.moveaxis(raw, [axes.index('Y'),axes.index('X')], [0,1]).astype(float)
        band_count = arranged.shape[2]
        if band == 'mean':
            values = arranged.mean(axis=2)
        else:
            index = int(band)
            if not 0 <= index < band_count:
                raise ValueError(f'Band index must be in 0..{band_count-1}')
            values = arranged[:,:,index]
    else:
        raise ValueError(f'Unsupported TIFF axes {axes} and shape {raw.shape}')
    valid = np.isfinite(values) & (values >= 0)
    if not np.any(valid):
        raise ValueError('TIFF has no valid nonnegative pixels')
    lower, upper = percentiles
    if not 0 <= lower < upper <= 100:
        raise ValueError('Invalid scaling percentiles')
    lo, hi = np.percentile(values[valid], [lower,upper])
    scaled = np.zeros(values.shape, dtype=np.uint8)
    if hi > lo:
        scaled[valid] = np.rint(np.clip((values[valid]-lo)/(hi-lo),0,1)*255).astype(np.uint8)
    info = {'raw_shape':list(raw.shape),'raw_axes':axes,'raw_dtype':str(raw.dtype),
        'band_count':int(band_count),'band_mode':str(band),'percentiles':[lower,upper],
        'scale_low':float(lo),'scale_high':float(hi),'valid_pixels':int(np.count_nonzero(valid)),
        'invalid_pixels':int(np.count_nonzero(~valid)),'image_shape':list(values.shape)}
    return scaled, valid, info
