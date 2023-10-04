"""
Exemplary call of the network realization script. 

Here, 'network_realization' is directly imported as a module.
Environment: Python3, dependencies as in 'in-silico.yml'. Install it
with conda like so:

conda env create -f in-silico.yml

The tutorial data required below can be downloaded here:

https://cloud.zib.de/index.php/s/S8ZetomaTnZrofJ

To use the script from a Python2 environment: A pragmatic way could be to wrap the
code below in a main method (with modelDataFolder, etc. as parameters) and to call
it from the Python2 environment via system call: os.system(python3 ...).
"""

import network_realization as nwr
import multiprocessing as mp

#modelDataFolder = "/local/network_embedding_data_2020-07-14"
modelDataFolder = "/vis/scratchN/bzfharth/network_embedding_data_2020-11-20"
preIdsFile_vS1 = "/vis/scratchN/bzfharth/network_embedding_data_2020-11-20/pre_IDs_vS1.txt"
postIdsFile_L5PT = "/vis/scratchN/bzfharth/network_embedding_data_2020-11-20/post_IDs_L5PT_all.txt"

#preIdsFile_test = "/local/bzfharth/BarrelField3D/data/boundary_2020-12-08/preIdsTest.txt"
#postIdsFile_test = "/local/bzfharth/BarrelField3D/data/boundary_2020-12-08/postIds2.txt"

# Within this folder, the actual output folder named realization_YYYY-MM-DD is created.
outputBaseFolder = "/vis/scratchN/bzfharth"

#nwr.create_realization(modelDataFolder, preIdsFile_vS1, postIdsFile_C2_L5PT, outputBaseFolder, randomSeed = 3000, poolSize = 5)
nwr.create_realization(modelDataFolder, preIdsFile_vS1, postIdsFile_L5PT, outputBaseFolder, randomSeed = 3000, poolSize = 10)



