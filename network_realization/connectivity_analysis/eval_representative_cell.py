import os 
import sys
import multiprocessing as mp
import numpy as np

import util
import util_batch
import util_meta
import util_feature_IO
import util_morphology
import util_amira

def getEmptyStatsSoma():
    return {
        "ids" : []
    }


def findInnervating(batchIndex, results, preIds, networkDir, postId):
    stats = getEmptyStatsSoma()
    print("n pre", len(preIds))
    filenamePost = os.path.join(networkDir, "subcellular_features_postsynaptic_50-50-50_all", "{}.csv".format(postId))
    cubesPost = util_feature_IO.getCubesFromFeatures(filenamePost)
    if(not cubesPost):
        raise RuntimeError

    for i in range(0,len(preIds)):        
        print(i)
        if((i+1) % 500 == 0):
            print("batch {}: {}/{}".format(batchIndex,i+1,len(preIds)))
        preId = preIds[i]
        filenamePre = os.path.join(networkDir, "subcellular_features_presynaptic_50-50-50_all", "{}.csv".format(preId))
        print("filename", filenamePre)
        cubesPre = util_feature_IO.getCubesFromFeatures(filenamePre)
        print("preCubes", len(cubesPre))
        if(cubesPre):
            overlapping = cubesPre & cubesPost
            if(overlapping):
                stats["ids"].append(preId)
    results[batchIndex] = stats


def determineInnervatingSoma(networkDir, outfolder, postId, numWorkers):
    preIds = util_batch.getAllPresynaptic(networkDir)
    np.random.shuffle(preIds)    
    batches = np.array_split(preIds, numWorkers)
    
    manager = mp.Manager()
    results = manager.dict()
    processes = []
    for i in range(0, len(batches)):
        p = mp.Process(target=findInnervating, args=(i, results, batches[i], networkDir, neuronId))
        processes.append(p)
        p.start()
    for p in processes:
        p.join()

    combinedPreIds = []
    for values in results.values():
        combinedPreIds.extend(values["ids"])
    combinedPreIds.sort()

    neurons = util_meta.loadNeuronProps(os.path.join(networkDir, "neurons.csv"))
    with open(os.path.join(outfolder, "{}_innervating-pre-neurons.csv".format(postId)), "w+") as f:
        f.write("pre_id,soma_x,soma_y,soma_z\n")
        for preId in combinedPreIds:
            somaPos = neurons[preId]["soma"]
            f.write("{},{:.1f},{:.1f},{:.1f}\n".format(preId, somaPos[0], somaPos[1], somaPos[2]))


def determineInnervatingDSC(networkDir, outfolder, postId, numWorkers):
    innervatingPreFile = os.path.join(outfolder, "{}_innervating-pre-neurons.csv".format(postId))
    if(not os.path.exists(innervatingPreFile)):
        raise RuntimeError("file not found: {}".format(innervatingPreFile))
    preIds = np.loadtxt(innervatingPreFile, skiprows=1, delimiter=",", usecols=0).astype(int)
    inverseDSC = {}
    for i in range(0, preIds.size):
        preId = preIds[i]
        print(i)
        dscFile = os.path.join(networkDir, "DSC_50-50-50_all","{}_DSC.csv".format(preId))        
        dscVal = util_feature_IO.readDSCForPostId(dscFile, postId)
        if(dscVal):
            inverseDSC[preId] = dscVal
    preIds = list(inverseDSC.keys())
    preIds.sort()
    with open(os.path.join(outfolder, "{}_innervating-pre-neurons-dsc.csv".format(postId)), "w+") as f:
        f.write("pre_id,dsc\n")
        for preId in preIds:
            f.write("{},{:.6f}\n".format(preId, inverseDSC[preId]))


def writeMorphology(networkDir, outfolder, neuronId, compartment):
    graphset = util_morphology.loadGraphset(networkDir)
    if(compartment == "dendrite"):
        neuron = util_morphology.loadDendrite(graphset, neuronId)        
    elif(compartment == "axon"):
        neuron = util_morphology.loadAxon(graphset, neuronId)            
    else:        
        raise ValueError(compartment)
    filename = os.path.join(outfolder, "{}_{}.am".format(compartment, neuronId))
    util_amira.writeSpatialGraph(filename, neuron)


# L5PT: 301854
# L2PY: 748854
# L6CC: 199678
def printUsageAndExit():
    print("eval_selected_cell.py network-dir mode neuron-id [num-workers]")
    print()
    print("mode:     innervating-soma, innervating-dsc, dendrite-morphology, axon-morphology")
    exit()
    

if __name__ == "__main__":
    if(len(sys.argv) not in [4, 5]):
        printUsageAndExit()
    networkDir = sys.argv[1]
    mode = sys.argv[2]
    neuronId = int(sys.argv[3])
    if(len(sys.argv) == 5):
        numWorkers = int(sys.argv[4])
    else:
        numWorkers = mp.cpu_count()

    util.makeDir(os.path.join(networkDir, "eval", "selected_cells"))
    outfolder = os.path.join(networkDir, "eval", "selected_cells", "{}".format(neuronId))
    util.makeDir(outfolder)

    if(mode == "innervating-soma"):
        determineInnervatingSoma(networkDir, outfolder, neuronId, numWorkers)
    elif(mode == "innervating-dsc"):
        determineInnervatingDSC(networkDir, outfolder, neuronId, numWorkers)
    elif(mode == "dendrite-morphology"):
        writeMorphology(networkDir, outfolder, neuronId, "dendrite")
    elif(mode == "axon-morphology"):
        writeMorphology(networkDir, outfolder, neuronId, "axon")
    else:
        raise RuntimeError("invalid mode: {}".format(mode))
    
    

