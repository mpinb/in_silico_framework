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
'''Base settings of the data base'''
#from __future__ import absolute_import
#import dask, dask.multiprocessing
import os  ##

# dask schedulers
#from .compatibility import synchronous_scheduler
#scheduler = dask.multiprocessing.get
#multiprocessing_scheduler = dask.multiprocessing.get#scheduler
#show_computation_progress = True
#dask.set_options(scheduler=scheduler)
#npartitions = 80

# data_base_register
data_base_register_path = os.path.dirname(__file__)