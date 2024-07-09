import Interface as I


def get_cell_with_network(neuron_param, network_param, cache=True):
    cell = I.scp.create_cell(neuron_param.neuron)
    nwMapMutable = [False
                   ]  # list that stores current network, always of length 1

    def fun():
        # start with resetting cell and network in case they have previously been used
        cell.re_init_cell()
        if nwMapMutable[0]:
            nwMapMutable[0].re_init_network()
        for sec in cell.sections:
            sec._re_init_vm_recording()
            sec._re_init_range_var_recording()
        # initializing network
        nwMap = I.scp.NetworkMapper(cell, network_param.network,
                                    neuron_param.sim)
        nwMap.create_saved_network2()
        nwMapMutable[0] = nwMap
        # special case: a second evokedNW exists in cell.evokedNW
        try:
            cell.evokedNW.re_init_network()
            par = neuron_param['neuron']['cell_modify_functions'][
                'synaptic_input']
            synaptic_input = I.scp.cell_modify_functions.get('synaptic_input')
            synaptic_input(cell, **par.as_dict())
        except AttributeError:  # if cell.evokedNW does not exist:
            pass  # do nothing
        return cell, nwMap

    return fun