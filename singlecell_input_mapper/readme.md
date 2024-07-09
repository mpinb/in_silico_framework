# SingleCellInputMapper

Tool for estimating connectivity (inputs) of individual neuron morphologies registered into standard barrel cortex model.
Based on methods and data presented in [Egger, Dercksen et al., Frontiers Neuroanatomy 2014](https://www.frontiersin.org/articles/10.3389/fnana.2014.00129/full#F2)

Inputs:
- single neuron morphology
- 3D Post-Synaptic Target site (PST) densities for normalization of innervation calculations
- number of cells per cell type spreadsheets
- connections spreadsheet containing PST length/area constants
- presynaptic bouton densities of individual axon morphologies
  sorted by presynaptic column and cell type

Outputs:
- summary file containing information about number and presynaptic type
  and column of anatomical synapses
- AmiraMesh landmark file containing 3D synapse locations of anatomical
  synapses of each presynaptic type and column
- Synapse location and connectivity file compatible with NeuroSim

Authors: Robert Egger, Arco Bast
