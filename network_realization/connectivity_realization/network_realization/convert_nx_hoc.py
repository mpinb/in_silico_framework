import sys
import numpy as np
import copy
import networkx as nx

from . import util_amira
from . import convert_nx_asc
from . import util_graph


def getHocLabel(label):
    if(label == "Soma"):
        return "soma"
    elif(label == "BasalDendrite"):
        return "dend"
    elif(label == "ApicalDendrite"):
        return "apical"
    elif(label == "Axon"):
        return "axon"
    else:
        raise RuntimeError("Unexpected label: {}".format(label))


def getSegment(name, previousName, previousConnectivity, points, color):
    lines = []
    lines.append("{{create {}}}".format(name))
    if(previousName):
        lines.append("{{connect {}(0), {}({})}}".format(name, previousName, previousConnectivity))
    lines.append("{{access {}}}".format(name))
    lines.append("{nseg = 1}")
    lines.append("{{strdef color color = \"{}\"}}".format(color))
    lines.append("{pt3dclear()}")
    for point in points:
        lines.append("{{pt3dadd({0:.3f},{1:.3f},{2:.3f},{3:.3f})}}".format(point[0], point[1], point[2], point[3]))
    return lines


def getSomaPoints(g):
    somaPoints = []
    rootIntersections = {}
    k = 0
    edges = list(nx.edge_dfs(g, source=0, orientation='ignore'))
    for (u, v, d) in edges:
        points = copy.deepcopy(g.edges[u, v]["points"])
        if(d == "reverse"):
            points.reverse()
        rootIntersections[u] = k / (len(edges) + 1)
        if(k == len(edges) - 1):
            somaPoints.extend(points[0:-2])
            rootIntersections[v] = 1
        else:
            somaPoints.extend(points)
        k += 1
    return somaPoints, rootIntersections


def getSegmentName(incomingSegmentName, outgoingCount, baseName):
    if(incomingSegmentName == "soma"):
        return "{}_{}".format(baseName, outgoingCount)
    else:
        return "{}_{}".format(incomingSegmentName, outgoingCount)


def getConnectionValue(previousSegmentName, rootIntersection):
    if(previousSegmentName == "soma"):
        return str(rootIntersection)
    else:
        return "1"


def traverseComponent(g, rootNode, rootIntersection, baseIndex, label, color):    
    segments = []    
    incomingSegments = {}
    outgoingCounts = {}
    baseName = "{}_{}".format(label, baseIndex)
    edges = list(nx.edge_dfs(g, source=rootNode, orientation='ignore'))            
    for (u, v, d) in edges:
        if(u == rootNode):
            incomingSegments[u] = "soma"
        if(u not in outgoingCounts.keys()):
            outgoingCounts[u] = 0
        else:
            outgoingCounts[u] += 1
        segmentName = getSegmentName(incomingSegments[u], outgoingCounts[u], baseName) 
        incomingSegments[v] = segmentName
        previousSegmentName = incomingSegments[u]
        connectionValue = getConnectionValue(previousSegmentName, rootIntersection)    
        
        # write segment
        points = copy.deepcopy(g.edges[u, v]["points"])
        if(d == "reverse"):
            points.reverse()
        segments.append(getSegment(segmentName, previousSegmentName, connectionValue, points, color))
    return segments


def save_HOC(g, filename):
    components = convert_nx_asc.getConnectedComponents(g)
    nComponents = len(components)
    if(len(components) != 1):
        raise RuntimeError(
            "Expected connected graph with single component. Number of components: {}".format(nComponents))

    util_graph.markRootNodes(g)
    g_soma = util_graph.getSubgraphByLabelFilter(g, "Soma")
    soma_components = convert_nx_asc.getConnectedComponents(g_soma)
    if(len(soma_components) != 1):
        raise RuntimeError("More than one soma")

    segments = []
    somaPoints, rootIntersections = getSomaPoints(g_soma)
    segments.append(getSegment("soma", "", "", somaPoints, "Red"))

    util_graph.removeEdgesByLabel(g, "Soma")
    g_basal = util_graph.getSubgraphByLabelFilter(g, "BasalDendrite")
    g_apical = util_graph.getSubgraphByLabelFilter(g, "ApicalDendrite")
    g_basal_components = convert_nx_asc.getConnectedComponents(g_basal)
    g_apical_components = convert_nx_asc.getConnectedComponents(g_apical)

    for i in range(0, len(g_basal_components)):
        basalDendrite = g_basal_components[i]
        basalRootNodes = util_graph.getRootNodes(basalDendrite)
        if(not len(basalRootNodes)):
            raise RuntimeError("No root node in basal dendrite {}".format(i))
        if(len(basalRootNodes) > 1):
            raise RuntimeError("More than one root node in basal dendrite {}".format(i))
        basalRoot = basalRootNodes[0]
        basalRootIntersection = rootIntersections[basalRoot]
        segments.extend(traverseComponent(basalDendrite, basalRoot, basalRootIntersection, i+1, "dend", "Blue"))

    if(len(g_apical_components) > 1):
        raise RuntimeError("More than one apical dendrite.")
    elif(len(g_apical_components) == 1):
        apicalDendrite = g_apical_components[0]
        apicalRootNodes = util_graph.getRootNodes(apicalDendrite)
        if(not len(apicalRootNodes)):
            raise RuntimeError("No root node in apical dendrite {}".format(i))
        if(len(apicalRootNodes) > 1):
            raise RuntimeError("More than one root node in apical dendrite {}".format(i))
        apicalRoot = apicalRootNodes[0]
        apicalRootIntersection = rootIntersections[apicalRoot]
        segments.extend(traverseComponent(apicalDendrite, apicalRoot, apicalRootIntersection, 1, "apical", "Blue"))

    with open(filename, "w+") as f:
        for i in range(0, len(segments)):
            if(i != 0):
                f.write("\n")
            f.write("\n".join(segments[i]))
            f.write("\n")
