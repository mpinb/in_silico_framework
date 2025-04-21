import Interface as I
import torch
from torch import nn
import torch.nn.functional as F
import torch.nn.utils.prune as prune


def get_cell_info(cellID, cis_realisation):
    neurons_df = I.pd.read_csv(cis_realisation + 'neurons.csv')
    celltypes_df = I.pd.read_csv(cis_realisation + 'cell_types.csv')

    cellID = int(cellID)
    celltype_id = neurons_df.loc[cellID, 'cell_type']
    celltype = celltypes_df.loc[celltype_id, 'id']

    x = neurons_df.loc[cellID, 'soma_x']
    y = neurons_df.loc[cellID, 'soma_y']
    z = neurons_df.loc[cellID, 'soma_z']

    return celltype, (x, y, z)


##########################
# SET UP A TORCH NETWORK #
##########################
def get_input_mask(rnn_nodes,
                   cis_realisation,
                   input_celltype,
                   input_node_assignments,
                   input_len=28):
    '''This function determines which nodes should receive which input connections. Should be applied as a pruning mask to the weight_ih_l0 parameter of the rnn layer.
        rnn_nodes: list of cell identifiers
        input_celltype: str, e.g. 'VPM' or 'VPM_C2'
        input_node_assignments: nested list of len input_len, where each list contains cell identifiers for all input cells that should be mapped to the corresponding input pixel
        input_len: int, optional (default = 28, for MNIST dataset), determines size of mask'''

    def has_input(con, input_celltype):
        pre_celltypes = con[0].keys()  # input_celltype has format 'VPM_C2'
        if input_celltype in pre_celltypes:
            return True
        pre_celltypes_split = [c.split('_')[0] for c in pre_celltypes
                              ]  # input_celltype has format 'VPM'
        if input_celltype in pre_celltypes_split:
            return True
        else:
            return False

    cells_with_direct_input = I.defaultdict(list)
    for cell in rnn_nodes:
        con = I.scp.reader.read_functional_realization_map(
            I.os.path.join(cis_realisation, 'post_neurons', cell,
                           cell + '.con'))
        if has_input(con, input_celltype):
            input_origins = [
                k for k in con[0].keys() if input_celltype in k
            ]  # works for both input_celltype 'VPM' and 'VPM_C2'
            inputs = [con[0][i] for i in input_origins]
            flat_inputs = [item for sublist in inputs for item in sublist]
            cells_with_direct_input[cell].extend(flat_inputs)

    input_mask = {}
    for cell in rnn_nodes:
        try:
            presyns = [v[1] for v in cells_with_direct_input[str(cell)]
                      ]  # cell IDs of presynaptic input cells
        except KeyError:  # this cell doesn't receive input from the target population
            input_mask[cell] = [0] * input_len
            continue

        pixels_in = []  # map to pixel index
        for pre in presyns:
            for n, v in enumerate(input_node_assignments):
                if pre in v:
                    pixels_in.append(n)
        input_mask[cell] = [
            1 if i in pixels_in else 0 for i in range(input_len)
        ]

    return input_mask


def get_connection_matrix_from_realisation(cis_realisation):
    post_cells_dir = I.os.path.join(cis_realisation, 'post_neurons')
    post_cells = I.os.listdir(post_cells_dir)

    @I.dask.delayed
    def write_con_matrix_row(post_cell):
        con_df = I.pd.DataFrame(columns=[post_cell], index=post_cells)
        con = I.scp.reader.read_functional_realization_map(
            I.os.path.join(post_cells_dir, post_cell, post_cell + '.con'))

        # get list of all unique presynaptic cells
        pre_cells = []
        for celltype in con[0].keys():
            l = con[0][celltype]
            pre_cells.extend(I.utils.unique([c[1] for c in l]))

        row = [1 if int(cell) in pre_cells else 0 for cell in post_cells]
        con_df[post_cell] = row

        return con_df.T

    ds = []
    for cell in post_cells:
        ds.append(write_con_matrix_row(cell))

    client = I.distributed.Client('localhost:38786')

    fs = client.compute(ds)
    out = client.gather(fs)
    out_df = I.pd.concat(out)
    return out_df


def make_cis_ann_binary(cis_realisation,
                        device,
                        con=None,
                        input_mask=None,
                        weight_min=0,
                        weight_max=1,
                        input_size=28,
                        input_celltype=None,
                        L5PTs=None,
                        inhs=None,
                        num_classes=10,
                        rand_seed=42):
    '''Fully sets up a torch RNN based on a cortex in silico realization folder, where cells that are not connected in CIS have unconnected nodes in the RNN. Other weights are initialised randomly, with inhibitory connections receiving negative weights and excitatory connections receiving positive weights.
        cis_realisation: str, filepath to cortex in silico folder ending in realization_YYYY-MM-DD/
        con: pandas dataframe, optional, shape cells x cells, containing 1 if cells are connected and 0 if not. Skips generating connection matrix if you already have one, as this takes some time.
        input_mask: torch tensor, optional (will be generated if not supplied, it just takes a long time)
        weight_min, weight_max: float, optional (default min 0, max 1). Initial weights will be sampled with a uniform distribution between weight_min and weight_max. Weights for inhibitory connections will be uniformly sampled between -weight_max and -weight_min.
        input_size: int, optional (default 28 for MNIST dataset)
        input_celltype: str, e.g. 'VPM' or 'VPM_C2'
        num_classes: int, optional (default 10 for MNIST dataset)
        rand_seed: int, optional (default 42), ensures reproducibility.'''
    ## get information about anatomical connectivity from cortex in silico realisation
    assert input_celltype is not None
    if con is None:
        print('generating connection matrix...')
        con = get_connection_matrix_from_realisation(cis_realisation)

    rnn_nodes = list(con.index)
    if L5PTs is None:
        print('reading cell types...')
        L5PTs = [
            n for n, c in enumerate(rnn_nodes)
            if get_cell_info(c, cis_realisation)[0] == 'L5tt'
        ]  # output layer
        inhs = [
            n for n, c in enumerate(rnn_nodes)
            if get_cell_info(c, cis_realisation)[0] in I.inhibitory
        ]  # identify inhibitory cells

    ## set up a basic torch RNN with a fully connected output layer
    torch.manual_seed(rand_seed)

    class RNN(nn.Module):

        def __init__(self, input_size, hidden_size, num_layers, num_classes):
            super(RNN, self).__init__()  # initialise the nn.Module
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            self.rnn = nn.RNN(input_size,
                              hidden_size,
                              num_layers,
                              nonlinearity='relu',
                              batch_first=True)
            self.fc = nn.Linear(len(L5PTs), num_classes)

        def forward(self, x):
            # set initial hidden state
            h0 = torch.zeros(self.num_layers, x.size(0),
                             self.hidden_size).float().to(device)
            # forward run model
            output, hidden = self.rnn(
                x, h0)  # output shape (batch_size, seq_length, hidden_size)

            # reshape the output so it fits into the fully connected layer (get the last output from the L5PTs)
            output = output[:, -1, L5PTs]  # shape (sample, timestep, node)
            # pass it to the linear layer
            output = self.fc(output)

            return output

    print('setting up torch network...')
    model = RNN(input_size, len(rnn_nodes), 1, num_classes)
    print(model)
    print('modifying hidden layer...')
    ## apply the anatomical information to the torch network
    rnn_layer = model.rnn
    rnn_layer.weight_hh_l0 = torch.nn.init.uniform_(
        rnn_layer.weight_hh_l0, a=weight_min,
        b=weight_max)  # randomly initialise weights
    with torch.no_grad():
        rnn_layer.weight_hh_l0[:,
                               inhs] *= -1  # make connections from inhibitory celltypes negative

    for cell in range(
            len(con.index)
    ):  # allow self-self connections, which reflects persistent cell state
        con.iloc[cell, cell] = 1

    mask = torch.tensor(con.to_numpy())
    prune.custom_from_mask(
        rnn_layer, 'weight_hh_l0',
        mask)  # remove connections not present in the anatomical model
    print('modifying input layer...')
    if input_mask is None:
        input_mask = get_input_mask(
            rnn_nodes,
            cis_realisation,
            input_celltype,
            input_node_assignments,
            input_len=input_size)  # give each cell appropriate input
        input_mask_list = []
        for n in rnn_nodes:
            input_mask_list.append(input_mask[n])
        input_mask_tensor = torch.tensor(input_mask_list)
    else:
        input_mask_tensor = input_mask
    prune.custom_from_mask(rnn_layer, 'weight_ih_l0', input_mask_tensor)

    return model


def make_dummy_ann(input_size=28,
                   L5PTs=None,
                   num_classes=10,
                   rnn_nodes=None,
                   device=None):
    '''Sets up a torch RNN as a foundation for loading an existing trained model's parameters into.
        input_size: int, optional (default 28 for MNIST dataset)
        num_classes: int, optional (default 10 for MNIST dataset)'''

    ## set up a basic torch RNN with a fully connected output layer
    class RNN(nn.Module):

        def __init__(self, input_size, hidden_size, num_layers, num_classes):
            super(RNN, self).__init__()  # initialise the nn.Module
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            self.rnn = nn.RNN(input_size,
                              hidden_size,
                              num_layers,
                              nonlinearity='relu',
                              batch_first=True)
            self.fc = nn.Linear(len(L5PTs), num_classes)

        def forward(self, x):
            # set initial hidden state
            h0 = torch.zeros(self.num_layers, x.size(0),
                             self.hidden_size).float().to(device)
            # forward run model
            output, hidden = self.rnn(
                x, h0)  # output shape (batch_size, seq_length, hidden_size)

            # reshape the output so it fits into the fully connected layer (get the last output from the L5PTs)
            output = output[:, -1, L5PTs]  # shape (sample, timestep, node)
            # pass it to the linear layer
            output = self.fc(output)

            return output

    print('setting up torch network...')
    model = RNN(input_size, len(rnn_nodes), 1, num_classes)
    print(model)

    return model