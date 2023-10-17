import os
import re
from random import randrange
from .definitions import ROOT_DIR
from . import transformation as tr
import cloudpickle as pickle
import numpy as np


class SaveData:
    def __init__(self, data_file):
        self.data_file = data_file

    def dump(self, data):
        f = open(self.data_file, 'wb')
        pickle.dump(data, f)
        f.close()

    def load(self):
        if os.path.isfile(self.data_file) == False:
            return None
        f = open(self.data_file, 'rb')
        return pickle.load(f)


def get_am_paths_from_hx(hx_path, verbose=False):
    out = []
    with open(hx_path) as f:
        for l in f.readlines():
            if '${SCRIPTDIR}' in l:
                path = l.strip(' []').split(' ')[1]
                if verbose:
                    print(path)
                out.append(path)
    return out


def get_files_by_folder(path_to_folder, file_extension=""):
    return [path_to_folder + "/" + f for f in os.listdir(path_to_folder) if f.endswith(file_extension)]


def make_directories(path):
    if path is None:
        path = ROOT_DIR + "/output_" + str(randrange(100))
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def get_slice_name(am_path, image_file):
    name = list(get_am_image_match([am_path], [image_file]).keys())
    if len(name) == 1:
        return os.path.basename(name[0])
    elif len(name) == 0:
        return "No name found"
    elif len(name) > 1:
        raise ValueError("multiple matches found!")


def get_file_name_from_path(path_to_file):
    return os.path.basename(path_to_file)


def get_am_image_match(am_paths, tif_paths):
    '''naming convention: #todo'''
    am_image_match = {}
    for am_path in am_paths:
        am_file_name = get_file_name_from_path(am_path)
        slice_name = re.findall(r'[sS]\d+', am_file_name)[0]
        for tif_path in tif_paths:
            tif_file_name = os.path.basename(tif_path)
            tif_file_name_slice_identifier = re.findall(r'[sS]\d+', tif_file_name)[0]
            if int(slice_name.strip('Ss')) == int(tif_file_name_slice_identifier.strip('Ss')):
                am_image_match[am_path] = tif_path
    return am_image_match


def get_nearest_point(point, points):
    neighbours = []
    width = 10
    while len(neighbours) == 0:
        neighbours = get_neighbours_of_point(point, points, width)
        width = width + width
    distances = [tr.get_distance(point, neighbour) for neighbour in neighbours]
    nearest_point = neighbours[distances.index(min(distances))]
    return nearest_point


def get_neighbours_of_point(point, points, width=10):
    points = np.array(points)
    neighbours = points
    for i in range(len(point)):
        neighbours = neighbours[neighbours[:, i] >= point[i] - width]
        neighbours = neighbours[neighbours[:, i] <= point[i] + width]
    return neighbours.tolist()


def contains(point, cube):
    return [point[i] for i in range(3) if cube[i][0] <= point[i] <= cube[i][1]] == point


def get_size_of_object(obj):
    return len(pickle.dumps(obj))


def compare_points(p1, p2):
    assert (len(p1) == len(p2))
    return max([np.abs(pp1 - pp2) for pp1, pp2 in zip(p1, p2)])


def are_same_points(p1, p2):
    if p1 == p2:
        return True
    else:
        return False


def create_image_stack_dict_of_slice(folder_path, subfolders = None):
    """
    :param channel: subfolder in folder path containing the images of the specified channel.
    :param folder_path: path to the folder of slice images stack. eg. : ../3d/S023/
    :return: dict of path of tif files with the keys corresponding to part of image names.
    (The key extracted from the image name which must reasonably corresponds to the z_coordinate of
    am_points in am_file)
    """
    tif_folder_path = folder_path
    if subfolders:
        tif_folder_path = get_files_by_folder(tif_folder_path, subfolders)
    assert(len(tif_folder_path) == 1)
    tif_folder_path = tif_folder_path[0]
    slice_image_stack_list = get_files_by_folder(tif_folder_path, "tif")
    slice_image_stack_dict = {int(path.split('/')[-1].split('.')[0].split('_')[-1].strip('z')):
                              path for path in slice_image_stack_list}
    return slice_image_stack_dict
