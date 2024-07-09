import chart_studio.plotly as py
import plotly
import plotly.graph_objs as go
import pandas as pd
import numpy as enp
import dendrite_thickness.transformTools as tr
import re
import Interface as I
from getting_started import getting_started_dir


def readPoints(pFile):
    """
    This function will read 3 points as an array from txt files
    only need to provide the path of the file as the input and in return you will
    get the array of points
    """
    points = []
    with open(pFile, 'r') as amLand:
        lines = amLand.readlines()
        for line in lines:
            matches = re.findall('-?\d+\.\d+', line)
            point = list(map(float, matches))
            points.append(point)
    return points


def plotCell(points, clr, sz):
    """
    In this function we use plotly to create 3d shapes of neurons, this is the setup of the coordinates
    and Colors and how to show the lines. One can change for example the height or the width of the produced image.
    parameters: points are the (x,y,z) array points, clr is the color and sz is the size of the graph.

    """

    x = pd.Series([point[0] for point in points])
    y = pd.Series([point[1] for point in points])
    z = pd.Series([point[2] for point in points])

    trace = go.Scatter3d(x=x,
                         y=y,
                         z=z,
                         mode='markers',
                         marker=dict(
                             size=sz,
                             color=clr,
                             colorscale='Viridis',
                         ))

    data = [trace]

    layout = dict(
        width=1200,
        height=1080,
        autosize=True,
        title='Spactial Data point',
        scene=dict(xaxis=dict(gridcolor='rgb(255, 255, 255)',
                              zerolinecolor='rgb(255, 255, 255)',
                              showbackground=True,
                              backgroundcolor='rgb(230, 230,230)'),
                   yaxis=dict(gridcolor='rgb(255, 255, 255)',
                              zerolinecolor='rgb(255, 255, 255)',
                              showbackground=True,
                              backgroundcolor='rgb(230, 230,230)'),
                   zaxis=dict(gridcolor='rgb(255, 255, 255)',
                              zerolinecolor='rgb(255, 255, 255)',
                              showbackground=True,
                              backgroundcolor='rgb(230, 230,230)'),
                   camera=dict(up=dict(x=0, y=0, z=1),
                               eye=dict(
                                   x=-1.7428,
                                   y=1.0707,
                                   z=0.7100,
                               )),
                   aspectratio=dict(x=1, y=1, z=0.7),
                   aspectmode='manual'),
    )

    fig = dict(data=data, layout=layout)
    return fig
