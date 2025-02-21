'''
Implementation of 3D scalar fields based on numpy arrays.

Note that this class is identical to :py:class:`single_cell_parser.scalar_field.ScalarField`.
It is duplicated here for package independence.
'''
import numpy as np

__author__ = 'Robert Egger'
__date__ = '2012-03-27'

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

    mesh = None
    origin = ()
    extent = ()
    spacing = ()
    boundingBox = ()

    def __init__(self, mesh=None, origin=(), extent=(), spacing=(), bBox=()):
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


        # if self.mesh is not None:
        #     self.resize_mesh()

    def resize_mesh(self):
        '''Resizes mesh to non-zero scalar data.
         
        This method resizes the mesh such that the bounding box 
        wraps around voxels that contain non-zero scalar data.
        Also updates :py:attr:`extent` and :py:attr:`boundingBox`
        '''
        roi = np.nonzero(self.mesh)
        iMin = np.min(roi[0])
        iMax = np.max(roi[0])
        jMin = np.min(roi[1])
        jMax = np.max(roi[1])
        kMin = np.min(roi[2])
        kMax = np.max(roi[2])
        self.extent = 0, iMax - iMin, 0, jMax - jMin, 0, kMax - kMin
        newDims = self.extent[1] + 1, self.extent[3] + 1, self.extent[5] + 1
        dx = self.spacing[0]
        dy = self.spacing[1]
        dz = self.spacing[2]
        xMin = self.origin[0] + iMin * dx
        yMin = self.origin[1] + jMin * dy
        zMin = self.origin[2] + kMin * dz
        xMax = self.origin[0] + (iMax + 1) * dx
        yMax = self.origin[1] + (jMax + 1) * dy
        zMax = self.origin[2] + (kMax + 1) * dz
        self.origin = xMin, yMin, zMin
        self.boundingBox = xMin, xMax, yMin, yMax, zMin, zMax
        newMesh = np.empty(shape=newDims)
        newMesh[:, :, :] = self.mesh[iMin:iMax + 1, jMin:jMax + 1,
                                     kMin:kMax + 1]
        self.mesh = np.copy(newMesh)
        del newMesh

    def get_scalar(self, xyz):
        '''Fetch the scalar value of the voxel containing the point xyz.

        Warning:
            Returns 0 if :paramref:`xyz` is outside the bounding box.

        Args:
            xyz (tuple): The 3D coordinates of the point.

        Returns:
            float: The scalar value of the voxel containing the point, 0 if outside bounding box.
        '''
        x, y, z = xyz
        delta = 1.0e-6
        if x < self.boundingBox[0] + delta:
            return None
        if x > self.boundingBox[1] - delta:
            return None
        if y < self.boundingBox[2] + delta:
            return None
        if y > self.boundingBox[3] - delta:
            return None
        if z < self.boundingBox[4] + delta:
            return None
        if z > self.boundingBox[5] - delta:
            return None
        i = int((x - self.origin[0]) // self.spacing[0])
        j = int((y - self.origin[1]) // self.spacing[1])
        k = int((z - self.origin[2]) // self.spacing[2])
        return self.mesh[i, j, k]

    def is_in_bounds(self, xyz):
        """Check if point is within bounding box of mesh.
        
        Args:
            xyz (tuple): The 3D coordinates of the point.
            
        Returns:
            bool: True if point is within bounding box, False otherwise."""
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
            If :paramref:`xyz` is outside the bounding box, the index will be out of bounds for the :py:attr:`mesh`.

        Args:
            xyz (tuple): The 3D coordinates of the point.

        Returns:
            tuple: The :py:attr:`mesh` index of the voxel containing the point. 
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
        yMax = self.origin[1] + (j + 1) * self.spacing[1]  # was spacing[01]
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
