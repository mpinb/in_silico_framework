'''This module contains functions to save simulation data in vtk compatible formats'''

import os
import numpy as np


def convert_amira_surf_to_vtk(surf_file, outname='surface', outdir='.'):
    """Given the path to an amira .surf file, this method converts it to a .vtk surface file.

    Args:
        surf_file (str): path to amira .surf file
        outname (str, optional): Name of the output vtk surface file. Defaults to 'surface'.
        outdir (str, optional): Directory to save the file to. Defaults to '.'.
    """
    with open(surf_file) as f:
        lines = f.readlines()

        vertices_header_n = [
            i for i in range(len(lines)) if "Vertices " in lines[i]
        ][0]

        n_vertices = int(lines[vertices_header_n].split(' ')[-1])
        vertices = lines[vertices_header_n + 1:vertices_header_n + 1 +
                         n_vertices]
        vertices = [e.lstrip().rstrip() for e in vertices]

        tiangle_header_n = [
            i for i in range(len(lines)) if "Triangles " in lines[i]
        ][0]
        n_triangles = int(lines[tiangle_header_n].split(' ')[-1])
        triangles = lines[tiangle_header_n + 1:tiangle_header_n + 1 +
                          n_triangles]
        triangles = [e.lstrip().rstrip() for e in triangles]
        triangles = [
            [str(int(e) - 1)
             for e in triangle.split(' ')]
            for triangle in triangles
        ]  # amira counts from 1, vtk from 0. Offset the off-by-one error

        with open(os.path.join(outdir, outname) + '.vtk', 'w+') as of:
            of.write(
                "# vtk DataFile Version 4.0\nsurface\nASCII\nDATASET POLYDATA\n"
            )
            of.write("POINTS {} float\n".format(n_vertices))
            for vert in vertices:
                of.write(vert)
                of.write('\n')

            of.write('\nPOLYGONS {} {}\n'.format(n_triangles,
                                                 (3 + 1) * n_triangles))
            for tri in triangles:
                of.write("3 " + " ".join(tri))
                of.write('\n')


def write_vtk_pointcloud_file(out_name=None,
                              out_dir='.',
                              points=None,
                              scalar_data=None,
                              scalar_data_names=None):
    '''
    write Amira landmark file
    landmarkList has to be iterable of tuples,
    each of which holds 3 float coordinates
    '''
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    if scalar_data is not None:
        scalar_data = np.array(scalar_data)
        assert scalar_data.shape[1] == len(points)
        assert len(
            scalar_data.shape
        ) == 2, "Please pass scalar data as a 2D array, where each element defines some type of scalar data per point."
        assert len(scalar_data_names) == scalar_data.shape[
            0], "You did not pass as many names as scalar data arrays. scalar data: {}, amount of names: {}".format(
                scalar_data.shape[0], len(scalar_data_names))

    def header_(out_name_=out_name):
        h = "# vtk DataFile Version 4.0\n{}\nASCII\nDATASET POLYDATA\n".format(
            out_name_)
        return h

    def points_str_(points_):
        p = ""
        for p_ in points_:
            line = ""
            for comp in p_:
                line += str(round(comp, 3))
                line += " "
            p += str(line[:-1])
            p += "\n"
        return p

    def scalar_str_(scalar_data):
        diameter_string = ""
        for d in scalar_data:
            diameter_string += str(d)
            diameter_string += "\n"
        return diameter_string

    # write out all data to .vtk file
    with open(os.path.join(out_dir, out_name) + ".vtk", "w+",
              encoding="utf-8") as of:
        of.write(header_(out_name))

        # Points
        of.write("POINTS {} float\n".format(len(points)))
        of.write(points_str_(points))

        of.write("VERTICES {} {}\n".format(len(points), 2 * len(points)))
        for i in range(len(points)):
            of.write("1 {}\n".format(i))

        if scalar_data is not None:
            for scalar_name, scalar_data in zip(scalar_data_names, scalar_data):
                of.write(
                    "POINT_DATA {}\nSCALARS {} float 1\nLOOKUP_TABLE default\n".
                    format(len(points), scalar_name))
                of.write(scalar_str_(scalar_data))