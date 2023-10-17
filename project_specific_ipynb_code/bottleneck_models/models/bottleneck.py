import Interface as I
import torch
from torch import nn
class Model(torch.nn.Module):
    def __init__(self, 
                 n_spatial_bins = None, temporal_window_width = None, n_celltypes = None, n_parameters = None,
                 bottleneck_size = 3, 
                 output_size = 1,     
                 layer_width = 40, 
                 number_of_layers_after_bottleneck = 5,
                 bottleneck_ISI_soma = True,
                 bottleneck_ISI_dend = True,
                 biophysics = True):
        '''Pytorch model class for the "bottleneck" model. It has the following structure:
                     \   synaptic input   /
                       \                /
           "Encoder"     \            /     linear compression with single layer (linear1)
                           \        /       dimensionality: in:  synaptic_input_size, out: bottleneck_size
                             \    /
                                     <-- optionally concatenate additional features(ISI soma, ISI dend)
                             /   \
                           /       \        decompress with bottleneck_layer
                         /           \      dimensionality: in: bottleneck_size + bottleneck_ISI_soma + bottleneck_ISI_dend
                       /               \                    out: layer_width
                       |               |
           "Decoder"   |               |    "number_of_layers_after_bottleneck" layers with width "layer_width"
                       |               |       -> ReLU layers after each layer 
                       |               |
                               |            output layer                    
                       
                           
            synaptic_input_size: dimensionality of the synaptic input. This depends on the morphology for which the 
                 model is trained. If the morphology has e.g. 260 spatial bins and 80ms of synaptic history is 
                 considered for excitatoryx and inhibitory synapses, the dimensionality would be 260*80*2 = 41600
            bottleneck_size: number of features extracted from the synaptic input. If bottleneck size is 2, this means
                the synaptic input vector is linearly compressed into "bottleneck_size" of features.
            output_size: number of features predicted by the model. This can be somatic AP probability, dendritic AP 
                probability, somatic membrane potential, dendritic membrane potential. Note that only the number
                of features is defined here, but not which features it is, as this is determined by the loss, which
                is not part of this model
            layer_width: width of the decoder
            number_of_layers_after_bottleneck: number of layers in the decoder'''
        
        super(Model, self).__init__()
        
        # parameters from the earlier bottleneck model
        self.n_spatial_bins = n_spatial_bins
        self.temporal_window_width = temporal_window_width
        self.n_celltypes = n_celltypes
        self.n_parameters = n_parameters
        self.bottleneck_ISI_soma = bottleneck_ISI_soma
        self.bottleneck_ISI_dend = bottleneck_ISI_dend
        self.biophysics = biophysics
        self.relu = nn.ReLU()
        self.bottleneck_size = bottleneck_size
        self.linear1 = nn.Linear(in_features = n_celltypes*temporal_window_width*n_spatial_bins, out_features = bottleneck_size , bias = False) # bias was true
        
        ###################################
        # bottleneck network
        ###################################
        # first layer after bottleneck
        bottleneck_in_features = bottleneck_size + bottleneck_ISI_soma + bottleneck_ISI_dend + biophysics * n_parameters
        print('linear 1 bottleneck in features', bottleneck_in_features)
        self.bottleneck_layer = nn.Linear(in_features = bottleneck_in_features, out_features = layer_width , bias = True)
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
        # if self.bottleneck_ISI_soma:
        #     num_layers_on_weight_predicting_ANN = 5
        # if self.bottleneck_ISI_dend:
        #     num_layers_on_weight_predicting_ANN = 5
        # if self.bottleneck_ISI_soma and self.bottleneck_ISI_dend:
        #     num_layers_on_weight_predicting_ANN = 5
        # # from biophysical parameters to network width
        # self.input_layer_weights = nn.Linear(in_features = 273, out_features = 200 , bias = True)
        # self.hidden_layers = []
        # # middle layers     
        # for lv in range(num_layers_on_weight_predicting_ANN):
        #     hidden_layers = nn.Linear(in_features = 200, out_features = 200, bias = True)
        #     setattr(self,'hidden_layers_weights_ANN_{}'.format(lv), hidden_layers)                                   
        #     self.hidden_layers.append(hidden_layers)
        # #self.layer_before_last = nn.Linear(in_features = 200, out_features = 1, bias = True)
        # # output layer of weights predicting network
        # self.weights_output_layer_ = nn.Linear(in_features = 200, out_features = synaptic_input_size, bias = True)
                                      
    def forward(self,X_ISI_MCM_list):
        # def forward_biopysics(BIOPHYSICS_DENDRITIC_LOCATION):
        #     '''
        #     network to predict weights from ('biophysics')
        #     we have to change this network !!!!!!!! this is only for soma_vt
        #     '''
        #     out = self.input_layer_weights(BIOPHYSICS_DENDRITIC_LOCATION)
        #     for layer in self.hidden_layers:
        #         out = self.relu(out)
        #         out = layer(out)
        #     weights = self.weights_output_layer_(out)
        #     return weights

        def forward_concatenate(dot_out, ISI_SOMA, ISI_DEND):
            list_ = [dot_out]
            if self.bottleneck_ISI_soma:
                list_ = list_ + [ISI_SOMA]
            if self.bottleneck_ISI_dend:
                list_ = list_ + [ISI_DEND]
            if self.biophysics:
                list_ = list_ + [BIOPHYSICS]
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
        
        # to not to keep gradients when back prop happens !!!!!! SHOULD WE DO IT INSIDE THE closure FUNCTION OR THIS IS FINE ??
        #X.requires_grad_(False)
        #print('X shape ',X.shape)
        
        #predicting the weights
        # weights = forward_biopysics(BIOPHYSICS)
        
        # Synaptic inputs
        #SYN = self.forward_bottleneck(X)
        
        # Batch-wise dot product
        dot_out = self.linear1.forward(X) # (X * weights).sum(dim=1, keepdim=True)
        
        # concatenate ISIs
        bottleneck_values = forward_concatenate(dot_out, ISI_SOMA, ISI_DEND)
        
        # more layers
        out = forward_after_bottleneck(bottleneck_values)
                                      
        # then final output
        return out
    
def show(savepath = None, model = None):
    sorted_index = [0, 61, 1, 32, 91, 230, 10, 48, 79, 33, 62, 2, 92, 104, 11, 22, 40, 63, 76, 231, 
                    34, 234, 64, 12, 56, 71, 3, 49, 20, 23, 45, 88, 6, 27, 41, 80, 93, 16, 68, 77, 
                    101, 65, 67, 105, 13, 72, 38, 35, 74, 235, 4, 57, 89, 94, 52, 232, 24, 46, 69, 
                    7, 42, 98, 28, 81, 8, 50, 21, 102, 66, 73, 84, 17, 36, 106, 14, 5, 233, 75, 58, 
                    236, 53, 39, 78, 43, 70, 82, 47, 25, 99, 51, 29, 103, 90, 95, 9, 37, 85, 18, 59, 
                    237, 54, 15, 44, 83, 26, 100, 96, 30, 19, 86, 60, 55, 97, 31, 87, 224, 109, 110, 
                    118, 225, 112, 111, 119, 221, 113, 226, 219, 127, 114, 120, 222, 213, 227, 220, 
                    133, 128, 115, 116, 214, 121, 223, 228, 129, 134, 122, 138, 117, 215, 229, 211, 
                    216, 130, 135, 139, 123, 136, 212, 217, 218, 147, 107, 108, 124, 125, 126, 131, 
                    132, 137, 140, 141, 142, 143, 144, 145, 146, 148, 149, 150, 151, 152, 153, 177, 
                    178, 154, 190, 179, 155, 167, 180, 159, 191, 187, 156, 168, 184, 181, 160, 192, 
                    203, 165, 188, 193, 157, 169, 199, 185, 207, 161, 183, 194, 182, 204, 170, 196, 
                    174, 189, 162, 158, 166, 209, 208, 163, 200, 186, 195, 171, 197, 210, 205, 175, 
                    201, 202, 172, 164, 173, 176, 198, 206]
    
    n_celltypes = model.n_celltypes
    n_spatial_bins = model.n_spatial_bins 
    temporal_window_width = model.temporal_window_width
    model.bottleneck_size = 1
    # n_spatial_bins = 238 # new dataset
    epoch = '1'
    # visualize the Linear1Model
    weights = model.state_dict()['module.linear1.weight'].data.cpu().detach().numpy()
    # # visualize the Hypernetwork
    # model_new = Model(bottleneck_size = 1, 
    #          output_size = 1,     
    #          layer_width = 40, 
    #          number_of_layers_after_bottleneck = 5,
    #          bottleneck_ISI_soma = True,
    #          bottleneck_ISI_dend = True,
    #          dendritic_location = False)
    # state_dict = model.state_dict()
    # state_dict = {k[7:]:v for k,v in state_dict.items()}
    # model_new.load_state_dict(state_dict)
    # weights = forward_biopysics(model_new,torch.ones(1).view(1,1))[0].cpu().detach().numpy()
    #elif isinstance(model, Model):
    # weights = model.forward_biopysics(PARAMS_DENDRITIC_LOCATION[[0]].to(device))
    #else:
    #    raise TypeError()
    # weights = weights.data.cpu().detach().numpy()
    fig, axes = I.plt.subplots(model.bottleneck_size, 2, 
                           gridspec_kw={'width_ratios': [70, 1]}, 
                           figsize = (6,4*model.bottleneck_size), dpi = 150)
    axes = axes.reshape(model.bottleneck_size, 2)
    for lv in range(model.bottleneck_size):
        #weights1 = weights[:,lv]
        weights1 = weights.reshape(n_celltypes,n_spatial_bins,temporal_window_width)[:,sorted_index,:]
        scaling = max(weights1.max(),-weights1.min())
        weights_for_fig = I.np.concatenate([I.np.transpose(weights1[0]), I.np.transpose(weights1[1])], axis = 0)
        im = axes[lv,0].imshow(weights_for_fig, vmin = -scaling, vmax = scaling, cmap='seismic', interpolation = 'none')
        fig.colorbar(im, cax = axes[lv,1]) 
        title = 'epoch_{}_batch_{}'.format(epoch, 'nan')
        axes[lv,0].set_title(title)
    if savepath:
        fig.savefig(I.os.path.join(savepath, title+'.png'))
    I.plt.show()
    I.plt.close()