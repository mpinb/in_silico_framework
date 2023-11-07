import { deepCopy, getColumnMinMaxValues } from './utilCore.js';

import { getServerURL } from './serverControl.js';
import axios from 'axios';

import { Observable } from 'babylonjs';


const headers = {
    'Content-Type': 'application/json'
};

function normalizeDensityValues(values, invalidValue = -999999) {
    const coords_value = [];
    const valid_values = [];
    for (let i = 0; i < values.length; i++) {
        for (let j = 0; j < values[i].length; j++) {
            const value = values[i][j];
            if (value !== invalidValue) {
                valid_values.push(value);
                coords_value.push([i, j, value])
            }
        }
    }

    let min_value = undefined;
    let max_value = undefined;

    if (valid_values.length) {
        min_value = Math.min(...valid_values);
        max_value = Math.max(...valid_values);
    }

    return {
        coords_value,
        min_value,
        max_value
    }
}

export class DataManager {
    constructor(viewManager) {
        this.viewManager = viewManager;

        this.OnDataChanged = new Observable();
        this.OnMatrixSelectionChanged = new Observable();
        this.OnMatrixReordered = new Observable();
        this.OnSelectedNeuronsChanged = new Observable();

        this.lastTreeSelection = undefined;
        this.RBCData = undefined;
        this.metaData = undefined;
        this.cacheServerData = {};
        this.cache = {};
        this.cacheExpanded = {};
        this.cacheTableProps = {};
        this.dataServerConnected = false;
        this.processSelection(this.lastTreeSelection);
    }


    getColumnsOfTable(tableName) {
        let metaData = this.metaData.filter(table => table.name === tableName);
        if (!metaData.length) {
            console.log("no meta data for table", tableName, this.metaData)
        }
        metaData = metaData[0];
        return metaData.columns;
    }

    loadTable(callback, tableName) {
        let that = this;
        const columns = this.getColumnsOfTable(tableName);
        //console.log("load table", tableName);
        this.getValues((serverResponse) => {
            //console.log("receive table", tableName);
            const tableFlat = serverResponse.values;
            that.cache[tableName] = tableFlat;
            that.cacheExpanded[tableName] = this.expandTable(tableFlat, columns);
            that.cacheTableProps[tableName] = getColumnMinMaxValues(tableFlat, columns);
            //console.log("processed table", tableName);
            callback();
        }, tableName, [], columns, "flat")

    }

    loadInitialData(callback) {
        let that = this;

        this.getMetaData((responseData) => {
            if(responseData === undefined){
                that.dataServerConnected = false;
                callback(false);
            } else {
                that.dataServerConnected = true;

                that.metaData = responseData.meta_data;
                that.available_views = responseData.available_views;            
                that.table_mapping = responseData.table_mapping;

                const cachedTables = responseData.cached_tables;
                const numTablesToLoad = cachedTables.length;
                let numTablesLoaded = 0;

                for (let tableIdx = 0; tableIdx < numTablesToLoad; tableIdx++) {
                    // eslint-disable-next-line
                    that.loadTable(() => {
                        numTablesLoaded += 1;
                        if (numTablesLoaded === numTablesToLoad) {
                            callback(true);
                        }
                    }, cachedTables[tableIdx]);
                }

                if (numTablesToLoad === 0) {
                    callback(true);
                }
            }
        });
    }


    getTableFlatNormalized(tableName, indices, selectedColumns) {
        const tableExpanded = this.cacheExpanded[tableName];
        const tableProps = this.cacheTableProps[tableName];

        let columnsMin = [];
        let columnsMax = [];

        for (let k = 0; k < selectedColumns.length; k++) {
            const columnName = selectedColumns[k];
            const props = tableProps.find(x => x.column === columnName);
            columnsMin.push(props.min);
            columnsMax.push(props.max);
        }

        const indicesSet = new Set(indices);
        const result = [];
        for (let rowIdx = 0; rowIdx < tableExpanded.length; rowIdx++) {
            if (!indicesSet.size || rowIdx in indicesSet) {
                const row = tableExpanded[rowIdx]
                const resultRow = []
                for (let k = 0; k < selectedColumns.length; k++) {
                    const columnName = selectedColumns[k];
                    const value = row[columnName];
                    const minTable = columnsMin[k];
                    const maxTable = columnsMax[k];
                    const normedValue = -1 + 2 * ((value - minTable) / (maxTable - minTable));
                    resultRow.push(normedValue);
                }
                result.push(resultRow)
            }
        }
        return result;
    }


    expandTable(tableFlat, columnNames) {
        let expandedTable = [];
        for (let rowIdx = 0; rowIdx < tableFlat.length; rowIdx++) {
            let row = { rowIdx };
            for (let colIdx = 0; colIdx < columnNames.length; colIdx++) {
                row[columnNames[colIdx]] = tableFlat[rowIdx][colIdx];
            }
            expandedTable.push(row);
        }
        return expandedTable;
    }

    getExpandedTableFiltered(tableName, indices, selectedColumns) {
        const table = this.cacheExpanded[tableName];
        const indicesSet = new Set(indices);
        if (!indices.length) {
            for (let rowIdx = 0; rowIdx < table.length; rowIdx++) {
                indicesSet.add(rowIdx);
            }
        }
        const filteredTable = table.filter((row) => indicesSet.has(row.rowIdx));
        const projectedTable = filteredTable.map((row) => {
            const filteredCols = {};
            for (let k = 0; k < selectedColumns.length; k++) {
                const columnName = selectedColumns[k];
                filteredCols[columnName] = row[columnName];
            }
            return filteredCols;
        })
        return projectedTable;
    }


    loadValues(callback, table, indices, columns, format) {
        if (this.cache[table] && (format === "flat-normalized" || format === "expanded")) {
            const filteredColProps = this.cacheTableProps[table].filter(x => columns.indexOf(x.column) !== -1)
            const dataRanges = {
                min: filteredColProps.map(x => x.min),
                max: filteredColProps.map(x => x.max)
            }

            if (format === "flat-normalized") {
                const normalizedTable = this.getTableFlatNormalized(table, indices, columns);
                callback({
                    indices: indices,
                    columns: columns,
                    values: normalizedTable,
                    data_ranges: dataRanges
                });
            }
            else if (format === "expanded") {
                const expandedTable = this.getExpandedTableFiltered(table, indices, columns);
                callback({
                    indices: indices,
                    columns: columns,
                    values: expandedTable,
                    data_ranges: dataRanges
                });
            } else {
                throw Error(format);
            }
        } else {
            let cacheKey = undefined;
            if (indices.length === 0) {
                cacheKey = table + format;
                for (let k = 0; k < columns.length; k++) {
                    cacheKey += columns[k]
                }
            }

            if (cacheKey !== undefined) {
                const cachedData = this.cacheServerData[cacheKey];
                if (cachedData !== undefined) {
                    callback(cachedData);
                }
            }

            let that = this;
            this.getValues((data) => {
                if (cacheKey !== undefined) {
                    that.cacheServerData[cacheKey] = data;
                }
                callback(data)
            }, table, indices, columns, format);
        }
    }

    project_data_2(column_names) {
        const dim1 = column_names[0];
        const dim2 = column_names[1];

        let data = this.RBCData.map((item) => {
            return {
                "dim_1": item[dim1],
                "dim_2": item[dim2],
                "selection_state": item.selection_state
            }
        });
        return data;
    }

    activateProfile(profileName) {
        window.sessionStorage.setItem("default_profile", profileName);
        window.location.reload();
    }

    processSelection(treeSelection) {
        this.selection = {
            leafsRow: undefined,
            leafsCol: undefined,
            numValuesPerLevelRow: undefined,
            numValuesPerLevelCol: undefined,
        }

        const emptyRowLeafs = [[["na", "1"]], [["na", "2"]], [["na", "3"]], [["na", "4"]], [["na", "5"]]];
        const emptyColLeafs = [[["na", "1"]], [["na", "2"]], [["na", "3"]], [["na", "4"]], [["na", "5"]], [["na", "6"]], [["na", "7"]], [["na", "8"]]];

        if (treeSelection === undefined) {
            this.selection.leafsRow = emptyRowLeafs;
            this.selection.leafsCol = emptyColLeafs;
            this.selection.numValuesPerLevelRow = [emptyRowLeafs.length];
            this.selection.numValuesPerLevelCol = [emptyColLeafs.length];
            return;
        }

        const getLeafs = (node, filterStack, list) => {
            if (node.functionalDescriptor) {
                filterStack.push([node.functionalDescriptor, node.value])
            }
            if (node.children.length) {
                for (let k = 0; k < node.children.length; k++) {
                    let filterStackCopy = JSON.parse(JSON.stringify(filterStack));
                    getLeafs(node.children[k], filterStackCopy, list);
                }
            } else {
                let filterStackCopy = JSON.parse(JSON.stringify(filterStack));
                list.push(filterStackCopy);
            }
        }

        const getNumValuesPerLevel = (node, numValues) => {
            if (node.children.length) {
                numValues.push(node.children.length);
                getNumValuesPerLevel(node.children[0], numValues);
            }
        }

        if (treeSelection.rows.children.length) {
            this.selection.leafsRow = [];
            this.selection.numValuesPerLevelRow = [];
            getLeafs(treeSelection.rows, [], this.selection.leafsRow);
            getNumValuesPerLevel(treeSelection.rows, this.selection.numValuesPerLevelRow)
        } else {
            this.selection.numValuesPerLevelRow = [emptyRowLeafs.length];
            this.selection.leafsRow = emptyRowLeafs;
        }

        if (treeSelection.cols.children.length) {
            this.selection.leafsCol = [];
            this.selection.numValuesPerLevelCol = [];
            getLeafs(treeSelection.cols, [], this.selection.leafsCol);
            getNumValuesPerLevel(treeSelection.cols, this.selection.numValuesPerLevelCol)
        } else {
            this.selection.numValuesPerLevelCol = [emptyColLeafs.length];
            this.selection.leafsCol = emptyColLeafs;
        }
    }

    setMatrixSelection(selection) {
        this.lastTreeSelection = deepCopy(selection);
        this.processSelection(this.lastTreeSelection);
        this.OnMatrixSelectionChanged.notifyObservers();
    }

    applyMatrixPermutation(permutation) {
        this.OnMatrixReordered.notifyObservers({
            isReset: false,
            permutation: permutation
        });
    }

    clearMatrixPermutation() {
        this.OnMatrixReordered.notifyObservers({
            isReset: true,
            permutation: undefined
        });
    }

    getActiveProfile() {
        if (this.activeProfile) {
            return this.profiles[this.activeProfile]
        } else {
            return undefined;
        }
    }

    getChannelDisplayName(channelIdx) {
        let name = this.getActiveProfile().channels[channelIdx].display_name;
        if (name !== undefined) {
            return name;
        } else {
            return "n/a";
        }
    }

    getDataServerURL(endpoint) {
        if (endpoint[0] !== '/') {
            endpoint = '/' + endpoint;
        }        
        const url = getServerURL("DATA_SERVER");
        return url + endpoint;        
    }

    getComputeServerURL(endpoint) {
        if (endpoint[0] !== '/') {
            endpoint = '/' + endpoint;
        }        
        const url = getServerURL("COMPUTE_SERVER")
        return url + endpoint;
    }


    /*  ##############################################
                    HTTP queries
        ##############################################        
    */


    getSimulation(callback, parameters) {
        const data = {
            "parameters": parameters
        }
        console.log("get parameters", parameters);
        axios.post(this.getComputeServerURL('/getSimulation'), data, { headers })
            .then(response => {
                let simulationData = response.data;
                callback(simulationData);
            }).catch(error => {
                console.log(error);
            });      
    }


    getValues(callback, table, indices, columns, format = "expanded") {
        const data = {
            "table": table,
            "indices": indices,
            "columns": columns,
            "format": format
        };
        axios.post(this.getDataServerURL('/getValues'), data, { headers })
            .then(response => {
                let responseData = response.data;
                callback(responseData);
            });            
    }


    getDensityValues(callback, table, columns, format, density_grid_shape) {
        const data = {
            "table" : table,            
            "columns" : columns,
            "format"  : format,
            "density_grid_shape" : density_grid_shape
        }
        axios.post(this.getDataServerURL('/getDensity'), data, { headers })
            .then(response => {
                let data = response.data;
                data.values = normalizeDensityValues(data.values, data.masked_value);                
                callback(data);                                
            });        
    }

    setDensityPlotSelection(data) {        
        axios.post(this.getDataServerURL('/setDensityPlotSelection'), data, { headers })
            .then(response => {
                console.log(response);
            })
            .catch(error => {                
                console.log(error);
            });           
    }

    setIndicesSelection(data) {        
        axios.post(this.getDataServerURL('/setIndicesSelection'), data, { headers })
            .then(response => {
                console.log(response);
            })
            .catch(error => {                
                console.log(error);
            });           
    }


    getResource(callback, filename) {
        if (this.cachedResource) {
            return callback(this.cachedResource);
        }
        let that = this;
        const data = {
            "filename": filename
        }
        axios.post(this.getDataServerURL('/getResourceJSON'), data, { headers })
            .then(response => {
                let jsonObj = response.data;
                that.cachedResource = jsonObj;
                callback(jsonObj);
            });
    }

    getMetaData(callback) {
        axios.post(this.getDataServerURL('/getMetaData'), {}, { headers })
            .then(response => {
                let responseData = response.data;
                callback(responseData);
            })        
            .catch(error => {
                console.log(error);
                callback(undefined);
            });        
    }
}