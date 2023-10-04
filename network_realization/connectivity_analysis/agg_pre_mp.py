import sys
import os
import multiprocessing as mp
from ctypes import c_float
import numpy as np

import util_feature_IO
import util
import util_batch
import util_geometry
import constants


def processBatch(batchIndex, nids, networkDir, gridDescriptor, boundsDescriptor, outProps):    
    boutons = outProps["boutons"]
    lock = outProps["lock"]
    gridBounds = outProps["gridBounds"]
    ixiyiz_min = gridBounds["ixiyiz_min"]
    ixiyiz_max = gridBounds["ixiyiz_max"]

    data = {}
    n = len(nids)    
    for i in range(0, n):
        nid = nids[i]
        if(i % 50 == 0):
            print("batch {}: {} ({}/{})".format(batchIndex, nid, i, n))
        features = util_feature_IO.readBoutonsPerCube(os.path.join(networkDir, "subcellular_features_presynaptic_{}_{}".format(gridDescriptor, boundsDescriptor), "{}.csv".format(nid)), None)
        if(features):
            for cube, boutonValue in features.items():                
                if(cube not in data):
                    data[cube] = 0         
                data[cube] += boutonValue

    lock.acquire()
    for cube, boutonSum in data.items():
        if(util_geometry.indicesInBounds(cube, ixiyiz_min, ixiyiz_max)):
            arrayIndex = util_geometry.getArrayIndex(gridBounds, cube)
            boutons[arrayIndex] += boutonSum
    lock.release()


def processBatchCubeIndex(batchIndex, nids, networkDir, gridDescriptor, boundsDescriptor, outProps):    
    boutons = outProps["boutons"]
    lock = outProps["lock"]
    writeLock = outProps["writeLock"]
    gridBounds = outProps["gridBounds"]
    ixiyiz_min = gridBounds["ixiyiz_min"]
    ixiyiz_max = gridBounds["ixiyiz_max"]
    outfolder = outProps["outfolder"]

    data = {} # cube -> [(preId, boutons)]
    n = len(nids)
    for i in range(0, n):
        nid = nids[i]
        if(i % 50 == 0):
            print("batch {}: {} ({}/{})".format(batchIndex, nid, i, n))
        features = util_feature_IO.readBoutonsPerCube(os.path.join(networkDir, "subcellular_features_presynaptic_{}_{}".format(gridDescriptor, boundsDescriptor), "{}.csv".format(nid)), None)
        if(features):
            for cube, boutonValue in features.items():                
                if(util_geometry.indicesInBounds(cube, ixiyiz_min, ixiyiz_max)):
                    if(cube not in data):
                        data[cube] = []         
                    data[cube].append((nid, boutonValue))

    for cube, preIds_boutons in data.items():
        filename = os.path.join(outfolder, "cube_{}_{}_{}.csv".format(cube[0], cube[1], cube[2]))
        writeLock.acquire()    
        existed = os.path.exists(filename)
        with open(filename, "a") as f:
            if(not existed):
                f.write("pre_id,boutons\n")
            for preId, boutons in preIds_boutons:
                f.write("{},{:.6f}\n".format(preId, boutons))
        writeLock.release()


def writeBoutons(outfile, boutons, gridBounds):
    with open(outfile, "w+") as f:
        f.write("ix,iy,iz,boutons\n")
        for i in range(0, gridBounds["numCells"]):
            cube = util_geometry.getCubeFromArrayIndex(gridBounds, i)
            f.write("{},{},{},{:.6f}\n".format(cube[0], cube[1], cube[2], boutons[i]))


def process(networkDir, outfile, gridDescriptor, boundsDescriptor, numWorkers, axonFilter):
    if(boundsDescriptor in ["ref-volume", "C2-volume", "L4-volume"]):
        nids = util.getNeuronIds(os.path.join(networkDir, "innervating_{}_pre.txt".format(boundsDescriptor)))
    elif(boundsDescriptor == "model-volume"):
        if(axonFilter == "all"):
            nids = util_batch.getAllPresynaptic(networkDir)
        elif(axonFilter == "exc-inside"):
            nids = util_batch.getPresynapticExcInside(networkDir)
        elif(axonFilter == "inh-inside"):
            nids = util_batch.getPresynapticInhInside(networkDir)
        elif(axonFilter == "vpm-inside"):
            nids = util_batch.getAllVPM(networkDir)            
        else:
            raise ValueError("invalid axon filter: {}".format(axonFilter))
    else:
        raise NotImplementedError
    
    # bounds of model volume
    boxMin, boxMax = constants.getModelVolume()
    util_geometry.setGridSize(gridDescriptor)
    gridBounds = util_geometry.getGridBounds(boxMin, boxMax)
    numCells = gridBounds["numCells"]    
    boutons = mp.Array(c_float, int(numCells), lock=False)
    lock = mp.Lock()

    outProps = {
        "boutons" : boutons,
        "lock" : lock,
        "gridBounds" : gridBounds
    }

    batches = np.array_split(nids, numWorkers)
    processes = []    
    for i in range(0, len(batches)):        
        p = mp.Process(target=processBatch, args=(i, batches[i], networkDir, gridDescriptor, boundsDescriptor, outProps))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()      

    writeBoutons(outfile, boutons, gridBounds)


def processCubeIndex(networkDir, outfolder, gridDescriptor, boundsDescriptor, numWorkers, axonFilter):
    if(boundsDescriptor in ["ref-volume", "C2-volume"]):
        nids = util.getNeuronIds(os.path.join(networkDir, "innervating_{}_pre.txt".format(boundsDescriptor)))
        boxMin, boxMax = constants.getModelVolume()
    elif(boundsDescriptor == "L4-volume"):
        nids = util.getNeuronIds(os.path.join(networkDir, "innervating_{}_pre.txt".format(boundsDescriptor)))
        boxMin, boxMax = constants.getL4Volume()
    else:
        raise NotImplementedError
    
    util_geometry.setGridSize(gridDescriptor)
    gridBounds = util_geometry.getGridBounds(boxMin, boxMax)
    numCells = gridBounds["numCells"]    
    boutons = mp.Array(c_float, int(numCells), lock=False)
    lock = mp.Lock()
    writeLock = mp.Lock()

    outProps = {
        "boutons" : boutons, # not used
        "lock" : lock,
        "gridBounds" : gridBounds,
        "writeLock" : writeLock,
        "outfolder" : outfolder
    }

    batches = np.array_split(nids, numWorkers)
    processes = []    
    for i in range(0, len(batches)):        
        p = mp.Process(target=processBatchCubeIndex, args=(i, batches[i], networkDir, gridDescriptor, boundsDescriptor, outProps))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()      

    
def printUsageAndExit():
    print("agg_pre_mp.py network-dir grid-descriptor bounds-descriptor mode [num-workers]")
    print("")
    print("gridDescriptor:      50-50-50, 100-100-100")
    print("bounds:              model-volume, ref-volume, C2-volume, L4-volume")
    print("mode:                sum-boutons, cube-index")
    sys.exit(1)


if __name__ == "__main__":
    if(len(sys.argv) not in [5,6]):
        printUsageAndExit()
    networkDir = sys.argv[1]
    gridDescriptor = sys.argv[2]
    boundsDescriptor = sys.argv[3]
    if(boundsDescriptor not in ["model-volume", "ref-volume", "C2-volume", "L4-volume"]):
        printUsageAndExit()
    mode = sys.argv[4]
    if(len(sys.argv) == 6):
        numWorkers = int(sys.argv[5])
    else:
        numWorkers = mp.cpu_count()
    
    if(mode == "sum-boutons"):
        axonFilters = ["exc-inside", "inh-inside"]
        for axonFilter in axonFilters:
            outfile = os.path.join(networkDir, "boutons_{}_{}_{}.csv".format(axonFilter, gridDescriptor, boundsDescriptor))        
            process(networkDir, outfile, gridDescriptor, boundsDescriptor, numWorkers, axonFilter)    
    elif(mode == "cube-index"):
        outfolder = os.path.join(networkDir, "cube_index_pre_{}_{}".format(gridDescriptor, boundsDescriptor))
        util.makeCleanDir(outfolder)
        processCubeIndex(networkDir, outfolder, gridDescriptor, boundsDescriptor, numWorkers, None)
    else:
        raise ValueError(mode)
    
