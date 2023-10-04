'''
Created on Mar 30, 2012

@author: regger
'''
import numpy as np
from . import util_geometry
from . import util_feature_IO
import sys

class SynapseMapper(object):

    def __init__(self, cell, networkProps):
 
        self.cell = cell
        self.networkProps = networkProps   
        self.voxelEdgeMap = {}
        self.synapseCount = 0
           
    def create_synapses(self, dsc, preIds):            
        for preId in preIds:       
            for structure in list(self.cell.structures.keys()):
                structureDescriptor = ""
                if(structure == "Soma"):
                    structureDescriptor = "soma"
                elif(structure == "Dendrite"):
                    structureDescriptor = "basal"
                elif(structure == "ApicalDendrite"):
                    structureDescriptor = "apical" 
                dscCubeIds = set(dsc.keys())
                neuronCubeIds = set(self.voxelEdgeMap[structure].keys())
                sharedCubeIds = list(dscCubeIds & neuronCubeIds)                
                sharedCubeIds.sort()
                for cubeId in sharedCubeIds:                    
                    dscValue = dsc[cubeId][structureDescriptor]                                                           
                    nrOfSyn = np.random.poisson(dscValue)
                    if (nrOfSyn > 0):                            
                        edges = self.voxelEdgeMap[structure][cubeId]
                        candidatePts = list(np.random.permutation(edges))
                        # fix for situation where nrOfSyn > len(candidatePts):
                        while len(candidatePts) < nrOfSyn:
                            candidatePts.append(edges[np.random.randint(len(edges))])
                        for n in range(nrOfSyn):
                            edgeID = candidatePts[n][0]
                            edgePtID = candidatePts[n][1]
                            edgex = self.cell.sections[edgeID].relPts[edgePtID]
                            if edgex < 0.0 or edgex > 1.0:
                                raise RuntimeError('Edge x out of range')                            
                            self.cell.add_synapse(edgeID, edgePtID, edgex, preId, self.synapseCount)       
                            self.synapseCount += 1     
                        break    


    def create_synapses_feature_based(self, preIds, featuresPre, featuresPost, agg_pst, excitatory):   
        subvolumesPre = set(featuresPre.keys())        
        subvolumesPost = set(featuresPost.keys())
        featureCubeIds = subvolumesPre & subvolumesPost        
                    
        for structure in list(self.cell.structures.keys()):
            structureDescriptor = ""
            if(structure == "Soma"):
                structureDescriptor = "soma"
            elif(structure == "Dendrite"):
                structureDescriptor = "basal"
            elif(structure == "ApicalDendrite"):
                structureDescriptor = "apical" 

            excitatoryDescriptor = ""
            if(excitatory):
                excitatoryDescriptor = "exc"
            else:
                excitatoryDescriptor = "inh"

            pstDescriptor = "pst_{}_{}".format(excitatoryDescriptor, structureDescriptor)
            pstAllDescriptor = "pst_{}".format(excitatoryDescriptor)
            
            neuronCubeIds = set(self.voxelEdgeMap[structure].keys())
            sharedCubeIds = list(featureCubeIds & neuronCubeIds)                
            sharedCubeIds.sort()                

            for cubeId in sharedCubeIds:                          
                pre = featuresPre[cubeId]["boutons"]                   
                pst = featuresPost[cubeId][pstDescriptor]
                pstAll = agg_pst[cubeId][pstAllDescriptor]
                dsc = pre * pst / pstAll

                for preId in preIds: 
                    nrOfSyn = np.random.poisson(dsc)
                    if (nrOfSyn > 0):    
                        edges = self.voxelEdgeMap[structure][cubeId]
                        candidatePts = list(np.random.permutation(edges))
                        # fix for situation where nrOfSyn > len(candidatePts):
                        while len(candidatePts) < nrOfSyn:
                            candidatePts.append(edges[np.random.randint(len(edges))])
                        for n in range(nrOfSyn):
                            edgeID = candidatePts[n][0]
                            edgePtID = candidatePts[n][1]
                            edgex = self.cell.sections[edgeID].relPts[edgePtID]
                            if edgex < 0.0 or edgex > 1.0:
                                raise RuntimeError('Edge x out of range')                            
                            self.cell.add_synapse(edgeID, edgePtID, edgex, preId, self.synapseCount)       
                            self.synapseCount += 1                                        
        

    def create_voxel_edge_map(self):
        sections = self.cell.sections
        for structure in list(self.cell.structures.keys()):         
            self.voxelEdgeMap[structure] = {}
            for cubeId, cubeProps in self.networkProps["grid"].items():
                voxelBBox = util_geometry.getBox(util_geometry.getFloatFromXYZ(cubeProps["subvolume_center"]))
                for l in range(len(sections)):
                    sec = sections[l]
                    if sec.label != structure:
                        continue
                    if self._intersect_bboxes(voxelBBox, sec.bounds):
                        for n in range(sec.nrOfPts):
                            pt = sec.pts[n]
                            if self._pt_in_box(pt, voxelBBox):
                                if(cubeId not in self.voxelEdgeMap[structure].keys()):
                                    self.voxelEdgeMap[structure][cubeId] = []
                                self.voxelEdgeMap[structure][cubeId].append((l,n))   
                                self.cell.sections_vS1.add(l)     

    def _intersect_bboxes(self, bbox1, bbox2):
        for i in range(3):
            intersect = False
            if bbox1[2*i] >= bbox2[2*i] and bbox1[2*i] <= bbox2[2*i+1]:
                intersect = True
            elif bbox2[2*i] >= bbox1[2*i] and bbox2[2*i] <= bbox1[2*i+1]:
                intersect = True
            if bbox1[2*i+1] <= bbox2[2*i+1] and bbox1[2*i+1] >= bbox2[2*i]:
                intersect = True
            elif bbox2[2*i+1] <= bbox1[2*i+1] and bbox2[2*i+1] >= bbox1[2*i]:
                intersect = True
            if not intersect:
                return False
        
        return True
        
    def _pt_in_box(self, pt, box):
        return box[0] <= pt[0] <= box[1] and box[2] <= pt[1] <= box[3] and box[4] <= pt[2] <= box[5]
    