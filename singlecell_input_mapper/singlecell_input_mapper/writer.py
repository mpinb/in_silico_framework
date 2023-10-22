'''
Created on Mar 8, 2012

@author: regger
'''
from __future__ import absolute_import
from .scalar_field import ScalarField
from .generate_nr_of_cells_spreadsheet import con_file_to_NumberOfConnectedCells_sheet
from model_data_base.mdbopen import mdbopen

labels2int = {\
    "Neuron":                 2,\
    "Dendrite":               3,\
    "ApicalDendrite":         4,\
    "BasalDendrite":          5,\
    "Axon":                   6,\
    "AIS":                    6,\
    "Myelin":                 6,\
    "Node":                   6,\
    "Soma":                   7,\
    "Landmark":               8,\
    "Pia":                    9,\
    "WhiteMatter":           48,\
    "Vessel":                10,\
    "Barrel":                11,\
    "ZAxis":                 50,\
    "aRow":                  12,\
    "A1":                    13,\
    "A2":                    14,\
    "A3":                    15,\
    "A4":                    16,\
    "bRow":                  17,\
    "B1":                    18,\
    "B2":                    19,\
    "B3":                    20,\
    "B4":                    21,\
    "cRow":                  22,\
    "C1":                    23,\
    "C2":                    24,\
    "C3":                    25,\
    "C4":                    26,\
    "C5":                    27,\
    "C6":                    28,\
    "dRow":                  29,\
    "D1":                    30,\
    "D2":                    31,\
    "D3":                    32,\
    "D4":                    33,\
    "D5":                    34,\
    "D6":                    35,\
    "eRow":                  36,\
    "E1":                    37,\
    "E2":                    38,\
    "E3":                    39,\
    "E4":                    40,\
    "E5":                    41,\
    "E6":                    42,\
    "greekRow":              43,\
    "Alpha":                 44,\
    "Beta":                  45,\
    "Gamma":                 46,\
    "Delta":                 47,\
    "Septum":                 0,\
              }


def write_landmark_file(fname=None, landmarkList=None):
    '''
    write Amira landmark file
    landmarkList has to be iterable of tuples,
    each of which holds 3 float coordinates
    '''
    if fname is None:
        err_str = 'No landmark output file name given'
        raise RuntimeError(err_str)


#    if not landmarkList:
#        print 'Landmark list empty!'
#        return
#    nrCoords = len(landmarkList[0])
#    if nrCoords != 3:
#        err_str = 'Landmarks have wrong format! Number of coordinates is ' + str(nrCoords) + ', should be 3'
#        raise RuntimeError(err_str)

    if not fname.endswith('.landmarkAscii'):
        fname += '.landmarkAscii'

    with mdbopen(fname, 'w') as landmarkFile:
        nrOfLandmarks = len(landmarkList)
        header = '# AmiraMesh 3D ASCII 2.0\n\n'\
                'define Markers ' + str(nrOfLandmarks) + '\n\n'\
                'Parameters {\n'\
                '\tNumSets 1,\n'\
                '\tContentType \"LandmarkSet\"\n'\
                '}\n\n'\
                'Markers { float[3] Coordinates } @1\n\n'\
                '# Data section follows\n'\
                '@1\n'
        landmarkFile.write(header)
        for pt in landmarkList:
            line = '%.6f %.6f %.6f\n' % (pt[0], pt[1], pt[2])
            landmarkFile.write(line)


def write_cell_synapse_locations(fname=None, synapses=None, cellID=None):
    '''
    writes list of all synapses with the locations
    coded by section ID and section x of cell with ID 'cellID'
    '''
    if fname is None or synapses is None or cellID is None:
        err_str = 'Incomplete data! Cannot write synapse location file'
        raise RuntimeError(err_str)

    if not fname.endswith('.syn') and not fname.endswith('.SYN'):
        fname += '.syn'

    synFormat = None
    with mdbopen(fname, 'w') as outputFile:
        header = '# Synapse distribution file\n'
        header += '# corresponding to cell: '
        header += cellID
        header += '\n'
        header += '# Type - section - section.x\n\n'
        outputFile.write(header)
        for synType in list(synapses.keys()):
            for syn in synapses[synType]:
                if synFormat is None:
                    try:
                        line = syn.preCellType
                        synFormat = 'Synapse'
                    except AttributeError:
                        synFormat = 'Tuple'
                if synFormat == 'Synapse':
                    line = syn.preCellType
                    line += '\t'
                    line += str(syn.secID)
                    line += '\t'
                    if syn.x > 1.0:
                        syn.x = 1.0
                    if syn.x < 0.0:
                        syn.x = 0.0
                    line += str(syn.x)
                    line += '\n'
                    outputFile.write(line)
                elif synFormat == 'Tuple':
                    line = syn[0]
                    line += '\t'
                    line += str(syn[1])
                    line += '\t'
                    if syn[2] > 1.0:
                        syn[2] = 1.0
                    if syn[2] < 0.0:
                        syn[2] = 0.0
                    line += str(syn[2])
                    line += '\n'
                    outputFile.write(line)


def write_anatomical_realization_map(fname=None,
                                     functionalMap=None,
                                     anatomicalID=None):
    '''
    writes list of all functional connections
    coded by tuples (cell type, presynaptic cell index, synapse index).
    Only valid for anatomical synapse realization given by anatomicalID
    '''
    if fname is None or functionalMap is None or anatomicalID is None:
        err_str = 'Incomplete data! Cannot write functional realization file'
        raise RuntimeError(err_str)

    if not fname.endswith('.con') and not fname.endswith('.CON'):
        fname += '.con'

    with mdbopen(fname, 'w') as outputFile:
        header = '# Anatomical connectivity realization file; only valid with synapse realization:\n'
        header += '# ' + anatomicalID
        header += '\n'
        header += '# Type - cell ID - synapse ID\n\n'
        outputFile.write(header)
        for con in functionalMap:
            line = con[0]
            line += '\t'
            line += str(con[1])
            line += '\t'
            line += str(con[2])
            line += '\n'
            outputFile.write(line)

    # added by arco: single_cell_parser needs number of connected cells spreadsheet
    # this can be generated out of the .con file.
    # todo: find a less ugly method to do this
    con_file_to_NumberOfConnectedCells_sheet(fname)


def write_sample_connectivity_summary(fname=None,
                                      cellTypeSummaryData=None,
                                      columnSummaryData=None):
    if fname is None or cellTypeSummaryData is None or columnSummaryData is None:
        #def write_sample_connectivity_summary(fname=None, columnSummaryData=None):
        #    if fname is None or columnSummaryData is None:
        err_str = 'Incomplete data! Cannot write results summary file'
        raise RuntimeError(err_str)

    if not fname.endswith('.csv') and not fname.endswith('.CSV'):
        fname += '.csv'


#    with open(fname, 'w') as outFile:
#        header = '# connectivity summary\n'
#        header += 'Presynaptic column\tPresynaptic cell type\tNumber of synapses\tConnected presynaptic cells\tTotal presynaptic cells\n'
#        outFile.write(header)
#        columns = columnSummaryData.keys()
#        columns.sort()
#        if len(columns):
#            preCellTypes = columnSummaryData[columns[0]].keys()
#            preCellTypes.sort()
#            for col in columns:
#                for preCellType in preCellTypes:
#                    data = columnSummaryData[col][preCellType]
#                    line = col + '\t' + preCellType + '\t'
#                    line += str(data[0])
#                    line += '\t'
#                    line += str(data[1])
#                    line += '\t'
#                    line += str(data[2])
#                    line += '\n'
#                    outFile.write(line)

    outCellTypes = ('L2','L34','L4py','L4sp','L4ss','L5st','L5tt','L6cc','L6ccinv','L6ct','VPM',\
                    'L1','L23Trans','L45Peak','L45Sym','L56Trans','SymLocal1','SymLocal2',\
                    'SymLocal3','SymLocal4','SymLocal5','SymLocal6')

    with mdbopen(fname, 'w') as outFile:
        header1 = '# connectivity per cell type summary\n'
        header1 += 'Presynaptic cell type\tNumber of synapses\tMean path length to soma\tSD path length to soma\t'
        header1 += 'Connected presynaptic cells\tTotal presynaptic cells\tConvergence\t'
        header1 += 'Number of apical dendrite synapses\tMean path length to soma (apical synapses)\tSD path length to soma (apical synapses)\t'
        header1 += 'Connected presynaptic cells (apical synapses)\tConvergence (apical synapses)\t'
        header1 += 'Number of basal dendrite synapses\tMean path length to soma (basal synapses)\tSD path length to soma (basal synapses)\t'
        header1 += 'Connected presynaptic cells (basal synapses)\tConvergence (basal synapses)\t'
        header1 += 'Number of soma synapses\t'
        header1 += 'Connected presynaptic cells (soma synapses)\tConvergence (soma synapses)\n'
        outFile.write(header1)
        #        preCellTypes = cellTypeSummaryData.keys()
        #        preCellTypes.sort()
        for preCellType in outCellTypes:
            try:
                data = cellTypeSummaryData[preCellType]
            except KeyError:
                continue
            totalSynapses = data[0]
            nrOfConnectedCells = data[1]
            nrOfAllCells = data[2]
            convergence = data[3]
            distanceTotalMean = data[4]
            distanceTotalSD = data[5]
            synapsesPerStructure = data[6]
            connectionsPerStructure = data[7]
            convergencePerStructure = data[8]
            distancesPerStructure = data[9]
            apicalSynapses = synapsesPerStructure['ApicalDendrite']
            basalSynapses = synapsesPerStructure['BasalDendrite']
            somaSynapses = synapsesPerStructure['Soma']
            connectionsPerStructureApical = connectionsPerStructure[
                'ApicalDendrite']
            connectionsPerStructureBasal = connectionsPerStructure[
                'BasalDendrite']
            connectionsPerStructureSoma = connectionsPerStructure['Soma']
            convergencePerStructureApical = convergencePerStructure[
                'ApicalDendrite']
            convergencePerStructureBasal = convergencePerStructure[
                'BasalDendrite']
            convergencePerStructureSoma = convergencePerStructure['Soma']
            distanceApicalMean = distancesPerStructure['ApicalDendrite'][0]
            distanceApicalSD = distancesPerStructure['ApicalDendrite'][1]
            distanceBasalMean = distancesPerStructure['BasalDendrite'][0]
            distanceBasalSD = distancesPerStructure['BasalDendrite'][1]
            line = preCellType + '\t'
            line += str(totalSynapses)
            line += '\t'
            line += str(distanceTotalMean)
            line += '\t'
            line += str(distanceTotalSD)
            line += '\t'
            line += str(nrOfConnectedCells)
            line += '\t'
            line += str(nrOfAllCells)
            line += '\t'
            line += str(convergence)
            line += '\t'
            line += str(apicalSynapses)
            line += '\t'
            line += str(distanceApicalMean)
            line += '\t'
            line += str(distanceApicalSD)
            line += '\t'
            line += str(connectionsPerStructureApical)
            line += '\t'
            line += str(convergencePerStructureApical)
            line += '\t'
            line += str(basalSynapses)
            line += '\t'
            line += str(distanceBasalMean)
            line += '\t'
            line += str(distanceBasalSD)
            line += '\t'
            line += str(connectionsPerStructureBasal)
            line += '\t'
            line += str(convergencePerStructureBasal)
            line += '\t'
            line += str(somaSynapses)
            line += '\t'
            line += str(connectionsPerStructureSoma)
            line += '\t'
            line += str(convergencePerStructureSoma)
            line += '\n'
            outFile.write(line)

        outFile.write('\n')

        header2 = '# connectivity per column per cell type summary\n'
        header2 += 'Presynaptic column\tPresynaptic cell type\tNumber of synapses\tMean path length to soma\tSD path length to soma\t'
        header2 += 'Connected presynaptic cells\tTotal presynaptic cells\tConvergence\t'
        header2 += 'Number of apical dendrite synapses\tMean path length to soma (apical synapses)\tSD path length to soma (apical synapses)\t'
        header2 += 'Connected presynaptic cells (apical synapses)\tConvergence (apical synapses)\t'
        header2 += 'Number of basal dendrite synapses\tMean path length to soma (basal synapses)\tSD path length to soma (basal synapses)\t'
        header2 += 'Connected presynaptic cells (basal synapses)\tConvergence (basal synapses)\t'
        header2 += 'Number of soma synapses\t'
        header2 += 'Connected presynaptic cells (soma synapses)\tConvergence (soma synapses)\n'
        outFile.write(header2)
        columns = list(columnSummaryData.keys())
        columns.sort()
        if len(columns):
            #            preCellTypes = columnSummaryData[columns[0]].keys()
            #            preCellTypes.sort()
            for col in columns:
                for preCellType in outCellTypes:
                    try:
                        data = columnSummaryData[col][preCellType]
                    except KeyError:
                        continue
                    totalSynapses = data[0]
                    nrOfConnectedCells = data[1]
                    nrOfAllCells = data[2]
                    convergence = data[3]
                    distanceTotalMean = data[4]
                    distanceTotalSD = data[5]
                    synapsesPerStructure = data[6]
                    connectionsPerStructure = data[7]
                    convergencePerStructure = data[8]
                    distancesPerStructure = data[9]
                    apicalSynapses = synapsesPerStructure['ApicalDendrite']
                    basalSynapses = synapsesPerStructure['BasalDendrite']
                    somaSynapses = synapsesPerStructure['Soma']
                    connectionsPerStructureApical = connectionsPerStructure[
                        'ApicalDendrite']
                    connectionsPerStructureBasal = connectionsPerStructure[
                        'BasalDendrite']
                    connectionsPerStructureSoma = connectionsPerStructure[
                        'Soma']
                    convergencePerStructureApical = convergencePerStructure[
                        'ApicalDendrite']
                    convergencePerStructureBasal = convergencePerStructure[
                        'BasalDendrite']
                    convergencePerStructureSoma = convergencePerStructure[
                        'Soma']
                    distanceApicalMean = distancesPerStructure[
                        'ApicalDendrite'][0]
                    distanceApicalSD = distancesPerStructure['ApicalDendrite'][
                        1]
                    distanceBasalMean = distancesPerStructure['BasalDendrite'][
                        0]
                    distanceBasalSD = distancesPerStructure['BasalDendrite'][1]
                    line = col + '\t' + preCellType + '\t'
                    line += str(totalSynapses)
                    line += '\t'
                    line += str(distanceTotalMean)
                    line += '\t'
                    line += str(distanceTotalSD)
                    line += '\t'
                    line += str(nrOfConnectedCells)
                    line += '\t'
                    line += str(nrOfAllCells)
                    line += '\t'
                    line += str(convergence)
                    line += '\t'
                    line += str(apicalSynapses)
                    line += '\t'
                    line += str(distanceApicalMean)
                    line += '\t'
                    line += str(distanceApicalSD)
                    line += '\t'
                    line += str(connectionsPerStructureApical)
                    line += '\t'
                    line += str(convergencePerStructureApical)
                    line += '\t'
                    line += str(basalSynapses)
                    line += '\t'
                    line += str(distanceBasalMean)
                    line += '\t'
                    line += str(distanceBasalSD)
                    line += '\t'
                    line += str(connectionsPerStructureBasal)
                    line += '\t'
                    line += str(convergencePerStructureBasal)
                    line += '\t'
                    line += str(somaSynapses)
                    line += '\t'
                    line += str(connectionsPerStructureSoma)
                    line += '\t'
                    line += str(convergencePerStructureSoma)
                    line += '\n'
                    outFile.write(line)


def write_population_connectivity_summary(fname=None,
                                          populationDistribution=None):
    if fname is None or populationDistribution is None:
        #def write_sample_connectivity_summary(fname=None, columnSummaryData=None):
        #    if fname is None or columnSummaryData is None:
        err_str = 'Incomplete data! Cannot write results summary file'
        raise RuntimeError(err_str)

    if not fname.endswith('.csv') and not fname.endswith('.CSV'):
        fname += '.csv'

    outCellTypes = ('L2','L34','L4py','L4sp','L4ss','L5st','L5tt','L6cc','L6ccinv','L6ct','VPM',\
                    'L1','L23Trans','L45Peak','L45Sym','L56Trans','SymLocal1','SymLocal2',\
                    'SymLocal3','SymLocal4','SymLocal5','SymLocal6')

    with mdbopen(fname, 'w') as outFile:
        header0 = '# connectivity per cell type population summary\n'
        header0 += 'Presynaptic cell type\tNumber of synapses\tSTD\tMean path length to soma\tSTD\tSD path length to soma\tSTD\t'
        header0 += 'Connected presynaptic cells\tSTD\tTotal presynaptic cells\tConvergence\tSTD\t'
        header0 += 'Number of apical dendrite synapses\tSTD\tMean path length to soma (apical synapses)\tSTD\tSD path length to soma (apical synapses)\tSTD\t'
        header0 += 'Connected presynaptic cells (apical synapses)\tSTD\tConvergence (apical synapses)\tSTD\t'
        header0 += 'Number of basal dendrite synapses\tSTD\tMean path length to soma (basal synapses)\tSTD\tSD path length to soma (basal synapses)\tSTD\t'
        header0 += 'Connected presynaptic cells (basal synapses)\tSTD\tConvergence (basal synapses)\tSTD\t'
        header0 += 'Number of soma synapses\tSTD\t'
        header0 += 'Connected presynaptic cells (soma synapses)\tSTD\tConvergence (soma synapses)\tSTD\n'
        outFile.write(header0)
        #        preCellTypes = populationDistribution.keys()
        #        preCellTypes.sort()
        for preCellType in outCellTypes:
            data = populationDistribution[preCellType]
            totalSynapses = data[0]
            nrOfConnectedCells = data[1]
            nrOfAllCells = data[2]
            convergence = data[3]
            distanceTotalMean = data[4]
            distanceTotalSD = data[5]
            synapsesPerStructure = data[6]
            connectionsPerStructure = data[7]
            convergencePerStructure = data[8]
            distancesPerStructure = data[9]
            apicalSynapses = synapsesPerStructure['ApicalDendrite']
            basalSynapses = synapsesPerStructure['BasalDendrite']
            somaSynapses = synapsesPerStructure['Soma']
            connectionsPerStructureApical = connectionsPerStructure[
                'ApicalDendrite']
            connectionsPerStructureBasal = connectionsPerStructure[
                'BasalDendrite']
            connectionsPerStructureSoma = connectionsPerStructure['Soma']
            convergencePerStructureApical = convergencePerStructure[
                'ApicalDendrite']
            convergencePerStructureBasal = convergencePerStructure[
                'BasalDendrite']
            convergencePerStructureSoma = convergencePerStructure['Soma']
            distanceApicalMean = distancesPerStructure['ApicalDendrite'][0]
            distanceApicalSD = distancesPerStructure['ApicalDendrite'][1]
            distanceBasalMean = distancesPerStructure['BasalDendrite'][0]
            distanceBasalSD = distancesPerStructure['BasalDendrite'][1]
            line = preCellType + '\t'
            line += str(totalSynapses[0])
            line += '\t'
            line += str(totalSynapses[1])
            line += '\t'
            line += str(distanceTotalMean[0])
            line += '\t'
            line += str(distanceTotalMean[1])
            line += '\t'
            line += str(distanceTotalSD[0])
            line += '\t'
            line += str(distanceTotalSD[1])
            line += '\t'
            line += str(nrOfConnectedCells[0])
            line += '\t'
            line += str(nrOfConnectedCells[1])
            line += '\t'
            line += str(nrOfAllCells[0])
            line += '\t'
            line += str(convergence[0])
            line += '\t'
            line += str(convergence[1])
            line += '\t'
            line += str(apicalSynapses[0])
            line += '\t'
            line += str(apicalSynapses[1])
            line += '\t'
            line += str(distanceApicalMean[0])
            line += '\t'
            line += str(distanceApicalMean[1])
            line += '\t'
            line += str(distanceApicalSD[0])
            line += '\t'
            line += str(distanceApicalSD[1])
            line += '\t'
            line += str(connectionsPerStructureApical[0])
            line += '\t'
            line += str(connectionsPerStructureApical[1])
            line += '\t'
            line += str(convergencePerStructureApical[0])
            line += '\t'
            line += str(convergencePerStructureApical[1])
            line += '\t'
            line += str(basalSynapses[0])
            line += '\t'
            line += str(basalSynapses[1])
            line += '\t'
            line += str(distanceBasalMean[0])
            line += '\t'
            line += str(distanceBasalMean[1])
            line += '\t'
            line += str(distanceBasalSD[0])
            line += '\t'
            line += str(distanceBasalSD[1])
            line += '\t'
            line += str(connectionsPerStructureBasal[0])
            line += '\t'
            line += str(connectionsPerStructureBasal[1])
            line += '\t'
            line += str(convergencePerStructureBasal[0])
            line += '\t'
            line += str(convergencePerStructureBasal[1])
            line += '\t'
            line += str(somaSynapses[0])
            line += '\t'
            line += str(somaSynapses[1])
            line += '\t'
            line += str(connectionsPerStructureSoma[0])
            line += '\t'
            line += str(connectionsPerStructureSoma[1])
            line += '\t'
            line += str(convergencePerStructureSoma[0])
            line += '\t'
            line += str(convergencePerStructureSoma[1])
            line += '\n'
            outFile.write(line)

        outFile.write('\n')


def write_population_and_sample_connectivity_summary(
        fname=None,
        populationDistribution=None,
        cellTypeSummaryData=None,
        columnSummaryData=None):
    if fname is None or populationDistribution is None or cellTypeSummaryData is None or columnSummaryData is None:
        #def write_sample_connectivity_summary(fname=None, columnSummaryData=None):
        #    if fname is None or columnSummaryData is None:
        err_str = 'Incomplete data! Cannot write results summary file'
        raise RuntimeError(err_str)

    if not fname.endswith('.csv') and not fname.endswith('.CSV'):
        fname += '.csv'


#    with open(fname, 'w') as outFile:
#        header = '# connectivity summary\n'
#        header += 'Presynaptic column\tPresynaptic cell type\tNumber of synapses\tConnected presynaptic cells\tTotal presynaptic cells\n'
#        outFile.write(header)
#        columns = columnSummaryData.keys()
#        columns.sort()
#        if len(columns):
#            preCellTypes = columnSummaryData[columns[0]].keys()
#            preCellTypes.sort()
#            for col in columns:
#                for preCellType in preCellTypes:
#                    data = columnSummaryData[col][preCellType]
#                    line = col + '\t' + preCellType + '\t'
#                    line += str(data[0])
#                    line += '\t'
#                    line += str(data[1])
#                    line += '\t'
#                    line += str(data[2])
#                    line += '\n'
#                    outFile.write(line)

    outCellTypes = ('L2','L34','L4py','L4sp','L4ss','L5st','L5tt','L6cc','L6ccinv','L6ct','VPM',\
                    'L1','L23Trans','L45Peak','L45Sym','L56Trans','SymLocal1','SymLocal2',\
                    'SymLocal3','SymLocal4','SymLocal5','SymLocal6')

    with mdbopen(fname, 'w') as outFile:
        header0 = '# connectivity per cell type population summary\n'
        header0 += 'Presynaptic cell type\tNumber of synapses\tSTD\tMean path length to soma\tSTD\tSD path length to soma\tSTD\t'
        header0 += 'Connected presynaptic cells\tSTD\tTotal presynaptic cells\tConvergence\tSTD\t'
        header0 += 'Number of apical dendrite synapses\tSTD\tMean path length to soma (apical synapses)\tSTD\tSD path length to soma (apical synapses)\tSTD\t'
        header0 += 'Connected presynaptic cells (apical synapses)\tSTD\tConvergence (apical synapses)\tSTD\t'
        header0 += 'Number of basal dendrite synapses\tSTD\tMean path length to soma (basal synapses)\tSTD\tSD path length to soma (basal synapses)\tSTD\t'
        header0 += 'Connected presynaptic cells (basal synapses)\tSTD\tConvergence (basal synapses)\tSTD\t'
        header0 += 'Number of soma synapses\tSTD\t'
        header0 += 'Connected presynaptic cells (soma synapses)\tSTD\tConvergence (soma synapses)\tSTD\n'
        outFile.write(header0)
        #        preCellTypes = populationDistribution.keys()
        #        preCellTypes.sort()
        for preCellType in outCellTypes:
            data = populationDistribution[preCellType]
            totalSynapses = data[0]
            nrOfConnectedCells = data[1]
            nrOfAllCells = data[2]
            convergence = data[3]
            distanceTotalMean = data[4]
            distanceTotalSD = data[5]
            synapsesPerStructure = data[6]
            connectionsPerStructure = data[7]
            convergencePerStructure = data[8]
            distancesPerStructure = data[9]
            apicalSynapses = synapsesPerStructure['ApicalDendrite']
            basalSynapses = synapsesPerStructure['BasalDendrite']
            somaSynapses = synapsesPerStructure['Soma']
            connectionsPerStructureApical = connectionsPerStructure[
                'ApicalDendrite']
            connectionsPerStructureBasal = connectionsPerStructure[
                'BasalDendrite']
            connectionsPerStructureSoma = connectionsPerStructure['Soma']
            convergencePerStructureApical = convergencePerStructure[
                'ApicalDendrite']
            convergencePerStructureBasal = convergencePerStructure[
                'BasalDendrite']
            convergencePerStructureSoma = convergencePerStructure['Soma']
            distanceApicalMean = distancesPerStructure['ApicalDendrite'][0]
            distanceApicalSD = distancesPerStructure['ApicalDendrite'][1]
            distanceBasalMean = distancesPerStructure['BasalDendrite'][0]
            distanceBasalSD = distancesPerStructure['BasalDendrite'][1]
            line = preCellType + '\t'
            line += str(totalSynapses[0])
            line += '\t'
            line += str(totalSynapses[1])
            line += '\t'
            line += str(distanceTotalMean[0])
            line += '\t'
            line += str(distanceTotalMean[1])
            line += '\t'
            line += str(distanceTotalSD[0])
            line += '\t'
            line += str(distanceTotalSD[1])
            line += '\t'
            line += str(nrOfConnectedCells[0])
            line += '\t'
            line += str(nrOfConnectedCells[1])
            line += '\t'
            line += str(nrOfAllCells[0])
            line += '\t'
            line += str(convergence[0])
            line += '\t'
            line += str(convergence[1])
            line += '\t'
            line += str(apicalSynapses[0])
            line += '\t'
            line += str(apicalSynapses[1])
            line += '\t'
            line += str(distanceApicalMean[0])
            line += '\t'
            line += str(distanceApicalMean[1])
            line += '\t'
            line += str(distanceApicalSD[0])
            line += '\t'
            line += str(distanceApicalSD[1])
            line += '\t'
            line += str(connectionsPerStructureApical[0])
            line += '\t'
            line += str(connectionsPerStructureApical[1])
            line += '\t'
            line += str(convergencePerStructureApical[0])
            line += '\t'
            line += str(convergencePerStructureApical[1])
            line += '\t'
            line += str(basalSynapses[0])
            line += '\t'
            line += str(basalSynapses[1])
            line += '\t'
            line += str(distanceBasalMean[0])
            line += '\t'
            line += str(distanceBasalMean[1])
            line += '\t'
            line += str(distanceBasalSD[0])
            line += '\t'
            line += str(distanceBasalSD[1])
            line += '\t'
            line += str(connectionsPerStructureBasal[0])
            line += '\t'
            line += str(connectionsPerStructureBasal[1])
            line += '\t'
            line += str(convergencePerStructureBasal[0])
            line += '\t'
            line += str(convergencePerStructureBasal[1])
            line += '\t'
            line += str(somaSynapses[0])
            line += '\t'
            line += str(somaSynapses[1])
            line += '\t'
            line += str(connectionsPerStructureSoma[0])
            line += '\t'
            line += str(connectionsPerStructureSoma[1])
            line += '\t'
            line += str(convergencePerStructureSoma[0])
            line += '\t'
            line += str(convergencePerStructureSoma[1])
            line += '\n'
            outFile.write(line)

        outFile.write('\n')

        header1 = '# connectivity per cell type representative realization summary\n'
        header1 += 'Presynaptic cell type\tNumber of synapses\tMean path length to soma\tSD path length to soma\t'
        header1 += 'Connected presynaptic cells\tTotal presynaptic cells\tConvergence\t'
        header1 += 'Number of apical dendrite synapses\tMean path length to soma (apical synapses)\tSD path length to soma (apical synapses)\t'
        header1 += 'Connected presynaptic cells (apical synapses)\tConvergence (apical synapses)\t'
        header1 += 'Number of basal dendrite synapses\tMean path length to soma (basal synapses)\tSD path length to soma (basal synapses)\t'
        header1 += 'Connected presynaptic cells (basal synapses)\tConvergence (basal synapses)\t'
        header1 += 'Number of soma synapses\t'
        header1 += 'Connected presynaptic cells (soma synapses)\tConvergence (soma synapses)\n'
        outFile.write(header1)
        #        preCellTypes = cellTypeSummaryData.keys()
        #        preCellTypes.sort()
        for preCellType in outCellTypes:
            data = cellTypeSummaryData[preCellType]
            totalSynapses = data[0]
            nrOfConnectedCells = data[1]
            nrOfAllCells = data[2]
            convergence = data[3]
            distanceTotalMean = data[4]
            distanceTotalSD = data[5]
            synapsesPerStructure = data[6]
            connectionsPerStructure = data[7]
            convergencePerStructure = data[8]
            distancesPerStructure = data[9]
            apicalSynapses = synapsesPerStructure['ApicalDendrite']
            basalSynapses = synapsesPerStructure['BasalDendrite']
            somaSynapses = synapsesPerStructure['Soma']
            connectionsPerStructureApical = connectionsPerStructure[
                'ApicalDendrite']
            connectionsPerStructureBasal = connectionsPerStructure[
                'BasalDendrite']
            connectionsPerStructureSoma = connectionsPerStructure['Soma']
            convergencePerStructureApical = convergencePerStructure[
                'ApicalDendrite']
            convergencePerStructureBasal = convergencePerStructure[
                'BasalDendrite']
            convergencePerStructureSoma = convergencePerStructure['Soma']
            distanceApicalMean = distancesPerStructure['ApicalDendrite'][0]
            distanceApicalSD = distancesPerStructure['ApicalDendrite'][1]
            distanceBasalMean = distancesPerStructure['BasalDendrite'][0]
            distanceBasalSD = distancesPerStructure['BasalDendrite'][1]
            line = preCellType + '\t'
            line += str(totalSynapses)
            line += '\t'
            line += str(distanceTotalMean)
            line += '\t'
            line += str(distanceTotalSD)
            line += '\t'
            line += str(nrOfConnectedCells)
            line += '\t'
            line += str(nrOfAllCells)
            line += '\t'
            line += str(convergence)
            line += '\t'
            line += str(apicalSynapses)
            line += '\t'
            line += str(distanceApicalMean)
            line += '\t'
            line += str(distanceApicalSD)
            line += '\t'
            line += str(connectionsPerStructureApical)
            line += '\t'
            line += str(convergencePerStructureApical)
            line += '\t'
            line += str(basalSynapses)
            line += '\t'
            line += str(distanceBasalMean)
            line += '\t'
            line += str(distanceBasalSD)
            line += '\t'
            line += str(connectionsPerStructureBasal)
            line += '\t'
            line += str(convergencePerStructureBasal)
            line += '\t'
            line += str(somaSynapses)
            line += '\t'
            line += str(connectionsPerStructureSoma)
            line += '\t'
            line += str(convergencePerStructureSoma)
            line += '\n'
            outFile.write(line)

        outFile.write('\n')

        header2 = '# connectivity per column per cell type summary\n'
        header2 += 'Presynaptic column\tPresynaptic cell type\tNumber of synapses\tMean path length to soma\tSD path length to soma\t'
        header2 += 'Connected presynaptic cells\tTotal presynaptic cells\tConvergence\t'
        header2 += 'Number of apical dendrite synapses\tMean path length to soma (apical synapses)\tSD path length to soma (apical synapses)\t'
        header2 += 'Connected presynaptic cells (apical synapses)\tConvergence (apical synapses)\t'
        header2 += 'Number of basal dendrite synapses\tMean path length to soma (basal synapses)\tSD path length to soma (basal synapses)\t'
        header2 += 'Connected presynaptic cells (basal synapses)\tConvergence (basal synapses)\t'
        header2 += 'Number of soma synapses\t'
        header2 += 'Connected presynaptic cells (soma synapses)\tConvergence (soma synapses)\n'
        outFile.write(header2)
        columns = list(columnSummaryData.keys())
        columns.sort()
        if len(columns):
            #            preCellTypes = columnSummaryData[columns[0]].keys()
            #            preCellTypes.sort()
            for col in columns:
                for preCellType in outCellTypes:
                    data = columnSummaryData[col][preCellType]
                    totalSynapses = data[0]
                    nrOfConnectedCells = data[1]
                    nrOfAllCells = data[2]
                    convergence = data[3]
                    distanceTotalMean = data[4]
                    distanceTotalSD = data[5]
                    synapsesPerStructure = data[6]
                    connectionsPerStructure = data[7]
                    convergencePerStructure = data[8]
                    distancesPerStructure = data[9]
                    apicalSynapses = synapsesPerStructure['ApicalDendrite']
                    basalSynapses = synapsesPerStructure['BasalDendrite']
                    somaSynapses = synapsesPerStructure['Soma']
                    connectionsPerStructureApical = connectionsPerStructure[
                        'ApicalDendrite']
                    connectionsPerStructureBasal = connectionsPerStructure[
                        'BasalDendrite']
                    connectionsPerStructureSoma = connectionsPerStructure[
                        'Soma']
                    convergencePerStructureApical = convergencePerStructure[
                        'ApicalDendrite']
                    convergencePerStructureBasal = convergencePerStructure[
                        'BasalDendrite']
                    convergencePerStructureSoma = convergencePerStructure[
                        'Soma']
                    distanceApicalMean = distancesPerStructure[
                        'ApicalDendrite'][0]
                    distanceApicalSD = distancesPerStructure['ApicalDendrite'][
                        1]
                    distanceBasalMean = distancesPerStructure['BasalDendrite'][
                        0]
                    distanceBasalSD = distancesPerStructure['BasalDendrite'][1]
                    line = col + '\t' + preCellType + '\t'
                    line += str(totalSynapses)
                    line += '\t'
                    line += str(distanceTotalMean)
                    line += '\t'
                    line += str(distanceTotalSD)
                    line += '\t'
                    line += str(nrOfConnectedCells)
                    line += '\t'
                    line += str(nrOfAllCells)
                    line += '\t'
                    line += str(convergence)
                    line += '\t'
                    line += str(apicalSynapses)
                    line += '\t'
                    line += str(distanceApicalMean)
                    line += '\t'
                    line += str(distanceApicalSD)
                    line += '\t'
                    line += str(connectionsPerStructureApical)
                    line += '\t'
                    line += str(convergencePerStructureApical)
                    line += '\t'
                    line += str(basalSynapses)
                    line += '\t'
                    line += str(distanceBasalMean)
                    line += '\t'
                    line += str(distanceBasalSD)
                    line += '\t'
                    line += str(connectionsPerStructureBasal)
                    line += '\t'
                    line += str(convergencePerStructureBasal)
                    line += '\t'
                    line += str(somaSynapses)
                    line += '\t'
                    line += str(connectionsPerStructureSoma)
                    line += '\t'
                    line += str(convergencePerStructureSoma)
                    line += '\n'
                    outFile.write(line)


def write_scalar_field(fname=None, scalarField=None):
    if fname is None or scalarField is None:
        err_str = 'Incomplete data! Cannot write scalar field file'
        raise RuntimeError(err_str)

    if not fname.endswith('.am') and not fname.endswith('.AM'):
        fname += '.am'

    with mdbopen(fname, 'w') as outFile:
        extent = scalarField.extent
        bounds = scalarField.boundingBox
        spacing = scalarField.spacing

        header = "# AmiraMesh 3D ASCII 2.0\n\n"
        header += "define Lattice "
        header += str(extent[1] - extent[0] + 1) + " "
        header += str(extent[3] - extent[2] + 1) + " "
        header += str(extent[5] - extent[4] + 1) + '\n'
        header += '\n'
        header += "Parameters {\n"
        header += "\tContent \"" + str(extent[1] - extent[0] + 1) + "x" + str(
            extent[3] - extent[2] + 1) + "x" + str(extent[5] - extent[4] + 1)
        header += " float, uniform coordinates\",\n"
        header += '\tSpacing ' + str(spacing[0]) + ' ' + str(
            spacing[1]) + ' ' + str(spacing[2]) + ',\n'
        header += "\tBoundingBox "
        #        Amira bounding box is measured from the centers of the bounding voxels
        header += str(bounds[0] +
                      0.5 * spacing[0]) + " " + str(bounds[1] -
                                                    0.5 * spacing[0]) + " "
        header += str(bounds[2] +
                      0.5 * spacing[1]) + " " + str(bounds[3] -
                                                    0.5 * spacing[1]) + " "
        header += str(bounds[4] +
                      0.5 * spacing[2]) + " " + str(bounds[5] -
                                                    0.5 * spacing[2]) + " "
        header += '\n'
        header += "\tCoordType \"uniform\"\n"
        header += "}\n"
        header += '\n'
        header += "Lattice { float Data } @1\n"
        header += '\n'
        header += "# Data section follows\n"
        header += "@1\n"
        outFile.write(header)

        for k in range(extent[4], extent[5] + 1):
            for j in range(extent[2], extent[3] + 1):
                for i in range(extent[0], extent[1] + 1):
                    val = scalarField.mesh[(i, j, k)]
                    line = '%.15e \n' % val
                    outFile.write(line)
