"""rio_cogeo.cogeo"""

import sys

import click

import numpy

from rasterio.io import MemoryFile
from rasterio.enums import Resampling


def create(src, bands, cog_profile, nodata, alpha, overview_level):
    """Create Cloud Optimized Geotiff
    """

    nodata = src.nodata if src.nodata else nodata

    meta = src.meta
    meta.update(**cog_profile)
    meta['count'] = len(bands)

    memfile = MemoryFile()
    with memfile.open(**meta) as dst:

        mask = numpy.zeros((meta['height'], meta['width']), dtype=numpy.uint8)

        wind = list(dst.block_windows(1))

        with click.progressbar(wind, length=len(wind), file=sys.stderr, show_percent=True) as windows:
            for ij, w in windows:
                matrix = src.read(window=w, indexes=bands, resampling=Resampling.bilinear)
                dst.write(matrix, window=w, indexes=bands)

                if nodata is not None:
                    mask_value = numpy.all(matrix != nodata, axis=0).astype(numpy.uint8) * 255
                elif alpha is not None:
                    mask_value = src.read(alpha, window=w, boundless=True,
                                          resampling=Resampling.bilinear)
                else:
                    mask_value = src.read_masks(1, window=w, boundless=True,
                                                resampling=Resampling.bilinear)

                mask[w.row_off:w.row_off + w.height, w.col_off:w.col_off + w.width] = mask_value

        dst.write_mask(mask)

        overviews = [2**j for j in range(1, overview_level + 1)]
        dst.build_overviews(overviews, Resampling.nearest)
        dst.update_tags(ns='rio_overview', resampling=Resampling.nearest.value)

    return memfile
