#import Interface as I
import pandas as pd
import barrel_cortex


def change_ongoing_interval(n, factor=1, pop=None):
    '''scales the ongoing frequency with a factor'''
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
    '''changes the offset when pointcells get activated'''
    for c in list(n.network.keys()):
        x = n.network[c]
        if isinstance(x.celltype, str):
            assert x.celltype == 'spiketrain'
            continue
        else:
            x.celltype.pointcell.offset = onset


def change_glutamate_syn_weights(param,
                                 g_optimal=None,
                                 pop=barrel_cortex.excitatory):
    for key in list(param['network'].keys()):
        celltype = key.split('_')[0]
        if celltype in pop:  # I.excitatory:
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


def change_evoked_INH_scaling(param, factor, pop=barrel_cortex.inhibitory):
    for key in list(param.network.keys()):
        if key.split('_')[0] in pop:
            if param.network[key].celltype == 'spiketrain':
                continue
            prob = param.network[key].celltype.pointcell.probabilities
            prob = [x * factor for x in prob]
            param.network[key].celltype.pointcell.probabilities = prob


def _celltype_matches(celltype_name, celltypes, columns):
    assert isinstance(celltypes, list)
    assert isinstance(columns, list)
    return  celltype_name.split('_')[0] in celltypes \
                and (celltype_name.split('_')[1] in columns or 'S1' in columns)


def _has_evoked(param, celltype):
    assert celltype in list(param.network.keys())
    x = param.network[celltype]
    try:
        x.celltype.pointcell.probabilities
        return True
    except:
        return False


def inactivate_evoked_activity_by_celltype_and_column(param, inact_celltypes,
                                                      inact_column):
    for celltype in list(param.network.keys()):
        if _celltype_matches(celltype, inact_celltypes,
                             inact_column) and _has_evoked(param, celltype):
            x = param.network[celltype]
            x.celltype.pointcell.probabilities = [0] * len(
                x.celltype.pointcell.probabilities)


def inactivate_evoked_and_ongoing_activity_by_celltype_and_column(
        param, inact_celltypes, inact_column):
    for celltype in list(param.network.keys()):
        if _celltype_matches(celltype, inact_celltypes, inact_column):
            del param['network'][celltype]


def multi_stimulus_trial(netp,
                         inter_stimulus_interval=100,
                         stims=100,
                         scale_factors=None,
                         pop=None):
    '''makes a network param file for repeatedly simulating the same whisker stimulus. There is also the option to apply a different evoked activity scaling factor to each stimulus.
    inter_stimulus_interval: int, milliseconds to wait between each whisker stimulus
    stims: int, number of stimuli to simulate
    scale factors: list, optional. A list of scale factors you want to apply to subsequent stimuli. Must have the same length as stims.
    pop: list, optional. The celltypes you would like the scaling to be applied to.'''
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