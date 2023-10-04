import networkx as nx
import numpy as np

import util_geometry
import util_graph
import util_amira


def getPlanes(sliceParams):
    xlow = sliceParams["sliceRange"][0]
    xhigh = sliceParams["sliceRange"][1]
    
    plane1 = {
        "position" : np.array([xlow, 0, 0]),
        "normal" : np.array([1, 0, 0]),
    }

    plane2 = {
        "position" : np.array([xhigh, 0, 0]),
        "normal" : np.array([-1, 0, 0]),
    }

    return plane1, plane2


def sliceNeuron(neuron, sliceParams):
    plane1, plane2 = getPlanes(sliceParams)
    sliced = traverseAndCut(neuron, plane1)    
    sliced = traverseAndCut(sliced, plane2)
    return sliced
    

def traverseAndCut(neuron, plane):

    neuronSliced = nx.DiGraph()

    visited = set()
    rootNode = util_graph.getSomaRoot(neuron)

    traversal = list(nx.edge_dfs(neuron, source=rootNode, orientation="ignore"))
    newNodeCounter = len(neuron)

    for u, v, d in traversal:
        
        edge = neuron.edges[u, v]
        nodeStart = u
        nodeEnd = v
        points = edge["points"]

        if(d == "reverse"):
            nodeStart = v
            nodeEnd = u
            points.reverse()
        
        if(not len(visited)):
            visited.add(nodeStart)
        if(nodeStart not in visited):
            continue        

        label = edge["label"]
        labelInt = edge["labelInt"]

        sides, intersectionPoints = util_geometry.intersectPlane(plane, points)      
        if(sides[0] < 0):
            raise RuntimeError("traversal started outside: {} {}: {}".format(nodeStart, nodeEnd, points[0]))

        pointsNew = [points[0]]
        newEndNode = None
        for i in range(1, len(points)):
            if(sides[i] > 0):             
                pointsNew.append(points[i])                    
            else:
                intersectionPoint = intersectionPoints[(i-1,i)]["position"]     
                pointsNew.append(intersectionPoint)
                newEndNode = newNodeCounter
                newNodeCounter += 1
                break
        
        if(newEndNode):
            neuronSliced.add_edge(nodeStart, newEndNode, label=label, labelInt = labelInt, points=pointsNew)
        else:
            visited.add(nodeEnd)
            neuronSliced.add_edge(nodeStart, nodeEnd, label=label, labelInt = labelInt, points=pointsNew)        

    neuronSliced = nx.convert_node_labels_to_integers(neuronSliced)

    return neuronSliced 


