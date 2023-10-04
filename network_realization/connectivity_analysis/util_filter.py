import util_meta
import os
import constants
from sortedcontainers import SortedDict


def getDefaultFilter(isSlice=False):
    defaultFilter = {
        "inside_vS1": [1],
        "layer_whitelist": [],
        "laminar_location_whitelist": [],
        "region_whitelist": [],
        "celltype_whitelist": [],
        "celltype_blacklist": [],
        "explicit_selection": [],
        "synaptic_side": [],
        "cortical_depth": []
    }

    if(isSlice):
        defaultFilter["tissue_depth"] = {
            "low": 31,
            "high": 130,
            "mode": "oneSided"
        }
    return defaultFilter

def getVPMFilter(column="C2"):
    return {
        "inside_vS1": [],
        "layer_whitelist": [],
        "laminar_location_whitelist": [],
        "region_whitelist": ["{}_Barreloid".format(column)],
        "celltype_whitelist": ["VPM"],
        "celltype_blacklist": [],
        "explicit_selection": [],
        "synaptic_side": [],
        "cortical_depth": []
    }

def getPostFilter():
    return {
        "inside_vS1": [],
        "layer_whitelist": [],
        "laminar_location_whitelist": [],
        "region_whitelist": [],
        "celltype_whitelist": [],
        "celltype_blacklist": [],
        "explicit_selection": [],
        "synaptic_side": [1,2],
        "cortical_depth": []
    }


def filter_vS1(neurons, inside_vS1):
    NIDs = set()
    for NID, props in neurons.items():
        if(props["inside_vS1"] in inside_vS1):
            NIDs.add(NID)
    return NIDs


def filterLayer(neurons, neuronsLayer, layers):
    if(neuronsLayer is None):
        ValueError(neuronsLayer)
    nidsAll = set(neurons.keys())

    nidsSelected = set()
    for layer in layers:
        nidsSelected |= neuronsLayer[layer]
    return nidsAll & nidsSelected


def filterLaminarLocation(neurons, laminarLocations):
    laminarLocationsInt = list(map(util_meta.getLaminarLocationId, laminarLocations))
    NIDs = set()
    for NID, props in neurons.items():
        if(props["laminar_location"] in laminarLocationsInt):
            NIDs.add(NID)
    return NIDs


def filterCellType(neurons, cellTypes):
    cellTypesDef = util_meta.loadCellTypes(os.path.join(os.environ["RBC_DATA_DIR"], "cell_types.csv"))
    NIDs = set()
    for cellType in cellTypes:
        cellTypeId = util_meta.getCellTypeId(cellTypesDef, cellType)
        for NID, props in neurons.items():
            if(props["cell_type"] == cellTypeId):
                NIDs.add(NID)
    return NIDs


def filterRegion(neurons, regions):
    regionsDef = util_meta.loadRegions(os.path.join(os.environ["RBC_DATA_DIR"], "regions.csv"))
    NIDs = set()
    for region in regions:
        regionId = util_meta.getRegionId(regionsDef, region)
        for NID, props in neurons.items():
            if(props["region"] == regionId):
                NIDs.add(NID)
    return NIDs


def filterRange_x(neurons, range_x):
    NIDs = set()
    for NID, props in neurons.items():
        soma_x = props["soma"][0]
        if(soma_x >= range_x[0] and soma_x <= range_x[1]):
            NIDs.add(NID)
    return NIDs


def filterTissueDepth(neurons, tissueDepth):
    NIDs = set()
    low = tissueDepth["low"]
    high = tissueDepth["high"]
    mode = tissueDepth["mode"]
    for NID, props in neurons.items():
        depth = props["tissue_depth"]
        if(depth >= low and depth <= high):
            NIDs.add(NID)
        if(mode == "twoSided"):
            depth = props["tissue_depth_inverted"]
            if(depth >= low and depth <= high):
                NIDs.add(NID)
    return NIDs


def filterSynapticSide(neurons, synapticSide):
    NIDs = set()
    for NID, props in neurons.items():
        side = props["synaptic_side"]
        if(side in synapticSide):
            NIDs.add(NID)
    return NIDs


def filterExplicitSelection(neurons, explicitSelection):
    NIDs = set(explicitSelection)
    return NIDs


def filterCorticalDepth(neurons, depthRange):
    NIDs = set()
    for NID, props in neurons.items():
        depth = props["cortical_depth"]
        if(depth >= depthRange[0] and depth <= depthRange[1]):
            NIDs.add(NID)
    return NIDs


def filterNeurons(neurons, filterSpec, verbose=False, invert=False, idsOnly = False, neuronsLayer=None):
    neuronsFiltered = SortedDict()
    NIDs_all = set(neurons.keys())
    NIDs_out = set()

    NIDs_VPM = filterCellType(neurons, ["VPM"])

    if(verbose):
        print("filter:")
        print(filterSpec)
        print("before filtering: ", len(NIDs_all))
    for filterName in filterSpec.keys():
        if(filterName == "inside_vS1" and len(filterSpec["inside_vS1"])):
            NIDs_out |= NIDs_all - filter_vS1(neurons, filterSpec["inside_vS1"])
        if(filterName == "layer_whitelist" and len(filterSpec["layer_whitelist"])):
            NIDs_out |= NIDs_all - (filterLayer(neurons, neuronsLayer, filterSpec["layer_whitelist"]) | NIDs_VPM)
        if(filterName == "laminar_location_whitelist" and len(filterSpec["laminar_location_whitelist"])):
            NIDs_out |= NIDs_all - (filterLaminarLocation(neurons, filterSpec["laminar_location_whitelist"]) | NIDs_VPM)
        if(filterName == "region_whitelist" and len(filterSpec["region_whitelist"])):
            NIDs_out |= NIDs_all - filterRegion(neurons, filterSpec["region_whitelist"])
        if(filterName == "celltype_whitelist" and len(filterSpec["celltype_whitelist"])):
            NIDs_out |= NIDs_all - filterCellType(neurons, filterSpec["celltype_whitelist"])
        if(filterName == "celltype_blacklist" and len(filterSpec["celltype_blacklist"])):
            NIDs_out |= filterCellType(neurons, filterSpec["celltype_blacklist"])
        if(filterName == "range_x"):
            NIDs_out |= NIDs_all - filterRange_x(neurons, filterSpec["range_x"])
        if(filterName == "tissue_depth"):
            NIDs_out |= NIDs_all - filterTissueDepth(neurons, filterSpec["tissue_depth"])
        if(filterName == "synaptic_side" and len(filterSpec["synaptic_side"])):
            NIDs_out |= NIDs_all - filterSynapticSide(neurons, filterSpec["synaptic_side"])
        if(filterName == "explicit_selection" and len(filterSpec["explicit_selection"])):
            NIDs_out |= NIDs_all - filterExplicitSelection(neurons, filterSpec["explicit_selection"])
        if(filterName == "cortical_depth" and len(filterSpec["cortical_depth"])):
            NIDs_out |= NIDs_all - (filterCorticalDepth(neurons, filterSpec["cortical_depth"]) | NIDs_VPM)

        if(verbose):
            print(filterName, "pruned {} of {}. Remaining: {}".format(len(NIDs_out), len(NIDs_all), len(NIDs_all)-len(NIDs_out)))
    if(invert):
        NIDs_filtered = NIDs_out
    else:
        NIDs_filtered = NIDs_all - NIDs_out
    
    if(idsOnly):
        return NIDs_filtered

    for NID in NIDs_filtered:
        neuronsFiltered[NID] = neurons[NID]
    return neuronsFiltered


def filterNIDs(neurons, filterSpec, neuronsLayer=None):
    neuronsFiltered = filterNeurons(neurons, filterSpec, neuronsLayer=neuronsLayer)
    return set(neuronsFiltered.keys())


def filterNIDsTwoRounds(neurons, firstFilter, secondFilter, neuronsLayer = None):
    neuronsFiltered1 = filterNeurons(neurons, firstFilter, neuronsLayer=neuronsLayer)
    neuronsFiltered2 = filterNeurons(neuronsFiltered1, secondFilter, neuronsLayer=neuronsLayer)
    return set(neuronsFiltered2.keys())


def getSortedNIDs(filteredNeurons):
    ids = list(filteredNeurons.keys())
    ids.sort()
    return ids

