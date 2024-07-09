#!/usr/bin/python

import sys
import single_cell_parser as scp
from data_base.dbopen import dbopen


def create_network_parameter(templateParamName,
                             cellNumberFileName,
                             synFileName,
                             conFileName,
                             outFileName,
                             write_all_celltypes=False):
    print('*************')
    print('creating network parameter file from template {:s}'.format(
        templateParamName))
    print('*************')

    templateParam = scp.build_parameters(templateParamName)
    cellTypeColumnNumbers = load_cell_number_file(cellNumberFileName)

    nwParam = scp.NTParameterSet({
        'info': templateParam.info,
        'NMODL_mechanisms': templateParam.NMODL_mechanisms
    })
    #    nwParam.info = templateParam.info
    #    nwParam.NMODL_mechanisms = templateParam.NMODL_mechanisms
    nwParam.network = {}

    for cellType in list(cellTypeColumnNumbers.keys()):
        cellTypeParameters = templateParam.network[cellType]
        for column in list(cellTypeColumnNumbers[cellType].keys()):
            numberOfCells = cellTypeColumnNumbers[cellType][column]
            if numberOfCells == 0 and not write_all_celltypes:
                continue
            cellTypeName = cellType + '_' + column
            nwParam.network[cellTypeName] = cellTypeParameters.tree_copy()
            nwParam.network[cellTypeName].cellNr = numberOfCells
            nwParam.network[
                cellTypeName].synapses.distributionFile = synFileName
            nwParam.network[cellTypeName].synapses.connectionFile = conFileName

    nwParam.save(outFileName)


def load_cell_number_file(cellNumberFileName):
    cellTypeColumnNumbers = {}
    with dbopen(cellNumberFileName, 'r') as cellNumberFile:
        lineCnt = 0
        for line in cellNumberFile:
            if line:
                lineCnt += 1
            if lineCnt <= 1:
                continue
            splitLine = line.strip().split('\t')
            column = splitLine[0]
            cellType = splitLine[1]
            numberOfCells = int(splitLine[2])
            if cellType not in cellTypeColumnNumbers:
                cellTypeColumnNumbers[cellType] = {}
            cellTypeColumnNumbers[cellType][column] = numberOfCells

    return cellTypeColumnNumbers


if __name__ == '__main__':
    if len(sys.argv) == 5:
        templateParamName = sys.argv[1]
        cellNumberFileName = sys.argv[2]
        synFileName = sys.argv[3]
        #        conFileName = sys.argv[4]
        conFileName = synFileName[:-4] + '.con'
        outFileName = sys.argv[4]
        create_network_parameter(templateParamName, cellNumberFileName,
                                 synFileName, conFileName, outFileName)
    else:
        #        print 'parameters: [templateParamName] [cellNumberFileName] [synFileName] [conFileName] [outFileName]'
        print(
            'parameters: [templateParamName] [cellNumberFileName] [synFileName] [outFileName]'
        )
