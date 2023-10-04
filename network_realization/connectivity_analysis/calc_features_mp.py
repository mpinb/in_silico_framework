import sys
import os
import multiprocessing as mp
import traceback
import networkx as nx
import numpy as np

import constants
import util
import util_batch
import util_amira
import util_geometry
import util_graph
import util_meta
import util_time
import util_feature_IO
import util_morphology
import util_morphology_slice


def getEmptyValues(synapticSide):
    if(synapticSide == "pre"):
        return {
            "length" : 0,
            "distSoma" : [],
            "boutons"  : 0
        }
    else:
        return {
            "length" : 0,
            "distSoma" : [],
            "pstExc"  : 0,
            "pstExcApical" : 0,
            "pstExcBasal" : 0,
            "pstExcSoma" : 0,            
            "pstInh"  : 0,
            "pstInhApical" : 0,
            "pstInhBasal" : 0,
            "pstInhSoma"  : 0,
        }


def getBoutonDensity(boutonDensities, cellType, gridCells, grid, cube):
    if(cube not in gridCells):
        return 0
    else:
        return boutonDensities[cellType][grid[cube]["laminar_location"]]        


def getPostsynapticTargets(densities, cellTypeId, edgeLabel, length, area):
    pstDensities = densities[cellTypeId]
    if(edgeLabel == "Soma"):
        pstExc = pstDensities["exc"]["density_soma_length"] * length + pstDensities["exc"]["density_soma_area"] * area 
        pstInh = pstDensities["inh"]["density_soma_length"] * length + pstDensities["inh"]["density_soma_area"] * area 
    elif(edgeLabel == "ApicalDendrite"):
        pstExc = pstDensities["exc"]["density_apical_length"] * length + pstDensities["exc"]["density_apical_area"] * area 
        pstInh = pstDensities["inh"]["density_apical_length"] * length + pstDensities["inh"]["density_apical_area"] * area
    elif(edgeLabel == "BasalDendrite"):
        pstExc = pstDensities["exc"]["density_basal_length"] * length + pstDensities["exc"]["density_basal_area"] * area 
        pstInh = pstDensities["inh"]["density_basal_length"] * length + pstDensities["inh"]["density_basal_area"] * area
    else:
        raise RuntimeError("invalid label {}".format(edgeLabel))
    return pstExc, pstInh


def updateTraversalState(node_cube_branch, cube_branch_values, traversal_state, synapticSide, event):
    """
    traversal_state = {
        "nodeStart"
        "nodeEnd"
        "nextCube"
        "activeCube"
        "activeBranch" 
    }
    """
    traversal_state["activeCube"] = traversal_state["nextCube"]
    cube = traversal_state["activeCube"]
    
    # first step on edge
    if(event == "firstStep"):        
        nodeStart = traversal_state["nodeStart"]
        if((nodeStart, cube) in node_cube_branch):                        
            existingBranchId = node_cube_branch[(nodeStart, cube)]
            traversal_state["activeBranch"] = existingBranchId
            return cube_branch_values[cube][existingBranchId]
        else:
            # check new cube visited
            if(cube not in cube_branch_values):
                cube_branch_values[cube] = {}
            # create new branch
            newBranchId = len(cube_branch_values[cube])
            cube_branch_values[cube][newBranchId] = getEmptyValues(synapticSide)
            node_cube_branch[(nodeStart, cube)] = newBranchId
            traversal_state["activeBranch"] = newBranchId
            return cube_branch_values[cube][newBranchId]
    
    # go from one cube into next
    if(event == "crossBorder"):
        # check new cube visited
        if(cube not in cube_branch_values):
            cube_branch_values[cube] = {}
        # create new branch
        newBranchId = len(cube_branch_values[cube])
        cube_branch_values[cube][newBranchId] = getEmptyValues(synapticSide)
        traversal_state["activeBranch"] = newBranchId
        return cube_branch_values[cube][newBranchId]

    # set branch in target node
    if(event == "lastStep"):
        nodeEnd = traversal_state["nodeEnd"]        
        node_cube_branch[(nodeEnd, cube)] = traversal_state["activeBranch"]
        return None
         

def filterFeatures(boundsFilter, cube_branch_values):        
    filtered = {}    
    gridCells = boundsFilter["gridCells"]
    if(gridCells):
        for cube, branch_values in cube_branch_values.items():
            if(cube in gridCells):
                filtered[cube] = branch_values
    else:        
        ixiyiz_min = boundsFilter["ixiyiz_min"]
        ixiyiz_max = boundsFilter["ixiyiz_max"]
        for cube, branch_values in cube_branch_values.items():
            if(util_geometry.indicesInBounds(cube, ixiyiz_min, ixiyiz_max)):
                filtered[cube] = branch_values
    #print("filter", len(cube_branch_values), len(filtered))
    return filtered


def getBoundsFilter(networkDir, boundsDescriptor, gridDescriptor, outProps):
    if(boundsDescriptor is None):
        return None            
    boundsFilter = {}
    if(outProps):
        boundsFilter["gridCells"] = None
        boundsFilter["boxMin"] = outProps["gridBounds"]["boxMin"]
        boundsFilter["boxMax"] = outProps["gridBounds"]["boxMax"]
        boundsFilter["ixiyiz_min"] = outProps["gridBounds"]["ixiyiz_min"]
        boundsFilter["ixiyiz_max"] = outProps["gridBounds"]["ixiyiz_max"]
    else:
        gridBounds = util_meta.loadGrid_ixiyiz(os.path.join(networkDir, "grid_{}_{}.csv".format(gridDescriptor, boundsDescriptor)))
        boundsFilter["gridCells"] = set(gridBounds.keys())
        if(boundsDescriptor == "ref-volume"):
            boundsFilter["boxMin"], boundsFilter["boxMax"] = constants.getReferenceVolume()
        elif(boundsDescriptor == "C2-volume"):
            boundsFilter["boxMin"], boundsFilter["boxMax"] = constants.getC2Volume()
        else:
            raise RuntimeError("Invalid bounds descriptor: {}".format(boundsDescriptor))
    return boundsFilter


def getBranchCount(cube_branch_values):
    count = 0
    for branches in cube_branch_values.values():
        count += len(branches)
    return count


def registerFeatures(neuronId, cube_branch_values, outProps):
    if(outProps["type"] == "pstAll"):
        pstAllExcArray = outProps["pstAllExc"]
        pstAllInhArray = outProps["pstAllInh"]
        lock = outProps["lock"]
        gridBounds = outProps["gridBounds"]        
        D = {} # cubeArrayIdx -> (pstExc, pstInh)
        for cube, branches in cube_branch_values.items():
            pstExc = 0
            pstInh = 0
            for values in branches.values():
                pstExc += values["pstExc"]
                pstInh += values["pstInh"]
            arrayIdx = util_geometry.getArrayIndex(gridBounds, cube)
            D[arrayIdx] = (pstExc, pstInh)
        lock.acquire()
        for idx, values in D.items(): 
            pstAllExcArray[idx] += values[0]
            pstAllInhArray[idx] += values[1]
        lock.release()     
    elif(outProps["type"] == "pst"):
        pstAllExcArray = outProps["pstAllExc"]
        pstAllInhArray = outProps["pstAllInh"]
        gridBounds = outProps["gridBounds"]
        
        nCubes = len(cube_branch_values.keys())
        arrayIndices = np.zeros(nCubes, dtype=int)
        arrayPstExcNorm = np.zeros(nCubes, dtype=np.float32)
        arrayPstExcApicalNorm = np.zeros(nCubes, dtype=np.float32)
        arrayPstExcBasalNorm = np.zeros(nCubes, dtype=np.float32)
        arrayPstExcSomaNorm = np.zeros(nCubes, dtype=np.float32)
        arrayPstInhNorm = np.zeros(nCubes, dtype=np.float32)
        arrayPstInhApicalNorm = np.zeros(nCubes, dtype=np.float32)
        arrayPstInhBasalNorm = np.zeros(nCubes, dtype=np.float32)
        arrayPstInhSomaNorm = np.zeros(nCubes, dtype=np.float32)

        i = 0
        for cube, branches in cube_branch_values.items():
            arrayIdx = util_geometry.getArrayIndex(gridBounds, cube)
            arrayIndices[i] = arrayIdx            
            pstExc = 0
            pstExcApical = 0
            pstExcBasal = 0
            pstExcSoma = 0
            pstInh = 0
            pstInhApical = 0
            pstInhBasal = 0
            pstInhSoma = 0
            for values in branches.values():
                pstExc += values["pstExc"]
                pstExcApical += values["pstExcApical"]
                pstExcBasal += values["pstExcBasal"]
                pstExcSoma += values["pstExcSoma"]
                pstInh += values["pstInh"]
                pstInhApical += values["pstInhApical"]
                pstInhBasal += values["pstInhBasal"]
                pstInhSoma += values["pstInhSoma"]
            if(pstExc > 0):
                arrayPstExcNorm[i] = pstExc / pstAllExcArray[arrayIdx]
                arrayPstExcApicalNorm[i] = pstExcApical / pstAllExcArray[arrayIdx]
                arrayPstExcBasalNorm[i] = pstExcBasal / pstAllExcArray[arrayIdx]
                arrayPstExcSomaNorm[i] = pstExcSoma / pstAllExcArray[arrayIdx]
            if(pstInh > 0):
                arrayPstInhNorm[i] = pstInh / pstAllInhArray[arrayIdx]
                arrayPstInhApicalNorm[i] = pstInhApical / pstAllInhArray[arrayIdx]
                arrayPstInhBasalNorm[i] = pstInhBasal / pstAllInhArray[arrayIdx]
                arrayPstInhSomaNorm[i] = pstInhSoma / pstAllInhArray[arrayIdx]                            
            i += 1        

        sortIdx = np.argsort(arrayIndices)
        arrayIndices = arrayIndices[sortIdx]
        arrayPstExcNorm = arrayPstExcNorm[sortIdx]
        arrayPstExcApicalNorm = arrayPstExcApicalNorm[sortIdx]
        arrayPstExcBasalNorm = arrayPstExcBasalNorm[sortIdx]
        arrayPstExcSomaNorm = arrayPstExcSomaNorm[sortIdx]
        arrayPstInhNorm = arrayPstInhNorm[sortIdx]
        arrayPstInhApicalNorm = arrayPstInhApicalNorm[sortIdx]
        arrayPstInhBasalNorm = arrayPstInhBasalNorm[sortIdx]
        arrayPstInhSomaNorm = arrayPstInhSomaNorm[sortIdx]

        outProps["featuresPost"][neuronId] = {
            "arrayIndices" : arrayIndices,
            "arrayPstExcNorm" : arrayPstExcNorm,
            "arrayPstExcApicalNorm" : arrayPstExcApicalNorm,
            "arrayPstExcBasalNorm" : arrayPstExcBasalNorm,
            "arrayPstExcSomaNorm" : arrayPstExcSomaNorm,
            "arrayPstInhNorm" : arrayPstInhNorm,
            "arrayPstInhApicalNorm" : arrayPstInhApicalNorm,
            "arrayPstInhBasalNorm" : arrayPstInhBasalNorm,
            "arrayPstInhSomaNorm" : arrayPstInhSomaNorm,
        } 
    elif(outProps["type"] == "pstBranch"):   
        pstAllExcArray = outProps["pstAllExc"]
        pstAllInhArray = outProps["pstAllInh"]
        gridBounds = outProps["gridBounds"]
        for cube, branchValues in cube_branch_values.items():
            arrayIdx = util_geometry.getArrayIndex(gridBounds, cube)
            pstAllExcVal = pstAllExcArray[arrayIdx]
            pstAllInhVal = pstAllInhArray[arrayIdx]
            for values in branchValues.values():
                pstExc = values["pstExc"]
                if(pstExc):
                    values["pstExc"] = pstExc / pstAllExcVal                
                pstInh = values["pstInh"]
                if(pstInh):
                    values["pstInh"] = pstInh / pstAllInhVal
        outProps["featuresPost"][neuronId] = cube_branch_values
    elif(outProps["type"] == "pre"):        
        if(outProps["featuresPre"] is None):
            raise NotImplementedError("refactored to dict: nid -> ...")

        gridBounds = outProps["gridBounds"]

        nCubes = len(cube_branch_values.keys())
        arrayIndices = np.zeros(nCubes, dtype=int)
        arrayBoutons = np.zeros(nCubes, dtype=np.float32)

        i = 0 
        for cube, branches in cube_branch_values.items():
            arrayIdx = util_geometry.getArrayIndex(gridBounds, cube)
            arrayIndices[i] = arrayIdx 

            boutons = 0
            for values in branches.values():
                boutons += values["boutons"]
            arrayBoutons[i] = boutons
            i += 1

        sortIdx = np.argsort(arrayIndices)
        arrayIndices = arrayIndices[sortIdx]
        arrayBoutons = arrayBoutons[sortIdx]            

        outProps["featuresPre"][neuronId] = {
            "arrayIndices" : arrayIndices,
            "arrayBoutons" : arrayBoutons,
        }
    elif(outProps["type"] == "preBranch"):        
        outProps["featuresPre"] = cube_branch_values
    elif(outProps["type"] == "postMorphology"):
        return
    else:
        raise RuntimeError("invalid output type {}".format(outProps["type"]))    


def isInsideBounds(cube, gridBounds):
    ixiyiz_min = gridBounds["ixiyiz_min"]
    ixiyiz_max = gridBounds["ixiyiz_max"]
    return util_geometry.indicesInBounds(cube, ixiyiz_min, ixiyiz_max)


def getGraphset(networkDir, outProps):    
    if(outProps and "featureComputationData" in outProps):
        return outProps["featureComputationData"]["graphset"]
    elif(outProps and ((outProps["type"] == "pre") or (outProps["type"] == "preBranch") or (outProps["type"] == "postMorphology"))):
        return outProps["graphset"]
    else:
        return util_morphology.loadGraphset(networkDir)


def getPreFeatureComputationData(networkDir, outProps):
    if(outProps and "featureComputationData" in outProps):
        boutonDensities = outProps["featureComputationData"]["boutonDensities"]
        grid = outProps["featureComputationData"]["grid"]
        gridCells = outProps["featureComputationData"]["gridCells"]
    elif(outProps and (outProps["type"] == "pre" or outProps["type"] == "preBranch")):
        boutonDensities = outProps["boutonDensities"]
        grid = outProps["grid"]
        gridCells = outProps["gridCells"]
    else:
        boutonDensities = util_meta.loadBoutonDensityMap(networkDir)    
        grid = util_meta.loadGrid_ixiyiz(os.path.join(networkDir, "grid_50-50-50_all.csv"))
        gridCells = set(grid.keys())
    return boutonDensities, grid, gridCells


def getPostFeatureComputationData(networkDir, outProps):
    if(outProps and "featureComputationData" in outProps):
        pstDensities = outProps["featureComputationData"]["pstDensities"]        
    elif(outProps and outProps["type"] == "postMorphology"):
        pstDensities = outProps["pstDensities"]
    else:
        pstDensities = util_meta.loadPstDensityMap(networkDir)
    return pstDensities


def getNeurons(batchfile, networkDir, outProps):
    if(batchfile is not None):
        batchDescriptor = os.path.basename(batchfile)
        neuronIds = np.loadtxt(batchfile, dtype=int).reshape((-1)).tolist()            
        if(outProps and "featureComputationData" in outProps):
            neuronsOriginal = outProps["featureComputationData"]["neuronsOriginal"]
        else:
            neuronsOriginal = util_meta.loadNeuronProps(os.path.join(networkDir, "meta", "neurons.csv"))   
    elif(outProps and (outProps["type"] == "pre" or outProps["type"] == "preBranch")):
        batchDescriptor = "single-pre"
        neuronIds = [outProps["neuronId"]]
        neuronsOriginal = outProps["neuronsOriginal"]
    elif(outProps and outProps["type"] == "postMorphology"):
        batchDescriptor = "single-post"
        neuronIds = [outProps["neuronId"]]
        neuronsOriginal = outProps["neuronsOriginal"]
    else:
        raise RuntimeError
    return batchDescriptor, neuronIds, neuronsOriginal


def getSliceParams(outProps):
    if(outProps is None):
        return None
    elif("sliceParams" in outProps):
        return outProps["sliceParams"]
    else:
        return None


def processBatch(batchfile, synapticSide, gridDescriptor, boundsDescriptor, networkDir, outputFolder, outProps=None, logFolder=None):  
    
    batchDescriptor, neuronIds, neuronsOriginal = getNeurons(batchfile, networkDir, outProps)

    if(synapticSide == "pre"): 
        boutonDensities, grid, gridCells = getPreFeatureComputationData(networkDir, outProps)
    else:
        pstDensities = getPostFeatureComputationData(networkDir, outProps)

    graphset = getGraphset(networkDir, outProps)
    boundsFilter = getBoundsFilter(networkDir, boundsDescriptor, gridDescriptor, outProps)  
    registerEdgePoints = outProps is not None and outProps["type"] == "postMorphology"        
    sliceParams = getSliceParams(outProps)

    util_geometry.setGridSize(gridDescriptor)
    #print("batch {}: active grid size".format(batchDescriptor), util_geometry.GRIDSIZE)    
    
    for k in range(0, len(neuronIds)):
        neuronId = neuronIds[k]
        if(outputFolder):
            outfile = os.path.join(outputFolder,"{}.csv".format(neuronId))                
        cellTypeOriginalId = neuronsOriginal[neuronId]["cell_type"]
        try:
            if(synapticSide == "pre"):
                idx = len(graphset[neuronId]) - 1                        
                filename = graphset[neuronId][idx]["file"]
                T = graphset[neuronId][idx]["transformation"]
            else:
                filename = graphset[neuronId][0]["file"]
                T = graphset[neuronId][0]["transformation"]

            neuron = util_amira.readSpatialGraph(filename, T)  
            nOriginal = len(neuron)  
            if(sliceParams is not None):            
                neuron = util_morphology_slice.sliceNeuron(neuron, sliceParams)

            if(synapticSide == "pre"):
                components = util_graph.getSeparatedComponentsPre(neuron)
                rootNode = components["axon"]["root"]
                tree = components["axon"]["tree"]
            else:
                components = util_graph.getSeparatedComponentsPost(neuron)
                rootNode = components["dendrite"]["root"]
                tree = components["dendrite"]["tree"]            
            rootDists = {}
            rootDists[rootNode] = 0
            edges = list(nx.edge_dfs(tree, source=rootNode, orientation='ignore'))        
            node_cube_branch = {}
            cube_branch_values = {}                             
            edgeCounter = 0
            edgeCounterMorphology = -1
            for u, v, d in edges:     
                edgeCounter += 1
                edgeCounterMorphology += 1
                
                edge = neuron.edges[u, v]
                nodeStart = u
                nodeEnd = v
                points = edge["points"]

                if(d == "reverse"):
                    nodeStart = v
                    nodeEnd = u
                    points.reverse()    

                if(boundsFilter is not None and not util_geometry.pointsInBounds(points, boundsFilter["boxMin"], boundsFilter["boxMax"])):
                    continue

                label = edge["label"]
                if(synapticSide == "pre" and label == "Soma"):
                    raise RuntimeError("Traversed soma: u {}, v {}".format(u, v))

                if(sliceParams is not None and label not in sliceParams["compartment"]):
                    continue
                       
                traversal_state = {
                    "nodeStart" : nodeStart,
                    "nodeEnd" : nodeEnd,
                    "nextCube" : None,
                    "activeCube" : None,
                    "activeBranch" : None,
                }
                dataHandle = None
                if(boundsFilter is None):
                    rd = rootDists[nodeStart]
                else:
                    rd = -1
                
                pointsIntersected, indices = util_geometry.getIntersectedEdgePoints(points)                                        
                for i in range(1, len(pointsIntersected)):
                    p1 = pointsIntersected[i-1]
                    i1 = indices[i-1]
                    p2 = pointsIntersected[i]
                    i2 = indices[i]            
                                        
                    traversal_state["nextCube"] = util_geometry.getCommonIndices(i1, i2)                    
                    if(i == 1):                               
                        dataHandle = updateTraversalState(node_cube_branch, cube_branch_values, traversal_state, synapticSide, "firstStep")
                    elif(traversal_state["nextCube"] != traversal_state["activeCube"]):
                        if(registerEdgePoints):
                            nextCubeInside = isInsideBounds(traversal_state["nextCube"], outProps["gridBounds"])
                            activeCubeInside = isInsideBounds(traversal_state["activeCube"], outProps["gridBounds"])
                            if(nextCubeInside != activeCubeInside):
                                edgeCounterMorphology += 1
                        dataHandle = updateTraversalState(node_cube_branch, cube_branch_values, traversal_state, synapticSide, "crossBorder")                       

                    l = np.linalg.norm(p1[0:3]-p2[0:3])
                    
                    if(label != "Soma"):
                        if(boundsFilter is None):
                            rd += l                        
                        dataHandle["length"] += l    
                    dataHandle["distSoma"].append(rd)

                    if(synapticSide == "pre"):
                        cubeForDensity = traversal_state["activeCube"]
                        if(gridDescriptor != "50-50-50"):
                            cubeForDensity = util_geometry.getClosest50MicronCube(cubeForDensity)
                        boutonDensity = getBoutonDensity(boutonDensities, cellTypeOriginalId, gridCells, grid, cubeForDensity)
                        dataHandle["boutons"] += boutonDensity * l                        
                    else:
                        area = util_geometry.getTruncatedConeArea(l, p1[3], p2[3])
                        pstExc, pstInh = getPostsynapticTargets(pstDensities, cellTypeOriginalId, label, l, area)
                        dataHandle["pstExc"] += pstExc
                        dataHandle["pstInh"] += pstInh
                        if(label == "BasalDendrite"):
                            dataHandle["pstExcBasal"] += pstExc
                            dataHandle["pstInhBasal"] += pstInh
                        if(label == "ApicalDendrite"):
                            dataHandle["pstExcApical"] += pstExc
                            dataHandle["pstInhApical"] += pstInh
                        if(label == "Soma"):
                            dataHandle["pstExcSoma"] += pstExc
                            dataHandle["pstInhSoma"] += pstInh
                    
                    if(registerEdgePoints):
                        if(isInsideBounds(traversal_state["activeCube"], outProps["gridBounds"])):
                            if(edgeCounterMorphology not in outProps["edges"].keys()):
                                outProps["edges"][edgeCounterMorphology] = []
                                outProps["edgeLabels"][edgeCounterMorphology] = label
                            outProps["edges"][edgeCounterMorphology].append(p1)
                            outProps["edges"][edgeCounterMorphology].append(p2)

                updateTraversalState(node_cube_branch, cube_branch_values, traversal_state, synapticSide, "lastStep")
                rootDists[nodeEnd] = rd
            
            if(boundsFilter is not None):                
                cube_branch_values = filterFeatures(boundsFilter, cube_branch_values)                
            if(cube_branch_values):
                if(outputFolder):
                    if(synapticSide == "pre"):
                        util_feature_IO.writeAxonFeatures(outfile, cube_branch_values)                
                    else:
                        util_feature_IO.writeDendriteFeatures(outfile, cube_branch_values)
                else:
                    registerFeatures(neuronId, cube_branch_values, outProps)
            print("batch {}: processed {} ({}/{})".format(batchDescriptor, neuronId, k+1, len(neuronIds)))
        except Exception as e:
            if(logFolder is not None):
                with open(os.path.join(logFolder,"{}_error.txt".format(neuronId)), "w+") as f:
                    f.write("{}\n\n".format(neuronId))
                    f.write("{}\n\n".format(e))
                    f.write(traceback.format_exc())      
            print(traceback.format_exc())  
            print("batch {}: failed {} ({}/{})".format(batchDescriptor, neuronId, k+1, len(neuronIds)))



def printUsageAndExit(message):
    if(message):
        print("{}\n\n".format(message))
    print("Usage:")
    print("calc_features_mp.py network-dir synaptic_side grid-descriptor bounds num-workers [exclude-existing] [NID]")
    print("")
    print("network-dir:         network directory")
    print("synaptic_side:       pre, post")
    print("grid-descriptor:     50-50-50, 100-100-50")
    print("bounds:              all, ref-volume, C2-volume")
    print("num-workers:         5, 6, ...")
    print("exclude-exsiting:    keep exisiting files in output directory (default: false)")
    sys.exit(1)


if __name__ == '__main__':
    if(len(sys.argv) not in [6,7,8]):
        printUsageAndExit("Wrong number of arguments.")
    networkDir = sys.argv[1]
    synapticSide = sys.argv[2]    
    if(synapticSide not in ["pre", "post"]):
        printUsageAndExit("Invalid synaptic side.")
    gridDescriptor = sys.argv[3]
    util_geometry.setGridSize(gridDescriptor)

    boundsDescriptor = sys.argv[4]
    if(boundsDescriptor not in ["all", "ref-volume", "C2-volume"]):
        printUsageAndExit("Invalid bounds.")
    outfolder = os.path.join(networkDir, "subcellular_features_{}synaptic_{}_{}".format(synapticSide, gridDescriptor, boundsDescriptor))
    if(boundsDescriptor == "all"):
        boundsDescriptor = None    
    
    numWorkers = int(sys.argv[5])    
    keepExisting = len(sys.argv) in [7,8]
    if(len(sys.argv) == 8):
        nid = int(sys.argv[7]) 
        numWorkers = 1
    else:
        nid = None
            
    if(not keepExisting):
        print("clearing folder {}".format(outfolder))
        util.makeCleanDir(outfolder)
    batchname = "{}_{}".format(synapticSide, gridDescriptor) 

    batchfiles = util_batch.getBatchFiles(networkDir, synapticSide, gridDescriptor, boundsDescriptor, batchname, numWorkers, excludeExisting=keepExisting, nids=[nid])        
    for batchfile in batchfiles:
        p = mp.Process(target=processBatch, args=(batchfile, synapticSide, gridDescriptor, boundsDescriptor, networkDir, outfolder,))
        p.start()
        
    
    
