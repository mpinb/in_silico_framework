import os
import cloudpickle
import compatibility
import numpy as np
from . import parent_classes
from single_cell_parser.cell import Cell
from single_cell_parser.serialize_cell import save_cell_to_file
from single_cell_parser.serialize_cell import load_cell_from_file


def check(obj):
    '''checks whether obj can be saved with this dumper'''
    return isinstance(obj, Cell)  #basically everything can be saved with pickle


class Loader(parent_classes.Loader):

    def get(self, savedir):
        return load_cell_from_file(os.path.join(savedir, 'cell'))


def dump(obj, savedir):
    save_cell_to_file(os.path.join(savedir, 'cell'), obj)

    with open(os.path.join(savedir, 'Loader.pickle'), 'wb') as file_:
        cloudpickle.dump(Loader(), file_)
    #compatibility.cloudpickle_fun(Loader(), file_)