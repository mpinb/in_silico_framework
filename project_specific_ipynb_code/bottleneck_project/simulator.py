import numpy as np
import torch
import single_cell_parser as scp


class BottleneckANNSimulator:
    # evokedUpNWParameters: this is necessary because we need the input
    def __init__(self,
                 model_soma_vt,
                 model_soma_ap,
                 model_dend_vt,
                 model_dend_ap,
                 spatial_bins_df=None,
                 outdir='',
                 network_paramfile=None):
        '''
        Args:
        - model: trained ANN used for predicting neuron output, morphology and biophysics-specific
        '''
        self.model_soma_vt = model_soma_vt
        self.model_soma_ap = model_soma_ap
        self.model_dend_vt = model_dend_vt
        self.model_dend_ap = model_dend_ap
        self.spatial_bins_df = spatial_bins_df  # where does this come from? depends on the model
        self.temporal_history_window = 80  # This should depend on how the model was trained
        self.outdir = outdir
        self.network_param_file = self.__get_network_from_network_param_file(
            network_paramfile)
        # Check that the model and network param file are referring to the same neuron with the same morphology!

    def __get_network_from_network_param_file(self, network_paramfile):
        network_param_file = None
        if network_paramfile is not None:
            network_paramfile = load_param_file_if_path_is_provided(
                network_paramfile)
            scp.load_NMODL_parameters(network_paramfile)
            network_param_file = network_paramfile.network
        return network_param_file

    def __create_synaptic_input_matrix_from_network_param_file(
            self, network_paramfile=None, spatial_bins_df=None):
        '''To be implemented!'''
        self.network_param_file = self.__get_network_from_network_param_file(
            network_paramfile)
        if self.network_param_file is None:
            raise ValueError('network parameter file has not been specified!')
        if spatial_bins_df is not None:
            self.spatial_bins_df = spatial_bins_df
        if self.spatial_bins_df is None:
            raise ValueError('spatial bins df has not been specified!')
        input_activity = np.array(
            [])  # Trials, activity populations, spatial bins, time bins
        # TODO: sample from self.network_param_file
        return input_activity

    def run_new_simulations(self,
                            tStop=60,
                            soma_isi=100,
                            dend_isi=100,
                            input_activity=None):
        # input_activity shape:  #trials, #populations, #spatial bins, #temporal bins
        if input_activity is None:
            input_activity = self.__create_synaptic_input_matrix_from_network_param_file(
            )
        #input_activity = torch.from_numpy(input_activity)
        trials = range(input_activity.shape[0])

        output_soma_vt = []
        output_dend_vt = []
        output_soma_ap = []
        output_dend_ap = []
        soma_isi = torch.ones(trials) * soma_isi
        dend_isi = torch.ones(trials) * dend_isi
        for t in range(tStop):
            synapse_activations = input_activity[:, :, :, t:self.
                                                 temporal_history_window +
                                                 t].flatten()
            synapse_activations = (synapse_activations.view(len(trials),
                                                            -1)).float()

            prediction_soma_vt = self.model_soma_vt.forward(
                [synapse_activations, soma_isi, dend_isi])
            prediction_dend_vt = self.model_dend_vt.forward(
                [synapse_activations, soma_isi, dend_isi])
            # check if its between 0 and 1, otherwise use torch.sigmoid:
            prediction_soma_ap = self.model_soma_ap.forward(
                [synapse_activations, soma_isi, dend_isi])
            prediction_dend_ap = self.model_dend_ap.forward(
                [synapse_activations, soma_isi, dend_isi])

            output_soma_vt.append(prediction_soma_vt)
            output_dend_vt.append(prediction_dend_vt)
            output_soma_ap.append(prediction_soma_ap)
            output_dend_ap.append(prediction_dend_ap)

            soma_aps = prediction_soma_ap < torch.from_numpy(
                np.random.rand(1000))
            dend_aps = prediction_dend_ap < torch.from_numpy(
                np.random.rand(1000))
            soma_isi[soma_aps] = 0
            soma_isi = soma_isi + 1  # check this is what the network saw during learning
            dend_isi[dend_aps] = 0
            dend_isi = dend_isi + 1

        return output_soma_vt, output_dend_vt, output_soma_ap, output_dend_ap