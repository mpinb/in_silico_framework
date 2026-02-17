# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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
