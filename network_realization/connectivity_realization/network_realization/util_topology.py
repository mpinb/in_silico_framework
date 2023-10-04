import os
import sys
import networkx as nx
from networkx.drawing.nx_agraph import graphviz_layout
import matplotlib.pyplot as plt


def extractNodeName(line):
    nodeName = line.replace("{create ", "").replace("}", "")
    return nodeName


def extractNodeFromConnection(part):
    part = part.strip()
    node = part.split("(")[0]
    return node


def extractConnectedNodes(line):
    line = line.replace("{connect ", "").replace("}", "")
    parts = line.split(",")
    n1 = extractNodeFromConnection(parts[0])
    n2 = extractNodeFromConnection(parts[1])
    return n1, n2


def readUndirectedApical(filename):
    g = nx.Graph()
    g.add_node("soma")
    with open(filename) as f:
        lines = f.readlines()
        for line in lines:
            if("create apical" in line):
                nodeName = extractNodeName(line.rstrip())
                g.add_node(nodeName)
            if("connect apical" in line):
                node1, node2 = extractConnectedNodes(line.rstrip())
                g.add_edge(node1, node2)
    return g


def drawGraph(filename):
    g = readUndirectedApical(filename)
    nx.draw_networkx(g, pos=nx.spring_layout(g), node_size=20, font_size=6)
    #nx.draw_networkx(g, pos=nx.draw_circular(g), node_size=5, font_size=6)
    ax = plt.gca()
    ax.margins(0.20)
    #plt.axis("off")
    #plt.show()
    #pos = graphviz_layout(g, prog="twopi", args="")
    #plt.figure(figsize=(8, 8))
    #nx.draw(g, pos, node_size=20, alpha=0.5, node_color="blue", with_labels=True)
    plt.axis("equal")
    plt.show()


def checkApicalIsomorphism(file1, file2):
    g1 = readUndirectedApical(file1)
    g2 = readUndirectedApical(file2)
    # print(g1.nodes)
    # print(g1.edges)
    print("Graph1: nodes {}, edges {}".format(len(g1.nodes), len(g1.edges)))
    print("Graph2: nodes {}, edges {}".format(len(g2.nodes), len(g2.edges)))
    isomorphic = nx.is_isomorphic(g1, g2)
    print("Isomorphic: {}".format(isomorphic))


def printUsageAndExit():
    print("Checks if the apical dendrites of two neurons are isomorphic.")
    print("Usage:")
    print("python util_topology.py mode hoc-file1 [hoc-file2]")
    print("")
    print("mode:    isomorphic-apical, draw")
    exit()


if __name__ == '__main__':
    if(len(sys.argv) not in [3, 4]):
        printUsageAndExit()

    mode = sys.argv[1]
    file1 = sys.argv[2]
   
    if(mode == "isomorphic-apical"):
        if(len(sys.argv) != 4):
            printUsageAndExit()
        file2 = sys.argv[3]
        checkApicalIsomorphism(file1, file2)
    elif(mode == "draw"):
        drawGraph(file1)
    else:
        raise RuntimeError("invalid mode: {}".format(mode))
