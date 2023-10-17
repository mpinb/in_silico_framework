import warnings
import single_cell_parser as scp
import logging
log = logging.getLogger("ISF").getChild(__name__)
errstr = "The cell_modify_function synaptic_input is experimental! Make sure synapses "
errstr += "are beeing activated as you expect and have the effect you expect!"

log.warning(errstr)

def synaptic_input(cell, network_param = None, synapse_activation_file = None, tStop = None):
    net = scp.build_parameters(network_param)
    sim = scp.NTParameterSet({'tStop': tStop})
    evokedNW = scp.NetworkMapper(cell, net.network, sim)
    if synapse_activation_file is None:
        log.info('activating synapses')
        evokedNW.create_saved_network2()
    else:
        evokedNW.reconnect_saved_synapses(synapse_activation_file)

    cell.evokedNW = evokedNW
    return cell