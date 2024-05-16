'''
This module gives convenient access to all subpackages and submodules in ISF:

    - biophysics_fitting
    - data_base
    - dendrite_thickness
    - NEURON mechanisms
    - simrun
    - single_cell_parser
    - single_cell_input_mapper
    - spike_analysis
    - visualize

The recommended use is to import it in a jupyter notebook in the following manner::

    import Interface as I
    
'''
import matplotlib

matplotlib.use('Agg')
matplotlib.rcParams['pdf.fonttype'] = 42  # for text editable in illustrator
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
from config.isf_logging import logger, logger_stream_handler

try:
    from IPython import display
except ImportError:
    pass

try:
    import seaborn as sns
except ImportError:
    logger.warning("Could not import seaborn")

# def warn_with_traceback(message, category, filename, lineno, file=None, line=None):
#
#     log = file if hasattr(file,'write') else sys.stderr
#     traceback.print_stack(file=log)
#     logger.write(warnings.formatwarning(message, category, filename, lineno, line))
#
# warnings.showwarning = warn_with_traceback

# TODO:
# The version is not specific to 'data_base'. Ideally, the '_version.py' file 
# should not reside in the subfolder 'model data base', but in the top folder.
# However, this causes issues.
#
# Currently, git needs to be installed to fetch the current version. 
# Consider using 'versioneer.py' for bundling the package without the 
# necessity of having git installed.
from data_base._version import get_versions
from data_base._module_versions import version_cached

if not 'ISF_MINIMIZE_IO' in os.environ:
    versions = get_versions()
    __version__ = versions['version']
    __git_revision__ = versions['full-revisionid']
    if __version__ == "0+unknown":
        raise OSError("Commit not found\nVersion is {}\nRevision_id is {}). Git is not found, or something else went wrong.".format(__version__, __git_revision__))
    else:
        logger.info("Current version: {version}".format(version = __version__))
        logger.info("Current pid: {pid}".format(pid = os.getpid()))

import data_base
from data_base.data_base import DataBase
from data_base.model_data_base.model_data_base import ModelDataBase
#from model_data_base.analyze.burst_detection import burst_detection
from data_base.analyze.LDA import lda_prediction_rates as lda_prediction_rates
from data_base.analyze.temporal_binning import universal as temporal_binning

from data_base.analyze.spike_detection import spike_detection, spike_in_interval
from data_base.analyze.spatiotemporal_binning import universal as spatiotemporal_binning
from data_base.analyze.spatial_binning import spatial_binning
from data_base.analyze import split_synapse_activation
from data_base.analyze.analyze_input_mapper_result import compare_to_neuronet
# data_base.__init__.py register the correct IO package upon import
from data_base.IO.LoaderDumper import numpy_to_npy as dumper_numpy_to_npy
from data_base.IO.LoaderDumper import numpy_to_npz as dumper_numpy_to_npz
from data_base.IO.LoaderDumper import numpy_to_msgpack as dumper_numpy_to_msgpack
from data_base.IO.LoaderDumper import pandas_to_pickle as dumper_pandas_to_pickle
from data_base.IO.LoaderDumper import pandas_to_msgpack as dumper_pandas_to_msgpack
from data_base.IO.LoaderDumper import pandas_to_parquet as dumper_pandas_to_parquet
from data_base.IO.LoaderDumper import dask_to_msgpack as dumper_dask_to_msgpack
from data_base.IO.LoaderDumper import dask_to_categorized_msgpack as dumper_dask_to_categorized_msgpack
from data_base.IO.LoaderDumper import cell as dumper_cell
from data_base.IO.LoaderDumper import to_pickle as dumper_to_pickle
from data_base.IO.LoaderDumper import to_cloudpickle as dumper_to_cloudpickle
from data_base.IO.LoaderDumper import to_msgpack as dumper_to_msgpack
from data_base.IO.LoaderDumper import reduced_lda_model as dumper_reduced_lda_model

if six.PY3:
    from data_base.IO.LoaderDumper.shared_numpy_store import SharedNumpyStore, shared_array_from_numpy, shared_array_from_disk, shared_array_from_shared_mem_name

from data_base.IO.roberts_formats import write_pandas_synapse_activation_to_roberts_format
from data_base.IO.roberts_formats import read_pandas_synapse_activation_from_roberts_format
from data_base.IO.roberts_formats import read_pandas_cell_activation_from_roberts_format
from data_base.IO.roberts_formats import read_InputMapper_summary
from data_base.db_initializers import load_simrun_general as db_init_simrun_general
from data_base.db_initializers import synapse_activation_binning as db_init_synapse_activation_binning

#--------------- isf db
load_param_files_from_db = db_init_simrun_general.load_param_files_from_db
load_initialized_cell_and_evokedNW_from_db = db_init_simrun_general.load_initialized_cell_and_evokedNW_from_db
#for compatibility, deprecated!
synapse_activation_binning_dask = db_init_synapse_activation_binning.synapse_activation_postprocess_dask
db_init_crossing_over = db_init_roberts_simulations = db_init_simrun_general
mdb_init_crossing_over = db_init_crossing_over

#--------------- mdb
from data_base.db_initializers import load_simrun_general as db_init_simrun_general
from data_base.db_initializers import synapse_activation_binning as db_init_synapse_activation_binning
load_param_files_from_mdb = db_init_simrun_general.load_param_files_from_db
load_initialized_cell_and_evokedNW_from_mdb = db_init_simrun_general.load_initialized_cell_and_evokedNW_from_db
#for compatibility, deprecated!
synapse_activation_binning_dask = db_init_synapse_activation_binning.synapse_activation_postprocess_dask
db_init_crossing_over = db_init_roberts_simulations = db_init_simrun_general

from data_base.analyze import split_synapse_activation  #, color_cellTypeColorMap, excitatory, inhibitory
from data_base.utils import silence_stdout
from data_base.utils import select, pandas_to_array, pooled_std
from data_base.utils import skit, chunkIt
from data_base.utils import cache
from data_base import utils
from data_base.data_base import get_db_by_unique_id
from data_base.data_base_register import assimilate_remote_register
from data_base.dbopen import resolve_db_path, create_db_path

try:  ##to avoid import errors in distributed system because of missing matplotlib backend
    import matplotlib
    import matplotlib.pyplot as plt
    try:
        from visualize.histogram import histogram as histogram
        from visualize.manylines import manylines
        from visualize.rasterplot import rasterplot, rasterplot2, rasterplot2_pdf_grouped
        from visualize.cell_to_ipython_animation import cell_to_ipython_animation, cell_to_animation, display_animation
        from visualize._figure_array_converter import show_pixel_object, PixelObject
    except ImportError as e:
        logger.warning(e)
except ImportError:
    logger.warning("Could not import matplotlib!")

try:
    from simrun.run_existing_synapse_activations import run_existing_synapse_activations \
        as simrun_run_existing_synapse_activations
    from simrun.generate_synapse_activations import generate_synapse_activations \
        as simrun_generate_synapse_activations
    from simrun.run_new_simulations import run_new_simulations \
        as simrun_run_new_simulations
    from simrun.sim_trial_to_cell_object import simtrial_to_cell_object \
        as simrun_simtrial_to_cell_object
    from simrun.sim_trial_to_cell_object import trial_to_cell_object \
        as simrun_trial_to_cell_object
    from simrun.parameters_to_cell import parameters_to_cell as simrun_parameters_to_cell
    from simrun.rerun_db import rerun_db as simrun_rerun_db
    simrun_rerun_mdb = simrun_rerun_db

except ImportError:
    logger.warning("Could not import full-compartmental-model simulator")

import single_cell_parser.analyze as sca
import single_cell_parser as scp
from single_cell_parser import network  # simrun.synaptic_strength_fitting relies on this
try:
    from visualize.cell_morphology_visualizer import CellMorphologyVisualizer
except ImportError:
    logger.warning("Could not import visualize.cell_morphology_visualizer!")
from visualize.utils import write_video_from_images, write_gif_from_images, display_animation_from_images

from simrun.reduced_model import synapse_activation \
    as rm_synapse_activations
#from simrun.reduced_model import spiking_output \
#    as simrun_reduced_model_spiking_output
from simrun.reduced_model import get_kernel \
    as rm_get_kernel

import simrun.synaptic_strength_fitting

from singlecell_input_mapper.map_singlecell_inputs import map_singlecell_inputs
from singlecell_input_mapper.evoked_network_param_from_template import create_network_parameter \
           as create_evoked_network_parameter
from singlecell_input_mapper.ongoing_network_param_from_template import create_network_parameter \
           as create_ongoing_network_parameter

if not 'ISF_MINIMIZE_IO' in os.environ:
    if get_versions()['dirty']: warnings.warn('The source folder has uncommited changes!')

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
    logger.warning('Could not load linked views')

from functools import partial


def svg2emf(filename, path_to_inkscape="/usr/bin/inkscape"):
    '''converts svg to emf, which can be imported in word using inkscape. '''
    command = ' '.join([
        'env -i', path_to_inkscape, "--file", filename, "--export-emf",
        filename[:-4] + ".emf"
    ])
    logger.info(os.system(command))


from data_base._module_versions import version_cached


def print_module_versions():
    module_versions = ["{}: {}".format(x,version_cached.get_module_versions()[x])\
                       for x in sorted(version_cached.get_module_versions().keys())]
    logger.info("Loaded modules with __version__ attribute are:\n" + ', '.join(module_versions))


def get_client(client_port=38786, timeout=120):
    """
    Gets the distributed.client object if dask has been setup

    Returns:
        Client: the client object
    """
    from socket import gethostbyname, gethostname
    from dask.distributed import Client
    client_port = str(client_port)
    if "IP_MASTER" in os.environ.keys():
        if "IP_MASTER_INFINIBAND" in os.environ.keys():
            ip = os.environ['IP_MASTER_INFINIBAND']
        else:
            ip = os.environ["IP_MASTER"]
    else:
        hostname = gethostname()
        ip = gethostbyname(
            hostname
        )  # fetches the ip of the current host, usually "somnalogin01" or "somalogin02"
    logger.info("Getting client with ip {}".format(ip))
    c = Client(ip + ':' + client_port, timeout=timeout)
    logger.info("Got client {}".format(c))
    logger.info("Making mechanisms visible on client side")
    def update_path(): sys.path.insert(0, os.path.dirname(__file__))
    def import_mechanisms(): import mechanisms
    c.run(update_path)
    c.run(import_mechanisms)
    return c

print("\n\n")
print_module_versions()

import barrel_cortex
from barrel_cortex import excitatory, inhibitory, color_cellTypeColorMap, color_cellTypeColorMap_L6paper, color_cellTypeColorMap_L6paper_with_INH

import compatibility
# Set logging level back to WARNING to suppress verbosity in regular usage
logger.setLevel(logging.WARNING)