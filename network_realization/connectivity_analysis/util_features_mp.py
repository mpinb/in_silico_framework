import os
import sys
import multiprocessing as mp
from ctypes import c_float
import numpy as np

import util
import calc_features_mp
import util_batch
import util_meta
import util_morphology

def loadFeatureComputationData(networkDir):
    data = {}
    data["neurons"] = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    data["neuronsOriginal"] = util_meta.loadNeuronProps(os.path.join(networkDir, "meta", "neurons.csv"))
    data["boutonDensities"] = util_meta.loadBoutonDensityMap(networkDir)    
    grid = util_meta.loadGrid_ixiyiz(os.path.join(networkDir, "grid_50-50-50.csv"))
    data["grid"] = grid
    data["gridCells"] = set(grid.keys())
    data["graphset"] = util_morphology.loadGraphset(networkDir)
    data["pstDensities"] = util_meta.loadPstDensityMap(networkDir)
    return data 


def getPstAll(featureComputationData, networkDir, gridBounds, boundsDescriptor, gridDescriptor, numWorkers, postIds=None):
    numCells = gridBounds["numCells"]    
    pstAllExc = mp.Array(c_float, int(numCells), lock=False)
    pstAllInh = mp.Array(c_float, int(numCells), lock=False)
          
    lock = mp.Lock()
    processes = []    
    outProps = {
        "featureComputationData" : featureComputationData,
        "type" : "pstAll",
        "gridBounds" : gridBounds,
        "pstAllExc" : pstAllExc,
        "pstAllInh" : pstAllInh,
        "lock" : lock,
    }    
    batches = util_batch.getBatchFiles(networkDir, "post", gridDescriptor, boundsDescriptor, "pstAll_{}".format(gridDescriptor), numWorkers, excludeExisting = False, nids = postIds)    
    for batch in batches:
        p = mp.Process(target = calc_features_mp.processBatch, args=(batch, "post", gridDescriptor, "", networkDir, None, outProps,))
        p.start()        
        processes.append(p)
    for p in processes:
        p.join()

    return pstAllExc, pstAllInh


def getPostFeatures(featureComputationData, pstDict, networkDir, gridBounds, boundsDescriptor, gridDescriptor, postIds, pstAllExc, pstAllInh, numWorkers, sliceParams = None):
    postIdsMissing = list(set(postIds) - set(pstDict.keys()))
    if(not postIdsMissing):
        return

    logFolder = makeLogFolder(networkDir)
    
    outPropsPst = {
        "featureComputationData" : featureComputationData,
        "type" : "pst",
        "pstAllExc" : pstAllExc,
        "pstAllInh" : pstAllInh,
        "gridBounds" : gridBounds,        
        "sliceParams" : sliceParams,      
        "featuresPost" : pstDict # neuronId -> { "arrayIndices" : [], "arrayPstExcNorm" : [], "arrayPstInhNorm" : [] }
    }   

    batchesPst = util_batch.getBatchFilesFromIds(networkDir, "pst_{}".format(gridDescriptor), postIdsMissing, numWorkers)
    processes = []    
    for batch in batchesPst:
        p = mp.Process(target=calc_features_mp.processBatch, args=(batch, "post", gridDescriptor, boundsDescriptor, networkDir, None, outPropsPst), kwargs={"logFolder": logFolder})
        p.start()
        processes.append(p)
    for p in processes:
        p.join()         

    return pstDict


def getPreFeatures(featureComputationData, preDict, networkDir, gridBounds, boundsDescriptor, gridDescriptor, preIds, numWorkers, sliceParams = None):
    preIdsMissing = list(set(preIds) - set(preDict.keys()))
    if(not preIdsMissing):
        return

    logFolder = makeLogFolder(networkDir)
   
    outPropsPre = {
        "featureComputationData" : featureComputationData,
        "type" : "pre",
        "gridBounds" : gridBounds,  
        "sliceParams" : sliceParams,         
        "featuresPre" : preDict # neuronId -> { "arrayIndices" : [], "arrayBoutons" : [] }
    }

    batchesPst = util_batch.getBatchFilesFromIds(networkDir, "pre_{}".format(gridDescriptor), preIdsMissing, numWorkers)
    processes = []    
    for batch in batchesPst:
        p = mp.Process(target=calc_features_mp.processBatch, args=(batch, "pre", gridDescriptor, boundsDescriptor, networkDir, None, outPropsPre), kwargs={"logFolder": logFolder})
        p.start()
        processes.append(p)
    for p in processes:
        p.join()         


def numpyToSharedArray(a):    
    aShared = mp.Array(c_float, int(a.size), lock=False)
    for i in range(0,a.size):
        aShared[i] = float(a[i])
    return aShared


def makeLogFolder(networkDir):
    logFolder = os.path.join(networkDir, "log")
    util.makeDir(logFolder)
    return logFolder


def writeFeatures(folder, neuronId_features, isPre):
    for neuronId, features in neuronId_features.items():
        with open(os.path.join(folder, "{}".format(neuronId)), "w") as f:
            n = features["arrayIndices"].size
            if(isPre):
                f.write("cubeId,boutons\n")
            else:
                f.write("cubeId,pstExc,pstExcApical,pstExcBasal,pstExcSoma,pstInh,pstInhApical,pstInhBasal,pstInhSoma\n")
            for i in range(0, n):                
                arrayIndex = features["arrayIndices"][i]
                if(isPre):
                    boutons = features["arrayBoutons"][i]
                    f.write("{},{:E}\n".format(arrayIndex, boutons))
                else:
                    pstExc = features["arrayPstExcNorm"][i]
                    pstExcApical = features["arrayPstExcApicalNorm"][i]
                    pstExcBasal = features["arrayPstExcBasalNorm"][i]
                    pstExcSoma = features["arrayPstExcSomaNorm"][i]
                    pstInh = features["arrayPstInhNorm"][i]
                    pstInhApical = features["arrayPstInhApicalNorm"][i]
                    pstInhBasal = features["arrayPstInhBasalNorm"][i]
                    pstInhSoma = features["arrayPstInhSomaNorm"][i]
                    f.write("{},{:E},{:E},{:E},{:E},{:E},{:E},{:E},{:E}\n".format(arrayIndex, 
                        pstExc, pstExcApical, pstExcBasal, pstExcSoma,
                        pstInh, pstInhApical, pstInhBasal, pstInhSoma))
                