import os
import sys
import multiprocessing as mp
import numpy as np
import json
import traceback
import warnings

import util
import util_meta
import util_filter
import motif_combinations
import constants
import util_intersomatic_distance

def getMotifIndex_16():
    return {
        (0,0,0,0,0,0) : 16, # no edges        
        (1,0,0,0,0,0) : 15, # A -> B
        (0,1,0,0,0,0) : 15, # B -> A
        (0,0,1,0,0,0) : 15, # A -> C
        (0,0,0,1,0,0) : 15, # C -> A
        (0,0,0,0,1,0) : 15, # B -> C
        (0,0,0,0,0,1) : 15, # C -> B
        (1,1,0,0,0,0) : 14, # A <-> B
        (0,0,1,1,0,0) : 14, # A <-> C
        (0,0,0,0,1,1) : 14, # B <-> C
        (1,0,0,0,1,0) : 13, # A -> B -> C
        (0,0,1,0,0,1) : 13, # A -> C -> B
        (0,1,1,0,0,0) : 13, # B -> A -> C
        (0,0,0,1,1,0) : 13, # B -> C -> A
        (1,0,0,1,0,0) : 13, # C -> A -> B 
        (0,1,0,0,0,1) : 13, # C -> B -> A 
        (1,0,1,0,0,0) : 12, # A -> B, C
        (0,1,0,0,1,0) : 12, # B -> A, C
        (0,0,0,1,0,1) : 12, # C -> A, B
        (0,0,1,0,1,0) : 11, # A, B -> C
        (1,0,0,0,0,1) : 11, # A, C -> B
        (0,1,0,1,0,0) : 11, # B, C -> A
        (1,1,0,1,0,0) : 10, # A <-> B; C -> A
        (1,1,0,0,0,1) : 10, # A <-> B; C -> B
        (0,1,1,1,0,0) : 10, # A <-> C; B -> A
        (0,0,1,1,1,0) : 10, # A <-> C; B -> C
        (1,0,0,0,1,1) : 10, # B <-> C; A -> B
        (0,0,1,0,1,1) : 10, # B <-> C; A -> C
        (1,1,1,0,0,0) : 9,  # A <-> B; A -> C
        (1,1,0,0,1,0) : 9,  # A <-> B; B -> C
        (1,0,1,1,0,0) : 9,  # A <-> C; A -> B
        (0,0,1,1,0,1) : 9,  # A <-> C; C -> B
        (0,1,0,0,1,1) : 9,  # B <-> C; B -> A
        (0,0,0,1,1,1) : 9,  # B <-> C; C -> A
        (1,1,1,1,0,0) : 8,  # A <-> B; A <-> C
        (1,1,0,0,1,1) : 8,  # A <-> B; B <-> C
        (0,0,1,1,1,1) : 8,  # A <-> C; B <-> C
        (1,0,0,1,1,0) : 7,  # A -> B -> C -> A
        (0,1,1,0,0,1) : 7,  # A -> C -> B -> A
        (1,0,1,0,1,0) : 6,  # A -> B,C; B -> C
        (1,0,1,0,0,1) : 6,  # A -> B,C; C -> B
        (0,1,1,0,1,0) : 6,  # B -> A,C; A -> C
        (0,1,0,1,1,0) : 6,  # B -> A,C; C -> A
        (1,0,0,1,0,1) : 6,  # C -> A,B; A -> B
        (0,1,0,1,0,1) : 6,  # C -> A,B; B -> A
        (1,1,1,0,0,1) : 5,  # A <-> B; A -> C -> B
        (1,1,0,1,1,0) : 5,  # A <-> B; B -> C -> A
        (1,0,1,1,1,0) : 5,  # A <-> C; A -> B -> C
        (0,1,1,1,0,1) : 5,  # A <-> C; C -> B -> A
        (0,1,1,0,1,1) : 5,  # B <-> C; B -> A -> C
        (1,0,0,1,1,1) : 5,  # B <-> C; C -> A -> B
        (1,1,0,1,0,1) : 4,  # A <-> B; C -> A, B
        (0,1,1,1,1,0) : 4,  # A <-> C; B -> A, C
        (1,0,1,0,1,1) : 4,  # B <-> C; A -> B, C
        (1,1,1,0,1,0) : 3,  # A <-> B; A -> C; B -> C
        (1,0,1,1,0,1) : 3,  # A <-> C; A -> B; C -> B
        (0,1,0,1,1,1) : 3,  # B <-> C; B -> A; C -> A
        (1,1,1,1,1,0) : 2,  # A <-> B; A <-> C; B -> C
        (1,1,1,1,0,1) : 2,  # A <-> B; A <-> C; C -> B
        (1,1,1,0,1,1) : 2,  # A <-> B; B <-> C; A -> C
        (1,1,0,1,1,1) : 2,  # A <-> B; B <-> C; C -> A
        (1,0,1,1,1,1) : 2,  # A <-> C; B <-> C; A -> B
        (0,1,1,1,1,1) : 2,  # A <-> C; B <-> C; B -> A
        (1,1,1,1,1,1) : 1   # A <-> B; A <-> C; B <-> C
    }


def assertSumsToOne(probabilities, tolerance = 0.01):
    summed = np.sum(list(probabilities.values()))
    if(abs(summed - 1) > tolerance):
        raise RuntimeError("summed probabilities: {:.12f}".format(summed))


def aggregateProbabilties_16(probabilities_64):
    probabilities_16 = {}
    
    for k in range(1, 17):
        probabilities_16[k] = 0

    motifIndex16 = getMotifIndex_16()
    
    for maskKey, probability in probabilities_64.items():
        motifNumber = motifIndex16[maskKey]
        probabilities_16[motifNumber] += probability

    assertSumsToOne(probabilities_16)

    return probabilities_16


def removePopulationPrefix(combination):
    if("#" in combination):
        return combination.split("#")[0]
    else:
        return combination


def getPopulationsFromCombinations(combinations, mode):
    nonredundantPopulations = set()

    for combination in combinations:
        nonredundantPopulations.add(removePopulationPrefix(combination[0]))
        nonredundantPopulations.add(removePopulationPrefix(combination[1]))
        nonredundantPopulations.add(removePopulationPrefix(combination[2]))

    populations = []  # [(column, celltype/layer)]

    for population in nonredundantPopulations:
        parts = population.split("-")
        column = parts[0]
        celltypeLayer = parts[1]        
        populations.append((column, celltypeLayer))

    return populations


def sampleIdsForPopulation(neurons, neuronsLayer, population, sampleSize):
    column = population[0]
    celltypeLayer = population[1]

    filterSpec = util_filter.getDefaultFilter()  

    if(column in constants.getColumns()):
        regions = constants.getRegionsForColumn(column, includeSurrounding=False)
        filterSpec["region_whitelist"] = regions
    elif(column == "ALL"):
        pass
    else:
        raise ValueError(column)

    if celltypeLayer in constants.getCellTypes():
        celltype = celltypeLayer
        if(celltype == "VPM"):
            filterSpec["inside_vS1"] = []
        filterSpec["celltype_whitelist"] = [celltype]   
    elif(celltypeLayer == "ALL"):
        pass
    elif(celltypeLayer == "EXC"):
        filterSpec["celltype_blacklist"] = ["INH"]
    elif(celltypeLayer == "INH"):
        filterSpec["celltype_whitelist"] = ["INH"]
    elif(celltypeLayer == "L1"):
        filterSpec["layer_whitelist"] = ["L1"]        
    elif(celltypeLayer == "L2"):
        filterSpec["layer_whitelist"] = ["L2"]
    elif(celltypeLayer == "L3"):
        filterSpec["layer_whitelist"] = ["L3"]
    elif(celltypeLayer == "L4"):
        filterSpec["layer_whitelist"] = ["L4"]        
    elif(celltypeLayer == "L5"):
        filterSpec["layer_whitelist"] = ["L5"]
    elif(celltypeLayer == "L6"):
        filterSpec["layer_whitelist"] = ["L6"]
    elif(celltypeLayer == "L1EXC"):
        filterSpec["layer_whitelist"] = ["L1"]
        filterSpec["celltype_blacklist"] = ["INH"]
    elif(celltypeLayer == "L1INH"):
        filterSpec["layer_whitelist"] = ["L2"]
        filterSpec["celltype_whitelist"] = ["INH"]    
    elif(celltypeLayer == "L2EXC"):
        filterSpec["layer_whitelist"] = ["L2"]
        filterSpec["celltype_blacklist"] = ["INH"]
    elif(celltypeLayer == "L2INH"):
        filterSpec["layer_whitelist"] = ["L2"]
        filterSpec["celltype_whitelist"] = ["INH"]
    elif(celltypeLayer == "L3EXC"):
        filterSpec["layer_whitelist"] = ["L3"]
        filterSpec["celltype_blacklist"] = ["INH"]
    elif(celltypeLayer == "L3INH"):
        filterSpec["layer_whitelist"] = ["L3"]
        filterSpec["celltype_whitelist"] = ["INH"]
    elif(celltypeLayer == "L4EXC"):
        filterSpec["layer_whitelist"] = ["L4"]
        filterSpec["celltype_blacklist"] = ["INH"]
    elif(celltypeLayer == "L4INH"):
        filterSpec["layer_whitelist"] = ["L4"]
        filterSpec["celltype_whitelist"] = ["INH"]
    elif(celltypeLayer == "L5EXC"):
        filterSpec["layer_whitelist"] = ["L5"]
        filterSpec["celltype_blacklist"] = ["INH"]
    elif(celltypeLayer == "L5INH"):
        filterSpec["layer_whitelist"] = ["L5"]
        filterSpec["celltype_whitelist"] = ["INH"]
    elif(celltypeLayer == "L6EXC"):
        filterSpec["layer_whitelist"] = ["L6"]
        filterSpec["celltype_blacklist"] = ["INH"]
    elif(celltypeLayer == "L6INH"):
        filterSpec["layer_whitelist"] = ["L6"]
        filterSpec["celltype_whitelist"] = ["INH"]
    else:
        raise ValueError(celltypeLayer)

    nids = list(util_filter.filterNIDs(neurons, filterSpec, neuronsLayer=neuronsLayer))
    nidsSampled = list(util.getRandomSubset(nids, sampleSize))

    if(not len(nidsSampled)):
        raise RuntimeError("empty sample: {}".format(population))

    nids.sort()
    nidsSampled.sort()

    return nids, nidsSampled


def parseIntersomaticDistanceDescriptor(descriptor):
    if("#" not in descriptor):
        raise ValueError(descriptor)
    
    parts = descriptor.split("#")
    
    if(len(parts) != 4):
        raise ValueError(descriptor)
    
    populationDescriptor = parts[0]
    partsPopulation = populationDescriptor.split("-")
    column = partsPopulation[0]
    celltypeLayer = partsPopulation[1]
    population = (column, celltypeLayer)

    distMin = float(parts[1])
    distMax = float(parts[2])
    distRange = (distMin, distMax)

    return population, distRange


def sampleIntersomaticDistanceIds(networkDir, outfolder, combinations, sampleSize, numWorkers):

    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    neuronsLayer = util_meta.loadNeuronsLayer(os.path.join(networkDir, "neurons_layer.csv"))

    for combination in combinations:
        A = combination[0]
        B = combination[1]
        C = combination[2]

        population_A, distRange_A = parseIntersomaticDistanceDescriptor(A)
        population_B, distRange_B = parseIntersomaticDistanceDescriptor(B)
        population_C, distRange_C = parseIntersomaticDistanceDescriptor(C)

        if(distRange_A != distRange_B or distRange_B != distRange_C):
            raise RuntimeError("incompatible distances {}".format(combination))
        distRange = distRange_A

        nids_A, nids_sampled_A = sampleIdsForPopulation(neurons, neuronsLayer, population_A, sampleSize)
        nids_B, nids_sampled_B = sampleIdsForPopulation(neurons, neuronsLayer, population_B, sampleSize)
        nids_C, nids_sampled_C = sampleIdsForPopulation(neurons, neuronsLayer, population_C, sampleSize)
        
        numTripletSamples = sampleSize**3        
        tripletSamples = util_intersomatic_distance.getTripletSamples(neurons, nids_A, nids_B, nids_C, distRange, numTripletSamples, numWorkers, numNeuronSubSamples=sampleSize)

        filename = os.path.join(outfolder, "ids_{}_{}_{}.txt".format(A,B,C))
        np.savetxt(filename, tripletSamples, fmt="%d", delimiter=",")


def sampleIds(networkDir, outfolder, mode, sampleSize, numWorkers):
    if(mode == "celltype-combinations"):
        combinations = motif_combinations.getCellTypeCombinations()                
    elif(mode == "celltype-layer-combinations"):
        combinations = motif_combinations.getCellTypeLayerCombinations()
    elif(mode == "all-column-combinations"):
        combinations = motif_combinations.getAllColumnCombinations()
    elif(mode == "selected-column-combinations"):
        combinations = motif_combinations.getSelectedColumnCombinations()                
    elif(mode == "intersomatic-distance-combinations"):                  
        combinations = motif_combinations.getIntersomaticDistanceCombinations()
        sampleIntersomaticDistanceIds(networkDir, outfolder, combinations, sampleSize, numWorkers)        
    else:
        raise ValueError(mode)

    populations = getPopulationsFromCombinations(combinations, mode)
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    neuronsLayer = util_meta.loadNeuronsLayer(os.path.join(networkDir, "neurons_layer.csv"))

    for population in populations:
        nids, nidsSampled = sampleIdsForPopulation(neurons, neuronsLayer, population, sampleSize)

        column = population[0]
        celltypeLayer = population[1]

        filename = os.path.join(outfolder, "ids_{}-{}.txt".format(column, celltypeLayer))
        np.savetxt(filename, nids, fmt="%d")
                
        filenameSampled = os.path.join(outfolder, "ids_{}-{}_sampled.txt".format(column, celltypeLayer))
        np.savetxt(filenameSampled, nidsSampled, fmt="%d")


def loadIds(idsFolder, descriptor, ignoreIdPostfix):
    if("#" in descriptor and ignoreIdPostfix):
        descriptor = descriptor.split("#")[0]
    nids = np.loadtxt(os.path.join(idsFolder, "ids_{}.txt".format(descriptor)), dtype=int)
    nidsSampled = np.loadtxt(os.path.join(idsFolder, "ids_{}_sampled.txt".format(descriptor)), dtype=int)
    return nids, nidsSampled


def loadDependentIds(idsFolder, descriptorA, descriptorB, descriptorC):
    filename = os.path.join(idsFolder, "ids_{}_{}_{}.txt".format(descriptorA, descriptorB, descriptorC))
    nids = np.loadtxt(filename, delimiter=",", dtype=int)
    nids_A = nids[:,0]
    nids_B = nids[:,1]
    nids_C = nids[:,2]
    return nids_A, nids_B, nids_C


def loadDSC(networkDir, preIds, dscCache, descriptor, dscFolder):
    with warnings.catch_warnings():          
        warnings.simplefilter("ignore", category=UserWarning)

        if(descriptor in dscCache):
            return dscCache[descriptor]

        dscFolder = os.path.join(networkDir, dscFolder)
        dscPerPre = {}
        for preId in preIds:
            filename = os.path.join(dscFolder, "{}_DSC.csv".format(preId))              
            postIds, dscValues = util.loadDataBlock(filename,1)
            dscPerPre[preId] = {
                "postIds" : postIds,
                "dscValues" : dscValues,
            }

        dscCache[descriptor] = dscPerPre
        return dscPerPre


def loadDSCOnlineExperiment(networkDir, preIds, dscCache, dscFolder):    
    dscFolder = os.path.join(networkDir, dscFolder)
    for preId in preIds:
        if(preId not in dscCache.keys()):
            filename = os.path.join(dscFolder, "{}_DSC.csv".format(preId))            
            postIds, dscValues = util.loadDataBlock(filename,1)
            dscCache[preId] = {
                "postIds" : postIds,
                "dscValues" : dscValues,
            }    



def calcProbabilitiesSinglePreNeuron(postIds, dscPerPreNeuron):
    dscMatched = np.zeros(postIds.size)

    overlappingPostIds = dscPerPreNeuron["postIds"]
    dscValues = dscPerPreNeuron["dscValues"]

    common, idxOverlapping, idxMatched = np.intersect1d(overlappingPostIds, postIds, assume_unique=True, return_indices=True)
    if(common.size):
        dscMatched[idxMatched] = dscValues[idxOverlapping]

    p = 1-np.exp(-dscMatched)
    return p


def calcProbabilties(preIds, postIds, dscPerPre):
    probs = np.zeros(shape=(preIds.size, postIds.size))
    for i in range(0, preIds.size):        
        preId = preIds[i]
        dscPerPreNeuron = dscPerPre[preId]
        probs[i,:] = calcProbabilitiesSinglePreNeuron(postIds, dscPerPreNeuron)
    return probs


def getMotifMasks(numNodes):
    nEdges = numNodes * (numNodes-1)
    if(nEdges > 8):
        raise ValueError(nEdges)
    edgeConfigurations = np.arange(2**nEdges, dtype=np.uint8).reshape((-1,1))
    masks = np.unpackbits(edgeConfigurations, axis=1)
    masks_inv = np.ones_like(masks) - masks
    masks = masks.astype(bool)
    masks_inv = masks_inv.astype(bool)
    return masks[:,(8-nEdges):], masks_inv[:,(8-nEdges):]


def calcMotifProbability(p, p_inv, mask, mask_inv):
    p_edges = np.concatenate((p[:,mask], p_inv[:,mask_inv]), axis=1)
    p_motif = np.prod(p_edges, axis=1)
    return np.mean(p_motif)


def calcModelProbabilitiesIndependentSamples(stats, nids_A_sample, nids_B_sample, nids_C_sample, dsc_A, dsc_B, dsc_C):
    num_A = nids_A_sample.size
    num_B = nids_B_sample.size
    num_C = nids_C_sample.size

    numSamples = num_A * num_B * num_C
    p_model = np.zeros(shape=(numSamples, 6))

    p_A_B = calcProbabilties(nids_A_sample, nids_B_sample, dsc_A)
    p_B_A = calcProbabilties(nids_B_sample, nids_A_sample, dsc_B)
    p_A_C = calcProbabilties(nids_A_sample, nids_C_sample, dsc_A)
    p_C_A = calcProbabilties(nids_C_sample, nids_A_sample, dsc_C)
    p_B_C = calcProbabilties(nids_B_sample, nids_C_sample, dsc_B)
    p_C_B = calcProbabilties(nids_C_sample, nids_B_sample, dsc_C)

    p_all = np.concatenate((p_A_B, p_B_A, p_A_C, p_C_A, p_B_C, p_C_B), axis=None)

    stats["avg_A-B"] = np.mean(p_A_B)
    stats["sd_A-B"] = np.std(p_A_B)
    stats["avg_B-A"] = np.mean(p_B_A)
    stats["sd_B-A"] = np.std(p_B_A)
    stats["avg_A-C"] = np.mean(p_A_C)
    stats["sd_A-C"] = np.std(p_A_C)            
    stats["avg_C-A"] = np.mean(p_C_A)
    stats["sd_C-A"] = np.std(p_C_A)            
    stats["avg_B-C"] = np.mean(p_B_C)
    stats["sd_B-C"] = np.std(p_B_C)
    stats["avg_C-B"] = np.mean(p_C_B)
    stats["sd_C-B"] = np.std(p_C_B)  
    stats["avg_all"] = np.mean(p_all)
    stats["sd_all"] = np.std(p_all)    

    idx = 0
    for i in range(0, num_A):
        for j in range(0, num_B):
            for k in range(0, num_C):
                if(i == j or i == k or j == k):
                    p_model[idx, :] = 0                    
                else:
                    p_model[idx, 0] = p_A_B[i,j]
                    p_model[idx, 1] = p_B_A[j,i]
                    p_model[idx, 2] = p_A_C[i,k]
                    p_model[idx, 3] = p_C_A[k,i]
                    p_model[idx, 4] = p_B_C[j,k]
                    p_model[idx, 5] = p_C_B[k,j]
                idx += 1
                
    return p_model


def calcProbilityAll(nids_A, nids_B, nids_C, p_model):    
    nids_ABC = np.concatenate((nids_A.reshape(-1,1), nids_B.reshape(-1,1), nids_C.reshape(-1,1)), axis=1)

    _, indices_AB = np.unique(nids_ABC[:, (0,1)], return_index = True, axis=1)
    _, indices_AC = np.unique(nids_ABC[:, (0,2)], return_index = True, axis=1)
    _, indices_BC = np.unique(nids_ABC[:, (1,2)], return_index = True, axis=1)
    
    p_A_B_unique = p_model[indices_AB, 0]
    p_B_A_unique = p_model[indices_AB, 1]
    p_A_C_unique = p_model[indices_AC, 2]
    p_C_A_unique = p_model[indices_AC, 3]
    p_B_C_unique = p_model[indices_BC, 4]
    p_C_B_unique = p_model[indices_BC, 5]

    p_ABC_unique = np.concatenate((p_A_B_unique, p_B_A_unique, p_A_C_unique, p_C_A_unique, p_B_C_unique, p_C_B_unique), axis=None)
    
    return p_ABC_unique


def calcModelProbabilitiesDependentSamples(stats, nids_A, nids_B, nids_C, dsc_ABC):    
    num_A = nids_A.size
    num_B = nids_B.size
    num_C = nids_C.size

    if(num_A != num_B or num_B != num_C):
        raise RuntimeError("dependent sample size mismatch")
    numSamples = num_A

    p_model = np.zeros(shape=(numSamples, 6))

    nids_merged_unique, rev_indices = getMergedUnique(nids_A, nids_B, nids_C)
    p_ABC = calcProbabilties(nids_merged_unique, nids_merged_unique, dsc_ABC)

    for i in range(0, numSamples):
        ia = rev_indices[i]
        ib = rev_indices[i + numSamples]
        ic = rev_indices[i + 2 * numSamples]

        p_model[i, 0] = p_ABC[ia, ib]
        p_model[i, 1] = p_ABC[ib, ia]
        p_model[i, 2] = p_ABC[ia, ic]
        p_model[i, 3] = p_ABC[ic, ia]
        p_model[i, 4] = p_ABC[ib, ic]
        p_model[i, 5] = p_ABC[ic, ib]
    
    p_all = calcProbilityAll(nids_A, nids_B, nids_C, p_model)

    stats["avg_A-B"] = np.mean(p_model[:, 0])
    stats["sd_A-B"] = np.std(p_model[:, 0])
    stats["avg_B-A"] = np.mean(p_model[:, 1])
    stats["sd_B-A"] = np.std(p_model[:, 1])
    stats["avg_A-C"] = np.mean(p_model[:, 2])
    stats["sd_A-C"] = np.std(p_model[:, 2])            
    stats["avg_C-A"] = np.mean(p_model[:, 3])
    stats["sd_C-A"] = np.std(p_model[:, 3])            
    stats["avg_B-C"] = np.mean(p_model[:, 4])
    stats["sd_B-C"] = np.std(p_model[:, 4])
    stats["avg_C-B"] = np.mean(p_model[:, 5])
    stats["sd_C-B"] = np.std(p_model[:, 5])  
    stats["avg_all"] = np.mean(p_all)
    stats["sd_all"] = np.std(p_all)    
        
    return p_model


def calcMotifProbabilities(stats, nids_A_sample, nids_B_sample, nids_C_sample, dsc_A, dsc_B, dsc_C, independentSamples):
    
    if(independentSamples):
        p_model = calcModelProbabilitiesIndependentSamples(stats, nids_A_sample, nids_B_sample, nids_C_sample, dsc_A, dsc_B, dsc_C)
    else:
        dsc_ABC = dsc_A
        p_model = calcModelProbabilitiesDependentSamples(stats, nids_A_sample, nids_B_sample, nids_C_sample, dsc_ABC)

    p_model_inv = 1 - p_model

    p_avg = np.zeros(6)
    p_avg[0] = stats["avg_A-B"]
    p_avg[1] = stats["avg_B-A"]
    p_avg[2] = stats["avg_A-C"]
    p_avg[3] = stats["avg_C-A"]
    p_avg[4] = stats["avg_B-C"]
    p_avg[5] = stats["avg_C-B"]

    p_avg = p_avg.reshape((-1,6))    
    p_avg_inv = 1 - p_avg

    masks, masks_inv = getMotifMasks(3)    

    stats["motif_probabilities_64_random"] = {}
    stats["motif_probabilities_64_model"] = {}

    for i in range(0, masks.shape[0]):
        mask = masks[i,:]
        mask_inv = masks_inv[i,:]
        
        p_motif_random = calcMotifProbability(p_avg, p_avg_inv, mask, mask_inv) 
        p_motif_model = calcMotifProbability(p_model, p_model_inv, mask, mask_inv) 
        
        motifKey = tuple(mask.astype(int))
        stats["motif_probabilities_64_random"][motifKey] = p_motif_random
        stats["motif_probabilities_64_model"][motifKey] = p_motif_model


def getMergedUnique(nidsA, nidsB, nidsC):
    merged = np.concatenate((nidsA, nidsB, nidsC))
    mergedUnique, reverseIndices = np.unique(merged, return_inverse=True)
    return mergedUnique, reverseIndices  


def calcEdgeProbabilitiesBatch(batchIndex, results, combinations, idsFolder, independentSamples, mode, networkDir, outfolder):

    k = 0
    dscCache = {}
        
    for combination in combinations:
        k += 1
        if(k % 10 == 0):
            dscCache = {}

        dscFolder = "DSC_50-50-50_all"                
        ignoreIdPostfix = False           
        if("h01" in mode):
            ignoreIdPostfix = True            
            if("#null-model" in combination[0]):
                dscFolder = "DSC_null-model"            
            else:
                dscFolder = "DSC_empirical"
        
        if(mode == "online-experiment"):
            combinationKey = combination
            A = "sel-A"
            B = "sel-B"
            C = "sel-C"
        else:
            A = combination[0]
            B = combination[1]
            C = combination[2]
            combinationKey = (A, B, C)

        try:                            
            if(independentSamples):
                if(mode == "online-experiment"):
                    nids_A_sample = idsFolder["A"]
                    nids_B_sample = idsFolder["B"]
                    nids_C_sample = idsFolder["C"]
                    loadDSCOnlineExperiment(networkDir, nids_A_sample, dscCache, dscFolder)
                    loadDSCOnlineExperiment(networkDir, nids_B_sample, dscCache, dscFolder)
                    loadDSCOnlineExperiment(networkDir, nids_C_sample, dscCache, dscFolder)
                    dsc_A = dscCache
                    dsc_B = dscCache
                    dsc_C = dscCache                
                else:
                    _, nids_A_sample = loadIds(idsFolder, A, ignoreIdPostfix)
                    _, nids_B_sample = loadIds(idsFolder, B, ignoreIdPostfix)
                    _, nids_C_sample = loadIds(idsFolder, C, ignoreIdPostfix)
                    dsc_A = loadDSC(networkDir, nids_A_sample, dscCache, A, dscFolder)        
                    dsc_B = loadDSC(networkDir, nids_B_sample, dscCache, B, dscFolder)
                    dsc_C = loadDSC(networkDir, nids_C_sample, dscCache, C, dscFolder)
            else:
                nids_A_sample, nids_B_sample, nids_C_sample = loadDependentIds(idsFolder, A, B, C)                
                nids_merged_unique, _ = getMergedUnique(nids_A_sample, nids_B_sample, nids_C_sample)
                print("nids_merged_unique", nids_merged_unique.shape)
                dsc_A = loadDSC(networkDir, nids_merged_unique, dscCache, A, dscFolder)        
                dsc_B = None
                dsc_C = None
            
            stats = {}

            calcMotifProbabilities(stats, nids_A_sample, nids_B_sample, nids_C_sample, dsc_A, dsc_B, dsc_C, independentSamples)
            
            stats["motif_probabilities_16_random"] = aggregateProbabilties_16(stats["motif_probabilities_64_random"])
            stats["motif_probabilities_16_model"] = aggregateProbabilties_16(stats["motif_probabilities_64_model"])
                        
            results[combinationKey] = stats

            print("batch {}: processed {}/{}".format(batchIndex, k, len(combinations)))
        
        except Exception as e:            
            results[combinationKey] = None
            print(traceback.format_exc())
            
            if(outfolder):
                errorFile = os.path.join(outfolder, "error_{}-{}-{}.txt".format(A, B, C))
                with open(errorFile, "w+") as f:
                    f.write(traceback.format_exc())
            
            print("batch {}: failed {}/{}".format(batchIndex, k, len(combinations)))        


def writeMotifFeatures(filename, results, combinations):
    with open(filename, "w+") as f:
        f.write("A,B,C,avg_A-B,sd_A-B,avg_B-A,sd_B-A,avg_A-C,sd_A-C,avg_C-A,sd_C-A,avg_B-C,sd_B-C,avg_B-C,sd_B-C,avg_all,sd_all\n")
        for combination in combinations:
            stats = results[combination]
            if(stats is None):
                continue

            f.write("{},{},{},".format(combination[0], combination[1], combination[2]))
            f.write("{:.12E},{:.12E},".format(stats["avg_A-B"], stats["sd_A-B"]))
            f.write("{:.12E},{:.12E},".format(stats["avg_B-A"], stats["sd_B-A"]))
            f.write("{:.12E},{:.12E},".format(stats["avg_A-C"], stats["sd_A-C"]))
            f.write("{:.12E},{:.12E},".format(stats["avg_C-A"], stats["sd_C-A"]))
            f.write("{:.12E},{:.12E},".format(stats["avg_B-C"], stats["sd_B-C"]))
            f.write("{:.12E},{:.12E},".format(stats["avg_C-B"], stats["sd_C-B"]))
            f.write("{:.12E},{:.12E}\n".format(stats["avg_all"], stats["sd_all"]))


def writeMotifProbabilities(outfolder, results, combinations):
    masks, masks_inv = getMotifMasks(3)
    
    for combination in combinations:

        if(results[combination] is None):
            continue

        probabilities_random = results[combination]["motif_probabilities_64_random"]
        probabilities_model = results[combination]["motif_probabilities_64_model"]

        filename = os.path.join(outfolder,"probabilities_64_{}-{}-{}.csv".format(combination[0], combination[1], combination[2]))

        with open(filename, "w+") as f:
            f.write("A-B,B-A,A-C,C-A,B-C,C-B,probability_random,probability_model\n")
            for i in range(0,masks.shape[0]):
                mask = masks[i,:]
                motifKey = tuple(mask.astype(int))

                p_random = probabilities_random[motifKey]
                p_model = probabilities_model[motifKey]

                f.write("{},{},{},{},{},{},".format(motifKey[0], motifKey[1], motifKey[2], motifKey[3], motifKey[4], motifKey[5]))
                f.write("{:.12E},{:.12E}\n".format(p_random, p_model))


def writeSummary(filename, results, combinations):

    with open(filename, "w+") as f:
        f.write("A,B,C")
        for k in range(1,17):
            f.write(",motif-{}_random".format(k))
            f.write(",motif-{}_model".format(k))
        f.write("\n")

        for combination in combinations:

            if(results[combination] is None):
                continue

            f.write("{},{},{}".format(combination[0], combination[1], combination[2]))

            probabilities_random = results[combination]["motif_probabilities_16_random"]
            probabilities_model = results[combination]["motif_probabilities_16_model"]

            for k in range(1,17):                
                f.write(",{:.12E}".format(probabilities_random[k]))
                f.write(",{:.12E}".format(probabilities_model[k]))

            f.write("\n")


def calcDeviation(p_random, p_model, maxDeviation = 1000000000000):    

    if(p_random > 0):
        deviation = p_model / p_random
        return min(deviation, maxDeviation)
    elif(p_model == 0):
        return 1
    else:
        return maxDeviation
    


def convertSummaryFileJson(filename):
    if(".csv" not in filename):
        raise ValueError(filename)

    outfile = filename.replace(".csv", ".json")    
    summary = []

    with open(filename) as f:
        lines = f.readlines()
        for i in range(1, len(lines)):
            parts = lines[i].rstrip().split(",")
            selection = "_".join([parts[0], parts[1], parts[2]])
            for k in range(0,16):

                p_random = float(parts[k * 2 + 3])
                p_model = float(parts[k * 2 + 4])
                deviation = calcDeviation(p_random, p_model)
                
                summary.append({
                    "selection" : selection,
                    "motif-number" : k + 1,
                    "prob-random" : round(p_random,8),
                    "prob-model" : round(p_model,8), 
                    "prob-deviation" : round(deviation,8)
                })

    with open(outfile, "w+") as f:
        json.dump(summary, f)


def getRuleBatchCombinations(networkDir, mode):
    dscBaseFolder = os.path.join(networkDir, "DSC_{}".format(mode))
    parameterDescriptors = util.getParameterDescriptorsFromFolder(dscBaseFolder)

    combinations = []
    for parameterDescriptor in parameterDescriptors:        
        combinations.append((parameterDescriptor, parameterDescriptor, parameterDescriptor))
    return combinations
    


def calcCombinations(networkDir, idsFolder, mode, outfolder, numWorkers): 
    independentSamples = True
    
    if(mode == "celltype-combinations"):
        combinations = motif_combinations.getCellTypeCombinations()
    elif(mode == "celltype-layer-combinations"):
        combinations = motif_combinations.getCellTypeLayerCombinations()
    elif(mode == "all-column-combinations"):
        combinations = motif_combinations.getAllColumnCombinations()
    elif(mode == "selected-column-combinations"):
        combinations = motif_combinations.getSelectedColumnCombinations()
    elif(mode == "intersomatic-distance-combinations"):
        combinations = motif_combinations.getIntersomaticDistanceCombinations()
        independentSamples = False    
    elif(mode == "h01-layer-combinations"):
        combinations = motif_combinations.getH01LayerCombinations()
    elif(mode == "h01-pyramidal-combinations"):
        combinations = motif_combinations.getH01PyramidalCombinations() 
    else:
        raise ValueError(mode)

    batches = np.array_split(combinations, numWorkers)
    manager = mp.Manager()
    results = manager.dict()
    processes = []
    for i in range(0, len(batches)):
        p = mp.Process(target=calcEdgeProbabilitiesBatch, args=(i, results, batches[i], idsFolder, independentSamples, mode, networkDir, outfolder))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()

    filename = os.path.join(outfolder, "features_{}.csv".format(mode))
    writeMotifFeatures(filename, results, combinations)

    writeMotifProbabilities(outfolder, results, combinations)

    filename = os.path.join(outfolder, "probabilities_16_{}.csv".format(mode))
    writeSummary(filename, results, combinations)
    convertSummaryFileJson(filename)


def printUsageAndExit():
    print("eval_motifs.py network-dir mode num-workers [sample-ids]")
    print()
    print("mode:    celltype-combinations, celltype-layer-combinations, all-column-combinations, selected-column-cobinations, intersomatic-distance-combinations")
    print("         h01-layer-combinations, h01-pyramidal-combinations")
    exit()


if __name__ == "__main__":
    if(len(sys.argv) not in [4,5]):
        printUsageAndExit()
    
    networkDir = sys.argv[1]
    mode = sys.argv[2]        
    numWorkers = int(sys.argv[3])
    
    resampleIds = False
    if(len(sys.argv) == 5):
        if(sys.argv[4] not in ["sample-ids"]):
            printUsageAndExit()
        resampleIds = True

    util.makeDir(os.path.join(networkDir, "eval", "motifs"))
    
    idsFolder = os.path.join(networkDir, "eval", "motifs", "samples_{}".format(mode))
    if(resampleIds):
        util.makeCleanDir(idsFolder)
        if(mode == "celltype-combinations"):        
            sampleSize = 200
        elif(mode == "celltype-layer-combinations"):        
            sampleSize = 200
        elif(mode == "all-column-combinations"):        
            sampleSize = 200
        elif(mode == "selected-column-combinations"):        
            sampleSize = 200
        elif(mode == "intersomatic-distance-combinations"):        
            sampleSize = 300        
        elif("h01" in mode):
            raise ValueError(mode)
        else:
            raise ValueError(mode)        

    combinationsDir = os.path.join(networkDir, "eval", "motifs", mode)
    util.makeCleanDir(combinationsDir)

    if(resampleIds):
        sampleIds(networkDir, idsFolder, mode, sampleSize, numWorkers)

    calcCombinations(networkDir, idsFolder, mode, combinationsDir, numWorkers)