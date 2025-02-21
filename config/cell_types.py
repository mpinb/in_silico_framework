"""Cell type configuration.

This module keeps track of which cell types are used throughout ISF.
This should be set on a per-project basis. Adapting this file usually invalidates previously created
:ref:`syn_file_format` files, :ref:`con_file_format` files, and :ref:`network_param_file_format` files.

These cell types are used to keep track of presynaptic cells in network modeling, and their
associated synapse types.
"""

# - Barrel cortex cell types
EXCITATORY = [
    "L1",       # Layer 1
    "L2",       # Layer 2
    "L34",      # Layer 3/4
    "L4py",     # Layer 4 pyramidal
    "L4sp",     # Layer 4 spiny
    "L4ss",     # Layer 4 spiny stellate
    "L5st",     # Layer 5 slender-tufted
    "L5tt",     # Layer 5 thick-tufted
    "L6cc",     # Layer 6 cortico-cortical
    "L6ccinv",  # Layer 6 cortico-cortical inverted
    "L6ct",     # Layer 6 corticothalamic
    "VPM"       # Ventral posteromedial nucleus (VPM)
    ]
INHIBITORY = ["INH"]

# - Generic cell types
# EXCITATORY = ["EXC"]
# INHIBITORY = ["INH"]