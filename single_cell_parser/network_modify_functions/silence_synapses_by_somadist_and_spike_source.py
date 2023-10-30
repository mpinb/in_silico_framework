import single_cell_parser.analyze as sca
import logging

logger = logging.getLogger("ISF").getChild(__name__)


def silence_synapses_by_somadist_and_spike_source(cell,
                                                  evokedNW,
                                                  soma_dist_ranges=None,
                                                  spike_sources=None):
    '''silences synapse activation at a somadistance (specified in soma_dist_ranges),
    that are from origins not listed in spike_sources.'''
    assert soma_dist_ranges is not None
    assert spike_sources is not None
    import six
    for synapse_type, ranges_ in six.iteritems(soma_dist_ranges):
        try:
            synapses = cell.synapses[synapse_type]
        except KeyError:
            logger.info('skipping', synapse_type,
                     '(no connected cells of that type present)')
        distances = sca.compute_syn_distances(cell, synapse_type)
        min_, max_ = ranges_
        for lv, (syn, dist) in enumerate(zip(synapses, distances)):
            if min_ <= dist < max_:
                if not syn.is_active():
                    continue
                spike_times_backup = syn.releaseSite.spikeTimes[:]
                syn.releaseSite.turn_off()
                for st in spike_times_backup:
                    ss = syn.releaseSite.spike_source[st]
                    if ss in spike_sources:
                        #print 'activating ', st, ss
                        syn.releaseSite.append(st, spike_source=ss)
                    else:
                        logger.info('deactivating synapse of type {}, id {}, activation time {}, soma_distance {}, from source {}'.\
                        format(synapse_type, lv, st, dist, ss))
                #syn.releaseSite.play()
                syn.releaseSite.spikes.play(syn.releaseSite.spikeVec)