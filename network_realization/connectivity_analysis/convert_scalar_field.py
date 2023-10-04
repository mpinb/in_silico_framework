import os
import sys
import numpy as np


def printUsageAndExit():
    print("Usage:")
    print("convert_scalar_field.py <csv-file> <am-file> <data-column>")
    exit()

if __name__ == "__main__":
    if(len(sys.argv) != 4):
        printUsageAndExit()

    filename = sys.argv[1]    
    filenameOut = sys.argv[2]
    dataCol = int(sys.argv[3]) 
    gridSizeOneDim = 50

    gridSize = np.array([gridSizeOneDim, gridSizeOneDim, gridSizeOneDim])

    D = np.loadtxt(filename, delimiter=",", skiprows=1, usecols=(0,1,2,dataCol)).reshape((-1,4))
    cubeIdxs = D[:,0:3].astype(int)
    data = {}
    for i in range(0,D.shape[0]):
        cube = (cubeIdxs[i,0], cubeIdxs[i,1], cubeIdxs[i,2])
        data[cube] = D[i,3]

    valuesFlat = []

    minIdx = np.min(cubeIdxs, axis=0)
    maxIdx = np.max(cubeIdxs, axis=0)
    ni = (maxIdx - minIdx) + 1

    bbMin = np.multiply(minIdx, gridSize) + 0.5 * gridSize
    bbMax = np.multiply(maxIdx+1, gridSize) - 0.5 * gridSize


    for iz in range(minIdx[2], maxIdx[2]+1):
        for iy in range(minIdx[1], maxIdx[1]+1):
            for ix in range(minIdx[0], maxIdx[0]+1):
                cube = (ix,iy,iz)
                if(cube in data):
                    valuesFlat.append(data[cube])
                else:
                    valuesFlat.append(0)

    with open(filenameOut, "w+") as f:
        f.write("# AmiraMesh 3D ASCII 2.0\n\n")
        f.write("define Lattice {} {} {}\n\n".format(ni[0], ni[1], ni[2]))
        f.write("Parameters {\n")         
        f.write("\tContent \"{}x{}x{} float, uniform coordinates\",\n".format(ni[0], ni[1], ni[2]))
        f.write("\tSpacing {} {} {},\n".format(gridSize[0], gridSize[1], gridSize[2]))
        f.write("\tBoundingBox {} {} {} {} {} {},\n".format(bbMin[0], bbMax[0], bbMin[1], bbMax[1], bbMin[2], bbMax[2]))
        f.write("\tCoordType \"uniform\"\n")
        f.write("}\n\n")
        f.write("Lattice { float Data } @1\n\n")
        f.write("# Data section follows\n")
        f.write("@1\n")
        for val in valuesFlat:
            f.write("{:4f}\n".format(val))
