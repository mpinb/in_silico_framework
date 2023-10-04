import os
import util
import numpy as np
import multiprocessing as mp


def loadPstAll(networkDir, boundsDescriptor):
    pstAllExcFile = os.path.join(networkDir, "cache", "pstAll", boundsDescriptor, "pstAllExc")
    pstAllInhFile = os.path.join(networkDir, "cache", "pstAll", boundsDescriptor, "pstAllInh")
    
    if(not os.path.exists(pstAllExcFile)):
        raise RuntimeError("File not found: {}".format(pstAllExcFile))
    if(not os.path.exists(pstAllInhFile)):
        raise RuntimeError("File not found: {}".format(pstAllExcFile))

    pstAllExc = np.loadtxt(pstAllExcFile)
    pstAllInh = np.loadtxt(pstAllInhFile)

    return pstAllExc, pstAllInh


def getFileName(cacheDir, isPresynaptic, sliceIndex, nid):
    compartment = "axon"
    if(not isPresynaptic):
        compartment = "dendrite"
    if(sliceIndex is None):
        return os.path.join(cacheDir, "{}".format(compartment), "{}.csv".format(nid))
    else:
        return os.path.join(cacheDir, "{}_slice-{}".format(compartment, sliceIndex), "{}.csv".format(nid))


def writePreFeatures(filename, features):
    arrayIndices = features["arrayIndices"]
    arrayBoutons = features["arrayBoutons"]
    n = arrayIndices.size

    with open(filename, "w+") as f:
        for i in range(0,n):
            f.write("{},{:.8e}\n".format(arrayIndices[i], arrayBoutons[i]))


def readPreFeatures(filename):
    features = {}
    with open(filename) as f:
        lines = f.readlines()
        n = len(lines)
        arrayIndices = np.zeros(n, dtype=int)
        arrayBoutons = np.zeros(n, dtype=np.float32)
        for i in range(0,n):
            parts = lines[i].rstrip().split(",")
            arrayIndices[i] = int(parts[0])
            arrayBoutons[i] = float(parts[1])
        features["arrayIndices"] = arrayIndices
        features["arrayBoutons"] = arrayBoutons
    return features


def writePostFeatures(filename, features):
    arrayIndices = features["arrayIndices"]
    arrayPstExcNorm = features["arrayPstExcNorm"]
    arrayPstInhNorm = features["arrayPstInhNorm"]
    n = arrayIndices.size

    with open(filename, "w+") as f:
        for i in range(0,n):
            f.write("{},{:.8e},{:.8e}\n".format(arrayIndices[i], arrayPstExcNorm[i], arrayPstInhNorm[i]))


def readPostFeatures(filename):
    features = {}
    with open(filename) as f:
        lines = f.readlines()
        n = len(lines)
        arrayIndices = np.zeros(n, dtype=int)
        arrayPstExcNorm = np.zeros(n, dtype=np.float32)
        arrayPstInhNorm = np.zeros(n, dtype=np.float32)
        for i in range(0,n):
            parts = lines[i].rstrip().split(",")
            arrayIndices[i] = int(parts[0])
            arrayPstExcNorm[i] = float(parts[1])
            arrayPstInhNorm[i] = float(parts[2])
        features["arrayIndices"] = arrayIndices
        features["arrayPstExcNorm"] = arrayPstExcNorm
        features["arrayPstInhNorm"] = arrayPstInhNorm        
    return features


def saveBatch(cacheDir, sliceIndex, featuresPerNeuron, isPresynaptic):
    for nid, features in featuresPerNeuron.items():
        filename = getFileName(cacheDir, isPresynaptic, sliceIndex, nid)
        if(not os.path.exists(filename)):
            if(isPresynaptic):
                writePreFeatures(filename, features)
            else:
                writePostFeatures(filename, features)


def initFolders(cacheDir, includeSlice = True):
    util.makeCleanDir(os.path.join(cacheDir, "axon"))
    util.makeCleanDir(os.path.join(cacheDir, "dendrite"))
    if(includeSlice):
        for i in range(0,20):
            util.makeCleanDir(os.path.join(cacheDir, "axon_slice-{}".format(i)))
            util.makeCleanDir(os.path.join(cacheDir, "dendrite_slice-{}".format(i)))    


def loadFromCache(ids, isPresynaptic, cacheDir, sliceIndex = None):
    manager = mp.Manager()
    featuresPerNeuron = manager.dict()

    k = 0
    for nid in ids:
        filename = getFileName(cacheDir, isPresynaptic, sliceIndex, nid)
        if(os.path.exists(filename)):
            if(isPresynaptic):
                featuresPerNeuron[nid] = readPreFeatures(filename)
            else:
                featuresPerNeuron[nid] = readPostFeatures(filename)
        if(k % 1000 == 0):
            print("load from cache {}/{}".format(k+1,len(ids)))
        k += 1
    return featuresPerNeuron


def getSharedDict():
    manager = mp.Manager()
    return manager.dict()
