import numpy as np
import time

from scipy.spatial import ConvexHull

# importing modules from folders:
# radii/radii/tranfromTools
# radii/radii/radii
import transformTools as tr
import radii as radi

import Interface as I
from getting_started import getting_started_dir

# Creating varianles for the address of hoc, am_final, and hoc-output Folders
hocDataPath = str('radii/data/neuron2/hoc/')
amDataPath = str('radii/data/neuron2/am_final/')
outputFolderPath = str('radii/data/neuron2/output/')

# Adding the name of files to their folder path and assing them to variables
hocFile = I.os.path.join(getting_started_dir, hocDataPath,
                         "504_GP_WR662_cell_1171_PoM_checked_RE.hoc")
hocFileOutput = I.os.path.join(getting_started_dir, outputFolderPath,
                               "504_hocFileWithRad.hoc")
amFile = I.os.path.join(getting_started_dir, amDataPath, '504_rad_merged.am')

# extract set1 points:
# Read the hoc points (reduced), then removing their radius from them
# ( we need it to have only 3d data points to use an external package)
pointsWithRadius = tr.read.hocFileReduced(hocFile)
hocSet = []
for el in pointsWithRadius:
    hocSet.append([el[0], el[1], el[2]])

# extract set2 points:
# read the spacial Graph points
points = radi.spacialGraph.getSpatialGraphPoints(amFile)
amSet = points

# -- Bellow (commented) there is a test for looking at the convecHall points in a landmark file
# trMatrix = tr.exTrMatrix.read(amFile)
# conPoints = []
# convexSet2 = ConvexHull(points)
# for verIndex in convexSet2.vertices:
#     conPoints.append(points[verIndex])
# calculate transformation matrix:
# set2 = []
# for point in points:
#     point.append(1)
#     p = np.dot(np.array(point), trMatrix)
#     set2.append(p)
# conFile = '/home/amir/Projects/radii/radii/data/neuron1/landmark/conFile.txt'
# with open(conFile, 'w') as f:
#     for item in set2:
#         f.write('{:f}\t{:f}\t{:f} \n'.format(item[0], item[1], item[2]))

# In this section we are finding the longest matched edges from set1 and set2:

# Choosing the number of edges that we need to find their corresponds
# from set2 to set1, for extrating teansformation matrix we need 4 points,
# so we need two edges.
numberOfEdges = 2

# Getting the mached set of edges
print("in the matchSet process")
matchedSet = tr.getDistance.matchEdges(hocSet, amSet, numberOfEdges)

# Here after finding the matched set, we sperate the source points
# and destination points.
src_hoc = []
dst_am = []
# matchedSet[0][1].end = matchedSet[0][1].start
# matchedSet[0][1].start = p0End
for point in matchedSet:
    src_hoc.append(point[0].start)
    src_hoc.append(point[0].end)

    dst_am.append(point[1].start)
    dst_am.append(point[1].end)
    print("mach points 1")
    print((point[0].start))
    print((point[1].start))
    print("mach points 2")
    print((point[0].end))
    print((point[1].end))

# Calculate the transformation matrix based on 4 source
# points and 4 destination points.
print("In the calculations of the transofrmation matrix")
trMatrix2 = tr.exTrMatrix.getTransformation(dst_am, src_hoc)
# print(trMatrix2)

# In the below we read the points from amFile (actual set2 with their radius)
# again but this time also we read their correspoinding radii
amPoints4D = tr.read.amFile(amFile)

# Now after getting the initial am points with their radius we will apply the
# transformation matrix on them
print("Applying the transofrmation matrix to the initial am points")
trAmPoints4D = []
for point4D in amPoints4D:
    point = point4D[:3]
    mPoint = np.matrix(point)
    mTrPoint = mPoint.T

    p = trMatrix2 * np.matrix(np.vstack((mTrPoint, 1.0)))
    p = np.array(p.T)
    p_listed = p.tolist()[0]
    # raw_input("somet")
    trAmPoints4D.append([p_listed[0], p_listed[1], p_listed[2], point4D[3]])

# it is small test to see if the amFileReader is working well enough or not
# for this we check some sample points from the both am readers function
# and compare them
print((amPoints4D[0]))
print((trAmPoints4D[0]))

print((amPoints4D[10]))
print((trAmPoints4D[10]))

print((amPoints4D[1234]))
print((trAmPoints4D[1234]))

print((amPoints4D[11]))
print((trAmPoints4D[11]))

print((amPoints4D[56]))
print((trAmPoints4D[56]))

# In the below we read the hoc file again this time completely,
# i.e. without just taking two points from each sections
print("reading hoc file completely")
hocPointsComplete = tr.read.hocFileComplete(hocFile)
hocSet = []
for el in hocPointsComplete:
    hocSet.append([el[0], el[1], el[2]])

trAmPoints4DList = trAmPoints4D
# a small test to see if the previous transofrmation on trAmPoints4DList
# does not change the 4th coloumn which contains the radii
print((trAmPoints4DList[0]))
print((amPoints4D[0]))

print((trAmPoints4DList[2]))
print((amPoints4D[2]))

print((trAmPoints4DList[100]))
print((amPoints4D[100]))

print((trAmPoints4DList[10]))
print((amPoints4D[10]))

print((trAmPoints4DList[1293]))
print((amPoints4D[1293]))

# In the below we are trying to find the closest points between transformed
# am points and hoc points
# print("In the process of finding pairs in between hoc file and the transoformed points to add radi to hocpoint")
# startTime = time.time()
# pairs = radi.addRadii.findPairs(trAmPoints4DList, hocSet)
# endTime = time.time()
# print(endTime - startTime)

# Little Test of the function above

# print(hocSet[0])
# print(pairs[0][0])
# print("---------")
# print(hocSet[1])
# print(pairs[1][0])
# print("---------")
# print(hocSet[42])
# print(pairs[42][0])
# print("---------")
# print(hocSet[13099])
# print(pairs[13099][0])
# print("---------")
# print(hocSet[13100])
# print(pairs[13100][0])
# print("---------")

# initialAmPointsWithRad = tr.read.amFile(amFile)
# initialAmPointsWithRad2 = radi.spacialGraph.getSpatialGraphPoints(amFile)

# Little Test of the reading functions again
# print(initialAmPointsWithRad[0])
# print(initialAmPointsWithRad2[0])
# print("---------")
# print(initialAmPointsWithRad[1])
# print(initialAmPointsWithRad2[1])
# print("---------")
# print(initialAmPointsWithRad[42])
# print(initialAmPointsWithRad2[42])
# print("---------")
# print(initialAmPointsWithRad[len(initialAmPointsWithRad)-1])
# print(initialAmPointsWithRad2[len(initialAmPointsWithRad2)-1])

# startTime = time.time()
# hocWithRad = []
# newHPoint = []

# In the below codes, we are adding radii to corresponding hoc point,
# based on the pairs that we found from the above codes
# print("adding radii to corresponding hoc point, based on the pairs")

# outTestFolder = str('/home/amir/Projects/in_silico_framework/getting_started/radii/data/neuron2/test/')

# pairesFile = "pairs.txt"
# trAmPoints4DFile = "trAmPoints4D.txt"
# amPoints4DFile = "amPoints4D.txt"

# testPairs = I.os.path.join(getting_started_dir, outTestFolder,pairesFile)
# testTrAmPoints4D = I.os.path.join(getting_started_dir, outTestFolder, trAmPoints4DFile)
# testAmPoints4D = I.os.path.join(getting_started_dir, outTestFolder, amPoints4DFile)

# with open(testPairs, 'w') as f:
# for pai in pairs:
# f.write('[[{:f},{:f},{:f},{:f}],\t[{:f},{:f},{:f}]] \n'.format(pai[0][0],pai[0][1],pai[0][2],pai[0][3], pai[1][0], pai[1][1], pai[1][2]))

# with open(testTrAmPoints4D, 'w') as f:
# for tp in trAmPoints4DList:
# f.write('[{:f},{:f},{:f},{:f}] \n'.format(tp[0],tp[1],tp[2],tp[3]))

# with open(testAmPoints4D, 'w') as f:
# for ap in amPoints4D:
# f.write('[{:f},{:f},{:f},{:f}] \n'.format(ap[0],ap[1],ap[2],ap[3]))

# for pair in pairs:
# newHPoint = pair[1]
# dual = pair[0]
# newHPoint.append(dual[3])
# hocWithRad.append(newHPoint)
# newHPoint = []

# endTime = time.time()
# print(endTime - startTime)

# test between to different hoc file arrays derived from above functions
# print(hocSet[0])
# print(hocWithRad[0])
# print("---------")
# print(hocSet[1])
# print(hocWithRad[1])
# print("---------")
# print(hocSet[42])
# print(hocWithRad[42])
# print("---------")

# In the below we are writing the final hoc file with its radii
# print("writing the final result in the output hocFile")
# startTime = time.time()
# tr.write.hocFile(hocFile, hocFileOutput, hocWithRad)
# endTime = time.time()
# print(endTime - startTime)

# These are sample code to write landmark files from different sets
# print(list(newPoints[3]))
# print(newPoints[1])
# for it in newPoints:
#     print(it.item((0,3)))

egHocFile = '/home/amir/Projects/in_silico_framework/getting_started/radii/data/neuron2/egHoc.txt'
egAmFile = '/home/amir/Projects/in_silico_framework/getting_started/radii/data/neuron2/egAm.txt'

with open(egHocFile, 'w') as f:
    for item in matchedSet:
        startPoint = item[0].start
        endPoint = item[0].end
        f.write('{:f}\t{:f}\t{:f} \n'.format(startPoint[0], startPoint[1],
                                             startPoint[2]))
        f.write('{:f}\t{:f}\t{:f} \n'.format(endPoint[0], endPoint[1],
                                             endPoint[2]))

with open(egAmFile, 'w') as f:
    for item in matchedSet:
        startPoint = item[1].start
        endPoint = item[1].end
        f.write('{:f}\t{:f}\t{:f} \n'.format(startPoint[0], startPoint[1],
                                             startPoint[2]))
        f.write('{:f}\t{:f}\t{:f} \n'.format(endPoint[0], endPoint[1],
                                             endPoint[2]))

amTrFile = '/home/amir/Projects/in_silico_framework/getting_started/radii/data/neuron2/amTransformed2.txt'
with open(amTrFile, 'w') as f:
    for it in trAmPoints4DList:
        f.write('{:f}\t{:f}\t{:f} \n'.format(it[0], it[1], it[2]))
