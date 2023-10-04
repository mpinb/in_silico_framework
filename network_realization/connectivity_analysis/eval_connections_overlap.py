import os
import sys
import glob
import multiprocessing as mp
import numpy as np
import matplotlib.pyplot as plt
import math

import util
import util_feature_IO
import util_batch
import util_geometry


def processBatch(batchIndex, results, dscFolder, preFolder, postFolder, outfolder, preIds):
    postCache = {}
    dscValues = []
    sharedCubes = []
    for i in range(0, len(preIds)):        
        print("batch", batchIndex, dscFolder, i, "of", len(preIds))
        preId = preIds[i]        
        filenameDSC = os.path.join(dscFolder, "{}_DSC.csv".format(preId))
        if(os.path.exists(filenameDSC)):
            cubesPre = util_feature_IO.getCubesFromFeatures(os.path.join(preFolder, "{}.csv".format(preId)))            
            dsc = np.loadtxt(filenameDSC, skiprows=1, delimiter=",", usecols=(0, 1)).reshape((-1, 2))
            for k in range(0, dsc.shape[0]):
                postId = int(dsc[k, 0])
                dscVal = dsc[k, 1]
                if(postId not in postCache):                    
                    postCache[postId] = util_feature_IO.getCubesFromFeatures(os.path.join(postFolder, "{}.csv".format(postId)))
                    print("batch", batchIndex, "loaded post", len(postCache))
                    if(postCache[postId] is None):
                        raise RuntimeError("could not load post features of {}".format(postId))
                cubesPost = postCache[postId]
                dscValues.append(dscVal)
                sharedCubes.append(len(cubesPre & cubesPost))
    with open(os.path.join(outfolder, "dsc_overlapping-cubes_batch-{}".format(batchIndex)), "w+") as f:
        for i in range(0, len(dscValues)):
            f.write("{:.4f},{}\n".format(dscValues[i], sharedCubes[i]))



def process(networkDir, outfolder, gridDescriptor, numWorkers):
    preIds = util_batch.getC2Presynaptic(networkDir)
    np.random.shuffle(preIds)
    batchesPre = np.array_split(preIds, numWorkers)

    dscFolder = os.path.join(networkDir, "DSC_{}_C2-volume".format(gridDescriptor))
    postFolder = os.path.join(networkDir, "subcellular_features_postsynaptic_{}_all".format(gridDescriptor))
    preFolder = os.path.join(networkDir, "subcellular_features_presynaptic_{}_all".format(gridDescriptor))

    processes = []
    manager = mp.Manager()
    results = manager.dict()
    for i in range(0, len(batchesPre)):
        p = mp.Process(target=processBatch, args=(i, results, dscFolder, preFolder, postFolder, outfolder, batchesPre[i],))
        processes.append(p)
        p.start()
    for p in processes:
        p.join()


def createPlot(outfolder):
    D = np.loadtxt(outfolder, "dsc_overlapping-cubes_batch-0", delimiter=",")
    fraction = np.divide(D[:,0],D[:,1])
    bins = np.zeros(1000)
    for i in range(0, bins.size, 100):
        val = fraction[i]
        if(val > 1):
            val = 1
        idx = math.floor(val * 1000)
        idx == 1000
        idx -= 1
        bins[idx] += 1
    
    plt.plot(bins)    
    plt.xlim([0,1])
    plt.yscale("log")
    plt.savefig(os.path.join(outfolder, "connections_overlap.png"))
   


def printUsageAndExit():
    print("eval_connections_overlap.py network-dir mode num-workers")
    print()
    print("mode:     aggregate, plot")
    exit()


if __name__ == "__main__":
    if(len(sys.argv) != 4):
        printUsageAndExit()
    networkDir = sys.argv[1]
    mode = sys.argv[2]
    numWorkers = int(sys.argv[3])

    gridDescriptor = "50-50-50"

    outfolder = os.path.join(networkDir, "eval", "connections_overlap")

    if(mode == "aggregate"):
        util.makeCleanDir(outfolder)
        process(networkDir, outfolder, gridDescriptor, numWorkers)
    elif(mode == "plot"):
        createPlot(outfolder)
    else:
        raise RuntimeError("invalid mode: {}".format(mode))
