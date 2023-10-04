import numpy as np
import re
import os
import glob
import shutil
import json
import copy
import collections
import math
from sortedcontainers import SortedDict


def loadData(filename):
    with open(filename) as f:
        lines = f.readlines()
        data = {}
        for i in range(1, len(lines)):
            line = lines[i].rstrip()
            parts = line.split(",")
            data[int(parts[0])] = float(parts[1])
        return data


def writeData(data, voxelName, valueName, filename):
    with open(filename, "w+") as f:
        f.write("%s,%s\n" % (voxelName, valueName))
        for k, v in data.items():
            f.write("%d,%f\n" % (k, v))


def getDuplicity(axon_mapping):
    duplicity = collections.OrderedDict()
    for k, v in axon_mapping.items():
        if(v in duplicity.keys()):
            duplicity[v] += 1
        else:
            duplicity[v] = 1
    return duplicity


def getUniquePre(neurons, axon_mapping):
    uniques = set()    
    for NID in neurons.keys():
        uniques.add(axon_mapping[NID])
    return uniques 


def getUniquePreIds(neuronIds, axon_mapping):
    uniques = set()    
    for NID in neuronIds:
        uniques.add(axon_mapping[NID])
    uniques = list(uniques)
    uniques.sort()
    return uniques


def getNeuronIdFromFileName(filename):
    s = re.search('neuron_\d+.csv', filename)
    if(s is None):
        return -1
    else:
        return int(s.group().split("_")[1].split(".")[0])


def getNeuronIdFromSubcellularFeatureFile(filename):
    return int(os.path.basename(filename).split("_")[0])


def getFilePathFromNeuronId(baseDir, folder, neuronId):
    fileName = "neuron_{:d}.csv".format(neuronId)
    return os.path.join(baseDir, folder, fileName)


def makeCleanDir(dirname):
    if(os.path.exists(dirname)):
        shutil.rmtree(dirname, ignore_errors=False, onerror=None)
    os.mkdir(dirname)


def makeDir(dirname):
    if(not os.path.exists(dirname)):
        os.mkdir(dirname)


def getSharedVoxels(a, b):
    voxels = set(list(a.keys()))
    voxels.intersection_update(set(list(b.keys())))
    return voxels


def geEPS(val):
    return val >= 0.0001


def calcOverlap(pre, pst, pstAll):
    voxels = set(list(pre.keys()))
    voxels.intersection_update(set(list(pst.keys())))
    overlap = 0
    for voxel in voxels:
        overlap += pre[voxel] * pst[voxel] / pstAll[voxel]
    return overlap


def calcConnectionProbability(overlap):
    return 1 - math.exp(-overlap)


def formatLength(val):
    return "{:.4f}".format(val)


def formatFloat(val, decimalDigits):
    return str(round(val, decimalDigits))


def getNeuronIds(whitelistFile):
    ids = []
    with open(whitelistFile) as f:
        lines = f.readlines()
        for line in lines:
            ids.append(int(line.rstrip()))
    return ids


def loadCellTypes(filename):
    with open(filename) as f:
        lines = f.readlines()
        id_name = {}
        name_id = {}
        for i in range(1, len(lines)):
            line = lines[i].rstrip().split(",")
            id = line[0]
            name = line[1]
            id_name[id] = name
            name_id[name] = id
        return id_name, name_id


def numToString(numList):
    stringList = []
    for num in numList:
        stringList.append(str(num))
    return stringList


def writeIdsToFile(filename, ids):
    idsCopy = []
    for id in ids:
        idsCopy.append(int(id))
    idsCopy.sort()
    with open(filename, "w+") as f:
        for id in idsCopy:
            f.write(str(id) + "\n")


def loadIdsFromFile(filename):
    ids = []
    with open(filename) as f:
        lines = f.readlines()
        for line in lines:
            ids.append(int(line.rstrip()))
    return ids


def writePreIdsToFile(filename, ids, mapping):
    idsCopy = []
    for id in ids:
        idsCopy.append(int(id))
    idsCopy.sort()
    with open(filename, "w+") as f:
        for id in idsCopy:
            f.write("{} {}\n".format(id, mapping[id]))


def resortOrderedDict(data):
    ids = list(data.keys())
    ids.sort()
    dataSorted = collections.OrderedDict()
    for id in ids:
        dataSorted[id] = data[id]
    return dataSorted



def load_csv(filename):
    with open(filename) as f:
        lines = f.readlines()
        header = lines[0].rstrip().split(",")
        data = []
        for i in range(1, len(lines)):
            data.append(lines[i].rstrip().split(","))
        return header, data


def convert_csv_json(header, data):
    data_json = []
    for entry in data:
        entry_json = {}
        for i in range(0, len(header)):
            entry_json[header[i]] = entry[i]
        data_json.append(entry_json)
    return data_json


def save_json_csv(filename, header, data):
    with open(filename, "w+") as f:
        f.write(",".join(header) + "\n")
        for entry in data:
            values = []
            for label in header:
                values.append(str(entry[label]))
            f.write(",".join(values) + "\n")


def json_float(data, blacklist):
    for entry in data:
        for label, value in entry.items():
            if(label not in blacklist):
                entry[label] = float(value)


def json_int(data, blacklist):
    for entry in data:
        for label, value in entry.items():
            if(label not in blacklist):
                entry[label] = int(value)


def saveJson(data, filename):
    with open(filename, "w+") as f:
        json.dump(data, f)


def loadJson(filename):
    with open(filename) as f:
        return json.load(f)


def convertFloat32List(listFloat32):
    converted = []
    for item in listFloat32:
        converted.append(float(item))
    return converted

def convertFloat32Matrix(M):
    converted = []
    for i in range(0, M.shape[0]):
        converted.append(convertFloat32List(M[i,:]))
    return converted

def getTuplesBySlice(tuples):
    tuplesBySlice = {}
    for t in tuples:
        nwIdx = t[2]
        if(nwIdx not in tuplesBySlice.keys()):
            tuplesBySlice[nwIdx] = []
        tuplesBySlice[nwIdx].append((t[0], t[1]))
    return tuplesBySlice


def getInferenceExperimentSpec(experiments, identifier):
    for experiment in experiments:
        if(experiment["identifier"] == identifier):
            return experiment
    raise RuntimeError("Unknown experiment: {}".format(identifier))


def assertDirectory(path):
    if(not os.path.isdir(path)):
        print("Not a directory: {}".format(path))
        exit()


def assertDirectories(paths):
    for path in paths:
        assertDirectory(path)


def getReverseAxonMap(mapping):
    reverseAxonMap = {}
    for preId, mappedPreId in mapping.items():
        if(mappedPreId not in reverseAxonMap.keys()):
            reverseAxonMap[mappedPreId] = []
        reverseAxonMap[mappedPreId].append(preId)
    for mappedId, preIds in reverseAxonMap.items():
        preIds.sort()
    return reverseAxonMap


def loadDataBlock(filename, dataColumn):    
    data = np.loadtxt(filename, delimiter=",", skiprows=1, usecols=(0,dataColumn)).reshape(-1, 2)
    idxnonzero = data[:,1] > 0
    return data[idxnonzero,0].astype(int), data[idxnonzero,1]


def getExistingIds(folder):
    print("a")
    files = glob.glob(os.path.join(folder,"*.csv"))
    print("b")
    ids = set()
    for file in files:
        fname = os.path.basename(file)
        ids.add(int(fname.split(".")[0]))
    return ids


def getLines(filename, skipLines=1):
    linesStripped = []
    with open(filename) as f:
        lines = f.readlines()
        for i in range(skipLines, len(lines)):
            linesStripped.append(lines[i].rstrip())
    return linesStripped


def getRandomSubset(itemSet, n, sortBeforeShuffle = False):
    if(n >= len(itemSet)):
        return itemSet

    array = list(itemSet)
    if(sortBeforeShuffle):
        array.sort()
    np.random.shuffle(array)
    return set(array[0:n]) 
    

def sortAndSaveIds(filename, ids):
    idsList = list(ids)
    idsList.sort()
    np.savetxt(filename, idsList, fmt="%d")

def nCr(n,r):
    f = math.factorial
    return f(n) / f(r) / f(n-r)


def getMaskForSelectedIds(idsVektor, idsSet):    
    n = idsVektor.size
    mask = np.zeros(n).astype(bool)
    for i in range(0, n):        
        postId = idsVektor[i]
        mask[i] = postId in idsSet
    maskInverted = ~mask
    return mask, maskInverted
    

def getDescriptorForParameters(parameters):
    descriptor = ""

    for i in range(parameters.size):
        if(i!=0):
            descriptor += "#"
        descriptor += "{:.4f}".format(parameters[i])

    return descriptor


def getParametersFromDescriptor(descriptor):
    parts = descriptor.split("#")
    parameters = np.zeros(len(parts))
    for i in range(len(parts)):
        parameters[i] = float(parts[i])
    return parameters


def getParameterDescriptorsFromFolder(folder):
    descriptors = []
    folderPaths = glob.glob(os.path.join(folder, "params_*"))
    for folderPath in folderPaths:
        descriptor = os.path.basename(folderPath).replace("params_", "")
        descriptors.append(descriptor)
    return descriptors


def getCombinationsAsTuples(A, B):
    pairs = []
    for a in A:
        for b in B:
            pairs.append((a, b))
    return pairs

def mergeDicts(a, b):    
    for bKey, bValue in b.items():
        if(bKey not in a):
            a[bKey] = 0
        a[bKey] += bValue


def getPairLabel(pair):
    return "{}-{}".format(pair[0], pair[1])