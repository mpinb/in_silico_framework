# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.
"""
This method groups by soma distance first, and then also by time. isn't this identical to spatiotemporal binning?

:skip-doc:
"""

from .spatiotemporal_binning import time_list_from_pd
import pandas as pd
import numpy as np
import dask.dataframe as dd
import dask
import compatibility
from .temporal_binning import universal as temporal_binning


def spatial_binning(
    sa,
    min_time=0,
    max_time=245 + 50,
    spatial_bin_size=50,
    spatial_column='soma_distance'):
    '''
    Binning of a pandas Dataframe, that contains timevalues in columns,
    whose name can be converted to int, like the usual spike_times dataframe.

    Parameters:
    spatial_bin_size
    min_time
    max_time
    normalize
    '''
    try:
        len(spatial_bin_size)
        bins = np.arange(0, max(sa[spatial_column]) + spatial_bin_size, spatial_bin_size)
    except:
        bins = spatial_bin_size
    labels = bins[:-1]  # unused
    sd_bins = pd.cut(
        sa[spatial_column],
        bins=bins,
        include_lowest=True,
        labels=bins[:-1])

    values = sa.groupby(sd_bins).apply(
        lambda x: temporal_binning(
            x,
            min_time=min_time,
            max_time=max_time,
            bin_size=max_time - min_time,
            normalize=False)[1][0]).values
    return (bins, values)
