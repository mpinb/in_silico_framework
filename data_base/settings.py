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