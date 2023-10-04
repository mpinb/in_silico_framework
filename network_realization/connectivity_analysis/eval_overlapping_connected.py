import os
import sys
import glob
import multiprocessing as mp
import numpy as np
import matplotlib.pyplot as plt
from ctypes import c_float
import math

import util
import util_feature_IO
import util_batch
import util_geometry
import util_meta
import util_amira
import constants
import calc_features_mp


def getEmptyStats():
    return {
        "overlapping": 0,
        "connected": 0
    }


def processBatch(batchIndex, results, dscFolder, nids):
    stats = getEmptyStats()
    for i in range(0, len(nids)):
        if(i % 50 == 0):
            print("batch", batchIndex, dscFolder, i, "of", len(nids))
        nid = nids[i]
        filename = os.path.join(dscFolder, "{}_DSC.csv".format(nid))
        if(os.path.exists(filename)):
            dsc = np.loadtxt(filename, skiprows=1, delimiter=",", usecols=1)
            stats["overlapping"] += dsc.size
            prob = 1-np.exp(-dsc)
            stats["connected"] += np.sum(prob)
    results[batchIndex] = stats


def mergeResults(results):
    statsMerged = getEmptyStats()
    for values in results.values():
        statsMerged["overlapping"] += values["overlapping"]
        statsMerged["connected"] += values["connected"]
    return statsMerged


def writeStats(filename, statsOverall):
    with open(filename, "w+") as f:
        f.write("overlapping_pairs,connected_pairs\n")
        f.write("{},{}\n".format(stats["overlapping"], int(stats["connected"])))


def process(networkDir, outfolder, gridDescriptor, numWorkers):
    preIds = util_batch.getC2Presynaptic(networkDir)
    np.random.shuffle(preIds)
    batchesPre = np.array_split(preIds, numWorkers)

    dscFolder = os.path.join(networkDir, "DSC_{}_C2-volume".format(gridDescriptor))

    processes = []
    manager = mp.Manager()
    results = manager.dict()
    for i in range(0, len(batchesPre)):
        p = mp.Process(target=processBatch, args=(i, results, dscFolder, batchesPre[i],))
        processes.append(p)
        p.start()
    for p in processes:
        p.join()

    merged = mergeResults(results)
    return merged


def computeStatsInMemory(batchIndex, results, preIds, postDict, networkDir, gridDescriptor, gridBounds):
    stats = getEmptyStats()        
    postIds = list(postDict.keys())

    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    neuronsOriginal = util_meta.loadNeuronProps(os.path.join(networkDir, "meta", "neurons.csv"))
    boutonDensities = util_meta.loadBoutonDensityMap(networkDir)    
    grid = util_meta.loadGrid_ixiyiz(os.path.join(networkDir, "grid_50-50-50_all.csv"))
    gridCells = set(grid.keys())
    if(os.path.exists(os.path.join(networkDir, "morphologies", "MorphologiesWithNeuronIDs.am"))):
        graphset = util_amira.readSpatialGraphSet(os.path.join(networkDir, "morphologies", "MorphologiesWithNeuronIDs.am"), legacy=True)
    else:
        graphset = util_amira.readSpatialGraphSet(os.path.join(networkDir, "morphologies", "Morphologies.am"), legacy=False)

    outPropsPre = {
        "type" : "pre",
        "gridBounds" : gridBounds,   
        "neuronsOriginal" : neuronsOriginal,        
        "boutonDensities" : boutonDensities,
        "grid" : grid,
        "gridCells" : gridCells,
        "graphset" : graphset,        
        "featuresPre" : None
    }

    postData = {}
    for postId in postIds:        
        postData[postId] = postDict[postId]
    print("copied post data")

    for i in range(0, len(preIds)):
        preId = preIds[i]
        exc = neurons[preId]["cell_type"] != 11
        outPropsPre["neuronId"] = preId
        outPropsPre["featuresPre"] = { preId : None }
        calc_features_mp.processBatch(None, "pre", gridDescriptor, "C2-volume", networkDir, None, outPropsPre)
        
        featuresPre = outPropsPre["featuresPre"]        
        arrayIndicesPre = featuresPre[preId]["arrayIndices"]
        arrayBoutons = featuresPre[preId]["arrayBoutons"]
               
        for j in range(0, len(postIds)):                            
            postId = postIds[j]

            featuresPost = postData[postId]
            arrayIndicesPost = featuresPost["arrayIndices"]
            arrayPstExcNorm = featuresPost["arrayPstExcNorm"]
            arrayPstInhNorm = featuresPost["arrayPstInhNorm"]

            common, commonPreIdx, commonPostIdx = np.intersect1d(arrayIndicesPre, arrayIndicesPost, assume_unique=True, return_indices=True)            
            if(common.size):
                stats["overlapping"] += 1
                if(exc):
                    dsc = np.multiply(arrayBoutons[commonPreIdx], arrayPstExcNorm[commonPostIdx])
                else:
                    dsc = np.multiply(arrayBoutons[commonPreIdx], arrayPstInhNorm[commonPostIdx])
                prob = 1-math.exp(-np.sum(dsc))
                stats["connected"] += prob
        print("batch {}: pre {}/{}".format(batchIndex, i+1, len(preIds)))
    results[batchIndex] = stats


def computeOverlappingDSCInMemory(networkDir, gridDescriptor, gridBounds, pstAllExc, pstAllInh, numWorkers, samplingFactor):
    preIds = util_batch.getC2Presynaptic(networkDir)
    np.random.shuffle(preIds)    
    preIdsSampled = []
    for i in range(0, len(preIds), samplingFactor):
        preIdsSampled.append(preIds[i])

    postIds = util_batch.getC2Postsynaptic(networkDir)
    np.random.shuffle(postIds)
    postIds = postIds
    print("preIds", len(preIdsSampled))
    print("postIds", len(postIds))

    manager = mp.Manager()

    # Post features    
    pstDict = manager.dict()
    outPropsPst = {
        "type" : "pst",
        "pstAllExc" : pstAllExc,
        "pstAllInh" : pstAllInh,
        "gridBounds" : gridBounds,              
        "featuresPost" : pstDict # neuronId -> cube -> (pstNormExc, pstNormInh)
    }   
    batchesPst = util_batch.getBatchFilesFromIds(networkDir, "overlapping_connected_pst_{}".format(gridDescriptor), postIds, numWorkers)
    processes = []    
    for batch in batchesPst:
        p = mp.Process(target=calc_features_mp.processBatch, args=(batch, "post", gridDescriptor, "C2-volume", networkDir, None, outPropsPst))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()           


    # Overlapping / connected
    batchesPre = np.array_split(preIdsSampled, numWorkers)
    results = manager.dict()
    processes = []
    for i in range(0, len(batchesPre)):
        p = mp.Process(target=computeStatsInMemory, args=(i, results, batchesPre[i].tolist(), pstDict, networkDir, gridDescriptor, gridBounds))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()

    statsMerged = mergeResults(results)
    statsMerged["overlapping"] *= samplingFactor
    statsMerged["connected"] *= samplingFactor

    return statsMerged


def processInMemory(networkDir, outfolder, gridDescriptor, numWorkers, samplingFactor):
    # bounds of C2 volume
    boxMin, boxMax = constants.getC2VolumeExt()
    util_geometry.setGridSize(gridDescriptor)
    gridBounds = util_geometry.getGridBounds(boxMin, boxMax)
    print(gridBounds)
    numCells = gridBounds["numCells"]

    # register pstAll
    pstAllExc = mp.Array(c_float, int(numCells), lock=False)
    pstAllInh = mp.Array(c_float, int(numCells), lock=False)
    print("initalized arrays")
    
    lock = mp.Lock()
    processes = []    
    outProps = {
        "type" : "pstAll",
        "gridBounds" : gridBounds,
        "pstAllExc" : pstAllExc,
        "pstAllInh" : pstAllInh,
        "lock" : lock,
    }    
    batches = util_batch.getBatchFiles(networkDir, "post", gridDescriptor, "C2-volume", "overlapping_connected_pstAll_{}".format(gridDescriptor), numWorkers, excludeExisting = False, nids = None)    
    for batch in batches:        
        p = mp.Process(target = calc_features_mp.processBatch, args=(batch, "post", gridDescriptor, "C2-volume", networkDir, None, outProps,))
        p.start()        
        processes.append(p)        
    for p in processes:
        p.join()
   
    sumExc = 0
    sumInh = 0
    for i in range(0,numCells):
        sumExc += pstAllExc[i]
        sumInh += pstAllInh[i]
    print("pst all {}".format(gridDescriptor), sumExc, sumInh)
    
    statsMerged = computeOverlappingDSCInMemory(networkDir, gridDescriptor, gridBounds, pstAllExc, pstAllInh, numWorkers, samplingFactor)
    return statsMerged


def createPlot(outfolder, gridDescriptors):
    volume = np.arange(6)
    overlapping = []
    connected = []
    for gridDescriptor in gridDescriptors:
        D = np.loadtxt(os.path.join(outfolder, "overlapping_connected_{}.csv".format(gridDescriptor)), delimiter=",", skiprows=1, usecols=(0, 1))
        gridSize = util_geometry.gridDescriptorToInt(gridDescriptor)
        overlapping.append(D[0])
        connected.append(D[1])
    idx = np.arange(len(overlapping))
    plt.plot(idx, overlapping, marker="o", label="overlapping cell pairs")
    plt.plot(idx, connected,  marker="o", label="connected cell pairs")    
    plt.xlabel("overlap volume (min: 1-1-1; max 100-100-100)")
    plt.legend()
    plt.yscale("log")
    plt.savefig(os.path.join(outfolder, "overlapping_connected.png"))


def printUsageAndExit():
    print("eval_overlapping_connected.py network-dir aggregate grid-descriptor [num-workers]")
    print("eval_overlapping_connected.py network-dir plot")
    print()
    exit()


if __name__ == "__main__":
    if(len(sys.argv) < 3):
        printUsageAndExit()
    networkDir = sys.argv[1]
    mode = sys.argv[2]
    if(mode == "aggregate"):
        gridDescriptor = sys.argv[3]
        if(len(sys.argv) == 5):
            numWorkers = int(sys.argv[4])
        else:
            numWorkers = 10
    elif(mode == "plot"):
        if(len(sys.argv) != 3):
            printUsageAndExit()
    else:
        printUsageAndExit()
    
    outfolder = os.path.join(networkDir, "eval", "overlapping_connected")

    if(mode == "aggregate"):
        util.makeDir(outfolder)                  
        stats = processInMemory(networkDir, outfolder, gridDescriptor, numWorkers, 1)            
        writeStats(os.path.join(outfolder, "overlapping_connected_{}.csv".format(gridDescriptor)), stats)
    elif(mode == "plot"):
        gridDescriptorsPlot = ["1-1-1", "5-5-5", "10-10-10", "25-25-25", "50-50-50", "100-100-100"]
        createPlot(outfolder, gridDescriptorsPlot)
    else:
        raise RuntimeError("invalid mode: {}".format(mode))
