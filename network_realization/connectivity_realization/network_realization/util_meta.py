import os
from sortedcontainers import SortedDict
import numpy as np
import collections


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


def loadPstDensities(filename=None):
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


def loadGrid(filename=None):
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
    if(location == "infragranular"):
        return 1
    elif(location == "granular"):
        return 2
    elif(location == "supragranular"):
        return 3
    elif(location == "L1"):
        return 4
    elif(location == "L2"):
        return 5
    elif(location == "L3"):
        return 6
    elif(location == "L4"):
        return 7
    elif(location == "L5"):
        return 8
    elif(location == "L6"):
        return 9
    else:
        raise RuntimeError("invalid laminar location " + location)


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
        }
    return grid_numericId


def extendProps(neurons, cell_types, pst_densities):
    for props in neurons.values():
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


def convertLayerInfraGranSupra(layerIdx):
    if(layerIdx == 0):
        return 0
    elif(layerIdx in [3, 4, 5, 6]):
        return 3
    elif(layerIdx in [2, 7]):
        return 2
    elif(layerIdx in [1, 8, 9]):
        return 1
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
