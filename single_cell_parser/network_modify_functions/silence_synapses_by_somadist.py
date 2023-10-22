import single_cell_parser.analyze as sca


def silence_synapses_by_somadist(cell, evokedNW, soma_dist_ranges=None):
    '''
    This allows to silence synapses active at a certain soma distance.
    Parameters:
        soma_dist_ranges: dict, with synapse types as keys (e.g. L5tt_C2) and the range 
            in which it should be silenced as value. Example:
                {'VPM_C2': [0,200],
                 'L5tt_C2': [1000,1200]}
    '''

    assert soma_dist_ranges is not None

    import six
    for synapse_type, ranges_ in six.iteritems(soma_dist_ranges):
        try:
            synapses = cell.synapses[synapse_type]
        except KeyError:
            print('skipping', synapse_type,
                  '(no connected cells of that type present)')
        distances = sca.compute_syn_distances(cell, synapse_type)
        min_, max_ = ranges_
        for syn, dist in zip(synapses, distances):
            if min_ <= dist < max_:
                syn.disconnect_hoc_synapse()