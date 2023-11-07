import os
import sys
import time
import logging
from logging import handlers
import tempfile
import threading
import util
import glob
import json
import pandas as pd
import numpy as np
import vaex
import vaex.ml

from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

from werkzeug.serving import make_server

INVALID_NUMBER = -999999

def load_tables(data_folder, config, max_num_rows = 50000):    
    csvFiles = glob.glob(os.path.join(data_folder,"*.csv"))
    tables = {}
    
    for filepath in csvFiles:   
        basename = os.path.basename(filepath) 

        print("start read: {}".format(basename))
        df = pd.read_csv(filepath, nrows=max_num_rows)    
        print("complete read")

        samplingSettings = config["sampling_settings"]
        if(basename in samplingSettings):
            settings = samplingSettings[basename]
            seed = settings["seed"]
            sampleSize = settings["number"]
            randomState = np.random.RandomState(seed)
            df = df.sample(sampleSize, random_state=randomState)

        columns_data = df.to_dict(orient="records")
        tables[basename] = {}
        tables[basename]["flat"] = df
        tables[basename]["records"] = columns_data

    return tables


def load_table_from_df(df):
    tables = {}
    basename = "pandas_df"
    tables[basename] = {}
    tables[basename]["flat"] = df
    columns_data = df.to_dict(orient="records")
    tables[basename]["records"] = columns_data
    return tables


def write_objects_to_file(filenameProjects, objects):    
    if(filenameProjects is None):
        return
    with open(filenameProjects, 'w') as file:
        json.dump(objects, file)

def get_data_ranges(df):
    ranges = {}
    ranges["min"] = df.min().to_list()
    ranges["max"] = df.max().to_list()
    return ranges 

def get_data_ranges_vaex(df):
    col_names = df.get_column_names()
    ranges = {}
    ranges["min"] = df.min(col_names).tolist()
    ranges["max"] = df.max(col_names).tolist()
    return ranges 

def normalize(df, low=-1, high=1):
    scaler = MinMaxScaler(feature_range=(low, high))
    df_normalized = pd.DataFrame(scaler.fit_transform(df), columns=df.columns)
    return df_normalized

def getPCA(df):    
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(df)
    
    pca = PCA(2)
    pca.fit(scaled_data)
    principal_components = pca.transform(scaled_data)

    min_max_scaler = MinMaxScaler(feature_range=(-1, 1))
    normalized_components = min_max_scaler.fit_transform(principal_components)

    return normalized_components.tolist()

    
class LinkedViewsServer:
    def __init__(self, config_file_path = None, data_folder=None):
        if(config_file_path is not None):
            self.config_file_path = config_file_path
        else:
            self.config_file_path = Path(os.path.dirname(__file__))/"defaults"/"config.json"        

        self.data_folder = None 
        if(data_folder):
            self.data_folder = Path(data_folder)
            self.resourceDir = self.data_folder/"resources"
            self.config_file_path = self.data_folder/"config.json"
        else:
            self.resourceDir = None
        self.filenameProjects = None

        self.thread = None    
        self.vaex_df = None
        self.selections = {}
        self.active_selection = None

        print(self.config_file_path)
        self.config = util.loadJson(self.config_file_path)

        if(self.data_folder):
            self.tables = load_tables(self.data_folder, self.config)
            self.filenameProjects = self.data_folder/"projects.json"
            # Load objects from the file on server startup
            try:
                with open(self.filenameProjects, 'r') as file:
                    self.objects = json.load(file)
            except FileNotFoundError:
                self.objects = []
        else:
            self.tables = {}
            self.objects = []


    def start(self, port=5000):                        
        if(self.thread is not None):
            print("server is running at port {}".format(self.port))
            return        
        try:
            self.app = Flask(__name__)       
            CORS(self.app)     
            self.server = make_server('0.0.0.0', port, self.app)                        
            self.port = port
            self.init_routes()
        except SystemExit as e:
            self.server = None
            return

        def _start():
            self.server.serve_forever()

        self.thread = threading.Thread(target=_start)      
        self.thread.start()
        print("server is running at port {}".format(self.port))
        self.start_logging()
        print("set data:        server.set_data(df)")        
        print("stop server:     server.stop()")
        

    def stop(self):
        if(self.thread is None):
            print("server is not running")
            return

        print("Stopping server. If operation does not terminate, try to repeatedly reopen http://127.0.0.1:{} in the browser.".format(self.port))
        self.stop_logging()
        self.server.shutdown()                
        self.thread.join()
        self.thread = None
        print("Server stopped.")

    def start_logging(self):
        tmp_folder = Path(tempfile.gettempdir())
        log_filename = tmp_folder/"linked-views-server.log"
        print("logs are written to {}".format(log_filename))
        self.logfile_handler = logging.handlers.RotatingFileHandler(
            filename=log_filename,
            mode='w',
            maxBytes=1048576
        )
        self.logfile_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s", "%Y-%m-%d %H:%M:%S")
        self.logfile_handler.setFormatter(formatter)
        logging.getLogger().addHandler(self.logfile_handler)

    def stop_logging(self):
        logging.getLogger().removeHandler(self.logfile_handler)

    def set_data(self, df):
        assert self.server is not None

        if(isinstance(df, pd.DataFrame)):
            self.tables = load_table_from_df(df)
            self.config["cached_tables"] = ["pandas_df"]
        elif(isinstance(df, vaex.DataFrame)):
            self.vaex_df = df        
            self.vaex_columns = df.get_column_names()         
            self.vaex_df["row_index"] = np.arange(self.vaex_df.shape[0])
            self.vaex_data_ranges = get_data_ranges_vaex(df)
        else:
            raise TypeError(df)

        
    

    def init_routes(self):
        self.app.add_url_rule('/', 'index', self.index)
        self.app.add_url_rule('/getSelections', 'getSelections', self.getSelections)
        self.app.add_url_rule('/getSelectedIndices', 'getSelectedIndices', self.getSelectedIndices)
        self.app.add_url_rule('/dataServer/', 'get_objects', self.get_objects, methods=['GET'])
        self.app.add_url_rule('/dataServer/<name>', 'delete_object', self.delete_object, methods=['DELETE'])
        self.app.add_url_rule('/dataServer/', 'add_object', self.add_object, methods=['POST'])
        self.app.add_url_rule('/dataServer/getMetaData', 'getMetaData', self.getMetaData, methods=["GET", "POST"])
        self.app.add_url_rule('/dataServer/getResourceJSON', 'getResourceJSON', self.getResourceJSON, methods=["GET", "POST"])
        self.app.add_url_rule("/dataServer/getValues", "getValues", self.getValues, methods=["GET", "POST"])
        self.app.add_url_rule("/dataServer/getDensity", "getDensity", self.getDensity, methods=["POST"])
        self.app.add_url_rule("/dataServer/setDensityPlotSelection", "setDensityPlotSelection", self.setDensityPlotSelection, methods=["POST"])
        self.app.add_url_rule("/dataServer/setIndicesSelection", "setIndicesSelection", self.setIndicesSelection, methods=["POST"])

    def index(self):
        if(self.vaex_df):
            return "vaex df columns: {}".format([name for name in list(self.vaex_df.columns)])
        else:
            return "Tables: {}".format([name for name in self.tables.keys()])



    """
    ########################################################################################
                                    session storage
    ########################################################################################
    """

    def get_objects(self):
        return jsonify(self.objects)

    def delete_object(self, name):        
        self.objects = [obj for obj in self.objects if obj['name'] != name]
        write_objects_to_file(self.filenameProjects, self.objects)    
        return jsonify({'message': 'Object deleted'})
    
    def add_object(self):

        def delete_object_by_property(json_list, property_name, property_value):
            filtered_list = [obj for obj in json_list if obj.get(property_name) != property_value]
            return filtered_list
        
        new_object = request.get_json()

        self.objects = delete_object_by_property(self.objects, "name", new_object["name"])
        self.objects.append(new_object)
        write_objects_to_file(self.filenameProjects, self.objects)
        return jsonify(new_object)


    def add_session(self, sessionData, name=None):
        if(name is None):
            name = "session-{}".format(len(self.objects)+1)
        sessionData["name"] = name
        self.objects.append(sessionData)
        return name 

    def remove_session(self, name):
        self.delete_object(name)


    def get_session(self, name):
        for session in self.objects:
            if(session["name"] == name):
                return session
        return None


    """
    ########################################################################################
                                    end of session storage
    ########################################################################################
    """


    #@app.route("/matrixServer/getMetaData", methods=["GET", "POST"])
    #@cross_origin()
    def getMetaData(self):        
        if request.method == "POST":
            if request.data:
                data = request.get_json(force=True)
                
                meta_data = []            
                for tableName, tableData in self.tables.items():
                    df = tableData["flat"]            
                    meta_data.append({
                        "name" : tableName,
                        "num_rows" : df.shape[0],
                        "columns" : df.columns.to_list(),
                        "data_ranges" : get_data_ranges(df)                
                    })

                if(self.vaex_df is not None):                       
                    meta_data.append({
                        "name" : "vaex_df",
                        "num_rows" : self.vaex_df.shape[0],
                        "columns" : self.vaex_columns,
                        "data_ranges" : self.vaex_data_ranges#'get_data_ranges_vaex(self.vaex_df)                
                    })


                response_data = {
                    "meta_data" : meta_data,
                    "available_views" : self.config["available_views"],
                    "table_mapping" : self.config["table_mapping"],
                    "cached_tables" : self.config["cached_tables"]
                }
                return json.dumps(response_data)


    #@app.route("/matrixServer/getResourceJSON", methods=["GET", "POST"])
    #@cross_origin()
    def getResourceJSON(self):        
        if request.method == "POST":
            if request.data:
                data = request.get_json(force=True)

                resourceName = data["filename"]
                filename = self.resourceDir/resourceName
                print(filename)

                if(not os.path.exists(filename)):
                    raise ValueError(filename)
                else:
                    jsonData = util.loadJson(filename)

                    response_data = {
                        "filename" : resourceName,
                        "jsonData" : jsonData
                    }

                    return json.dumps(response_data)



    #@app.route("/matrixServer/getValues", methods=["GET", "POST"])
    #@cross_origin()
    def getValues(self):
        
        if request.method == "POST":
            if request.data:
                data = request.get_json(force=True)

                tableName = data["table"]
                df = self.tables[tableName]["flat"]

                columns = data["columns"]
                indices = data["indices"]
                format = data["format"]
                #print(columns)
                #print(set(columns) - set(df.columns))
                assert set(columns).issubset(set(df.columns))
                assert len(indices) == 0 or max(indices) < df.shape[0]            

                if(len(indices) == 0):
                    filtered_df = df[columns]
                else:
                    filtered_df = df.iloc[indices][columns]

                if(format == "expanded"):
                    values = filtered_df.to_dict(orient="records")
                elif(format == "flat"):
                    values = filtered_df.values.tolist()
                elif(format == "flat-normalized"):
                    values = normalize(filtered_df).values.tolist()
                elif(format == "flat-normalized-PCA"):
                    values = getPCA(filtered_df) 
                else:
                    raise ValueError(format)

                response_data = {
                    "columns" : columns,
                    "indices" : indices,
                    "values" : values,
                    "data_ranges" : get_data_ranges(filtered_df)
                }

                return json.dumps(response_data)
    

    def getDensity(self): 
        self.last_request = request.data
        if request.method == "POST":            
            if request.data:
                data = request.get_json(force=True)

                tableName = data["table"]
                if(tableName not in ["vaex_df"]):
                    raise ValueError(tableName)

                df = self.vaex_df
              
                columns = data["columns"]                
                #indices = data["indices"]
                format = data["format"]
                if(format in ["count"]):
                    assert len(columns) == 2
                elif(format in ["min", "max", "mean", "median"]):
                    assert len(columns) == 3
                    value_column = columns[2]
                else:
                    raise ValueError(format)

                binbycols = columns[0:2]
                density_grid_shape = tuple(data["density_grid_shape"])
                nCells = density_grid_shape[0] * density_grid_shape[1]
                #indices = np.arange(nCells)
                                                
                minmax_x = df.minmax(binbycols[0])
                minmax_y = df.minmax(binbycols[1])
                data_ranges = [minmax_x.tolist(), minmax_y.tolist()]
                
                if(format == "count"):
                    values = df.count(binby=binbycols, shape=density_grid_shape, selection=self.active_selection, limits=data_ranges).astype(float)
                    values[values == 0] = np.nan
                elif(format == "min"):                    
                    values = df.min(value_column, binby=binbycols, shape=density_grid_shape, selection=self.active_selection, limits=data_ranges)
                    values[values > 10**100] = np.nan
                elif(format == "max"):                    
                    values = df.max(value_column, binby=binbycols, shape=density_grid_shape, selection=self.active_selection, limits=data_ranges)
                    values[values < -10**100] = np.nan
                elif(format == "mean"):                    
                    values = df.mean(value_column, binby=binbycols, shape=density_grid_shape, selection=self.active_selection, limits=data_ranges)
                elif(format == "median"):
                    values = df.median_approx(value_column, binby=binbycols, shape=density_grid_shape, selection=self.active_selection, limits=data_ranges)
                else:
                    raise ValueError(format)             

                values = np.nan_to_num(values, nan=INVALID_NUMBER)
                
                response_data = {
                    "columns" : columns,
                    #"indices" : indices.tolist(),
                    "values" : values.tolist(),
                    "density_grid_shape" : data["density_grid_shape"],
                    "data_ranges" : data_ranges,
                    "masked_value" : INVALID_NUMBER
                }

                return json.dumps(response_data)


    def setDensityPlotSelection(self): 
        self.last_request = request.data
        if request.method == "POST":            
            if request.data:
                data = request.get_json(force=True)
                
                table = data["table"]
                columns = data["columns"]
                bin_ranges = data["bin_ranges"]
                selection_name = data["selection_name"]
                
                assert table == "vaex_df"
                for column in columns:
                    assert column in self.vaex_columns

                self.selections[selection_name] = {
                    "columns" : columns,
                    "bin_ranges" : bin_ranges
                }

                response_data = {}
                return json.dumps(response_data)


    def setIndicesSelection(self): 
        self.last_request = request.data
        if request.method == "POST":            
            if request.data:
                data = request.get_json(force=True)
                
                table = data["table"]
                view_name = data["view_name"]                
                indices = data["indices"]
                
                assert table == "pandas_df"
                
                self.selections[view_name] = sorted(indices)

                response_data = {}
                return json.dumps(response_data)


    def computeSelection(self, return_indices=True):
        if("global" in self.selections):
            columns = self.selections["global"]["columns"] 
            col1 = columns[0]
            col2 = columns[1]

            ranges = self.selections["global"]["bin_ranges"]

            self.vaex_df.select_nothing(name="selection_global")
            for idx, range_i in enumerate(ranges):    
                limit_i = [(range_i[0][0], range_i[0][1]), (range_i[1][0], range_i[1][1])]        
                self.vaex_df.select_rectangle(self.vaex_df[col1], self.vaex_df[col2], limit_i, name="selection_global", mode="or")
            self.active_selection = "selection_global"

            if(return_indices):
                df_selected_indices = self.vaex_df.evaluate(self.vaex_df["row_index"], selection="selection_global")
                return df_selected_indices
            else:
                return "selection_global"
        else:
            self.active_selection = None
            return None            

    def resetSelection(self):
        self.active_selection = None


    def getSelections(self):
        return self.selections

    def getSelectionFromView(self, view_name):
        if(view_name not in self.selections):
            return []
        else:
            return self.selections[view_name]



    def getSelectedIndices(self):
        df_selected_indices = self.computeSelection()
        if(df_selected_indices is None):
            return "no selection"
        else:
            return "number of selected rows: {}".format(df_selected_indices.shape[0])



def printUsageAndExit():
    print("Usage:")
    print("python server.py <data-folder> [<port>]")
    exit()


if __name__ == "__main__":
    if(len(sys.argv) not in [2,3]):
        printUsageAndExit()

    dataDir = Path(sys.argv[1])

    port = 5000
    if(len(sys.argv) == 3):
        port = int(sys.argv[2])
    
    server = LinkedViewsServer(data_folder=dataDir)
    server.start(port)
        
    time.sleep(3600) # keep running for 1h
