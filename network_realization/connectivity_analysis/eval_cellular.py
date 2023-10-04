import os
import sys
import numpy as np
import multiprocessing as mp
from ctypes import c_float
import json
import math
import matplotlib.pyplot as plt

import util
import util_empirical
import util_meta
import util_filter
import util_geometry
import constants
import util_features_mp
import util_stats
import util_cache

def getDefaultSlices():
    slices = []
    x0 = -145
    dx = -20
    width = 300
    tissueDepth = (31, 130)
    for i in range(0, 10):
        xlow = x0 + i * dx
        xhigh = xlow + width

        sliceLow = {
            "sliceRange": (xlow, xhigh),
            "somaRange": (xlow + tissueDepth[0], xlow + tissueDepth[1]),
            "compartment" : ["BasalDendrite", "Soma", "Axon"]
        }
        slices.append(sliceLow)

        sliceHigh = {
            "sliceRange": (xlow, xhigh),
            "somaRange": (xhigh - tissueDepth[1], xhigh - tissueDepth[0]),
            "compartment" : ["BasalDendrite", "Soma", "Axon"]
        }
        slices.append(sliceHigh)

    return slices


def applyFilter(neurons, layer, celltype, onlySeptum, sliceSpec):
    if(celltype == "VPM"):
        spec = util_filter.getVPMFilter()
    else:
        spec = util_filter.getDefaultFilter()
        if(onlySeptum):
            spec["region_whitelist"] = ["S1_Septum_C2"]
        else:
            spec["region_whitelist"] = ["C2", "S1_Septum_C2"]

        layerDepths = constants.getLayerDepths()
        if(layer not in layerDepths):
            raise ValueError(layer)
        else:
            spec["cortical_depth"] = layerDepths[layer]

        if(celltype == "EXC"):
            spec["celltype_blacklist"] = ["INH"]
        elif(celltype in constants.getCellTypesExc(includeVPM=False)):
            spec["celltype_whitelist"] = [celltype]
        else:
            raise ValueError(celltype)

        if(sliceSpec is not None):
            spec["range_x"] = sliceSpec["somaRange"]

    nids = util_filter.filterNIDs(neurons, spec)
    return nids


def filterIdsSinglePopulation(neurons, userFilter, sliceSpec):
    userFilter["range_x"] = list(sliceSpec["somaRange"])
    if("region_whitelist" in userFilter):
        regionFilter = {}
        regionFilter["region_whitelist"] = userFilter["region_whitelist"]
        return util_filter.filterNIDsTwoRounds(neurons, regionFilter, userFilter)
    else:
        return util_filter.filterNIDs(neurons, userFilter) 


def filterIdsDefaultSlicesOnline(neurons, preFilter, postFilter, returnMerged = True):
    print("filterIdsDefaultSlicesOnline")
    slices = getDefaultSlices()
    preIdsMerged = set()
    postIdsMerged = set()
    preIdsPerSlice = []
    postIdsPerSlice = []
    for i in range(0, len(slices)):
        print("filter slice", i)
        sliceSpec = slices[i]
        preIds = filterIdsSinglePopulation(neurons, preFilter, sliceSpec)
        postIds = filterIdsSinglePopulation(neurons, postFilter, sliceSpec)
        preIdsMerged |= preIds
        postIdsMerged |= postIds   
        preIdsPerSlice.append(preIds)
        postIdsPerSlice.append(postIds)
    if(returnMerged):
        return preIdsMerged, postIdsMerged
    else:
        return preIdsPerSlice, postIdsPerSlice


def filterIdsBatch(publications, publicationIndices, networkDir, outputDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    slices = getDefaultSlices()

    for pubIndex in publicationIndices:
        publication = publications[pubIndex]

        publicationId = publication["ID"]
        measurementType = publication["type"]
        preLayer = publication["pre_layer"]
        postLayer = publication["post_layer"]
        preType = publication["pre_type"]
        postType = publication["post_type"]
        onlySeptum = publication["only_septum"] == "yes"

        if(measurementType == "connection_probability_invivo"):
            preIds = applyFilter(neurons, preLayer, preType, onlySeptum, None)
            postIds = applyFilter(neurons, postLayer, postType, onlySeptum, None)

            filenamePre = os.path.join(outputDir, "{}_pre.txt".format(publicationId))
            filenamePost = os.path.join(outputDir, "{}_post.txt".format(publicationId))

            util.writeIdsToFile(filenamePre, preIds)
            util.writeIdsToFile(filenamePost, postIds)

        elif(measurementType == "connection_probability_invitro"):
            for i in range(0, len(slices)):
                preIds = applyFilter(neurons, preLayer, preType, onlySeptum, slices[i])
                postIds = applyFilter(neurons, postLayer, postType, onlySeptum, slices[i])

                filenamePre = os.path.join(outputDir, "{}_pre_slice-{}.txt".format(publicationId, i))
                filenamePost = os.path.join(outputDir, "{}_post_slice-{}.txt".format(publicationId, i))

                util.writeIdsToFile(filenamePre, preIds)
                util.writeIdsToFile(filenamePost, postIds)
        else:
            raise ValueError(measurementType)


def filterIds(networkDir, outputDir, numWorkers):
    publicationsFile = os.path.join(networkDir, "empirical_data.json")
    publications = util_empirical.loadPublications(publicationsFile, extend_sort=True)

    publicationIndices = np.arange(len(publications))
    batches = np.array_split(publicationIndices, numWorkers)

    processes = []
    for batch in batches:
        p = mp.Process(target=filterIdsBatch, args=(publications, batch, networkDir, outputDir))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()


def calcConnectivityBatch(probabilities, preFeatures, postFeatures, preIds, preIndices, postIds, neurons):
    nPre = len(preIndices)
    nPost = len(postIds)

    # local copy from shared dict
    postData = {}
    for postId in postIds:
        postData[postId] = postFeatures[postId]

    for i in range(0, nPre):
        preIdx = preIndices[i]
        preId = preIds[preIdx]
        exc = neurons[preId]["cell_type"] != 11

        featuresPre = preFeatures[preId]
        arrayIndicesPre = featuresPre["arrayIndices"]
        arrayBoutons = featuresPre["arrayBoutons"]

        for j in range(0, nPost):
            postId = postIds[j]

            idx_ij = preIdx * nPost + j
            
            if(preId == postId):

                probabilities[idx_ij] = -1
            
            else:

                featuresPost = postData[postId]
                arrayIndicesPost = featuresPost["arrayIndices"]
                arrayPstExcNorm = featuresPost["arrayPstExcNorm"]
                arrayPstInhNorm = featuresPost["arrayPstInhNorm"]

                common, commonPreIdx, commonPostIdx = np.intersect1d(arrayIndicesPre, arrayIndicesPost, assume_unique=True, return_indices=True)
                if(common.size):

                    if(exc):
                        dsc = np.multiply(arrayBoutons[commonPreIdx], arrayPstExcNorm[commonPostIdx])
                    else:
                        dsc = np.multiply(arrayBoutons[commonPreIdx], arrayPstInhNorm[commonPostIdx])

                    prob = 1-math.exp(-np.sum(dsc))                    
                    probabilities[idx_ij] = prob


def getIdsArray(preIds, postIds):
    idsArray = np.zeros(shape=(len(preIds) * len(postIds), 2), dtype=int)
    k = 0
    for preId in preIds:
        for postId in postIds:
            if(preId == postId):
                idsArray[k, 0] = -1
            else:
                idsArray[k, 0] = preId
                idsArray[k, 1] = postId
            k +=1 

    validRows = idsArray[:,0] >= 0
    idsArray = idsArray[validRows, :]

    return idsArray

def getIndices(preIds, postIds):
    nPre = len(preIds)
    nPost = len(postIds)
    nPairs = nPre * nPost    

    indices = -1 * np.ones((nPairs,2), dtype=int)    
    for i in range(0, len(preIds)):
        for j in range(0, len(postIds)):
            idx = i * nPost + j
            indices[idx,0] = preIds[i]
            indices[idx,1] = postIds[j]
    return indices


def calcConnectivity(preFeatures, postFeatures, preIds, postIds, neurons, numWorkers, probabilitiesOnly = False):
    nPre = len(preIds)
    nPost = len(postIds)
    nPairs = nPre * nPost    

    probabilitiesShared = mp.Array(c_float, nPairs, lock=False)
    preIndices = np.arange(nPre)
    batches = np.array_split(preIndices, numWorkers)

    processes = []
    for batch in batches:
        p = mp.Process(target=calcConnectivityBatch, args=(probabilitiesShared, preFeatures, postFeatures, preIds, batch, postIds, neurons))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()

    probabilitiesUnfiltered = np.array(probabilitiesShared)
    probabilities = probabilitiesUnfiltered[probabilitiesUnfiltered >= 0] # filter self-connections
    
    if(probabilitiesOnly):        
            indices = getIndices(preIds, postIds)
            probabilitiesUnfiltered[probabilitiesUnfiltered == -1] = 0 # set self-connections to zero
            return probabilities, probabilitiesUnfiltered, indices        
    else:
        stats = {
            "nPre": len(preIds),
            "nPost": len(postIds),
            "avg": float(np.mean(probabilities)),
            "std": float(np.std(probabilities))
        }
        histogram = util_stats.probabilityArrayToHistogram(probabilities)

        idsArray = getIdsArray(preIds, postIds)

        return stats, histogram, probabilities, idsArray


def writeConnectivityStats(outfolder, publicationId, stats, histogram, probabilitiesFlat, idsArray, sliceIndex=None):
    if(sliceIndex is not None):
        sliceDescriptor = "slice-{}_".format(sliceIndex)
    else:
        sliceDescriptor = ""

    statsFile = os.path.join(outfolder, "{}_{}stats.json".format(publicationId, sliceDescriptor))
    with open(statsFile, "w+") as f:
        json.dump(stats, f)

    histogramFile = os.path.join(outfolder, "{}_{}probability_histogram.txt".format(publicationId, sliceDescriptor))
    np.savetxt(histogramFile, histogram)

    probabilitiesFile = os.path.join(outfolder, "{}_{}probabilities_flat.txt".format(publicationId, sliceDescriptor))
    np.savetxt(probabilitiesFile, probabilitiesFlat)

    idsFile = os.path.join(outfolder, "{}_{}ids.csv".format(publicationId, sliceDescriptor))
    np.savetxt(idsFile, idsArray, fmt="%d", delimiter=",")


def loadPstAll(cacheDir):
    pstExcFile = os.path.join(cacheDir, "pstAllExc")
    pstInhFile = os.path.join(cacheDir, "pstAllInh")
    if(not os.path.exists(pstExcFile)):
        return None, None

    pstAllExc = np.loadtxt(pstExcFile)
    pstAllInh = np.loadtxt(pstInhFile)

    pstAllExcShared = util_features_mp.numpyToSharedArray(pstAllExc)
    pstAllInhShared = util_features_mp.numpyToSharedArray(pstAllInh)
    return pstAllExcShared, pstAllInhShared


def savePstAll(cacheDir, pstAllExc, pstAllInh):
    pstExcFile = os.path.join(cacheDir, "pstAllExc")
    pstInhFile = os.path.join(cacheDir, "pstAllInh")

    pstAllExcNumpy = np.array(pstAllExc)
    pstAllInhNumpy = np.array(pstAllInh)

    np.savetxt(pstExcFile, pstAllExcNumpy)
    np.savetxt(pstInhFile, pstAllInhNumpy)


def initCache(numSlices):
    manager = mp.Manager()
    preCache = {}  # sliceIndex -> preFeatures
    postCache = {}  # sliceIndex -> postFeatures
    for i in range(-1, numSlices):
        preCache[i] = manager.dict()
        postCache[i] = manager.dict()
    return preCache, postCache


def computeConnectivity(networkDir, idsDir, cacheDir, outfolder, numWorkers):

    # shared data
    gridDescriptor = "50-50-50"
    boundsDescriptor = "cellular-connectivity-volume"
    util_geometry.setGridSize(gridDescriptor)
    boxMin, boxMax = constants.getCellularConnectivityVolume()
    gridBounds = util_geometry.getGridBounds(boxMin, boxMax)
    slices = getDefaultSlices()
    featureComputationData = util_features_mp.loadFeatureComputationData(networkDir)

    # pstAll
    pstAllExc, pstAllInh = loadPstAll(cacheDir)
    if(pstAllExc is None):
        pstAllExc, pstAllInh = util_features_mp.getPstAll(featureComputationData, networkDir, gridBounds, boundsDescriptor, gridDescriptor, numWorkers)
        savePstAll(cacheDir, pstAllExc, pstAllInh)

    # publications
    publicationsFile = os.path.join(networkDir, "empirical_data.json")
    publications = util_empirical.loadPublications(publicationsFile, extend_sort=True)

    lastPreLayer = ""
    for publication in publications:

        publicationId = publication["ID"]
        measurementType = publication["type"]
        selectionDescriptor = publication["selection_descriptor"]
        preLayer = publication["pre_layer"]

        if(preLayer != lastPreLayer):
            preCache, postCache = initCache(20)
            lastPreLayer = preLayer

        if(measurementType == "connection_probability_invivo"):
            sliceIndex = -1

            fileIdsPre = os.path.join(idsDir, "{}_pre.txt".format(publicationId))
            fileIdsPost = os.path.join(idsDir, "{}_post.txt".format(publicationId))

            preIds = util.loadIdsFromFile(fileIdsPre)
            postIds = util.loadIdsFromFile(fileIdsPost)

            preFeatures = preCache[sliceIndex]
            postFeatures = postCache[sliceIndex]
            util_features_mp.getPreFeatures(featureComputationData, preFeatures, networkDir, gridBounds, boundsDescriptor, gridDescriptor, preIds, numWorkers, sliceParams=None)
            util_features_mp.getPostFeatures(featureComputationData, postFeatures, networkDir, gridBounds, boundsDescriptor,
                                             gridDescriptor, postIds, pstAllExc, pstAllInh, numWorkers, sliceParams=None)
            util_cache.saveBatch(cacheDir, None, preFeatures, True)
            util_cache.saveBatch(cacheDir, None, postFeatures, False)
            stats, histogram, probabilitiesFlat, idsArray = calcConnectivity(preFeatures, postFeatures, preIds, postIds, featureComputationData["neurons"], numWorkers)
            writeConnectivityStats(outfolder, publicationId, stats, histogram, probabilitiesFlat, idsArray)

            print("processed", selectionDescriptor, len(preIds), len(postIds), len(preIds) * len(postIds), stats["avg"])
        elif(measurementType == "connection_probability_invitro"):            
            for i in range(0, len(slices)):
                sliceParams = slices[i]

                fileIdsPre = os.path.join(idsDir, "{}_pre_slice-{}.txt".format(publicationId, i))
                fileIdsPost = os.path.join(idsDir, "{}_post_slice-{}.txt".format(publicationId, i))

                preIds = util.loadIdsFromFile(fileIdsPre)
                postIds = util.loadIdsFromFile(fileIdsPost)
                
                preFeatures = preCache[i]
                postFeatures = postCache[i]
                util_features_mp.getPreFeatures(featureComputationData, preFeatures, networkDir, gridBounds, boundsDescriptor, gridDescriptor, preIds, numWorkers, sliceParams = sliceParams)        
                util_features_mp.getPostFeatures(featureComputationData, postFeatures, networkDir, gridBounds, boundsDescriptor, gridDescriptor, postIds, pstAllExc, pstAllInh, numWorkers, sliceParams = sliceParams)
                
                util_cache.saveBatch(cacheDir, i, preFeatures, True)
                util_cache.saveBatch(cacheDir, i, postFeatures, False)
                stats, histogram, probabilitiesFlat, idsArray = calcConnectivity(preFeatures, postFeatures, preIds, postIds, featureComputationData["neurons"], numWorkers)                
                writeConnectivityStats(outfolder, publicationId, stats, histogram, probabilitiesFlat, idsArray, sliceIndex = i)
            
                print("processed", selectionDescriptor, "slice-{}".format(i), len(preIds), len(postIds), len(preIds) * len(postIds), stats["avg"])            
        else:
            raise ValueError(measurementType)


def checkExist(filenames):
    for filename in filenames:
        if(not os.path.exists(filename)):
            return False
    return True


def getFilenames(connectivityDir, publicationId, measurementType):
    numSlices = 20

    filenames = {
        "stats" : [],
        "probabilities_flat" : [],
        "histograms" : [],
        "ids" : []
    }
    if(measurementType == "connection_probability_invivo"):
        filenames["stats"].append(os.path.join(connectivityDir, "{}_stats.json".format(publicationId)))
        filenames["probabilities_flat"].append(os.path.join(connectivityDir, "{}_probabilities_flat.txt".format(publicationId)))
        filenames["histograms"].append(os.path.join(connectivityDir, "{}_probability_histogram.txt".format(publicationId)))
        filenames["ids"].append(os.path.join(connectivityDir, "{}_ids.csv".format(publicationId)))
    elif(measurementType == "connection_probability_invitro"):
        for i in range(0, numSlices):
            filenames["stats"].append(os.path.join(connectivityDir, "{}_slice-{}_stats.json".format(publicationId, i)))
            filenames["probabilities_flat"].append(os.path.join(connectivityDir, "{}_slice-{}_probabilities_flat.txt".format(publicationId, i)))
            filenames["histograms"].append(os.path.join(connectivityDir, "{}_slice-{}_probability_histogram.txt".format(publicationId, i)))
            filenames["ids"].append(os.path.join(connectivityDir, "{}_slice-{}_ids.csv".format(publicationId, i)))
    else:
        raise ValueError(measurementType)

    complete = checkExist(filenames["stats"]) and checkExist(filenames["probabilities_flat"]) and checkExist(filenames["histograms"]) 

    return filenames, complete


def readSingleStats(filename):
    with open(filename) as f:
        stats = json.load(f)
    return stats["avg"], stats["std"]


def getFlattenedProbability(filenames):
    stat = util_stats.getStatEmptyStatVector()
    for filename in filenames:
        probabilities = np.loadtxt(filename)
        for value in probabilities:
            util_stats.updateStat(stat, value)
    results = util_stats.evalStat(stat)
    return results["average"], results["stdev"]


def getSubsampledProbability(filenames):
    probsSubsampled = []
    numSubsamples = 50
    for filename in filenames:
        probabilities = np.loadtxt(filename)
        idx = np.arange(probabilities.size)
        np.random.shuffle(idx)
        probsSampled = probabilities[idx[0:numSubsamples]]
        probsSubsampled.extend(probsSampled.tolist())
    
    synapses = np.random.poisson(probsSubsampled)
    nConnected = np.count_nonzero(synapses)
    return nConnected / len(probsSubsampled)


def getMergedHistogram(filenames):
    D = np.loadtxt(filenames[0])
    for i in range(1, len(filenames)):
        D += np.loadtxt(filenames[i])
    return D


def getAggregatedValues(filenames):
    statsFiles = filenames["stats"]
    probabilitiesFlatFiles = filenames["probabilities_flat"]
    histogramFiles = filenames["histograms"]
    n = len(statsFiles)

    scalarStats = np.zeros(shape=(n,2))
    for i in range(0, n):
        avg, std = readSingleStats(statsFiles[i])
        scalarStats[i, 0]  = avg
        scalarStats[i, 1]  = std

    scalarStatsFlat = np.zeros(3)
    scalarStatsFlat[0] = getFlattenedProbability(probabilitiesFlatFiles)[0]    
    scalarStatsFlat[1] = getFlattenedProbability(probabilitiesFlatFiles)[1]    
    scalarStatsFlat[2] = getSubsampledProbability(probabilitiesFlatFiles)

    histogram = getMergedHistogram(histogramFiles)

    return np.mean(scalarStats, axis=0), scalarStatsFlat, histogram


def computeStatsBatch(results, publications, publicationIndices, connectivityDir):    
    
    for publicationIndex in publicationIndices:

        result = {}
        
        publication = publications[publicationIndex]        
        selectionDescriptor = publication["selection_descriptor"].replace("-->","_")
        publicationId = publication["ID"]
        authorYear = util_empirical.getFirstAuthorYearDescriptor(publication)
        measurementType = publication["type"]
                
        empiricalValue = publication["cp_empirical"] / 100
        filenames, complete = getFilenames(connectivityDir, publicationId, measurementType)

        result["empirical"] = empiricalValue
        result["complete"] = complete

        if(complete):
            scalarStats, scalarStatsFlat, histogram = getAggregatedValues(filenames)
            result["scalarStats"] = scalarStats
            result["scalarStatsFlat"] = scalarStatsFlat
            result["histogram"] = histogram

            print(selectionDescriptor, empiricalValue, scalarStats[0])
        
        results[publicationId] = result


def computeStats(networkDir, connectivityDir, statsDir, numWorkers):
    publicationsFile = os.path.join(networkDir, "empirical_data.json")
    publications = util_empirical.loadPublications(publicationsFile, extend_sort=True)

    plotData = []
    manager = mp.Manager()
    results = manager.dict()

    publicationIndices = np.arange(len(publications))
    batches = np.array_split(publicationIndices, numWorkers)

    processes = []
    for batch in batches:
        p = mp.Process(target=computeStatsBatch, args=(results, publications, batch, connectivityDir))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()

    summaryFile = os.path.join(statsDir, "summary.csv")
    with open(summaryFile, "w") as f:
        f.write("descriptor,author_year,ID,empirical,avg_slices_individual,std_slices_individual,avg_slices_merged,std_slices_merged,avg_discrete_subsamples\n")
        
        for publication in publications:

            publicationId = publication["ID"]
            authorYear = util_empirical.getFirstAuthorYearDescriptor(publication)            
            selectionDescriptor = publication["selection_descriptor"].replace("-->","_")

            result = results[publicationId]
            if(result["complete"]):
                empiricalValue = result["empirical"]
                scalarStats = result["scalarStats"]
                scalarStatsFlat = result["scalarStatsFlat"]
                histogram = result["histogram"]
            
                line = "{},{},{},{:.4f},{:.4f},{:.4f},{:.4f},{:.4f},{:.4f}".format(selectionDescriptor, authorYear, publicationId,
                    empiricalValue, scalarStats[0], scalarStats[1], scalarStatsFlat[0], scalarStatsFlat[1], scalarStatsFlat[2])
                f.write(line + "\n")
                print(line)
                
                np.savetxt(os.path.join(statsDir, "{}_histogram.txt".format(selectionDescriptor)), histogram)
        
                plotData.append([scalarStats[0], empiricalValue])

    return np.array(plotData)


def readSummaryFile(filename):
    data = {}
    with open(filename) as f:
        lines = f.readlines()
        for i in range(1, len(lines)):
            parts = lines[i].rstrip().split(",")
            publicationId = parts[2]
            data[publicationId] = {
                "descriptor" : parts[0],
                "avg_slices_merged" : float(parts[6]),
                "std_slices_merged" : float(parts[7])
            }
    return data
        

def plotStats(statsDir, plotData):
    plt.scatter(plotData[:,0], plotData[:,1])
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    plt.xlabel("model")
    plt.ylabel("empirical")
    plt.gca().set_aspect('equal', adjustable='box')
    plt.savefig(os.path.join(statsDir, "probabilities.png"))


def writeDSC(dscSubfolder, ids, probabilities):
    if(ids.shape[0] != probabilities.size):
        raise RuntimeError("size mismatch")
    n = probabilities.size

    dsc = -np.log(1-probabilities)

    uniquePreIds = np.unique(ids[:,0])
    for preId in uniquePreIds:
        idx = ids[:,0] == preId
        postIds = ids[idx,1]
        sortIdx = np.argsort(postIds)
        postIds = postIds[sortIdx]
        dscValues = dsc[idx]
        dscValues = dscValues[sortIdx]
        with open(os.path.join(dscSubfolder, "{}_DSC.csv".format(preId)), "w") as f:
            f.write("post_id,dsc\n")
            for i in range(0, postIds.size):
                f.write("{},{:.12E}\n".format(postIds[i], dscValues[i]))


def computeDSC(networkDir, connectivityDir, dscDir, publicationId = "3410f9b8-f11a-49c2-b033-f63eb98b2dc9"):    

    publicationsFile = os.path.join(networkDir, "empirical_data.json")
    publications = util_empirical.loadPublications(publicationsFile, extend_sort=True)
    publication = util_empirical.getPublication(publications, publicationId)
    measurementType = publication["type"]

    filenames, complete = getFilenames(connectivityDir, publicationId, measurementType)
    if(not complete):
        raise RuntimeError

    probabilityFlatFiles = filenames["probabilities_flat"]
    idsFiles = filenames["ids"]
    n = len(probabilityFlatFiles)
    for i in range(0,n):
        if(n > 1):
            subfolderName = os.path.join(dscDir, "{}_slice-{}".format(publicationId, i))
        else:
            subfolderName = os.path.join(dscDir, publicationId)
        util.makeDir(subfolderName)

        probabilities = np.loadtxt(probabilityFlatFiles[i])
        ids = np.loadtxt(idsFiles[i], delimiter=",", dtype=int)
        writeDSC(subfolderName, ids, probabilities)


def printUsageAndExit():
    print("eval_cellular.py network-dir mode [num-workers]")
    print()
    print("mode:    filter-ids, compute-connectivity, compute-stats, compute-dsc")
    exit()


if __name__ == "__main__":
    if(len(sys.argv) not in [3, 4]):
        printUsageAndExit()
    networkDir = sys.argv[1]
    mode = sys.argv[2]
    if(len(sys.argv) == 4):
        numWorkers = int(sys.argv[3])
    else:
        numWorkers = mp.cpu_count()

    outputDir = os.path.join(networkDir, "eval", "cellular_connectivity")
    util.makeDir(outputDir)

    idsDir = os.path.join(outputDir, "ids")
    cacheDir = os.path.join(outputDir, "cache")
    connectivityDir = os.path.join(outputDir, "connectivity")
    statsDir = os.path.join(outputDir, "stats")
    dscDir = os.path.join(outputDir, "dsc")

    if(mode == "filter-ids"):
        util.makeCleanDir(idsDir)
        util.makeCleanDir(cacheDir)
        util.makeCleanDir(connectivityDir)
        filterIds(networkDir, idsDir, numWorkers)
    elif(mode == "compute-connectivity"):
        util_cache.initFolders(cacheDir)
        util.makeCleanDir(connectivityDir)
        computeConnectivity(networkDir, idsDir, cacheDir, connectivityDir, numWorkers)
    elif(mode == "compute-stats"):
        util.makeCleanDir(statsDir)
        plotData = computeStats(networkDir, connectivityDir, statsDir, numWorkers)
        plotStats(statsDir, plotData)
    elif(mode == "compute-dsc"):
        util.makeCleanDir(dscDir)
        computeDSC(networkDir, connectivityDir, dscDir)
    else:
        raise ValueError(mode)
