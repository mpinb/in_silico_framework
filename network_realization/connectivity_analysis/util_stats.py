import os
import math
import numpy as np


def getEmptyHistogram(expectedMaxValue):
    bins = np.zeros(1001)
    binSize = expectedMaxValue / 1000
    return {
        "bins": bins,
        "binSize": binSize
    }


def getEmptyFixedHistogram(nBins, maxValue):
    bins = np.zeros(nBins + 1)
    binSize = maxValue / nBins
    return {
        "bins": bins,
        "binSize": binSize
    }


def isZero(value):
    isZero = math.isclose(0, value, abs_tol=0.000000001)
    return isZero


def updateHistogram(hist, value):
    if(isZero(value)):
        hist["bins"][0] += 1
    else:
        index = int(math.ceil(value / hist["binSize"]))
        if(index < hist["bins"].shape[0]):
            hist["bins"][index] += 1
        else:
            hist["bins"][-1] += 1


def evalHistogram(hist):
    binCenters = []
    binCounts = []
    numZeros = hist["bins"][0]
    binSize = hist["binSize"]
    numValues = 0
    for i in range(0, hist["bins"].shape[0]):
        count = hist["bins"][i]
        if(count):
            binCounts.append(float(count))
            numValues += count
            binCenters.append(i*binSize - 0.5*binSize)
    result = {
        "numberOfValues": numValues,
        "numberOfZeros": numZeros,
        "binSize": binSize,
        "binCenters": binCenters,
        "binCounts": binCounts
    }

    return result


def evalHistogramNormed(hist):
    numValues = np.sum(hist["bins"])
    a = hist["bins"] / numValues    
    return a.tolist()


def evalHistogramMax(hist):
    maxValue = np.max(hist["bins"][1:])
    if(maxValue == 0):
        return hist["bins"][1:].tolist()
    a = hist["bins"][1:] / maxValue    
    return a.tolist()


def evalHistogramMaxNonempty(hist):
    maxValue = np.max(hist["bins"][1:])
    if(maxValue == 0):
        return None
    a = hist["bins"][1:] / maxValue    
    return a.tolist()


def getInnervationHistograms():
    hists = {
        "innervationHisto": getEmptyHistogram(10),
        "connectionProbabilityHisto": getEmptyHistogram(1)
    }
    return hists


def getPercentiles(): 
    prctls = {
        "probabilities" : []
    }
    return prctls


def updatePercentiles(prctls, prob):
    prctls["probabilities"].append(prob)


def evalPercentiles(prctls):
    probabilities = prctls["probabilities"]
    if(len(probabilities)):
        cp_median = np.median(probabilities)
        cp_prctl_25 = np.percentile(probabilities, 25, interpolation='higher')
        cp_prctl_75 = np.percentile(probabilities, 75, interpolation='higher')
    else: 
        cp_median = 0
        cp_prctl_25 = 0
        cp_prctl_75 = 0
    return {
        "median" : round(100*cp_median,1),
        "prctl_25" : round(100*cp_prctl_25,1),
        "prctl_75" : round(100*cp_prctl_75,1)
    }  


def getStatEmptyStatVector():
    return {
        "n": 0,
        "min": 99999,
        "max": 0,
        "sum": 0,
        "sumSquared": 0
    }


def getInnervationStats(percentiles = False):
    stats = {
        "innervation": getStatEmptyStatVector(),
        "connectionProbability": getStatEmptyStatVector(),
        "innervationPerPre": getStatEmptyStatVector(),
        "innervationPerPost": getStatEmptyStatVector(),
    }
    if(percentiles):
        stats["percentiles"] = getPercentiles()
    return stats


def updateStat(stat, value):
    stat["n"] += 1
    stat["sum"] += value
    stat["sumSquared"] += value * value
    if (value < stat["min"]):
        stat["min"] = value
    if(value > stat["max"]):
        stat["max"] = value


def evalStat(stat):
    result = {}
    if(stat["n"]):
        v = stat["sum"] / stat["n"]
        result["average"] = v
        variance = stat["sumSquared"] / stat["n"] - (v * v)    
        try:
            standardDeviation = math.sqrt(variance)            
            result["stdev"] = standardDeviation
        except:                    
            result["stdev"] = 0        
            
        result["min"] = stat["min"]
        result["max"] = stat["max"]
    else:
        result["average"] = 0
        result["stdev"] = 0
        result["min"] = 0
        result["max"] = 0
    return result


def getStatOrderAndNames():
    order = ["innervation", "connectionProbability",
             "innervationPerPre", "innervationPerPost"]
    mapping = {
        "innervation": "DSO",
        "connectionProbability": "connection_probability",
        "innervationPerPre": "DSO_per_pre_neuron",
        "innervationPerPost": "DSO_per_post_neuron"
    }
    return order, mapping


def getHistNames():
    mapping = {
        "innervationHisto": "histogram_DSO",
        "connectionProbabilityHisto": "histogram_connection_probability"
    }
    return mapping


def writeHistogram(hist, filename):
    with open(filename, "w+") as f:
        f.write(
            "bin_index (empty bins omitted),bin_min (exclusive),bin_max (inclusive),bin_value\n")
        binSize = hist["binSize"]
        binCenters = hist["binCenters"]
        binCounts = hist["binCounts"]
        for i in range(0, len(binCenters)):
            if(binCenters[i] < 0):
                f.write("0,-inf,0,{}\n".format(int(binCounts[i])))
            else:
                count = int(binCounts[i])
                low = binCenters[i] - 0.5 * binSize
                high = binCenters[i] + 0.5 * binSize
                if(count):
                    f.write("{},{:.3f},{:.3f},{}\n".format(i, low, high, count))


def writeSummary(folder, stats, hists):
    order, mapping = getStatOrderAndNames()
    filename = os.path.join(folder, "statistics.csv")
    with open(filename, "w+") as f:
        f.write("name,samples,mean,std,min,max\n")
        for item in order:
            samples = stats[item]["n"]
            stat = evalStat(stats[item])
            name = mapping[item]
            f.write("{},{},{:.3f},{:.3f},{:.3f},{:.3f}\n".format(
                name, samples, stat["average"], stat["stdev"], stat["min"], stat["max"]))
    histNames = getHistNames()
    for item, name in histNames.items():
        hist = evalHistogram(hists[item])
        filename = os.path.join(folder, "{}.csv".format(name))
        writeHistogram(hist, filename)


def probabilityArrayToHistogram(array, step = 0.01):
    bins = int(1 / step + 1)
    histogram = np.zeros(bins, dtype=int)    
    idxnonzero = array > 0
    arrayNonzero = array[idxnonzero]

    histogram[0] = array.size - np.count_nonzero(idxnonzero)
    binIndices = np.floor_divide(arrayNonzero, step)
    for idx in binIndices:
        binIdx = int(min(idx+1, idx+1))
        histogram[binIdx] += 1

    return histogram