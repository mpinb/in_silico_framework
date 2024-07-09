# Coordinated Views — A Grammar-based Approach
## About

Supports the creation of web-based data analytics dashboards consisting of linked views. Key features:
- Integrate different JavaScript visualization libraries (e.g., Vega-Lite, Plotly.js, Babylon.js)
- Thereby enable combination of InfoVis (e.g., scatter plot, parallel coordinates) and 3D views
- Specify layout and interactions with a JSON-based grammar


## Running the application

### 1a. Interactive usage with jupyter notebooks
Setting up the data server is done in 3 steps, which are also outlined in [example/ipynb](./example.ipynb).
To start the data server:
1. Start the server on a port (5000 by default)
2. Set a dataframe (only pandas or vaex are currently supported)
3. Set a session. There are 3 (default session)[./defaults/default_sessions] configured.
Start backend server in jupyter notebook (use Python 3.8 or 3.9 environment of In-Silico-Framework as kernel, see [setup instructions](../../installer/README.md)). 
```
example_vaex.ipynb
```

### 1b. Legacy mode (start server from command line as in paper)
Navigate to this folder, activate Python 3.8 environment of In-Silico-Framework (see [setup instructions](../../installer/README.md)), and start data server from a console.
```
source_3
python server.py ../../getting_started/linked-views-example-data/case_study_1
```
Replace `case_study_1` with `case_study_2` to view the second case study from the paper (excluding membrane potentials).
To inspect the membrane potentials over time on the dendrite [download](https://cloud.zib.de/s/jmF7dejCm92Hpi6) the precomputed simulation data from case study 2 and additionally start the compute server.
```
source_3
python compute_server.py <path-to>/case_study_2/simulation_data
```


### 2. Start web-based frontend
Please refer to the [documentation](frontend/README.md) in the frontend folder.


## Publications
Rapid Prototyping for Coordinated Views of Multi-scale Spatial and Abstract Data: A Grammar-based Approach.
Philipp Harth, Arco Bast, Jakob Troidl, Bjorge Meulemeester, Hanspeter Pfister, Johanna Beyer, Marcel Oberlaender, Hans-Christian Hege, Daniel Baum.
<i>Eurographics Workshop on Visual Computing for Biology and Medicine (VCBM)</i>, 2023.

Ion channel distributions in cortical neurons are optimized for energy-efficient active dendritic computations. Arco Bast, Marcel Oberlaender. <i>bioRxiv</i> 2021.12.11.472235; doi: https://doi.org/10.1101/2021.12.11.472235