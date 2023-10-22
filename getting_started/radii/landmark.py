# Please run this file in after using source_isf
# With the help of  I.scp.write_landmark_file,
# This piece of code will write a text file to
# a landmark file

import Interface as I
import re

# inputFile = '/home/amir/Projects/radii/radii/data/neuron1/landmark/conFile.txt'
# outputFile = '/home/amir/Projects/radii/radii/data/neuron1/landmark/hocFile'
# outputFile = '/home/amir/Projects/radii/radii/data/neuron1/landmark/hocFile_reduced'
# outputFile = '/home/amir/Projects/radii/radii/data/neuron1/landmark/conFile_transformed'

# inputFile = '/home/amir/Projects/in_silico_framework/getting_started/radii/data/neuron2/test/pairs.txt'
# outputFile = '/home/amir/Projects/in_silico_framework/getting_started/radii/data/neuron2/test/landmark/pairs_landmark'

inputEgHoc = '/home/amir/Projects/in_silico_framework/getting_started/radii/data/neuron2/egHoc.txt'
outputEgHoc = '/home/amir/Projects/in_silico_framework/getting_started/radii/data/neuron2/landmark/egHoc_landmark'

inputEgAm = '/home/amir/Projects/in_silico_framework/getting_started/radii/data/neuron2/egAm.txt'
outputEgAm = '/home/amir/Projects/in_silico_framework/getting_started/radii/data/neuron2/landmark/egAm_landmark'

inputAmTr = '/home/amir/Projects/in_silico_framework/getting_started/radii/data/neuron2/amTransformed2.txt'
outputAmTr = '/home/amir/Projects/in_silico_framework/getting_started/radii/data/neuron2/landmark/am2_transformed_landmark'

# opening and reading txt file and set their points to a list of
# arrays of points
points = []
with open(inputEgHoc, 'r') as hocLand:
    lines = hocLand.readlines()
    for line in lines:
        matches = re.findall('-?\d+\.\d+', line)
        point = list(map(float, matches))
        points.append(point)
I.scp.write_landmark_file(outputEgHoc, points)

points = []
with open(inputEgAm, 'r') as amLand:
    lines = amLand.readlines()
    for line in lines:
        matches = re.findall('-?\d+\.\d+', line)
        point = list(map(float, matches))
        points.append(point)
I.scp.write_landmark_file(outputEgAm, points)

points = []
with open(inputAmTr, 'r') as trLand:
    lines = trLand.readlines()
    for line in lines:
        matches = re.findall('-?\d+\.\d+', line)
        point = list(map(float, matches))
        points.append(point)
I.scp.write_landmark_file(outputAmTr, points)
