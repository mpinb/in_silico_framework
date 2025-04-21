from model_data_base import ModelDataBase
import Interface as I
from bokeh.io import push_notebook, show, output_notebook
from bokeh.layouts import row, gridplot
from bokeh.plotting import figure, show, output_file

output_notebook()
TOOLS = "pan,wheel_zoom,box_zoom,reset,save,box_select"
mdb = ModelDataBase('/gpfs/soma_fs/scratch/meulemeester/results/bottleneck')
df = mdb["4d-data"]
x, y, z = df[["soma_isi", "dend_isi", "bottleneck_node"]].values.T
p = figure(tools=TOOLS)
p.scatter(x, y, z, fill_color=df["model_output"].values)
show(p)