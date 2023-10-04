import os
import numpy as np
import networkx as nx

def getSections(lines, isGraphSet=True):
    sections = {}
    files = {}
    currentSection = ""
    for i in range(0, len(lines)):
        line = lines[i].rstrip()
        if(isGraphSet and "File" in line and not "Files" in line):
            files[int(line.replace("File", "").replace(" ", "").replace(
                "{", ""))] = lines[i+1].rstrip().split(" ")[-1].replace("\"", "")
        if("@" in line):
            if(line in sections.keys()):
                currentSection = line
            else:
                sections[line.split(" ")[-1]] = []
        elif(not line):
            currentSection = ""
        elif(currentSection):
            sections[currentSection].append(line)
    sections["files"] = files
    return sections


def readSpatialGraphSet(filename):
    with open(filename) as f:
        lines = f.readlines()
    graphs = {}
    sections = getSections(lines)
    files = sections["files"]
    # @1 FileID, @3 transformation, @6 NID
    for i in range(0, len(sections["@6"])):
        graphs[int(sections["@6"][i])] = []
    for i in range(0, len(sections["@6"])):
        graphs[int(sections["@6"][i])].append({
            "file": os.path.join(os.path.dirname(filename), files[int(sections["@1"][i])]),
            "transformation": np.fromstring(sections["@3"][i], dtype=float, sep=' ').reshape((4, 4)).T
        })        
    return graphs


def getLabelNames(lines, parentGroup):    
    labelStack = []
    ignoreSection = False
    names = {}
    for i in range(0, len(lines)):        
        if("SpatialGraphUnitsVertex" in lines[i] or "SpatialGraphUnitsEdge" in lines[i]):
            ignoreSection = True
        if("{} {{".format(parentGroup) in lines[i].strip()):
            if(ignoreSection):
                ignoreSection = False
            else:
                labelStack.append(parentGroup)            
        elif(len(labelStack)):
            if("{" in lines[i]):
                labelStack.append(lines[i].strip().split(" ")[0])
            elif("}" in lines[i]):
                names[int(lines[i-1].strip().split(" ")[1])] = labelStack.pop()    
                if(not len(labelStack)):
                    return names        
    raise RuntimeError("Label group {} not found.".format(parentGroup))


def readSpatialGraph(filename, T = np.eye(4, dtype=float)):
    with open(filename) as f:
        lines = f.readlines()
    labelNames = getLabelNames(lines, "GraphLabels")
    sections = getSections(lines, False)
    # @3 edge, @4 numPoints, @5 label, @6 point, @7 radius
    g = nx.DiGraph()
    edges = {}
    k = 0
    for i in range(0, len(sections["@3"])):
        s_t = sections["@3"][i].split(" ")
        s_t = (int(s_t[0]), int(s_t[1]))
        points = []
        for _ in range(0, int(sections["@4"][i])):
            p = T.dot(np.fromstring(
                sections["@6"][k] + " 1", dtype=float, sep=' '))
            p[3] = float(sections["@7"][k])
            points.append(p)
            k += 1
        edges[s_t] = {
            "label": labelNames[int(sections["@5"][i])],
            "points": points
        }
    g.add_edges_from(list(edges.keys()))
    for k, v in edges.items():
        g.edges[k[0], k[1]]["label"] = v["label"]
        g.edges[k[0], k[1]]["points"] = v["points"]
    return g
