import os
import sys
import time
import shutil
import datetime
import traceback
import numpy as np
import multiprocessing as mp

from . import util_amira
from . import util_selection
from . import util_feature_IO
from . import util_meta
from . import convert_nx_asc
from . import convert_nx_hoc
from .cell import CellParser
from .network_embedding import NetworkMapper


def initFolders(outputBaseFolder, postIds):
    ts = time.time()
    timeStampString = datetime.datetime.fromtimestamp(
        ts).strftime('%Y-%m-%d')
    outputFolder = os.path.join(
        outputBaseFolder, "realization_{}".format(timeStampString))
    if(os.path.exists(outputFolder)):
        shutil.rmtree(outputFolder)
    os.makedirs(outputFolder)

    postNeuronsFolder = os.path.join(outputFolder, "post_neurons")
    os.makedirs(postNeuronsFolder)

    status = {}
    for NID in postIds:
        neuronFolder = os.path.join(postNeuronsFolder, str(NID))
        os.makedirs(neuronFolder)
        status[NID] = {
            "folder": neuronFolder,
            "hocFile": os.path.join(neuronFolder, "{}.hoc".format(NID)),
            "status": 1,
            "time": 0
        }
    return outputFolder, status


def getStatusDescriptor(status):
    if(status):
        return "OK"
    else:
        return "FAIL"


def writeSummary(outputDir, status):
    with open(os.path.join(outputDir, "summary.csv"), "w+") as f:
        NIDs = list(status.keys())
        NIDs.sort()
        f.write(
            ",".join(["post_ID", "status", "time[s]"]) + "\n")
        for NID in NIDs:
            props = status[NID]
            f.write(
                ",".join([str(NID), getStatusDescriptor(props["status"]), "{:.3f}".format(props["time"])]) + "\n")


def loadPresynapticFeatures(preIds, modelDataFolder):
    featuresPre = {}
    mappedPreIds = list(set(preIds.values()))
    mappedPreIds.sort()
    for mappedPreId in mappedPreIds:
        print("unique pre_ID {}: Loading bouton distribution".format(mappedPreId))
        filenamePre = os.path.join(modelDataFolder, "RBC", "subcellular_features_presynaptic",
                                   "{}_subcellular_features_presynaptic.csv".format(mappedPreId))
        featuresPre[mappedPreId] = util_feature_IO.loadFeatures(
            filenamePre, util_feature_IO.getSpec_subcellular_features_presynaptic_sparse())
    return featuresPre


def packParameters(networkProps, spatialGraphSet, preIds, postIds, postProps, outputFolder, randomSeed):
    seedIncrement = 7
    seeds = randomSeed + np.arange(0, seedIncrement * len(postIds), seedIncrement)

    args = []
    for i in range(0, len(postIds)):
        postId = postIds[i]
        args.append((networkProps, spatialGraphSet, postId, postProps[postId], preIds, outputFolder, seeds[i]))
    return args


def processPostNeuron(networkProps, spatialGraphSet, postId, postProps, preIds, outputFolder, randomSeed):
    np.random.seed(randomSeed)  # called for each postsynaptic neuron
    start = time.time()
    logMessage = ""

    try:
        fileName = spatialGraphSet[postId][0]["file"]
        transformation = spatialGraphSet[postId][0]["transformation"]
        g = util_amira.readSpatialGraph(fileName, transformation)
        convert_nx_asc.postprocessGraph(g, separateSoma=False, relabel=False)
        convert_nx_hoc.save_HOC(g, postProps["hocFile"])
        cellParser = CellParser(postProps["hocFile"], postId)
        postCell = cellParser.get_cell()
        networkMapper = NetworkMapper(postCell, networkProps)
        networkMapper.create_network_embedding()
        networkMapper.write_population_output_files(postProps["folder"])
    except Exception as e:
        track = traceback.format_exc()
        logMessage = track

    end = time.time()
    if(not logMessage):
        logMessage = "Execution time: {:.1f}s".format(end-start)
    with open(os.path.join(postProps["folder"], "{}.log".format(postId)), "w+") as f:
        f.write(logMessage)


def create_realization(modelDataFolder, preIdsFile, postIdsFile, outputBaseFolder, randomSeed=5000, poolSize=5):
    """
    This method generates an explicit subcellular-level realization of the statistical 
    barrel cortex connectome, meaning spatially resolved synaptic contacts on postsynaptic
    compartments of selected neurons in the network. 

    Pre- and postsynaptic neuron IDs that become part of the network realization can 
    be freely specified. Presynaptic neurons are always treated as point-like objects. 
    To achieve recurrent connections among the postynaptic population, postsynaptic 
    neuron IDs can be included in the presynaptic selection. In a typical scenario,
    the presynaptic selection will include all neurons in the barrel cortex, and the 
    postsynaptic selection all neurons from a specific layer in a specific column.

    Parameters
    ----------
    modelDataFolder : str
        Folder with model data of vS1.        
    preIdsFile: str
        Text file with IDs of presynaptic neurons (two colums: <neuron ID> <mapped neuron ID / axon>).
    postIdsFile: str
        Text file with IDs of postsynaptic neurons (one column: <neuron ID>).
    outputBaseFolder: str
        Base path where actual output folder is created (named: realization_YYYY-MM-DD).
    randomSeed: int
        Random seed for numpy (synapse counts are drawn from a Poisson distribution).
    poolSize: int
        Number of proccesses for parallel execution.
    """

    postIds = util_selection.readIds(postIdsFile)
    preIds = util_selection.readPreIdsMap(preIdsFile)
    outputFolder, postProps = initFolders(outputBaseFolder, postIds)

    networkProps = {
        "modelDataFolder": modelDataFolder,
        "neurons": util_meta.loadNeuronProps(os.path.join(modelDataFolder, "RBC", "neurons.csv")),
        "regions": util_meta.loadRegions(os.path.join(modelDataFolder, "regions.csv")),
        "cellTypes": util_meta.loadCellTypes(os.path.join(modelDataFolder, "cell_types.csv")),
        "preIds": preIds,
        "grid": util_meta.convertGridNumericId(util_meta.loadGrid(os.path.join(modelDataFolder, "meta", "grid_vS1.csv"))),
        "featuresPre": loadPresynapticFeatures(preIds, modelDataFolder),
        "agg_pst": util_feature_IO.loadFeatures(
            os.path.join(modelDataFolder, "RBC", "agg_pst.csv"), util_feature_IO.getSpec_agg_pst())
    }

    spatialGraphSet = util_amira.readSpatialGraphSet(
        os.path.join(modelDataFolder, "morphologies", "MorphologiesWithNeuronIDs.am"))

    shutil.copy2(os.path.join(modelDataFolder, "cell_types.csv"), outputFolder)
    shutil.copy2(os.path.join(modelDataFolder, "regions.csv"), outputFolder)
    shutil.copy2(os.path.join(modelDataFolder, "RBC", "neurons.csv"), outputFolder)

    parameters = packParameters(networkProps, spatialGraphSet, preIds, postIds, postProps, outputFolder, randomSeed)

    start = time.time()
    with mp.Pool(poolSize) as p:
        p.starmap(processPostNeuron, parameters)

    print("Total excution time {:.1f}s".format(time.time()-start))
