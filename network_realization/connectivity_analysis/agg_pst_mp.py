import sys
import os
import multiprocessing as mp
import numpy as np
import glob

import util_meta
import util_feature_IO
import util
import util_filter
import util_batch


def processBatch(batchIndex, networkDir, nids, gridDescriptor, boundsDescriptor, tmpOutFolder):
    if(boundsDescriptor):
        gridCells = util_meta.loadGridCells(os.path.join(networkDir, "grid_{}_{}.csv".format(gridDescriptor, boundsDescriptor)))
    data = {}
    n = len(nids)
    for i in range(0, n):
        nid = nids[i]
        if(i % 50 == 0):
            print("batch {}: {} ({}/{})".format(batchIndex, nid, i, n))
        features = util_feature_IO.readDendriteFeatures(os.path.join(networkDir, "subcellular_features_postsynaptic_{}_{}".format(gridDescriptor, boundsDescriptor), "{}.csv".format(nid)))
        if(features):
            for cube, branches in features.items():
                if(not gridCells or cube in gridCells):
                    if(cube not in data):
                        data[cube] = []
                    pstExc = 0
                    pstInh = 0
                    for branch in branches:
                        pstExc += branch["pstExc"]
                        pstInh += branch["pstInh"]
                    data[cube].append((nid, pstExc, pstInh))    
    for cube, values in data.items():
        filename = os.path.join(tmpOutFolder, "cube_{}_{}_{}.csv".format(cube[0], cube[1], cube[2]))
        util_feature_IO.writeCubeIndex(filename, values)


def mergeResults(results):
    merged = {}
    for singleResults in results.values():
        for cube, values in singleResults.items():
            if(cube not in merged):
                merged[cube] = []
            merged[cube].extend(values)
    return merged


def writeMerged(tmpFolder, nBatches, outfolder):
    data = {}
    for i in range(0, nBatches):        
        files = glob.glob(os.path.join(tmpFolder,"{}".format(i),"*.csv"))        
        k = 0
        for filename in files:
            k += 1
            if(k % 50 == 0):                
                print("merging",i,k,len(files))
            basename = os.path.basename(filename)
            if(basename not in data):
                data[basename] = []
            lines = util.getLines(filename)
            data[basename].extend(lines)
    for basename, lines in data.items():
        with open(os.path.join(outfolder,basename), "w+") as f:
            f.write("post_id,pst_exc,pst_inh\n")
            for line in lines:
                f.write(line + "\n")



def process(networkDir, outfolder, tmpFolder, gridDescriptor, boundsDescriptor, numWorkers):
    if(boundsDescriptor in ["ref-volume", "C2-volume", "L4-volume"]):
        nids = util.getNeuronIds(os.path.join(networkDir, "innervating_{}_post.txt".format(boundsDescriptor)))
    elif(boundsDescriptor == "all-inh"):
        nids = util_batch.getPostsynapticInh(networkDir)
        print("num ids", len(nids))
        boundsDescriptor = "all"
    elif(boundsDescriptor == "all-exc"):
        nids = util_batch.getPostsynapticExc(networkDir)
        print("num ids", len(nids))
        boundsDescriptor = "all"
    else:
        neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
        nids = list(util_filter.filterNIDs(neurons, util_filter.getPostFilter()))
        np.random.shuffle(nids)

    batches = np.array_split(nids, numWorkers)
    processes = []
    for i in range(0, len(batches)):
        tmpOutFolder = os.path.join(tmpFolder, "{}".format(i))
        util.makeCleanDir(tmpOutFolder)
        p = mp.Process(target=processBatch, args=(i, networkDir, batches[i], gridDescriptor, boundsDescriptor, tmpOutFolder))
        processes.append(p)
        p.start()
    for p in processes:
        p.join()

    writeMerged(tmpFolder, len(batches), outfolder)
    

def mergeSingleFile(networkDir, outfolder, gridDescriptor, boundsDescriptor):
    files = glob.glob(os.path.join(outfolder, "*.csv"))    
    data = {}
    k = 0
    for filename in files:
        k += 1
        if(k % 50 == 0):
            print("single file", k)
        parts = os.path.basename(filename).split(".")[0].split("_")
        cube = (int(parts[1]), int(parts[2]), int(parts[3]))
        D = np.loadtxt(filename, skiprows=1, delimiter=",", usecols=(1,2)).reshape((-1,2))
        pstVal = np.sum(D,axis=0)
        data[cube] = pstVal
    with open(os.path.join(networkDir, "agg_pst_{}_{}.csv".format(gridDescriptor, boundsDescriptor)), "w+") as f:
        f.write("ix,iy,iz,pst_exc,pst_inh\n")
        for cube, values in data.items():
            f.write("{},{},{},{:.4f},{:.4f}\n".format(cube[0], cube[1], cube[2], values[0], values[1]))


def printUsageAndExit():
    print("agg_pst_mp.py network-dir grid-descriptor bounds-descriptor num-workers")
    print("")
    print("gridDescriptor:      50-50-50, 100-100-100")
    print("bounds:              all, all-inh, all-exc, ref-volume, C2-volume, L4-volume")
    sys.exit(1)


if __name__ == "__main__":
    if(len(sys.argv) not in [5]):
        printUsageAndExit()
    networkDir = sys.argv[1]
    gridDescriptor = sys.argv[2]
    boundsDescriptor = sys.argv[3]
    if(boundsDescriptor not in ["all", "all-inh", "all-exc", "ref-volume", "C2-volume", "L4-volume"]):
        printUsageAndExit()
    numWorkers = int(sys.argv[4])

    outfolder = os.path.join(networkDir, "cube_index_post_{}_{}".format(gridDescriptor, boundsDescriptor))
    
    util.makeCleanDir(outfolder)
    tmpFolder = os.path.join(networkDir, "tmp_{}_{}".format(gridDescriptor, boundsDescriptor))
    util.makeCleanDir(tmpFolder)

    process(networkDir, outfolder, tmpFolder, gridDescriptor, boundsDescriptor, numWorkers)
    
    mergeSingleFile(networkDir, outfolder, gridDescriptor, boundsDescriptor)