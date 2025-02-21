'''Calculate the cell type specific synaptic strengths of synapses based on the neuron model and network parameters.

This module provides functionality to simulate each synapse in a network-embedded neuron model,
calculate statistics per synapse type (e.g. mean, median and max voltage deflection).
It can linearly interpolates the relationship between the synaptic strength and the EPSP statistics, and
infers the optimal synaptic strength for each synapse type based on empirical data.

The main class :py:class:`~simrun.synaptic_strength_fitting.PSPs` is used to manage the synaptic strength fitting process.
'''

import cloudpickle, logging, six
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from single_cell_parser import NTParameterSet, init_neuron_run
from single_cell_parser.network import activate_functional_synapse
from dask import delayed
from simrun.get_cell_with_network import get_cell_with_network
from collections import defaultdict
defaultdict_defaultdict = lambda: defaultdict(lambda: defaultdict_defaultdict())
from .utils import get_cellnumbers_from_confile, split_network_param_in_one_elem_dicts
from .get_cell_with_network import get_cell_with_network
from config.cell_types import EXCITATORY, INHIBITORY

logger = logging.getLogger("ISF").getChild(__name__)


###############################
# First part: class to manage synaptic strength fitting
###############################
class PSPs:
    '''Calculate PSP amlitudes of single synapses and fit synaptic strength
    
    Attributes:
        neuron_param (NTParameterSet): The :ref:`cell_parameters_format`.
        confile (str): Path to a :ref:`con_file_format` file.
        gExRange (list): List of allowed synaptic strength values (in :math:`\mu S`).
        AMPA_component (float): 
        NMDA_component (float):
        vardt (bool): Whether to use the variable step size solver.
        mode (str): 
            Whether to activate each synapse one by one, or each cell one by one.
            A presynaptic cell may have multiple synaptic connections with the neuron model (i.e. the :py:class:`~single_cell_parser.cell.Cell`).
            Options: ``('cells', 'synapses')``
            Default: ``'cells'``
        exc_inh (str):
            Whether to fit excitatory or inhibitory synapses.
            Used to infer the deflection direction of the PSP (positive or negative).
            Options: ``('exc', 'inh')``
            Default: ``'exc'``
        tStim (float): Time of the synaptic activation. Should be large enough such that the membrane voltage has time to stabilize.
        tEnd (float): End time of the simulation.
        futures (list): List of futures returned by the dask client, containing the future results of the synaptic strength fitting simulations.
        result (list): List of results returned by the dask client, containing the results of the synaptic strength fitting simulations.
        network_param (NTParameterSet): 
            The :ref:`network_parameters_format` for either excitatory or inhibitory synapses to be fitted.
            The synapse type is defined by :paramref:`exc_inh`.
        network_params_by_celltype (list):
            List of network parameters for each cell type in the network.
    '''

    def __init__(
        self,
        neuron_param=None,
        confile=None,
        gExRange=[0.5, 1.0, 1.5, 2.0],
        AMPA_component=1,
        NMDA_component=1,
        vardt=True,
        mode='cells',
        exc_inh='exc',
        tStim=110,
        tEnd=150):
        ''' 
        Args:
            neuron_param (NTParameterSet): The :ref:`cell_parameters_format`.
            confile (str): Path to a :ref:`con_file_format` file.
            gExRange (list): 
                List of synaptic strength values to simulate (in :math:`\mu S`). 
                The resulting ePSPs will be interpolated and compared to empirical data to find an optimal synaptic strength.
            AMPA_component (float): 
            NMDA_component (float):
            vardt (bool): Whether to use the variable step size solver.
            mode (str): 
                Whether to activate each synapse one by one, or each cell one by one.
                A presynaptic cell may have multiple synaptic connections with the neuron model (i.e. the :py:class:`~single_cell_parser.cell.Cell`).
                Options: ``('cells', 'synapses')``
                Default: ``'cells'``
            exc_inh (str):
                Whether to fit excitatory or inhibitory synapses.
                Used to infer the deflection direction of the PSP (positive or negative).
                Options: ``('exc', 'inh')``
                Default: ``'exc'``
            tStim (float): Time of the synaptic activation. Should be large enough such that the membrane voltage has time to stabilize.
            tEnd (float): End time of the simulation.
        '''
        assert 'neuron' in list(neuron_param.keys())
        self.neuron_param = neuron_param
        self.confile = confile
        self.gExRange = gExRange
        self.vardt = vardt
        self.AMPA_component = AMPA_component
        self.NMDA_component = NMDA_component
        self.mode = mode
        self.tStim = tStim
        self.tEnd = tEnd
        self._keys = []
        self._delayeds = []
        self._simfun = delayed(run_ex_synapses)
        self.futures = None
        self.result = None

        if exc_inh == 'exc':
            self.network_param = generate_ex_network_param_from_network_embedding(self.confile)
        elif exc_inh == 'inh':
            self.network_param = generate_inh_network_param_from_network_embedding(self.confile)
        self.network_params_by_celltype = split_network_param_in_one_elem_dicts(self.network_param)

        self._setup_computation(exc_inh)

    def _setup_computation(self, exc_inh):
        """Construct delayed functions for running single-synapse simulations.
        
        For each celltype in :paramref:`network_params_by_celltype`, create a delayed
        function that activates each synapse of that particular celltype one by one.
        Simulations are reset after each synapse activation.
        The simulations are parallelized across the synaptic strength values in :paramref:`gExRange` and the 
        amount of celltypes in :paramref:`network_params_by_celltype`, so the amount of delayed simulations is 
        ``len(gExRange) * len(network_params_by_celltype)``.
        
        Args:
            exc_inh (str): Whether to fit excitatory or inhibitory synapses.
            
        Returns:
            None. updates the :paramref:`_keys` and :paramref:`_delayeds` attributes.
        """
        if exc_inh == 'exc':
            logger.info('setting up computation for exc cells')
            for n in self.network_params_by_celltype:
                assert len(list(n.network.keys())) == 1
                celltype = list(n.network.keys())[0]
                n.network[celltype]['synapses']
                for gEx in self.gExRange:
                    self._keys.append((celltype, gEx * self.AMPA_component, gEx * self.NMDA_component))
                    d = self._simfun(
                        cloudpickle.dumps(self.neuron_param),
                        cloudpickle.dumps(n),
                        celltype,
                        gAMPA=gEx * self.AMPA_component,
                        gNMDA=gEx * self.NMDA_component,
                        vardt=self.vardt,
                        mode=self.mode,
                        tStim=self.tStim,
                        tEnd=self.tEnd)
                    self._delayeds.append(d)
        elif exc_inh == 'inh':
            logger.info('setting up computation for inh cells')
            for n in self.network_params_by_celltype:
                assert len(list(n.network.keys())) == 1
                celltype = list(n.network.keys())[0]
                n.network[celltype]['synapses']
                for gEx in self.gExRange:
                    self._keys.append((celltype, gEx, gEx))
                    d = self._simfun(
                        cloudpickle.dumps(self.neuron_param),
                        cloudpickle.dumps(n),
                        celltype,
                        gGABA=gEx,
                        vardt=self.vardt,
                        mode=self.mode,
                        tStim=self.tStim,
                        tEnd=self.tEnd)
                    self._delayeds.append(d)

    def run(self, client, rerun=False):
        '''Run the single-cell simulations from the :paramref:`_delayeds`.
        
        The simulations are parallelized across the synaptic strength values in :paramref:`gExRange` and the 
        amount of celltypes in :paramref:`network_params_by_celltype`, so the amount of delayed simulations is 
        ``len(gExRange) * len(network_params_by_celltype)``.
        
        Args:
            client (dask.distributed.Client): The dask client for parallel computation.
            rerun (bool): 
                Force rerun the computation.
                Otherwise, calling this function has no effect if the computation is already running or finished.
                Default: ``False``
                
        Returns:
            None. Updates the :paramref:`futures` attribute.
        '''
        if (self.futures is None) or rerun:
            self.result = None
            self.futures = client.compute(self._delayeds)

    def get_voltage_traces(self):
        '''Gather the ePSP voltage traces for each synapse.
        
        The result is of the form::
        
            {
                celltype_1: {       # from self.network_params_by_celltype
                    g1_1: {         # from self.gExRange
                        g2_1: [
                            t_baseline, 
                            v_baseline, 
                            [[t_vec_1], ...], 
                            [[v_soma_synapse_1], [v_soma_synapse_2], ...]],
                        g2_2: [...],
                        ...
                    },
                    g1_2: {...},
                celltype_2: {...},
            }
            
        For excitatory synapses, :math:`g_1` is the AMPA component and :math:`g_2` is the NMDA component.
        For inhibitory synapses, :math:`g_1` and :math:`g_2` are both the GABA component.

        Returns:
            defaultdict: A dictionary of voltage traces and activation times.
        '''
        if self.result is None:
            self.result = [f.result() for f in self.futures]
            assert len(self._keys) == len(self.result)
            del self.futures
            self.futures = 'done'
        out = defaultdict_defaultdict()
        for n, (cell_type, g1, g2) in enumerate(self._keys):
            out[cell_type][g1][g2] = self.result[n]
            # calculate maximum voltage in the respective simulation
            # list comprehension used to flatten the list
            max = np.max([x for x in self.result[n][3] for x in x])
            #if  max > -45:
            #    errstr = "Result Nr {} has a maximum membrane potential of {} mV. ".format(lv, max) +\
            #             "Make sure, the cell does not depolarize during initialization "+\
            #             "as a suprathreashold activity can potentially change the PSP."
            #    warnings.warn(errstr)
            #if max > 0:
            #    raise RuntimeError(errstr)
        return out

    def get_voltage_and_timing(
        self,
        method='dynamic_baseline',
        merged=False,
        merge_celltype_kwargs=None
        ):
        '''Calculate a PSP's maximum voltage deflection and timing thereof.
        
        Note that for inhibitory synapses, the voltage trace is inverted, so the maximum still
        corresponds to its extremum.
        
        Args:
            method (str):
                ``dynamic_baseline``: a simulation without any synaptic activation is 
                    substracted from a simulation with cell activation. The maximum and 
                    timepoint of maximum is returned
                ``constant_baseline``: the voltage at :math:`t = 110ms` (i.e. directly before
                    synapse activation) is considered as baseline and substracted
                    from all voltages at all timepoints.
                    The maximum and timepoint of the maximum after :math:`t = 110ms` is 
                    returned. 
            merged (bool): Whether to merge the EPSPs of some cell types.
            merge_celltype_kwargs (dict):
                Additional keyword arguments to pass to :py:meth:`~simrun.synaptic_strength_fitting.merge_celltypes`.
        
        Returns:
            defaultdict: A dictionary of voltage traces and activation times.
        '''
        if merge_celltype_kwargs is None:
            merge_celltype_kwargs = {}
        res = self.get_voltage_traces()
        if merged:
            res = merge_celltypes(res, **merge_celltype_kwargs)
        return get_voltage_and_timing(
            res,
            method,
            tStim=self.tStim,
            tEnd=self.tEnd)

    def get_summary_statistics(
        self,
        method='dynamic_baseline',
        merge_celltype_kwargs={},
        ePSP_summary_statistics_kwargs={}
        ):
        """Calculate summary statistics of the PSP voltage and timing.
        
        Args:
            method (str):
                ``dynamic_baseline``: a simulation without any synaptic activation is
                    substracted from a simulation with cell activation. The maximum and
                    timepoint of maximum is returned
                ``constant_baseline``: the voltage at :math:`t = 110ms` (i.e. directly before
                    synapse activation) is considered as baseline and substracted
                    from all voltages at all timepoints.
                    The maximum and timepoint of the maximum after :math:`t = 110ms` is
                    returned.
            merge_celltype_kwargs (dict):
                Additional keyword arguments to pass to :py:meth:`~simrun.synaptic_strength_fitting.merge_celltypes`.
            ePSP_summary_statistics_kwargs (dict):
                Additional keyword arguments to pass to :py:meth:`~simrun.synaptic_strength_fitting.ePSP_summary_statistics`.
                Options: ("threashold", "tPSPStart")

        Returns:
            pd.DataFrame: A table of summary statistics.
            
        Example::
        
            >>> psp.get_summary_statistics(method='dynamic_baseline')
                                epspMean   epspStd   epspMed   epspMin   epspMax      tMean      tStd    tMed
            celltype gAMPA gNMDA                                                                               
            L2      0.5   0.5   0.288331  0.141456  0.262698  0.100779  1.440870  15.509268  2.305882  15.050
                    1.0   1.0    0.538904  0.273115  0.500306  0.129087  2.739804  15.696267  2.420884  15.150
                    1.5   1.5    0.773226  0.395746  0.707955  0.181199  3.927223  15.741435  2.441578  15.175
                    2.0   2.0    0.994781  0.513567  0.891020  0.108587  5.031582  15.881431  2.539182  15.350
            ...
        
        """
        vt = self.get_voltage_and_timing(method, merged=True, merge_celltype_kwargs=merge_celltype_kwargs)
        return ePSP_summary_statistics(vt, **ePSP_summary_statistics_kwargs)

    def get_optimal_g(self, measured_data, method='dynamic_baseline', merge_celltype_kwargs=None):
        """Calculate the optimal synaptic conductance such that the EPSP matches empirical data.
        
        For each celltype (or merged celltype), the optimal synaptic conductance is calculated
        by linearly interpolating the relationship between the synaptic strength and each of the EPSP statistics (mean, median and maximum).
        This linear interpolation is cross-referenced with empirically observed statistics to infer the optimal synaptic conductance.
        
        Args:
            measured_data (pd.DataFrame): 
                A table containing the empirical EPSP statistics (mean, median and maximum) for each celltype.
                Must contain the keys: ``[EPSP_mean_measured, EPSP_median_measured, EPSP_max_measured]`` and the index ``celltype``.
            method (str): ``dynamic_baseline`` or ``constant_baseline``.
            merge_celltype_kwargs (dict): Additional keyword arguments to pass to :py:meth:`~simrun.synaptic_strength_fitting.merge_celltypes`.
            
        Returns:
            pd.DataFrame: A table of the optimal synaptic conductance for each celltype.
            
        See also:
            :py:meth:`~simrun.synaptic_strength_fitting.calculate_optimal_g`.
        """
        if merge_celltype_kwargs is None: merge_celltype_kwargs = {}
        pdf = self.get_summary_statistics(method=method, merge_celltype_kwargs=merge_celltype_kwargs)
        pdf = pdf.reset_index()
        pdf = pdf.groupby('celltype').apply(linear_fit_pdf)
        pdf = pd.concat([pdf, measured_data], axis=1)
        calculate_optimal_g(pdf)
        return pdf

    def visualize_psps(
        self,
        g=1.0,
        method='dynamic_baseline',
        merge_celltype_kwargs={},
        fig=None):
        """Plot a histogram of the EPSP max voltage deflections for each celltype.
        
        Args:
            g (float): The simulated synaptic strength value to plot.
            method (str): ``dynamic_baseline`` or ``constant_baseline``.
            merge_celltype_kwargs (dict): Additional keyword arguments to pass to :py:meth:`~simrun.synaptic_strength_fitting.merge_celltypes`.
            fig (plt.Figure): A matplotlib figure to plot the histograms on.
            
        Returns:
            None. Plots the histograms.
        """
        psp = self
        vt = psp.get_voltage_and_timing(method, merged=True, merge_celltype_kwargs=merge_celltype_kwargs)
        #vt = I.simrun.synaptic_strength_fitting.get_voltage_and_timing(vt, method)
        pdf = pd.concat(
            [
                pd.Series([x[1]for x in vt[name][g][g]], name=name) 
                for name in list(vt.keys())],
            axis=1)
        if fig is None:
            fig = plt.figure(figsize=(10, len(vt) * 1.3))
        ax = fig.add_subplot(111)
        lower_bound = min(0, pdf.min().min())
        upper_bound = max(0, pdf.max().max())
        pdf.plot(
            kind='hist',
            subplots=True,
            bins=np.arange(lower_bound, upper_bound, 0.01),
            ax=ax)

    def _get_cell_and_nw_map(self, network_param=None):
        """Get a network-embedded neuron model and its :py:class:`single_cell_parser.network.Networkmapper` from parameter files.
        
        Args:
            network_param (NTParameterSet): The :ref:`network_parameters_format` file.
            
        Returns:
            tuple: A tuple of the neuron model (:py:class:`single_cell_parser.cell.Cell`) 
                and the :py:class:`single_cell_parser.network.NetworkMapper` that assigns synapses onto it.
        
        """
        neuron_param = self.neuron_param
        if network_param is None:
            network_param = self.network_param  # psp.network_params_by_celltype[0]
        cell_nw_generator = get_cell_with_network(neuron_param, network_param)
        cell, nwMap = cell_nw_generator()
        return cell, nwMap

    def get_synapse_coordinates(
        self,
        population,
        flatten=False,
        cell_indices=None):
        """Get the coordinates of all synapses of a particular celltype.
        
        Args:
            population (str): The celltype to get the synapse coordinates from.
            flatten (bool): Whether to flatten the list of synapse coordinates. Default: ``False``.
            cell_indices (list): A list of cell indices to get the synapse coordinates from. Default: ``None`` (all synapses).
            
        Returns:
            list: A list of synapse coordinates.
        """
        _, nwMap = self._get_cell_and_nw_map()
        cells = nwMap.cells[population]
        if cell_indices is not None:
            cells = [cells[lv] for lv in cell_indices]
        synapses = [c.synapseList for c in cells]
        syn_coordinates = [
            [syn.coordinates for syn in synlist] for synlist in synapses
        ]
        if flatten:
            syn_coordinates = [x for x in syn_coordinates for x in x]
        return syn_coordinates

    def get_merged_synapse_coordinates(self, mergestring, flatten=False):
        """Get the coordinates of all synapses that contain a certain string in their name.
        
        Args:
            mergestring (str): The string to search for in the synapse names.
            flatten (bool): Whether to flatten the list of synapse coordinates. Default: ``False``.
            
        Returns:
            list: A list of synapse coordinates.
        """
        _, nwMap = self._get_cell_and_nw_map()
        cells = []
        for k in sorted(nwMap.cells.keys()):
            if not mergestring in k:
                continue
            logger.info(k)
            cells.extend(nwMap.cells[k])
        synapses = [c.synapseList for c in cells]
        syn_coordinates = [
            [syn.coordinates for syn in synlist] for synlist in synapses
        ]
        if flatten:
            syn_coordinates = [x for x in syn_coordinates for x in x]
        return syn_coordinates

    def get_synapse_coordinates_with_psp_amplitude(
            self,
            population,
            g=1.0,
            merged=True,
            select_synapses_per_cell=None):
        """Get the synapse coordinates and the PSP amplitude for each synapse.
        
        Args:
            population (str): The celltype to get the synapse coordinates for.
            g (float): The synaptic strength value to get the PSP amplitude for.
            merged (bool): Whether to merge the voltage traces of cell types.
            select_synapses_per_cell (int): The amount of synapses per cell to select. Default: ``None`` (all synapses).
            
        Returns:
            np.array: An array of synapse coordinates and PSP amplitudes.
            
        See also:
            :py:meth:`~simrun.synaptic_strength_fitting.merge_celltypes` for merging
            the voltage traces of certain cell types.
        """
        if merged:
            coordinates = self.get_merged_synapse_coordinates(population)
            values = self.get_voltage_and_timing(
                merged=True,
                merge_celltype_kwargs=dict(detection_strings=[population]))
        else:
            coordinates = self.get_synapse_coordinates(population)
            values = self.get_voltage_and_timing(merged=False)
        values = [x[1] for x in values[population][g][g]]
        if select_synapses_per_cell is None:
            dummy = [
                list(c) + [v]
                for clist, v in zip(coordinates, values)
                for c in clist
            ]
        else:
            dummy = [
                list(c) + [v]
                for clist, v in zip(coordinates, values)
                for c in clist
                if len(clist) == select_synapses_per_cell
            ]
        return np.array(dummy)

    #neuron_param = PSP_c2center_robert.neuron_param
    #############
    # changing the hoc_file: does it resolve the issue?
    #####################
    ####################

    def plot_vt(
        self,
        population,
        opacity=1,
        g=1.0,
        merge=True,
        merge_celltype_kwargs={},
        fig=None):
        """Plot the voltage traces of the PSPs.
        
        Args:
            population (str): The celltype to plot the voltage traces for.
            opacity (float): The opacity of the voltage traces. Default: ``1``.
            g (float): The synaptic strength value to plot the voltage traces for.
            merge (bool): Whether to merge the EPSPs of some cell types.
            merge_celltype_kwargs (dict): Additional keyword arguments to pass to :py:meth:`~simrun.synaptic_strength_fitting.merge_celltypes`.
            fig (plt.Figure): A matplotlib figure to plot the voltage traces on.
            
        Returns:
            None. Plots the voltage traces.
        """
        vt = self.get_voltage_traces()  # d.compute(scheduler=I.dask.get)
        if merge:
            vt = merge_celltypes(vt, **merge_celltype_kwargs)
        vt = vt[population][g][g]
        if fig is None:
            fig = plt.figure(figsize=(10, 5))
        fig.suptitle(population)
        ax = fig.add_subplot(121)
        ax.plot(vt[0], vt[1], c='r')
        for lv in range(len(vt[2])):
            ax.plot(vt[2][lv], vt[3][lv], alpha=opacity, c='k')
        t_baseline, v_baseline = np.arange(0, self.tEnd, 0.025), np.interp(
            np.arange(0, self.tEnd, 0.025), vt[0], vt[1])
        ax = fig.add_subplot(122)
        for lv in range(len(vt[2])):
            t, v = vt[2][lv], vt[3][lv]
            t, v = np.arange(0, self.tEnd, 0.025), np.interp(
                np.arange(0, self.tEnd, 0.025), t, v)
            ax.plot(t, v - v_baseline, alpha=opacity, c='k')


#############################################
# Second part: functions to simulate PSPs
#############################################
def set_ex_synapse_weight(syn, weight):
    """Set the synaptic strength of an excitatory :py:class:`single_cell_parser.synapse.Synapse`.
    
    Args:
        syn (:py:class:`single_cell_parser.synapse.Synapse`): The excitatory synapse to set the synaptic strength for.
        weight (list): The synaptic strength values for the AMPA and NMDA components.
        
    Returns:
        None. Updates the synaptic strength of the excitatory synapse.
    """
    if weight is not None:
        assert len(weight) == 2
        gAMPA = weight[0]
        gNMDA = weight[1]
        syn.weight = {'glutamate_syn': [gAMPA, gNMDA]}


def set_inh_synapse_weight(syn, weight):
    """Set the synaptic strength of an inhibitory :py:class:`single_cell_parser.synapse.Synapse`.
    
    Args:
        syn (single_cell_parser.synapse.Synapse): The inhibitory synapse to set the synaptic strength for.
        weight (float): The synaptic strength value.
        
    Returns:
        None. Updates the synaptic strength of the inhibitory synapse.
    """
    if weight is not None:
        gGABA = weight
        syn.weight = {'gaba_syn': gGABA}


def run_ex_synapse(
    cell_nw_generator,
    neuron_param,
    network_param,
    celltype,
    preSynCellID,
    gAMPA=None,
    gNMDA=None,
    gGABA=None,
    vardt=False,
    return_cell=False,
    synapseID=None,
    tEnd=None,
    tStim=None):
    '''Simulate a single excitatory or inhibitory synapse
    
    This is the core function to activate a single synapse and run the simulation.
    Used in the :py:class:`~simrun.synaptic_strength_fitting.PSPs` class to simulate each synapse.
    
    For excitatory synapses, :paramref:`gAMPA` and :paramref:`gNMDA` must be specified, and not :paramref:`gGABA`.
    For inhibitory synapses, only :paramref:`gGABA` may be specified.
    
    Args:
        cell_nw_generator (callable): A callable that returns a :py:class:`~single_cell_parser.cell.Cell` and :py:class:`~single_cell_parser.network.NetworkMapper` when called.
        neuron_param (NTParameterSet): The :ref:`cell_parameters_format`.
        network_param (NTParameterSet): The :ref:`network_parameters_format`.
        celltype (str): The celltype to activate the synapse for. Used to fetch the correct network parameters.
        preSynCellID (int): The presynaptic cell ID to activate the synapse for. Default: ``None``.
        gAMPA (float): The AMPA conductance value. Default: ``None``.
        gNMDA (float): The NMDA conductance value. Default: ``None``.
        gGABA (float): The GABA conductance value. Default: ``None``.
        vardt (bool): Whether to use the variable step size solver. Default: ``False``.
        return_cell (bool): Whether to return the :py:class:`~single_cell_parser.cell.Cell` object. Default: ``False``.
        synapseID (int): The synapse ID to activate. 
            If ``None``, all synapses assigned to the presynaptic cell get activated synchronously during the simulation.
            Default: ``None``.
        tEnd (float): The end time of the simulation. Default: ``None``.
        tStim (float): The time of the synaptic activation. Default: ``None``.
        
    Returns:
        tuple: A tuple of the time vector and the voltage trace at the soma.
    '''
    spikeTime = 0
    assert tStim is not None
    assert tEnd is not None
    cell, nwMap = cell_nw_generator()

    # do not disable cells hat do not originate from this network_param
    # for cellType in nwMap.cells.keys():
    for cellType in list(network_param.network.keys()):
        for syn in cell.synapses[cellType]:
            syn.disconnect_hoc_synapse()

    synParameters = network_param.network[celltype]['synapses']

    for syn in cell.synapses[celltype]:
        syn.weight = {}
        if 'glutamate_syn' in list(synParameters.receptors.keys()):
            syn.weight['glutamate_syn'] = [gAMPA, gNMDA]
        if 'gaba_syn' in list(synParameters.receptors.keys()):
            syn.weight['gaba_syn'] = [gGABA]

    if preSynCellID is not None:
        assert ((gAMPA is not None) and
                (gNMDA is not None)) or (gGABA is not None)
        preSynCell = nwMap.cells[celltype][preSynCellID]
        if synapseID is None:
            synapse_list = preSynCell.synapseList
        else:
            synapse_list = [preSynCell.synapseList[synapseID]]
        for syn in synapse_list:
            # syn.weight = {'glutamate_syn': [gAMPA, gNMDA]}
            activate_functional_synapse(
                syn,
                cell,
                preSynCell,
                synParameters,
                releaseTimes=[tStim + spikeTime])

    neuron_param.sim.tStop = tEnd

    init_neuron_run(neuron_param.sim, vardt=vardt)

    if return_cell:
        return cell

    t, v = np.array(cell.tVec), np.array(cell.soma.recVList)[0, :]

    # without the following lines, the simulation will crash from time to time
    try:
        cell.evokedNW.re_init_network()
        logger.info('found evokedNW attached to cell')
        logger.info('explicitly resetting it.')
    except AttributeError:
        pass

    for cellType in list(nwMap.cells.keys()):
        for syn in cell.synapses[cellType]:
            syn.disconnect_hoc_synapse()

    cell.re_init_cell()
    nwMap.re_init_network()

    return t, v


def run_ex_synapses(
    neuron_param,
    network_param,
    celltype,
    gAMPA=None,
    gNMDA=None,
    gGABA=None,
    vardt=False,
    tStim=None,
    tEnd=None,
    mode='cells'):
    '''Simulate all EPSPs of a given celltype, one by one.
    
    This function is used in the :py:class:`~simrun.synaptic_strength_fitting.PSPs` class to simulate each synapse.
    
    Args:
        neuron_param (NTParameterSet): The :ref:`cell_parameters_format`.
        network_param (NTParameterSet): The :ref:`network_parameters_format`.
        celltype (str): The celltype to activate the synapse for. Used to fetch the correct network parameters.
        gAMPA (float): The AMPA conductance value. Default: ``None``.
        gNMDA (float): The NMDA conductance value. Default: ``None``.
        gGABA (float): The GABA conductance value. Default: ``None``.
        vardt (bool): Whether to use the variable step size solver. Default: ``False``.
        tStim (float): The time of the synaptic activation. Default: ``None``.
        tEnd (float): The end time of the simulation. Default: ``None``.
        mode (str):
            Whether to activate each synapse one by one, or each cell one by one.
            A presynaptic cell may have multiple synaptic connections with the neuron model (i.e. the :py:class:`~single_cell_parser.cell.Cell`).
            Options: ``('cells', 'synapses')``
            
    Returns:
        tuple: A tuple containing the votlage bbaseline, and voltage traces of all synapses. Format: ``(t_baseline, v_baseline, [t_vecs], [v_vecs])``
    
    See also:
        :py:meth:`~simrun.synaptic_strength_fitting.PSPs.run_ex_synapse` for the core function to
        simulate a single synapse.
    
    '''

    neuron_param = NTParameterSet(
        cloudpickle.loads(neuron_param).as_dict())
    network_param = NTParameterSet(
        cloudpickle.loads(network_param).as_dict())
    # with I.silence_stdout:
    cell_nw_generator = get_cell_with_network(neuron_param, network_param)
    cell, nwMap = cell_nw_generator()
    
    # Voltage traces for each synapse
    somaT, somaV, = [], []
    
    # Get the baseline by running a sim with no synapses
    t_baseline, v_baseline = run_ex_synapse(
        cell_nw_generator,
                neuron_param,
                network_param,
                celltype,
                None, # preSynCellID: run no synapses
                gAMPA=gAMPA,
                gNMDA=gNMDA,
                gGABA=gGABA,
                vardt=vardt,
                tStim=tStim,
                tEnd=tEnd)
    n_cells = len(nwMap.connected_cells[celltype])
    if mode == 'cells':
        for preSynCellID in range(n_cells):
            logger.info(
                "Activating presyanaptic cell {} of {} cells of celltype {}".
                format(preSynCellID + 1, n_cells, celltype))
            t, v = run_ex_synapse(
                cell_nw_generator,
                neuron_param,
                network_param,
                celltype,
                preSynCellID,
                gAMPA,
                gNMDA,
                vardt=vardt,
                tStim=tStim,
                tEnd=tEnd)
            somaT.append(t), somaV.append(v)
        del cell_nw_generator, cell, nwMap
    if mode == 'synapses':
        for preSynCellID in range(n_cells):
            n_synapses = len(nwMap.cells[celltype][preSynCellID].synapseList)
            for preSynCellSynapseID in range(n_synapses):
                logger.info(
                    "Activating synapse {} of presyanaptic cell {} of {} cells of celltype {}"
                    .format(preSynCellSynapseID + 1, preSynCellID + 1, n_cells,
                            celltype))
                t, v = run_ex_synapse(
                    cell_nw_generator,
                    neuron_param,
                    network_param,
                    celltype,
                    preSynCellID,
                    gAMPA=gAMPA,
                    gNMDA=gNMDA,
                    gGABA=gGABA,
                    vardt=vardt,
                    synapseID=preSynCellSynapseID,
                    tStim=tStim,
                    tEnd=tEnd)
                somaT.append(t), somaV.append(v)
        del cell_nw_generator, cell, nwMap
    return t_baseline, v_baseline, somaT, somaV


def generate_ex_network_param_from_network_embedding(confile):
    '''Generate a network parameter file for excitatory synapses from a :ref:`con_file_format` file.
    
    Generates a template that defines a glutamate-binding synapse with default parameters, as described in the 
    :ref:`network_parameters_format`. Together with a :ref:`con_file_format` file, this template 
    with default parameters is used to construct a network parameter file, that can in turn be used to 
    activate the presynaptic cells one by one.
    
    Returns:
        NTParameterSet: Network parameter file.
        
    See also:
        :py:meth:`simrun.synaptic_strength_fitting.generate_inh_network_param_from_network_embedding`
        for the template of inhibitory synapses.
    '''
    param_template = {
        'glutamate_syn': {
            'delay': 0.0,
            'parameter': {
                'decaynmda': 1.0,
                'facilampa': 0.0,
                'facilnmda': 0.0,
                'tau1': 26.0,
                'tau2': 2.0,
                'tau3': 2.0,
                'tau4': 0.1
            },
            'threshold': 0.0,
            'weight': [0.0, 1.0]
        }
    }

    out = defaultdict_defaultdict()
    import six
    for k, cellnumber in six.iteritems(get_cellnumbers_from_confile(confile)):
        if not k.split('_')[0] in EXCITATORY:
            continue
        out['network'][k]['cellNr'] = cellnumber
        out['network'][k]['activeFrac'] = 1.0
        out['network'][k]['celltype'] = 'pointcell'
        out['network'][k]['spikeNr'] = 1
        out['network'][k]['spikeT'] = 10
        out['network'][k]['spikeWidth'] = 1.0
        out['network'][k]['synapses']['connectionFile'] = confile
        out['network'][k]['synapses']['distributionFile'] = confile[:-3] + 'syn'
        out['network'][k]['synapses']['receptors'] = param_template
    return NTParameterSet(out)


def generate_inh_network_param_from_network_embedding(confile):
    '''Generate a network parameter file for inhibitory synapses from a :ref:`con_file_format` file.
    
    Generates a template that defines a GABA-binding synapse with default parameters, as described in the 
    :ref:`network_parameters_format`. Together with a :ref:`con_file_format` file, this template 
    with default parameters is used to construct a network parameter file, that can in turn be used to 
    activate the presynaptic cells one by one.
    
    Returns:
        NTParameterSet: Network parameter file.
        
    See also:
        :py:meth:`simrun.synaptic_strength_fitting.generate_exc_network_param_from_network_embedding`
        for the template of excitatory synapses.
    '''
    param_template = {
        'gaba_syn': {
            'delay': 0.0,
            'parameter': {
                'decaygaba': 1.0,
                'decaytime': 20.0,
                'e': -80.0,
                'facilgaba': 0.0,
                'risetime': 1.0
            },
            'threshold': 0.0,
            'weight': 1.0
        }
    }

    import six
    out = defaultdict_defaultdict()
    for k, cellnumber in six.iteritems(get_cellnumbers_from_confile(confile)):
        if not k.split('_')[0] in INHIBITORY:
            continue
        out['network'][k]['cellNr'] = cellnumber
        out['network'][k]['activeFrac'] = 1.0
        out['network'][k]['celltype'] = 'pointcell'
        out['network'][k]['spikeNr'] = 1
        out['network'][k]['spikeT'] = 10
        out['network'][k]['spikeWidth'] = 1.0
        out['network'][k]['synapses']['connectionFile'] = confile
        out['network'][k]['synapses']['distributionFile'] = confile[:-3] + 'syn'
        out['network'][k]['synapses']['receptors'] = param_template
    return NTParameterSet(out)


###############################################
# Third part: functions to analyze PSPs
###############################################
def get_voltage_and_timing(
    vt,
    method='dynamic_baseline',
    tStim=None,
    tEnd=None):
    '''Calculate the maximum amplitude (and their timing) of an ePSP for all synapses.
    
    The maximum amplitude is its extremum, hether that is a mimimum or a maximum.
    The result is of the form::
    
        {
            celltype_1: {
                g1_1: {
                    g2_1: [
                        (tMax_1, vMax_1,)  # synapse 1
                        (tMax_2, vMax_2,)  # synapse 2
                        ...
                    ],
                    g2_2: [...],
                    ...
                },
                g1_2: {...},
            celltype_2: {...},
        }
    
    Args:
        vt (defaultdict): Voltage traces and activation times, as returned by :py:meth:`~simrun.synaptic_strength_fitting.PSPs.get_voltage_traces`.
        method (str):
            ``dynamic_baseline``: a simulation without any synaptic activation is 
                substracted from a simulation with cell activation. The maximum and 
                timepoint of maximum is returned
            ``constant_baseline``: the voltage at :math:`t = 110ms` (i.e. directly before
                synapse activation) is considered as baseline and substracted
                from all voltages at all timepoints.
                The maximum and timepoint of the maximum after :math:`t = 110ms` is 
                returned.
        tStim (float): Timepoint of synapse activation.
        tEnd (float): End time of the simulation.
        
    Returns:
        defaultdict: A dictionary where lists of ``(time, max_v)`` are given for each synapse, categorized under the keys ``(cell_type, g1, g2)``.
    '''
    res = vt
    if method == 'dynamic_baseline':
        import six
        vt = {
            cell_type: {
                g1: {
                    g2: [
                        get_tMax_vMax_baseline(t_baseline, v_baseline, t[ind], v_soma[ind], tStim, tEnd)
                        for ind in range(len(t))
                    ]
                    for g2, (t_baseline, v_baseline, t, v_soma) in six.iteritems(g2_ranges)
                }
                for g1, g2_ranges in six.iteritems(g1_ranges)
            } for cell_type, g1_ranges in six.iteritems(res)
        }
    elif method == 'constant_baseline':
        vt = {
            cell_type: {
                g1: {
                    g2: [
                        get_tMax_vMax(t[ind], v_soma[ind], tStim, tEnd)
                        for ind in range(len(t))
                    ]
                    for g2, (_, _, t, v_soma) in six.iteritems(g2_ranges)
                }
                for g1, g2_ranges in six.iteritems(g1_ranges)
            } for cell_type, g1_ranges in six.iteritems(res)
        }
    else:
        errstr = 'Method must be dynamic_baseline or constant_baseline'
        raise ValueError(errstr)
    return vt


def get_summary_statistics(
    self,
    method='dynamic_baseline',
    merge_celltype_kwargs={},
    ePSP_summary_statistics_kwargs={}):
    """Calculate summary statistics of the EPSPs.
    
    Args:
        method (str): ``dynamic_baseline`` or ``constant_baseline``.
        merge_celltype_kwargs (dict): Additional keyword arguments to pass to :py:meth:`~simrun.synaptic_strength_fitting.merge_celltypes`.
        ePSP_summary_statistics_kwargs (dict): Additional keyword arguments to pass to :py:meth:`~simrun.synaptic_strength_fitting.ePSP_summary_statistics`.
        
    Returns:
        pd.DataFrame: A table of summary statistics.
    
    See also:
        :py:meth:`~simrun.synaptic_strength_fitting.ePSP_summary_statistics` for which statistics are calculated.
    """
    vt = self.get_voltage_and_timing(
        method, merged=True, merge_celltype_kwargs=merge_celltype_kwargs)
    vt = merge_celltypes(vt, **merge_celltype_kwargs)
    return ePSP_summary_statistics(vt, **ePSP_summary_statistics_kwargs)


def get_optimal_g(
    self,
    measured_data,
    method='dynamic_baseline',
    threashold=0.1):
    """Calculate the optimal synaptic conductance such that the EPSP matches empirical data.
    
    For each celltype (or merged celltype), the optimal synaptic conductance is calculated
    by linearly interpolating the relationship between the synaptic strength and each of the EPSP statistics (mean, median and maximum).
    This linear interpolation is cross-referenced with empirically observed statistics to infer the optimal synaptic conductance.
    
    Args:
        measured_data (pd.DataFrame): 
            A table containing the empirical EPSP statistics (mean, median and maximum) for each celltype.
            Must contain the keys: ``[EPSP_mean_measured, EPSP_median_measured, EPSP_max_measured]``.
        method (str): ``dynamic_baseline`` or ``constant_baseline``.
        threashold (float): The threashold to consider a celltype as excitatory.
        
    Returns:
        pd.DataFrame: A table of the optimal synaptic conductance for each celltype.
        
    See also:
        :py:meth:`~simrun.synaptic_strength_fitting.calculate_optimal_g`.
    """
    pdf = self.get_summary_statistics(method=method, threashold=threashold)
    pdf = pdf.reset_index()
    pdf = pdf.groupby('celltype').apply(linear_fit_pdf)
    pdf = pd.concat([pdf, measured_data], axis=1)
    calculate_optimal_g(pdf)
    return pdf


def get_tMax_vMax_baseline(
    t_baseline, 
    v_baseline, 
    t, 
    v, 
    tStim=None, 
    tEnd=None
    ):
    '''Calculate the ePSP amplitude.
    
    This method subtracts a voltage trace without any synapse activation from a voltage trace with synapse activation,
    and then calculates the maximum voltage deflection and the timepoint thereof.
    
    Args:
        t_baseline (np.array): Timepoints of the baseline voltage trace.
        v_baseline (np.array): Voltage trace without synapse activation.
        t (np.array): Timepoints of the voltage trace with synapse activation.
        v (np.array): Voltage trace with synapse activation.
        tStim (float): Timepoint of synapse activation.
        tEnd (float): End time of the simulation.
    
    Returns:
        tuple: Timepoint and amplitude of the maximum voltage deflection.
    '''
    assert tStim is not None
    assert tEnd is not None
    try:
        t, v = np.arange(0, tEnd, 0.025), np.interp(np.arange(0, tEnd, 0.025), t, v)
    except:
        raise RuntimeError()
    t_baseline, v_baseline = np.arange(0, tEnd, 0.025), np.interp(np.arange(0, tEnd, 0.025), t_baseline, v_baseline)
    return get_tMax_vMax(t, v - v_baseline, tStim=tStim, tEnd=tEnd)
    # return I.sca.analyze_voltage_trace(v-v_baseline, t)


def analyze_voltage_trace(vTrace, tTrace):
    """Calculate a voltage trace's extremum and time point thereof.
    
    Args:
        vTrace (np.array): Voltage trace.
        tTrace (np.array): Timepoints of the voltage trace.
        
    Returns:
        tuple: Timepoint and amplitude of the maximum voltage deflection.    
    """
    v = np.array(vTrace)
    t = np.array(tTrace)
    max_abs_v = np.abs(v)
    maxT = t[np.argmax(max_abs_v)]
    maxV = v[np.argmax(max_abs_v)]
    return maxT, maxV


def get_tMax_vMax(t, v, tStim=None, tEnd=None):
    '''Calculate the maximum amplitude of an ePSP.
    
    Args:
        t (np.array): Timepoints of the voltage trace.
        v (np.array): Voltage trace.
        tStim (float): Timepoint of synapse activation.
        tEnd (float): End time of the simulation.
        
    Returns:
        tuple: Timepoint and amplitude of the maximum voltage deflection of an ePSP.
    '''
    assert tStim is not None
    assert tEnd is not None
    t, v = np.arange(0, tEnd, 0.025), np.interp(np.arange(0, tEnd, 0.025), t, v)
    start_index = int(tStim - 1 / 0.025)
    stop_index = int(tStim / 0.025)
    baseline = np.median(v[start_index:stop_index])  # 1ms pre-stim
    v -= baseline
    return analyze_voltage_trace(v[stop_index:], t[stop_index:])


def merge_celltypes(
    vt,
    detection_strings=['L2', 'L34', 'L4', 'L5st', 'L5tt', 'L6cc', 'L6ct', 'VPM_C2'],
    celltype_must_be_in=None):
    """Concatenate the EPSPs of given celltypes.
    
    This method concatenates the EPSPs of the given celltypes, and returns a dictionary with the concatenated voltage traces.
    This essentially groups the EPSPs of the given celltypes together, and considers them as one celltype.
    
    Args:
        vt (defaultdict): Voltage traces, as returned by :py:meth:`~simrun.synaptic_strength_fitting.PSPs.get_voltage_traces`.
        detection_strings (list): List of celltypes to concatenate.
        celltype_must_be_in (list): List of celltypes that must be included.
        
    Returns:
        defaultdict: A dictionary with concatenated voltage traces.
    """
    if celltype_must_be_in is None:
        celltype_must_be_in = EXCITATORY

    out = defaultdict_defaultdict()
    for detection_string in detection_strings:
        for celltype in sorted(vt.keys()):
            if not celltype.split('_')[0] in celltype_must_be_in:
                logger.info('skipping {}'.format(celltype))
                continue
            for gAMPA in sorted(vt[celltype].keys()):
                for gNMDA in sorted(vt[celltype][gAMPA].keys()):
                    if detection_string in celltype:
                        # print celltype
                        if not isinstance(out[detection_string][gAMPA][gNMDA],
                                          list):
                            out[detection_string][gAMPA][gNMDA] = [
                                vt[celltype][gAMPA][gNMDA][0],
                                vt[celltype][gAMPA][gNMDA][1], [], []
                            ]
                        out[detection_string][gAMPA][gNMDA][2].extend(
                            vt[celltype][gAMPA][gNMDA][2])
                        out[detection_string][gAMPA][gNMDA][3].extend(
                            vt[celltype][gAMPA][gNMDA][3])

    return out


def ePSP_summary_statistics(vt, threashold=0.1, tPSPStart=100.0):
    """Calculate summary statistics of the PSP voltage and timing.
    
    Args:
        vt (defaultdict): Voltage traces and activation times, as returned by :py:meth:`~simrun.synaptic_strength_fitting.PSPs.get_voltage_traces`.
        threashold (float): Minimum voltage deflection to be considered as a response.
        tPSPStart (float): Timepoint of synapse activation (ms).
        
    Returns:
        pd.DataFrame: A table of summary statistics.
        
    Example::
    
        >>> vt = psp.get_voltage_and_timing(method='dynamic_baseline')
        >>> ePSP_summary_statistics(vt)
                            epspMean   epspStd   epspMed   epspMin   epspMax      tMean      tStd    tMed
        celltype gAMPA gNMDA                                                                               
        L2      0.5   0.5   0.288331  0.141456  0.262698  0.100779  1.440870  15.509268  2.305882  15.050
                1.0   1.0    0.538904  0.273115  0.500306  0.129087  2.739804  15.696267  2.420884  15.150
                1.5   1.5    0.773226  0.395746  0.707955  0.181199  3.927223  15.741435  2.441578  15.175
                2.0   2.0    0.994781  0.513567  0.891020  0.108587  5.031582  15.881431  2.539182  15.350
        ...
    """
    summaryData = []  #I.defaultdict_defaultdict()
    for celltype, g1_ranges in six.iteritems(vt):
        for g1, g2_ranges in six.iteritems(g1_ranges):
            for g2, tv_all_synapses in six.iteritems(g2_ranges):
                # Extract timepoints and maximum voltage deflections as a list
                timepoints_max_epsps = list(t for (t, v) in tv_all_synapses if v >= threashold)
                max_epsps = list(v for (_, v) in tv_all_synapses if v >= threashold)
                
                # If no response above threashold is found, skip this celltype
                if len(timepoints_max_epsps) == 0:
                    logger.info((
                        "skipping celltype {}, gAMPA {}, gNMDA {}: no response above threashold of {} found"
                        .format(celltype, g1, g2, threashold)))
                    continue
                
                # Calculate summary statistics
                out = {}
                out['epspMean'] = np.mean(max_epsps)
                out['epspStd'] = np.std(max_epsps)
                out['epspMed'] = np.median(max_epsps)
                out['epspMin'] = np.min(max_epsps)
                out['epspMax'] = np.max(max_epsps)
                out['tMean'] = np.mean(np.array(timepoints_max_epsps) - tPSPStart)
                out['tStd'] = np.std(np.array(timepoints_max_epsps) - tPSPStart)
                out['tMed'] = np.median(np.array(timepoints_max_epsps) - tPSPStart)
                out['gNMDA'] = g2
                out['gAMPA'] = g1
                out['celltype'] = celltype
                summaryData.append(out)
    return pd.DataFrame(summaryData).set_index(['celltype', 'gAMPA', 'gNMDA'])


def linear_fit(gAMPANMDA, epsp):
    """Calculate a linear fit between the synaptic conductance and the EPSP.
    
    Args:
        gAMPANMDA (np.array): Synaptic conductance.
        epsp (np.array): EPSP.
        
    Returns:
        np.array: The coefficients of the linear fit: offset and slope.
    """
    return np.polyfit(gAMPANMDA, epsp, 1)


def linear_fit_pdf(pdf):
    """Calculate linear fits between the synaptic conductance and the EPSP.
    
    This method calculates the mean and offset of a linear fit between gAMPA and the following statistics of the EPSP:
    
    - mean
    - standard deviation
    - median
    - maximum
    
    Is used to calculate per-celltype conductance values that match empirical data.
    
    Args:
        pdf (pd.DataFrame): 
            A table of summary statistics, as returned by :py:meth:`~simrun.synaptic_strength_fitting.ePSP_summary_statistics`,
            but without an index.
            
    Returns:
        pd.Series: A table of linear fits.
    """
    assert pdf['gAMPA'].equals(pdf['gNMDA'])
    return pd.Series({
        'EPSP mean_offset': linear_fit(pdf.gAMPA, pdf.epspMean)[1],
        'EPSP mean_slope': linear_fit(pdf.gAMPA, pdf.epspMean)[0],
        'EPSP std_offset': linear_fit(pdf.gAMPA, pdf.epspStd)[1],
        'EPSP std_slope': linear_fit(pdf.gAMPA, pdf.epspStd)[0],
        'EPSP med_offset': linear_fit(pdf.gAMPA, pdf.epspMed)[1],
        'EPSP med_slope': linear_fit(pdf.gAMPA, pdf.epspMed)[0],
        'EPSP max_offset': linear_fit(pdf.gAMPA, pdf.epspMax)[1],
        'EPSP max_slope': linear_fit(pdf.gAMPA, pdf.epspMax)[0]
    })


def calculate_optimal_g(pdf):
    """Calculate the optimal synaptic conductance such that the EPSP statistics match empirical data.
    
    This function calculates the optimal synaptic conductance by matching empirically observed EPSP statistics (mean, median, maximum)
    to a linear model. Each statistic provides a different estimate of the optimal ``g``.
    The final optimal ``g`` is then a weighed average of the three statistics, where the weights for ``mean:median:max`` are ``2:2:1`` respectively.
    
    This function is used in :py:class:`~simrun.synaptic_strength_fitting.PSPs` to calculate the optimal synaptic conductance for each celltype.
    
    Args:
        pdf (pd.DataFrame): 
            A table containing the empirical EPSP statistics (mean, median and maximum), and linear fits for each statistic.
            
    Returns:
        None. Updates the original table inplace. Adds the columns ``optimal g``, ``optimal g mean``, ``optimal g median``, and ``optimal g max``.
    
    See also:
        :py:meth:`~simrun.synaptic_strength_fitting.linear_fit_pdf` for the linear model that relates the EPSP statistics to the synaptic conductance.
        
    Example::
    
        >>> pdf = psp.get_summary_statistics(method='dynamic_baseline')
        >>> fit = linear_fit_pdf(pdf)
        >>> fit.head()
            EPSP mean_offset  EPSP mean_slope  EPSP med_offset  EPSP med_slope  EPSP max_offset  EPSP max_slope EPSP_std_offset EPSP_std_slope
        ...
        >>> measured_data
                    EPSP_mean_measured  EPSP_med_measured   EPSP_max_measured
        celltype_1  ...
        celltype_2  ...
        >>> pdf = pd.concat([fit, measured_data], axis=1)
        >>> calculate_optimal_g(pdf)
        >>> pdf[cell_type 1']['optimal g']
        1.85

    """
    mean = (pdf['EPSP_mean_measured'] - pdf['EPSP mean_offset']) / pdf['EPSP mean_slope']
    med = (pdf['EPSP_med_measured'] - pdf['EPSP med_offset']) / pdf['EPSP med_slope']
    max_ = (pdf['EPSP_max_measured'] - pdf['EPSP max_offset']) / pdf['EPSP max_slope']
    pdf['optimal g'] = (2 * mean + 2 * med + 1 * max_) * 1 / 5.
    pdf['optimal g mean'] = mean  #(2 * mean + 2 * med  + 1 * max_ ) * 1 / 5.
    pdf['optimal g median'] = med  #(2 * mean + 2 * med  + 1 * max_ ) * 1 / 5.
    pdf['optimal g max'] = max_  #(2 * mean + 2 * med  + 1 * max_ ) * 1 / 5.
