import os
import sys
import glob
import multiprocessing as mp
import numpy as np
import matplotlib.pyplot as plt

import util
import util_feature_IO


def printUsageAndExit():
    print("eval_branch_pairs_synapses.py network-dir mode num-workers")
    print()
    print("mode:     aggregate, plot")
    exit()


def getFiles(networkDir, gridDescriptor, boundDescriptor, synapticSide):
    files = glob.glob(os.path.join(networkDir, "subcellular_features_{}synaptic_{}_{}".format(synapticSide, gridDescriptor, boundDescriptor), "*.csv"))
    return files


def getEmptyStats():
    return {
        "branchesPre": 0,
        "neuronsPre": 0,
        "branchesPost": 0,
        "neuronsPost": 0,
        "boutons": 0
    }


def processBatch(batchIndex, results, files, synapticSide):
    stats = {}
    for i in range(0, len(files)):
        if(i % 50 == 0):
            print("batch", batchIndex, "item", i, "of", len(files))
        filename = files[i]
        if(synapticSide == "pre"):
            features = util_feature_IO.readAxonFeatures(filename)
            for cube, branches in features.items():
                if(cube not in stats):
                    stats[cube] = getEmptyStats()
                for branch in branches:
                    stats[cube]["branchesPre"] += 1
                    stats[cube]["boutons"] += branch["boutons"]
                stats[cube]["neuronsPre"] += 1
        else:
            features = util_feature_IO.readDendriteFeatures(filename)
            for cube, branches in features.items():
                if(cube not in stats):
                    stats[cube] = getEmptyStats()
                stats[cube]["branchesPost"] += len(branches)
                stats[cube]["neuronsPost"] += 1
    results[batchIndex] = stats


def mergeResults(results):
    statsMerged = {}
    for statsSingle in results.values():
        for cube, values in statsSingle.items():
            if (cube not in statsMerged):
                statsMerged[cube] = getEmptyStats()
            statsMerged[cube]['branchesPre'] += values["branchesPre"]
            statsMerged[cube]['neuronsPre'] += values["neuronsPre"]
            statsMerged[cube]['branchesPost'] += values["branchesPost"]
            statsMerged[cube]['neuronsPost'] += values["neuronsPost"]
            statsMerged[cube]['boutons'] += values["boutons"]
    return statsMerged


def writeCubeStats(filename, stats):
    with open(filename, "w+") as f:
        f.write("ix,iy,iz,branches_pre,neurons_pre,branches_post,neurons_post,boutons\n")
        for cube, values in stats.items():
            f.write("{},{},{},{},{},{},{},{:.4f}\n".format(cube[0], cube[1], cube[2], values["branchesPre"], values["neuronsPre"], values["branchesPost"], values["neuronsPost"], values["boutons"]))


def aggregate(outfolder, gridDescriptor, filesPre, filesPost, numWorkers):
    batchesPre = np.array_split(filesPre, numWorkers)
    batchesPost = np.array_split(filesPost, numWorkers)

    processes = []
    manager = mp.Manager()
    results = manager.dict()
    for i in range(0, len(batchesPre)):
        p = mp.Process(target=processBatch, args=(i, results, batchesPre[i], "pre", ))
        processes.append(p)
        p.start()
    for i in range(len(batchesPre), len(batchesPre)+len(batchesPost)):
        p = mp.Process(target=processBatch, args=(i, results, batchesPost[i-len(batchesPre)], "post", ))
        processes.append(p)
        p.start()
    for p in processes:
        p.join()

    merged = mergeResults(results)
    writeCubeStats(os.path.join(outfolder, "cube-stats_{}.csv".format(gridDescriptor)), merged)


def createPlot(outfolder, gridDescriptors):
    idx = np.arange(len(gridDescriptors))
    pairsMean = []
    boutonsMean = []
    for gridDescriptor in gridDescriptors:
        D = np.loadtxt(os.path.join(outfolder, "cube-stats_{}.csv".format(gridDescriptor)), delimiter=",", skiprows=1, usecols=(3,4,5))
        pairs = np.multiply(D[:,0],D[:,1])
        boutons = D[:,2]
        pairsMean.append(np.mean(pairs))
        boutonsMean.append(np.mean(boutons))
    plt.plot(idx, pairsMean,  marker="o", label="branch pairs")
    plt.plot(idx, boutonsMean,  marker="o", label="synapses")
    plt.legend()
    plt.yscale("log")
    plt.xlabel("overlap volume (min: 1-1-1; max 100-100-100)")
    plt.savefig(os.path.join(outfolder, "branchPairsSynapses.png"))


if __name__ == "__main__":
    if(len(sys.argv) != 4):
        printUsageAndExit()
    networkDir = sys.argv[1]
    mode = sys.argv[2]
    numWorkers = int(sys.argv[3])

    gridDescriptors = ["100-100-100", "50-50-50", "25-25-25", "10-10-10", "5-5-5", "1-1-1"]
    boundDescriptor = "ref-volume"

    outfolder = os.path.join(networkDir, "eval", "branch_pairs_synapses")

    if(mode == "aggregate"):
        util.makeCleanDir(outfolder)
        for gridDescriptor in gridDescriptors:
            filesPre = getFiles(networkDir, gridDescriptor, boundDescriptor, "pre")
            filesPost = getFiles(networkDir, gridDescriptor, boundDescriptor, "post")
            aggregate(outfolder, gridDescriptor, filesPre, filesPost, numWorkers)
    elif(mode == "plot"):
        gridDescriptors.reverse()
        createPlot(outfolder, gridDescriptors)
    else:
        raise RuntimeError("invalid mode: {}".format(mode))
