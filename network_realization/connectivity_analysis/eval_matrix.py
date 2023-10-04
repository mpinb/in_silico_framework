import os
import sys

import drawSvg as draw
from colour import Color
import math
from numpy import random
import numpy as np
import matplotlib.cm
import multiprocessing as mp
from ctypes import c_float

import util
import util_meta
import util_filter
import constants

def getMatrixColorTable():    
    return [
        [0.008, 0.016, 0.098], [0.012, 0.020, 0.102], [0.016, 0.020, 0.106],
        [0.020, 0.024, 0.110], [0.027, 0.027, 0.114], [0.031, 0.027, 0.118],
        [0.035, 0.031, 0.122], [0.043, 0.035, 0.125], [0.047, 0.039, 0.129],
        [0.055, 0.039, 0.133], [0.059, 0.043, 0.137], [0.067, 0.047, 0.141],
        [0.071, 0.047, 0.145], [0.078, 0.051, 0.149], [0.082, 0.055, 0.153],
        [0.086, 0.055, 0.157], [0.094, 0.059, 0.161], [0.098, 0.063, 0.165],
        [0.106, 0.063, 0.169], [0.110, 0.067, 0.173], [0.118, 0.067, 0.176],
        [0.122, 0.071, 0.180], [0.125, 0.071, 0.184], [0.133, 0.075, 0.188],
        [0.137, 0.075, 0.192], [0.145, 0.078, 0.196], [0.149, 0.078, 0.200],
        [0.157, 0.082, 0.204], [0.161, 0.082, 0.208], [0.169, 0.086, 0.212],
        [0.173, 0.086, 0.216], [0.180, 0.086, 0.220], [0.184, 0.090, 0.224],
        [0.192, 0.090, 0.227], [0.196, 0.094, 0.231], [0.200, 0.094, 0.235],
        [0.208, 0.094, 0.239], [0.212, 0.098, 0.243], [0.220, 0.098, 0.247],
        [0.224, 0.098, 0.251], [0.231, 0.102, 0.255], [0.239, 0.102, 0.259],
        [0.243, 0.102, 0.263], [0.251, 0.106, 0.267], [0.255, 0.106, 0.271],
        [0.263, 0.106, 0.271], [0.267, 0.106, 0.275], [0.275, 0.110, 0.278],
        [0.278, 0.110, 0.282], [0.286, 0.110, 0.286], [0.290, 0.110, 0.286],
        [0.298, 0.110, 0.290], [0.306, 0.114, 0.294], [0.310, 0.114, 0.298],
        [0.318, 0.114, 0.298], [0.322, 0.114, 0.302], [0.329, 0.114, 0.306],
        [0.333, 0.114, 0.306], [0.341, 0.118, 0.310], [0.349, 0.118, 0.314],
        [0.353, 0.118, 0.314], [0.361, 0.118, 0.318], [0.365, 0.118, 0.318],
        [0.373, 0.118, 0.322], [0.380, 0.118, 0.322], [0.384, 0.118, 0.325],
        [0.392, 0.118, 0.325], [0.400, 0.118, 0.329], [0.404, 0.118, 0.329],
        [0.412, 0.122, 0.333], [0.416, 0.122, 0.333], [0.424, 0.122, 0.337],
        [0.431, 0.122, 0.337], [0.435, 0.122, 0.341], [0.443, 0.122, 0.341],
        [0.451, 0.122, 0.341], [0.455, 0.118, 0.345], [0.463, 0.118, 0.345],
        [0.471, 0.118, 0.345], [0.475, 0.118, 0.349], [0.482, 0.118, 0.349],
        [0.490, 0.118, 0.349], [0.494, 0.118, 0.349], [0.502, 0.118, 0.353],
        [0.510, 0.118, 0.353], [0.514, 0.118, 0.353], [0.522, 0.114, 0.353],
        [0.529, 0.114, 0.353], [0.537, 0.114, 0.353], [0.541, 0.114, 0.357],
        [0.549, 0.114, 0.357], [0.557, 0.110, 0.357], [0.561, 0.110, 0.357],
        [0.569, 0.110, 0.357], [0.576, 0.110, 0.357], [0.580, 0.106, 0.357],
        [0.588, 0.106, 0.357], [0.596, 0.106, 0.357], [0.604, 0.102, 0.357],
        [0.608, 0.102, 0.357], [0.616, 0.102, 0.357], [0.624, 0.102, 0.357],
        [0.631, 0.098, 0.353], [0.635, 0.098, 0.353], [0.643, 0.098, 0.353],
        [0.651, 0.094, 0.353], [0.655, 0.094, 0.353], [0.663, 0.094, 0.349],
        [0.671, 0.090, 0.349], [0.675, 0.090, 0.349], [0.682, 0.090, 0.349],
        [0.690, 0.086, 0.345], [0.694, 0.086, 0.345], [0.702, 0.086, 0.341],
        [0.710, 0.086, 0.341], [0.714, 0.086, 0.341], [0.722, 0.086, 0.337],
        [0.729, 0.086, 0.337], [0.733, 0.086, 0.333], [0.741, 0.086, 0.329],
        [0.749, 0.086, 0.329], [0.753, 0.086, 0.325], [0.761, 0.090, 0.325],
        [0.765, 0.090, 0.322], [0.773, 0.090, 0.318], [0.776, 0.094, 0.318],
        [0.784, 0.098, 0.314], [0.788, 0.098, 0.310], [0.796, 0.102, 0.310],
        [0.800, 0.106, 0.306], [0.804, 0.110, 0.302], [0.812, 0.114, 0.302],
        [0.816, 0.118, 0.298], [0.820, 0.122, 0.294], [0.827, 0.129, 0.290],
        [0.831, 0.133, 0.290], [0.835, 0.137, 0.286], [0.843, 0.145, 0.282],
        [0.847, 0.149, 0.278], [0.851, 0.153, 0.278], [0.855, 0.161, 0.275],
        [0.859, 0.165, 0.271], [0.863, 0.173, 0.271], [0.871, 0.176, 0.267],
        [0.875, 0.184, 0.263], [0.878, 0.188, 0.259], [0.882, 0.196, 0.259],
        [0.886, 0.204, 0.255], [0.890, 0.208, 0.255], [0.894, 0.216, 0.251],
        [0.898, 0.224, 0.251], [0.902, 0.231, 0.247], [0.902, 0.235, 0.247],
        [0.906, 0.243, 0.243], [0.910, 0.251, 0.243], [0.914, 0.259, 0.243],
        [0.914, 0.267, 0.239], [0.918, 0.275, 0.239], [0.922, 0.282, 0.239],
        [0.922, 0.290, 0.239], [0.925, 0.298, 0.239], [0.925, 0.306, 0.243],
        [0.929, 0.314, 0.243], [0.929, 0.318, 0.243], [0.933, 0.325, 0.247],
        [0.933, 0.333, 0.247], [0.937, 0.341, 0.251], [0.937, 0.349, 0.251],
        [0.937, 0.357, 0.255], [0.941, 0.365, 0.259], [0.941, 0.373, 0.263],
        [0.941, 0.380, 0.267], [0.945, 0.388, 0.271], [0.945, 0.396, 0.275],
        [0.945, 0.404, 0.278], [0.945, 0.412, 0.282], [0.949, 0.420, 0.286],
        [0.949, 0.427, 0.290], [0.949, 0.431, 0.294], [0.949, 0.439, 0.302],
        [0.949, 0.447, 0.306], [0.953, 0.455, 0.310], [0.953, 0.463, 0.318],
        [0.953, 0.471, 0.322], [0.953, 0.475, 0.325], [0.953, 0.482, 0.333],
        [0.953, 0.490, 0.337], [0.953, 0.498, 0.345], [0.957, 0.502, 0.349],
        [0.957, 0.510, 0.357], [0.957, 0.518, 0.361], [0.957, 0.525, 0.369],
        [0.957, 0.529, 0.373], [0.957, 0.537, 0.380], [0.957, 0.545, 0.384],
        [0.957, 0.553, 0.392], [0.957, 0.557, 0.396], [0.961, 0.565, 0.404],
        [0.961, 0.573, 0.412], [0.961, 0.576, 0.416], [0.961, 0.584, 0.424],
        [0.961, 0.592, 0.431], [0.961, 0.596, 0.435], [0.961, 0.604, 0.443],
        [0.961, 0.612, 0.451], [0.961, 0.616, 0.455], [0.961, 0.624, 0.463],
        [0.961, 0.631, 0.471], [0.961, 0.635, 0.478], [0.961, 0.643, 0.482],
        [0.961, 0.651, 0.490], [0.961, 0.655, 0.498], [0.961, 0.663, 0.506],
        [0.961, 0.667, 0.514], [0.961, 0.675, 0.522], [0.961, 0.682, 0.529],
        [0.965, 0.686, 0.537], [0.965, 0.694, 0.545], [0.965, 0.698, 0.549],
        [0.965, 0.706, 0.557], [0.965, 0.714, 0.565], [0.965, 0.718, 0.573],
        [0.965, 0.725, 0.584], [0.965, 0.729, 0.592], [0.965, 0.737, 0.600],
        [0.965, 0.741, 0.608], [0.965, 0.749, 0.616], [0.965, 0.753, 0.624],
        [0.965, 0.761, 0.631], [0.965, 0.765, 0.639], [0.965, 0.773, 0.647],
        [0.965, 0.780, 0.659], [0.965, 0.784, 0.667], [0.965, 0.792, 0.675],
        [0.969, 0.796, 0.682], [0.969, 0.804, 0.690], [0.969, 0.808, 0.702],
        [0.969, 0.812, 0.710], [0.969, 0.820, 0.718], [0.969, 0.824, 0.725],
        [0.969, 0.831, 0.733], [0.969, 0.835, 0.745], [0.973, 0.843, 0.753],
        [0.973, 0.847, 0.761], [0.973, 0.855, 0.769], [0.973, 0.859, 0.776],
        [0.973, 0.867, 0.788], [0.973, 0.871, 0.796], [0.973, 0.878, 0.804],
        [0.976, 0.882, 0.812], [0.976, 0.890, 0.820], [0.976, 0.894, 0.827],
        [0.976, 0.902, 0.839], [0.976, 0.906, 0.847], [0.980, 0.914, 0.855],
        [0.980, 0.918, 0.863]
    ]


def interpolateMatrixColor(val):
    table = getMatrixColorTable()
    n = len(table)
    idx = math.floor(val * n)
    if(idx >= len(table)):
        idx = len(table) - 1
    rgb = table[idx]
    color = Color(rgb=(rgb[0], rgb[1], rgb[2]))
    return color


def drawSepatorHorizontal(d, nx, ny, val):
    d.append(draw.Line(0, (1-val) * ny, nx, (1-val) * ny, stroke='white', stroke_width=1, fill='white'))


def drawSepatorHorizontal2(d, nx, ny, val, col="white"):
    d.append(draw.Rectangle(0, (1-val) * ny, nx,1, fill=col, stroke_width=0))


def drawSepatorVertical(d, nx, ny, val):
    d.append(draw.Line(val*nx, 0, val*nx, ny, stroke='white', stroke_width=1, fill='white'))


def drawSepatorVertical2(d, nx, ny, val, col="white"):
    d.append(draw.Rectangle(val*nx, 0, 1,ny, fill=col, stroke_width=0))


def isSeparated(oldLabel, newLabel):
    if(oldLabel in getCellTypesReordered() or oldLabel == "VPM"):
        return True
    return "{}-{}".format(oldLabel, newLabel) in ["Alpha-B1","Beta-C1","Gamma-D1","Delta-E1"]


def getSeparatorPoints(data, mode):    
    points = []
    n = len(data)
    if(mode in ["C2", "C2-subset"]):
        lastLabel = data[0][1]
    else:
        lastLabel = data[0]["column"]
    for i in range(0,n):
        if(mode in ["C2", "C2-subset"]):
            newLabel = data[i][1]
        else:
            newLabel = data[i]["column"]
        if(lastLabel != newLabel):            
            if(isSeparated(lastLabel, newLabel)):
                points.append(i/n)
            lastLabel = newLabel
    
    return points


def getSelectedPoints(data):
    points = []
    n = len(data)    
    for i in range(0,n):
        if(data[i][2]):
            points.append(i/n)            
    return points


def getColorFromDict(val, colorDict):
    numSteps = len(colorDict) - 1
    idx = math.floor(val * numSteps)
    return colorDict[idx]


def getQuantilesIntValues(quantiles, numSteps):
    quantilesInt = []
    colSegments = []
    for q in quantiles:
        valInt = int(math.floor(q * numSteps))
        quantilesInt.append(valInt)
    stepInt = numSteps // (len(quantiles)-1)
    for i in range(0,len(quantiles)):
        colSegments.append(i*stepInt)
    return quantilesInt, colSegments


def renderColorscale(outfile, colorDict, quantilesProb):
    numSteps = len(colorDict)
    offsetY = 2
    offsetX = 50
    offsetD = 10
    widthScale = 50
    width = offsetX + widthScale + offsetD + widthScale + offsetX
    height = numSteps + 4

    quantilesInt, colSegments = getQuantilesIntValues(quantilesProb, numSteps-1)

    d = draw.Drawing(width, height, displayInline=False)
    d.setPixelScale(1)  # Set number of pixels per geometry unit

    for i in range(0, numSteps):
        c = colorDict[i]
        d.append(draw.Rectangle(offsetX, numSteps - i - 1 + offsetY, widthScale, 1, fill=c, stroke_width=0))
        
        relVal = i / (numSteps-1)
        c = interpolateMatrixColor(relVal)
        d.append(draw.Rectangle(offsetX + widthScale + offsetD, numSteps - i - 1 + offsetY, widthScale, 1, fill=c, stroke_width=0))

        if(i > 0 and i<numSteps-1 and i % 100 == 0):
            d.append(draw.Rectangle(0, numSteps - i - 1 + offsetY, offsetX, 2, fill="black", stroke_width=0))
        if(i in quantilesInt): 
            d.append(draw.Rectangle(0, numSteps - i - 1 + offsetY, offsetX, 2, fill="red", stroke_width=0))
        if(i in colSegments): 
            d.append(draw.Rectangle(offsetX + widthScale + offsetD + widthScale, numSteps - i - 1 + offsetY, offsetX, 2, fill="red", stroke_width=0))

    d.savePng(outfile)


def writeColorscale(outfile, colorDict):
    with open(outfile, "w+") as f:
        f.write("probability,r,g,b\n")
        for i in range(0, len(colorDict)):
            c = colorDict[i]
            prob = i / (len(colorDict)-1) 
            f.write("{:.3f},{:.3f},{:.3f},{:.3f}\n".format(prob, c.red, c.green, c.blue))


def renderMatrix(D, rows, cols, outfile, colorDict, mode):
    nrows = D.shape[0]
    ncols = D.shape[1]

    d = draw.Drawing(ncols, nrows, displayInline=False)
    d.setPixelScale(1)  # Set number of pixels per geometry unit

    for iy in range(0, nrows):
        print("render row",iy)
        for ix in range(0, ncols):
            c = getColorFromDict(D[iy,ix], colorDict)
            d.append(draw.Rectangle(ix ,nrows-iy-1, 1, 1, fill=c, stroke_width=0))

    sepRows = getSeparatorPoints(rows, mode)
    for sep in sepRows:
        drawSepatorHorizontal2(d, ncols, nrows, sep)
    sepCols = getSeparatorPoints(cols, mode)
    for sep in sepCols:
        drawSepatorVertical2(d, ncols, nrows, sep)
    
    d.savePng(outfile)

    if(mode in ["C2", "C2-subset"]):

        sepRows = getSelectedPoints(rows)
        for sep in sepRows:
            drawSepatorHorizontal2(d, ncols, nrows, sep, "green")
        sepCols = getSelectedPoints(cols)
        for sep in sepCols:
            drawSepatorVertical2(d, ncols, nrows, sep, "green")

        outfileMarked = outfile.replace(".png","_marked.png")
        d.savePng(outfileMarked)


def getCellTypesReordered():    
    return ["L2PY", "L3PY", "L4PY", "L4sp", "L4ss","L5IT", "L5PT", "L6CC", "L6INV", "L6CT", "INH"]


def getColumnsReordered():    
    return ["A1", "A2", "A3", "A4", "Alpha",
            "B1", "B2", "B3", "B4", "Beta",
            "C1", "C2", "C3", "C4", "Gamma",
            "D1", "D2", "D3", "D4", "Delta",
            "E1", "E2", "E3", "E4"]


def getColumnsReordered9():    
    return ["B1", "B2", "B3",
            "C1", "C2", "C3",
            "D1", "D2", "D3"]


def getColumnsReordered3():    
    return ["Alpha", "B1", "C2"]


def sortNeurons(neuronIds, neuronProps, propertyName="cortical_depth"):
    propVals = []
    for neuronId in neuronIds:
        propertyVal = neuronProps[neuronId][propertyName]
        propVals.append(propertyVal)
    idx = np.argsort(propVals)
    neuronIdsSorted = np.array(neuronIds)[idx]
    return neuronIdsSorted


def appendNeuronIds(data, neuronIds, meta, neuronProps):
    selectedIds = constants.getSelectedCellIds()
    neuronIds = list(neuronIds)
    neuronIdsSorted = sortNeurons(neuronIds, neuronProps)
    for neuronId in neuronIdsSorted:
        selected = neuronId in selectedIds 
        data.append((neuronId, meta, selected))


def getRowColMeta(neurons, mode):
    rows = []
    cols = []
    
    if(mode == "C2"):
        vpmFilter = util_filter.getVPMFilter()
        neuronIds = util_filter.filterNIDs(neurons, vpmFilter)    
        appendNeuronIds(rows, neuronIds, "VPM", neurons)

        for ct in getCellTypesReordered():
            filterSpec = util_filter.getDefaultFilter()
            filterSpec["region_whitelist"] = ["C2","S1_Septum_C2"]
            filterSpec["celltype_whitelist"] = [ct]
            neuronIds = util_filter.filterNIDs(neurons, filterSpec)    
            appendNeuronIds(rows, neuronIds, ct, neurons)
            appendNeuronIds(cols, neuronIds, ct, neurons)                        
    elif(mode == "C2-subset"):
        for ct in ["L4ss", "L5IT", "L5PT", "L6CC", "L6INV"]:
            filterSpec = util_filter.getDefaultFilter()
            filterSpec["region_whitelist"] = ["C2","S1_Septum_C2"]
            filterSpec["celltype_whitelist"] = [ct]
            neuronIds = util_filter.filterNIDs(neurons, filterSpec)    
            appendNeuronIds(rows, neuronIds, ct, neurons)
            appendNeuronIds(cols, neuronIds, ct, neurons)                        
    else:
        raise ValueError(mode)        
    return rows, cols


def getRowColMetaComplete(neurons, preSamples):
    rows = []
    cols = []

    celltypes = ["VPM"]
    celltypes.extend(getCellTypesReordered())
    
    for col in getColumnsReordered():      
        print("filter", col)  
        for ct in celltypes:            
            if(ct == "VPM"):
                filterSpec = util_filter.getVPMFilter()
                filterSpec["region_whitelist"] = ["{}_Barreloid".format(col)]
            else:
                filterSpec = util_filter.getDefaultFilter()
                filterSpec["region_whitelist"] = ["{}".format(col),"S1_Septum_{}".format(col)]
                filterSpec["celltype_whitelist"] = [ct]            

            neuronIds = list(util_filter.filterNIDs(neurons, filterSpec))
            np.random.shuffle(neuronIds)
            neuronIdsPre = neuronIds[0:preSamples]
            
            rows.append({
                "column" : col,
                "cellType" : ct,
                "neuronIds" : neuronIdsPre
            })
            if(ct != "VPM"):
                cols.append({
                    "column" : col,
                    "cellType" : ct,
                    "neuronIds" : neuronIds
                })
    return rows, cols


def sample(rows, cols, targetSize):
    rowsSampled = []
    colsSampled = []
    step = math.floor(len(rows)/targetSize)
    for i in range(0, len(rows)):
        row = rows[i]
        if(i % step == 0 or row[2]):
            rowsSampled.append(row)
    for i in range(0, len(cols)):
        col = cols[i]
        if(i % step == 0 or col[2]):
            colsSampled.append(col)
    return rowsSampled, colsSampled


def getPostIds(cols):
    postIds = []
    for col in cols:
        postIds.append(col[0])
    return np.array(postIds)


def getMatrixValues(networkDir, rows, cols, dscFolder):
    nrows = len(rows)
    ncols = len(cols)
    D = np.zeros(shape=(nrows, ncols))
    postIds = getPostIds(cols)
    for i in range(0,nrows):
        print("values {}/{}".format(i,nrows))
        preId = rows[i][0]
        postIdsPre, dsc = util.loadDataBlock(os.path.join(dscFolder, "{}_DSC.csv".format(preId)),1)
        _, idxSharedPre, idxSharedPost = np.intersect1d(postIdsPre, postIds, assume_unique=True, return_indices=True)
        print(preId,idxSharedPre.shape, idxSharedPost.shape, postIdsPre.shape, dsc.shape, D.shape)
        D[i,idxSharedPost] = dsc[idxSharedPre]
    D = 1-np.exp(-D)
    for i in range(0,nrows):
        preId = rows[i][0]
        for j in range(0,postIds.size):
            if(preId == postIds[j]):
                D[i,j] = 0
    return D
    

def getMatrixValuesBatch(rowIndices, rows, cols, networkDir, dataArray, dscFolder):    
    ncols = len(cols)
    postIds = getPostIds(cols)
    k = 0
    for i in rowIndices:
        k += 1
        D = np.zeros(ncols)
        preId = rows[i][0]
        postIdsPre, dsc = util.loadDataBlock(os.path.join(dscFolder, "{}_DSC.csv".format(preId)),1)
        _, idxSharedPre, idxSharedPost = np.intersect1d(postIdsPre, postIds, assume_unique=True, return_indices=True)
        D[idxSharedPost] = dsc[idxSharedPre]
        probs = 1-np.exp(-D)
        
        offset = i * ncols
        for j in range(0, ncols):
            arrayIndex = offset + j
            dataArray[arrayIndex] = probs[j]
        print("loaded data for row {}/{}".format(k, len(rowIndices)))


def getMatrixValuesCompleteBatch(rowIndices, rows, cols, networkDir, dataArray, dscFolder):    
    ncols = len(cols)

    m = 0
    for i in rowIndices:        
        m += 1
        row = rows[i]
        preIds = row["neuronIds"]
        nPre = len(preIds)
        
        # Load DSC
        postIdsPerPreNeuron = {}
        dscPerPreNeuron = {}
        for preId in preIds:
            postIdsPre, dsc = util.loadDataBlock(os.path.join(dscFolder, "{}_DSC.csv".format(preId)),1)
            postIdsPerPreNeuron[preId] = postIdsPre
            dscPerPreNeuron[preId] = dsc

        offset = i * ncols
        for j in range(0, ncols):
            col = cols[j]
            postIds = col["neuronIds"]
            nPost = len(postIds)
            # calc mean prob 
            D = np.zeros(nPost * nPre)
            for k in range(0, nPre):
                preId = preIds[k]
                postIdsPerPre = postIdsPerPreNeuron[preId]
                dscPerPre = dscPerPreNeuron[preId]
                common, idxSharedPre, idxSharedPost = np.intersect1d(postIdsPerPre, postIds, assume_unique=True, return_indices=True)                
                if(common.size):
                    rangeDLow = k * nPost
                    rangeDHigh = rangeDLow + common.size
                    D[rangeDLow:rangeDHigh] = dscPerPre[idxSharedPre]

            probs = 1-np.exp(-D)    
            meanProb = np.mean(probs)
            arrayIndex = offset + j
            dataArray[arrayIndex] = meanProb
          
        print("loaded data for row {}/{} ({},{})".format(m, len(rowIndices), row["column"], row["cellType"]))


def getMatrixValuesMP(networkDir, rows, cols, dscFolder, numWorkers):
    nrows = len(rows)
    ncols = len(cols)

    dataArray = mp.Array(c_float, nrows * ncols, lock=False)
    rowIndices = np.arange(nrows)
    batches = np.array_split(rowIndices, numWorkers)
    processes = []
    for batch in batches:
        p = mp.Process(target=getMatrixValuesBatch, args=(batch, rows, cols, networkDir, dataArray, dscFolder))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()

    D = np.zeros(shape=(nrows, ncols))
    for i in range(0, nrows):
        for j in range(0, ncols):
            arrayIndex = i * ncols + j
            D[i,j] = dataArray[arrayIndex]

    return D 


def getMatrixValuesComplete(networkDir, rows, cols, dscFolder, numWorkers):
    nrows = len(rows)
    ncols = len(cols)

    dataArray = mp.Array(c_float, nrows * ncols, lock=False)
    rowIndices = np.arange(nrows)
    batches = np.array_split(rowIndices, numWorkers)
    processes = []
    for batch in batches:
        p = mp.Process(target=getMatrixValuesCompleteBatch, args=(batch, rows, cols, networkDir, dataArray, dscFolder))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()

    D = np.zeros(shape=(nrows, ncols))
    for i in range(0, nrows):
        for j in range(0, ncols):
            arrayIndex = i * ncols + j
            D[i,j] = dataArray[arrayIndex]

    return D 


def getColorFromTable(rgb):    
    color = Color(rgb=(rgb[0], rgb[1], rgb[2]))
    return color


def getAllQuantiles(D):
    # compute all quantiles {0, ..., 1}
    step = 0.01
    quantiles = np.arange(0, 1+step, step)
    return np.quantile(D, quantiles)


def getColorscaleByQuantiles(D, q):
        
    table = getMatrixColorTable()    
    quantiles = np.quantile(D, q)
    numInterquantiles = len(q) - 1

    nColors = len(table)
    nColorsPerQuantile =  nColors / numInterquantiles

    colorDict = {}
    step = 0.001  
    nSteps = int(1/step) + 1
    for k in range(0, nSteps):
        prob = k * step
        probInt = int((nSteps-1) * prob)

        if(prob < quantiles[0]):
            colorDict[probInt] = getColorFromTable(table[0])
        elif(prob >= quantiles[-1]):
            colorDict[probInt] = getColorFromTable(table[-1])
        else:
            for k in range(1, len(quantiles)):
                qLow = quantiles[k-1]
                qHigh = quantiles[k]
                if(prob < qHigh):   
                    quantileIndex = k - 1
                    quantileRel = (prob - qLow) / (qHigh - qLow)                                                        
                    tableIndex = int(math.floor(quantileIndex * nColorsPerQuantile + quantileRel * nColorsPerQuantile))
                    if(tableIndex >=  len(table)):
                        tableIndex = len(table) -1
                    colorDict[probInt] = getColorFromTable(table[tableIndex])
                    break
        
    print(quantiles)   
    quantilesAll = getAllQuantiles(D)
    return colorDict, quantiles, quantilesAll     


def getFormattedArray(values):
    s = ""
    for val in values:
        s += "{:.6f} ".format(val)
    return s


def getFromToDescriptor(mode, row, col):
    if(mode in ["C2", "C2-subset"]):
        return "({} -> {})".format(row[0], col[0])
    elif(mode == "complete"):
        return "({}-{} -> {}-{})".format(row["column"], row["cellType"], col["column"], col["cellType"])
    else:
        raise ValueError(mode)


def writeStats(filename, quantiles, quantilesProb, quantilesAll, D, mode):    
    maxIdx = np.unravel_index(D.argmax(), D.shape)    
    nonzeroIdx = D > 0
    with open(filename, "w+") as f:
        f.write("maxValue: {:.6f} {}\n".format(D[maxIdx], getFromToDescriptor(mode, rows[maxIdx[0]], cols[maxIdx[1]])))
        f.write("median: {:.6f}\n".format(np.median(D)))
        f.write("mean: {:.6f}\n".format(np.mean(D)))
        f.write("median nonzero: {:.6f}\n".format(np.median(D[nonzeroIdx])))
        f.write("mean nonzero: {:.6f}\n\n".format(np.mean(D[nonzeroIdx])))
        f.write("quantiles for colorscale:    {}\n".format(getFormattedArray(quantiles)))
        f.write("corresponding values:        {}\n".format(getFormattedArray(quantilesProb)))
        f.write("\nColorscale is split and the resulting colorscale segments are linearly mapped to inter-quantile invervals.\nIn case of three quantiles, the colorscale is split into two segments.")
        f.write("\n\nquantile,probability\n")
        for i in range(0, quantilesAll.size):
            quantile = i / 100
            probability = quantilesAll[i]
            f.write("{:.3f},{:.5f}\n".format(quantile, probability))


def printUsageAndExit():
    print("eval_matrix.py network-dir mode [num-workers]")
    print()
    print("mode:    complete, C2, C2-subset")
    exit()


if __name__ == "__main__":
    if(len(sys.argv) not in [3,4]):        
        printUsageAndExit()

    networkDir = sys.argv[1]
    mode = sys.argv[2]
    if(len(sys.argv) == 4):
        numWorkers = int(sys.argv[3])
    else:
        numWorkers = mp.cpu_count()
    
    dscFolder = os.path.join(networkDir, "DSC_50-50-50_all")
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    matrixFolder = os.path.join(networkDir, "eval", "matrix")
    util.makeDir(matrixFolder)
    outfolder = os.path.join(matrixFolder, mode)
    util.makeCleanDir(outfolder)
    outfile = os.path.join(outfolder, "matrix_{}.png".format(mode))
    
    if(mode == "complete"):    
        quantiles = [0, 0.8, 0.97]
        #quantiles = [0.7, 0.8, 0.97]        
        preSamples = 10
        rows, cols = getRowColMetaComplete(neurons, preSamples)        
        D = getMatrixValuesComplete(networkDir, rows, cols, dscFolder, numWorkers)            
    elif(mode == "C2"):        
        quantiles = [0, 0.87, 0.95]        
        rows, cols = getRowColMeta(neurons, mode)
        n = 1000
        rows, cols = sample(rows, cols, n)
        D = getMatrixValuesMP(networkDir, rows, cols, dscFolder, numWorkers)        
    elif(mode == "C2-subset"):
        quantiles = [0, 0.86, 0.955]
        rows, cols = getRowColMeta(neurons, mode)
        n = 1000
        rows, cols = sample(rows, cols, n)
        D = getMatrixValuesMP(networkDir, rows, cols, dscFolder, numWorkers)
    else:
        raise ValueError(mode)

    dataFile = os.path.join(outfolder, "data_raw.csv")
    np.savetxt(dataFile, D, delimiter=",")
    
    colorDict, quantilesProb, quantilesAll = getColorscaleByQuantiles(D, quantiles)
    renderColorscale(os.path.join(outfolder, "colorscale.png"), colorDict, quantilesProb)
    writeColorscale(os.path.join(outfolder, "colorscale.csv"), colorDict)
    writeStats(os.path.join(outfolder, "statistics.txt"), quantiles, quantilesProb, quantilesAll, D, mode)
    
    renderMatrix(D, rows, cols, outfile, colorDict, mode)