'''
Created on Mar 27, 2012

@author: regger
'''
import numpy as np


class ScalarField(object):
    '''
    implements 3D scalar field based on numpy array
    used for e.g. sub-cellular synapse distributions
    modeled after vtkImageData; i.e. regular mesh
    with extent[6], spacing[3], and boundingBox[xMin, xMax, ... , zMax]
    '''

    mesh = None
    origin = ()
    extent = ()
    spacing = ()
    boundingBox = ()

    def __init__(self, mesh=None, origin=(), extent=(), spacing=(), bBox=()):
        '''
        Constructor
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
        '''
        resize mesh to bounding box around non-zero voxels
        also updates extent and boundingBox
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
        xMax = self.origin[0] + iMax * dx
        yMax = self.origin[1] + jMax * dy
        zMax = self.origin[2] + kMax * dz
        self.origin = xMin, yMin, zMin
        self.boundingBox = xMin, xMax, yMin, yMax, zMin, zMax
        newMesh = np.empty(shape=newDims)
        newMesh[:, :, :] = self.mesh[iMin:iMax + 1, jMin:jMax + 1,
                                     kMin:kMax + 1]
        self.mesh = np.copy(newMesh)
        del newMesh

    def get_scalar(self, xyz):
        '''
        does perform range checking; however, if outside
        of bounding box, simply returns 0, so use with caution!
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
        '''
        does NOT perform range checking; index may be invalid!
        '''
        x, y, z = xyz
        i = int((x - self.origin[0]) // self.spacing[0])
        j = int((y - self.origin[1]) // self.spacing[1])
        k = int((z - self.origin[2]) // self.spacing[2])
        return i, j, k

    def get_voxel_bounds(self, ijk):
        '''
        returns bounding box of voxel given by indices
        i,j,k. Does NOT perform bounds checking!
        '''
        i, j, k = ijk
        xMin = self.origin[0] + i * self.spacing[0]
        xMax = self.origin[0] + (i + 1) * self.spacing[0]
        yMin = self.origin[1] + j * self.spacing[1]
        yMax = self.origin[1] + (j + 1) * self.spacing[
            1]  # in case this breaks - it used to say spacing[01] (rieke, 08022021)
        zMin = self.origin[2] + k * self.spacing[2]
        zMax = self.origin[2] + (k + 1) * self.spacing[2]
        return xMin, xMax, yMin, yMax, zMin, zMax
