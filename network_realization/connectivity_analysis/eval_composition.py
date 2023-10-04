import os
import sys
import numpy as np
import json
import multiprocessing as mp

import constants
import util_feature_IO
import util
import util_meta
import util_geometry
import util_version
import util_batch


def evalCubeStatsPost(networkDir, outfolder, ids, neurons, gridDescriptor):
    data = {}
    k = 0
    for nid in ids:
        if(k % 100 == 0):
            print(k, len(ids))
        k += 1
        ct = neurons[nid]["cell_type"]
        exc = ct <= 10
        features = util_feature_IO.readDendriteFeatures(os.path.join(networkDir, "subcellular_features_postsynaptic_{}_all".format(gridDescriptor), "{}.csv".format(nid)))
        for ixiyiz, branches in features.items():
            if(ixiyiz not in data.keys()):
                data[ixiyiz] = getEmptyCube()
            for branch in branches:
                length = branch["length"]
                pstExc = branch["pstExc"]
                pstInh = branch["pstInh"]
                if(exc):
                    data[ixiyiz]["lengthExc"] += length
                    data[ixiyiz]["contactSitesExc"] += pstExc + pstInh
                    data[ixiyiz]["pst_exc-to-exc"] += pstExc
                    data[ixiyiz]["pst_inh-to-exc"] += pstInh
                else:
                    data[ixiyiz]["lengthInh"] += length
                    data[ixiyiz]["contactSitesInh"] += pstExc + pstInh
                    data[ixiyiz]["pst_exc-to-inh"] += pstExc
                    data[ixiyiz]["pst_inh-to-inh"] += pstInh
                data[ixiyiz]["branches"] += 1
            data[ixiyiz]["neurons"] += 1
    writeCubeComposition(os.path.join(outfolder, "cube_composition_post_{}.csv".format(gridDescriptor)), data)


def evalCubeStatsPre(networkDir, outfolder, ids, neurons, gridDescriptor):
    data = {}
    k = 0
    for nid in ids:
        if(k % 100 == 0):
            print(k, len(ids))
        k += 1
        ct = neurons[nid]["cell_type"]
        exc = ct <= 10
        vpm = ct == 10
        features = util_feature_IO.readAxonFeatures(os.path.join(networkDir, "subcellular_features_presynaptic_{}_all".format(gridDescriptor), "{}.csv".format(nid)))
        for ixiyiz, branches in features.items():
            if(ixiyiz not in data.keys()):
                data[ixiyiz] = getEmptyCube()
            for branch in branches:
                length = branch["length"]
                boutons = branch["boutons"]
                if(exc):
                    data[ixiyiz]["lengthExc"] += length
                    data[ixiyiz]["contactSitesExc"] += boutons
                else:
                    data[ixiyiz]["lengthInh"] += length
                    data[ixiyiz]["contactSitesInh"] += boutons
                if(vpm):
                    data[ixiyiz]["lengthVPM"] += length
                    data[ixiyiz]["contactSitesVPM"] += boutons
                data[ixiyiz]["branches"] += 1 
            data[ixiyiz]["neurons"] += 1
    writeCubeComposition(os.path.join(outfolder, "cube_composition_pre_{}.csv".format(gridDescriptor)), data)


def getEmptyCube():
    return {
        "lengthExc": 0,
        "lengthInh": 0,
        "contactSitesExc": 0,
        "contactSitesInh": 0,
        "lengthVPM": 0,
        "contactSitesVPM": 0,
        "branches": 0,
        "neurons": 0,
        "pst_exc-to-exc" : 0,
        "pst_exc-to-inh" : 0,
        "pst_inh-to-exc" : 0,        
        "pst_inh-to-inh" : 0
    }


def writeCubeComposition(filename, cubes):
    with open(filename, "w+") as f:
        f.write("ix,iy,iz,length_exc,length_inh,contactSites_exc,contactSites_inh,length_vpm,contactSites_vpm,branches,neurons,pst_exc-to-exc,pst_exc-to-inh,pst_inh-to-exc,pst_inh-to-inh\n")
        for ixiyiz, props in cubes.items():
            f.write("{},{},{},{:.3f},{:.3f},{:.3f},{:.3f},{:.3f},{:.3f},{},{},{:.3f},{:.3f},{:.3f},{:.3f}\n".format(*ixiyiz, props["lengthExc"],
                                                                                        props["lengthInh"], props["contactSitesExc"], 
                                                                                        props["contactSitesInh"], props["lengthVPM"], 
                                                                                        props["contactSitesVPM"], props["branches"], props["neurons"],
                                                                                        props["pst_exc-to-exc"], props["pst_exc-to-inh"],
                                                                                        props["pst_inh-to-exc"], props["pst_inh-to-inh"]))


def filterCubes(data, grid):
    ixiyiz_grid = set(grid.keys())
    idx = []
    for i in range(0, data.shape[0]):
        ixiyiz = (data[i, 0], data[i, 1], data[i, 2])
        if(ixiyiz in ixiyiz_grid):
            idx.append(i)
    return data[idx, :]


def summarize(networkDir, outfolder, gridDescriptor):
    grid = util_meta.loadGrid_ixiyiz(os.path.join(networkDir, "grid_{}_all.csv".format(gridDescriptor)), onlyInside=True)
    preComposition = np.loadtxt(os.path.join(outfolder, "cube_composition_pre_{}.csv".format(gridDescriptor)), delimiter=",", skiprows=1)
    preCompositionFiltered = filterCubes(preComposition, grid)
    postComposition = np.loadtxt(os.path.join(outfolder, "cube_composition_post_{}.csv".format(gridDescriptor)), delimiter=",", skiprows=1)
    postCompositionFiltered = filterCubes(postComposition, grid)

    lengthDendriteExc = np.sum(postCompositionFiltered[:, 3])
    lengthDendriteInh = np.sum(postCompositionFiltered[:, 4])
    pstExc = np.sum(postCompositionFiltered[:, 5])
    pstInh = np.sum(postCompositionFiltered[:, 6])
    pst_exc_to_exc = np.sum(postCompositionFiltered[:, 11])
    pst_exc_to_inh = np.sum(postCompositionFiltered[:, 12])
    pst_inh_to_exc = np.sum(postCompositionFiltered[:, 13])
    pst_inh_to_inh = np.sum(postCompositionFiltered[:, 14])

    lengthAxonExc = np.sum(preCompositionFiltered[:, 3])
    lengthAxonInh = np.sum(preCompositionFiltered[:, 4])
    boutonsExc = np.sum(preCompositionFiltered[:, 5])
    boutonsInh = np.sum(preCompositionFiltered[:, 6])
    lengthVPM = np.sum(preCompositionFiltered[:, 7])
    boutonsVPM = np.sum(preCompositionFiltered[:, 8])

    data = {
        "length_dendrite_exc": "{:.3f}".format(lengthDendriteExc),
        "length_dendrite_inh": "{:.3f}".format(lengthDendriteInh),
        "length_axon_exc": "{:.3f}".format(lengthAxonExc),
        "length_axon_inh": "{:.3f}".format(lengthAxonInh),
        "pst_exc": "{:.3f}".format(pstExc),
        "pst_inh": "{:.3f}".format(pstInh),
        "pst_exc_to_exc": "{:.3f}".format(pst_exc_to_exc),
        "pst_exc_to_inh": "{:.3f}".format(pst_exc_to_inh),
        "pst_inh_to_exc": "{:.3f}".format(pst_inh_to_exc),
        "pst_inh_to_inh": "{:.3f}".format(pst_inh_to_inh),
        "boutons_exc": "{:.3f}".format(boutonsExc),
        "boutons_inh": "{:.3f}".format(boutonsInh),
        "length_VPM": "{:.3f}".format(lengthVPM),
        "boutons_VPM" : "{:.3f}".format(boutonsVPM),
        "boutons_total_million": "{:.0f}".format(0.000001 * (boutonsExc + boutonsInh)),
        "pst_total_million": "{:.0f}".format(0.000001 * (pstExc + pstInh)),
        "length_axon_total_meter": "{:.0f}".format(0.000001 * (lengthAxonExc + lengthAxonInh)),
        "length_dendrite_total_meter": "{:.0f}".format(0.000001 * (lengthDendriteExc + lengthDendriteInh))
    }
    with open(os.path.join(outfolder, "length_{}.json".format(util_version.getDate())), "w+") as f:
        json.dump(data, f)


def getEmptyCubeStats(synapticSide):
    stats = {
        "length": 0,
        "branches": 0,
        "contributingCells" : 0
    }
    if(synapticSide == "pre"):
        stats["boutons"] = 0
    return stats


def mergeCubeStats(results, synapticSide):
    statsAggregated = {}
    for stats in results.values():
        for cube, values in stats.items():
            if(cube not in statsAggregated):
                statsAggregated[cube] = values
            else:
                statsAggregated[cube]["length"] += values["length"]
                statsAggregated[cube]["branches"] += values["branches"]
                statsAggregated[cube]["contributingCells"] += values["contributingCells"]
                if(synapticSide == "pre"):
                    statsAggregated[cube]["boutons"] += values["boutons"]
    return statsAggregated


def writeCubeStats(filename, stats, synapticSide):
    cubes = list(stats.keys())
    cubes.sort()
    with open(filename, "w+") as f:
        if(synapticSide == "pre"):
            f.write("ix,iy,iz,length,contributing_cells,branches,boutons\n")
        else:
            f.write("ix,iy,iz,length,contributing_cells,branches\n")
        for cube in cubes:
            values = stats[cube]
            if(synapticSide == "pre"):
                f.write("{},{},{},{:.4f},{},{},{:.4f}\n".format(cube[0], cube[1], cube[2], values["length"], values["contributingCells"], values["branches"], values["boutons"]))
            else:
                f.write("{},{},{},{:.4f},{},{}\n".format(cube[0], cube[1], cube[2], values["length"], values["contributingCells"], values["branches"]))


def cubeStatsRefVolumeBatch(batchIndex, results, networkDir, neuronIds, gridDescriptor, synapticSide):
    grid = util_meta.loadGridCells(os.path.join(networkDir, "grid_{}_ref-volume.csv".format(gridDescriptor)))
    stats = {}
    for gridCell in grid:
        stats[gridCell] = getEmptyCubeStats(synapticSide)
    n = len(neuronIds)
    for i in range(0,len(neuronIds)):
        neuronId = neuronIds[i]
        printProgress(batchIndex, neuronId, i, n)
        if(synapticSide == "pre"):
            features = util_feature_IO.readAxonFeatures(os.path.join(networkDir, "subcellular_features_{}synaptic_{}_all".format(synapticSide, gridDescriptor), "{}.csv".format(neuronId)))
        else:
            features = util_feature_IO.readDendriteFeatures(os.path.join(networkDir, "subcellular_features_{}synaptic_{}_all".format(synapticSide, gridDescriptor), "{}.csv".format(neuronId)))
        for cube, branches in features.items():
            if cube in grid:
                for branch in branches:
                    stats[cube]["length"] += branch["length"]
                    stats[cube]["branches"] += 1
                    if(synapticSide == "pre"):
                        stats[cube]["boutons"] += branch["boutons"]
                stats[cube]["contributingCells"] += 1
    results[batchIndex] = stats


def cubeStatsRefVolume(networkDir, gridDescriptor, synapticSide):
    util_geometry.setGridSize(gridDescriptor)
    neuronIds = np.loadtxt(os.path.join(networkDir, "innervating_ref-volume_{}.txt".format(synapticSide)), dtype=int)

    # filter inside
    if(synapticSide == "post"):
        allowedIds = util_batch.getPostsynaptic_vS1(networkDir)    
    elif(synapticSide == "pre"):        
        allowedIds = util_batch.getPresynapticInside(networkDir)  
    else:
        raise ValueError(synapticSide)
    neuronIds = list(set(neuronIds) & set(allowedIds))

    np.random.shuffle(neuronIds)

    batches = np.array_split(neuronIds, util_batch.NUM_WORKERS)
    manager = mp.Manager()
    results = manager.dict()
    processes = []
    for i in range(0, len(batches)):
        p = mp.Process(target=cubeStatsRefVolumeBatch, args=(i, results, networkDir, batches[i], gridDescriptor, synapticSide, ))
        processes.append(p)
        p.start()
    for p in processes:
        p.join()

    statsAggregated = mergeCubeStats(results, synapticSide)
    filename = os.path.join(networkDir, "eval", "cube-stats_{}_ref-volume_{}.csv".format(gridDescriptor, synapticSide))
    writeCubeStats(filename, statsAggregated, synapticSide)


def getInnervatingIds(batchIndex, neuronIds, networkDir, gridDescriptor, synapticSide, boxMin, boxMax, results):
    n = len(neuronIds)
    util_geometry.setGridSize(gridDescriptor)
    innervatingIds = []
    for i in range(0, n):
        neuronId = neuronIds[i]
        if(i % 50 == 0):
            print("batch {}: {} ({}/{})".format(batchIndex, neuronId, i, n))
        filenamePre = os.path.join(networkDir, "subcellular_features_{}synaptic_{}_all".format(synapticSide, gridDescriptor), "{}.csv".format(neuronId))
        ixiyiz = np.loadtxt(filenamePre, delimiter=",", skiprows=1, usecols=(0, 1, 2)).astype(int)
        nrows = ixiyiz.shape[0]
        for k in range(0, nrows):
            if(util_geometry.cubeInBounds(ixiyiz[k], boxMin, boxMax)):
                innervatingIds.append(neuronId)
                break
    results[batchIndex] = innervatingIds


def printProgress(batchIndex, neuronId, i, n):
    if(i % 50 == 0):
        print("batch {}: {} ({}/{})".format(batchIndex, neuronId, i, n))


def printUsageAndExit():
    print("Usage:")
    print("eval_composition.py network-dir mode grid-descriptor [num-workers]")
    print("")
    print("network-dir:         network directory")
    print("mode:                length, cube-stats-ref-volume")
    print("grid-descriptor:     50-50-50")
    sys.exit(1)


if __name__ == '__main__':
    if(len(sys.argv) not in [4,5]):
        printUsageAndExit()

    networkDir = sys.argv[1]
    mode = sys.argv[2]
    gridDescriptor = sys.argv[3]
    if(len(sys.argv) == 5):
        numWorkers = int(sys.argv[4])
    else:
        numWorkers = mp.cpu_count()

    outfolder = os.path.join(networkDir, "eval")
    util.makeDir(outfolder)

    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))   

    if(mode == "length"):
        outfolderLength = os.path.join(outfolder, "length")
        util.makeDir(outfolderLength)
        postIds = util_batch.getPostsynaptic_vS1(networkDir)    
        preIds = util_batch.getPresynapticInside(networkDir)          
        evalCubeStatsPost(networkDir, outfolderLength, postIds, neurons, gridDescriptor)
        evalCubeStatsPre(networkDir, outfolderLength, preIds, neurons, gridDescriptor)    
        summarize(networkDir, outfolderLength, gridDescriptor)
    elif(mode == "cube-stats-ref-volume"):
        cubeStatsRefVolume(networkDir, gridDescriptor, "pre")
        cubeStatsRefVolume(networkDir, gridDescriptor, "post")   
    else:
        raise RuntimeError("invalid mode: {}".format(mode))
