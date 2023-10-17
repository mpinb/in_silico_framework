import torch
from torch import nn

class Model(torch.nn.Module):
    def __init__(self,
                 GLOBAL_n_spatial_bins, GLOBAL_temporal_window_width, GLOBAL_n_parameters,
                 bottleneck_size = 3, 
                 output_size = 1,     
                 layer_width = 40, 
                 number_of_layers_after_bottleneck = 5,
                 bottleneck_ISI_soma = True,
                 bottleneck_ISI_dend = True,
                 dendritic_location = True):
        
        
        super(Model, self).__init__()
        
        # parameters from the earlier bottleneck model
        self.synaptic_input_size = synaptic_input_size = GLOBAL_n_spatial_bins * 2 * GLOBAL_temporal_window_width
        self.bottleneck_ISI_soma = bottleneck_ISI_soma
        self.bottleneck_ISI_dend = bottleneck_ISI_dend
        self.dendritic_location = dendritic_location
        self.relu = nn.ReLU()
        self.bottleneck_size = bottleneck_size
        #self.linear1 = nn.Linear(in_features = synaptic_input_size, out_features = bottleneck_size , bias = False) # bias was true
        
        ###################################
        # bottleneck network
        ###################################
        # first layer after bottleneck
        self.bottleneck_layer = nn.Linear(in_features = bottleneck_size+sum([bottleneck_ISI_soma, bottleneck_ISI_dend]), out_features = layer_width , bias = True)
        # other layers after bottleneck
        self.layers_after_bottleneck = []
        for lv in range(number_of_layers_after_bottleneck):
            layer = nn.Linear(in_features = layer_width, out_features = layer_width, bias = True)
            setattr(self,'layer_asd_{}'.format(lv), layer)                                   
            self.layers_after_bottleneck.append(layer)
        # output_layer
        self.output_layer = nn.Linear(in_features = layer_width, out_features = output_size,bias = True)
        
        
        ###################################
        #  weights predicting network
        ###################################        
        if self.bottleneck_ISI_soma:
            num_layers_on_weight_predicting_ANN = 5
        if self.bottleneck_ISI_dend:
            num_layers_on_weight_predicting_ANN = 5
        if self.bottleneck_ISI_soma and self.bottleneck_ISI_dend:
            num_layers_on_weight_predicting_ANN = 5
        # from biophysical parameters to network width
        if self.dendritic_location:
            self.input_layer_weights = nn.Linear(in_features = GLOBAL_n_spatial_bins + GLOBAL_n_parameters, out_features = 200 , bias = True)
        else:
            self.input_layer_weights = nn.Linear(in_features = GLOBAL_n_parameters, out_features = 200 , bias = True)
        self.hidden_layers = []
        # middle layers     
        for lv in range(num_layers_on_weight_predicting_ANN):
            hidden_layers = nn.Linear(in_features = 200, out_features = 200, bias = True)
            setattr(self,'hidden_layers_weights_ANN_{}'.format(lv), hidden_layers)                                   
            self.hidden_layers.append(hidden_layers)
        #self.layer_before_last = nn.Linear(in_features = 200, out_features = 1, bias = True)
        # output layer of weights predicting network
        self.weights_output_layer_ = nn.Linear(in_features = 200, out_features = synaptic_input_size, bias = True)
                                      
    def forward(self,X_ISI_MCM_list):
        def forward_biopysics(BIOPHYSICS_DENDRITIC_LOCATION):
            '''
            network to predict weights from ('biophysics')
            we have to change this network !!!!!!!! this is only for soma_vt
            '''
            out = self.input_layer_weights(BIOPHYSICS_DENDRITIC_LOCATION)
            for layer in self.hidden_layers:
                out = self.relu(out)
                out = layer(out)
            weights = self.weights_output_layer_(out)
            return weights

        def forward_concatenate(dot_out, ISI_SOMA, ISI_DEND):
            list_ = [dot_out]
            if self.bottleneck_ISI_soma:
                list_ = list_ + [ISI_SOMA]
            if self.bottleneck_ISI_dend:
                list_ = list_ + [ISI_DEND]
            dot_out = torch.cat(list_, axis = 1)
            bottleneck_values = self.bottleneck_layer(dot_out)
            return bottleneck_values

        def forward_after_bottleneck(bottleneck_values):
            final_out = bottleneck_values
            for layer in self.layers_after_bottleneck:
                final_out = self.relu(final_out)
                final_out = layer(final_out)
            final_out = self.output_layer(final_out)
            return final_out
        
        X,ISI_SOMA,ISI_DEND,BIOPHYSICS, DENDRITIC_LOCATION = X_ISI_MCM_list
        
        if self.dendritic_location:
            BIOPHYSICS_DENDRITIC_LOCATION = torch.cat([BIOPHYSICS, DENDRITIC_LOCATION], axis = 1)
        else:
            BIOPHYSICS_DENDRITIC_LOCATION = BIOPHYSICS
        # to not to keep gradients when back prop happens !!!!!! SHOULD WE DO IT INSIDE THE closure FUNCTION OR THIS IS FINE ??
        #X.requires_grad_(False)
        #print('X shape ',X.shape)
        
        
        #predicting the weights
        weights = forward_biopysics(BIOPHYSICS)
        
        # Synaptic inputs
        #SYN = self.forward_bottleneck(X)
        
        # Batch-wise dot product
        dot_out = (X * weights).sum(dim=1, keepdim=True)
        
        # concatenate ISIs
        bottleneck_values = forward_concatenate(dot_out, ISI_SOMA, ISI_DEND)
        
        # more layers
        out = forward_after_bottleneck(bottleneck_values)
                                      
        # then final output
        return out