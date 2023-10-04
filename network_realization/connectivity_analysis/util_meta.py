import os
from sortedcontainers import SortedDict
import numpy as np
import collections
import constants


def loadNeuronProps(filename):
    with open(filename) as f:
        lines = f.readlines()
        labels = lines[0].rstrip().split(",")
        isSlice = "tissue_depth_low" in labels  # rename tissue_depth
        neuronProps = SortedDict()
        for i in range(1, len(lines)):
            line = lines[i].rstrip().split(",")

            props = {}
            props["graph_id"] = int(line[labels.index("graph_id")])
            props["soma"] = np.array([float(line[labels.index("soma_x")]), float(
                line[labels.index("soma_y")]), float(line[labels.index("soma_z")])])
            props["cell_type"] = int(line[labels.index("cell_type")])
            props["synaptic_side"] = int(line[labels.index("synaptic_side")])
            props["region"] = int(line[labels.index("region")])
            props["nearest_column"] = int(line[labels.index("nearest_column")])
            props["laminar_location"] = int(
                line[labels.index("laminar_location")])
            props["region"] = int(line[labels.index("region")])
            props["cortical_depth"] = float(
                line[labels.index("cortical_depth")])
            props["inside_vS1"] = int(line[labels.index("inside_vS1")])
            if(isSlice):
                props["tissue_depth"] = float(
                    line[labels.index("tissue_depth_low")])  # rename tissue_depth
                props["tissue_depth_inverted"] = float(
                    line[labels.index("tissue_depth_high")])  # rename tissue_depth_inverted

            neuronProps[int(line[labels.index("id")])] = props
    return neuronProps


def saveNeuronProps(neurons, filename, isSlice=False):
    with open(filename, "w+") as f:
        if(isSlice):
            header = "id,graph_id,soma_x,soma_y,soma_z,cell_type,nearest_column,region,laminar_location,cortical_depth,synaptic_side,inside_vS1,tissue_depth,tissue_depth_inverted,axon_matched\n"
        else:
            header = "id,graph_id,soma_x,soma_y,soma_z,cell_type,nearest_column,region,laminar_location,cortical_depth,synaptic_side,inside_vS1\n"
        f.write(header)
        for NID, props in neurons.items():

            if(not isSlice):
                line = "{:d},{:d},{:.3f},{:.3f},{:.3f},{:d},{:d},{:d},{:d},{:.3f},{:d},{:d}\n".format(NID, props["graph_id"],
                                                                                                      props["soma"][0], props["soma"][
                                                                                                      1], props["soma"][2],
                                                                                                      props["cell_type"],
                                                                                                      props["nearest_column"],
                                                                                                      props["region"],
                                                                                                      props["laminar_location"],
                                                                                                      props["cortical_depth"],
                                                                                                      props["synaptic_side"],
                                                                                                      props["inside_vS1"])
            else:
                line = "{:d},{:d},{:.3f},{:.3f},{:.3f},{:d},{:d},{:d},{:d},{:.3f},{:d},{:d},{:.3f},{:.3f},{:d}\n".format(NID, props["graph_id"],
                                                                                                                         props["soma"][0], props["soma"][
                    1], props["soma"][2],
                    props["cell_type"],
                    props["nearest_column"],
                    props["region"],
                    props["laminar_location"],
                    props["cortical_depth"],
                    props["synaptic_side"],
                    props["inside_vS1"],
                    props["tissue_depth"],
                    props["tissue_depth_inverted"],
                    props["axon_matched"])
            f.write(line)


def getPostIds(neurons):
    postIds = []
    for k, v in neurons.items():
        if(v["synaptic_side"] in [1, 2] and v["inside_vS1"]):
            postIds.append(k)
    postIds.sort()
    return postIds


def setOriginalCellTypes(neurons):
    neuronsOriginal = loadNeuronProps(os.path.join(
        os.environ["RBC_EXPORT_DIR"], "meta", "neurons.csv"))
    for NID, props in neurons.items():
        props["cell_type"] = neuronsOriginal[NID]["cell_type"]


def loadAxonMapping(filename):
    with open(filename) as f:
        lines = f.readlines()
        mapping = collections.OrderedDict()
        for i in range(1, len(lines)):
            line = lines[i].rstrip()
            parts = line.split(",")
            mapping[int(parts[0])] = int(parts[1])
        return mapping


def saveAxonMapping(axonMapping, filename):
    with open(filename, "w+") as f:
        f.write("id,mapped_id\n")
        for id, mappedId in axonMapping.items():
            f.write("{:d},{:d}\n".format(id, mappedId))


def loadRegions(filename):
    with open(filename) as f:
        lines = f.readlines()
        labels = lines[0].rstrip().split(",")
        regions = SortedDict()
        for i in range(1, len(lines)):
            line = lines[i].rstrip().split(",")

            region = {}
            region["name"] = line[labels.index("name")]
            region["parent_id"] = int(line[labels.index("parent_id")])

            regions[int(line[labels.index("id")])] = region
    return regions


def getRegionId(regions, name):
    for id, props in regions.items():
        if(name == props["name"]):
            return id
    return None


def getRegionDisplayName(name):
    return name.replace("S1_Septum_", "").replace("_Barreloid", "")


def loadCellTypes(filename):
    with open(filename) as f:
        lines = f.readlines()
        labels = lines[0].rstrip().split(",")
        loadBoutonDensities = "density_bouton_infragranular" in labels
        cell_types = SortedDict()
        for i in range(1, len(lines)):
            line = lines[i].rstrip().split(",")

            props = {}
            props["name"] = line[labels.index("name")]
            props["excitatory"] = int(line[labels.index("excitatory")])
            if(loadBoutonDensities):
                props["density_bouton_infragranular"] = float(
                    line[labels.index("density_bouton_infragranular")])
                props["density_bouton_granular"] = float(
                    line[labels.index("density_bouton_granular")])
                props["density_bouton_supragranular"] = float(
                    line[labels.index("density_bouton_supragranular")])

            cell_types[int(line[labels.index("id")])] = props
    return cell_types


def loadBoutonDensityMap(networkDir):
    cellTypes = loadCellTypes(os.path.join(networkDir, "meta", "cell_types.csv"))
    boutonDensities = {}
    for cellType, props in cellTypes.items():
        boutonDensities[cellType] = {
            0: 0,
            1: props["density_bouton_infragranular"],
            2: props["density_bouton_granular"],
            3: props["density_bouton_supragranular"]
        }
    return boutonDensities


def loadPstDensityMap(networkDir):
    cellTypesOriginal = loadCellTypes(os.path.join(networkDir, "meta", "cell_types.csv"))
    pstDensities = loadPstDensities(os.path.join(networkDir, "meta", "pst_densities.csv"))
    pstMap = {}
    for ctId, props in cellTypesOriginal.items():
        name = props["name"]
        if(name != "VPM"):
            pstMap[ctId] = pstDensities[name]
    return pstMap


def getCellTypeId(cell_types, name):
    for id, props in cell_types.items():
        if(name == props["name"]):
            return id
    return None


def saveCellTypesProcessed(celltypes, filename):
    with open(filename, "w+") as f:
        f.write("id,name,excitatory\n")
        for id, props in celltypes.items():
            f.write("{:d},{:s},{:d}\n".format(
                id, props["name"], props["excitatory"]))


def getDensityProps(line, labels):
    props = {}
    for label in labels[2:]:
        props[label] = float(line[labels.index(label)])
    return props


def loadPstDensities(filename):
    with open(filename) as f:
        lines = f.readlines()
        labels = lines[0].rstrip().split(",")
        densities = {}
        for i in range(1, len(lines)):
            line = lines[i].rstrip().split(",")
            name = line[labels.index("post_cell_type")]
            if(name not in densities.keys()):
                densities[name] = {}
            if(line[labels.index("pre_cell_type")] == "EXC_ANY"):
                densities[name]["exc"] = getDensityProps(line, labels)
            else:
                densities[name]["inh"] = getDensityProps(line, labels)
    return densities


def writeGrid(filename, cubes):
    with open(filename, "w+") as f:
        f.write("id,subvolume_center,laminar_location,cortical_depth,region\n")
        cubeIds = list(cubes.keys())
        cubeIds.sort()
        for cubeId in cubeIds:
            f.write("{},{},0,-1,-1\n".format(cubeId, cubes[cubeId]))


def loadGrid(filename):
    with open(filename) as f:
        lines = f.readlines()
        labels = lines[0].rstrip().split(",")
        grid = {}
        for i in range(1, len(lines)):
            line = lines[i].rstrip().split(",")
            props = {}
            props["id"] = int(line[labels.index("id")])
            props["laminar_location"] = getLaminarLocation(
                int(line[labels.index("laminar_location")]))
            if("cortical_depth" in labels):
                props["cortical_depth"] = float(line[labels.index("cortical_depth")])
            else:
                props["cortical_depth"] = None
            if("region" in labels):
                props["region"] = int(line[labels.index("region")])
            else:
                props["region"] = None
            grid[line[labels.index("subvolume_center")]] = props
    return grid


def writeGrid_ixiyiz(filename, grid):
    with open(filename, "w+") as f:
        f.write("ix,iy,iz,inside_vS1,laminar_location\n")
        for ixiyiz, values in grid.items():
            f.write("{},{},{},{},{}\n".format(int(ixiyiz[0]), int(ixiyiz[1]), int(ixiyiz[2]), int(values["inside_vS1"]), int(values["laminar_location"])))


def loadGrid_ixiyiz(filename, onlyInside=False):
    grid = {}
    with open(filename) as f:
        lines = f.readlines()
        for i in range(1, len(lines)):
            parts = lines[i].rstrip().split(",")
            ixiyiz = (int(parts[0]), int(parts[1]), int(parts[2]))
            inside = bool(int(parts[3]))
            if(inside or not onlyInside):
                grid[ixiyiz] = {
                    "inside_vS1": inside,
                    "laminar_location": int(parts[4])
                }
    return grid


def loadGridCells(filename):
    D = np.loadtxt(filename, delimiter=",", skiprows=1, usecols=(0, 1, 2), dtype=int).reshape((-1,3))
    gridCells = set()
    for i in range(0, D.shape[0]):
        gridCells.add((D[i][0], D[i][1], D[i][2]))
    return gridCells


def getLaminarLocation(locationId):
    locationId = convertLayerInfraGranSupra(locationId)
    if(locationId == 0):
        return "unknown"
    elif(locationId == 1):
        return "infragranular"
    elif(locationId == 2):
        return "granular"
    elif(locationId == 3):
        return "supragranular"
    else:
        raise RuntimeError("invalid laminar location ID " + str(locationId))


def getLaminarLocationId(location):
    if(location == "unknown"):
        return 0
    elif(location == "infragranular"):
        return 1
    elif(location == "granular"):
        return 2
    elif(location == "supragranular"):
        return 3
    elif(location == "L1"):
        return 4
    elif(location == "L2" or location == "L23"):
        return 5
    elif(location == "L3"):
        return 6
    elif(location == "L4"):
        return 7
    elif(location == "L5"):
        return 8
    elif(location == "L6"):
        return 9
    elif(location == "I"):
        return 4
    elif(location == "II"):
        return 5
    elif(location == "III"):
        return 6
    elif(location == "IV"):
        return 7
    elif(location == "V"):
        return 8
    elif(location == "VI"):
        return 9
    elif(location == "SUBCORTICAL"):
        return 10
    else:
        raise RuntimeError("invalid laminar location {}".format(location))


def getLayerName(idx):
    if(idx == 4):
        return "L1"
    elif(idx == 5):
        return "L23"
    elif(idx == 7):
        return "L4"
    elif(idx == 8):
        return "L5"
    elif(idx == 9):
        return "L6"
    elif(idx == 0 or idx == 3):
        return ""
    else:
        raise RuntimeError("invalid layer index {}".format(idx))


def convertGridNumericId(grid):
    ids = []
    for cube, props in grid.items():
        ids.append(props["id"])
    ids.sort()
    grid_numericId = collections.OrderedDict()
    for id in ids:
        grid_numericId[id] = {}
    for cube, props in grid.items():
        grid_numericId[props["id"]] = {
            "subvolume_center": cube,
            "laminar_location": props["laminar_location"],
            "region": props["region"],
            "cortical_depth": props["cortical_depth"]
        }
    return grid_numericId


def loadGridNumericId(file):
    return convertGridNumericId(loadGrid(file))


def loadGridLaminarLocations(filename):
    with open(filename) as f:
        lines = f.readlines()
        labels = lines[0].rstrip().split(",")
        grid = {}
        for i in range(1, len(lines)):
            line = lines[i].rstrip().split(",")
            grid[int(line[labels.index("id")])] = int(line[labels.index("laminar_location")])
        return grid


def updateCubeLayers(grid):
    layerNames = constants.getLaminarLocations()
    depths = constants.getLayerDepths()
    maxDepths = []
    for layer in layerNames:
        maxDepths.append(depths[layer][1])
    maxDepths = np.array(maxDepths)
    for _, props in grid.items():
        depth = props["cortical_depth"]
        if(depth < 0 or depth > maxDepths[-1]):
            props["layer_id"] = -1
        layerIdx = np.count_nonzero(maxDepths <= depth)
        props["layer_id"] = layerIdx


def extendProps(neurons, neuronIds, cell_types, pst_densities):
    for NID, props in neurons.items():
        if(NID in neuronIds):
            cellTypeId = props["cell_type"]
            cellTypeName = cell_types[cellTypeId]["name"]
            if(props["synaptic_side"] in [0, 2]):
                props["bouton_densities"] = {
                    "density_bouton_infragranular": cell_types[cellTypeId]["density_bouton_infragranular"],
                    "density_bouton_granular": cell_types[cellTypeId]["density_bouton_granular"],
                    "density_bouton_supragranular": cell_types[cellTypeId]["density_bouton_supragranular"]
                }
            if(props["synaptic_side"] in [1, 2]):
                props["pst_densities"] = pst_densities[cellTypeName]
            props["compute_main_bifurcation"] = cellTypeName == "L5PT"


def convertLayerInfraGranSupra(layerIdx):
    if(layerIdx == 0):
        return 0
    elif(layerIdx in [3, 4, 5, 6]):
        return 3  # supra
    elif(layerIdx in [2, 7]):
        return 2  # granular
    elif(layerIdx in [1, 8, 9]):
        return 1  # infra
    else:
        raise RuntimeError("Invalid layer index: {}".format(layerIdx))


def loadIds(filename):
    ids = []
    with open(filename) as f:
        lines = f.readlines()
        for line in lines:
            ids.append(int(line.rstrip()))
    return ids


def getGraphIdMap(neurons):
    graphIdMap = {}
    for NID, props in neurons.items():
        graphId = props["graph_id"]
        graphIdMap[graphId] = NID
    return graphIdMap


def loadAxonSomata(filename):
    somata = {}
    with open(filename) as f:
        lines = f.readlines()
        header = lines[0].rstrip().split(",")
        idx_id = header.index("id")
        idx_soma_x = header.index("soma_x")
        idx_soma_y = header.index("soma_y")
        idx_soma_z = header.index("soma_z")
        for i in range(1, len(lines)):
            parts = lines[i].rstrip().split(",")
            somaPos = np.array([float(parts[idx_soma_x]), float(parts[idx_soma_y]), float(parts[idx_soma_z])])
            somata[int(parts[idx_id])] = somaPos
        return somata


def loadNeuronsLayer(filename):
    layerNeuronIds = {
        "L1" : set(),
        "L2" : set(),
        "L3" : set(),
        "L4" : set(),
        "L5" : set(),
        "L6" : set(),
        "undefined" : set()
    }
    with open(filename) as f:
        lines = f.readlines()
        for i in range(1, len(lines)):
            parts = lines[i].rstrip().split(",")
            nid = int(parts[0])
            layer = int(parts[4])
            if(layer == 0):
                layerNeuronIds["undefined"].add(nid)
            elif(layer <= 6):
                layerNeuronIds["L{}".format(layer)].add(nid)
            else:
                raise ValueError(layer)
    return layerNeuronIds