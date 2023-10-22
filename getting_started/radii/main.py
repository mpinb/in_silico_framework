#It is just a test sample code.

# coding: utf-8

# This little code in the below box allows us to import our written modules
# which we have in the parent directory. Like radii as in the below example.

# In[1]:

import os
import sys

nb_dir = os.path.split(os.getcwd())[0]
if (nb_dir not in sys.path):
    sys.path.append(nb_dir)

# Here we import needed packages

# In[2]:

import radii as radi
import SimpleITK as sitk
import matplotlib.pyplot as plt

# Set path of different raw data folders and output folders.

# In[3]:

amDataPath = str('../data/am/')
tifDataPath = str('../data/tif/')
amOutputPath = str('../output/am/')

for root, dirs, files in os.walk("."):
    for filename in files:
        print(filename)
    for rootname in root:
        print(rootname)
    for dirsname in dirs:
        print(dirsname)

# Loadin the raw data for a slice and creating array of points from them

# In[4]:

#  s13_data = amDataPath + 'S13_final_done_Alison_zScale_40.am'
#  debug_s13_data = amDataPath + 'debug-S13_final_done_Alison_zScale_40.am'
#  s13_r = amOutputPath + 's13-r.am'
#  debug_s13_r = amOutputPath + 'debug-s13-r.am'
#  s13_points = radi.spacialGraph.getSpatialGraphPoints(debug_s13_data)
#  s13_points = list(map(lambda x: map(lambda y: int(y/0.092), x), s13_points))
#

# Loaiding image corresponding to the points above.

# In[5]:

#
#  s13_tif = tifDataPath + 'S13_max_z_projection.tif'
#  imageFileReader = sitk.ImageFileReader()
#  imageFileReader.SetFileName(s13_tif)
#  s13_image = imageFileReader.Execute()
#

# Plotting the input tif image

# In[6]:

#plt.imshow(sitk.GetArrayViewFromImage(s13_image));

# In[6]:

#  res = radi.radius.getRadiiHalfMax(s13_image, s13_points)

# In[8]:

#  radii = res[1]
#  radii = [r*0.092 for r in radii]
#  radi.spacialGraph.write_spacial_graph_with_thickness(s13_data, debug_s13_r, radii)
