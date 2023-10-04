## Structural model of barrel cortex
Scripts to retrieve anatomical features and structural connectivity statistics from barrel cortex model. The model is constructed from a representative set of experimentally reconstructed neuronal morphologies that are duplicated and spatially displaced to create realistic packing densities of neurites within the modeled brain region.

### System requirements 
- 2TB disk space
- 64GB RAM, multiprocessor system (CPU)
- Ubuntu 18.04 (recommended)

Local setup for reference: 64GB RAM, 10 x Intel(R) Xeon(R) W-2155 CPU @ 3.30GHz 

### Python environment
The recommened way for setting up the Python environment using conda is as follows:
```
cd structural_model
conda env create --file env.yml
conda activate structural-model
pip install matplotlib
pip install drawSvg
pip install colour
```
Note that networkx=2.4 is required (contained in env.yml).
### Model data
- Download the model data from [BarreCortexInSilico](https://cortexinsilico.zib.de/download) (model data 2021-v1)
- Extract the zip file and replace model_data.txt in this repo with a symbolic link to the downloaded dataset.
```
cd structural_model
rm model_data.txt
ln -s /path/to/model_data_2021v1 model_data
```
### Running scripts
A valid sequence of calls to the feature computation and evaluation routines can be found the following batch script:
```
cd structural_model
python run.py
```
Note that most of the evaluation routines (eval_*) that generate connectivity statistics depend on structural features to be precomputed (e.g., calc_features_mp.py, calc_DSC_mp.py).