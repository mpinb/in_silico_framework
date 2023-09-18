import math
import os
import shutil
import json
import itertools
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

def makeCleanDir(dirname):
    if(os.path.exists(dirname)):
        shutil.rmtree(dirname, ignore_errors=False, onerror=None)
    os.mkdir(dirname)


def makeDir(dirname):
    if(not os.path.exists(dirname)):
        os.mkdir(dirname)


def loadJson(filename):
    with open(filename) as f:
        return json.load(f)


def getHeaderCols(filename, delimiter=","):
    with open(filename) as f:
        headerLine = f.readline()
        return headerLine.rstrip().split(delimiter)


def printDataRange(name, dataColumn, invalidValue = None):
    if(invalidValue is None):
        filterMask = np.ones(dataColumn.size, dtype=bool)
    else:
        filterMask = dataColumn != invalidValue
    print(name, np.min(dataColumn[filterMask]), np.max(dataColumn[filterMask]))


def printQuantiles(name, dataVector):
    print(name,np.quantile(dataVector, [0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1]))


def printDataRangeCategorical(name, dataColumn):
    uniqueValues = np.unique(dataColumn)
    print(name, uniqueValues)


def assertMaskConsistency(bins, lenDataColumn):
    count = 0
    for bin in bins:
        count += np.count_nonzero(bin["mask"])
    assert count == lenDataColumn


def writeBins(baseFolder, propertyName, bins, displayName=None, selectionProperties = None):
    targetFolder = os.path.join(baseFolder, propertyName)
    makeCleanDir(targetFolder)
    values = []
    for bin in bins:
        filename = os.path.join(targetFolder, bin["value"])
        np.savetxt(filename, bin["mask"].astype(int), fmt="%d")
        values.append(bin["value"])
    meta = {
        "name" : propertyName,
        "values" : values,
        "property_type" : "categorical"
    }
    if(displayName is not None):
        meta["display_name"] = displayName
    metaFile = os.path.join(targetFolder, "meta.json")
    with open(metaFile, "w") as f:
        json.dump(meta, f)
    if(selectionProperties is not None):
        selectionProperties.append(meta)
    

def binCategoricalAttributes(dataColumn, values, valueId_value, isArrayData = False):
    value_mask = {}
    if(isArrayData):
        lenDataColumn = len(dataColumn)
    else:
        lenDataColumn = dataColumn.size

    for value in values:            
        value_mask[value] = np.zeros(lenDataColumn, dtype=bool)
    
    for i in range(0, lenDataColumn):
        valueId = dataColumn[i]
        value = valueId_value[valueId]
        value_mask[value][i] = True

    bins = []
    for value in values:
        bins.append({
            "value" : value,
            "mask" : value_mask[value]
        })

    assertMaskConsistency(bins, lenDataColumn)
    return bins


def binIntegerValuedAttributes(dataColumn):
    values = np.unique(dataColumn)
    
    value_mask = {}
    for value in values:
        value_mask[str(value)] = np.zeros(dataColumn.size, dtype=bool)

    for i in range(0, dataColumn.size):
        valueStr = str(dataColumn[i])
        value_mask[valueStr][i] = True
    
    bins = []
    for value in values:
        bins.append({
            "value" : "{:d}".format(int(value)),
            "mask" : value_mask[str(value)]
        })

    assertMaskConsistency(bins, dataColumn.size)
    return bins


def binTags(data, values, id_value, na_id):
    n = len(data)
    value_mask = {}
    for value in values:
        value_mask[value] = np.zeros(n, dtype=bool)
    
    for i in range(0, n):
        tags = data[i]
        assigned = False
        for tag in tags:
            if(tag in id_value):
                value_mask[id_value[tag]][i] = True
                assigned = True
        if(not assigned):
            value_mask[id_value[na_id]][i] = True

    bins = []
    for value in values:
        bins.append({
            "value" : value,
            "mask" : value_mask[value]
        })
    return bins  

def binNumericAttributes(dataColumn, firstBinStartValue, lastBinStartValue, step):
    bins = [] 
    currentStartValue = firstBinStartValue
    mask_binned = np.zeros(dataColumn.size, dtype=bool)
    while(currentStartValue <= lastBinStartValue):        
        currentEndValue = currentStartValue + step
        mask_current = (dataColumn > currentStartValue) & (dataColumn <= currentEndValue)
        mask_binned |= mask_current        
        bins.append({
            "value" : "{}".format(currentEndValue),
            "mask" : mask_current            
        })
        currentStartValue = currentEndValue
    bins.append({
        "value" : "other",
        "mask" : ~mask_binned
    })

    assertMaskConsistency(bins, dataColumn.size)
    return bins


def getBinsFromQuantiles(dataVector, numQuantiles):
    bins = []
    for k in range(0,numQuantiles):
        a = np.quantile(dataVector, k / numQuantiles)
        if(k==0):
            a -=1 
        b = np.quantile(dataVector, (k+1) / numQuantiles)
        bins.append((a,b))
    return bins 


def getBinsFromFixedQuantiles(dataVector, quantiles):
    bins = []
    for k in range(0,len(quantiles)):        
        if(k==0):
            a =-1
        else:
            a = np.quantile(dataVector,quantiles[k-1])
        b = np.quantile(dataVector, quantiles[k])
        bins.append((a,b))
    return bins 


def getBinBounds(startValue, numBins, step):
    bounds = []
    for i in range(0,numBins):
        a = startValue + i * step
        b = a + step
        bounds.append((a,b))
    return bounds


def binNumericAttributesFixedBins(dataColumn, binBounds):
    # (a,b] start exclusive, end inclusive
    bins = []     
    mask_binned = np.zeros(dataColumn.size, dtype=bool)
    for binBound in binBounds:               
        mask_current = (dataColumn > binBound[0]) & (dataColumn <= binBound[1])
        mask_binned |= mask_current        
        bins.append({
            "value" : "{:.0f}".format(binBound[1]),
            "mask" : mask_current            
        })
    bins.append({
        "value" : "other",
        "mask" : ~mask_binned
    })

    assertMaskConsistency(bins, dataColumn.size)
    return bins


def getQuantileIndicesForDataVector(dataVector, invalidValues, quantiles):
    quantileIndices = np.zeros(dataVector.size, dtype=int)
    for i in range(0, dataVector.size):               
        value = dataVector[i]
        if(value not in invalidValues):
            for k in range(0, quantiles.size):
                if (value <= quantiles[k]):
                    quantileIndices[i] = k + 1
                    break
    return quantileIndices



def getRandomSubset(itemSet, n, sortBeforeShuffle = False):
    if(n >= len(itemSet)):
        return itemSet

    array = list(itemSet)
    if(sortBeforeShuffle):
        array.sort()
    np.random.shuffle(array)
    return set(array[0:n]) 


def convertIntFormat(items):
    converted = []
    for item in items:
        converted.append(int(item))
    return converted


def writeMeta(filename, selectionProperties, channels, options = {}):
    meta = {
        "options" : options,
        "channels" : channels,
        "selection_properties" : selectionProperties
    }
    with open(filename,"w") as f:
        json.dump(meta, f)

def revertDict(dictIn):
    return dict((v,k) for k,v in dictIn.items())


def getQuantileSteps(step = 0.1):
    numSteps = 1/step
    if(not numSteps.is_integer()):
        raise ValueError(step)
    return np.arange(1,numSteps+1) / numSteps


def getDSCFromProb(p, eps = 0.00001):
    if(p == 1):
        p -= eps
    return -math.log(1-p)


def getInitializedDict(numValuesPerProperty):
    """
    Returns dictionary with all possible value combinations
    of the properties (-1: wildcard/property not used). Every
    value combination is initialized with count 0. For example:
    (1,2,-1,1,7) -> 0
    """
    expandedValues = []
    for numValues in numValuesPerProperty:
        expandedValues.append(list(np.arange(-1,numValues, dtype=int)))
    emptyDict = {}
    for idx in itertools.product(*expandedValues):
        emptyDict[idx] = 0
    return emptyDict


def getPropertyCombinationKeys(numProperties):
    propertyIndices = np.arange(numProperties)
    powerSet = list(itertools.chain.from_iterable(itertools.combinations(propertyIndices, r) for r in range(len(propertyIndices)+1)))
    keysAll = -1 * np.ones((len(powerSet), numProperties))
    for i in range(0, len(powerSet)):        
        keysAll[i,powerSet[i]] = 1
    return keysAll


def getIndicesForIncrement(keyCombinations, propertyValues):
    values = np.array(propertyValues)
    values += 1
    indices = np.multiply(values, keyCombinations)
    indices[indices < 0] = 0
    indices -= 1
    return indices


def getQuantilesForDataVector(dataVector, propertyName, outFolderPlot, quantileStep, numBins=50):
    
    quantileSteps = getQuantileSteps(quantileStep)
    print("quantile steps", quantileSteps)
    quantiles = np.quantile(dataVector, quantileSteps)
    print("quantiles", quantiles)
    
    mpl.rcParams["font.size"] = 8

    plt.clf()
    fig = plt.figure(figsize=(7,4))
    ax1 = fig.add_subplot(111)
    ax2 = ax1.twiny()

    _ = ax1.hist(dataVector, bins=numBins)
    for quantile in quantiles:
        ax1.axvline(x=quantile, color="black", linewidth=1)

    xmin = np.min(dataVector)
    xmax = np.max(dataVector)    
    
    def getQuantileCenters():
        centers = []
        for k1 in range(0,quantiles.size):
            if(k1 == 0):
                center = xmin + 0.5 * (quantiles[k1]-xmin)
                centers.append(center)
            else:
                center = quantiles[k1-1] + 0.5 * (quantiles[k1]-quantiles[k1-1])
                centers.append(center)
        return centers

    ax1.set_xlabel(r"{}".format(propertyName))            
    ax1.set_xlim(xmin, xmax)     
    ax2.set_xlim(xmin, xmax)        
    ax2.set_xticks(getQuantileCenters(), np.arange(1,quantiles.size+1))    
    ax2.set_xlabel("quantiles")    
    plotfile = os.path.join(outFolderPlot, "distribution_{}.png".format(propertyName))
    plt.savefig(plotfile, dpi=300)

    dataVectorIndexed = getQuantileIndicesForDataVector(dataVector, [-1], quantiles)
    values = []
    valueId_value = {}
    for i in range(1, quantiles.size+1):
        value = "Q{}".format(i)
        values.append(value)
        valueId_value[i] = value

    return dataVectorIndexed, values, valueId_value


def getQuantilesForLargeDataVector(dataVector, propertyName, outFolderPlot, quantileStep, numBins=50, plot_quantileIdxMin=-1, plot_quantileIdxMax=-1, useLog_x = False, useLog_y = False):
    quantileSteps = getQuantileSteps(quantileStep)
    print("quantile steps", quantileSteps)
    quantiles = np.quantile(dataVector, quantileSteps)
    print("quantiles", quantiles)
    
    mpl.rcParams["font.size"] = 8

    plt.clf()
    fig = plt.figure(figsize=(7,4))
    ax1 = fig.add_subplot(111)
    ax2 = ax1.twiny()

    _ = ax1.hist(dataVector, bins=numBins)
    for quantile in quantiles:
        ax1.axvline(x=quantile, color="black", linewidth=1)

    if(plot_quantileIdxMin == -1):
        xmin = np.min(dataVector)
    else:
        xmin = quantiles[plot_quantileIdxMin]
    xmax = quantiles[plot_quantileIdxMax]
    
    def getQuantileCenters():
        centers = []
        for k1 in range(0,quantiles.size):
            if(k1 == 0):
                center = xmin + 0.5 * (quantiles[k1]-xmin)
                centers.append(center)
            else:
                center = quantiles[k1-1] + 0.5 * (quantiles[k1]-quantiles[k1-1])
                centers.append(center)
        return centers

    ax1.set_xlabel(r"{}".format(propertyName))            
    ax1.set_xlim(xmin, xmax)             
    ax2.set_xlim(xmin, xmax)        
    if(useLog_x):
        ax1.set_xscale("log")
        ax2.set_xscale("log")
    if(useLog_y):
        ax1.set_yscale("symlog")
        ax2.set_yscale("symlog")
        ymax = dataVector.size * 10
        ax1.set_ylim(0, ymax)
        ax2.set_ylim(0, ymax)
    ax2.set_xticks(getQuantileCenters(), np.arange(1,quantiles.size+1))    
    ax2.set_xlabel("quantiles")    
    plotfile = os.path.join(outFolderPlot, "distribution_{}.png".format(propertyName))
    plt.savefig(plotfile, dpi=300)

    dataVectorIndexed = np.digitize(dataVector, quantiles, right=True)
    values = []
    valueId_value = {}
    for i in range(quantiles.size):
        value = "Q{}".format(i+1)
        values.append(value)
        valueId_value[i] = value

    return dataVectorIndexed, values, valueId_value


def loadDataVector(filename, colIdx, delimiter=" ", skiprows=0):
    with open(filename) as f:
        lines = f.readlines()
        x = np.zeros(len(lines)-skiprows, dtype=int)    
        for i in range(skiprows, len(lines)):            
            x[i-skiprows] = int(lines[i].rstrip().split(delimiter)[colIdx])
        return x

def getParamsCols():
    params_py2 = ['ephys.CaDynamics_E2.apic.decay',
        'ephys.CaDynamics_E2.apic.gamma', 'ephys.CaDynamics_E2.axon.decay',
        'ephys.CaDynamics_E2.axon.gamma', 'ephys.CaDynamics_E2.soma.decay',
        'ephys.CaDynamics_E2.soma.gamma', 'ephys.Ca_HVA.apic.gCa_HVAbar',
        'ephys.Ca_HVA.axon.gCa_HVAbar', 'ephys.Ca_HVA.soma.gCa_HVAbar',
        'ephys.Ca_LVAst.apic.gCa_LVAstbar', 'ephys.Ca_LVAst.axon.gCa_LVAstbar',
        'ephys.Ca_LVAst.soma.gCa_LVAstbar', 'ephys.Im.apic.gImbar',
        'ephys.K_Pst.axon.gK_Pstbar', 'ephys.K_Pst.soma.gK_Pstbar',
        'ephys.K_Tst.axon.gK_Tstbar', 'ephys.K_Tst.soma.gK_Tstbar',
        'ephys.NaTa_t.apic.gNaTa_tbar', 'ephys.NaTa_t.axon.gNaTa_tbar',
        'ephys.NaTa_t.soma.gNaTa_tbar', 'ephys.Nap_Et2.axon.gNap_Et2bar',
        'ephys.Nap_Et2.soma.gNap_Et2bar', 'ephys.SK_E2.apic.gSK_E2bar',
        'ephys.SK_E2.axon.gSK_E2bar', 'ephys.SK_E2.soma.gSK_E2bar',
        'ephys.SKv3_1.apic.gSKv3_1bar', 'ephys.SKv3_1.apic.offset',
        'ephys.SKv3_1.apic.slope', 'ephys.SKv3_1.axon.gSKv3_1bar',
        'ephys.SKv3_1.soma.gSKv3_1bar', 'ephys.none.apic.g_pas',
        'ephys.none.axon.g_pas', 'ephys.none.dend.g_pas',
        'ephys.none.soma.g_pas', 'scale_apical.scale']

    params_py3 = [p.replace('ephys.CaDynamics_E2', 'ephys.CaDynamics_E2_v2') for p in params_py2]
    return params_py3



"""
code for sending request to server from notebook

import requests

url = "http://127.0.0.1:5000/matrixServer/getDensity"

data = {
    "table" : "vaex_df",
    "format" : "mean",
    "columns" : [*binbycols,value_col],
    "density_grid_shape" : [10,10]
}

response = requests.post(url, json=data)
# Check the status code of the response
if response.status_code == 200:  # 200 means success
    data = response.json()  # Assuming the server returns JSON data
    print(data)
else:
    print("Request failed with status code: {}".format(response.status_code))
    print(response.text)  # Print the response content, which may contain the error message from the server

"""