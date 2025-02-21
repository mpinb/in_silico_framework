"""Build a cell with realized synapses from a :ref:`cell_parameters_format` file and a :ref:`network_parameters_format` file.
"""
import single_cell_parser as scp


def get_cell_with_network(neuron_param, network_param, cache=True):
    """Build a cell with realized synapses from a :ref:`cell_parameters_format` file and a :ref:`network_parameters_format` file.
    
    This method creates a new network embedding for the :py:class:`~single_cell_parser.cell.Cell` based on the :ref:`network_parameters_format` file.
    
    Args:
        neuron_param (str): Path to cell parameter file. 
        network_param (str): Path to network parameter file.
    
    Returns:
        callable: A callable that returns a :py:class:`~single_cell_parser.cell.Cell` and :py:class:`~single_cell_parser.network.NetworkMapper` when called.
    
    See also:
        :py:mod:`simrun.parameters_to_cell` for rebuilding **and** simulating the cell and network from 
        an existing network realization (:ref:`syn_file_format` file) it.
    """
    cell = scp.create_cell(neuron_param.neuron)
    nwMapMutable = [False]  # list that stores current network, always of length 1

    def fun():
        # start with resetting cell and network in case they have previously been used
        cell.re_init_cell()
        if nwMapMutable[0]:
            nwMapMutable[0].re_init_network()
        for sec in cell.sections:
            sec._re_init_vm_recording()
            sec._re_init_range_var_recording()
        
        # initializing network
        nwMap = scp.NetworkMapper(
            cell, 
            network_param.network,
            neuron_param.sim)
        nwMap.create_saved_network2()
        nwMapMutable[0] = nwMap
        
        # special case: a second evokedNW exists in cell.evokedNW
        try:
            cell.evokedNW.re_init_network()
            par = neuron_param['neuron']['cell_modify_functions']['synaptic_input']
            synaptic_input = scp.cell_modify_functions.get('synaptic_input')
            synaptic_input(cell, **par.as_dict())
        except AttributeError:  # if cell.evokedNW does not exist:
            pass  # do nothing
        return cell, nwMap

    return fun