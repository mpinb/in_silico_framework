'''This module retrieves the filename of the morphology by id.'''
import sys
import os
import util_amira

if __name__ == '__main__':
    modelDataFolder = sys.argv[1]
    spatial_graph_set = util_amira.readSpatialGraphSet(os.path.join(modelDataFolder, "morphologies", "MorphologiesWithNeuronIDs.am"))
    for postId in spatial_graph_set.keys():
        print(postId, spatial_graph_set[int(postId)][0]["file"])
