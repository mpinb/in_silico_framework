"""Read and write data.

This subpackage provides mainly the :py:mod:`~data_base.isf_data_base.IO.LoaderDumper` subpackage to read and write data
in various file formats and data types.

In additions, it provides some convenience methods for dask.
"""

import logging
import sys
sys.modules['isf_data_base.IO'] = sys.modules[__name__]

logger = logging.getLogger("ISF").getChild(__name__)