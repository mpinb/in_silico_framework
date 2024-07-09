# The Visualizer module
This readme provides some info on how to use the visualizer module. This module currently consists of:
- [cell morphology visualizer methods](./cell_morphology_visualizer.py), to plot the shape of a neuron, overlayed with its activity. This can be done as a videa, interactively, exporting it as .vtk frames...
- [activity analysis methods](./activity_analysis/), to plot cellular activity, PSTHs ... This module should be well integrated with the [DataBase](../data_base/) for easy parallellisation.
- [helper methods](./helper_methods.py) for general methods to write out a video or gif from frames using ffmpeg, or plot out an animation from frames.

JupyterLab 2.x (which is what isf uses) does not allow to render arbitrary Javascript code. I'm not sure yet what works and what doesn't, but ipywidgets.VBox is not working atm, which is what the method `plot_interactive_3d()` is using. It does work, however, on VSCode. Either JupyterLab must be updated to 3.x, or I need to do a deepdive on which versions I need for:
- @jupyter-widgets/jupyterlab-manager@x.x.x (1.0.0 should work with JupyterLab 2.x which is what we're running)
- Plotly

In either case, when using Jupyterlab 2.x, one must install nodejs `source_3; conda install -c conda-forge nodejs` and then jupyterlab manager `source_3; jupyter labextension @jupyter-widgets/jupyterlab-manager@x.x.x` in order to make interactive widgets work. This should not be necessary on JupyterLab 3.x, and is not necessary on VSCode, which renders javascript without too much hassle (tested).


## Usage of CellMorphologyVisualizer
```python
from Interface import CellMorphologyVisualizer
# make a visualisation to Cell object
t_end = 100
cell = Interface.simrun_simtrail_to_cell_object(db,sim, tStop=t_end)

# create a single cell visualizer object from the cell
cv = visualize.CellMorphologyVisualizer(cell)

# Show a quick plot of the cell
cv.show_cell_2d()
        
# Show a plot with the membrane voltage
cv.show_voltage_cell_2d()

# make an interactive visualisation (may take some time to load)
cv.plot_interactive_3d(downsample_time=1)

# write out to .vtk frames for analysis in e.g. ParaView
cv.write_vtk_frames(out_name="cell", out_dir=".")
```

# TODO:
- Refractor all visualisation methods to this module

---
Last updated on 23/01/2023