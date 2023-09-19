'''
The purpose of this module is to glue together all libraries necessary for single cell simulations
of cells in barrel cortex. This includes:

 - Moving around hoc-morphologies
 - Compute anatomical realization of presynaptic cells and synapses
 - Activation of synapses based on experimental data
 - determining apropriate biophysical parameters
 - setting up a cluster
 - use that cluster to optimize / find suitable parameters
 - use that cluster to compute single cell responses to synaptic input
 - efficiently store the simulation results and provide an easy interface to query data

The recommended use is to import it in a jupyter notebook in the following manner::

    import Interface as I
    
'''
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['pdf.fonttype'] = 42 # for text editable in illustrator
matplotlib.rcParams['ps.fonttype'] = 42
import os
import sys
import tempfile
import shutil
import glob
import pandas as pd
import numpy as np
import dask
import dask.dataframe as dd
import distributed
import warnings
import traceback
import sys
import collections
from functools import partial
import itertools
from collections import defaultdict
import cloudpickle
import six
import scipy 
import scipy.signal 
import math 

### logging setup
import logging
# All loggers will inherit the root logger's level and handlers
root_logger = logging.getLogger()
# Redirect warnings to the logging system. This will format them accordingly.
logging.captureWarnings(True)
if not any([h.name == "root_logger_stream_handler" for h in root_logger.handlers]):
    # If the stream handler hasn't been set yet: set it.
    # a singular stream handler, so that all logs can redirect to this one
    root_logger_stream_handler = logging.StreamHandler(stream=sys.stdout)
    root_logger_stream_handler.name = "root_logger_stream_handler"
    root_logger_stream_handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    root_logger.handlers = [root_logger_stream_handler]  # Additional handlers can always be configured.
root_logger_stream_handler = [h for h in root_logger.handlers if h.name == "root_logger_stream_handler"][0]

try:
    from IPython import display
except ImportError:
    pass

try:
    import seaborn as sns
except ImportError:
    print("Could not import seaborn")


# def warn_with_traceback(message, category, filename, lineno, file=None, line=None):
#  
#     log = file if hasattr(file,'write') else sys.stderr
#     traceback.print_stack(file=log)
#     log.write(warnings.formatwarning(message, category, filename, lineno, line))
#  
# warnings.showwarning = warn_with_traceback


# todo: the version is not specific to model_data_base,
# therefore - ideally - the _version.py file would not live in the 
# subfolder mondel data base but in the top folder.
# But then it does not work anymore ...
# Currently, git needs to be installed to be able to get
# the current version. Use versioneer.py to be able 
# to bundle package without the need of having git installed.
from model_data_base._version import get_versions
versions = get_versions()
__version__ = versions['version']
__git_revision__ = versions['full-revisionid']

print("Current version: {version}".format(version = __version__))
print("Current pid: {pid}".format(pid = os.getpid()))

import barrel_cortex
from barrel_cortex import excitatory, inhibitory, color_cellTypeColorMap, color_cellTypeColorMap_L6paper, color_cellTypeColorMap_L6paper_with_INH
from model_data_base.model_data_base import ModelDataBase
#from model_data_base.analyze.burst_detection import burst_detection
from model_data_base.analyze.LDA import lda_prediction_rates as lda_prediction_rates
from model_data_base.analyze.temporal_binning import universal as temporal_binning

from model_data_base.analyze.spike_detection import spike_detection, spike_in_interval
from model_data_base.analyze.spatiotemporal_binning import universal as spatiotemporal_binning
from model_data_base.analyze.spatial_binning import spatial_binning
from model_data_base.analyze import split_synapse_activation
from model_data_base.analyze.analyze_input_mapper_result import compare_to_neuronet

from model_data_base.IO.LoaderDumper import dask_to_csv as dumper_dask_to_csv
from model_data_base.IO.LoaderDumper import numpy_to_npy as dumper_numpy_to_npy
from model_data_base.IO.LoaderDumper import numpy_to_npz as dumper_numpy_to_npz
from model_data_base.IO.LoaderDumper import numpy_to_msgpack as dumper_numpy_to_msgpack
from model_data_base.IO.LoaderDumper import pandas_to_pickle as dumper_pandas_to_pickle
from model_data_base.IO.LoaderDumper import pandas_to_msgpack as dumper_pandas_to_msgpack
from model_data_base.IO.LoaderDumper import pandas_to_parquet as dumper_pandas_to_parquet
from model_data_base.IO.LoaderDumper import dask_to_msgpack as dumper_dask_to_msgpack
from model_data_base.IO.LoaderDumper import dask_to_categorized_msgpack as dumper_dask_to_categorized_msgpack
from model_data_base.IO.LoaderDumper import cell as dumper_cell
from model_data_base.IO.LoaderDumper import to_pickle as dumper_to_pickle
from model_data_base.IO.LoaderDumper import to_cloudpickle as dumper_to_cloudpickle
from model_data_base.IO.LoaderDumper import to_msgpack as dumper_to_msgpack
from model_data_base.IO.LoaderDumper import reduced_lda_model as dumper_reduced_lda_model

if six.PY3:
    from model_data_base.IO.LoaderDumper.shared_numpy_store import  SharedNumpyStore, shared_array_from_numpy, shared_array_from_disk, shared_array_from_shared_mem_name    

from model_data_base.IO.roberts_formats import write_pandas_synapse_activation_to_roberts_format
from model_data_base.IO.roberts_formats import read_pandas_synapse_activation_from_roberts_format
from model_data_base.IO.roberts_formats import read_pandas_cell_activation_from_roberts_format
from model_data_base.IO.roberts_formats import read_InputMapper_summary

from model_data_base.mdb_initializers import load_simrun_general as mdb_init_simrun_general
from model_data_base.mdb_initializers import synapse_activation_binning as mdb_init_synapse_activation_binning
load_param_files_from_mdb = mdb_init_simrun_general.load_param_files_from_mdb
load_initialized_cell_and_evokedNW_from_mdb = mdb_init_simrun_general.load_initialized_cell_and_evokedNW_from_mdb
#for compatibility, deprecated!
synapse_activation_binning_dask = mdb_init_synapse_activation_binning.synapse_activation_postprocess_dask
mdb_init_crossing_over = mdb_init_roberts_simulations = mdb_init_simrun_general


from model_data_base.analyze import split_synapse_activation #, color_cellTypeColorMap, excitatory, inhibitory
from model_data_base.utils import silence_stdout
from model_data_base.utils import select, pandas_to_array, pooled_std
from model_data_base.utils import skit, chunkIt
from model_data_base.utils import cache
from model_data_base import utils
from model_data_base.model_data_base_register import get_mdb_by_unique_id
from model_data_base.model_data_base_register import assimilate_remote_register
from model_data_base.mdbopen import resolve_mdb_path, create_mdb_path

try: ##to avoid import errors in distributed system because of missing matplotlib backend
    import matplotlib
    import matplotlib.pyplot as plt
    try:
        from visualize.average_std import average_std as average_std
        from visualize.histogram import histogram as histogram
        from visualize.manylines import manylines
        from visualize.rasterplot import rasterplot, rasterplot2, rasterplot2_pdf_grouped
        from visualize.cell_to_ipython_animation import cell_to_ipython_animation, cell_to_animation, display_animation
        from visualize._figure_array_converter import show_pixel_object, PixelObject
    except ImportError as e:
        print(e)
except ImportError:
    print("Could not import matplotlib!")

try:
    from simrun2.run_existing_synapse_activations import run_existing_synapse_activations \
        as simrun_run_existing_synapse_activations
    from simrun2.generate_synapse_activations import generate_synapse_activations \
        as simrun_generate_synapse_activations
    from simrun2.run_new_simulations import run_new_simulations \
        as simrun_run_new_simulations
    from simrun2.sim_trail_to_cell_object import simtrail_to_cell_object \
        as simrun_simtrail_to_cell_object
    from simrun2.sim_trail_to_cell_object import trail_to_cell_object \
        as simrun_trail_to_cell_object
    from simrun2 import crossing_over as simrun_crossing_over_module
    from simrun2.parameters_to_cell import parameters_to_cell as simrun_parameters_to_cell
    from simrun2.rerun_mdb import rerun_mdb as simrun_rerun_mdb
    
    from simrun2.crossing_over.crossing_over_simple_interface import crossing_over as simrun_crossing_over_simple_interface
except ImportError:
    print("Could not import full-compartmental-model simulator")

import single_cell_analyzer as sca
import single_cell_parser as scp
from single_cell_parser import network  # simrun3.synaptic_strength_fitting relies on this
try:
    from visualize.cell_morphology_visualizer import CellMorphologyVisualizer
except ImportError:
    print("Could not import visualize.cell_morphology_visualizer!")
from visualize.utils import write_video_from_images, write_gif_from_images, display_animation_from_images

from simrun2.reduced_model import synapse_activation \
    as rm_synapse_activations
#from simrun2.reduced_model import spiking_output \
#    as simrun_reduced_model_spiking_output
from simrun2.reduced_model import get_kernel \
    as rm_get_kernel

import simrun3.synaptic_strength_fitting


from singlecell_input_mapper.map_singlecell_inputs import map_singlecell_inputs
from singlecell_input_mapper.evoked_network_param_from_template import create_network_parameter \
           as create_evoked_network_parameter
from singlecell_input_mapper.ongoing_network_param_from_template import create_network_parameter \
           as create_ongoing_network_parameter           

if get_versions()['dirty']: warnings.warn('The source folder has uncommited changes!')

from SLURM_scripts.utils import get_user_port_numbers, get_client

defaultdict_defaultdict = lambda: defaultdict(lambda: defaultdict_defaultdict())

import biophysics_fitting
from biophysics_fitting import hay_complete_default_setup as bfit_hay_complete_default_setup
from biophysics_fitting import L5tt_parameter_setup as bfit_L5tt_parameter_setup
from biophysics_fitting.parameters import param_to_kwargs as bfit_param_to_kwargs
from biophysics_fitting.optimizer import start_run as bfit_start_run
try:
    import visualize.linked_views
    from visualize.linked_views.server import LinkedViewsServer
    from visualize.linked_views import defaults as LinkedViewsDefaults
except ImportError:
    print('Could not load linked views')

from functools import partial

def svg2emf(filename, path_to_inkscape = "/usr/bin/inkscape"):
    '''converts svg to emf, which can be imported in word using inkscape. '''
    command = ' '.join(['env -i', path_to_inkscape, "--file", filename,  "--export-emf",  filename[:-4]+".emf"])
    print(os.system(command))

from model_data_base._module_versions import version_cached
def print_module_versions():
    print("Loaded modules with __version__ attribute are:")
    module_versions = ["{}: {}".format(x,version_cached.get_module_versions()[x])\
                       for x in sorted(version_cached.get_module_versions().keys())]
    print(', '.join(module_versions))
    
print('')
print('')
print_module_versions() 
