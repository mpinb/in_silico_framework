from visualize.cell_to_ipython_animation import display_animation
from IPython.display import clear_output


def test_display_animation_can_be_called_with_list_of_files():
    display_animation(['1', '2'])
    clear_output(wait=True)


def test_display_animation_can_be_called_with_globstring():
    display_animation('1*')
    clear_output(wait=True)