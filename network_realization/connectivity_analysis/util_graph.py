import networkx as nx
import numpy as np


def getSeparatedComponentsPre(neuron):
    components = {
        "axon" : {                    
        }
    }
    axonNodes = set()
    somaNodes = set()
    for u, v, label in neuron.edges(data = "label"):
        if(label == "Axon"):
            axonNodes.add(u)
            axonNodes.add(v)
        elif(label == "Soma"):
            somaNodes.add(u)
            somaNodes.add(v)
    axonRoot = list(axonNodes & somaNodes)
    if(len(axonRoot) != 1):
        raise RuntimeError("axon root")
    components["axon"]["root"] = axonRoot[0]
    components["axon"]["tree"] = neuron.subgraph(list(axonNodes))    
    return components


def getSeparatedComponentsPost(neuron):
    components = {
        "dendrite" : {                    
        }
    }
    somaNodes = set()
    allLabels = set()
    for u, v, label in neuron.edges(data = "label"):
        allLabels.add(label)
        if(label == "Soma"):
            somaNodes.add(u)
            somaNodes.add(v)
    dendriteRoot = list(somaNodes)[0]    
    components["dendrite"]["root"] = dendriteRoot
    components["dendrite"]["tree"] = neuron
    return components


def getSomaRoot(neuron):
    somaNodes = set()
    for u, v, label in neuron.edges(data = "label"):        
        if(label == "Soma"):
            somaNodes.add(u)
            somaNodes.add(v)
    return list(somaNodes)[0]