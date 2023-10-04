import numpy as np
import multiprocessing as mp
from ctypes import c_bool


def isInRange(neurons, nidA, nidB, distRange):
    somaA = neurons[nidA]["soma"]
    somaB = neurons[nidB]["soma"]
    distance = np.linalg.norm(somaA - somaB)
    return distance >= distRange[0] and distance <= distRange[1]


def checkDistanceConditionBatch(batchIndex, neurons, nids, idxA, distRange, conditionArray):
    n = len(nids)
    for i in range(0, idxA.size):

        if((i+1) % 100 == 0):
            print("batch {}: {}/{}".format(batchIndex, i+1, idxA.size))

        nidA = nids[idxA[i]]
        for j in range(idxA[i]+1, n):
            nidB = nids[j]            
            if(isInRange(neurons, nidA, nidB, distRange)):
                arrayIndex = idxA[i] * n + j
                conditionArray[arrayIndex] = True


def getValidPairs(conditionArray, nids):
    n = len(nids)
    pairs = []

    for i in range(0, n):        
        for j in range(i+1, n):  
            arrayIndex = i * n + j 
            if(bool(conditionArray[arrayIndex])):                                
                pairs.append((i, j))                
        print(i)

    print("valid pairs", len(pairs))
    return pairs


def getMutualDistances(neurons, nids, distRange, numWorkers):    
    n = len(nids)
    numCells = n**2
    print("num pairs", numCells)
    conditionArray = mp.Array(c_bool, int(numCells), lock=False)

    idxA = np.arange(n)
    batches = np.array_split(idxA, numWorkers)

    processes = []
    for i in range(0,len(batches)):
        p = mp.Process(target=checkDistanceConditionBatch, args=(i, neurons, nids, batches[i], distRange, conditionArray))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()

    validPairs = getValidPairs(conditionArray, nids)    
    return conditionArray, validPairs


def isValid(conditionArray, i, j, n):
    if(i < j):
        idx = i * n + j 
    else:
        idx = j * n + i 
    return bool(conditionArray[idx])


def assertDistanceCondition(tripletSamples, neurons, distRange):
    for i in range(tripletSamples.shape[0]):
        nidA = tripletSamples[i][0]
        nidB = tripletSamples[i][1]
        nidC = tripletSamples[i][2]
        if(not isInRange(neurons, nidA, nidB, distRange)
            or not isInRange(neurons, nidA, nidC, distRange)
            or not isInRange(neurons, nidB, nidC, distRange)):
            raise RuntimeError("distance condition violated")


def assertSamplesUnique(tripletSamples):
    uniqueSet = set()
    for i in range(tripletSamples.shape[0]):
        nidA = tripletSamples[i][0]
        nidB = tripletSamples[i][1]
        nidC = tripletSamples[i][2]
        if(nidA >= nidB or nidB >= nidC):
            raise RuntimeError("nids not ordered")        
        uniqueSet.add((nidA, nidB, nidC))
    if(len(uniqueSet) != tripletSamples.shape[0]):
        print(len(uniqueSet), tripletSamples.shape[0])
        raise RuntimeError("samples not unqiue")


def getOrderedTuple(nids, ii, ij, ik):
    i = nids[ii]
    j = nids[ij]
    k = nids[ik]
    if(i < j):
        if(j < k):
            return (i, j, k)
        elif(i < k):
            return (i, k, j)
        else:
            return (k, i, j)
    elif(j < k):
        if(i < k):
            return (j, i, k)
        else:
            return (j, k, i)
    else:
        return (k, j, i)


def getTripletSamplesFromValidPairs(nids, conditionArray, validPairs, numTripletSamples):
    n = len(nids)
    nPairs = len(validPairs)

    np.random.shuffle(validPairs)

    counter = 0    
    counts_k_to_ij = np.zeros(n, dtype=int) # [0,n) x [0,nPairs]    
    offsets_k_to_ij = np.random.randint(0, nPairs, n) # [0,n) x [0,nPairs)    
    exhaustedCombinations = False
    reachedTripletSamples = False
    tripletSamples = []

    while(not (reachedTripletSamples or exhaustedCombinations)):
        k = counter % n        
        count_k_to_ij = counts_k_to_ij[k]
        offset_k_to_ij = offsets_k_to_ij[k]

        if(count_k_to_ij < nPairs):            
            counts_k_to_ij[k] += 1

            k_to_ij = (offset_k_to_ij + count_k_to_ij) % nPairs
            ij = validPairs[k_to_ij]
            i = ij[0]
            j = ij[1]

            if(j <= i):
                raise RuntimeError("i j invalid")

            if(isValid(conditionArray, i, k, n) and isValid(conditionArray, j, k, n)):
                if(i < k and j < k):
                    nidTuple = getOrderedTuple(nids, i, j, k)
                    tripletSamples.append(nidTuple)                            

        reachedTripletSamples = len(tripletSamples) == numTripletSamples
        exhaustedCombinations = np.all(counts_k_to_ij == nPairs)
        counter += 1

        if(counter % 1000 == 0):
            print("triplet samples", len(tripletSamples))
     
    return np.array(tripletSamples)


def getTripletSamples(neurons, nidsA, nidsB, nidsC, distRange, numTripletSamples, numWorkers, numNeuronSubSamples = 5000):
    setA = set(nidsA)
    setB = set(nidsB)
    setC = set(nidsC)
    if(setA != setB or setB != setA):
        raise NotImplementedError
    nids = nidsA

    np.random.shuffle(nids)
    numNeuronSubSamples = min(numNeuronSubSamples, len(nids))
    nids = nids[0:numNeuronSubSamples]

    conditionArray, validPairs = getMutualDistances(neurons, nids, distRange, numWorkers)        
    tripletSamples = getTripletSamplesFromValidPairs(nids, conditionArray, validPairs, numTripletSamples)
    
    assertDistanceCondition(tripletSamples, neurons, distRange)
    assertSamplesUnique(tripletSamples)

    return tripletSamples