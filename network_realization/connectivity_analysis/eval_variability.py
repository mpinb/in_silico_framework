import sys
import os
import multiprocessing as mp
import ctypes
import numpy as np

import util
import util_morphology
import util_meta
import util_feature_IO
import util_geometry
import constants


def createMorphologyFile(networkDir, morphologyFile):
    graphset = util_morphology.loadGraphset(networkDir)
    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    nids = list(graphset.keys())
    nids.sort()
    with open(morphologyFile, "w+") as f:
        f.write("neuron_id,dendrite_file,axon_file\n")
        for nid in nids:
            synapticSide = neurons[nid]["synaptic_side"]
            if synapticSide in [0, 2]:
                idx = len(graphset[nid])-1
                axonFile = os.path.basename(graphset[nid][idx]["file"])
            else:
                axonFile = "n/a"
            if synapticSide in [1, 2]:
                dendriteFile = os.path.basename(graphset[nid][0]["file"])
            else:
                dendriteFile = "n/a"
            f.write("{},{},{}\n".format(nid, dendriteFile, axonFile))


def getMorphologyDescriptor(filepath):
    if(filepath == "n/a"):
        return filepath
    else:
        return os.path.basename(filepath)


def excludePreNeuron(axonDescriptor, column, columnDescriptors):
    colDescriptor = axonDescriptor.split("_registered_")[1].replace(".am", "").replace("_stripped", "")
    columnDescriptors.add(colDescriptor)
    return column != colDescriptor


def createMorphologyIndex(morphologyFile, nids, neurons, regions, synapticSide):
    column_celltype_morphology = {}  # (column, cellType) -> {morphology}
    neuron_morphology = {}  # nid -> morphology
    nids = set(nids)
    nidsFiltered = set()
    columnDescriptors = set()

    with open(morphologyFile) as f:
        lines = f.readlines()
        for i in range(1, len(lines)):
            parts = lines[i].rstrip().split(",")
            nid = int(parts[0])
            if(nid in nids):
                dendriteDescriptor = getMorphologyDescriptor(parts[1])
                axonDescriptor = getMorphologyDescriptor(parts[2])

                regionId = neurons[nid]["region"]
                regionName = regions[regionId]["name"]
                column = util_meta.getRegionDisplayName(regionName)
                cellType = neurons[nid]["cell_type"]

                if(synapticSide == "post" or not excludePreNeuron(axonDescriptor, column, columnDescriptors)):
                    nidsFiltered.add(nid)

                    if((column, cellType) not in column_celltype_morphology):
                        column_celltype_morphology[(column, cellType)] = set()

                    if(synapticSide == "post"):
                        column_celltype_morphology[(column, cellType)].add(dendriteDescriptor)
                        neuron_morphology[nid] = dendriteDescriptor
                    else:
                        column_celltype_morphology[(column, cellType)].add(axonDescriptor)
                        neuron_morphology[nid] = axonDescriptor

    numMorphologies = []
    numMorphologies_keys = []
    for column_celltype, morphologies in column_celltype_morphology.items():
        numMorphologies_keys.append(column_celltype)
        numMorphologies.append(len(morphologies))

    print("columDescriptors", columnDescriptors)
    idx = np.argmax(numMorphologies)
    maxMorphologies = numMorphologies[idx]
    print("column ct max morphologies", column_celltype_morphology[numMorphologies_keys[idx]])
    print("num max morphologies", maxMorphologies, numMorphologies_keys[idx])

    nidsFiltered = list(nidsFiltered)
    nidsFiltered.sort()
    return column_celltype_morphology, neuron_morphology, maxMorphologies, nidsFiltered


def generateMultiplicitiesForNumMorphologies(nids, neurons, column_celltype_morphology, neuron_morphology, numMorphologies, maxMorphologies, maxRealizations):
    multiplicities = []  # numMorphpolgies -> [neuronId -> multiplicity]
    combinations = util.nCr(maxMorphologies, numMorphologies)
    print("------")
    print(numMorphologies, maxMorphologies, combinations, maxRealizations)
    print("col-ct", len(column_celltype_morphology))

    for k in range(0, maxRealizations):

        currentMultiplicities = {}

        enabledMorphologies = {}
        for column_cellType, morphologies in column_celltype_morphology.items():
            enabledMorphologies[column_cellType] = util.getRandomSubset(morphologies, numMorphologies)        

        enabledIndex = {}  # (column, cellType) -> [nid]
        disabledIndex = {}  # (column, cellType) -> disabledCount

        for nid in nids:
            regionId = neurons[nid]["region"]
            regionName = regions[regionId]["name"]
            column = util_meta.getRegionDisplayName(regionName)
            cellType = neurons[nid]["cell_type"]
            morphology = neuron_morphology[nid]

            if((column, cellType) not in enabledIndex):
                enabledIndex[(column, cellType)] = []
                disabledIndex[(column, cellType)] = 0

            if(morphology in enabledMorphologies[(column, cellType)]):
                currentMultiplicities[nid] = 1
                enabledIndex[(column, cellType)].append(nid)
            else:
                currentMultiplicities[nid] = 0
                disabledIndex[(column, cellType)] += 1

        for column_cellType, reassignCount in disabledIndex.items():
            if(reassignCount):
                enabledIds = enabledIndex[(column_cellType)]
                a, b = np.divmod(reassignCount, len(enabledIds))
                for nid in enabledIds:
                    currentMultiplicities[nid] += a
                enabledIdsSubset = util.getRandomSubset(set(enabledIds), b)
                for nid in enabledIdsSubset:
                    currentMultiplicities[nid] += 1

        multiplicities.append(currentMultiplicities)
        print("generated realization: {} {}".format(numMorphologies, k))

    return multiplicities


def getMaxNumRealizations(multiplicities):
    numRealizations = []
    for realizations in multiplicities.values():
        numRealizations.append(len(realizations))
    return np.max(numRealizations)


def initArrays(outProps, maxNumRealizations):
    numCells = outProps["gridBounds"]["numCells"]

    for i in range(0, maxNumRealizations):
        outProps["lengthArrays"].append(mp.Array(ctypes.c_float, int(numCells), lock=False))
        outProps["lengthArrayLocks"].append(mp.Lock())
        outProps["contributingArrays"].append(mp.Array(ctypes.c_int, int(numCells), lock=False))
        outProps["contributingArrayLocks"].append(mp.Lock())
        outProps["boutonArrays"].append(mp.Array(ctypes.c_float, int(numCells), lock=False))
        outProps["boutonArrayLocks"].append(mp.Lock())
        outProps["branchesArrays"].append(mp.Array(ctypes.c_int, int(numCells), lock=False))
        outProps["branchesArrayLocks"].append(mp.Lock())
        outProps["pathSomaArrays"].append(mp.Array(ctypes.c_float, int(numCells), lock=False))
        outProps["pathSomaArrayLocks"].append(mp.Lock())
        outProps["cellTypeArrays"].append(mp.Array(ctypes.c_int, int(numCells), lock=False))
        outProps["cellTypeArrayLocks"].append(mp.Lock())        


def clearArrays(outProps):
    numCells = outProps["gridBounds"]["numCells"]

    for lengthArray in outProps["lengthArrays"]:
        for i in range(0, numCells):
            lengthArray[i] = 0
    for contributingArray in outProps["contributingArrays"]:
        for i in range(0, numCells):
            contributingArray[i] = 0
    for boutonArray in outProps["boutonArrays"]:
        for i in range(0, numCells):
            boutonArray[i] = 0
    for branchesArray in outProps["branchesArrays"]:
        for i in range(0, numCells):
            branchesArray[i] = 0
    for pathSomaArray in outProps["pathSomaArrays"]:
        for i in range(0, numCells):
            pathSomaArray[i] = 0
    for cellTypeArray in outProps["cellTypeArrays"]:
        for i in range(0, numCells):
            cellTypeArray[i] = 2**20


def writeCubeStats(outfolder, numMorphologies, numRealizations, outProps, synapticSide):
    numCells = outProps["gridBounds"]["numCells"]
    gridBounds = outProps["gridBounds"]

    for k in range(0, numRealizations):
        filename = os.path.join(outfolder, "{}_morphologies-{}_realization-{}".format(synapticSide, numMorphologies, k))
        lengthArray = outProps["lengthArrays"][k]
        contributingArray = outProps["contributingArrays"][k]
        boutonsArray = outProps["boutonArrays"][k]
        branchesArray = outProps["branchesArrays"][k]
        pathSomaArray = outProps["pathSomaArrays"][k]
        cellTypesArray = outProps["cellTypeArrays"][k]

        with open(filename, "w+") as f:
            f.write("ix,iy,iz,length,contributing_cells,boutons,branches,path_soma_sum,cell_types\n")
            for i in range(0, numCells):
                ixiyiz = util_geometry.getCubeFromArrayIndex(gridBounds, i)
                length = lengthArray[i]
                contributingCells = contributingArray[i]
                boutons = boutonsArray[i]
                branches = branchesArray[i]
                pathSoma = pathSomaArray[i]
                cellTypes = getCellTypes(cellTypesArray[i])
                f.write("{},{},{},{:.1f},{},{:.1f},{},{:.1f},{}\n".format(ixiyiz[0], ixiyiz[1], ixiyiz[2], length, contributingCells, boutons, branches, pathSoma, cellTypes))

        print("written {} {}".format(numMorphologies, k))


def setCellType(intRep, ct):
    bitstring = list("{:b}".format(intRep))
    bitstring[len(bitstring)-ct-1] = "1"
    return int("".join(bitstring), 2)


def getCellTypes(intRep):
    total = 0
    bitstring = list("{:b}".format(intRep))
    for ct in range(0, 12):
        total += int(bitstring[len(bitstring) - ct - 1] == "1")
    return total


def registerCubeStatsBatch(batchIndex, outProps, networkDir, nids, multiplicities, synapticSide):
    gridDescriptor = "50-50-50"
    gridBounds = outProps["gridBounds"]
    ixiyiz_min = gridBounds["ixiyiz_min"]
    ixiyiz_max = gridBounds["ixiyiz_max"]
    numRealizations = len(multiplicities)

    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))

    for i in range(0, len(nids)):
        nid = nids[i]
        cellType = neurons[nid]["cell_type"]
        cubeStats = {}  # arrayIndex -> {}
        if(synapticSide == "pre"):
            filename = os.path.join(networkDir, "subcellular_features_presynaptic_{}_all".format(gridDescriptor), "{}.csv".format(nid))
            features = util_feature_IO.readAxonFeatures(filename)
            if(not features):
                print("no features", nid, filename)
        else:
            filename = os.path.join(networkDir, "subcellular_features_postsynaptic_{}_all".format(gridDescriptor), "{}.csv".format(nid))
            features = util_feature_IO.readDendriteFeatures(filename)
        if(features):
            for ixiyiz, branches in features.items():
                if(util_geometry.indicesInBounds(ixiyiz, ixiyiz_min, ixiyiz_max)):
                    arrrayIndex = util_geometry.getArrayIndex(gridBounds, ixiyiz)
                    length = 0
                    numBranches = 0
                    boutons = 0
                    pathSoma = 0
                    for branch in branches:
                        length += branch["length"]
                        numBranches += 1
                        if(synapticSide == "pre"):
                            boutons += branch["boutons"]
                        pathSoma += branch["distSoma"]
                    cubeStats[arrrayIndex] = {
                        "length": length,
                        "boutons": boutons,
                        "branches": numBranches,
                        "pathSoma": pathSoma
                    }
        

        for k in range(0, numRealizations):
            multiplicity = multiplicities[k][nid]
            if(multiplicity):
                lengthArray = outProps["lengthArrays"][k]
                lengthArrayLock = outProps["lengthArrayLocks"][k]
                contributingArray = outProps["contributingArrays"][k]
                contributingArrayLock = outProps["contributingArrayLocks"][k]
                boutonArray = outProps["boutonArrays"][k]
                boutonArrayLock = outProps["boutonArrayLocks"][k]
                branchesArray = outProps["branchesArrays"][k]
                branchesArrayLock = outProps["branchesArrayLocks"][k]
                pathSomaArray = outProps["pathSomaArrays"][k]
                pathSomaArrayLock = outProps["pathSomaArrayLocks"][k]
                cellTypeArray = outProps["cellTypeArrays"][k]
                cellTypeArrayLock = outProps["cellTypeArrayLocks"][k]

                lengthArrayLock.acquire()
                for arrayIndex, stats in cubeStats.items():
                    lengthArray[arrayIndex] += multiplicity * stats["length"]
                lengthArrayLock.release()

                contributingArrayLock.acquire()
                for arrayIndex, stats in cubeStats.items():
                    contributingArray[arrayIndex] += multiplicity
                contributingArrayLock.release()

                boutonArrayLock.acquire()
                for arrayIndex, stats in cubeStats.items():
                    boutonArray[arrayIndex] += multiplicity * stats["boutons"]
                boutonArrayLock.release()

                branchesArrayLock.acquire()
                for arrayIndex, stats in cubeStats.items():
                    branchesArray[arrayIndex] += multiplicity * stats["branches"]
                branchesArrayLock.release()

                pathSomaArrayLock.acquire()
                for arrayIndex, stats in cubeStats.items():
                    pathSomaArray[arrayIndex] += multiplicity * stats["pathSoma"]
                pathSomaArrayLock.release()

                cellTypeArrayLock.acquire()
                for arrayIndex, stats in cubeStats.items():
                    intRep = cellTypeArray[arrayIndex]
                    cellTypeArray[arrayIndex] = setCellType(intRep, cellType)
                cellTypeArrayLock.release()

        if((i+1) % 50 == 0):
            print("batch {}: processed {}/{}".format(batchIndex, i+1, len(nids)))


def computeCubeStats(networkDir, outfolder, nids, numMorphologies, realizations, synapticSide, numWorkers, outProps):

    batches = np.array_split(nids, numWorkers)

    clearArrays(outProps)

    processes = []
    for i in range(0, len(batches)):
        p = mp.Process(target=registerCubeStatsBatch, args=(i, outProps, networkDir, batches[i], realizations, synapticSide))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()

    writeCubeStats(outfolder, numMorphologies, len(realizations), outProps, synapticSide)


def filterExc(nids, neurons):
    nidsFiltered = []
    for nid in nids:
        if(neurons[nid]["cell_type"] != 11):
            nidsFiltered.append(nid)
    return nidsFiltered


def getGridBounds_ref_volume(networkDir):
    boxMin, boxMax = constants.getReferenceVolume()
    util_geometry.setGridSize("50-50-50")
    gridBounds = util_geometry.getGridBounds(boxMin, boxMax)
    return gridBounds


def printUsageAndExit():
    print("eval_variability.py network-dir mode [num-workers]")
    print()
    exit()


if __name__ == "__main__":
    numArgs = len(sys.argv)
    if(numArgs not in [3, 4]):
        printUsageAndExit()
    networkDir = sys.argv[1]
    mode = sys.argv[2]
    if(numArgs == 4):
        numWorkers = int(sys.argv[3])
    else:
        numWorkers = mp.cpu_count()

    maxNumRealizations = 500

    util.makeDir(os.path.join(networkDir, "eval"))

    outfolder = os.path.join(networkDir, "eval", "variability")
    util.makeDir(outfolder)

    batchFolder = os.path.join(outfolder, mode)
    util.makeCleanDir(batchFolder)

    morphologyFile = os.path.join(outfolder, "morphology_mapping.csv")
    if(not os.path.exists(morphologyFile)):
        createMorphologyFile(networkDir, morphologyFile)

    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    regions = util_meta.loadRegions(os.path.join(networkDir, "regions.csv"))

    if(mode == "pre"):
        nids = np.loadtxt(os.path.join(networkDir, "innervating_ref-volume_{}.txt".format("pre")), dtype=int)
        nids = filterExc(nids, neurons)
    elif(mode == "post"):
        nids = np.loadtxt(os.path.join(networkDir, "innervating_ref-volume_{}.txt".format("post")), dtype=int)
        nids = filterExc(nids, neurons)
    else:
        raise ValueError(mode)

    column_celltype_morphology, neuron_morphology, maxMorphologies, nidsFiltered = createMorphologyIndex(morphologyFile, nids, neurons, regions, mode)
    print(mode, len(nids), len(nidsFiltered), "max morphologies", maxMorphologies)

    # init shared arrays
    gridBounds = getGridBounds_ref_volume(networkDir)
    print("gridBouds", gridBounds)

    outProps = {
        "gridBounds": gridBounds,
        "lengthArrays": [],
        "lengthArrayLocks": [],
        "contributingArrays": [],
        "contributingArrayLocks": [],
        "boutonArrays": [],
        "boutonArrayLocks": [],
        "branchesArrays": [],
        "branchesArrayLocks": [],
        "pathSomaArrays": [],
        "pathSomaArrayLocks": [],
        "cellTypeArrays": [],
        "cellTypeArrayLocks": []
    }

    initArrays(outProps, maxNumRealizations)

    for numMorphologies in range(1, maxMorphologies + 1):
        realizations = generateMultiplicitiesForNumMorphologies(nidsFiltered, neurons, column_celltype_morphology, neuron_morphology, numMorphologies, maxMorphologies, maxNumRealizations)
        computeCubeStats(networkDir, batchFolder, nidsFiltered, numMorphologies, realizations, mode, numWorkers, outProps)
