import Interface as I
def spatialgraph_to_cell(self, parameters, axon=False, scaleFunc=None):
        '''
        reads cell morphology from Amira hoc file
        and sets up PySections and Cell object
        optional: takes function object scaleFunc as argument
        for scaling dendritic diameters.
        scaleFunc takes cell object as argument
        '''
        edgeList = reader.read_hoc_file(self.hoc_path)
        #part1 = self.hoc_fname.split('_')[0]
        #part2 = self.hoc_fname.split('_')[1]
        #part3 = self.hoc_fname.split('.')[-2]
        self.cell = Cell()
        #self.cell.id = '_'.join([part1, part2, part3])
        self.cell.hoc_path = self.hoc_path  # sotre path to hoc_file in cell object

        #        first loop: create all Sections
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

#        add axon initial segment, myelin and nodes
        if axon:
            self._create_ais_Hay2013()
#            self._create_ais()

#        add dendritic spines (Rieke)
        try:
            if 'rieke_spines' in list(
                    parameters.spatialgraph_modify_functions.keys()):
                self.rieke_spines(parameters)
            else:
                logger.info("No spines are being added...")
        except AttributeError:
            pass

#        second loop: connect sections
#        and create structures dict
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

#        create trees
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

        #        scale dendrites if necessary
        if scaleFunc:
            warnings.warn(
                'Keyword scaleFunc is deprecated! ' +
                'New: To ensure reproducability, scaleFunc should be ' +
                'specified in the parameters, as described in single_cell_parser.cell_modify_funs'
            )
            scaleFunc(self.cell)

from single_cell_parser.cell import Cell, PySection
from single_cell_parser.cell_parser import CellParser

def TABLE_to_cell(TABLE, x, axon = True):
    from neuron import h
    cell = Cell()
    for secID, row in enumerate(TABLE):
        hocLabel = None # not sure if that is ok
        detailed_label = row['detailed_label']
        label_dict = {
            'Soma': 'Soma',
            '0_basal': 'Dendrite',
            '1_obliques': 'ApicalDendrite',
            '2_trunk': 'ApicalDendrite',
            '3_tuft': 'ApicalDendrite',
        }
        label = label_dict[detailed_label]
        sec = PySection(hocLabel, cell.id, label)
        sec.detailed_label = detailed_label
        sec.secID = secID
        if sec.label == 'Soma':
            parentx = 0.5
        else:
            parentx = 1.
        sec.parentx = parentx
        sec.parentID = row['parent']
        pts = ((1-x)*I.np.array(row['pts_start'])+x*I.np.array(row['pts_target'])).tolist()
        edgePts = [x[:3] for x in pts] # x,y,z row['pts_start']
        diameterList = [x[3] for x in pts]
        sec.set_3d_geometry(edgePts, diameterList)
        cell.sections.append(sec)
        if sec.label == 'Soma':
            cell.soma = sec
    cell_parser = CellParser()
    cell_parser.cell = cell
    
    if axon:
        cell_parser._create_ais_Hay2013()

    self = cell_parser

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

    #        create trees
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
    return cell_parser

def create_cell(parameters, TABLE = None, x = None, scaleFunc=None, allPoints=False, setUpBiophysics = True,\
                silent = False):
    '''
    modified to be able to create cell object from TABLE
    
    
    default way of creating NEURON cell models;
    includes spatial discretization and inserts
    biophysical mechanisms according to parameter file
    '''
    #x = parameters['transition_x']
    #del parameters['transition_x']
    # raise RuntimeError()
    if scaleFunc is not None:
        warnings.warn(
            'Keyword scaleFunc is deprecated! ' +
            'New: To ensure reproducability, scaleFunc should be specified in the parameters, as described in single_cell_parser.cell_modify_funs'
        )
    #logger.info('-------------------------------')
    #logger.info('Starting setup of cell model...')
    axon = False

    if 'AIS' in list(parameters.keys()):
        axon = True

    #logger.info('Loading cell morphology...')
    parser = TABLE_to_cell(TABLE, x, axon = axon) # CellParser(parameters.filename)
    #parser.spatialgraph_to_cell(parameters, axon, scaleFunc)
    if setUpBiophysics:
        #logger.info('Setting up biophysical model...')
        parser.set_up_biophysics(parameters, allPoints)
    #logger.info('-------------------------------')

    parser.apply_cell_modify_functions(parameters)
    parser.cell.init_time_recording()
    parser.cell.parameters = parameters
    parser.cell.scaleFunc = scaleFunc
    parser.cell.allPoints = allPoints
    parser.cell.neuronParam = parameters
    return parser.cell
