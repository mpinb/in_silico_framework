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

"""
Read and write data formats for AMIRA.

The primary function of this module is to provide read and write acces to AMIRA ``ScalarField`` files.
These are represented internally by the :class:`~ScalarField` object.
"""
from __future__ import annotations
import numpy as np
from data_base.dbopen import dbopen
from matplotlib import cm
from matplotlib.colors import Normalize
from typing import Tuple

__author__  = 'Robert Egger'
__date__    = '2012-03-08'

class ScalarField(object):
    '''3D scalar fields based on numpy arrays
    
    A convenience class around numpy array for 3D scalar fields.
    The class provides methods to access scalar values at arbitrary
    3D coordinates, to get the bounding box of a voxel, and to get
    the center of a voxel.

    This class is used for e.g. assigning sub-cellular synapse distributions
    modeled after vtkImageData, i.e. a regular mesh.
    
    Attributes:
        mesh (numpy.ndarray): 
            3D numpy array representing the scalar field.
        origin (tuple): 
            3-tuple of floats representing the origin of the scalar field.
        extent (tuple): 
            6-tuple of integers representing the extent of the scalar field.
            Note that the extent always starts at 0: 
            Format: (0, xmax - xmin, 0, ymax - ymin, 0, zmax - zmin)
        spacing (tuple): 
            3-tuple of floats representing the spacing of the scalar field.
            If all values are equal, the scalar field has cubic voxels.
        boundingBox (tuple): 
            6-tuple of floats representing the bounding box of the scalar field.
            Format: (xmin, xmax, ymin, ymax, zmin, zmax)
    
    '''

    mesh: np.ndarray = None
    origin = (0., 0., 0.)
    extent = (0., 0., 0., 0., 0., 0.)
    spacing = (0., 0., 0.)
    boundingBox= (0., 0., 0., 0., 0., 0., 0.)

    def __init__(self, mesh=None, origin=None, extent=None, spacing=None, bBox=None):
        '''
        Args:
            mesh (numpy.ndarray):
                3D numpy array representing the scalar field.
            origin (tuple):
                3-tuple of floats representing the origin of the scalar field.
            extent (tuple):
                6-tuple of integers representing the extent of the scalar field.
            spacing (tuple):
                3-tuple of floats representing the spacing of the scalar field.
            bBox (tuple):
                6-tuple of floats representing the bounding box of the scalar field.
        '''
        if mesh is not None:
            self.mesh = np.copy(mesh)
        if origin:
            self.origin = tuple(origin)
        if extent:
            self.extent = tuple(extent)
        if spacing:
            self.spacing = tuple(spacing)
        if bBox:
            self.boundingBox = tuple(bBox)
        if self.mesh is not None:
            self.resize_mesh()


    def resize_mesh(self):
        """Resizes mesh to non-zero scalar data using slicing views (no copy)."""
        roi = np.where(self.mesh)
        if roi[0].size == 0:
            return  # no non-zero voxels

        iMin, iMax = roi[0].min(), roi[0].max()
        jMin, jMax = roi[1].min(), roi[1].max()
        kMin, kMax = roi[2].min(), roi[2].max()

        self.extent = (0, iMax - iMin, 0, jMax - jMin, 0, kMax - kMin)

        dx, dy, dz = self.spacing
        xMin, yMin, zMin = (
            self.origin[0] + iMin * dx,
            self.origin[1] + jMin * dy,
            self.origin[2] + kMin * dz)
        xMax, yMax, zMax = (
            self.origin[0] + (iMax + 1) * dx,
            self.origin[1] + (jMax + 1) * dy,
            self.origin[2] + (kMax + 1) * dz)

        self.origin = (xMin, yMin, zMin)
        self.boundingBox = (xMin, xMax, yMin, yMax, zMin, zMax)

        # Slice view instead of copying
        self.mesh = self.mesh[iMin:iMax + 1, jMin:jMax + 1, kMin:kMax + 1]

    def get_scalar(self, xyz):
        '''Fetch the scalar value of the voxel containing the point xyz.

        Warning:
            Returns 0 if :param:`xyz` is outside the bounding box.

        Args:
            xyz (tuple): The 3D coordinates of the point.

        Returns:
            float: The scalar value of the voxel containing the point, 0 if outside bounding box.
        '''
        x, y, z = xyz
        delta = 1.0e-6
        if x < self.boundingBox[0] + delta:
            return 0
        if x > self.boundingBox[1] - delta:
            return 0
        if y < self.boundingBox[2] + delta:
            return 0
        if y > self.boundingBox[3] - delta:
            return 0
        if z < self.boundingBox[4] + delta:
            return 0
        if z > self.boundingBox[5] - delta:
            return 0
        i = int((x - self.origin[0]) // self.spacing[0])
        j = int((y - self.origin[1]) // self.spacing[1])
        k = int((z - self.origin[2]) // self.spacing[2])
        return self.mesh[i, j, k]

    def is_in_bounds(self, xyz):
        """Check if point is within bounding box of mesh.
        
        Args:
            xyz (tuple): The 3D coordinates of the point.
            
        Returns:
            bool: True if point is within bounding box, False otherwise.
        """
        x, y, z = xyz
        delta = 1.0e-6
        if x < self.boundingBox[0] + delta:
            return False
        if x > self.boundingBox[1] - delta:
            return False
        if y < self.boundingBox[2] + delta:
            return False
        if y > self.boundingBox[3] - delta:
            return False
        if z < self.boundingBox[4] + delta:
            return False
        if z > self.boundingBox[5] - delta:
            return False
        return True

    def get_mesh_coordinates(self, xyz):
        '''Fetch the mesh index of the voxel containing the point xyz.

        Warning:
            This method does not perform range checking.
            If :param:`xyz` is outside the bounding box, the index will be out of bounds for the :attr:`mesh`.

        Args:
            xyz (tuple): The 3D coordinates of the point.

        Returns:
            tuple: The :attr:`mesh` index of the voxel containing the point. 
        '''
        x, y, z = xyz
        i = int((x - self.origin[0]) // self.spacing[0])
        j = int((y - self.origin[1]) // self.spacing[1])
        k = int((z - self.origin[2]) // self.spacing[2])
        return i, j, k

    def get_voxel_bounds(self, ijk):
        '''Gets the bounding box of voxel given by indices i,j,k. 
        
        Args:   
            ijk (tuple): tuple of 3 integers: the indices of voxel in mesh.
        
        Warning:
            Does not perform bounds checking. The voxel bounds may be beyond the span of the mesh.
        '''
        i, j, k = ijk
        xMin = self.origin[0] + i * self.spacing[0]
        xMax = self.origin[0] + (i + 1) * self.spacing[0]
        yMin = self.origin[1] + j * self.spacing[1]
        yMax = self.origin[1] + (j + 1) * self.spacing[1]  # in case this breaks - it used to say spacing[01] (rieke, 08022021)
        zMin = self.origin[2] + k * self.spacing[2]
        zMax = self.origin[2] + (k + 1) * self.spacing[2]
        return xMin, xMax, yMin, yMax, zMin, zMax

    def get_voxel_center(self, ijk):
        '''Fetch the center of the voxel given by indices i,j,k.

        Warning:
            Does not perform bounds checking. The voxel center may be outside the span of the mesh.
        
        Args:
            ijk (tuple): tuple of 3 integers: the indices of voxel in mesh.
        
        Returns:
            tuple: The 3D coordinates of the center of the voxel.
        '''
        i, j, k = ijk
        x = self.origin[0] + (i + 0.5) * self.spacing[0]
        y = self.origin[1] + (j + 0.5) * self.spacing[1]
        z = self.origin[2] + (k + 0.5) * self.spacing[2]
        return x, y, z

def read_scalar_field(fname='', dtype=np.float64):
    """Read ASCII AMIRA scalar field mesh files with high speed.
    
    This function reads in AMIRA scalar fields. Particular attention is given to speeding up reading of 
    the actual data.
    
    Args:
        fname (str): Filename of the Amira Mesh file to be read.
        dtype (numpy.dtype): Data type of the scalar field, default is `np.float64`.

    Raises:
        IOError: If the input file does not have a `.am` or `.AM` suffix.
        
    Returns:
        :class:`~single_cell_parser.scalar_field.ScalarField`: A scalar field object containing the mesh data, origin, extent, spacing, and bounds.
    """
    if not fname.endswith(('.am', '.AM')):
        raise IOError('Input file is not an Amira Mesh file!')

    with dbopen(fname, 'r') as meshFile:
        mesh = None
        extent, dims, bounds, origin, spacing = [], [], [], [], []
        header_lines = []

        # Read until we reach the data section
        for line in meshFile:
            header_lines.append(line)
            if line.strip().startswith('@1'):
                break

        # Parse header info
        for line in header_lines:
            line = line.strip()
            if not line:
                continue
            if 'define' in line and 'Lattice' in line:
                dims = list(map(int, line.split()[-3:]))
                extent = [v for dim in dims for v in (0, dim - 1)]
            elif 'BoundingBox' in line:
                bounds = list(map(float, line.strip(' \t\n,').split()[-6:]))
                origin = [bounds[2 * i] for i in range(3)]
            elif 'Spacing' in line:
                spacing = list(map(float, line.strip(' \t\n,').split()[-3:]))

        # Adjust bounds/origin before reading the data section
        for i in range(3):
            bounds[2 * i + 1] += 0.5 * spacing[i]
            bounds[2 * i] -= 0.5 * spacing[i]
            origin[i] -= 0.5 * spacing[i]

        # Read the remainder of the file as one string and convert to float64
        data_str = meshFile.read()
        data = np.fromstring(data_str, sep=' ', dtype=dtype)

        # Reshape into a 3D array in Fortran order
        mesh = data.reshape(dims, order='F')

        return ScalarField(mesh, origin, extent, spacing, bounds)


def read_landmark_file(landmarkFilename):
    '''Read an AMIRA landmark file

    Args:
        landmarkFilename (str): Filename of the landmark file to be read.

    Raises:
        RuntimeError: If the input file does not have a `.landmarkAscii` suffix.    

    Returns:
        list: (x,y,z) points of landmarks.
    '''
    if not landmarkFilename.endswith('.landmarkAscii'):
        errstr = 'Wrong input format: has to be landmarkAscii format'
        raise RuntimeError(errstr)

    landmarks = []
    with dbopen(landmarkFilename, 'r') as landmarkFile:
        readPoints = False
        for line in landmarkFile:
            stripLine = line.strip()
            if not stripLine:
                continue
            if stripLine[:2] == '@1':
                readPoints = True
                continue
            if readPoints:
                splitLine = stripLine.split()
                x = float(splitLine[0])
                y = float(splitLine[1])
                z = float(splitLine[2])
                landmarks.append((x, y, z))

    return landmarks



def write_landmark_file(fname=None, landmarkList=None):
    '''Write an AMIRA landmark file from 3D coordinates

    Args:
        fname (str): string, name of the output file
        landmarkList (list): list of tuples, each of which holds 3 float coordinates

    Returns:
        None. Writes out the landmark file to :param:`fname`

    Raises:
        RuntimeError: if no file name is given or if the landmark list is empty
        RuntimeError: if the landmarks have the wrong format (not 3 coordinates)

    Example:
        >>> landmarkList = [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0)]
        >>> write_landmark_file('landmarks.landmarkAscii', landmarkList)
    '''
    if fname is None:
        err_str = 'No landmark output file name given'
        raise RuntimeError(err_str)

    nrCoords = 3 if not landmarkList else len(landmarkList[0])
    if nrCoords != 3:
        err_str = 'Landmarks have wrong format! Number of coordinates is ' + str(
            nrCoords) + ', should be 3'
        raise RuntimeError(err_str)

    if not fname.endswith('.landmarkAscii'):
        fname += '.landmarkAscii'

    with dbopen(fname, 'w') as landmarkFile:
        nrOfLandmarks = len(landmarkList)
        header = '# AmiraMesh 3D ASCII 2.0\n\n'+\
                'define Markers ' + str(nrOfLandmarks) + '\n\n'+\
                'Parameters {\n'+\
                '\tNumSets 1,\n'+\
                '\tContentType \"LandmarkSet\"\n'+\
                '}\n\n'+\
                'Markers { float[3] Coordinates } @1\n\n'+\
                '# Data section follows\n'+\
                '@1\n'
        landmarkFile.write(header)
        for pt in landmarkList:
            line = '%.6f %.6f %.6f\n' % (pt[0], pt[1], pt[2])
            landmarkFile.write(line)

def write_landmarks_colorcoded_to_folder(
        basedir,
        landmarks,
        values,
        vmin=0,
        vmax=10,
        vbinsize=.1):
    """Write landmarks to a folder, colorcoded by their values.
    
    Args:
        basedir (str): The directory to write the landmarks to.
        landmarks (numpy.array): The landmarks to write.
        values (numpy.array): The values to color the landmarks by.
        vmin (float): The minimum value to color by.
        vmax (float): The maximum value to color by.
        vbinsize (float): The size of the bins to color by.
        
    Returns:
        None. Writes out the landmarks to the directory :param:`basedir`.
    """
    import os
    from itertools import groupby
    # os.makedirs(basedir)
    lv = 0
    key = lambda x: int(x[1] / vbinsize)
    complete_list = list(zip(landmarks.tolist(), values.tolist()))
    complete_list = sorted(complete_list, key=key)

    with open(os.path.join(basedir, 'out.hx'), 'w') as f:
        f.write(template_init)
        for v, group in groupby(complete_list, key=key):
            v = v * vbinsize
            landmark_name = str(v) + '.landmarkAscii'
            print('writing landmarks for values between {} and {} to {}'.format(
                v, v + vbinsize, landmark_name))
            group = list(zip(*group))
            l, _ = group[0], group[1]
            print(len(l))
            write_landmark_file(os.path.join(basedir, landmark_name), l)
            c = value_to_color(v, vmin=vmin, vmax=vmax)
            f.write(generate_landmark_template(landmark_name, c, lv,
                                               len(l) - 1))
            lv = lv + 1


def value_to_color(v, vmin=0, vmax=1):
    '''Map a value to a color.
        
    See: https://stackoverflow.com/questions/15140072/how-to-map-number-to-color-using-matplotlibs-colormap
    
    Args:
        v (float): The value to map to a color.
        vmin (float): The minimum value of the range. Default is 0.
        vmax (float): The maximum value of the range. Default is 1.
        
    Returns:
        tuple: The RGBA color tuple.
    '''
    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap = cm.inferno
    m = cm.ScalarMappable(norm=norm, cmap=cmap)
    return m.to_rgba(v)[:-1]

def generate_landmark_template(landmark_name, c, vertexviewid, len):
    """Generate a template for a landmark file in Amira.
    
    Args:
        landmark_name (str): The name of the landmark file.
        c (tuple): The color of the landmark.
        vertexviewid (int): The vertex view id.
        len (int): The length of the landmark.
    
    Returns:
        str: The template for the landmark file.
    """
    return template_landmark\
        .replace('LANDMARKNAME', landmark_name)\
        .replace('RRRR', str(c[0]))\
        .replace('GGGG', str(c[1]))\
        .replace('BBBB', str(c[2]))\
        .replace('VERTEXVIEWID', str(vertexviewid))\
        .replace('LEN', str(len))

# Template for landmarks

template_init = '''
# Amira Project 640
# AmiraZIBEdition
# Generated by AmiraZIBEdition 6.4.0
remove -all

# Create viewers
viewer setVertical 0

viewer 0 setTransparencyType 5
viewer 0 setAutoRedraw 0
viewer 0 show
mainWindow show

set hideNewModules 1
[ load ${AMIRA_ROOT}/data/colormaps/glow.col ] setLabel "glow.col"
"glow.col" setIconPosition 0 0
"glow.col" setNoRemoveAll 1
"glow.col" setVar "CustomHelp" {HxColormap256}
"glow.col" fire
"glow.col" setMinMax 0 255
"glow.col" flags setValue 1
"glow.col" shift setMinMax -1 1
"glow.col" shift setButtons 0
"glow.col" shift setEditButton 1
"glow.col" shift setIncrement 0.133333
"glow.col" shift setValue 0
"glow.col" shift setSubMinMax -1 1
"glow.col" scale setMinMax 0 1
"glow.col" scale setButtons 0
"glow.col" scale setEditButton 1
"glow.col" scale setIncrement 0.1
"glow.col" scale setValue 1
"glow.col" scale setSubMinMax 0 1
"glow.col" fire
"glow.col" setViewerMask 16383
'''
template_landmark = '''
set hideNewModules 0
[ load ${SCRIPTDIR}/LANDMARKNAME ] setLabel "LANDMARKNAME"
"LANDMARKNAME" setIconPosition 19 10
"LANDMARKNAME" fire
"LANDMARKNAME" fire
"LANDMARKNAME" setViewerMask 16383

set hideNewModules 0
create HxDisplayVertices "VERTEXVIEWID"
"VERTEXVIEWID" setIconPosition 59 59
"VERTEXVIEWID" setVar "CustomHelp" {HxDisplayVertices}
"VERTEXVIEWID" data connect "LANDMARKNAME"
"VERTEXVIEWID" colormap disconnect
"VERTEXVIEWID" colormap setDefaultColor 0.8 0.5 0.2
"VERTEXVIEWID" colormap setDefaultAlpha 1.000000
"VERTEXVIEWID" colormap activateLocalRange 1
"VERTEXVIEWID" colormap setLocalMinMax 0.000000 0.000000
"VERTEXVIEWID" colormap enableAlpha 1
"VERTEXVIEWID" colormap enableAlphaToggle 1
"VERTEXVIEWID" colormap setAutoAdjustRangeMode 1
"VERTEXVIEWID" colormap setColorbarMinMax 0 120
"VERTEXVIEWID" fire
"VERTEXVIEWID" color setIndex 0 0
"VERTEXVIEWID" drawStyle setValue 2
"VERTEXVIEWID" sphereRadius setMinMax 0 15.9162673950195
"VERTEXVIEWID" sphereRadius setButtons 0
"VERTEXVIEWID" sphereRadius setEditButton 1
"VERTEXVIEWID" sphereRadius setIncrement 1.06108
"VERTEXVIEWID" sphereRadius setValue 7
"VERTEXVIEWID" sphereRadius setSubMinMax 0 15.9162673950195
"VERTEXVIEWID" pointSize setMinMax 1 10
"VERTEXVIEWID" pointSize setButtons 1
"VERTEXVIEWID" pointSize setEditButton 1
"VERTEXVIEWID" pointSize setIncrement 1
"VERTEXVIEWID" pointSize setValue 7
"VERTEXVIEWID" pointSize setSubMinMax 1 10
"VERTEXVIEWID" complexity setMinMax 0 1
"VERTEXVIEWID" complexity setButtons 0
"VERTEXVIEWID" complexity setEditButton 1
"VERTEXVIEWID" complexity setIncrement 0.1
"VERTEXVIEWID" complexity setValue 0.2
"VERTEXVIEWID" complexity setSubMinMax 0 1
"VERTEXVIEWID" textOnOff setValue 0
"VERTEXVIEWID" transparentOnOff setValue 0
"VERTEXVIEWID" displaySelectionOnOff setValue 0
"VERTEXVIEWID" fontSize setMinMax 5 50
"VERTEXVIEWID" fontSize setButtons 1
"VERTEXVIEWID" fontSize setEditButton 1
"VERTEXVIEWID" fontSize setIncrement 1
"VERTEXVIEWID" fontSize setValue 15
"VERTEXVIEWID" fontSize setSubMinMax 5 50
"VERTEXVIEWID" transparency setMinMax 0 1
"VERTEXVIEWID" transparency setButtons 0
"VERTEXVIEWID" transparency setEditButton 1
"VERTEXVIEWID" transparency setIncrement 0.0666667
"VERTEXVIEWID" transparency setValue 0.9
"VERTEXVIEWID" transparency setSubMinMax 0 1
"VERTEXVIEWID" setTextColor 1 1 1
"VERTEXVIEWID" pointStarts0
"VERTEXVIEWID" fire
"VERTEXVIEWID" drawStyle setValue 2
"VERTEXVIEWID" setColor 0 LEN RRRR GGGG BBBB
"VERTEXVIEWID" fire
"VERTEXVIEWID" setViewerMask 16383
"VERTEXVIEWID" select
"VERTEXVIEWID" setPickable 1
'''



