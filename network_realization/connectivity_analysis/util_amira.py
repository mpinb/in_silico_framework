import os
import sys
import numpy as np
import networkx as nx
import util_amira_write


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


def readSpatialGraphSet(filename, legacy = True):
    with open(filename) as f:
        lines = f.readlines()
    graphs = {}
    sections = getSections(lines)
    files = sections["files"]
    # @1 FileID, @3 transformation, @4 morph type, @6 NID
    secMorph = "@4"
    secNID = "@6"
    if(not legacy):
        # @4 NID, @6 morph type
        secMorph = "@6"
        secNID = "@4"
    for i in range(0, len(sections[secNID])):
        graphs[int(sections[secNID][i])] = []
    for i in range(0, len(sections[secNID])):
        graphs[int(sections[secNID][i])].append({
            "graphId": i,
            "morphType": int(sections[secMorph][i]),
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


def readSpatialGraph(filename, T=np.eye(4, dtype=float), labelFilter = []):
    with open(filename) as f:
        linesRaw = f.readlines()
    lines = []
    for line in linesRaw:
        if(not "&" in line):
            lines.append(line)
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
        label = labelNames[int(sections["@5"][i])]
        if(not labelFilter or label in labelFilter):
            edges[s_t] = {
                "label": label,
                "labelInt": int(sections["@5"][i]),
                "points": points
            }
    g.add_edges_from(list(edges.keys()))
    for k, v in edges.items():
        g.edges[k[0], k[1]]["label"] = v["label"]
        g.edges[k[0], k[1]]["labelInt"] = v["labelInt"]
        g.edges[k[0], k[1]]["points"] = v["points"]
    if(labelFilter):
        g = nx.convert_node_labels_to_integers(g)
    return g


def getCoords(points):
    coords = []
    for p in points:
        coords.append(p[0:3])           
    return coords


def getRadii(points):
    radii = []
    for p in points:
        if(p.shape[0] == 4):
            radii.append(p[3])  
        else:
            radii.append(0)
    return radii


def writeSpatialGraph(filename, g):
    props = {
        "numVertex" : len(g.nodes),
        "numEdge" : len(g.edges),
        "numPoint" : 0,
        "edgeProps" : [],
        "vertexCoords" : {}
    }
    for e in g.edges:
        u = e[0]
        v = e[1]
        points = g.edges[u, v]["points"]
        props["edgeProps"].append({
            "u" : u,
            "v" : v,                        
            "labelInt" : g.edges[u, v]["labelInt"],
            "points" : getCoords(points),
            "radii" : getRadii(points)
        })        
        props["numPoint"] += len(points)
        props["vertexCoords"][u] = points[0][0:3]
        props["vertexCoords"][v] = points[-1][0:3]       
    with open(filename, "w+") as f: 
        util_amira_write.writeHeader(f, props)
        if(len(g.edges)):
            f.write("\n@1\n")       
            for i in range(0, len(g.nodes)):                       
                coords = props["vertexCoords"][i]
                f.write("{:.6f} {:.6f} {:.6f}\n".format(coords[0], coords[1], coords[2]))
            f.write("\n@2\n")
            for i in range(0, len(g.nodes)):            
                f.write("0\n")
            f.write("\n@3\n")
            for edge in props["edgeProps"]:
                f.write("{} {}\n".format(edge["u"],edge["v"]))
            f.write("\n@4\n")
            for edge in props["edgeProps"]:
                f.write("{}\n".format(len(edge["points"])))            
            f.write("\n@5\n")
            for edge in props["edgeProps"]:
                f.write("{}\n".format(edge["labelInt"]))
            f.write("\n@6\n")
            for edge in props["edgeProps"]:
                for point in edge["points"]:
                    f.write("{:.6f} {:.6f} {:.6f}\n".format(point[0], point[1], point[2]))
            f.write("\n@7\n")
            for edge in props["edgeProps"]:
                for radius in edge["radii"]:
                    f.write("{:.6f}\n".format(radius))


def mapLabelName(name):
    if(name == "Axon"):
        return "axon"
    elif(name == "ApicalDendrite"):
        return "apical"
    elif(name == "BasalDendrite"):
        return "basal"
    elif(name == "Soma"):
        return "soma"
    else:
        raise RuntimeError("Unknown label: {}".format(name))


def readSpatialGraphEdgePointsFlat(filename, T=np.eye(4, dtype=float)):
    with open(filename) as f:
        linesRaw = f.readlines()
    lines = []
    for line in linesRaw:
        if(not "&" in line):
            lines.append(line)
    labelNames = getLabelNames(lines, "GraphLabels")
    sections = getSections(lines, False)
    # @3 edge, @4 numPoints, @5 label, @6 point, @7 radius
    edgePoints = []
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
        for j in range(0, len(points)):
            point = points[j]
            edgePoints.append({
                "edge_id": i,
                "edge_point_id" : j,
                "source_node_id": s_t[0],
                "target_node_id": s_t[1],
                "edge_label": mapLabelName(labelNames[int(sections["@5"][i])]),
                "position": np.array(point[0:3]),
                "radius": point[3]
            })
    return edgePoints


def readSpatialGraphEdgePointsNumpy(filename, T=np.eye(4, dtype=float)):
    with open(filename) as f:
        lines = f.readlines()
    sections = getSections(lines, False)
    # @3 edge, @4 numPoints, @5 label, @6 point, @7 radius   
    edgePoints = sections["@6"]
    n = len(edgePoints)
    D = np.zeros(shape = (n, 4))
    for i in range(0, n):
        D[i,:] = T.dot(np.fromstring(edgePoints[i] + " 1", dtype=float, sep=' '))
    return D


def getSomaPosition(g, somaLabel="Soma"):
    points = []
    for edge in g.edges.data():
        if(edge[2]["label"] == somaLabel):
            points.append(edge[2]["points"][0:3])
    return np.mean(np.vstack(points), axis=0)


def readLandmarks(filename):
    with open(filename) as f:
        lines = f.readlines()
    landmarks = []
    sections = getSections(lines)
    # @1 Markers
    for i in range(0, len(sections["@1"])):
        landmarks.append(np.fromstring(sections["@1"][i], dtype=float, sep=' '))
    return landmarks


def writeLandmarks(filename, positions):
    n = len(positions)
    with open(filename, "w+") as f:
        f.write("# Avizo 3D ASCII 3.0\n\n")
        f.write("define Markers {}\n\n".format(n))
        f.write("Parameters {\n")
        f.write("\tNumSets 1,\n")
        f.write("\tContentType \"LandmarkSet\"\n")
        f.write("}\n\n")
        f.write("Markers { float[3] Coordinates } @1\n\n")
        f.write("# Data section follows\n@1\n")
        for position in positions:
            f.write("{:.3f} {:.3f} {:.3f}\n".format(position[0], position[1], position[2]))


    