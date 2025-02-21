"""Scale a morphology between its current shape and a target morphology.

Attention:
    This is still in development

:skip-doc:
"""


import numpy as np
import pandas as pd
import time
import single_cell_parser as scp
import six
if six.PY3:
    from scipy.spatial.transform import Rotation
else:
    # let ImportWarnings show up when importing this module through Interface
    warnings.filterwarnings("default", category=ImportWarning, module=__name__)
    warnings.warn("Scipy version is too old to import spatial.transform.Rotation.")
import logging
logger = logging.getLogger("ISF").getChild(__name__)

def scale_morphology(cell, scale, target_morphology):
    """Scale a morphology between its current shape and a target morphology.

    Given a target morphology :ref:`hoc_file_format` file, this method scales the current
    :paramref:`cell` to be closer to the target morphology. The scaling is done by linearly
    interpolating each point between the current and target morphology.

    A :paramref:`scale` factor of 0.0 will result in the current morphology, while a factor of 1.0
    will result in the target morphology. Anything in between will be a linear interpolation.

    The target morphology must contain the same amount of points as the current morphology, 
    (ignoring AIS and Myelin), and the points must be in the same order.
    
    Args:
        cell (:py:class:`~single_cell_parser.cell.Cell`): The cell to scale.
        scale (float): The scaling factor.
        target_morphology (str): The path to the target morphology file.
        
    Returns:
        :py:class:`~single_cell_parser.cell.Cell`: The scaled cell.
    """
    import re
    pattern = r"[-+]?(?:\d*\.*\d+)"  # matches floats
    f = open(target_morphology)
    
    # extract points from target morphology
    points = []
    for l in f:
        if 'pt3dadd' in l:
            _,x,y,z,_ = [float(i) for i in re.findall(pattern,l)]
            points.append([x,y,z])
    
    # count amount of non-AIS, non-Myelin points in cell
    n_pts = 0
    for sec in cell.sections:
        if sec.label not in ['AIS', 'Myelin']:
            n_pts += len(sec.pts)
    assert(n_pts == len(points))
    
    # scale each point
    count = -1
    for i, sec in enumerate(cell.sections):
        if sec.label not in ['AIS', 'Myelin']:
            for j, pt in enumerate(sec.pts):
                count += 1
                x = pt[0] + (points[count][0] - pt[0]) * scale
                y = pt[1] + (points[count][1] - pt[1]) * scale
                z = pt[2] + (points[count][2] - pt[2]) * scale
                cell.sections[i].pts[j] = [x,y,z]
    return cell

def scale_morphology_old(cell, scaling_infragranular, scaling_granular, scaling_supragranular, home_column='C2'):
    """
    :skip-doc:
    """
    mis = MorphologyInSpace(cell)
    mis.scale_morphology(scaling_infragranular, scaling_granular, scaling_supragranular, home_column)
    cell = mis.update_cell_morphology()
    logger.info('Morphology scaled successfully')
    return cell
    
class MorphologyInSpace:
    """
    :skip-doc:
    """
    def __init__(self, cell):
        self.cell = cell
        self.original_hoc_file = cell.neuron_param.filename
        self.soma = None
        self._update_soma()
        # self.soma = np.mean(cell.soma.pts, axis=0) # Center of the soma of the original cell object, unaligned with z-axis
        self.parents = {} # Maps sections to their parents. self.parents[10] returns the parent of section 10
        self.morphology = None # pd.DataFrame containing point information, diameter and section ID
        self.sections = None # Set of section indices
        self.n_sections = None
        self._calc_morphology()  # pandas DataFrame
        self.whiskers_order = ['alpha','A1','A2','A3','A4','beta','B1','B2','B3','B4','gamma','C1','C2','C3','C4','delta','D1','D2','D3','D4','E1','E2','E3','E4']
        self.columns_axis = {
            'A1'   : [  59.00701904,  210.52996826, 1078.05102539],
            'A2'   : [ 135.57009888,  305.17907715, 1048.0869751 ],
            'A3'   : [ 179.12460136,  337.34594727, 1031.55700684],
            'A4'   : [ 215.23300171,  357.02996826, 1017.94100952],
            'alpha': [   5.92700195,  168.90606689, 1086.9380188 ],
            'B1'   : [   8.70300293,  132.89202881, 1091.90795898],
            'B2'   : [  99.53600311,  192.34399414, 1078.46899414],
            'B3'   : [ 148.21909332,  246.67901611, 1061.68701172],
            'B4'   : [ 188.26397705,  301.77099609, 1040.90802002],
            'beta' : [ -73.02197266,   64.89501953, 1095.65301514],
            'C1'   : [ -54.29904175,   32.98699951, 1098.16397095],
            'C2'   : [  40.15970612,   82.21600342, 1096.1880188 ],
            'C3'   : [ 121.25201416,  192.97299194, 1076.13198853],
            'C4'   : [ 149.99200439,  230.14398193, 1065.14599609],
            'gamma': [-122.15698242,  -31.45098877, 1092.74298096],
            'D1'   : [ -59.9960022 ,  -24.2512989 , 1098.09503174],
            'D2'   : [1.44668599e-06, 1.72487995e-06, 1.10000003e+03],
            'D3'   : [  63.96600342,   62.83650017, 1096.33999634],
            'D4'   : [ 113.01495361,  130.85349655, 1086.32699585],
            'delta': [-114.75701904,  -56.37998962, 1092.54403687],
            'E1'   : [ -59.67300415,  -82.61001587, 1095.26898193],
            'E2'   : [   3.69302368,  -58.09802246, 1098.45898438],
            'E3'   : [  35.93103027,  -23.52700806, 1099.16101074],
            'E4'   : [ 102.30993652,   39.70300293, 1094.51199341]}
        self.unitary_columns_axis = {c:self._unit_vector(self.columns_axis[c]) for c in self.columns_axis.keys()}
        self.columns_compartments_sizes = np.array([
            [ 814.18180155,  306.81826453,  479.00142472], [ 876.67936449,  319.32243749,  455.00198407], [ 956.52397627,  335.47949855,  466.99943567], 
            [1026.55022483,  313.44871614,  484.999777  ], [1112.49578169,  314.49974228,  489.00049767], [ 814.08281571,  336.9172873 ,  472.00002113],
            [ 910.49961063,  344.49811139,  481.00023164], [ 982.20179949,  342.80061271,  489.99993817], [1055.66722433,  353.33438054,  490.00039481], 
            [1108.85171205,  351.14868451,  501.00025157], [ 882.93039183,  352.0715039 ,  477.99930804], [ 965.70014916,  356.29680905,  477.99994414],
            [1036.52527401,  359.47080226,  495.99995063], [1098.00727611,  352.99337307,  534.00023824], [1119.34587015,  361.65497556,  557.00048468],
            [ 986.54405767,  352.45707422,  505.99984927], [1003.70530905,  370.29834192,  491.00035556], [1070.15895081,  360.8420105 ,  525.99897766],
            [1126.92335664,  367.07559521,  551.9999768 ], [1162.76386065,  362.23906126,  555.99909122], [1089.61717184,  341.38319424,  546.00021266],
            [1185.05279034,  353.94606994,  557.00058895], [1205.24896481,  362.74860685,  549.00063281], [1188.06839458,  342.93270428,  580.00085812]])
        self.L4_upper_points = np.array([ # Each point (x, y, z coordinates) belongs to a column in the upper L4 limit
            [-5.87161011e+02,  9.96203979e+02,  1.72660004e+02], [-3.09496002e+02,  1.17637000e+03,  1.55679001e+02], [ 3.15109997e+01,  1.20307996e+03,  9.28683014e+01],
            [ 2.88225006e+02,  1.18089001e+03,  3.28432999e+01], [ 5.41994019e+02,  1.11506006e+03, -1.20783005e+01], [-7.16676025e+02,  6.13708008e+02,  2.18664001e+02],
            [-3.35770996e+02,  7.70181030e+02,  2.03746002e+02], [ 3.94286003e+01,  8.13328979e+02,  1.47807999e+02], [ 3.67765991e+02,  8.12831970e+02,  9.38972015e+01],
            [ 6.78364990e+02,  8.26741028e+02,  3.34301987e+01], [-6.61581970e+02,  1.84242996e+02,  2.18335007e+02], [-3.41765991e+02,  4.12729004e+02,  2.32169998e+02],
            [ 1.00332001e+02,  4.22709015e+02,  1.92727997e+02], [ 5.47833984e+02,  4.30726013e+02,  9.75058975e+01], [ 9.46325012e+02,  4.51372986e+02,  2.63148003e+01],
            [-4.08967010e+02, -2.61393005e+02,  1.89425003e+02], [-2.48565994e+02,  2.31359997e+01,  2.21733994e+02], [ 1.98671997e+02,  2.82911998e-07,  1.80421005e+02],
            [ 6.18078003e+02,  7.31018019e+00,  1.24717003e+02], [ 1.03339001e+03,  3.12929993e+01,  7.93759003e+01], [ 4.46730995e+01, -4.56092987e+02,  1.48535995e+02],
            [ 4.99273010e+02, -5.01877014e+02,  1.24821999e+02], [ 9.49302002e+02, -4.89696991e+02,  1.16722000e+02], [ 1.33829004e+03, -3.65243988e+02,  6.58533020e+01]])
        self.L4_lower_points = np.array([ # Each point (x, y, z coordinates) belongs to a column in the lower L4 limit
            [-5.88814026e+02,  9.49091003e+02, -1.30514999e+02], [-3.26626007e+02,  1.11526001e+03, -1.57272995e+02], [-9.83512020e+00,  1.11000000e+03, -2.26776993e+02],
            [ 2.37182999e+02,  1.08476001e+03, -2.61101990e+02], [ 4.80457001e+02,  1.01297998e+03, -3.03115997e+02], [-6.94309998e+02,  5.93831970e+02, -1.16921997e+02],
            [-3.38496002e+02,  7.28562012e+02, -1.38218002e+02], [ 8.40962982e+00,  7.53388000e+02, -1.88283005e+02], [ 3.20157013e+02,  7.33596008e+02, -2.47130997e+02],
            [ 6.18265991e+02,  7.30408020e+02, -2.98855011e+02], [-6.22484009e+02,  1.94309006e+02, -1.31414001e+02], [-3.24178009e+02,  4.02044006e+02, -1.23531998e+02],
            [ 8.72086029e+01,  3.95841003e+02, -1.65496994e+02], [ 5.08924011e+02,  3.68799988e+02, -2.47828003e+02], [ 8.97010986e+02,  3.75707001e+02, -3.23881012e+02],
            [-3.72196991e+02, -2.43328003e+02, -1.60643005e+02], [-2.28369003e+02,  3.12998009e+01, -1.47923004e+02], [ 1.98671997e+02, -2.82911998e-07, -1.80421005e+02],
            [ 5.96731995e+02, -1.36587000e+01, -2.41136993e+02], [ 9.96169983e+02, -1.17981005e+01, -2.78359985e+02], [ 6.31926994e+01, -4.30454987e+02, -1.91378998e+02],
            [ 4.98084991e+02, -4.83182007e+02, -2.28628006e+02], [ 9.37453003e+02, -4.81937988e+02, -2.45750000e+02], [ 1.30640002e+03, -3.77622009e+02, -2.75368988e+02]])
        
    def _calc_morphology(self):
        '''Retrieve cell MORPHOLOGY from cell object. Fills the self.morphology attribute'''
        t1 = time.time()
        points = []
        for sec_n, sec in enumerate(self.cell.sections):
            if sec.label == 'Soma':
                n_segments = len([seg for seg in sec])
                for i, pt in enumerate(sec.pts):
                    seg_n = int(n_segments * i / len(sec.pts))
                    x, y, z = pt
                    d = sec.diamList[i]
                    points.append([x, y, z, d, sec_n, seg_n])
            elif sec.label in ['AIS', 'Myelin']:
                continue
            else:
                self.parents[sec_n] = self.cell.sections.index(sec.parent)
                # Points within the same section
                xs_in_sec = [seg.x for seg in sec]
                n_segments = len([seg for seg in sec])
                for i, pt in enumerate(sec.pts):
                    seg_n = int(n_segments * i / len(sec.pts))
                    x, y, z = pt
                    d = sec.diamList[i]
                    points.append([x, y, z, d, sec_n, seg_n])

        self.morphology = pd.DataFrame(points, columns=['x', 'y', 'z', 'diameter', 'sec_n', 'seg_n'])
        self.morphology['sec_n'] = self.morphology['sec_n'].astype(int)
        self.morphology['seg_n'] = self.morphology['seg_n'].astype(int)
        t2 = time.time()
        logger.info('Morphology retrieved in {} seconds'.format(np.around(t2 - t1, 2)))
        
        self.sections = self.morphology['sec_n'].unique()
        self.n_sections = len(self.sections)
        for sec in self.sections[1:]:
            parent_sec = self.parents[sec]
            parent_point = self.morphology[self.morphology['sec_n'] == parent_sec].iloc[[-1]]
            parent_point["sec_n"] = sec
            
    def _update_soma(self):
        self.soma = np.mean(self.cell.soma.pts, axis=0)
        
    def update_cell_morphology(self):
        for i,sec in enumerate(self.cell.sections):
            if sec.label not in ['AIS', 'Myelin']:
                sec.pts = self.morphology.loc[self.morphology['sec_n'] == i][['x','y','z']].values.tolist()
        self._update_soma()
        return self.cell
       
    def _unit_vector(self, vector):
        """ Returns the unit vector of the vector.  """
        return vector / np.linalg.norm(vector)
            
    def scale_morphology(self, scaling_infragranular, scaling_granular, scaling_supragranular, home_column='C2'):
        translated_morphology = self.morphology[['x','y','z']] - self.soma
        original_col_idx = self.whiskers_order.index(home_column)
        home_column_axis = self.unitary_columns_axis[home_column]
        angle = np.arccos(np.dot([0,0,1], home_column_axis)) # angle between column and z axes
        xy_proj = self._unit_vector([home_column_axis[0], home_column_axis[1], 0]) # home column axis projected onto xy plane, mde unitary
        xy_proj_orth = [xy_proj[1], -xy_proj[0], 0] # create vector to rotate about
        # rotation towards z-axis as rotation vector: direction is axis to rotate about, norm is angle of rotation
        rotation = Rotation.from_rotvec(angle*np.array(xy_proj_orth))
        # Rotate morphology to align column axis with z-axis
        rotated_morphology = rotation.apply([pt for pt in translated_morphology[['x', 'y', 'z']].values])

        translated_hom_col_lowerL4_pt = self.L4_lower_points[original_col_idx] - self.soma
        rotated_hom_col_lowerL4_pt = rotation.apply([pt for pt in translated_hom_col_lowerL4_pt])
        z_infralimit = rotated_hom_col_lowerL4_pt[2]
        translated_hom_col_upperL4_pt = self.L4_upper_points[original_col_idx] - self.soma
        rotated_hom_col_upperL4_pt = rotation.apply([pt for pt in translated_hom_col_upperL4_pt])
        z_supralimit = rotated_hom_col_upperL4_pt[2]

        infra_pts = np.where(rotated_morphology[:,2] <= z_infralimit)[0]
        granular_pts = np.where(np.logical_and(rotated_morphology[:,2]>z_infralimit, rotated_morphology[:,2]<=z_supralimit))[0]
        supra_pts = np.where(rotated_morphology[:,2] > z_supralimit)[0]

        scaled_morphology_ = np.array(rotated_morphology)
        scaled_morphology_[infra_pts,2]    = scaled_morphology_[infra_pts,2]*scaling_infragranular
        scaled_morphology_[granular_pts,2] = (scaled_morphology_[granular_pts,2]-z_infralimit)*scaling_granular + \
                                                                                  z_infralimit*scaling_infragranular
        scaled_morphology_[supra_pts,2]    = (scaled_morphology_[supra_pts,2]   -z_supralimit)*scaling_supragranular + \
                                                                   (z_supralimit-z_infralimit)*scaling_granular + \
                                                                                  z_infralimit*scaling_infragranular

        derotation = Rotation.from_rotvec(-angle*np.array(xy_proj_orth))
        derotated_morphology = derotation.apply([pt for pt in scaled_morphology_])

        scaled_morphology = derotated_morphology + self.soma
        self.morphology[['x','y','z']] = scaled_morphology
            
    def scale_morphology_along_column_axis(self,home_column, new_column):
        new_col_idx      = self.whiskers_order.index(new_column)
        original_col_idx = self.whiskers_order.index(home_column)
        scaling_infragranular = self.columns_compartments_sizes[new_col_idx,0]/self.columns_compartments_sizes[original_col_idx,0]
        scaling_granular      = self.columns_compartments_sizes[new_col_idx,1]/self.columns_compartments_sizes[original_col_idx,1]
        scaling_supragranular = self.columns_compartments_sizes[new_col_idx,2]/self.columns_compartments_sizes[original_col_idx,2]
        logger.info('Infragranular scaling: {}'.format(np.around(scaling_infragranular, 3)))
        logger.info('Granular scaling: {}'.format(np.around(scaling_granular, 3)))
        logger.info('Supragranular scaling: {}'.format(np.around(scaling_supragranular, 3)))
        self.scale_morphology(scaling_infragranular, scaling_granular, scaling_supragranular)
    
    def _rotation_matrix(self,A,B):
        au = A/(np.sqrt(A[0]*A[0] + A[1]*A[1] + A[2]*A[2]))
        bu = B/(np.sqrt(B[0]*B[0] + B[1]*B[1] + B[2]*B[2]))
        R=np.array([[bu[0]*au[0], bu[0]*au[1], bu[0]*au[2]], [bu[1]*au[0], bu[1]*au[1], bu[1]*au[2]], [bu[2]*au[0], bu[2]*au[1], bu[2]*au[2]]])
        return(R)
    
    def rotate_morphology_to_different_column(self,home_column, new_column):
        R = self._rotation_matrix(self.unitary_columns_axis[home_column],self.unitary_columns_axis[new_column])
        rotation = Rotation.from_matrix(R)
        translated_morphology = self.morphology[['x','y','z']] #- self.soma
        rotated_morphology = rotation.apply([pt for pt in translated_morphology[['x', 'y', 'z']].values])
        self.morphology[['x','y','z']] = rotated_morphology #+ self.soma
    
    def write_hoc_file(self,file_path=''):
        if not file_path.endswith('.hoc') and not file_path.endswith('.HOC'):
            raise IOError('Output file is not a .hoc file!')

        fin = open(self.original_hoc_file)
        fout = open(file_path, "wt")
        ptcount = -1
        for line in fin:
            if 'pt3dadd' in line:
                ptcount += 1
                pt = self.morphology.loc[ptcount]
                newline = '{pt3dadd('+'{},{},{},{}'.format(pt['x'],pt['y'],pt['z'],pt['diameter'])+')}\n'
                fout.write(newline)
            else:
                fout.write(line)
        fin.close()
        fout.close()
