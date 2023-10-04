import os
import sys
import glob
import math
import multiprocessing as mp
import numpy as np
import matplotlib.pyplot as plt
import traceback

import util
import util_feature_IO
import util_meta


def writeFloatFlat(filename, values, append=True):
    if(not values):
        return
    writeMode = "w"
    if(append):
        writeMode = "a"
    with open(filename, writeMode) as f:
        for val in values:
            f.write("{:.4f}\n".format(val))


def processBatch(batchIndex, networkDir, outfolder, cubes, gridDescriptor, boundsDescriptor, maxK):

    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))

    for cube in cubes:
        try:
            postCache = {}

            cube = (cube[0], cube[1], cube[2])

            clusterProbabilitiesBranch = np.zeros(maxK+2)
            clusterProbabilitiesCell = np.zeros(maxK+2)
            filenameBranches = os.path.join(outfolder, "cube_{}_{}_{}_branch-probabilities.csv".format(cube[0], cube[1], cube[2]))
            filenamePairs = os.path.join(outfolder, "cube_{}_{}_{}_cell-probabilities.csv".format(cube[0], cube[1], cube[2]))

            preIds = np.loadtxt(os.path.join(
                networkDir, "cube_index_pre_{}_{}/cube_{}_{}_{}.csv".format(gridDescriptor, boundsDescriptor, cube[0], cube[1], cube[2])), delimiter=",", skiprows=1, usecols=0).astype(int).tolist()
            D_post = np.loadtxt(os.path.join(networkDir, "cube_index_post_{}_{}/cube_{}_{}_{}.csv".format(gridDescriptor,
                                                                                                          boundsDescriptor, cube[0], cube[1], cube[2])), delimiter=",", skiprows=1).reshape((-1, 3))

            postIds = D_post[:, 0].astype(int).tolist()
            pstAll = np.sum(D_post[:, 1:3], axis=0)

            for i in range(0, len(preIds)):
                preId = preIds[i]
                print("batch", batchIndex, i, "of", len(preIds))

                dataPre = util_feature_IO.readAxonFeatures(os.path.join(networkDir, "subcellular_features_presynaptic_{}_{}".format(gridDescriptor, boundsDescriptor), "{}.csv".format(preId)))
                branchesPre = dataPre[cube]

                exc = neurons[preId]["cell_type"] != 11 # 11 -> INH
                if(exc):
                    pstAllVal = pstAll[0]
                else:
                    pstAllVal = pstAll[1]
                if(not pstAllVal):
                    continue

                for j in range(0, len(postIds)):
                    postId = postIds[j]
                    if(postId not in postCache):
                        dataPost = util_feature_IO.readDendriteFeatures(os.path.join(
                            networkDir, "subcellular_features_postsynaptic_{}_{}".format(gridDescriptor, boundsDescriptor), "{}.csv".format(postId)))
                        if(not dataPost):
                            raise RuntimeError("not found pre {}".format(postId))
                        postCache[postId] = dataPost
                    branchesPost = postCache[postId][cube]

                    dscNewPair = 0
                    for branchPre in branchesPre:
                        for branchPost in branchesPost:

                            if(exc):
                                dscNewBranch = branchPre["boutons"] * branchPost["pstExc"] / pstAllVal
                            else:
                                dscNewBranch = branchPre["boutons"] * branchPost["pstInh"] / pstAllVal

                            clusterProbabilitiesBranch += computeSingleValue(dscNewBranch, maxK)
                            dscNewPair += dscNewBranch

                    clusterProbabilitiesCell += computeSingleValue(dscNewPair, maxK)

            np.savetxt(filenameBranches, clusterProbabilitiesBranch, delimiter=",")
            np.savetxt(filenamePairs, clusterProbabilitiesCell, delimiter=",")

        except Exception as e:
            with open(os.path.join(outfolder, "cube_{}_{}_{}_error.txt".format(cube[0], cube[1], cube[2])), "w+") as f:
                f.write("{}\n\n".format(e))
                f.write(traceback.format_exc())
                print(traceback.format_exc())


def process(networkDir, outfolder, gridDescriptor, numWorkers, maxK):
    if(gridDescriptor == "50-50-50"):
        allCubes = list(util_meta.loadGridCells(os.path.join(networkDir, "grid_50-50-50_ref-volume.csv")))
        boundsDescriptor = "ref-volume"
    elif(gridDescriptor == "100-100-50"):
        allCubes = list(util_meta.loadGridCells(os.path.join(networkDir, "grid_100-100-50_L4-volume.csv")))
        boundsDescriptor = "L4-volume"
    else:
        raise ValueError(gridDescriptor)
    
    print("num cubes", len(allCubes))
    np.random.shuffle(allCubes)

    batches = np.array_split(allCubes, numWorkers)

    processes = []
    for i in range(0, len(batches)):
        p = mp.Process(target=processBatch, args=(i, networkDir, outfolder, batches[i], gridDescriptor, boundsDescriptor, maxK))
        processes.append(p)
        p.start()
    for p in processes:
        p.join()


def getProb(lamb, k):
    return (lamb**k) * math.exp(-lamb) / math.factorial(k)


def computeSingle(filename, mode, maxK):
    D = np.zeros(maxK+2)
    with open(filename) as f:
        for line in f:
            dsc = float(line.rstrip())
            sumProbs = 0
            for k in range(0, maxK+1):
                p = getProb(dsc, k)
                sumProbs += p
                D[k] += p
            D[maxK+1] += 1 - sumProbs
    return D.tolist()


def computeVector(dsc, maxK):
    n = dsc.shape[0]
    D = np.zeros((n, maxK+2))
    for k in range(0, maxK + 1):
        D[:,k] = (np.multiply(np.power(dsc, k), np.exp(-dsc)) / math.factorial(k)).flatten()
    D[:,maxK + 1] = 1 - np.sum(D, axis=1)
    return D


def computeSingleValue(dsc, maxK):
    D = np.zeros(maxK+2)
    sumProbs = 0
    for k in range(0, maxK+1):
        p = getProb(dsc, k)
        sumProbs += p
        D[k] += p
    D[maxK+1] += 1 - sumProbs
    return D


def getCube(filename):
    parts = filename.split(".")[0].split("_")
    return (int(parts[1]), int(parts[2]), int(parts[3]))


def computeBatch(batchIndex, results, files, idxs, mode, maxK):
    stats = {}
    k = 0
    for idx in idxs:
        k += 1
        filename = files[idx]
        cube = getCube(os.path.basename(filename))
        stats[cube] = computeSingle(filename, mode, maxK)
        print("batch {}, processed {}/{}".format(batchIndex, k, len(idxs)))
    results[batchIndex] = stats


def compute(infolderCompute, outfolderCompute, numWorkers, mode, maxK):
    files = glob.glob(os.path.join(infolderCompute, "*-{}-pairs.csv".format(mode)))    
    idx = np.arange(len(files))
    batches = np.array_split(idx, numWorkers)

    manager = mp.Manager()
    results = manager.dict()
    processes = []
    for i in range(0, len(batches)):
        p = mp.Process(target=computeBatch, args=(i, results, files, batches[i], mode, maxK))
        processes.append(p)
        p.start()
    for p in processes:
        p.join()

    with open(os.path.join(outfolderCompute, "summary_{}.csv".format(mode)), "w") as f:
        f.write("ix,iy,iz")
        for k in range(0, maxK+2):
            if(k == maxK+1):
                f.write(",k>{}".format(maxK))
            else:
                f.write(",k{}".format(k))

        f.write("\n")
        for cubes_probs in results.values():
            for cube, probs in cubes_probs.items():
                f.write("{},{},{}".format(cube[0], cube[1], cube[2]))
                for k in range(0, maxK+2):
                    f.write(",{:.3f}".format(probs[k]))
                f.write("\n")


def summarize(infolderCompute, outfolderCompute, mode, maxK):
    files = glob.glob(os.path.join(infolderCompute, "*_{}-probabilities.csv".format(mode)))

    with open(os.path.join(outfolderCompute, "summary_{}.csv".format(mode)), "w") as f:
        # write header
        f.write("ix,iy,iz")
        for k in range(0, maxK+2):
            if(k == maxK+1):
                f.write(",k>{}".format(maxK))
            else:
                f.write(",k{}".format(k))
        f.write("\n")

        # write values for cubes
        for filename in files:
            probs = np.loadtxt(filename, delimiter=",")
            cube = getCube(os.path.basename(filename))
            f.write("{},{},{}".format(cube[0], cube[1], cube[2]))
            for k in range(0, maxK+2):
                f.write(",{:.3f}".format(probs[k]))
            f.write("\n")


def createPlot(outfolder, mode):
    filename = os.path.join(outfolder, "summary_{}.csv".format(mode))
    with open(filename) as f:
        lines = f.readlines()
        parts = lines[0].rstrip().split(",")
        cols = len(parts)-3
        D = np.zeros((len(lines)-1, cols))
        for i in range(1, len(lines)):
            parts = lines[i].rstrip().split(",")
            for k in range(0, cols):
                D[i-1, k] = float(parts[k+3])

    minVal = np.min(D, axis=0)
    maxVal = np.max(D, axis=0)
    medianVal = np.median(D, axis=0)
    idx = np.arange(D.shape[1])

    plt.plot(idx, minVal,  marker=".", label="min")
    plt.plot(idx, maxVal,  marker=".", label="max")
    plt.plot(idx, medianVal,  marker="o", label="median")
    plt.legend()
    plt.yscale("log")
    plt.xlabel("connections per {} pair".format(mode))
    plt.savefig(os.path.join(outfolder, "clustersize_{}.png".format(mode)))


def printUsageAndExit():
    print("eval_cluster.py network-dir mode grid-descriptor num-workers")
    print()
    print("mode:     aggregate, compute, plot")
    exit()


if __name__ == "__main__":
    if(len(sys.argv) != 5):
        printUsageAndExit()
    networkDir = sys.argv[1]
    mode = sys.argv[2]
    gridDescriptor = sys.argv[3]
    numWorkers = int(sys.argv[4])
    maxK = 8

    outfolder = os.path.join(networkDir, "eval", "connections_cluster_{}".format(gridDescriptor))
    infolderCompute = os.path.join(networkDir, "eval", "connections_cluster_{}".format(gridDescriptor))
    outfolderCompute = os.path.join(networkDir, "eval", "connections_cluster_{}".format(gridDescriptor), "stats")

    if(mode == "aggregate"):
        util.makeCleanDir(outfolder)
        process(networkDir, outfolder, gridDescriptor, numWorkers, maxK)
    elif(mode == "compute"):
        util.makeCleanDir(outfolderCompute)
        summarize(infolderCompute, outfolderCompute, "branch", maxK)
        summarize(infolderCompute, outfolderCompute, "cell", maxK)
    elif(mode == "plot"):
        createPlot(outfolderCompute, "branch")
        plt.clf()
        createPlot(outfolderCompute, "cell")
    else:
        raise RuntimeError("invalid mode: {}".format(mode))
