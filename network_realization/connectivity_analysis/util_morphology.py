import os
import numpy as np
import json

import util_amira

def getEdgeLabelName(label):
    if(label == 6):
        return "axon"
    elif(label == 4):
        return "apical"
    elif(label == 5):
        return "basal"
    elif(label == 7):
        return "soma"
    else:
        return "other"


def getSomaPosition(points):
    somaPos = []
    for p in points:
        if(p["edge_label"] == "soma"):
            somaPos.append(p["position"])
    return np.mean(np.vstack(tuple(somaPos)), axis=0)


def loadAmiraExport(filename):
    with open(filename) as f:
        lines = f.readlines()
        labels = lines[0].rstrip().split(",")
        points = []
        for i in range(1, len(lines)):
            line = lines[i].rstrip().split(",")

            point = {}
            point["edge_id"] = int(line[labels.index("edge_id")])
            point["source_node_id"] = int(line[labels.index("source_node")])
            point["target_node_id"] = int(line[labels.index("target_node")])
            point["edge_label"] = getEdgeLabelName(
                int(line[labels.index("edge_label")]))
            point["edge_point_id"] = int(line[labels.index("edge_point")])
            point["position"] = np.array([float(line[labels.index("x")]), float(
                line[labels.index("y")]), float(line[labels.index("z")])])
            point["radius"] = float(line[labels.index("radius")])
            point["inside_vS1"] = int(line[labels.index("inside_vS1")])
            if(point["edge_label"] != "other"):
                points.append(point)

    return points


def separateCompartments(edgePoints):
    apical = []
    basal = []
    axon = []
    for edgePoint in edgePoints:
        if(edgePoint["edge_label"] == "apical"):
            apical.append(edgePoint)
        elif(edgePoint["edge_label"] == "basal"):
            basal.append(edgePoint)
        elif(edgePoint["edge_label"] == "axon"):
            axon.append(edgePoint)
    compartments = {}
    compartments["apical"] = apical
    compartments["basal"] = basal
    compartments["axon"] = axon
    return compartments


def loadGraphset(networkDir):
    if(os.path.exists(os.path.join(networkDir, "morphologies", "Morphologies.am"))):
        graphset = util_amira.readSpatialGraphSet(os.path.join(networkDir, "morphologies", "Morphologies.am"), legacy=False)
    else:    
        graphset = util_amira.readSpatialGraphSet(os.path.join(networkDir, "morphologies", "MorphologiesWithNeuronIDs.am"), legacy=True)  
    return graphset


def writeToCache(filename, transformation, neuronId):
    transformationFile = "/tmp/transformation_{}".format(neuronId)
    np.savetxt(transformationFile, transformation)

    meta = {
        "morphologyFile" : filename,
        "transformationFile" : transformationFile
    }
    metaFile = "/tmp/meta_{}.json".format(neuronId)
    with open(metaFile, "w") as f:
        print("meta", meta)
        json.dump(meta, f)
    

def readFromCache(neuronId):
    metaFile = "/tmp/meta_{}.json".format(neuronId)
    with open(metaFile) as f:
        meta = json.load(f)

    transformationFile = meta["transformationFile"]
    T = np.loadtxt(transformationFile)
    morphologyFile = meta["morphologyFile"]

    return morphologyFile, T


def loadAxon(graphset, neuronId, saveToCache = False, loadFromCache = False):    
    if(loadFromCache):
        filename, T = readFromCache(neuronId)
    else:
        idx = len(graphset[neuronId]) - 1                   
        filename = graphset[neuronId][idx]["file"]
        T = graphset[neuronId][idx]["transformation"] 
        if(saveToCache):
            writeToCache(filename, T, neuronId)
    
    return util_amira.readSpatialGraph(filename, T)


def loadDendrite(graphset, neuronId, saveToCache = False, loadFromCache = False):
    if(loadFromCache):
        filename, T = readFromCache(neuronId)
    else:
        filename = graphset[neuronId][0]["file"]
        T = graphset[neuronId][0]["transformation"] 
        if(saveToCache):
            writeToCache(filename, T, neuronId)
    
    return util_amira.readSpatialGraph(filename, T)