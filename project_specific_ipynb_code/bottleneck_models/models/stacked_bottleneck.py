import Interface as I
import torch
import torch.nn as nn
import torch.nn.functional as F
device = "cuda" if torch.cuda.is_available() else "cpu"
from tqdm import tqdm
from sklearn.metrics import roc_auc_score
from scipy.stats import pearsonr
import time 
from torch.utils.data import Dataset, DataLoader
import random, string 

class Model(nn.Module):
    def __init__(self, 
                 synaptic_input_size,
                 bottleneck_size = 5, 
                 output_size = 1,
                 layer_width = 40, 
                 number_of_layers_after_bottleneck = 5,
                 bottleneck_ISI_soma = True,
                 bottleneck_ISI_dend = True):
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
        self.bottleneck_ISI_soma = bottleneck_ISI_soma
        self.bottleneck_ISI_dend = bottleneck_ISI_dend
        self.relu = nn.ReLU()
        # first layer: compresses synaptic input to low number of features ("bottleneck")
        # synaptic_input_size: typical dimensionality: 40000
        # bottleneck_size: typical dimensionaility: 1-2
        self.linear1 = nn.Linear(in_features = synaptic_input_size, out_features = bottleneck_size , bias = False) # bias was true
        # expand bottleneck output, concatenated with ISI_soma and ISI_dend
        self.bottleneck_layer = nn.Linear(in_features = bottleneck_size+sum([bottleneck_ISI_soma, bottleneck_ISI_dend]), out_features = layer_width , bias = True)
        # subsequent layers, typicall dimensionality: 5 layers, widht 40
        self.layers_after_bottleneck = []
        for lv in range(number_of_layers_after_bottleneck):
            layer = nn.Linear(in_features = layer_width, out_features = layer_width, bias = True)
            setattr(self,'layer_asd_{}'.format(lv), layer)                                   
            self.layers_after_bottleneck.append(layer)
        # output layer, dimensionality 1-4, depending on amount of targets predicted by the network
        # (can be: somatic AP probability, somatic membrane potential, dendritic AP probability, dendrtic membrane potential)
        self.output_layer = nn.Linear(in_features = layer_width, out_features = output_size, bias = True)

    def forward(self, X_ISI_MCM_list):
        '''
        X_ISI_list: a list containing two elements.
           First element is X, i.e. the same as in My_model_bottleneck
           Second element is ISI for each trial
        '''
        X,ISI_SOMA,ISI_DEND = X_ISI_MCM_list
        assert(isinstance(X,torch.Tensor))
        out = self.linear1(X)
        list_ = [out]
        if self.bottleneck_ISI_soma:
            list_ = list_ + [ISI_SOMA]
        if self.bottleneck_ISI_dend:
            list_ = list_ + [ISI_DEND]            
        out = torch.cat(list_, axis = 1)
        out = self.bottleneck_layer(out)
        for layer in self.layers_after_bottleneck:
            out = self.relu(out)
            out = layer(out)
        out = self.output_layer(out)
        return out
    
class StackedModel(nn.Module):
    def __init__(self, models):
        super(StackedModel, self).__init__()        
        self.models = nn.ModuleList(models)
        
    def forward(self, X_ISI_MCM_list):
        X,ISI_SOMA,ISI_DEND = X_ISI_MCM_list
        outputs = []
        for model in self.models:
            out = model.forward(X_ISI_MCM_list)
            outputs.append(out)
        return outputs
    
class CustomDataset(Dataset):
    def __init__(self, numpy_store_object, device = 'cpu'):
        self.nps = numpy_store_object
        self.device = device
        self.names = ['VT', 'SA', 'ISI_SOMA', 'ISI_DEND', 'AP_SOMA', 'AP_DEND']
        self.arrays = [torch.from_numpy(numpy_store_object.load(name)[1]) for name in self.names]

    def __getitem__(self, index):
        samples = [x[index].float().to(self.device) for x in self.arrays]
        return samples

    def __len__(self):
        return len(self.arrays[0])
    
class TrainParams:
    def __init__(self,**kwargs):
        for key, value in kwargs.items():
                    setattr(self, key, value)      
    
# computes the loss for specified targets("desired_outputs")
def get_loss(losses, model_out, desired_outputs):
    j = 0
    output_losses = []    
    for loss, desired_output in zip(losses, desired_outputs):
        if loss is None:
            continue
        current_output = model_out[:,[j]]
        j = j + 1
        current_loss = loss(current_output, desired_output)
        output_losses.append(current_loss)
    # at max for losses for 4 distinct targets (somatic AP, somatic voltage, dendritic AP, dendritic voltage)
    loss = sum(output_losses)
    # regularization
    ## total variation loss
    return loss
    
class Trainer:
    def __init__(self, model, optimizer, device, savedir=None):
        self.model = model
        self.optimizer = optimizer
        self.device = device
        self.savedir = savedir
        self.batch = 0
        self.epoch = 0
        self.mode = 'train'
        self.loss = None
        self.ind = None
        self.weights_collection = []
        self.loss_collection = []    
        
    def clear_tracking():
        self.model_out_tracking = []
        self.desired_outputs_tracking = []        
        
def get_descriptor(self):
    descriptor = 'loss_' + '_'.join([ln for ln,l in zip(loss_names, losses) if l])
    descriptor += '__bn_{}'.format(bottleneck_size)
    descriptor += '__ISI' 
    if bottleneck_ISI_soma:
        descriptor += 's'
    if bottleneck_ISI_dend:
        descriptor += 'd'
    descriptor += '__width_min_max_{}_{}_{}'.format(temporal_window_width, t_rolling_window_min, t_rolling_window_max)    
    descriptor += '__decoder_{}x{}'.format(number_of_layers_after_bottleneck,layer_width) 
    descriptor += '__L2_{}_L1_{}_TV_{}'.format(l2_lambda,l1_lambda,total_variation_weight) 
    descriptor += '__epochs_{}__batches_{}'.format(n_epochs,n_batches) 
    descriptor += '__ntrials_{}'.format(n_trials) 
    descriptor += '__traintest_{}_{}'.format(len(ind_train),len(ind_test)) 
    descriptor += '__' + ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(5))
    return descriptor

def clear_tracking():
    global model_out_tracking, desired_outputs_tracking
    model_out_tracking = []
    desired_outputs_tracking = []

# evaluate model on current batch and return loss
# note: the model is applied in a convolutionary fashion on the data by slicing 
#       along the last axis, gradients are accumulated for all time points
# current problem: this slicing is not zero-copy
def closure(tracking = False):
    print('entering closure')
    #t0 = time.time()
    optimizer.zero_grad() 
    l = []
    # temporal convolution
    #t00 = time.time()
    losses_list = []    
    for i in range(t_rolling_window_min, t_rolling_window_max):
        #t000 = time.time()
        X_ISI_MCM_list = [SA[:,:,:,i:temporal_window_width+i].flatten().view(len(ind),-1),
                          ISI_SOMA[:,[temporal_window_width+i]].view(len(ind),-1),
                          ISI_DEND[:,[temporal_window_width+i]].view(len(ind),-1)]
        desired_outputs = [None, # currently not needed, AP_SOMA[:,[temporal_window_width+i]].view(len(ind),-1),
                           None, # not needed anymore VT[:,0,[temporal_window_width + i]].view(len(ind),-1), # VT_SOMA[:,[temporal_window_width+i]].view(len(ind),-1),
                           None, # not needed currently AP_DEND[:,[temporal_window_width+i]].view(len(ind),-1),
                           None] # VT_DEND[:,[temporal_window_width+i]].view(len(ind),-1)] 
        #t0000 = time.time()                    
        outputs = stacked_model.forward(X_ISI_MCM_list)
        #times['temporal_convolution_forward'] += time.time() - t0000 
        for lv, output in enumerate(outputs):
            desired_outputs[-1] = VT[:,lv,[temporal_window_width + i]].view(len(ind),-1)            
            loss = get_loss(losses, output, desired_outputs)
            losses_list.append(loss)
    #t0000 = time.time()                            
    sum(losses_list).backward()
    #times['temporal_convolution_backward'] += time.time() - t0000                                       
                
    #times['temporal_convolution'] += time.time() - t00    
    #regularization
    if mode == 'train':
        print('regularization')
        if total_variation_weight:
            for model in models:
                TVL = torch.pow(model.linear1.weight.view(bottleneck_size, 
                                                      n_celltypes, 
                                                      n_spatial_bins, 
                                                      temporal_window_width).diff(axis = -1),2).sum()
                loss = total_variation_weight*TVL
                loss.backward()
        if l1_lambda:
            raise NotImplementedError()
        if adjacent_models_TV:
            for a,b in all_neighbors:     
                loss = torch.pow(flat_parameters[a]-flat_parameters[b],2).sum() * adjacent_models_TV                    
                loss.backward()
    #if tracking:
    #    model_out_tracking.append(model_out.cpu().detach().numpy())
    #    desired_outputs_tracking.append([d.cpu().detach().numpy() for d in desired_outputs])
    print('leaving closure')
    #times['in_closure'] += time.time() - t0
    #times['outside_closure'] = time.time() - times['outside_closure']
    #counter.append(0)
    #if len(counter) == 5:
    #raise
    return loss

# track and compute metrics of accuracy during training  
def log(detailed_log = False, print_ = False):
    weights_collection.append(model.linear1.weight.data.cpu().detach().numpy())
    loss_collection.append((mode+'_loss', epoch, batch, float(loss.cpu().detach().numpy())))
    if print_:
        print(loss_collection[-1])
    if detailed_log:
        model_out = I.np.concatenate(model_out_tracking)
        desired_outputs = I.np.concatenate(desired_outputs_tracking, axis = 1)
        i = 0
        for lv,(l,n,e) in enumerate(zip(losses, loss_names, evaluations)):
            if not l:
                continue
            if e == 'AUROC': # for sonmatic and dendritic acition potential prediction (binary)
                AUC = roc_auc_score(desired_outputs[lv].flatten(), model_out[:,i].flatten())
                loss_collection.append((mode + '_' + n + '_' + e, epoch, batch, AUC))
            elif e == 'pearson': # for sonmatic and dendritic membrane potential prediction (continous)
                r = pearsonr(desired_outputs[lv].flatten(), model_out[:,i].flatten())[0]
                loss_collection.append((mode + '_' + n + '_' + e, epoch, batch, r))
            if print_:
                print(loss_collection[-1])
            i = i+1

# makes figures of the weights of linear layer 1            
def show(model, savepath = None):
    weights = model.linear1.weight.data.cpu().detach().numpy()
    fig, axes = I.plt.subplots(bottleneck_size, 2, 
                           gridspec_kw={'width_ratios': [70, 1]}, 
                           figsize = (6,4*bottleneck_size), dpi = 150)
    axes = axes.reshape(bottleneck_size, 2)
    for lv in range(bottleneck_size):
        weights1 = weights[lv,:]
        weights1 = weights1.reshape(n_celltypes,n_spatial_bins,temporal_window_width)[:,sorted_index,:]
        scaling = max(weights1.max(),-weights1.min())
        weights_for_fig = I.np.concatenate([I.np.transpose(weights1[0]), I.np.transpose(weights1[1])], axis = 0)
        im = axes[lv,0].imshow(weights_for_fig, vmin = -scaling, vmax = scaling, cmap='seismic', interpolation = 'none')
        fig.colorbar(im, cax = axes[lv,1]) 
        title = 'epoch_{}_batch_{}'.format(epoch,batch)
        axes[lv,0].set_title(title)
    if savepath:
        fig.savefig(I.os.path.join(savepath, title+'.png'))
    I.plt.show()
    I.plt.close()

# depending on the global variable ind, which is the list of indices that constitute the current batch:
# send this data to the gpu
def set_data():
    global ind, VT, SA, ISI_SOMA, ISI_DEND, AP_SOMA, AP_DEND
    # get the cached full dataset in CPU memory
    VT, SA, ISI_SOMA, ISI_DEND, AP_SOMA, AP_DEND = load_data()  
    # put the selected fraction of the dataset (selected by the global variable ind, defining the current chunk of data we want to train on)
    # on the GPU
    VT = VT[ind,:,445-80:445+60].float().to(device)
    SA = SA[ind,:,:,445-80:445+60].float().to(device)
    ISI_SOMA = ISI_SOMA[ind,445-80:445+60].float().to(device).view(len(ind),-1)
    ISI_DEND = ISI_DEND[ind,445-80:445+60].float().to(device).view(len(ind),-1)
    AP_SOMA = AP_SOMA[ind,445-80:445+60].float().to(device).view(len(ind),-1)
    AP_DEND = AP_DEND[ind,445-80:445+60].float().to(device).view(len(ind),-1)

# save the model    
def save():
    if savedir is not None:
        with open(savedir.join('model__epoch_{}__batch_{}'.format(epoch, batch)),'wb') as f:
            I.cloudpickle.dump(model, f)
        with open(savedir.join('loss'), 'wb') as f:
            I.cloudpickle.dump(loss_collection, f)

# training loop             

def train():
    print('I save to', savedir)
    global batch, epoch, mode, loss, ind
    batch = epoch = 0
    save() # save freshly initialized model
    show(models[0], savedir) # save weights
    show(models[1], savedir) # save weights    
    show(models[bifur_index], savedir) # save weights        
    for epoch in range(n_epochs):
        t0 = time.time()       
        # learning rate scheduler
        if epoch < n_epochs/3:
            learning_rate = 0.01
        elif epoch < 2*n_epochs/3:
            learning_rate = 0.001
        else:
            learning_rate = 0.0001
        for g in optimizer.param_groups:
            g['lr'] = learning_rate
        # shuffle ind_train once per epoch to train on "new" i.e. randomly selected batches
        I.np.random.shuffle(ind_train)
        mode = 'train'
        clear_tracking()
        for batch, ind in enumerate(I.utils.chunkIt(ind_train, n_batches)): # set global variable ind
            t00 = time.time()
            set_data() # put data specified in ind onto the GPU
            #times['set_data'] += time.time() - t00
            optimizer.zero_grad() # reset gradients in the model
            loss = closure(tracking=True) # get loss (if mode==train: accumulate gradients)
            t00 = time.time()            
            optimizer.step() # optimize model
            #times['optimizer_step'] += time.time() - t00            
            show(models[0], savedir) # save weights
            show(models[1], savedir) # save weights    
            show(models[bifur_index], savedir) # save weights  
            print('step')
            log() # log progress
            
        # log(detailed_log=True, print_ = True) # performed a detailed evaluation of model performance 
        # clear_tracking() # delete all data from memory required for detailed evaluation         
        mode = 'test'
        with torch.no_grad():
            ind = ind_test # set ind to the test dataset
            set_data() # move test dataset to gpu
            loss = closure(tracking=True) # compute loss
            log(detailed_log=True, print_ = True)
        #show(savedir)
        save() # save model
        print('epoch {} of {} took {}s. n_batches: {}'.format(epoch, n_epochs, time.time()-t0, n_batches))