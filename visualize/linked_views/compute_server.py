"""
Simulation server that computes membrane potential over time on dendrite surface
for given model parameters (case study 2). This serves as an example for a compute 
server.

Code dependencies to the core simulation framework (authored by Arco Bast et al., Max Planck 
Institute for Neurobiology of Behavior, Bonn) have been commented out in this file. The 
core simulation framework is not publicly available at this point and requires extensive
configurations and supervision to set up locally.

We therefore supply precomputed simulation data for testing the membrane potential views 
of the visual analysis tool. Please refer to README.md for a download link of the data. 

Usage:
python compute_server.py <simulation_data_precomputed>
"""

import sys
import os
#import Interface as I
import json
import pandas as pd
#import numpy as np
#import visualize
from pathlib import Path

#from project_specific_ipynb_code.biophysical_models import CurrentAnalysis
#from project_specific_ipynb_code.biophysical_models import modify_simulator_to_record_apical_dendrite_conductances

import flask
from flask import request
from flask_cors import cross_origin

app = flask.Flask(__name__)

T_START = 275
T_END = 375
T_STIM = 295
T_POSTSTIM = 55


"""
def getParamsCols():
    params_py2 = ['ephys.CaDynamics_E2.apic.decay',
                  'ephys.CaDynamics_E2.apic.gamma', 'ephys.CaDynamics_E2.axon.decay',
                  'ephys.CaDynamics_E2.axon.gamma', 'ephys.CaDynamics_E2.soma.decay',
                  'ephys.CaDynamics_E2.soma.gamma', 'ephys.Ca_HVA.apic.gCa_HVAbar',
                  'ephys.Ca_HVA.axon.gCa_HVAbar', 'ephys.Ca_HVA.soma.gCa_HVAbar',
                  'ephys.Ca_LVAst.apic.gCa_LVAstbar', 'ephys.Ca_LVAst.axon.gCa_LVAstbar',
                  'ephys.Ca_LVAst.soma.gCa_LVAstbar', 'ephys.Im.apic.gImbar',
                  'ephys.K_Pst.axon.gK_Pstbar', 'ephys.K_Pst.soma.gK_Pstbar',
                  'ephys.K_Tst.axon.gK_Tstbar', 'ephys.K_Tst.soma.gK_Tstbar',
                  'ephys.NaTa_t.apic.gNaTa_tbar', 'ephys.NaTa_t.axon.gNaTa_tbar',
                  'ephys.NaTa_t.soma.gNaTa_tbar', 'ephys.Nap_Et2.axon.gNap_Et2bar',
                  'ephys.Nap_Et2.soma.gNap_Et2bar', 'ephys.SK_E2.apic.gSK_E2bar',
                  'ephys.SK_E2.axon.gSK_E2bar', 'ephys.SK_E2.soma.gSK_E2bar',
                  'ephys.SKv3_1.apic.gSKv3_1bar', 'ephys.SKv3_1.apic.offset',
                  'ephys.SKv3_1.apic.slope', 'ephys.SKv3_1.axon.gSKv3_1bar',
                  'ephys.SKv3_1.soma.gSKv3_1bar', 'ephys.none.apic.g_pas',
                  'ephys.none.axon.g_pas', 'ephys.none.dend.g_pas',
                  'ephys.none.soma.g_pas', 'scale_apical.scale']

    params_py3 = [p.replace('ephys.CaDynamics_E2', 'ephys.CaDynamics_E2_v2') for p in params_py2]
    return params_py3


def retrieve_currents(self, ax = None, normalized = False, t_stim = 295, select_window_relative_to_stim = (0,55)):
    t = I.np.array(self.t) - t_stim
    #if ax is None:
    #    fig = I.plt.figure(figsize = (10,4), dpi = 200)
    #    ax = fig.add_subplot(111)

    def __helper(currents, plot_label = True):            
        selectedTimesteps = (t>=select_window_relative_to_stim[0]) & (t<=select_window_relative_to_stim[1]) 
        currentResult = {}
        dummy = I.np.cumsum(currents, axis = 0)
        dummy = I.np.vstack([I.np.zeros(dummy.shape[1]), dummy])    
        for lv, rv in enumerate(self.rangeVars):
            x,y1,y2 = t,dummy[lv,:],dummy[lv+1,:]
            #select = (x>=select_window_relative_to_stim[0]) & (x<=select_window_relative_to_stim[1]) 
            x,y1,y2 = x[selectedTimesteps],y1[selectedTimesteps],y2[selectedTimesteps]
            currentResult[rv + "_y1"] = y1.tolist()
            currentResult[rv + "_y2"] = y2.tolist()
            #ax.fill_between(x,-y1,-y2, 
            #                label = rv if plot_label else None,
            #                color = self.colormap[rv],
            #                linewidth = 0)
            print(y1.size)
        return currentResult
    
    depolarizingCurrents = __helper(self.depolarizing_currents)
    hyperpolarizingCurrents  =__helper(self.hyperpolarizing_currents, False)
    return {
        "depolarizing" : depolarizingCurrents, 
        "hyperpolarizing" : hyperpolarizingCurrents
    }
         

def find_nearest(array, value):
    'https://stackoverflow.com/questions/2566412/find-nearest-value-in-numpy-array'
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx 


def get_lines(cell, n, range_vars = 'Vm'):
    '''returns list of dictionaries of lines that can be displayed using the plot_lines function'''
    difference_limit = 1
    if isinstance(range_vars, str):
        range_vars = [range_vars]
         
    cmap = {'Soma': 'k', 'Dendrite': 'b', 'ApicalDendrite': 'r', 'AIS': 'g', 'Myelin': 'y', 'SpineNeck': 'cyan', 'SpineHead': 'orange'}
    out_all_lines = []
    points_lines = {} # contains data to be plotted as points
    for currentSec in cell.sections:
        if currentSec.label == "Soma": #don't plot soma
            continue 
        
        out = {}
        currentSec_backup = currentSec
        
        
        parentSec = currentSec.parent
         
        #compute distance from current section to soma
        dist = 0.0
        parentLabel = parentSec.label
 
        while parentLabel != 'Soma':
            dist += parentSec.L * currentSec.parentx
            currentSec = parentSec 
            parentSec = currentSec.parent
            parentLabel = parentSec.label
         
        parent_idx_segment = find_nearest(currentSec_backup.parent.segx, currentSec_backup.parentx)
                 
        #now calculate it segment wise.
        #First point is branchpoint of parent section, because otherwise there will be a gap in the plot
        distance_dummy = [dist] #  + currentSec_backup.parent.relPts[parent_idx]*currentSec_backup.parent.L]
        #calculate each segment distance
        for seg in currentSec_backup:
            distance_dummy.append(dist + seg.x*currentSec_backup.L)
        
        # voltage traces are a special case
        if range_vars[0] == 'Vm':
            traces_dummy = [currentSec_backup.parent.recVList[parent_idx_segment][n]]
            for vec in currentSec_backup.recVList:
                traces_dummy.append(vec[n])       
        # other range vars are saved differently in the cell object compared to Vm       
        else:
            vec_list = [] # currentSec_backup.recordVars[range_vars[0]]
            try:
                traces_dummy = [currentSec_backup.parent.recordVars[range_vars[0]][parent_idx_segment][n]]
            except:
                [np.NaN]
            if not vec_list: continue #if range mechanism is not in section: continue
            for vec in vec_list:
                traces_dummy.append(vec[n])
                #sec.recordVars[range_vars[0]][lv_for_record_vars]
                  
        out['x'] = distance_dummy
        out['y'] = traces_dummy
        out['color'] = cmap[currentSec_backup.label]
        out['label'] = currentSec_backup.label
        out['t'] = cell.tVec[n]
        out_all_lines.append(out)
    out_all_lines.extend(list(points_lines.values()))
    return out_all_lines

def downsample_spatial_resolution(morphology, voltage_timeseries):
    lines = morphology["lines"]

    def get_middle_element(lst):
        middle_index = len(lst) // 2
        return lst[middle_index]

    lineIdx_pointIdx = {}
    for lineIdx, lineData in enumerate(lines):
        lineIdx_pointIdx[lineIdx] = get_middle_element(lineData[1:])


    voltage_timeseries_downsampled = []
    for voltages in voltage_timeseries:
        voltages_for_lines = []
        for lineIdx in range(0, len(lines)):
            voltages_for_lines.append(voltages[lineIdx_pointIdx[lineIdx]])
        voltage_timeseries_downsampled.append(voltages_for_lines)

    return voltage_timeseries_downsampled


def run_simulation(db, parameters, morphologyName, morphologyCache, tstart=T_START, tend=T_END, tstim=T_STIM, tpostStim = T_POSTSTIM, tstep=1):
        
    if(parameters is None):
        df = db['examplary_models']
        params_py3 = getParamsCols()
        model_idx = 0
        parameters = df.iloc[model_idx][params_py3]
        
    def get_simulator(id_, py2 = False):
        s = db[id_]['get_Simulator'](db[id_])
        return s

    s = get_simulator(morphologyName)
    s.setup.stim_run_funs = [s.setup.stim_run_funs[1]] 
    s.setup.stim_setup_funs = [s.setup.stim_setup_funs[1]]
    s.setup.stim_response_measure_funs = [s.setup.stim_response_measure_funs[1]] 

    # voltage_traces = s.run(parameters)
    # tVec = voltage_traces['BAC.hay_measure']["tVec"]
    # vList = voltage_traces['BAC.hay_measure']["vList"]

    #s = modify_simulator_to_record_apical_dendrite_conductances(s)
        
    cell, _ = s.get_simulated_cell(parameters, 'BAC')
    cmv = visualize.CellMorphologyVisualizer(cell)

    cmv.write_vtk_frames(out_dir="./vtk_tmp", t_start=tstart, t_end=tend, t_step=tstep, scalar_data="vm")
    return downsample_spatial_resolution(morphologyCache[morphologyName], cmv.voltage_timeseries)

def computeMorphology(db, morphology, tmpFolder, tstart=245, tend=310, tstep=1):
    df = db['examplary_models']
    params_py3 = getParamsCols()
    model_idx = 10
    parameters = df.iloc[model_idx][params_py3]

    def get_simulator(id_, py2 = False):
        s = db[id_]['get_Simulator'](db[id_])
        return s

    s = get_simulator(morphology)
    cell, _ = s.get_simulated_cell(parameters, 'BAC')
    cmv = visualize.CellMorphologyVisualizer(cell)
    cmv.write_vtk_frames(out_dir=tmpFolder, t_start=tstart, t_end=tend, t_step=tstep)

    return loadMorphology(Path(tmpFolder)/"frame_000000.vtk")


@app.route("/matrixComputeServer/getMorphology", methods=["GET", "POST"])
@cross_origin()
def getMorphology():    
    global morphologies

    if request.method == "POST":
        if request.data:
            data = request.get_json(force=True)

            morphologyName = data["morphologyName"]
            response_data = {
                "morphology" : morphologies[morphologyName]                
            }
            
            return json.dumps(response_data)

def loadMorphology(filename):
    currentJsonField = ""
    jsonData = {
        "points": [],
        "lines": [],
        "diameters": []
    }

    def isDataDescriptor(line, currentField):
        if("#" in line):
            return True, ""
        if("frame" in line):
            return True, ""
        if("ASCII" in line):
            return True, ""
        if("DATASET POLYDATA" in line):
            return True, ""
        if("POINTS" in line):
            return True, "points"
        if("LINES" in line):
            return True, "lines"
        if("FIELD" in line):
            return True, ""
        if("LOOKUP_TABLE" in line):
            return True, "diameters"
        return False, currentField

    with open(filename) as f:
        lines = f.readlines()
        for line in lines:
            lineCleaned = line.rstrip()
            isMeta, currentJsonField = isDataDescriptor(line, currentJsonField)
            if(not isMeta):
                if(currentJsonField == "points"):
                    xyz = lineCleaned.split(" ")
                    jsonData["points"].append(list(map(float, xyz)))
                elif (currentJsonField == "lines"):
                    indices = lineCleaned.split(" ")
                    jsonData["lines"].append(list(map(int, indices)))
                elif (currentJsonField == "diameters"):
                    jsonData["diameters"].append(float(lineCleaned))

    return jsonData
"""


def write_traces_to_cache(filename, voltage_timeseries):
    with open(filename, "w") as f:
        for voltages in voltage_timeseries:
            line = ",".join(["{:.1f}".format(value) for value in voltages])
            f.write(line + "\n")


def load_traces_from_cache(filename):
    if(not os.path.exists(filename)):
        return None

    df = pd.read_csv(filename, index_col=False)
    return df.values.tolist()


@app.route("/computeServer/getSimulation", methods=["GET", "POST"])
@cross_origin()
def getSimulation():
    #global db
    #global morphologies
    global cacheFolder

    if request.method == "POST":
        if request.data:
            data = request.get_json(force=True)

            parameters = data["parameters"]
            originalIdx = parameters["sample_idx_original"]
            #parameterValuesTmp = {}
            #for parameterName in getParamsCols():
            #    parameterValuesTmp[parameterName] = [parameters[parameterName]]
            #df = pd.DataFrame(parameterValuesTmp)
            #parameterValues = df.iloc[0][getParamsCols()]

            filename_cache = cacheFolder/"voltage_traces_{}".format(originalIdx)
            voltage_timeseries = load_traces_from_cache(filename_cache)
            if(voltage_timeseries is None):
                #voltage_timeseries = run_simulation(db, parameterValues, 'WR64', morphologies)
                #write_traces_to_cache(filename_cache, voltage_timeseries)
                raise RuntimeError(f"Precomputed simulation data not available for sample idx {originalIdx}.")
            else:
                print("use cached ", originalIdx)

            result = {
                "tstart": T_START,
                "tend": T_END,
                "tstim": T_STIM,
                "tpoststim": T_POSTSTIM,
                "voltage_traces": voltage_timeseries
            }

            response_data = {
                "sample_idx_original": originalIdx,
                "voltage_timeseries_points": result
            }

            return json.dumps(response_data)


def printUsageAndExit():
    print("Usage:")
    print("python ")
    exit()


if __name__ == "__main__":
    if(len(sys.argv) != 2):
        printUsageAndExit()

    cacheFolder = sys.argv[1]
    assert os.path.exists(cacheFolder)
    cacheFolder = Path(cacheFolder)

    #db = I.DataBase('/scratch/visual/bzfharth/model_database')

    #tmpFolder = "vtk_tmp/morphologies"
    #cacheFolder = Path("simulation_data_cache")
    #os.makedirs(tmpFolder, exist_ok=True)
    #os.makedirs(cacheFolder, exist_ok=True)

    # morphologies = {}  # name -> json
    #morphologyName = 'WR64'
    #morphologies[morphologyName] = computeMorphology(db, morphologyName, tmpFolder)

    #run_simulation(db, None, morphologyName, morphologies)

    app.run(host="localhost", port=5001)
