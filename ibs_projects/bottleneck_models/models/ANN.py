import torch
from torch import nn


import torch
from torch import nn

class Model(torch.nn.Module):
    def __init__(self,
                 n_spatial_bins = None, 
                 temporal_window_width = None, 
                 n_celltypes = None, 
                 n_parameters = None,
                 bottleneck_size = 3, 
                 output_size = 1,     
                 layer_width = 40, 
                 number_of_layers_after_bottleneck = 5,
                 bottleneck_ISI_soma = True,
                 bottleneck_ISI_dend = True,
                 biophysics = True,
                 dendritic_location = True,
                 total_variation_spatial = 0.,
                 total_variation_temporal = 0.,
                 L2_hypernetwork = 0.,
                 neighbors_0 = None,
                 neighbors_1 = None):
        
        
        super(Model, self).__init__()
        # assert total_variation_temporal == 0.
        # assert total_variation_spatial == 0.
        # assert L2_hypernetwork == 0.
        
        # parameters from the earlier bottleneck model
        self.n_spatial_bins = n_spatial_bins
        self.temporal_window_width = temporal_window_width
        self.n_celltypes = n_celltypes
        self.n_parameters = n_parameters
        self.synaptic_input_size =  synaptic_input_size =  n_spatial_bins * n_celltypes * temporal_window_width
        self.bottleneck_ISI_soma = bottleneck_ISI_soma
        self.bottleneck_ISI_dend = bottleneck_ISI_dend
        self.neighbors_0 = neighbors_0
        self.neighbors_1 = neighbors_1
        self.L2_hypernetwork = L2_hypernetwork
        self.dendritic_location = dendritic_location
        self.relu = nn.ReLU()
        self.bottleneck_size = bottleneck_size
        self.total_variation_spatial = total_variation_spatial
        self.total_variation_temporal = total_variation_temporal
        self.biophysics = biophysics
        if biophysics:
            self.in_feature_size = synaptic_input_size + bottleneck_ISI_soma + bottleneck_ISI_dend + n_parameters
        else:
            self.in_feature_size = synaptic_input_size + bottleneck_ISI_soma + bottleneck_ISI_dend
            
        self.linear1 = nn.Linear(in_features = self.in_feature_size, out_features = layer_width , bias = False) # bias was true
        
        ###################################
        # bottleneck network
        ###################################
        
        # other layers after bottleneck
        self.layers_after_bottleneck = []
        for lv in range(number_of_layers_after_bottleneck):
            layer = nn.Linear(in_features = layer_width, out_features = layer_width, bias = True)
            setattr(self,'layer_asd_{}'.format(lv), layer)                                   
            self.layers_after_bottleneck.append(layer)
        # output_layer
        self.output_layer = nn.Linear(in_features = layer_width, out_features = output_size,bias = True)
        
                                      
    def forward(self,X_ISI_MCM_list):
        X,ISI_SOMA,ISI_DEND,BIOPHYSICS, DENDRITIC_LOCATION = X_ISI_MCM_list
        
        list_ = [X]
        if self.bottleneck_ISI_soma:
            list_ = list_ + [ISI_SOMA]
        if self.bottleneck_ISI_dend:
            list_ = list_ + [ISI_DEND]
        if self.biophysics and self.n_parameters:
            list_ = list_ + [BIOPHYSICS]
        
        out = torch.cat(list_, axis = 1)
        out = self.linear1(out)
        for layer in self.layers_after_bottleneck:
            out = self.relu(out)
            out = layer(out)
        out = self.output_layer(out)
        
        extra_loss = 0
                                    
        return out, extra_loss
        
def show(savepath = None, model = None, model_kwargs = None, params = 0, title = None):
    pass
