"""Modify the :ref:`network_parameters_format`.

"""

# import Interface as I
import pandas as pd
from config.cell_types import EXCITATORY, INHIBITORY

def change_ongoing_interval(n, factor=1, pop=None):
    '''Scales the ongoing frequency with a :paramref:`factor`.

    Does so by scaling the time bins of the ongoing activity of the presynaptic :py:class:`~single_cell_parser.celltypes.Spiketrain` celltype.
    
    Args:
        n (sumatra.parameters.NTParameterSet | dict): The :ref:`network_parameters_format`.
        factor (float): The factor to scale the ongoing frequency with.
        pop (list): The celltypes to apply the scaling to.
    
    Raises:
        AssertionError: If the presynptic :py:class:`~single_cell_parser.celltypes.PointCell` is not of type ``spiketrain``.

    Example:
        >>> celltype = 'L6cc_C2'  # layer 6 cortico-cortical cells in column C2
        >>> n.network[celltype].celltype.pointcell.intervals
        [(0, 1000)]
        >>> change_ongoing_interval(n, 2, pop=['L6cc'])
        >>> n.network[celltype].celltype.pointcell.intervals
        [(0, 2000)]

    '''
    for c in list(n.network.keys()):
        celltype, location = c.split('_')
        if not celltype in pop:
            continue
        x = n.network[c]
        if isinstance(x.celltype, str):
            assert x.celltype == 'spiketrain'
            x.interval = x.interval * factor
        else:
            x.celltype.spiketrain.interval = x.celltype.spiketrain.interval * factor


def set_stim_onset(n, onset=None):
    '''Changes the offset when pointcells get activated
    
    Args:
        n (sumatra.parameters.NTParameterSet | dict): The :ref:`network_parameters_format`.
        onset (float): The onset time in milliseconds.

    Example:
        >>> celltype = 'L6cc_C2'  # layer 6 cortico-cortical cells in column C2
        >>> n.network[celltype].celltype.pointcell.offset
        0
        >>> set_stim_onset(n, 100)
        >>> n.network[celltype].celltype.pointcell.offset
        100
    '''
    for c in list(n.network.keys()):
        x = n.network[c]
        if isinstance(x.celltype, str):
            assert x.celltype == 'spiketrain'
            continue
        else:
            x.celltype.pointcell.offset = onset


def change_glutamate_syn_weights(
        param,
        g_optimal=None,
        pop=EXCITATORY):
    '''Changes the glutamate synapse weights in the :ref:`network_parameters_format` to the optimal values.
    
    Args:
        param (sumatra.parameters.NTParameterSet | dict): The :ref:`network_parameters_format`.
        g_optimal (pandas.core.series.Series | pandas.core.frame.DataFrame): 
            The optimal values for the glutamate synapse weights.
            If a :py:class:`~pandas.core.series.Series` is given, the same value is applied to both the AMPA and NMDA receptors.
            If a :py:class:`~pandas.core.frame.DataFrame` is given, the AMPA and NMDA receptors are set to the values in the 'AMPA' and 'NMDA' columns, respectively.
        pop (list): The celltypes to apply the scaling to.
        
    Raises:
        AssertionError: If more than 1 index is found for the celltype in :paramref:`g_optimal`.
        AssertionError: If the celltype is not found in :paramref:`g_optimal`.
    '''
    for key in list(param['network'].keys()):
        celltype = key.split('_')[0]
        if celltype in pop:
            index = [x for x in g_optimal.index if x in celltype]
            assert len(index) == 1

            if type(g_optimal) == pd.core.series.Series:
                g = g_optimal[index[0]]
                param['network'][key]['synapses']['receptors']['glutamate_syn'][
                    'weight'] = [g, g]

            elif type(g_optimal) == pd.core.frame.DataFrame:
                ampa = g_optimal.loc[index[0]]['AMPA']
                nmda = g_optimal.loc[index[0]]['NMDA']
                param['network'][key]['synapses']['receptors']['glutamate_syn'][
                    'weight'] = [ampa, nmda]
            else:
                print('g_optimal is in an unrecognised dataformat')


def change_evoked_INH_scaling(param, factor, pop=INHIBITORY):
    """Scales the response probability for inhibitory cells in the :ref:`network_parameters_format`.
    
    Args:
        param (sumatra.parameters.NTParameterSet | dict): The :ref:`network_parameters_format`.
        factor (float): The scaling factor.
        pop (list): The celltypes to apply the scaling to. 
            Default is the inhibitory celltypes in the rat somatosensory cortex vS1.

"""
    for key in list(param.network.keys()):
        if key.split('_')[0] in pop:
            if param.network[key].celltype == 'spiketrain':
                continue
            prob = param.network[key].celltype.pointcell.probabilities
            prob = [x * factor for x in prob]
            param.network[key].celltype.pointcell.probabilities = prob


def _celltype_matches(celltype_name, celltypes, columns):
    """Check if the celltype name matches the celltypes and columns.
    
    Args:
        celltype_name (str): The celltype name.
        celltypes (list): The celltypes to match.
        columns (list): The columns to match.

    Example:
        >>> celltype_name = 'L6cc_C2'
        >>> celltypes = ['L6cc', 'L5tt']
        >>> columns = ['C2', "B2']
        >>> _celltype_matches(celltype_name, celltypes, columns)
        True
        >>> celltype_name = 'L6cc_C1'
        >>> _celltype_matches(celltype_name, celltypes, columns)
        False
        
    Returns:
        bool: True if the celltype matches the celltypes and columns, False otherwise.
        
    Raises:
        AssertionError: If :paramref:`celltypes` is not a list.
        AssertionError: If :paramref:`columns` is not a list.
    """
    assert isinstance(celltypes, list)
    assert isinstance(columns, list)
    return  celltype_name.split('_')[0] in celltypes \
                and (celltype_name.split('_')[1] in columns or 'S1' in columns)


def _has_evoked(param, celltype):
    """Check if the celltype has evoked activity.
    
    Args:
        param (sumatra.parameters.NTParameterSet | dict): The :ref:`network_parameters_format`.
        celltype (str): The celltype to check.
    
    Returns:
        bool: True if the celltype has evoked activity, False otherwise.

    Raises:
        AssertionError: If :paramref:`celltype` is not in the network
    """
    assert celltype in list(param.network.keys())
    x = param.network[celltype]
    try:
        x.celltype.pointcell.probabilities
        return True
    except:
        return False


def inactivate_evoked_activity_by_celltype_and_column(
        param, 
        inact_celltypes,
        inact_column):
    """Inactivates the evoked activity for the celltypes in the :ref:`network_parameters_format`.
    
    Args:
        param (sumatra.parameters.NTParameterSet | dict): The :ref:`network_parameters_format`.
        inact_celltypes (list): The celltypes to inactivate.
        inact_column (list): The columns to inactivate.

    Example:
        >>> inact_celltypes = ['L6cc_C2']
        >>> network_parameters.network[inact_celltypes[0]].celltype.pointcell.probabilities
        [0.1, 0.1]
        >>> inactivate_evoked_activity_by_celltype_and_column(network_parameters, inact_celltypes, ['C2'])
        >>> network_parameters.network[inact_celltypes[0]].celltype.pointcell.probabilities
        [0, 0]
    """
    for celltype in list(param.network.keys()):
        if _celltype_matches(celltype, inact_celltypes, inact_column) and _has_evoked(param, celltype):
            x = param.network[celltype]
            x.celltype.pointcell.probabilities = [0] * len(x.celltype.pointcell.probabilities)


def inactivate_evoked_and_ongoing_activity_by_celltype_and_column(
        param, 
        inact_celltypes, 
        inact_column):
    """Inactivates both the evoked and ongoing activity for the celltypes in the :ref:`network_parameters_format`.
    
    Does so by completely removing them from the :ref:`network_parameters_format`.

    Args:
        param (sumatra.parameters.NTParameterSet | dict): The :ref:`network_parameters_format`.
        inact_celltypes (list): The celltypes to inactivate.
        inact_column (list): The columns to inactivate.

    Example:
        >>> inact_celltypes = ['L6cc_C2']
        >>> network_parameters.network[inact_celltypes[0]].celltype.pointcell.probabilities
        [0.1, 0.1]
        >>> network_parameters.network[inact_celltypes[0]].celltype.pointcell.intervals
        [(0, 1000)]
        >>> inactivate_evoked_and_ongoing_activity_by_celltype_and_column(network_parameters, inact_celltypes, ['C2'])
        >>> network_parameters.network[inact_celltypes[0]]
        KeyError: 'L6cc_C2'

    """
    for celltype in list(param.network.keys()):
        if _celltype_matches(celltype, inact_celltypes, inact_column):
            del param['network'][celltype]


def multi_stimulus_trial(
        netp,
        inter_stimulus_interval=100,
        stims=100,
        scale_factors=None,
        pop=None):
    '''Makes a network param file for repeatedly stimulating the same whisker during a single trial. 
    
    Optionally applies a different evoked activity scaling factor to each stimulus.
    
    Args:
        netp (sumatra.parameters.NTParameterSet | dict): The :ref:`network_parameters_format`.
        inter_stimulus_interval (int | float): amount of time to wait (in ms) between each whisker stimulus
        stims (int): number of stimuli to simulate
        scale_factors (list, optional): 
            A list of scale factors you want to apply to subsequent stimuli. 
            Must have the same length as stims.
        pop (list, optional): The celltypes you would like the scaling to be applied to.
        
    '''
    if scale_factors is not None:
        assert len(scale_factors) == stims

    for syntype in list(netp.network.keys()):
        try:
            i = netp.network[syntype].celltype.pointcell.intervals
        except:
            continue
        p = netp.network[syntype].celltype.pointcell.probabilities
        intervals = []
        probabilities = []
        offset = 0
        if scale_factors is not None and syntype.split('_')[0] in pop:
            print(syntype)
            for lv, factor in enumerate(scale_factors):
                probabilities.extend([n * factor for n in p])
                intervals.extend([(x[0] + inter_stimulus_interval * lv,
                                   x[1] + inter_stimulus_interval * lv)
                                  for x in i])

        else:
            for lv in range(stims):
                probabilities.extend(p)
                intervals.extend([(x[0] + inter_stimulus_interval * lv,
                                   x[1] + inter_stimulus_interval * lv)
                                  for x in i])

        netp.network[syntype].celltype.pointcell.intervals = intervals
        netp.network[syntype].celltype.pointcell.probabilities = probabilities
