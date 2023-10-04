import sys
import numpy as np
import networkx as nx


def getNameMapping():
    mapping = {
        "CellBody": ["soma", "Soma", "cellBody", "CellBody"],
        "Apical": ["apical", "Apical", "ApicalDendrite"],
        "Dendrite": ["dendrite", "Dendrite", "basal", "BasalDendrite"],
        "Axon": ["axon", "Axon"],
    }
    return mapping


def getStandardColors():
    defaultColors = {
        "CellBody": [255, 0, 0],
        "Apical": [255, 0, 0],
        "Dendrite": [255, 0, 0],
        "Axon": [0, 0, 255]
    }
    return defaultColors


def getDefaultColor():
    return [0, 255, 0]


"""
def loadGraphFromSWC(filename):
    # parse SWC into a graph datastructure (e.g., https://networkx.github.io/)
    return mock_data.getGraph()
"""


def writeHeader():
    return ["; File created with, ...", "; Converter version ..."]


def getConnectedComponents(g):
    gUndirected = g.to_undirected()
    nodesPerComponent = nx.connected_components(gUndirected)
    components = list(map(g.subgraph, nodesPerComponent))
    return components


def printCycle(g, cycle):
    print("Node IDs in cycle:")
    for edge in cycle:
        print(edge[0] + 1)
    print("> Edge Points in cycle:")
    for edge in cycle:
        print(g.edges[edge[0], edge[1]])
        print(edge)
        #print(g.edges(data=True)[edge[0], edge[1]])


def isClosedContour(g):
    try:
        cycle = list(nx.find_cycle(g, orientation='ignore'))
        if(len(cycle) != len(g.edges)):
            print("Graph has cycle that is not a closed contour.")
            printCycle(g, cycle)
            raise RuntimeError("Graph has cycle that is not a closed contour.")
        return True
    except nx.NetworkXNoCycle:
        return False


def getComponentName(g):
    names = set()
    for node, labels in g.nodes(data="adjacentLabels"):
        names |= labels
    if(len(names) != 1):
        raise RuntimeError("Component not uniquely labelled.")
    name = names.pop()
    mapping = getNameMapping()
    for standardName, aliasNames in mapping.items():
        if(name in aliasNames):
            return standardName
    return name


def getStandardName(name):
    mapping = getNameMapping()
    for standardName, aliasNames in mapping.items():
        if(name in aliasNames):
            return standardName
    return name
    #raise RuntimeError("Unexpected label {}".format(name))


def relabelEdges(g):
    for u, v, label in g.edges(data="label"):
        g.edges[u, v]["label"] = getStandardName(label)


def writeColor(g):
    name = getComponentName(g)
    if(name not in getStandardColors().keys()):
        color = getDefaultColor()
    else:
        color = getStandardColors()[name]
    return "(Color RGB({0}, {1}, {2}))".format(*color)


def getClosedContour(g):
    lines = []
    return lines


def getRootNodeClosedContour(g):
    return next(iter(g.nodes))


def getRootNodeBranchedStructure(g):
    for node in g.nodes:
        # If we cut the connection to the soma, the replacement node has a negative index
        # and can be used as root node.
        if(node < 0):
            return node
    # Otherwise, we could use any heuristic to determine the root node of the branch
    # (e.g., Euclidean distance to the soma). To be implemented ...
    return next(iter(g.nodes))


def getUnvisitedEdges(g, n):
    # unvisited edges adjacent to n
    inEdges = g.in_edges(n, data="visited", default=False)
    outEdges = g.out_edges(n, data="visited", default=False)
    unvisitedEdges = []
    for e in inEdges:
        if(not e[2]):
            unvisitedEdges.append(e)
    for e in outEdges:
        if(not e[2]):
            unvisitedEdges.append(e)
    return unvisitedEdges


def setEdgeVisited(g, e):
    # mark edge as visited
    return None


def writePoint(edgePoint):
    return "({:.3f} {:.3f} {:.3f} {:.3f})".format(*edgePoint)


def getEdgePointAtLocationOfNode(g, n):
    inEdges = list(g.in_edges(n, data="points"))
    if(len(inEdges)):
        return inEdges[0][2][-1]
    else:
        outEdges = list(g.out_edges(n, data="points"))
        return outEdges[0][2][0]


def writeNodePoint(g, n):
    edgePoint = getEdgePointAtLocationOfNode(g, n)
    return writePoint(edgePoint)


def getNextNode(n, e):
    if(e[0] == n):
        return e[1]
    else:
        return e[0]


def walkRevert(g, n, e):
    # True, if n is not the source node of e, but the target node
    return False


def getEdgePoints(g, e):
    # get edge points of edge e
    return []


def removeIntermediateNodesFromContour(g):
    # remove all nodes except one such that the contour has one node an one edge
    return g


def traverse(lines, g, node, depth, brackets):
    # recursively traverse graph starting at 'node'
    unvisitedEdges = getUnvisitedEdges(g, node)
    isRoot = depth == 0
    isDegenerateRoot = False  # a root that is at the same time a bifurcation

    if(isRoot):
        if(len(unvisitedEdges) == 1):
            edge = unvisitedEdges[0]
            nextNode = getNextNode(node, edge)
            walkEdge(lines, g, node, edge, True)
            traverse(lines, g, nextNode, depth + 1, brackets)
        else:
            isDegenerateRoot = True
            lines.append(writeNodePoint(g, node))

    if(not isRoot or isDegenerateRoot):
        if(len(unvisitedEdges) > 0):
            if(len(unvisitedEdges) == 1):
                edge = unvisitedEdges[0]
                nextNode = getNextNode(node, edge)
                walkEdge(lines, g, node, edge, False)
                traverse(lines, g, nextNode, depth + 1, brackets)
            else:
                lines.append("(")
                brackets[0] += 1
                for i in range(0, len(unvisitedEdges)):
                    edge = unvisitedEdges[i]
                    nextNode = getNextNode(node, edge)
                    walkEdge(lines, g, node, edge, False)
                    traverse(lines, g, nextNode, depth + 1, brackets)
                    if(i < len(unvisitedEdges) - 1):
                        lines.append("|")
                lines.append(")")
                brackets[1] += 1
        else:
            lines.append("Normal")


def walkEdge(lines, g, n, edge, includeFirst):
    reverse = edge[1] == n
    edgePoints = g.edges[edge[0], edge[1]]["points"]
    lines.extend(writeEdgePoints(edgePoints, reverse, includeFirst))
    g.edges[edge[0], edge[1]]["visited"] = True


def writeEdgePoints(edgePoints, reverse, includeFirst):
    lines = []
    if(reverse):
        if(includeFirst):
            lines.append(writePoint(edgePoints[-1]))
        for i in range(len(edgePoints)-2, -1, -1):
            lines.append(writePoint(edgePoints[i]))
    else:
        if(includeFirst):
            lines.append(writePoint(edgePoints[0]))
        for i in range(1, len(edgePoints)):
            lines.append(writePoint(edgePoints[i]))
    return lines


def writeClosedContour(g):
    # write a closed contour (e.g., barrel)
    lines = []
    n = getRootNodeClosedContour(g)
    edges = list(nx.edge_dfs(g, source=n, orientation="ignore"))
    for i in range(0, len(edges)):
        edge = edges[i]
        reverse = edge[2] == "reverse"
        edgePoints = g[edge[0]][edge[1]]["points"]
        lines.extend(writeEdgePoints(edgePoints, reverse, i == 0))
    return lines


def writeBranchedStructure(g):
    # write a branched structure (e.g., axon)
    brackets = [0, 0]
    lines = []
    rootNode = getRootNodeBranchedStructure(g)
    traverse(lines, g, rootNode, 0, brackets)
    if(brackets[0] != brackets[1]):
        msg = "Syntax error. Open brackets {} closed brackets {}".format(
            *brackets)
        print(msg)
        raise RuntimeError(msg)
    return lines


def removeIsolatedNodes(g):
    return None


def labelNodesByEdgeLabels(g):
    for n in g:
        g.nodes[n]["adjacentLabels"] = set()
    for u, v, label in g.edges(data='label'):
        g.nodes[u]["adjacentLabels"].add(label)
        g.nodes[v]["adjacentLabels"].add(label)


def rerouteEdge(g, original, rerouted):
    label = g.edges[original[0], original[1]]["label"]
    points = np.copy(g.edges[original[0], original[1]]["points"])
    g.remove_edge(original[0], original[1])
    g.add_edge(rerouted[0], rerouted[1], label=label, points=points)


def separateBranchSoma(g):
    edgesToReroute = []
    nextNodeLabel = -1

    for u, v, label in g.edges(data='label'):
        if(label != "CellBody"):
            uIsSoma = "CellBody" in g.nodes[u]["adjacentLabels"]
            vIsSoma = "CellBody" in g.nodes[v]["adjacentLabels"]
            if(uIsSoma and vIsSoma):
                raise RuntimeError("Invalid labelling.")
            elif(uIsSoma):
                edgesToReroute.append({
                    "original": [u, v],
                    "rerouted": [nextNodeLabel, v]
                })
                nextNodeLabel -= 1
            elif(vIsSoma):
                edgesToReroute.append({
                    "original": [u, v],
                    "rerouted": [u, nextNodeLabel]
                })
                nextNodeLabel -= 1
    for edge in edgesToReroute:
        rerouteEdge(g, edge["original"], edge["rerouted"])


def postprocessGraph(g, separateSoma = True, relabel = True):
    removeIsolatedNodes(g)
    if(relabel):
        relabelEdges(g)
    labelNodesByEdgeLabels(g)
    if(separateSoma):
        separateBranchSoma(g)
        labelNodesByEdgeLabels(g)
    checkCycles(g)

def checkCycles(g):
    components = getConnectedComponents(g)
    for component in components:
        isClosedContour(component)


def assertBrackets(lines, k):
    joined = "\n".join(lines)
    openBrackets = joined.count("(")
    closedBrackets = joined.count(")")
    if(openBrackets != closedBrackets):
        raise RuntimeError("Open and closed brackets mismatch.")


def sortComponents(components):
    componentsSorted = []
    cellBody = []
    other = []
    for component in components:
        name = getComponentName(component)
        if(name == "CellBody"):
            cellBody.append(component)
        else:
            other.append(component)

    componentsSorted.extend(cellBody)
    componentsSorted.extend(other)
    return componentsSorted


def writeGraph(g):
    # write complete graph, usually consisting of multiple components
    lines = []
    components = getConnectedComponents(g)
    components = sortComponents(components)
    k = 0
    for component in components:
        k += 1

        try:
            if(isClosedContour(component)):
                lines.append("(\"{0}\"".format(getComponentName(component)))
                lines.append(writeColor(component))
                lines.append("(Closed)")
                lines.extend(writeClosedContour(component))
            else:
                lines.append("(")
                lines.append("({0})".format(getComponentName(component)))
                lines.append(writeColor(component))
                lines.append("(Object)")
                lines.extend(writeBranchedStructure(component))
            lines.append(")")
            assertBrackets(lines, k)
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            print(message)
            exit(1)

    return lines


def saveGraphToASC(filename, g):
    # write graph to ASC file
    lines = []
    lines.extend(writeHeader())
    lines.extend(writeGraph(g))
    with open(filename, "w+") as f:
        f.write("\n".join(lines))
