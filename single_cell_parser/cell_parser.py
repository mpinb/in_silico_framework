'''Read and parse a :py:class:`~single_cell_parser.cell.Cell` object from a NEURON :ref:`hoc_file_format` file.
'''

import warnings, traceback
from neuron import h
import numpy as np
import math
from . import reader
from .cell import PySection, Cell
from . import cell_modify_functions
import logging

__author__  = ["Robert Egger", "Arco Bast"]
__credits__ = ["Robert Egger", "Arco Bast"]
__date__    = "2012-03-08"

logger = logging.getLogger("ISF").getChild(__name__)


class CellParser(object):
    '''Configure a :py:class:`~single_cell_parser.cell.Cell` object from a NEURON hoc file.
    
    This class is used to read a hoc file and set up a :py:class:`~single_cell_parser.cell.Cell` object for single cell simulations.
    It segmentizes the morphology accroding to :cite:t:`hines2001neuron`, and sets the :py:class:`~single_cell_parser.cell.Cell` object's 
    membrane properties, mechanisms, and ion properties based on a :ref:`cell_parameters_format` file.
    
    See also:
        This is not the same class as :py:class:`singlecell_input_mapper.singlecell_input_mapper.cell.CellParser`.
        This class provides biophysical details, such as segmentation, channel mechanisms, and membrane properties.
    
    Attributes:
        hoc_path (str): Path to hoc file
        membraneParams (dict): Membrane parameters
        cell_modify_functions_applied (bool): 
            Whether or not cell modify functions have already been applied. See: :py:meth:`~single_cell_parser.cell_parser.CellParser.apply_cell_modify_functions`
        cell (:py:class:`~single_cell_parser.cell.Cell`): Cell object.
    '''
    #    h = neuron.h
    cell = None

    def __init__(self, hocFilename=''):
        '''
        Args:
            hocFilename (str): Path to :ref:`hoc_file_format` file.
        '''
        if not hocFilename:
            warnings.warn('No hoc file specified')
        self.hoc_path = hocFilename
        #         self.hoc_fname = self.hoc_path.split('/')[-1]

        #        implement parameters to be read from
        #        corresponding membrane file
        #        (analogous to synapse distribution,
        #        every cell could have its own optimized
        #        channel distributions)
        self.membraneParams = {}
        self.cell_modify_functions_applied = False

    def spatialgraph_to_cell(self, parameters, axon=False, scaleFunc=None):
        '''Create a :py:class:`~single_cell_parser.cell.Cell` object from an AMIRA spatial graph in :ref:`hoc_file_format` format.
        
        Reads cell morphology from Amira hoc file and sets up PySections and Cell object.
        
        Args:
            parameters (:py:class:`~sumatra.parameters.NTParameterSet`): Neuron biophysical parameters, read from a :ref:`cell_parameters_format` file.
            axon (bool): Whether or not to add an axon initial segment (AIS). AIS creation is according to :cite:t:`Hay_Schuermann_Markram_Segev_2013`.
            scaleFunc (callable, optional): Optional function object that scales dendritic diameters.
                **Deprecated**: This argument is deprecated and will be removed in a future version.
        
        .. deprecated:: 0.1.0
            The `scaleFunc` argument is deprecated and will be removed in a future version.
            To ensure reproducability, scaleFunc should be specified in the parameters, as 
            described in :py:mod:`~single_cell_parser.cell_modify_funs`
        
        '''
        edgeList = reader.read_hoc_file(self.hoc_path)
        #part1 = self.hoc_fname.split('_')[0]
        #part2 = self.hoc_fname.split('_')[1]
        #part3 = self.hoc_fname.split('.')[-2]
        self.cell = Cell()
        #self.cell.id = '_'.join([part1, part2, part3])
        self.cell.hoc_path = self.hoc_path  # sotre path to hoc_file in cell object

        # 1. Create all Sections
        for secID, edge in enumerate(edgeList):
            sec = PySection(edge.hocLabel, self.cell.id, edge.label)
            sec.secID = secID
            if sec.label != 'Soma':
                sec.parentx = edge.parentConnect
                sec.parentID = edge.parentID
            sec.set_3d_geometry(edge.edgePts, edge.diameterList)
            self.cell.sections.append(sec)
            if sec.label == 'Soma':
                self.cell.soma = sec

        ## add axon initial segment, myelin and nodes
        if axon:
            self._create_ais_Hay2013()
            # self._create_ais()

        ## add dendritic spines (Rieke)
        try:
            if 'rieke_spines' in list(
                    parameters.spatialgraph_modify_functions.keys()):
                self.rieke_spines(parameters)
            else:
                logger.info("No spines are being added...")
        except AttributeError:
            pass

        # 2. Connect sections and create structures dict
        branchRoots = []
        for sec in self.cell.sections:
            if sec.label != 'Soma':
                if self.cell.sections[sec.parentID].label == 'Soma':
                    #                    unfortunately, necessary to enforce that nothing
                    #                    is connected to soma(0) b/c of ri computation in NEURON
                    sec.parentx = 0.5
                sec.connect(self.cell.sections[sec.parentID], sec.parentx, 0.0)
                sr = h.SectionRef(sec=sec)
                sec.parent = sr.parent
                if sec.parent.label == 'Soma':
                    branchRoots.append(sec)
            if sec.label not in self.cell.structures:
                self.cell.structures[sec.label] = [sec]
            else:
                self.cell.structures[sec.label].append(sec)

        # create trees
        self.cell.tree = h.SectionList()
        self.cell.tree.wholetree(sec=self.cell.soma)
        for root in branchRoots:
            if root.label not in self.cell.branches:
                branch = h.SectionList()
                branch.subtree(sec=root)
                self.cell.branches[root.label] = [branch]
            else:
                branch = h.SectionList()
                branch.subtree(sec=root)
                self.cell.branches[root.label].append(branch)

        somaList = h.SectionList()
        somaList.append(sec=self.cell.soma)
        self.cell.branches['Soma'] = [somaList]

        # scale dendrites if necessary
        if scaleFunc:
            warnings.warn(
                'Keyword scaleFunc is deprecated! ' +
                'New: To ensure reproducability, scaleFunc should be ' +
                'specified in the parameters, as described in single_cell_parser.cell_modify_funs'
            )
            scaleFunc(self.cell)

    def set_up_biophysics(self, parameters, full=False):
        '''Initialize membrane properties.
        
        Default method for determining the compartment sizes for NEURON simulation, initializing membrane properties, and mechanisms.
        Properties are constants that are defined for an entire structure. Mechanisms have specific densities (not always uniform), and can be transient.
        Poperties are added to the section by executing the NEURON command ``sec.<property>=<value>``.
        
        - Properties:
            - :math:`C_m` (see :py:meth:`insert_membrane_properties`)
            - :math:`R_a` (see :py:meth:`insert_membrane_properties`)
            - ion properties (see :py:meth:`_insert_ion_properties`)
        - Mechanisms:
            - range mechanisms (see :py:meth:`insert_range_mechanisms`)
            
        The workflow is as follows:
        
        1. Add membrane properties to all structures (see :py:meth:`insert_membrane_properties`).
        2. Determine the number of segments for each structure (see :py:meth:`determine_nseg`).
        3. Add range mechanisms to all structures (see :py:meth:`insert_range_mechanisms`).
        4. Add ion properties to all structures (see :py:meth:`_insert_ion_properties`), if the ``ion`` keyword is present in the :ref:`cell_parameters_format` file.
        5. Add spines, if the ``spines`` keyword is present in the :ref:`cell_parameters_format` file.
            5.1 Add passive spines if ``pas`` is present in the range mechanisms (see :py:meth:`_add_spines`).
            5.2 Add passive spines to anomalously rectifying membrane if ``ar`` is present in the range mechanisms (see :py:meth:`_add_spines_ar`).
                
        Args:
            parameters (:py:class:`~sumatra.parameters.NTParameterSet`): Neuron biophysical parameters, read from a :ref:`cell_parameters_format` file.
            full (bool): Whether or not to use full spatial discretization.
        '''
        for label in list(parameters.keys()):
            if label == 'filename':
                continue
            if label == 'cell_modify_functions':
                continue
            if label == 'spatialgraph_modify_functions':
                continue
            if label == 'discretization':
                continue
            #if not 'rieke_spines' in parameters.spatialgraph_modify_functions.keys():
            #    if label == 'SpineHead' or label == 'SpineNeck':
            #        continue
            logger.info('    Adding membrane properties to %s' % label)
            self.insert_membrane_properties(label, parameters[label].properties)

        #  spatial discretization
        logger.info('    Setting up spatial discretization...')
        if 'discretization' in parameters:
            f = parameters['discretization']['f']
            max_seg_length = parameters['discretization']['max_seg_length']
            self.determine_nseg(f=f, max_seg_length=max_seg_length, full=full)
        else:
            self.determine_nseg(full=full)

        for label in list(parameters.keys()):
            if label == 'filename':
                continue
            if label == 'cell_modify_functions':
                continue
            if label == 'spatialgraph_modify_functions':
                continue
            if label == 'discretization':
                continue
            try:
                if not 'rieke_spines' in list(
                        parameters.spatialgraph_modify_functions.keys()):
                    if label == 'SpineHead' or label == 'SpineNeck':
                        continue
            except AttributeError:
                pass
            
            logger.info('    Adding membrane range mechanisms to %s' % label)
            self.insert_range_mechanisms(
                label,
                parameters[label].mechanisms.range)
            
            if 'ions' in parameters[label].properties:
                self._insert_ion_properties(
                    label,
                    parameters[label].properties.ions)
            
            #  add spines if desired
            if 'pas' in parameters[label].mechanisms.range\
                and 'spines' in parameters[label].properties:
                self._add_spines(
                    label, 
                    parameters[label].properties.spines)
            if 'ar' in parameters[label].mechanisms.range\
                and 'spines' in parameters[label].properties:
                self._add_spines_ar(
                    label, 
                    parameters[label].properties.spines)

        self.cell.neuron_param = parameters

    def apply_cell_modify_functions(self, parameters):
        """Apply cell modify functions to the cell object.
        
        Cell modify functions that appear in the :ref:`cell_parameters_format` file are applied to the cell object.
        For a list of possible cell modify functions, refer to :py:mod:`~single_cell_parser.cell_modify_functions`.
        
        Args:
            parameters (:py:class:`~sumatra.parameters.NTParameterSet`): Neuron parameters, read from a :ref:`cell_parameters_format` file.
        """
        if 'cell_modify_functions' in list(parameters.keys()):
            if self.cell_modify_functions_applied == True:
                logger.warning('Cell modify functions have already been applied. We '+\
                'are now modifying the cell again. Please doublecheck, whether '+\
                'this is intended. This should not occur, if the cell is setup '+\
                'up using the recommended way, i.e. by calling '+\
                'single_cell_parser.create_cell')
            for funname in list(parameters.cell_modify_functions.keys()):
                kwargs = parameters.cell_modify_functions[funname]
                logger.info('Applying cell_modify_function {} with parameters {}'.
                         format(funname, str(kwargs)))
                fun = cell_modify_functions.get(funname)
                self.cell = fun(self.cell, **kwargs)
            self.cell_modify_functions_applied = True
        else:
            logger.info('No cell_modify_functions to apply')

        self.cell.neuron_param = parameters

    def get_cell(self):
        '''Returns cell if it is set up for simulations.
        
        Raises:
            RuntimeError: If cell is not set up.
            
        Returns:
            :py:class:`~single_cell_parser.cell.Cell`: Cell object.
        '''
        if self.cell is None:
            raise RuntimeError('Trying to start simulation with empty morphology')
        return self.cell

    def insert_membrane_properties(self, label, props):
        '''Inserts membrane properties into all structures named as :paramref:`label`.
        
        Args:
            label (str): Label of the structure.
            props (dict | :py:class:`~sumatra.parameters.NTParameterSet`): Membrane properties. 
                Keys named ``spines`` or ``ions`` are ignored, 
                as they are taken care of by :py:meth:`insert_range_mechanisms` and :py:meth:`_insert_ion_properties`.
                
        Raises:
            RuntimeError: If the structure has not been parsed from the :ref:`hoc_file_format` file yet.
        '''
        if self.cell is None:
            raise RuntimeError(
                'Trying to insert membrane properties into empty morphology')
        if label != 'Soma' and label not in self.cell.structures:
            errstr = 'Trying to insert membrane properties, but %s has not' % label\
                               +' yet been parsed as hoc'
            raise RuntimeError(errstr)
        elif label == 'Soma' and not self.cell.soma:
            errstr = 'Trying to insert membrane properties, but %s has not' % label\
                               +' yet been parsed as hoc'
            raise RuntimeError(errstr)

        propStrings = []
        for prop in list(props.keys()):
            if prop == 'spines' or prop == 'ions':
                continue
            s = prop + '=' + str(props[prop])
            propStrings.append(s)

        for sec in self.cell.structures[label]:
            for s in propStrings:
                exec('sec.' + s)

    def insert_range_mechanisms(self, label, mechs):
        r'''Inserts range mechanisms into all structures named as :paramref:`label`.
        
        Range mechanism specifications can be found in :py:mod:`mechanisms`.
        
        Args:
            label (str): Label of the structure.
            mechs (:py:class:`~sumatra.parameters.NTParameterSet`): Range mechanisms. Must contain the key ``spatial`` to define the spatial distribution. Possible values for spatial distributions are given below.
            
        Raises:
            RuntimeError: If the structure has not been parsed from the :ref:`hoc_file_format` file yet.
            NotImplementedError: If the spatial distribution is not implemented.
                
        The following table lists the possible spatial keywords of ``mech``, the additional keys each spatial key requires, and the corresponding math equations.

        .. table:: Possible spatial keywords of ``mech``, the additional keys each spatial key requires, and the corresponding math equations.

            +------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------+
            | Spatial Key            | Additional Keys                                                 | Math Equation                                                                                                                       |
            +========================+=================================================================+=====================================================================================================================================+
            | uniform                | None                                                            | :math:`y = c`                                                                                                                       |
            +------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------+
            | linear                 | ``slope``, ``offset``                                           | :math:`y = \text{slope} \cdot x + \text{offset}`                                                                                    |
            +------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------+
            | linear_capped          | ``prox_value``, ``dist_value``, ``dist_value_distance``         | :math:`y = \min(\text{prox_value} + \frac{\text{dist_value} - \text{prox_value}}{\text{dist_value_distance}} x, \text{dist_value})` |
            +------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------+
            | exponential            | ``offset``, ``linScale``, ``_lambda``, ``xOffset``              | :math:`y = \text{offset} + \text{linScale} \cdot e^{-\frac{x - \text{xOffset}}{\lambda}}`                                           |
            +------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------+
            | exponential_by_z_dist  | ``offset``, ``linScale``, ``_lambda``, ``xOffset``              | :math:`y = \text{offset} + \text{linScale} \cdot e^{-\frac{z - \text{xOffset}}{\lambda}}`                                           |
            +------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------+
            | capped_exponential     | ``offset``, ``linScale``, ``_lambda``, ``xOffset``, ``max_g``   | :math:`y = \min(\text{offset} + \text{linScale} \cdot e^{-\frac{x - \text{xOffset}}{\lambda}}, \text{max_g})`                       |
            +------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------+
            | sigmoid                | ``offset``, ``linScale``, ``xOffset``, ``width``                | :math:`y = \text{offset} + \frac{\text{linScale}}{1 + e^{\frac{x - \text{xOffset}}{\text{width}}}}`                                 |
            +------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------+
            | uniform_range          | ``begin``, ``end``, ``outsidescale``, ``outsidescale_sections`` | :math:`y = c` for :math:`\text{begin} \leq x \leq \text{end}`, :math:`y = c \cdot \text{outsidescale}` otherwise                    |
            +------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------+

        '''
        if self.cell is None:
            raise RuntimeError(
                'Trying to insert membrane properties into empty morphology')
        if label != 'Soma' and label not in self.cell.structures:
            errstr = 'Trying to insert membrane properties, but %s has not' % label\
                               +' yet been parsed as hoc'
            raise RuntimeError(errstr)
        elif label == 'Soma' and not self.cell.soma:
            errstr = 'Trying to insert membrane properties, but %s has not' % label\
                               +' yet been parsed as hoc'
            raise RuntimeError(errstr)

        for mechName in list(mechs.keys()):
            mech = mechs[mechName]
            logger.info('        Inserting mechanism %s with spatial distribution %s' %(mechName, mech.spatial))
            
            if mech.spatial == 'uniform':
                ''' spatially uniform distribution'''
                paramStrings = []
                for param in list(mech.keys()):
                    if param == 'spatial':
                        continue
                    s = param + '=' + str(mech[param])
                    paramStrings.append(s)
                for sec in self.cell.structures[label]:
                    # sec are neuron sections, i.e. __nrnsec__0x-----
                    try:
                        sec.insert(mechName)
                    except ValueError as e:
                        logger.error(
                            "Could not insert range mechanism {} in label {}\n\
                            NEURON could not find range mechanism with name: {}.\n\
                            Did you build and import the mechanisms? \
                            If you are working on a distributed cluster, you should import the mechanisms on the server side as well.".format(mechName, label, mechName))
                        logger.error(traceback.format_exc())
                        raise e
                    for seg in sec:
                        for s in paramStrings:
                            if not '_ion' in mechName:
                                s = '.'.join(('seg', mechName, s))
                                try:
                                    exec(s)
                                except ValueError as e:
                                    logger.error(
                                        "NEURON Could not set range mechanism parameter {} in label {}\n Tried exectuing: {}.".format(mechName, label, s))
                                    logger.error(traceback.format_exc())
                                    raise e
                            else:
                                sec.push()
                                exec(s)
                                h.pop_section()

            elif mech.spatial == 'linear':
                ''' spatially linear distribution with negative slope'''
                maxDist = self.cell.max_distance(label)
                #                set origin to 0 of first branch with this label
                if label == 'Soma':
                    silent = h.distance(0, 0.0, sec=self.cell.soma)
                else:
                    for sec in self.cell.sections:
                        if sec.label != label:
                            continue
                        if sec.parent.label == 'Soma':
                            silent = h.distance(0, 0.0, sec=sec)
                            break
                relDistance = False
                if mech['distance'] == 'relative':
                    relDistance = True
                slope = mech['slope']
                offset = mech['offset']
                for sec in self.cell.structures[label]:
                    sec.insert(mechName)
                    for seg in sec:
                        paramStrings = []
                        for param in list(mech.keys()):
                            if param == 'spatial' or param == 'distance' or param == 'slope'\
                            or param == 'offset':
                                continue
                            dist = self.cell.distance_to_soma(sec, seg.x)
                            if relDistance:
                                dist = dist / maxDist
                            #rangeVarVal = mech[param]*(dist*slope + offset)
                            rangeVarVal = max(mech[param] * (dist * slope + 1),
                                              mech[param] * offset)
                            s = param + '=' + str(rangeVarVal)
                            paramStrings.append(s)
                        for s in paramStrings:
                            s = '.'.join(('seg', mechName, s))
                            exec(s)
                            
            elif mech.spatial == 'linear_capped':
                ''' spatially linear distribution which reaches a constant value after a specified soma distance'''
                maxDist = self.cell.max_distance(label)
                #                set origin to 0 of first branch with this label
                if label == 'Soma':
                    silent = h.distance(0, 0.0, sec=self.cell.soma)
                else:
                    for sec in self.cell.sections:
                        if sec.label != label:
                            continue
                        if sec.parent.label == 'Soma':
                            silent = h.distance(0, 0.0, sec=sec)
                            break
                relDistance = False
                if mech['distance'] == 'relative':
                    relDistance = True
                param_name = mech['param_name']
                prox_value = mech['prox_value']
                dist_value = mech['dist_value']
                dist_value_distance = mech['dist_value_distance']
                for sec in self.cell.structures[label]:
                    sec.insert(mechName)
                    for seg in sec:
                        paramStrings = []
                        dist = self.cell.distance_to_soma(sec, seg.x)
                        if relDistance:
                            dist = dist / maxDist
                        if dist >= dist_value_distance:
                            value = dist_value
                        else:
                            value = prox_value+(dist_value-prox_value)/dist_value_distance*dist
                        s = param_name + '=' + str(value)
                        paramStrings.append(s)
                        s = '.'.join(('seg', mechName, s))
                        exec(s)
                        
            elif mech.spatial == 'exponential':
                ''' spatially exponential distribution:
                f(x) = offset + linScale*exp(_lambda*(x-xOffset))'''
                maxDist = self.cell.max_distance(label)
                #                set origin to 0 of first branch with this label
                if label == 'Soma':
                    silent = h.distance(0, 0.0, sec=self.cell.soma)
                else:
                    for sec in self.cell.sections:
                        if sec.label != label:
                            continue
                        if sec.parent.label == 'Soma':
                            silent = h.distance(0, 0.0, sec=sec)
                            break
                relDistance = False
                if mech['distance'] == 'relative':
                    relDistance = True
                offset = mech['offset']
                linScale = mech['linScale']
                _lambda = mech['_lambda']
                xOffset = mech['xOffset']
                for sec in self.cell.structures[label]:
                    sec.insert(mechName)
                    for seg in sec:
                        paramStrings = []
                        for param in list(mech.keys()):
                            if param == 'spatial' or param == 'distance' or param == 'offset'\
                            or param == 'linScale' or param == '_lambda' or param == 'xOffset':
                                continue
                            dist = h.distance(seg.x, sec=sec)
                            if relDistance:
                                dist = dist / maxDist
                            rangeVarVal = mech[param] * (
                                offset + linScale * np.exp(_lambda *
                                                           (dist - xOffset)))
                            s = param + '=' + str(rangeVarVal)
                            paramStrings.append(s)
                        for s in paramStrings:
                            s = '.'.join(('seg', mechName, s))
                            exec(s)

            # exponential distribution in the apical dendrite based on the distance by z
            elif mech.spatial == 'exponential_by_z_dist':
                ''' spatially exponential distribution:
                f(x) = offset + linScale*exp(_lambda*(x-xOffset))'''
                maxDist = self.cell.max_distance(label)
                #                set origin to 0 of first branch with this label
                if label == 'Soma':
                    silent = h.distance(0, 0.0, sec=self.cell.soma)
                else:
                    for sec in self.cell.sections:
                        if sec.label != label:
                            continue
                        if sec.parent.label == 'Soma':
                            silent = h.distance(0, 0.0, sec=sec)
                            break
                relDistance = False
                if mech['distance'] == 'relative':
                    relDistance = True
                offset = mech['offset']
                linScale = mech['linScale']
                _lambda = mech['_lambda']
                xOffset = mech['xOffset']
                for sec in self.cell.structures[label]:
                    sec.insert(mechName)
                    if label == 'ApicalDendrite':
                        relPts_list = sec.relPts
                        mid_soma = int(self.cell.soma.nrOfPts / 2)
                        z_distance_per_relPts = [
                            sec.pts[i][2] - self.cell.soma.pts[mid_soma][2]
                            for i in range(len(relPts_list))
                        ]
                    for seg in sec:
                        paramStrings = []
                        for param in list(mech.keys()):
                            if param == 'spatial' or param == 'distance' or param == 'offset'\
                            or param == 'linScale' or param == '_lambda' or param == 'xOffset':
                                continue
                            if label == 'ApicalDendrite':
                                dist = np.interp(seg.x, relPts_list,
                                                 z_distance_per_relPts)
                            else:
                                dist = h.distance(seg.x, sec=sec)
                            if relDistance:
                                dist = dist / maxDist
                            if not relDistance:
                                dist = dist / 1000
                            rangeVarVal = mech[param] * (
                                offset + linScale * np.exp(_lambda *
                                                           (dist - xOffset)))
                            s = param + '=' + str(rangeVarVal)
                            paramStrings.append(s)
                        for s in paramStrings:
                            s = '.'.join(('seg', mechName, s))
                            exec(s)

            elif mech.spatial == 'capped_exponential':
                ''' spatially exponential distribution until a maximum conductance, then uniform:
                exponential function: f(x) = offset + linScale*exp(_lambda*(x-xOffset))'''
                maxDist = self.cell.max_distance(label)
                #                set origin to 0 of first branch with this label
                if label == 'Soma':
                    silent = h.distance(0, 0.0, sec=self.cell.soma)
                else:
                    for sec in self.cell.sections:
                        if sec.label != label:
                            continue
                        if sec.parent.label == 'Soma':
                            silent = h.distance(0, 0.0, sec=sec)
                            break
                relDistance = False
                if mech['distance'] == 'relative':
                    relDistance = True
                offset = mech['offset']
                linScale = mech['linScale']
                _lambda = mech['_lambda']
                xOffset = mech['xOffset']
                max_g = mech['max_g']
                for sec in self.cell.structures[label]:
                    sec.insert(mechName)
                    for seg in sec:
                        paramStrings = []
                        for param in list(mech.keys()):
                            if param == 'spatial' or param == 'distance' or param == 'offset' or param == 'max_g'\
                            or param == 'linScale' or param == '_lambda' or param == 'xOffset':
                                continue
                            dist = h.distance(seg.x, sec=sec)
                            if relDistance:
                                dist = dist / maxDist
                            rangeVarVal = mech[param] * (
                                offset + linScale * np.exp(_lambda *
                                                           (dist - xOffset)))
                            if rangeVarVal < max_g:
                                s = param + '=' + str(rangeVarVal)
                                paramStrings.append(s)
                            elif rangeVarVal >= max_g:
                                s = param + '=' + str(max_g)
                                paramStrings.append(s)
                        for s in paramStrings:
                            s = '.'.join(('seg', mechName, s))
                            exec(s)

            elif mech.spatial == 'sigmoid':
                ''' spatially sigmoid distribution:
                f(x) = offset + linScale/(1+exp((x-xOffset)/width))'''
                maxDist = self.cell.max_distance(label)
                #                set origin to 0 of first branch with this label
                if label == 'Soma':
                    silent = h.distance(0, 0.0, sec=self.cell.soma)
                else:
                    for sec in self.cell.sections:
                        if sec.label != label:
                            continue
                        if sec.parent.label == 'Soma':
                            silent = h.distance(0, 0.0, sec=sec)
                            break
                relDistance = False
                if mech['distance'] == 'relative':
                    relDistance = True
                offset = mech['offset']
                linScale = mech['linScale']
                xOffset = mech['xOffset']
                width = mech['width']
                for sec in self.cell.structures[label]:
                    sec.insert(mechName)
                    for seg in sec:
                        paramStrings = []
                        for param in list(mech.keys()):
                            if param == 'spatial' or param == 'distance' or param == 'offset'\
                            or param == 'linScale' or param == 'xOffset' or param == 'width':
                                continue
                            dist = h.distance(seg.x, sec=sec)
                            if relDistance:
                                dist = dist / maxDist
                            rangeVarVal = mech[param] * (
                                offset + linScale / (1 + np.exp(
                                    (dist - xOffset) / width)))
                            s = param + '=' + str(rangeVarVal)
                            paramStrings.append(s)
                        for s in paramStrings:
                            s = '.'.join(('seg', mechName, s))
                            exec(s)

            elif mech.spatial == 'uniform_range':
                ''' spatially piece-wise constant distribution
                (constant between begin and end, constant scaled value
                outside of begin and end'''
                #                set origin to 0 of first branch with this label
                if label == 'Soma':
                    silent = h.distance(0, 0.0, sec=self.cell.soma)
                else:
                    for sec in self.cell.sections:
                        if sec.label != label:
                            continue
                        if sec.parent.label == 'Soma':
                            silent = h.distance(0, 0.0, sec=sec)
                            break
                begin = mech['begin']
                end = mech['end']
                outsideScale = mech['outsidescale']
                if 'outsidescale_sections' in list(mech.keys()):
                    outsideScale_sections = mech['outsidescale_sections']
                else:
                    outsideScale_sections = []
                for sec in self.cell.structures[label]:
                    secID = self.cell.sections.index(sec)
                    sec.insert(mechName)
                    for seg in sec:
                        paramStrings = []
                        for param in list(mech.keys()):
                            if param == 'spatial' or param == 'begin' or param == 'end'\
                            or param == 'outsidescale' or param == 'outsidescale_sections':
                                continue
                            dist = h.distance(seg.x, sec=sec)
                            if secID in outsideScale_sections:
                                # logger.info('setting section {} to outsidescale'.format(secID))
                                rangeVarVal = mech[param] * outsideScale
                            elif begin <= dist <= end:
                                rangeVarVal = mech[param]
                            else:
                                rangeVarVal = mech[param] * outsideScale
                            s = param + '=' + str(rangeVarVal)
                            paramStrings.append(s)
                        for s in paramStrings:
                            s = '.'.join(('seg', mechName, s))
                            exec(s)

            else:
                errstr = 'Invalid distribution of mechanisms: \"%s\"' % mech.spatial
                raise NotImplementedError(errstr)

    def update_range_mechanisms(self, label, updateMechName, mechs):
        '''Updates range mechanism :paramref:`updateMechName` in all structures named as :paramref:`label`.
        
        This method is essentially the same as insert_range_mechanisms, but does not
        insert mechanisms. Instead assumes they're already present.
        
        Used during parameter variations; e.g. for optimization and exploration of neuron models (see :py:mod:`biophysics_fitting`).
        
        Args:
            label (str): Label of the structure.
            updateMechName (str): Name of the mechanism to update.
            mechs (:py:class:`~sumatra.parameters.NTParameterSet`): Range mechanisms. Must contain the key ``spatial`` to define the spatial distribution. Possible values for spatial distributions are given in :py:meth:`insert_range_mechanisms`.
            
        Raises:
            RuntimeError: If the structure has not been parsed from the :ref:`hoc_file_format` file yet.
            NotImplementedError: If the spatial distribution is not implemented.
        '''
        if self.cell is None:
            raise RuntimeError(
                'Trying to insert membrane properties into empty morphology')

        mech = mechs[updateMechName]
        if mech.spatial == 'uniform':
            ''' spatially uniform distribution'''
            paramStrings = []
            for param in list(mech.keys()):
                if param == 'spatial':
                    continue
                s = param + '=' + str(mech[param])
                paramStrings.append(s)
            for sec in self.cell.structures[label]:
                for seg in sec:
                    present = 0
                    for mech in seg:
                        if mech.name() == updateMechName:
                            present = 1
                            break
                    if not present:
                        errstr = 'Trying to update non-existing mechanism %s in section %s' % (
                            updateMechName, sec.name())
                        raise RuntimeError(errstr)
                    for s in paramStrings:
                        s = '.'.join(('seg', updateMechName, s))
                        exec(s)
        else:
            errstr = 'Invalid distribution of mechanisms: \"%s\"' % mech.spatial
            raise NotImplementedError(errstr)

    def _insert_ion_properties(self, label, ionParam):
        '''Inserts ion properties into all structures named as :paramref:`label`
        
        Args:
            label (str): Label of the structure.
            ionParam (:py:class:`~sumatra.parameters.NTParameterSet`): Ion properties. See :ref:`cell_parameters_format` for an example.
        '''
        if self.cell is None:
            raise RuntimeError(
                'Trying to insert membrane properties into empty morphology')
        if label != 'Soma' and label not in self.cell.structures:
            errstr = 'Trying to insert membrane properties, but %s has not' % label\
                               +' yet been parsed as hoc'
            raise RuntimeError(errstr)
        elif label == 'Soma' and not self.cell.soma:
            errstr = 'Trying to insert membrane properties, but %s has not' % label\
                               +' yet been parsed as hoc'
            raise RuntimeError(errstr)

        propStrings = []
        for ion in list(ionParam.keys()):
            s = ion + '=' + str(ionParam[ion])
            propStrings.append(s)

        for sec in self.cell.structures[label]:
            for s in propStrings:
                exec('sec.' + s)

    def _add_spines(self, label, spineParam):
        '''Adds passive spines to the membrane.
    
        Spines are added according to spine parameters for individual (dendritic) structures
        by scaling :math:`C_m` and :math:`R_m` by :math:`F` and :math:`1/F` respectively, where
    
        .. math::
            
            F = 1 + \\frac{A_{spines}}{A_{dend}}
    
        Precise morphological effects of the spines are not considered, only their effect on membrane capacitance and resistance.
    
        See also:
            :cite:t:`Koch_Segev_1998`
        '''
        if self.cell is None:
            raise RuntimeError(
                'Trying to insert membrane properties into empty morphology')
        if label != 'Soma' and label not in self.cell.structures:
            errstr = 'Trying to insert membrane properties, but %s has not' % label\
                               +' yet been parsed as hoc'
            raise RuntimeError(errstr)
        elif label == 'Soma' and not self.cell.soma:
            errstr = 'Trying to insert membrane properties, but %s has not' % label\
                               +' yet been parsed as hoc'
            raise RuntimeError(errstr)

        spineDens = spineParam.density
        spineArea = spineParam.area

        for sec in self.cell.structures[label]:
            dendArea = sec.area
            addtlArea = spineArea * spineDens * sec.L
            F = 1.0 + addtlArea / dendArea
            sec.cm = sec.cm * F
            for seg in sec:
                seg.g_pas = seg.g_pas * F

    def _add_spines_ar(self, label, spineParam):
        r'''Adds passive spines to anomalously rectifying membrane :cite:`Waters_Helmchen_2006`.
        
        Spines are added according to spine parameters for individual (dendritic) structures
        by scaling :math:`C_m` and :math:`R_{N,0}` by :math:`F` and :math:`1/F` respectively, where
        
        .. math::
            
            F = 1 + \\frac{A_{spines}}{A_{dend}}
            
        Precise morphological effects of the spines are not considered, only their effect on membrane capacitance and resistance. 
        '''
        if self.cell is None:
            raise RuntimeError(
                'Trying to insert membrane properties into empty morphology')
        if label != 'Soma' and label not in self.cell.structures:
            errstr = 'Trying to insert membrane properties, but %s has not' % label\
                               +' yet been parsed as hoc'
            raise RuntimeError(errstr)
        elif label == 'Soma' and not self.cell.soma:
            errstr = 'Trying to insert membrane properties, but %s has not' % label\
                               +' yet been parsed as hoc'
            raise RuntimeError(errstr)

        spineDens = spineParam.density
        spineArea = spineParam.area

        for sec in self.cell.structures[label]:
            dendArea = sec.area
            addtlArea = spineArea * spineDens * sec.L
            F = 1.0 + addtlArea / dendArea
            sec.cm = sec.cm * F
            for seg in sec:
                seg.g0_ar = seg.g0_ar * F
               # seg.c_ar = seg.c_ar*F*F  # quadratic term

    def insert_passive_membrane(self, label):
        """Set up a passive membrane with default values.
        
        Sets up the cell structure :paramref:`label` with a passive membrane that has the following properties:
        
        * :math:`R_a = 200 \\Omega \\cdot cm`
        * :math:`C_m = 0.75 \\mu F/cm^2`
        * :math:`g_{pas} = 0.00025 S/cm^2`
        * :math:`E_{pas} = -60 mV`
        """
        if self.cell is None:
            raise RuntimeError('Trying to insert membrane properties into empty morphology')
        if label != 'Soma' and label not in self.cell.branches:
            errstr = 'Trying to insert membrane properties, but %s has not' % label\
                               +' yet been parsed as hoc'
            raise RuntimeError(errstr)
        elif label == 'Soma' and not self.cell.soma:
            errstr = 'Trying to insert membrane properties, but %s has not' % label\
                               +' yet been parsed as hoc'
            raise RuntimeError(errstr)

        for branch in self.cell.branches[label]:
            for sec in branch:
                sec.insert('pas')
                sec.Ra = 200.0
                sec.cm = 0.75
                for seg in sec:
                    seg.pas.g = 0.00025
                    seg.pas.e = -60.0

    def insert_hh_membrane(self, label):
        """Set up a Hodgkin-Huxley membrane with default values.
        
        Sets up the cell structure :paramref:`label` with a Hodgkin-Huxley membrane that has the following properties:
        
        - :math:`\\bar{g}_{L} = 0.0003 \\, S/cm^2`
        - :math:`E_{L} = -54.3 \\, mV`
        - Soma:
        
            - :math:`\\bar{g}_{Na} = 0.003 \\, S/cm^2`
            - :math:`\\bar{g}_{K} = 0.01 \\, S/cm^2`
            
        - Axon:
        
            - :math:`\\bar{g}_{Na} = 3.0 \\, S/cm^2`
            - :math:`\\bar{g}_{K} = 0.0 \\, S/cm^2`
            
        - Dendrite:
        
            - :math:`\\bar{g}_{Na} = 0.003 \\, S/cm^2`
            - :math:`\\bar{g}_{K} = 0.01 \\, S/cm^2`
        
        """
        if self.cell is None:
            raise RuntimeError(
                'Trying to insert membrane properties into empty morphology')
        if label not in self.cell.branches:
            errstr = 'Trying to insert membrane properties, but %s has not' % label\
                               +' yet been parsed as hoc'
            raise RuntimeError(errstr)

        for branch in self.cell.branches[label]:
            for sec in branch:
                sec.insert('hh')
                if label == 'Soma':
                    for seg in sec:
                        seg.hh.gnabar = 0.003
                        seg.hh.gkbar = 0.01
                        seg.hh.gl = 0.0003
                        seg.hh.el = -54.3
                elif label == 'Axon':
                    for seg in sec:
                        seg.hh.gnabar = 3.0
                        seg.hh.gkbar = 0.0
                        seg.hh.gl = 0.0003
                        seg.hh.el = -54.3
                else:
                    for seg in sec:
                        seg.hh.gnabar = 0.003
                        seg.hh.gkbar = 0.01
                        seg.hh.gl = 0.0003
                        seg.hh.el = -54.3

    def determine_nseg(self, f=100.0, full=False, max_seg_length=None):
        '''Determine the number of segments for each section according to the d-lambda rule.

        Args:
            f (float, optional): frequency used for determining discretization. Default is 100.0 Hz.
            full (bool, optional): Whether or not to use full spatial discretization (one segment per morphology point). Default is False.
            max_seg_length (float, optional): Maximum segment length. Default is None.
            
        Note:
            The d-lambda rule predicates the spatial grid on the AC length constant :math:`\\lambda_f`
            computed at a frequency :math:`f` that is high enough for transmembrane current to be primarily
            capacitive, yet still within the range of frequencies relevant to neuronal function.
            :cite:t:`hines2001neuron` suggested that the distance between adjacent nodes should be no larger than a
            user-specified fraction ("d-lambda") of :math:`\\lambda_{100}`, the length constant at 100 Hz. This
            frequency is high enough for signal propagation to be insensitive to shunting by ionic
            conductances, but it is not unreasonably high because the rise time τr of fast EPSPs and
            spikes is ~ 1 ms, which corresponds to a bandpass of :math:`1/\\tau \\, 2 \\, \\pi \\, r \\approx 400 Hz`.
            At frequencies where :math:`R_m` can be ignored, the attenuation of signal amplitude is
            described by
            
            .. math::
            
                \\log \\left| \\frac{V_0}{V_x} \\right| \\approx 2 x \\sqrt{\\frac{\\pi f R_a C_m}{d}}
        
            So the distance over which an e-fold attenuation occurs is
            
            .. math::
            
                \\lambda_f \\approx \\frac{1}{2} \\sqrt{\\frac{d}{\\pi f R_a C_m}}
        

        See also:
            :cite:t:`hines2001neuron` (Chapter 5).
        '''
        totalNSeg = 0
        maxL = 0.0
        avgL = 0.0
        maxLabel = ''
        for label in list(self.cell.branches.keys()):
            if label == 'AIS' or label == 'Myelin' or label == 'Node':
                for branch in self.cell.branches[label]:
                    for sec in branch:
                        sec.set_segments(sec.nseg)
                continue
            for branch in self.cell.branches[label]:
                for sec in branch:
                    if full:
                        sec.set_segments(sec.nrOfPts)
                        totalNSeg += sec.nrOfPts
                        tmpL = sec.L / sec.nrOfPts
                        avgL += sec.L
                        if tmpL > maxL:
                            maxL = tmpL
                            maxLabel = label
                    else:
                        d = sec.diamList[sec.nrOfPts // 2]
                        _lambda = 100000 * math.sqrt(d / (4 * np.pi * f * sec.Ra * sec.cm))
                        nrOfSegments = int(((sec.L /
                                             (0.1 * _lambda) + 0.5) // 2) * 2 +
                                           1)
                        if max_seg_length is not None:
                            tmpL = sec.L / nrOfSegments
                            if tmpL > max_seg_length:
                                nrOfSegments = int(
                                    np.ceil(
                                        float(sec.L) / float(max_seg_length)))
                        # nrOfSegments = 1 + 2*int(sec.L/40.0)
#                        # nrOfSegments = int(((sec.L/(0.05*_lambda) + 0.5)//2)*2 + 1)
                        sec.set_segments(nrOfSegments)
                        totalNSeg += nrOfSegments
                        tmpL = sec.L / nrOfSegments
                        avgL += sec.L
                        if tmpL > maxL:
                            maxL = tmpL
                            maxLabel = label

                    # logger.info sec.name()
                    # logger.info '\tnr of points: %d' % sec.nrOfPts
                    # logger.info '\tnr of segments: %d' % sec.nseg
        totalL = avgL
        avgL /= totalNSeg
        logger.info(
            '    frequency used for determining discretization: {}'.format(f))
        logger.info('    maximum segment length: {}'.format(max_seg_length))
        logger.info('    Total number of compartments in model: %d' % totalNSeg)
        logger.info('    Total length of model cell: %.2f' % totalL)
        logger.info('    Average compartment length: %.2f' % avgL)
        logger.info('    Maximum compartment (%s) length: %.2f' % (maxLabel, maxL))

    def _create_ais(self):
        '''Create axon hillock and AIS according to :cite:t:`Mainen_Joerges_Huguenard_Sejnowski_1995`
        
        .. deprecated:: 0.1.0
            This method is deprecated in favor of the more recent :py:meth:`_create_ais_Hay2013`.
       
        Note:
            Connectivity is automatically taken care of, since this should only be called from :py:meth:`spatialgraph_to_cell`.
        
        '''
        nseg = 11  # nr of segments for hillock/ais

        somaDiam = 2 * np.sqrt(h.area(0.5, sec=self.cell.soma) / (4 * np.pi))
        '''AIS'''
        #        pyramidal neurons
        #        aisDiam = 1.0 # [um]
        #        aisLength = 15.0 # [um]
        #        spiny stellates
        #        aisDiam = 0.75 # [um]
        aisDiam = somaDiam * 0.05  # [um]
        aisLength = 15.0  # [um]
        aisStep = aisLength / (nseg - 1)
        '''axon hillock'''
        #        pyramidal neurons
        #        hillBeginDiam = 4.0 # [um]
        #        hillLength = 10.0 # [um]
        #        hillTaper = -3.0/(nseg-1) # from 4mu to 1mu
        #        spiny stellates
        #        hillBeginDiam = 1.5 # [um]
        hillBeginDiam = 4 * aisDiam  # [um]
        hillLength = 10.0  # [um]
        hillTaper = (aisDiam - hillBeginDiam) / (nseg - 1)  # from 4mu to 1mu
        hillStep = hillLength / (nseg - 1)

        logger.info('Creating AIS:')
        logger.info('    soma diameter: %.2f' % somaDiam)
        logger.info('    axon hillock diameter: %.2f' % hillBeginDiam)
        logger.info('    initial segment diameter: %.2f' % aisDiam)
        '''myelin & nodes'''
        myelinSeg = 25  # nr of segments internode section
        #        myelinDiam = 1.5 # [um]
        myelinDiam = 1.5 * aisDiam  # [um]
        myelinLength = 100.0  # [um]
        myelinStep = myelinLength / (myelinSeg - 1)
        #        nodeDiam = 1.0 # [um]
        nodeDiam = aisDiam  # [um]
        nodeLength = 1.0  # [um]
        nodeSeg = 3
        nrOfNodes = 2

        zAxis = np.array([0, 0, 1])

        soma = self.cell.soma
        somaCenter = np.array(soma.pts[len(soma.pts) // 2])
        somaRadius = 0.5 * soma.diamList[len(soma.pts) // 2]
        somaID = 0
        for i in range(len(self.cell.sections)):
            sec = self.cell.sections[i]
            if sec.label == 'Soma':
                somaID = i
                break

        hillBegin = somaCenter - somaRadius * zAxis
        hill = [hillBegin - i * hillStep * zAxis for i in range(nseg)]
        hillDiameter = [hillBeginDiam + hillTaper * i for i in range(nseg)]
        aisBegin = hill[-1]
        ais = [aisBegin - i * aisStep * zAxis for i in range(nseg)]
        aisDiameter = [aisDiam for i in range(nseg)]

        hHill = PySection('axon_0', self.cell.id, 'AIS')
        hHill.set_3d_geometry(hill, hillDiameter)
        hHill.parentx = 0.5
        hHill.parentID = somaID
        hHill.nseg = nseg
        #        hHill.set_segments(nseg)
        self.cell.sections.append(hHill)

        hAis = PySection('axon_0_0', self.cell.id, 'AIS')
        hAis.set_3d_geometry(ais, aisDiameter)
        hAis.parentx = 1.0
        hAis.parentID = len(self.cell.sections) - 1
        hAis.nseg = nseg
        #        hAis.set_segments(nseg)
        self.cell.sections.append(hAis)

        myelinBegin = ais[-1]
        for i in range(nrOfNodes):
            myelin = [
                myelinBegin - j * myelinStep * zAxis for j in range(myelinSeg)
            ]
            myelinDiameter = [myelinDiam for j in range(myelinSeg)]
            nodeBegin = myelin[-1]
            node = [nodeBegin - j * nodeLength * zAxis for j in range(nodeSeg)]
            nodeDiameter = [nodeDiam for j in range(nodeSeg)]

            myelinStr = 'axon_0_0' + (2 * i + 1) * '_0'
            hMyelin = PySection(myelinStr, self.cell.id, 'Myelin')
            hMyelin.set_3d_geometry(myelin, myelinDiameter)
            hMyelin.parentx = 1.0
            hMyelin.parentID = len(self.cell.sections) - 1
            hMyelin.nseg = myelinSeg
            #            hMyelin.set_segments(myelinSeg)
            self.cell.sections.append(hMyelin)
            nodeStr = 'axon_0_0' + 2 * (i + 1) * '_0'
            hNode = PySection(nodeStr, self.cell.id, 'Node')
            hNode.set_3d_geometry(node, nodeDiameter)
            hNode.parentx = 1.0
            hNode.parentID = len(self.cell.sections) - 1
            hNode.nseg = nodeSeg
            #            hNode.set_segments(nodeSeg)
            self.cell.sections.append(hNode)

            myelinBegin = node[-1]

    def _create_ais_Hay2013(self):
        '''Create axon hillock and AIS according to :cite:t:`Hay_Schuermann_Markram_Segev_2013`
        
        Note:
            connectivity is automatically taken care of since this should only be called from :py:meth:`spatialgraph_to_cell`
            
        '''
        
        '''myelin'''
        myelinDiam = 1.0  # [um]
        myelinLength = 1000.0  # [um]
        myelinSeg = 1 + 2 * int(myelinLength / 100.0)
        myelinStep = myelinLength / (myelinSeg - 1)
        '''AIS'''
        aisDiam = 1.75  # [um]
        aisLength = 30.0  # [um]
        aisSeg = 1 + 2 * int(aisLength / 10.0)
        aisTaper = (myelinDiam - aisDiam) / (aisSeg - 1)
        aisStep = aisLength / (aisSeg - 1)
        '''axon hillock'''
        hillBeginDiam = 3  # [um]
        hillLength = 20.0  # [um]
        hillSeg = 1 + 2 * int(hillLength / 10.0)
        hillTaper = (aisDiam - hillBeginDiam) / (hillSeg - 1)
        hillStep = hillLength / (hillSeg - 1)
        #        '''AIS'''
        #        aisDiam = 1.0 # [um]
        #        aisLength = 30.0 # [um]
        #        aisSeg = 1 + 2*int(aisLength/10.0)
        #        aisTaper = (myelinDiam-aisDiam)/(aisSeg-1)
        #        aisStep = aisLength/(aisSeg-1)
        #        '''axon hillock'''
        #        hillBeginDiam = 1.0 # [um]
        #        hillLength = 30.0 # [um]
        #        hillSeg = 1 + 2*int(hillLength/10.0)
        #        hillTaper = (aisDiam-hillBeginDiam)/(hillSeg-1)
        #        hillStep = hillLength/(hillSeg-1)

        logger.info('Creating AIS:')
        logger.info('    axon hillock diameter: {:.2f}'.format(hillBeginDiam))
        logger.info('    initial segment diameter: {:.2f}'.format(aisDiam))
        logger.info('    myelin diameter: {:.2f}'.format(myelinDiam))

        zAxis = np.array([0, 0, 1])

        soma = self.cell.soma
        somaCenter = np.array(soma.pts[len(soma.pts) // 2])
        somaRadius = 0.5 * soma.diamList[len(soma.pts) // 2]
        somaID = 0
        for i in range(len(self.cell.sections)):
            sec = self.cell.sections[i]
            if sec.label == 'Soma':
                somaID = i
                break

        hillBegin = somaCenter - somaRadius * zAxis
        hill = [hillBegin - i * hillStep * zAxis for i in range(hillSeg)]
        hillDiameter = [hillBeginDiam + hillTaper * i for i in range(hillSeg)]

        aisBegin = hill[-1]
        ais = [aisBegin - i * aisStep * zAxis for i in range(aisSeg)]
        aisDiameter = [aisDiam + aisTaper * i for i in range(aisSeg)]

        myelinBegin = ais[-1]
        myelin = [
            myelinBegin - j * myelinStep * zAxis for j in range(myelinSeg)
        ]
        myelinDiameter = [myelinDiam for j in range(myelinSeg)]

        hHill = PySection('axon_0', self.cell.id, 'AIS')
        hHill.set_3d_geometry(hill, hillDiameter)
        hHill.parentx = 0.5
        hHill.parentID = somaID
        hHill.nseg = hillSeg
        self.cell.sections.append(hHill)

        hAis = PySection('axon_0_0', self.cell.id, 'AIS')
        hAis.set_3d_geometry(ais, aisDiameter)
        hAis.parentx = 1.0
        hAis.parentID = len(self.cell.sections) - 1
        hAis.nseg = aisSeg
        self.cell.sections.append(hAis)

        myelinStr = 'axon_0_0_0'
        hMyelin = PySection(myelinStr, self.cell.id, 'Myelin')
        hMyelin.set_3d_geometry(myelin, myelinDiameter)
        hMyelin.parentx = 1.0
        hMyelin.parentID = len(self.cell.sections) - 1
        hMyelin.nseg = myelinSeg
        self.cell.sections.append(hMyelin)

    def rieke_spines(self, parameters):
        """Add spines with morphological features to the neuron.
        
        .. deprecated:: 0.1.0
            Including specific morphological features of spines made it impossible to find a neuron model for as long as we tried this
            project.
            Instead we scale the membrane capacitance and resistance of the dendritic structures (see :py:meth:`_add_spines`).
            
        Args:
            parameters (:py:class:`~sumatra.parameters.NTParameterSet`): Parameters for spine morphology. See :ref:`cell_parameters_format` for an example.
        
        :skip-doc:
        """
        spineneckDiam = parameters.spatialgraph_modify_functions.rieke_spines.spine_morphology.spineneckDiam
        spineneckLength = parameters.spatialgraph_modify_functions.rieke_spines.spine_morphology.spineneckLength

        spineheadDiam = parameters.spatialgraph_modify_functions.rieke_spines.spine_morphology.spineheadDiam
        spineheadLength = parameters.spatialgraph_modify_functions.rieke_spines.spine_morphology.spineheadLength

        logger.info("Creating dendritic spines:")
        logger.info(("    spine neck length: {}".format(spineneckLength)))
        logger.info(("    spine neck diameter: {}".format(spineneckDiam)))
        logger.info(("    spine head length: {}".format(spineheadLength)))
        logger.info(("    spine head diameter: {}".format(spineheadDiam)))

        from config.cell_types import EXCITATORY
        excitatory = EXCITATORY.extend("GENERIC")

        def get_closest(lst, target):
            lst = np.asarray(lst)
            idx = (np.abs(lst - target)).argmin()
            return idx, lst[idx]

        synFile = parameters.spatialgraph_modify_functions.rieke_spines.syn_filepath

        with open(synFile, "r") as synapse_file:
            file_data = synapse_file.readlines()

        for n, line in enumerate(file_data):
            if n > 3:  # line 5 is first line containing data
                line_split = line.split("\t")

                if (line_split[0].split("_"))[0] in excitatory:

                    hSpineNeck = PySection(name="spine_neck",
                                           cell=self.cell.id,
                                           label="SpineNeck")
                    hSpineNeck.nseg = 1
                    self.cell.sections.append(hSpineNeck)

                    hSpineHead = PySection(name="spine_head",
                                           cell=self.cell.id,
                                           label="SpineHead")
                    hSpineHead.nseg = 1
                    self.cell.sections.append(hSpineHead)

                    # 3d geometry for spine neck
                    section = self.cell.sections[int(line_split[1])]

                    idx, closest_rel_pt = get_closest(section.relPts,
                                                      float(line_split[2]))
                    spine_neck_start = section.pts[idx]

                    spine_neck_end = [
                        spine_neck_start[0], spine_neck_start[1],
                        spine_neck_start[2] + spineneckLength
                    ]

                    points_neck = [spine_neck_start, spine_neck_end]
                    diameters_neck = [spineneckDiam, spineneckDiam]

                    hSpineNeck.set_3d_geometry(points_neck, diameters_neck)
                    hSpineNeck.parentx = closest_rel_pt
                    hSpineNeck.parentID = int(line_split[1])

                    # 3d geometry for spine head
                    spine_head_start = spine_neck_end
                    spine_head_end = [
                        spine_head_start[0], spine_head_start[1],
                        spine_head_start[2] + spineheadLength
                    ]

                    points_head = [spine_head_start, spine_head_end]
                    diameters_head = [spineheadDiam, spineheadDiam]

                    hSpineHead.set_3d_geometry(points_head, diameters_head)
                    hSpineHead.parentx = 1.0
                    hSpineHead.parentID = self.cell.sections.index(hSpineNeck)
