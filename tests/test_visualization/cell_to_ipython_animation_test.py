import numpy as np
from .context import *
from visualize.cell_to_ipython_animation import *


def test_display_animation_can_be_called_with_list_of_files():
    display_animation(['1', '2'])


def test_display_animation_can_be_called_with_globstring():
    display_animation('1*')

    # maybe test real functionality in ipynb?
