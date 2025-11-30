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
"""Save and load dask dataframes to msgpack.

This uses a fork of the original `pandas_to_msgpack` package, `available on PyPI <https://pypi.org/project/isf-pandas-msgpack/>`_

See also:
    :py:mod:`~data_base.isf_data_base.IO.LoaderDumper.dask_to_parquet` for saving dask dataframes to parquet files.
"""


from . import dask_to_categorized_msgpack
import os

Loader = dask_to_categorized_msgpack.Loader
check = dask_to_categorized_msgpack.check


def dump(obj, savedir, repartition=False, scheduler=None, client=None):
    import os
    return dask_to_categorized_msgpack.dump(
        obj,
        savedir,
        repartition=repartition,
        scheduler=scheduler,
        categorize=False,
        client=client
        )
