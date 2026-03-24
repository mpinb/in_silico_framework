# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''Write out the results of a single connectivity realization or a population of realizations.
'''
from __future__ import absolute_import
from .scalar_field import ScalarField
from .generate_nr_of_cells_spreadsheet import con_file_to_NumberOfConnectedCells_sheet
from config.user.cell_types import EXCITATORY, INHIBITORY
from data_base.dbopen import dbopen
import logging
__author__ = 'Robert Egger'
__date__ = '2012-03-08'
logger = logging.getLogger("ISF").getChild(__name__)

OUT_CELL_TYPES = EXCITATORY + INHIBITORY


def write_landmark_file(fname=None, landmarkList=None):
    '''Write Amira landmark file

    Args:
        fname (str): Name of the output file
        landmarkList (array): List of tuples, each of which holds 3 float coordinates

    Raises:
        RuntimeError: If no file name is given
    '''
    if fname is None:
        err_str = 'No landmark output file name given'
        raise RuntimeError(err_str)


    if not fname.endswith('.landmarkAscii'):
        fname += '.landmarkAscii'

    with dbopen(fname, 'w') as landmarkFile:
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
    '''Write a :ref:`syn_file_format` file, containing all synapses and their corresponding cellID, sectionID and x.
    
    The locations of each synapse are coded by section ID and section x of cell with ID :param:`cellID`.

    Args:
        fname (str): Name of the output file. May or may not contain the suffix `.syn` or `.SYN`
        synapses (dict): Dictionary containing synapse objects. Keys are synapse types, values are lists of synapse objects
        cellID (str): ID of the cell the synapses belong to

    Raises:
        RuntimeError: If any of the input arguments is `None`

    Returns:
        None
    '''
    if fname is None or synapses is None or cellID is None:
        err_str = 'Incomplete data! Cannot write synapse location file'
        raise RuntimeError(err_str)

    if not fname.endswith('.syn') and not fname.endswith('.SYN'):
        fname += '.syn'

    synFormat = None
    with dbopen(fname, 'w') as outputFile:
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


def write_anatomical_realization_map(
        fname=None,
        functionalMap=None,
        anatomicalID=None
        ):
    '''Writes a :ref:`con_file_format` file containing a list of all functional connections.
     
    Connections are tuples of the form: (cell type, presynaptic cell index, synapse index).
    Only valid for an anatomical synapse realization with ID :param:`anatomicalID`.
    Uses :func:`~singlecell_input_mapper.singlecell_input_mapper.generate_nr_of_cells_spreadsheet.con_file_to_NumberOfConnectedCells_sheet` 
    to generate the number of connected cells spreadsheet.

    Args:
        fname (str): Name of the output file
        functionalMap (list): List of tuples, each containing the cell type, presynaptic cell index and synapse index
        anatomicalID (str): ID of the anatomical realization

    Warning:
        A :ref:`con_file_format` file is only valid with a corresponding :ref:`syn_file_format` file.
        See :func:`~write_cell_synapse_locations`

    Returns:
        None. Writes results to disk.
    '''
    if fname is None or functionalMap is None or anatomicalID is None:
        err_str = 'Incomplete data! Cannot write functional realization file'
        raise RuntimeError(err_str)

    if not fname.endswith('.con') and not fname.endswith('.CON'):
        fname += '.con'

    with dbopen(fname, 'w') as outputFile:
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
    # this can be generated out of the :ref:`con_file_format` file.
    # todo: find a less ugly method to do this
    con_file_to_NumberOfConnectedCells_sheet(fname)


def write_sample_connectivity_summary(
        fname=None,
        cellTypeSummaryData=None,
        columnSummaryData=None):
    """Write a summary of a single connectivity realization to a file.
    """
    if fname is None or cellTypeSummaryData is None or columnSummaryData is None:
        err_str = 'Incomplete data! Cannot write results summary file'
        raise RuntimeError(err_str)

    if not fname.endswith('.csv') and not fname.endswith('.CSV'):
        fname += '.csv'

    def _get_structures(summary_data):
        for cell_type in OUT_CELL_TYPES:
            for key, data in summary_data.items():
                entry = data[key] if isinstance(list(data.values())[0], dict) else data
                if cell_type in (entry if isinstance(entry, dict) else summary_data):
                    candidate = entry[cell_type] if isinstance(entry, dict) else summary_data[cell_type]
                    return list(candidate[6].keys())  # synapsesPerStructure keys
        return []

    structures = _get_structures(
        {k: {k2: v2 for k2, v2 in v.items()} if isinstance(list(v.values())[0], (list, tuple)) is False else v
         for k, v in columnSummaryData.items()}
        if columnSummaryData else cellTypeSummaryData
    )

    for ct in OUT_CELL_TYPES:
        if ct in cellTypeSummaryData:
            structures = list(cellTypeSummaryData[ct][6].keys())
            break

    def _make_header(prefix_cols):
        parts = prefix_cols[:]
        parts += ['Number of synapses', 'Mean path length to soma', 'SD path length to soma',
                  'Connected presynaptic cells', 'Total presynaptic cells', 'Convergence']
        for struct in structures:
            parts += [
                f'Number of {struct} synapses',
                f'Mean path length to soma ({struct} synapses)',
                f'SD path length to soma ({struct} synapses)',
                f'Connected presynaptic cells ({struct} synapses)',
                f'Convergence ({struct} synapses)',
            ]
        return '\t'.join(parts) + '\n'

    def _make_line(prefix_values, data):
        totalSynapses        = data[0]
        nrOfConnectedCells   = data[1]
        nrOfAllCells         = data[2]
        convergence          = data[3]
        distanceTotalMean    = data[4]
        distanceTotalSD      = data[5]
        synapsesPerStructure     = data[6]
        connectionsPerStructure  = data[7]
        convergencePerStructure  = data[8]
        distancesPerStructure    = data[9]

        parts = prefix_values[:]
        parts += [str(totalSynapses), str(distanceTotalMean), str(distanceTotalSD),
                  str(nrOfConnectedCells), str(nrOfAllCells), str(convergence)]

        for struct in structures:
            parts.append(str(synapsesPerStructure[struct]))
            if struct in distancesPerStructure:
                parts.append(str(distancesPerStructure[struct][0]))
                parts.append(str(distancesPerStructure[struct][1]))
            parts.append(str(connectionsPerStructure[struct]))
            parts.append(str(convergencePerStructure[struct]))

        return '\t'.join(parts) + '\n'

    with dbopen(fname, 'w') as outFile:
        outFile.write('# connectivity per cell type summary\n')
        outFile.write(_make_header(['Presynaptic cell type']))

        for preCellType in OUT_CELL_TYPES:
            try:
                data = cellTypeSummaryData[preCellType]
            except KeyError:
                logger.warning("Cell type summary data does not contain cell type %s" % preCellType)
                continue
            outFile.write(_make_line([preCellType], data))

        outFile.write('\n')

        outFile.write('# connectivity per column per cell type summary\n')
        outFile.write(_make_header(['Presynaptic column', 'Presynaptic cell type']))

        columns = sorted(columnSummaryData.keys())
        for col in columns:
            for preCellType in OUT_CELL_TYPES:
                try:
                    data = columnSummaryData[col][preCellType]
                    logger.info("Column %s does not contain cell type %s" % (col, preCellType))
                except KeyError:
                    continue
                outFile.write(_make_line([col, preCellType], data))


def write_population_connectivity_summary(
        fname=None,
        populationDistribution=None):
    """Write a summary of populations of connectivity realizations to a file.

    The populationDistribution can be calculated with :func:`~singlecell_input_mapper.singlecell_input_mapper.NetworkMapper._compute_parameter_distribution`
    For each cell type, this method writes a summary on the same attributes for each cell structure as :func:`write_sample_connectivity_summary`, namely:
    
    - Presynaptic cell type
    - Number of synapses
    - Mean path length to soma
    - SD path length to soma
    - Connected presynaptic cells
    - Total presynaptic cells
    - Convergence
    - Number of synapses
    
    In addition, however, it also writes out the standard deviation of these values, taken across network realizations.

    Args:
        fname (str): Name of the output file
        populationDistribution (dict): Dictionary containing the summary data for each cell type
            Must contain at least a key for each presynaptic cell type.
            Values are lists of the form [mean, std] for each of the attributes mentioned above.

    Returns:
        None. Writes the results to disk.
    """
    if fname is None or populationDistribution is None:
        raise RuntimeError('Incomplete data! Cannot write results summary file')

    if not fname.endswith('.csv') and not fname.endswith('.CSV'):
        fname += '.csv'

    # Discover structures from the first present cell type
    structures = []
    for ct in OUT_CELL_TYPES:
        if ct in populationDistribution:
            structures = list(populationDistribution[ct][6].keys())
            break

    def _make_header():
        parts = ['Presynaptic cell type',
                 'Number of synapses', 'STD',
                 'Mean path length to soma', 'STD',
                 'SD path length to soma', 'STD',
                 'Connected presynaptic cells', 'STD',
                 'Total presynaptic cells',
                 'Convergence', 'STD']
        for struct in structures:
            parts += [f'Number of {struct} synapses', 'STD']
            if struct in populationDistribution[next(ct for ct in OUT_CELL_TYPES if ct in populationDistribution)][9]:
                parts += [f'Mean path length to soma ({struct} synapses)', 'STD',
                          f'SD path length to soma ({struct} synapses)', 'STD']
            parts += [f'Connected presynaptic cells ({struct} synapses)', 'STD',
                      f'Convergence ({struct} synapses)', 'STD']
        return '# connectivity per cell type population summary\n' + '\t'.join(parts) + '\n'

    def _make_line(preCellType, data):
        totalSynapses           = data[0]
        nrOfConnectedCells      = data[1]
        nrOfAllCells            = data[2]
        convergence             = data[3]
        distanceTotalMean       = data[4]
        distanceTotalSD         = data[5]
        synapsesPerStructure    = data[6]
        connectionsPerStructure = data[7]
        convergencePerStructure = data[8]
        distancesPerStructure   = data[9]

        parts = [
                preCellType,
                str(totalSynapses[0]),       str(totalSynapses[1]),
                str(distanceTotalMean[0]),   str(distanceTotalMean[1]),
                str(distanceTotalSD[0]),     str(distanceTotalSD[1]),
                str(nrOfConnectedCells[0]),  str(nrOfConnectedCells[1]),
                str(nrOfAllCells[0]),
                str(convergence[0]),         str(convergence[1])
        ]

        for struct in structures:
            synapses = synapsesPerStructure[struct]
            parts += [str(synapses[0]), str(synapses[1])]
            if struct in distancesPerStructure:
                mean, sd = distancesPerStructure[struct]
                parts += [str(mean[0]), str(mean[1]), str(sd[0]), str(sd[1])]
            conns = connectionsPerStructure[struct]
            conv  = convergencePerStructure[struct]
            parts += [str(conns[0]), str(conns[1]), str(conv[0]), str(conv[1])]

        return '\t'.join(parts) + '\n'

    with dbopen(fname, 'w') as outFile:
        outFile.write(_make_header())
        for preCellType in OUT_CELL_TYPES:
            if preCellType not in populationDistribution:
                logger.warning("Population distribution does not contain cell type %s" % preCellType)
                continue
            outFile.write(_make_line(preCellType, populationDistribution[preCellType]))
        outFile.write('\n')


def write_population_and_sample_connectivity_summary(
        fname=None,
        populationDistribution=None,
        cellTypeSummaryData=None,
        columnSummaryData=None):
    """...(docstring unchanged)"""
    if fname is None or populationDistribution is None or cellTypeSummaryData is None or columnSummaryData is None:
        raise RuntimeError('Incomplete data! Cannot write results summary file')

    if not fname.endswith('.csv') and not fname.endswith('.CSV'):
        fname += '.csv'



    # Discover structures from the first present cell type in each dataset
    def _get_structures(summary_data):
        for ct in OUT_CELL_TYPES:
            if ct in summary_data:
                return list(summary_data[ct][6].keys())
        return []

    pop_structures    = _get_structures(populationDistribution)
    sample_structures = _get_structures(cellTypeSummaryData)

    def _pop_header():
        parts = ['Presynaptic cell type',
                 'Number of synapses', 'STD',
                 'Mean path length to soma', 'STD',
                 'SD path length to soma', 'STD',
                 'Connected presynaptic cells', 'STD',
                 'Total presynaptic cells',
                 'Convergence', 'STD']
        for struct in pop_structures:
            parts += [f'Number of {struct} synapses', 'STD']
            if struct in populationDistribution[next(ct for ct in OUT_CELL_TYPES if ct in populationDistribution)][9]:
                parts += [f'Mean path length to soma ({struct} synapses)', 'STD',
                          f'SD path length to soma ({struct} synapses)', 'STD']
            parts += [f'Connected presynaptic cells ({struct} synapses)', 'STD',
                      f'Convergence ({struct} synapses)', 'STD']
        return '# connectivity per cell type population summary\n' + '\t'.join(parts) + '\n'

    def _pop_line(preCellType, data):
        totalSynapses           = data[0]
        nrOfConnectedCells      = data[1]
        nrOfAllCells            = data[2]
        convergence             = data[3]
        distanceTotalMean       = data[4]
        distanceTotalSD         = data[5]
        synapsesPerStructure    = data[6]
        connectionsPerStructure = data[7]
        convergencePerStructure = data[8]
        distancesPerStructure   = data[9]

        parts = [preCellType,
                 str(totalSynapses[0]),      str(totalSynapses[1]),
                 str(distanceTotalMean[0]),  str(distanceTotalMean[1]),
                 str(distanceTotalSD[0]),    str(distanceTotalSD[1]),
                 str(nrOfConnectedCells[0]), str(nrOfConnectedCells[1]),
                 str(nrOfAllCells[0]),
                 str(convergence[0]),        str(convergence[1])]
        for struct in pop_structures:
            synapses = synapsesPerStructure[struct]
            parts += [str(synapses[0]), str(synapses[1])]
            if struct in distancesPerStructure:
                mean, sd = distancesPerStructure[struct]
                parts += [str(mean[0]), str(mean[1]), str(sd[0]), str(sd[1])]
            conns = connectionsPerStructure[struct]
            conv  = convergencePerStructure[struct]
            parts += [str(conns[0]), str(conns[1]), str(conv[0]), str(conv[1])]
        return '\t'.join(parts) + '\n'

    def _sample_header(prefix_cols):
        parts = prefix_cols + ['Number of synapses',
                               'Mean path length to soma', 'SD path length to soma',
                               'Connected presynaptic cells', 'Total presynaptic cells', 'Convergence']
        for struct in sample_structures:
            parts += [f'Number of {struct} synapses']
            if struct in cellTypeSummaryData[next(ct for ct in OUT_CELL_TYPES if ct in cellTypeSummaryData)][9]:
                parts += [f'Mean path length to soma ({struct} synapses)',
                          f'SD path length to soma ({struct} synapses)']
            parts += [f'Connected presynaptic cells ({struct} synapses)',
                      f'Convergence ({struct} synapses)']
        return '\t'.join(parts) + '\n'

    def _sample_line(prefix_values, data):
        totalSynapses           = data[0]
        nrOfConnectedCells      = data[1]
        nrOfAllCells            = data[2]
        convergence             = data[3]
        distanceTotalMean       = data[4]
        distanceTotalSD         = data[5]
        synapsesPerStructure    = data[6]
        connectionsPerStructure = data[7]
        convergencePerStructure = data[8]
        distancesPerStructure   = data[9]

        parts = prefix_values + [str(totalSynapses), str(distanceTotalMean), str(distanceTotalSD),
                                  str(nrOfConnectedCells), str(nrOfAllCells), str(convergence)]
        for struct in sample_structures:
            parts.append(str(synapsesPerStructure[struct]))
            if struct in distancesPerStructure:
                parts += [str(distancesPerStructure[struct][0]),
                          str(distancesPerStructure[struct][1])]
            parts += [str(connectionsPerStructure[struct]),
                      str(convergencePerStructure[struct])]
        return '\t'.join(parts) + '\n'

    with dbopen(fname, 'w') as outFile:
        # Section 1: population summary
        outFile.write(_pop_header())
        for preCellType in OUT_CELL_TYPES:
            if preCellType not in populationDistribution:
                logger.warning("Population distribution does not contain cell type %s" % preCellType)
                continue
            outFile.write(_pop_line(preCellType, populationDistribution[preCellType]))
        outFile.write('\n')

        # Section 2: single-realization per cell type
        outFile.write('# connectivity per cell type representative realization summary\n')
        outFile.write(_sample_header(['Presynaptic cell type']))
        for preCellType in OUT_CELL_TYPES:
            if preCellType not in cellTypeSummaryData:
                logger.warning("Cell type summary data does not contain cell type %s" % preCellType)
                continue
            outFile.write(_sample_line([preCellType], cellTypeSummaryData[preCellType]))
        outFile.write('\n')

        # Section 3: single-realization per column per cell type
        outFile.write('# connectivity per column per cell type summary\n')
        outFile.write(_sample_header(['Presynaptic column', 'Presynaptic cell type']))
        for col in sorted(columnSummaryData.keys()):
            for preCellType in OUT_CELL_TYPES:
                try:
                    data = columnSummaryData[col][preCellType]
                    logger.info("Column %s does not contain cell type %s" % (col, preCellType))
                except KeyError:
                    continue
                outFile.write(_sample_line([col, preCellType], data))


def write_scalar_field(fname=None, scalarField=None):
    """Write a scalar field to an AmiraMesh file.

    These can be visualized in AMIRA, or converted to VTK using :func:`~visualize.vtk.convert_amira_lattice_to_vtk`
    for visualization in VTK-compatible renderers.
    
    Args:
        fname (str): Name of the output file
        scalarField (:class:`~singlecell_input_mapper.singlecell_input_mapper.scalar_field.ScalarField`): 
            Scalar field to be written to disk
        
    Returns:
        None. Writes the results to disk.
    """
    if fname is None or scalarField is None:
        err_str = 'Incomplete data! Cannot write scalar field file'
        raise RuntimeError(err_str)

    if not fname.endswith('.am') and not fname.endswith('.AM'):
        fname += '.am'

    with dbopen(fname, 'w') as outFile:
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
