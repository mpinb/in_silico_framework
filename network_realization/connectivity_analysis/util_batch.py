import os
import numpy as np

import util
import util_meta
import util_filter
import constants

NUM_WORKERS = 10

def getOriginalCellTypes(neuronsOriginal, neuronIds):
    cellTypes = []
    for neuronId in neuronIds:
        cellTypes.append(neuronsOriginal[neuronId]["cell_type"])
    return cellTypes


def getPstDensitiesMap(pstDensities, cellTypesOriginal):
    pstMap = {}
    for ctId, props in cellTypesOriginal.items():
        name = props["name"]
        if(name != "VPM"):
            pstMap[ctId] = pstDensities[name]
    return pstMap


def getPreBatches(networkDir, columns=["C2"]):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    neuronsOriginal = util_meta.loadNeuronProps(os.path.join(networkDir, "meta", "neurons.csv"))
    cellTypesOriginal = util_meta.loadCellTypes(os.path.join(networkDir, "meta", "cell_types.csv"))
    boutonDensities = util_meta.loadBoutonDensityMap(os.path.join(networkDir, "meta", "cell_types.csv"))

    batches = []    
    total = 0

    for column in columns:
        regions = constants.getRegionsForColumn(column)
        for region in regions:
            for cellType in constants.getCellTypes():
                filterPre = util_filter.getDefaultFilter()
                filterPre["inside_vS1"] = []
                filterPre["celltype_whitelist"] = [cellType]
                filterPre["region_whitelist"] = [region]
                preIds = list(util_filter.filterNIDs(neurons, filterPre))
                preIds.sort()
                if(preIds):
                    total += len(preIds)
                    descriptor = "{}-{}-{}".format(column, region, cellType)
                    print(descriptor)
                    batch = {
                        "descriptor": descriptor,
                        "excitatory": cellType != "INH",
                        "neuronIds": preIds,
                        "cellTypesOriginal": getOriginalCellTypes(neuronsOriginal, preIds),
                        "boutonDensities": boutonDensities
                    }
                    batches.append(batch)
    print("batches: neurons total {}".format(total))
    return batches


def getPostBatches(networkDir, columns=["C2"]):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    neuronsOriginal = util_meta.loadNeuronProps(os.path.join(networkDir, "meta", "neurons.csv"))
    cellTypesOriginal = util_meta.loadCellTypes(os.path.join(networkDir, "meta", "cell_types.csv"))
    pstDensities = util_meta.loadPstDensities(os.path.join(networkDir, "meta", "pst_densities.csv"))
    pstDensitiesMap = getPstDensitiesMap(pstDensities, cellTypesOriginal)

    batches = []    
    total = 0

    for column in columns:
        regions = constants.getRegionsForColumn(column)
        for region in regions:
            for cellType in constants.getCellTypes():                
                filterPre = util_filter.getDefaultFilter()
                filterPre["inside_vS1"] = []
                filterPre["synaptic_side"] = [1,2]
                filterPre["celltype_whitelist"] = [cellType]
                filterPre["region_whitelist"] = [region]
                postIds = list(util_filter.filterNIDs(neurons, filterPre))
                postIds.sort()
                if(postIds):
                    total += len(postIds)
                    descriptor = "{}-{}-{}".format(column, region, cellType)
                    print(descriptor)
                    batch = {
                        "descriptor": descriptor,
                        "neuronIds": postIds,
                        "cellTypesOriginal": getOriginalCellTypes(neuronsOriginal, postIds),
                        "pstDensities": pstDensitiesMap
                    }
                    batches.append(batch)
    print("batches: neurons total {}".format(total))
    return batches


def getPostBatchesFlat(networkDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    neuronsOriginal = util_meta.loadNeuronProps(os.path.join(networkDir, "meta", "neurons.csv"))
    filterSpec = util_filter.getDefaultFilter()
    filterSpec["inside_vS1"] = []
    filterSpec["synaptic_side"] = [1,2]
    neuronIds = list(util_filter.filterNIDs(neurons, filterSpec))
    np.random.shuffle(neuronIds)
    
    batches = []
    neuronCellTypes = []
    neuronCellTypesOriginal = []
    batchedIds = np.array_split(neuronIds, 10)
    for i in range(0,len(batchedIds)):
        ids = batchedIds[i].tolist()        
        for neuronId in ids:
            neuronCellTypes.append(neurons[neuronId]["cell_type"])
            neuronCellTypesOriginal.append(neuronsOriginal[neuronId]["cell_type"])
        batch = {
            "descriptor": "batch {}".format(i),
            "neuronIds": ids,
            "cellTypes" : neuronCellTypes,
            "cellTypesOriginal": neuronCellTypesOriginal,
            "pstDensities": None
        }
        batches.append(batch)
    return batches


def getC2Presynaptic(networkDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    filterSpec = util_filter.getDefaultFilter()
    filterSpec["inside_vS1"] = []
    filterSpec["region_whitelist"] = ["C2_Barreloid", "C2", "S1_Septum_C2"]
    neuronIds = list(util_filter.filterNIDs(neurons, filterSpec))
    return neuronIds


def getC2Postsynaptic(networkDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    filterSpec = util_filter.getDefaultFilter()
    filterSpec["synaptic_side"] = [1,2]
    filterSpec["region_whitelist"] = ["C2", "S1_Septum_C2"]
    neuronIds = list(util_filter.filterNIDs(neurons, filterSpec))
    return neuronIds


def getAllPresynaptic(networkDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    filterSpec = util_filter.getDefaultFilter()
    filterSpec["inside_vS1"] = []    
    filterSpec["synaptic_side"] = [0,2]
    neuronIds = list(util_filter.filterNIDs(neurons, filterSpec))
    return neuronIds


def getAllVPM(networkDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    filterSpec = util_filter.getDefaultFilter()
    filterSpec["inside_vS1"] = []    
    filterSpec["synaptic_side"] = [0,2]
    filterSpec["celltype_whitelist"] = ["VPM"]
    neuronIds = list(util_filter.filterNIDs(neurons, filterSpec))
    return neuronIds


def getPresynapticExcInside(networkDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    filterSpec = util_filter.getDefaultFilter()
    filterSpec["inside_vS1"] = [1]    
    filterSpec["synaptic_side"] = [0,2]
    filterSpec["celltype_blacklist"] = ["INH"]
    neuronIds = list(util_filter.filterNIDs(neurons, filterSpec))    
    vpmIds = getAllVPM(networkDir)
    neuronIds.extend(vpmIds)
    return neuronIds


def getPrePostInside(networkDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    filterSpec = util_filter.getDefaultFilter()
    filterSpec["inside_vS1"] = [1]    
    filterSpec["synaptic_side"] = [2]    
    neuronIds = list(util_filter.filterNIDs(neurons, filterSpec))        
    return neuronIds


def getPostsynapticExcInside(networkDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    filterSpec = util_filter.getDefaultFilter()
    filterSpec["inside_vS1"] = [1]    
    filterSpec["synaptic_side"] = [1,2]
    filterSpec["celltype_blacklist"] = ["INH"]
    neuronIds = list(util_filter.filterNIDs(neurons, filterSpec))
    return neuronIds


def getPresynapticInside(networkDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    filterSpec = util_filter.getDefaultFilter()
    filterSpec["inside_vS1"] = [1]    
    filterSpec["synaptic_side"] = [0,2]
    neuronIds = list(util_filter.filterNIDs(neurons, filterSpec))
    vpmIds = getAllVPM(networkDir)
    neuronIds.extend(vpmIds)
    return neuronIds


def getPostsynapticInside(networkDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    filterSpec = util_filter.getDefaultFilter()
    filterSpec["inside_vS1"] = [1]    
    filterSpec["synaptic_side"] = [1,2]
    neuronIds = list(util_filter.filterNIDs(neurons, filterSpec))    
    return neuronIds


def getPresynapticInhInside(networkDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    filterSpec = util_filter.getDefaultFilter()
    filterSpec["inside_vS1"] = [1]    
    filterSpec["synaptic_side"] = [0,2]
    filterSpec["celltype_whitelist"] = ["INH"]
    neuronIds = list(util_filter.filterNIDs(neurons, filterSpec))
    vpmIds = getAllVPM(networkDir)
    neuronIds.extend(vpmIds)
    return neuronIds


def getAllPostsynaptic(networkDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    filterSpec = util_filter.getDefaultFilter()
    filterSpec["inside_vS1"] = []    
    filterSpec["synaptic_side"] = [1,2]
    neuronIds = list(util_filter.filterNIDs(neurons, filterSpec))
    return neuronIds


def getPostsynapticInh(networkDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    filterSpec = util_filter.getDefaultFilter()
    filterSpec["inside_vS1"] = []    
    filterSpec["synaptic_side"] = [1,2]
    filterSpec["celltype_whitelist"] = ["INH"]
    neuronIds = list(util_filter.filterNIDs(neurons, filterSpec))
    return neuronIds


def getPostsynapticExc(networkDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    filterSpec = util_filter.getDefaultFilter()
    filterSpec["inside_vS1"] = []    
    filterSpec["synaptic_side"] = [1,2]
    filterSpec["celltype_blacklist"] = ["INH"]
    neuronIds = list(util_filter.filterNIDs(neurons, filterSpec))
    return neuronIds


def getPostsynaptic_vS1(networkDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    filterSpec = util_filter.getDefaultFilter()
    filterSpec["inside_vS1"] = [1]    
    filterSpec["synaptic_side"] = [1,2]
    neuronIds = list(util_filter.filterNIDs(neurons, filterSpec))
    return neuronIds

def getBatchFilesFromIds(networkDir, name, ids, numBatches):
    util.makeDir(os.path.join(networkDir, "batches"))
    batchDir = os.path.join(networkDir, "batches", name)
    util.makeCleanDir(batchDir)

    neuronIds = list(ids)
    np.random.shuffle(neuronIds)    
    batches = np.array_split(neuronIds, numBatches)
    filenames = []    
    for i in range(0,len(batches)):
        filename = os.path.join(batchDir, "{}".format(i))
        np.savetxt(filename, batches[i], fmt='%d')
        filenames.append(filename)
    return filenames


def getBatchFiles(networkDir, synapticSide, gridDescriptor, boundsDescriptor, name, numBatches, excludeExisting = False, nids = None):    
    util.makeDir(os.path.join(networkDir, "batches"))
    batchDir = os.path.join(networkDir, "batches", name)
    util.makeCleanDir(batchDir)

    if(boundsDescriptor is None):
        neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
        filterSpec = util_filter.getDefaultFilter()
        filterSpec["inside_vS1"] = []
        if(synapticSide == "post"):
            filterSpec["synaptic_side"] = [1,2]
        neuronIds = list(util_filter.filterNIDs(neurons, filterSpec))
    else:
        if(boundsDescriptor == "ref-volume"):
            neuronIds = np.loadtxt(os.path.join(networkDir, "innervating_{}_{}.txt".format(boundsDescriptor, synapticSide)), dtype=int).tolist()
        elif(boundsDescriptor in ["C2-volume", "cellular-connectivity-volume"]):
            if(synapticSide == "pre"):
                neuronIds = getC2Presynaptic(networkDir)
            else:
                neuronIds = np.loadtxt(os.path.join(networkDir, "innervating_{}_{}.txt".format(boundsDescriptor, synapticSide)), dtype=int).tolist()
        elif(boundsDescriptor == "reference-volume-L5"):            
            neuronIds = np.loadtxt(os.path.join(networkDir, "innervating_{}_{}.txt".format(boundsDescriptor, synapticSide)), dtype=int).tolist()
        elif(boundsDescriptor == "D2-volume"):
            if(nids is None):
                raise ValueError()
            neuronIds = nids
        else:
            raise RuntimeError("invalid bounds descriptor: {}".format(boundsDescriptor))

    if(excludeExisting):
        if(nids is None):
            filteredIds = []
            for neuronId in neuronIds:     
                print(neuronId)       
                if(boundsDescriptor is None):
                    filename = os.path.join(networkDir, "subcellular_features_{}synaptic_{}".format(synapticSide, gridDescriptor), "{}.csv".format(neuronId))             
                else:
                    filename = os.path.join(networkDir, "subcellular_features_{}synaptic_{}_{}".format(synapticSide, gridDescriptor, boundsDescriptor), "{}.csv".format(neuronId))             
                if(not os.path.exists(filename)):
                    filteredIds.append(neuronId)
        else:
            filteredIds = nids
        neuronIds = filteredIds
    print("total", len(neuronIds))

    np.random.shuffle(neuronIds)    
    batches = np.array_split(neuronIds, numBatches)
    filenames = []    
    for i in range(0,len(batches)):
        filename = os.path.join(batchDir, "{}".format(i))
        np.savetxt(filename, batches[i], fmt='%d')
        filenames.append(filename)
    return filenames


def getPreBatchesFlat(networkDir, excludeExisting = False):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    neuronsOriginal = util_meta.loadNeuronProps(os.path.join(networkDir, "meta", "neurons.csv"))    
    boutonDensities = util_meta.loadBoutonDensityMap(os.path.join(networkDir, "meta", "cell_types.csv"))
    neuronIds = list(neurons.keys())
    if(excludeExisting):
        filteredIds = []
        for neuronId in neuronIds:     
            print(neuronId)       
            filename = os.path.join(networkDir, "subcellular_features_presynaptic_50-50-50", "{}.csv".format(neuronId))             
            if(not os.path.exists(filename)):
                filteredIds.append(neuronId)
        neuronIds = filteredIds
    #np.random.shuffle(neuronIds)
    neuronIds.sort()
    
    batches = []
    neuronCellTypes = []
    neuronCellTypesOriginal = []
    batchedIds = np.array_split(neuronIds, 10)
    total = 0
    for i in range(0,len(batchedIds)):
        ids = batchedIds[i].tolist()        
        for neuronId in ids:
            neuronCellTypes.append(neurons[neuronId]["cell_type"])
            neuronCellTypesOriginal.append(neuronsOriginal[neuronId]["cell_type"])
        total += len(ids)
        batch = {
            "descriptor": "batch {}".format(i),
            "neuronIds": ids,
            "cellTypes" : neuronCellTypes,
            "cellTypesOriginal": neuronCellTypesOriginal,
            "pstDensities": None,
            "boutonDensities" : boutonDensities
        }
        batches.append(batch)
    print(total)
    return batches


def getExamplePreBatch(networkDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    neuronsOriginal = util_meta.loadNeuronProps(os.path.join(networkDir, "meta", "neurons.csv"))    
    boutonDensities = util_meta.loadBoutonDensityMap(os.path.join(networkDir, "meta", "cell_types.csv"))
    neuronIds = [500213]
    
    batches = []
    neuronCellTypes = []
    neuronCellTypesOriginal = []
    batchedIds = [neuronIds]
    for i in range(0,len(batchedIds)):
        ids = batchedIds[i]   
        for neuronId in ids:
            neuronCellTypes.append(neurons[neuronId]["cell_type"])
            neuronCellTypesOriginal.append(neuronsOriginal[neuronId]["cell_type"])
        batch = {
            "descriptor": "batch {}".format(i),
            "neuronIds": ids,
            "cellTypes" : neuronCellTypes,
            "cellTypesOriginal": neuronCellTypesOriginal,
            "pstDensities": None,
            "boutonDensities" : boutonDensities
        }
        batches.append(batch)
    return batches


def getExamplePostBatch(networkDir):
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    neuronsOriginal = util_meta.loadNeuronProps(os.path.join(networkDir, "meta", "neurons.csv"))

    neuronIds = [0]    
    neuronCellTypes = []
    neuronCellTypesOriginal = []
    for neuronId in neuronIds:
        neuronCellTypes.append(neurons[neuronId]["cell_type"])
        neuronCellTypesOriginal.append(neuronsOriginal[neuronId]["cell_type"])

    batch = {
        "descriptor": "example-post",
        "neuronIds": neuronIds,
        "cellTypes" : neuronCellTypes,
        "cellTypesOriginal": neuronCellTypesOriginal,
        "pstDensities": None
    }
    return [batch]
    