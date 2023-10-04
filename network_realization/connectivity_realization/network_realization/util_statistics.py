import os
import sys
import glob

import util_meta


def printUsageAndExit():
    print("python util_statistics.py <realization-dir>")
    exit()


def readStats(filename):
    with open(filename) as f:
        lines = f.readlines()
        parts = lines[1].rstrip().split("\t")        
        return {
            "nSegments" : int(parts[0]),
            "nSegments_vS1" : int(parts[1])
        }

def aggregateStatistics(realizationDir):
    postFolders = glob.glob(os.path.join(realizationDir, "post_neurons", "*"))
    stats = {}
    for postFolder in postFolders:
        postId = int(os.path.basename(postFolder))
        statFile = os.path.join(postFolder, "{}_statistics.tsv".format(postId))
        if(os.path.exists(statFile)):
            stats[postId] = readStats(statFile)
        else:
            stats[postId] = None
    writeAggregateStats(stats, realizationDir)


def writeAggregateStats(stats, realizationDir):
    ids = list(stats.keys())
    ids.sort()

    neurons = util_meta.loadNeuronProps(os.path.join(realizationDir, "neurons.csv"))
    regions = util_meta.loadRegions(os.path.join(realizationDir, "regions.csv"))

    unfinished = 0

    with open(os.path.join(realizationDir, "summary.tsv"), "w+") as f:
        f.write("post_id\tcompleted\tcell_type_id\tregion_id\tregion_name\tall_inside\tsegments\tsegments_vS1\n")
        for NID in ids:
            regionId = neurons[NID]["region"]
            cellTypeId = neurons[NID]["cell_type"]
            regionName = regions[regionId]["name"]
            if(stats[NID] is None):
                f.write("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(NID, 0, cellTypeId, regionId, regionName,  -1, -1, -1))
                unfinished += 1
            else:
                stat = stats[NID]
                inside = stat["nSegments"] == stat["nSegments_vS1"]
                f.write("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(NID, 1, cellTypeId, regionId, regionName, int(inside), stat["nSegments"], stat["nSegments_vS1"]))

    print("unfinished", unfinished)


if __name__ == "__main__":
    if(len(sys.argv) != 2):
        printUsageAndExit()
    realizationDir = sys.argv[1]    
    aggregateStatistics(realizationDir)