"""Cell API for single cell simulations.

This package provides functionality to parse :py:class:`~single_cell_parser.cell.Cell` objects
from NEURON :ref:`hoc_file_format` files, map synapses onto these cells, and run biophysically 
detailed NEURON simulations with the resulting neuron-network models.

See also:
    This package should not be confused with :py:mod:`singlecell_input_mapper`. 
    
    This package is specialized to handle biophysical properties of neurons and simulation runs, and
    provides API access to the NEURON simulator :cite:`hines2001neuron`.
    It handles (among other things) synaptic activations onto a biophysically detailed neuron model.
    
    :py:mod:`singlecell_input_mapper` provides extensive functionality to generate network realizations,
    constrained by empirical data. 
    The results of such pipelines can be read in with this package.

"""

import logging

logger = logging.getLogger("ISF").getChild(__name__)
import warnings

# from sim_control import SimControl
import neuron
import numpy as np
import tables  # so florida servers have no problem with neuron
from sumatra.parameters import NTParameterSet
from sumatra.parameters import build_parameters as build_parameters_sumatra

from config.cell_types import EXCITATORY
from data_base.dbopen import dbopen

from . import network_param_modify_functions
from .cell import Cell, PointCell, PySection, SynParameterChanger
from .cell_parser import CellParser

# from synapse import activate_functional_synapse
from .network import NetworkMapper
from .network_realizations import create_functional_network, create_synapse_realization
from .reader import (
    read_complete_synapse_activation_file,
    read_functional_realization_map,
    read_landmark_file,
    read_scalar_field,
    read_spike_times_file,
    read_synapse_activation_file,
    read_synapse_realization,
    read_synapse_weight_file,
)
from .synapse_mapper import SynapseMapper
from .writer import (
    write_all_traces,
    write_cell_simulation,
    write_cell_synapse_locations,
    write_landmark_file,
    write_presynaptic_spike_times,
    write_PSTH,
    write_sim_results,
    write_spike_times_file,
    write_synapse_activation_file,
    write_synapse_weight_file,
)

__author__ = "Robert Egger"
__credits__ = ["Robert Egger", "Arco Bast"]


# ------------------------------------------------------------------------------
# commonly used functions required for running single neuron simulations
# ------------------------------------------------------------------------------
def build_parameters(filename, fast_but_security_risk=True):
    """Read in a parameter file and return a NTParameterSet object.

    Args:
        filename (str): path to the parameter file
        fast_but_security_risk (bool): If True, the parameter file is read in using eval. This is faster, but can be a security risk if the file is not trusted.

    Returns:
        NTParameterSet: The parameter file as a NTParameterSet object.
    """
    from data_base.dbopen import resolve_db_path

    filename = resolve_db_path(filename)

    if fast_but_security_risk:
        # taking advantage of the fact that sumatra NTParameterSet produces
        # valid python code
        with dbopen(filename, "r") as f:
            dummy = eval(f.read())
        return NTParameterSet(dummy)
    else:
        # slow, but does not call the evil 'eval'
        return build_parameters_sumatra(filename)


def load_NMODL_parameters(parameters):
    """Load NMODL mechanisms from paths in parameter file.

    Parameters are added to the NEURON namespace by executing string Hoc commands.

    See also: https://www.neuron.yale.edu/neuron/static/new_doc/programming/neuronpython.html#important-names-and-sub-packages

    Args:
        parameters (NTParameterSet | dict):
            The neuron parameters to load.
            Must contain the key `NMODL_mechanisms`.
            May contain the key `mech_globals`.

    Returns:
        None. Adds parameters to the NEURON namespace.
    """
    for mech in list(parameters.NMODL_mechanisms.values()):
        neuron.load_mechanisms(mech)
    try:
        for mech in list(parameters.mech_globals.keys()):
            for param in parameters.mech_globals[mech]:
                paramStr = param + "_" + mech + "="
                paramStr += str(parameters.mech_globals[mech][param])
                print("Setting global parameter", paramStr)
                neuron.h(paramStr)
    except AttributeError:
        pass


def create_cell(
    parameters, scaleFunc=None, allPoints=False, setUpBiophysics=True, silent=False
):
    """Creating NEURON cell models from cell parameters.

    Adds spatial discretization and inserts biophysical mechanisms according to parameter file

    Args:
        parameters (dict | dict-like):
            A nested dictionary structure, read from a :ref:`cell_parameters_format` file.
            Should include at least the keys 'filename' and one key per structure present in the :ref:`hoc_file_format` file (e.g. "AIS", "Soma" ...).
            Optional keys include: ``cell_modify_functions``, ``discretization``
        scaleFunc (bool):
            DEPRECATED,  should be specified in the parameters, as described in :meth:`~single_cell_parser.cell_modify_funs`
        allPoints (bool):
            Whether or not to use all the points in the `.hoc` file, or one point per segment (according to the distance-lambda rule).
            Will be passed to ``full`` in :meth:`~single_cell_parser.cell_parser.CellParser.determine_nseg`
        setUpBiophysics (bool):
            Whether or not to insert mechanisms corresponding to the biophysical parameters in ``parameters``

    """
    if scaleFunc is not None:
        warnings.warn(
            "Keyword scaleFunc is deprecated! "
            + "New: To ensure reproducability, scaleFunc should be specified in the parameters, as described in single_cell_parser.cell_modify_funs"
        )
    logger.info("-------------------------------")
    logger.info("Starting setup of cell model...")
    axon = False

    if "AIS" in list(parameters.keys()):
        axon = True

    logger.info("Loading cell morphology...")
    parser = CellParser(parameters.filename)
    parser.spatialgraph_to_cell(parameters, axon, scaleFunc)
    if setUpBiophysics:
        logger.info("Setting up biophysical model...")
        parser.set_up_biophysics(parameters, allPoints)
    logger.info("-------------------------------")

    parser.apply_cell_modify_functions(parameters)
    parser.cell.init_time_recording()
    parser.cell.parameters = parameters
    parser.cell.scaleFunc = scaleFunc
    parser.cell.allPoints = allPoints
    parser.cell.neuronParam = parameters
    return parser.cell


def init_neuron_run(simparam, vardt=False, *events):
    """Default NEURON run with inital parameters according to parameter file.

    Used in :py:mod:`~simrun.run_new_simulations` to set up and run a simulation.

    Args:
        simparam (dict | dict-like):
            A dictionary containing the simulation parameters.
            Must include the keys 'dt', 'tStop', 'Vinit', 'T'.
        vardt (bool):
            Whether or not to use variable time step integration.
        events (callable, optional):
            Optional parameters: callable "events" that are
            passed to Event objects holding a FInitializeHandler.
            This can be used to implement changes of parameters during
            the course of the simulation using ``h.cvode.event(t, "statement")``
            in the supplied callable, where "statement" is another
            Python callable which may be used to change parameters.

    Returns:
        None. Runs the NEURON simulation.
    """
    #    use fixed time step for now
    neuron.h.load_file("stdrun.hoc")
    cvode = neuron.h.CVode()
    if vardt:
        cvode.active(1)
        # minimum tolerance: heuristically
        # tested with BAC firing
        # to give good tradeoff accuracy/speed
    #        cvode.atol(1e-2)
    #        cvode.rtol(2e-3)
    #    neuron.h('using_cvode_=1')
    #    neuron.h('cvode_active(1)')
    #    cvode.use_local_dt(1)
    #    cvode.condition_order(2)
    #    cvode.atol(1e-3)
    #    cvode.rtol(1e-12)
    else:
        cvode.active(0)
    eventList = []
    for event in events:
        e = Event(event)
        eventList.append(e)

    #        print 'added cvode event to EventList'
    neuron.h.dt = simparam.dt
    neuron.h.celsius = simparam.T
    vInitStr = "v_init=" + str(simparam.Vinit)
    neuron.h(vInitStr)
    neuron.h("init()")
    #    neuron.h('run()')
    #    neuron.h.finitialize(simparam.Vinit)
    neuron.run(simparam.tStop)


def sec_distance_to_soma(currentSec):
    """Compute the path length from :``sec(x=0)`` to soma

    Args:
        currentSec (:py:class:`neuron.h.Section`): The section for which to compute the distance.
    """
    parentSec = currentSec.parent
    dist = 0.0
    parentLabel = parentSec.label
    while parentLabel != "Soma":
        dist += parentSec.L
        currentSec = parentSec
        parentSec = currentSec.parent
        parentLabel = parentSec.label
    return dist


class Event:
    """Class to handle events in NEURON simulations."""

    def __init__(self, func):
        self.callback = func
        self.fih = neuron.h.FInitializeHandler(1, self.callback)


def spines_update_synapse_distribution_file(
    cell, synapse_distribution_file, new_synapse_distribution_file
):
    """Update the :ref:`syn_file_format` file to correctly point to spine heads as excitatory synapse locations.

    Spines must already exist, so call this after :py:meth:`create_cell`,
    using the same :ref:`syn_file_format` file that was used to create the cell.

    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell object.
        synapse_distribution_file (str): The path to the original :ref:`syn_file_format` file.
        new_synfile (str): The path to the new :ref:`syn_file_format` file.
            A new_synfile will be created if it does not already exist.
    """
    ## update the .syn file
    spine_heads = []
    for sec in cell.sections:
        if sec.label == "SpineHead":
            spine_heads.append(sec)

    with open(synapse_distribution_file, "r") as synapse_file:
        file_data = synapse_file.readlines()

    i = 0

    for n, line in enumerate(file_data):
        if n > 3:  # line 5 is first line containing data
            line_split = line.split("\t")

            if (line_split[0].split("_"))[0] in EXCITATORY:

                file_data[n] = "\t".join(
                    (
                        line_split[0],
                        str(cell.sections.index(spine_heads[i])),
                        str(1.0) + "\n",
                    )
                )
                i += 1

    with open(new_synapse_distribution_file, "w") as synapse_file:
        synapse_file.writelines(file_data)
    logger.info("Success: .syn file updated")


def spines_update_network_paramfile(
    new_synapse_distribution_file, network_paramfile, new_network_paramfile
):
    """Update a :ref:`network_parameters_format` file to point to a new :ref:`syn_file_format` file.

    Args:
        new_synapse_distribution_file (str): The path to the new :ref:`syn_file_format` file.
        network_paramfile (str): The path to the original :ref:`network_parameters_format` file.
        new_network_paramfile (str): The path to the new :ref:`network_parameters_format` file.
            A new_network_paramfile will be created if it does not already exist.
    """
    network_param = build_parameters(network_paramfile)
    for i in list(network_param.network.keys()):
        network_param.network[i].synapses.distributionFile = (
            new_synapse_distribution_file
        )
    network_param.save(new_network_paramfile)
    logger.info("Success: network.param file updated")
