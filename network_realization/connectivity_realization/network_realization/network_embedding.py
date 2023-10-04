'''
Created on Nov 17, 2012

@author: regger
'''

import os
import sys
import time
import numpy as np
from .synapse_mapper import SynapseMapper
from . import util_feature_IO


class NetworkMapper:
    '''
    Handles connectivity of presynaptic populations
    to multi-compartmental neuron model.
    '''

    def __init__(self, postCell, networkProps):
        self.postCell = postCell
        self.networkProps = networkProps
        self.mapper = SynapseMapper(postCell, networkProps)

    def create_network_embedding(self):
        '''
        Main method for computing synapse/connectivity
        realization from precomputed synapse densities.
        Returns anatomical connectivity map.
        '''
        self.mapper.create_voxel_edge_map()
        reverseAxonMap = {}
        for preId, mappedPreId in self.networkProps["preIds"].items():
            if(preId != self.postCell.id):
                if(mappedPreId not in reverseAxonMap.keys()):
                    reverseAxonMap[mappedPreId] = []
                reverseAxonMap[mappedPreId].append(preId)

        filenamePost = os.path.join(self.networkProps["modelDataFolder"], "RBC", "subcellular_features_postsynaptic",
                                    "{}_subcellular_features_postsynaptic.csv".format(self.postCell.id))
        featuresPost = util_feature_IO.loadFeatures(
            filenamePost, util_feature_IO.getSpec_subcellular_features_postsynaptic_sparse())

        for mappedPreId, preIds in reverseAxonMap.items():
            print("unique pre_ID {} (duplicity: {})  -->  post_ID {}".format(mappedPreId, len(preIds), self.postCell.id))
            preIds.sort()

            featuresPre = self.networkProps["featuresPre"][mappedPreId]
            exc = self.networkProps["neurons"][mappedPreId]["cell_type"] <= 10
            self.mapper.create_synapses_feature_based(preIds, featuresPre, featuresPost, self.networkProps["agg_pst"], exc)

    def getPreDescriptor(self, regionId, cellTypeId):
        regionName = self.networkProps["regions"][regionId]["name"]
        regionName = regionName.replace("S1_Septum_","")
        regionName = regionName.replace("_Barreloid","")
        cellTypeName = self.networkProps["cellTypes"][cellTypeId]["name"]
        return "{}_{}".format(cellTypeName, regionName)

    def write_population_output_files(self, baseFolder, write3DLocations=True):
        preIds = list(self.postCell.synapses.keys())
        preIds.sort()

        synapsesSeq = []
        synapseIdsSeq = []
        preDescriptorsSeq = []
        preRegionIdsSeq = []
        preCellTypeIdsSeq = []
        preIdsSeq = []

        with open(os.path.join(baseFolder, "{}.con".format(self.postCell.id)), "w+") as f:
            f.write("# Anatomical connectivity realization file; only valid with synapse realization:\n")
            f.write("# {}.syn\n".format(self.postCell.id))
            f.write("# Type - neuron ID (pre) - synapse ID\n\n")

            synapseCountsPerPreDescriptor = {}            
            for preId in preIds:
                regionId = self.networkProps["neurons"][preId]["region"]
                cellTypeId = self.networkProps["neurons"][preId]["cell_type"]
                preDescriptor = self.getPreDescriptor(regionId, cellTypeId)
                if(preDescriptor not in synapseCountsPerPreDescriptor.keys()):
                    synapseCountsPerPreDescriptor[preDescriptor] = 0                 
                for synapse in self.postCell.synapses[preId]:
                    synapseId = synapseCountsPerPreDescriptor[preDescriptor]
                    synapseCountsPerPreDescriptor[preDescriptor] += 1
                    preRegionIdsSeq.append(regionId)
                    preCellTypeIdsSeq.append(cellTypeId)
                    preIdsSeq.append(preId)
                    synapsesSeq.append(synapse)
                    synapseIdsSeq.append(synapseId)                    
                    preDescriptorsSeq.append(preDescriptor)
                    f.write("{}\t{}\t{}\n".format(preDescriptor, preId, synapseId))                    

        with open(os.path.join(baseFolder, "{}.syn".format(self.postCell.id)), "w+") as f:
            f.write("# Synapse distribution file\n")
            f.write("# corresponding to neuron ID (post): {}\n".format(self.postCell.id))
            f.write("# Type - section - section.x\n\n")
            for i in range(0, len(synapsesSeq)):
                preDescriptor = preDescriptorsSeq[i]
                synapse = synapsesSeq[i]
                f.write("{}\t{}\t{:.3f}\n".format(preDescriptor, synapse.secID, synapse.x))

        if(write3DLocations):
            with open(os.path.join(baseFolder, "{}_synapses_3D.csv".format(self.postCell.id)), "w+") as f:
                f.write("x y z pre_ID pre_region_ID pre_cell_type_ID\n")
                for i in range(0, len(synapsesSeq)):
                    synapse = synapsesSeq[i]                    
                    preId = preIdsSeq[i]
                    preRegionId = preRegionIdsSeq[i]
                    preCellTypeId = preCellTypeIdsSeq[i]
                    f.write("{:.3f} {:.3f} {:.3f} {} {} {}\n".format(synapse.coordinates[0], synapse.coordinates[1],
                                                                        synapse.coordinates[2], preId, preRegionId, preCellTypeId))

        with open(os.path.join(baseFolder, "{}_statistics.tsv".format(self.postCell.id)), "w+") as f:
            nSections = len(self.postCell.sections)
            nSections_vS1 = len(self.postCell.sections_vS1)
            f.write("sections\tsections_vS1\n")
            f.write("{}\t{}\n".format(nSections, nSections_vS1))
