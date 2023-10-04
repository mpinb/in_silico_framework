import os
import sys
import numpy as np
import warnings

import util_feature_IO
import util
import util_meta
import util_time
import util_filter
import util_batch
import constants
import multiprocessing as mp


def splitColumns(data):  # ids values
    idxnonzero = data[:, 1] > 0
    return data[idxnonzero, 0].astype(int), data[idxnonzero, 1]


def getPreBatches(neurons, columns):
    batches = []    
    for column in columns:  
        regions = constants.getRegionsForColumn(column)
        for cellType in constants.getCellTypes():
            filterPre = util_filter.getDefaultFilter()
            if(cellType == "VPM"):
                filterPre = util_filter.getVPMFilter(column)
            else:                
                filterPre["inside_vS1"] = []
                filterPre["celltype_whitelist"] = [cellType]
                filterPre["region_whitelist"] = regions
            preIds = list(util_filter.filterNIDs(neurons, filterPre))
            preIds.sort()
            if(preIds):
                batch = {
                    "descriptor": "{}-{}".format(column, cellType),
                    "excitatory": cellType != "INH",
                    "preIds": preIds
                }
                batches.append(batch)
    return batches


def getPostIdsC2(neurons):
    filterSpec = util_filter.getPostFilter()
    filterSpec["region_whitelist"] = ["C2", "S1_Septum_C2"]
    return util_filter.filterNIDs(neurons, filterSpec)


def writeDSCDict(filename, dsc):
    with open(filename, "w+") as f:
        f.write("post_id,DSC\n")
        for postId, value in dsc.items():
            if(value):
                f.write("{},{:6f}\n".format(postId, value))


def processBatch(batch, networkDir, outfolder, gridDescriptor, boundsDescriptor):
    preIds = batch["preIds"]
    postIdsFilter = batch["postIds"]
    descriptor = batch["descriptor"]
    print("batch {}, start pre-ids {}".format(descriptor, len(preIds)))

    if(batch["excitatory"]):
        colsPost = (0, 1)
    else:
        colsPost = (0, 2)

    cubesPre = set()
    dataPre = {}  # preId -> {cube -> boutons}
    dataPost = {}  # cubeId -> {[postIds], [pstNorm]}

    util_time.startTimer("batch {}, load pre".format(descriptor))
    for preId in preIds:
        data = util_feature_IO.readAxonFeaturesForDSC(os.path.join(networkDir, "subcellular_features_presynaptic_{}_{}".format(gridDescriptor, boundsDescriptor), "{}.csv".format(preId)))
        dataPre[preId] = data
        cubesPre |= set(data.keys())
    util_time.writeTimer("batch {}, load pre".format(descriptor))

    util_time.startTimer("batch {}, load post".format(descriptor))
    k = 0
    for cube in cubesPre:
        if(k % 500 == 0):
            print("batch {}, load cube ({}/{})".format(descriptor, k, len(cubesPre)))
        k += 1
        filename = os.path.join(networkDir, "cube_index_post_{}_{}".format(gridDescriptor, boundsDescriptor), "cube_{}_{}_{}.csv".format(cube[0], cube[1], cube[2]))
        if(os.path.exists(filename)):
            data = np.loadtxt(filename, delimiter=",", skiprows=1, usecols=colsPost).reshape(-1, 2)
            postIds, values = splitColumns(data)
            valNorm = np.sum(values)
            if(valNorm):
                pstNorm = np.divide(values, valNorm)
                dataPost[cube] = {
                    "postIds": postIds,
                    "pstNorm": pstNorm
                }
    util_time.writeTimer("batch {}, load post".format(descriptor))
    cubesPost = set(dataPost.keys())
    util_time.startTimer("batch {}, compute".format(descriptor))
    k = 0    
    for preId, cube_boutons in dataPre.items():        
        k += 1
        dsc = {}        
        for cube, boutons in cube_boutons.items():            
            if(cube in cubesPost):
                postProps = dataPost[cube]
                postIds = postProps["postIds"]
                pstNorm = postProps["pstNorm"]
                dscValues = np.multiply(boutons, pstNorm)
                for m in range(0, len(postIds)):
                    postId = postIds[m]
                    if(postIdsFilter is None or postId in postIdsFilter):
                        if(postId not in dsc):
                            dsc[postId] = 0
                        dsc[postId] += dscValues[m]
        writeDSCDict(os.path.join(outfolder, "{}_DSC.csv".format(preId)), dsc)
        print("batch {}, processed {} ({}/{})".format(descriptor, preId, k, len(preIds)))

    util_time.writeTimer("batch {}, compute".format(descriptor))


def printUsageAndExit():
    print("Usage:")
    print("calc_DSC_mp.py network-dir grid-descriptor mode [num-workers]")
    exit()

if __name__ == "__main__":
    warnings.filterwarnings('ignore')

    if(len(sys.argv) != 5):
        printUsageAndExit()

    networkDir = sys.argv[1]    
    gridDescriptor = sys.argv[2]
    boundsDescriptor = sys.argv[3]
    numWorkers = int(sys.argv[4])    

    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    if(boundsDescriptor == "C2-volume"):
        batches = getPreBatches(neurons, ["C2"])
        postIds = getPostIdsC2(neurons)
    elif(boundsDescriptor == "all"):
        batches = getPreBatches(neurons, constants.getColumns())
        postIds = None # apply no filter
    else:
        raise ValueError()

    outfolder = os.path.join(networkDir, "DSC_{}_{}".format(gridDescriptor, boundsDescriptor))
    util.makeCleanDir(outfolder)

    
    parameters = []

    for i in range(0, len(batches)):
        batch = batches[i]
        batch["postIds"] = postIds
        parameters.append((batch, networkDir, outfolder, gridDescriptor, boundsDescriptor))

    util_time.startTimer("PROCESS")    
    with mp.Pool(numWorkers) as p:
        try:
            p.starmap(processBatch, parameters)
        except RuntimeError as e:
            print('aborting', e)
            p.close()
    util_time.writeTimer("PROCESS")
