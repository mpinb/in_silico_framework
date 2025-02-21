"""Modify network activity by silencing synapses based on soma distance and spike source.

These functions can be used in e.g. :py:mod:`simrun.rerun_db` to re-simulate a network with modified activity patterns,
silencing synapses based on their postsynaptic location, or synapse type (i.e. spike source).
"""

import single_cell_parser.analyze as sca
import logging
logger = logging.getLogger("ISF").getChild(__name__)


def silence_synapses_by_somadist_and_spike_source(
        cell,
        evokedNW,
        soma_dist_ranges=None,
        spike_sources=None):
    '''Silences synapse activation at a :paramref:`soma_dist_ranges`,
    that are from presynaptic origins **not** listed in :paramref:`spike_sources`.

    Args:
        cell (:py:class:`single_cell_parser.cell.Cell`): The cell to modify.
        soma_dist_ranges (dict): A dictionary with synapse types as keys and
            tuples of minimum and maximum soma distances as values.
        spike_sources (list): A list of spike sources to keep active.
    '''
    assert soma_dist_ranges is not None
    assert spike_sources is not None
    import six
    for synapse_type, distance_range in six.iteritems(soma_dist_ranges):
        try:
            synapses = cell.synapses[synapse_type]
        except KeyError:
            logger.info('Skipping ', synapse_type, ' (no connected cells of that type present)')
        distances = sca.compute_syn_distances(cell, synapse_type)
        min_dist, max_dist = distance_range
        for lv, (synapse, dist) in enumerate(zip(synapses, distances)):
            if min_dist <= dist < max_dist:
                if not synapse.is_active():
                    continue
                spike_times_backup = synapse.releaseSite.spikeTimes[:]
                synapse.releaseSite.turn_off()
                for spike_time in spike_times_backup:
                    spike_source = synapse.releaseSite.spike_source[spike_time]
                    if spike_source in spike_sources:
                        # logger.info('activating ', st, ss)
                        synapse.releaseSite.append(spike_time, spike_source=spike_source)
                    else:
                        logger.info('Deactivating synapse of type {}, id {}, activation time {}, soma_distance {}, from source {}'.\
                        format(synapse_type, lv, spike_time, dist, spike_source))
                #syn.releaseSite.play()
                synapse.releaseSite.spikes.play(synapse.releaseSite.spikeVec)
