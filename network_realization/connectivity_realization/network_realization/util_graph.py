import networkx as nx
import numpy as np


def determineEdgeEndpoints(data):
    endpoints = {}
    for item in data:
        endpoints[item["edge_id"]] = -99
    for item in data:
        edgeId = item["edge_id"]
        edgePointId = item["edge_point_id"]
        if(edgePointId > 0 and edgePointId > endpoints[edgeId]):
            endpoints[edgeId] = edgePointId
    return endpoints


def determineIsSourceTarget(edgePoints, endPoints):
    for edgePoint in edgePoints:
        edgePointId = edgePoint["edge_point_id"]
        edgeId = edgePoint["edge_id"]
        endPoint = endPoints[edgeId]
        edgePoint["is_source_target"] = "none"
        if(edgePointId == 0):
            edgePoint["is_source_target"] = "source"
        elif (edgePointId == endPoint):
            edgePoint["is_source_target"] = "target"


def getSharedCube(ep1, ep2, neuronId):
    c1 = ep1["cubeId"]
    c2 = ep2["cubeId"]
    cubes1 = set(ep1["borderingCubeIds"])
    cubes1.add(c1)
    cubes2 = set(ep2["borderingCubeIds"])
    cubes2.add(c2)
    sharedCubes = cubes1 & cubes2
    if(len(sharedCubes) == 1):
        return sharedCubes.pop()
    elif(c1 in cubes2):
        return c1
    elif(c2 in cubes1):
        return c2
    else:
        raise RuntimeError("no unique shared cube", ep1, ep2, neuronId)


def buildGraph(edgesFlattened, neuronId, connectApicalToSoma=False, apicalToSomaEdge=[]):
    endpoints = determineEdgeEndpoints(edgesFlattened)
    determineIsSourceTarget(edgesFlattened, endpoints)
    g = nx.Graph()
    # add edge points as nodes
    logicalNodes = {}
    logicalNodesRev = {}
    for i in range(0, len(edgesFlattened)):
        ep = edgesFlattened[i]
        # register source and target nodes of edge
        if(ep["is_source_target"] == "source"):
            sourceNodeId = ep["source_node_id"]
            if(sourceNodeId not in logicalNodes.keys()):
                logicalNodes[sourceNodeId] = []
            logicalNodes[sourceNodeId].append(i)
            logicalNodesRev[i] = sourceNodeId
        elif(ep["is_source_target"] == "target"):
            targetNodeId = ep["target_node_id"]
            if(targetNodeId not in logicalNodes.keys()):
                logicalNodes[targetNodeId] = []
            logicalNodes[targetNodeId].append(i)
            logicalNodesRev[i] = targetNodeId
        g.add_node(i, edgeId=ep["edge_id"], sourceNodeId=ep["source_node_id"], targetNodeId=ep["target_node_id"],
                   edgePointId=ep["edge_point_id"], edgeLabel=ep["edge_label"], cubeId=ep["cubeId"],
                   borderingCubeIds=ep["borderingCubeIds"], sourceTarget=ep["is_source_target"], position=ep["position"], isRoot=False)
    # add 'geometric' edges
    for i in range(0, len(edgesFlattened) - 1):
        ep1 = edgesFlattened[i]
        ep2 = edgesFlattened[i+1]
        if(ep1["edge_id"] == ep2["edge_id"]):
            length = np.linalg.norm(ep1["position"] - ep2["position"])
            area = util_geometry.getTruncatedConeArea(
                length, ep1["radius"], ep2["radius"])
            sharedCube = getSharedCube(ep1, ep2, neuronId)
            # if((ep1["position"][2] == -650 or ep2["position"][2] == -650) and (ep1["edge_point_id"] == -1 or ep2["edge_point_id"] == -1)):
            #    print(ep1["position"], ep2["position"], length, sharedCube)
            # if(sharedCube in xyz_cubeId.keys()):
            g.add_edge(i, i+1, cubeId=sharedCube,
                       edgeLabel=ep1["edge_label"], length=length, area=area)
    # add 'logical' edges between source and terminal nodes
    for i in range(0, len(edgesFlattened)):
        if i in logicalNodesRev.keys():
            ep = edgesFlattened[i]
            sourceTarget = logicalNodesRev[i]
            neighbours = logicalNodes[sourceTarget]
            neighbours.sort()
            if(len(neighbours) > 1 and i == neighbours[0]):
                for nb in neighbours:                
                    connect = True
                    label_i = g.nodes[i]["edgeLabel"]
                    label_nb = g.nodes[nb]["edgeLabel"]
                    if(isRoot(label_i, label_nb)):
                        g.nodes[i]["isRoot"] = True
                        connect = connectApicalToSoma or not (
                            label_i == "apical")
                    if(isRoot(label_nb, label_i)):
                        g.nodes[nb]["isRoot"] = True
                        connect = connectApicalToSoma or not (
                            label_nb == "apical")
                    if(connect):
                        g.add_edge(
                            i, nb, cubeId=ep["cubeId"], edgeLabel=ep["edge_label"], length=0, area=0)
    return g


def isRoot(label_i, label_j):
    return (label_i != label_j) and (label_j == "soma")


def getRootNodes(g):
    rootNodes = []
    for n in g.nodes:
        if(g.nodes[n]["isRoot"]):
            rootNodes.append(n)
    return rootNodes

def getRootNode(g, label, NID):
    rootNodes = []
    for n in g.nodes:
        if(g.nodes[n]["isRoot"]):
            rootNodes.append(n)
    if(len(rootNodes) != 1):
        raise RuntimeError("Invalid number of root nodes ({}) in {} branch of neuron {}".format(len(rootNodes), label, NID))
    return rootNodes[0]


def calcDistancesToRoot(g, NID):
    labels = ["apical", "basal"]        
    for label in labels:
        branches = getBranchesByLabel(g, label, NID)
        for branch in branches:
            subgraph = g.subgraph(branch)
            rootNode = getRootNode(subgraph, label, NID)            
            for n in subgraph.nodes:
                try:                
                    distanceToRoot = nx.shortest_path_length(
                        subgraph, n, rootNode, "length")
                    subgraph.nodes[n]["distanceToRoot"] = distanceToRoot
                except nx.NetworkXNoPath:
                    print("node:", subgraph.nodes[n])
                    print("root node:", subgraph.nodes[rootNode])
                    raise RuntimeError("No path to root node found: NID {}".format(NID))            

def markBifurcations(g, NID):
    for n in g.nodes:
        if(g.degree(n) > 2):
            g.nodes[n]["is_bifurcation"] = True
        else:
            g.nodes[n]["is_bifurcation"] = False


def getConnectedComponents(graph):
    components = nx.connected_components(graph)
    result = []
    for c in components:
        result.append(c)
    return result

def getBranchesByLabel(g, label, NID):
    subgraph = getSubgraphByLabel(g, label)
    components = getConnectedComponents(subgraph)
    if(label in ["axon", "apical"] and len(components) > 1):
        raise RuntimeError("More than 1 {} branch in {}".format(label, NID))
    return components


def getSubgraphByLabel(g, label):
    filteredNodes = []
    for n in g.nodes:
        print(g.nodes[n])
        if(g.nodes[n]["label"] == label):
            filteredNodes.append(n)
    return g.subgraph(filteredNodes)

def getSubgraphByLabelFilter(g, label):
    filteredNodes = []
    for n in g.nodes:        
        if(label in g.nodes[n]["adjacentLabels"]):
            filteredNodes.append(n)
    return g.subgraph(filteredNodes)

def markRootNodes(g):
    for n in g.nodes:        
        if("Soma" in g.nodes[n]["adjacentLabels"]):        
            g.nodes[n]["isRoot"] = len(g.nodes[n]["adjacentLabels"]) > 1                            
        else:
            g.nodes[n]["isRoot"] = False


def sliceGraph(g, networkSpec, NID):
    range_x = networkSpec["range_x"]
    somaNode = -1
    nodesInSlice = []
    for n, soma in g.nodes(data="position"):
        if(soma[0] >= range_x[0] and soma[0] <= range_x[1]):
            nodesInSlice.append(n)
            if(g.nodes[n]["edgeLabel"] == "soma"):
                somaNode = n
    if(somaNode == -1):
        raise RuntimeError("No soma within slice " + str(NID))
    slicedGraph = g.subgraph(nodesInSlice)
    slicedGraphFromSoma = nx.node_connected_component(slicedGraph, somaNode)
    return g.subgraph(slicedGraphFromSoma).copy()


def disconnectApicalSoma(g):
    toDelete = []
    for e in g.edges():
        label1 = g.nodes[e[0]]["edgeLabel"]
        label2 = g.nodes[e[1]]["edgeLabel"]
        if((label1 == "soma" and label2 == "apical") or (
                label1 == "apical" and label2 == "soma")):
            toDelete.append(e)
    for e in toDelete:
        g.remove_edge(e[0], e[1])

def removeEdgesByLabel(g, label):
    toDelete = []
    for e in g.edges():
        if(g.edges[e]["label"] == label):        
            toDelete.append(e)
    for e in toDelete:
        g.remove_edge(e[0], e[1])

def filterByLabel(g, nodes, labels):
    filtered = []
    for n in nodes:
        if(g.nodes[n]["edgeLabel"] in labels):
            filtered.append(n)
    return filtered