# By running the below code we can extract the radii from a
# bunch of am files which they are in a folder. by providing their folder path
# and their corresponding tif image folder path
import os
import sys

nb_dir = os.path.split(os.getcwd())[0]
if (nb_dir not in sys.path):
    sys.path.append(nb_dir)

# Set folder paths
amDataPath = str('../data/report/input/am/')
tifDataPath = str('../data/report/input/tif/max_z_projections/')
amOutputPath = str('../data/report/output/am/')
outputFolderPath = str('../data/report/output/am/')
tifOutputPath = str('../data/report/output/tif/')

import radii as radi

getRad = radi.exRadSets.exRadSets

# extract all radii from all am files in folder path and writing them
# in output files in outputFolderPath
getRad(amDataPath, tifDataPath, outputFolderPath)
