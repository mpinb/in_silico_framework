# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.

"""
Visualization utilities.
"""

import os
import shutil
import jinja2
import IPython
import glob
import numpy as np
from base64 import b64encode
import subprocess
from data_base.utils import mkdtemp
from mpl_toolkits.mplot3d.proj3d import proj_transform
from matplotlib.patches import FancyArrowPatch
from matplotlib.text import Annotation
from mpl_toolkits.mplot3d.axes3d import Axes3D
from matplotlib.colors import Normalize
import matplotlib.cm as cm


def write_video_from_images(
    images,
    out_path,
    fps=24,
    images_format='.png',
    quality=5,
    codec='mpeg4',
    auto_sort_paths=True):
    '''Creates a video from a set of images. 
    
    Images must be specified as a list of images, a directory with images or a list of directories with images.
    Uses glob pattern matching if a directory of images is specified (allows for using the "*" as a wildcard). 

    Note:
        Globbing is not enabled by default on Windows machines.
        If running this command on windows, please set the :paramref:`glob` argument to False and specify a non-glob type match pattern.
    
    Args:
        images (list | str): list of images, a directory with images or a list of directories with images
        out_path (str): dir where the video will be generated + name of the video
        fps (int): frames per second
        images_format (str): .png, .pdf, .jpg ...
        quality (int): quality of the video. Only used with the mpeg4 codec
        codec (str): codec to use. Default is mpeg4.
        auto_sort_paths (bool): paths to images sorted

    Returns:
        None. Writes the video to the specified path.
    '''
    subprocess.call(["module load", "ffmpeg"], shell=True)

    if not out_path.endswith('.mp4'):
        raise ValueError('output path must be the path to an mp4 video!')
    # make it a list if we want to auto_sort_paths since this is what find_files_and_order_them expects
    if isinstance(images, str) and auto_sort_paths == True:
        if not os.path.isdir(images):
            raise ValueError(
                'images must be a path to a folder or a list of folders or a list of images'
            )
        images = [images]

    # call ffmpeg directly
    if isinstance(images,
                  str) and os.path.isdir(images) and auto_sort_paths == False:
        out = subprocess.call([
            "ffmpeg", "-y", "-r",
            str(fps), "-i", images + "/%*" + images_format, "-vcodec", codec,
            "-q:v",
            str(quality), "-r",
            str(fps), out_path
        ])
    #
    elif isinstance(images, list):
        if auto_sort_paths:
            listFrames = find_files_and_order_them(images, images_format)
        else:
            listFrames = images
        with mkdtemp() as temp_folder:
            for i, file in enumerate(listFrames):
                new_name = str(i + 1).zfill(6) + images_format
                shutil.copy(file, os.path.join(temp_folder, new_name))
            out = subprocess.call([
                "ffmpeg", "-y", "-r",
                str(fps), "-i",
                str(temp_folder + "/%*" + images_format), "-vcodec",
                str(codec), "-q:v",
                str(quality), "-r",
                str(fps),
                str(out_path)
            ])
    else:
        raise ValueError(
            "images must be a list of images, a directory with images or a list of directories with images"
        )

    if out == 0:
        print('Video created successfully!')
    else:
        print('Something went wrong. Make sure:')
        print(
            ' - the module ffmpeg is loaded, otherwise use the command: module load ffmpeg'
        )
        print(
            ' - the param images is a list of images, a directory with images or a list of directories with images'
        )
        print(' - images_format is specified properly')


def write_gif_from_images(
        images,
        out_path,
        interval=40,
        images_format='.png',
        auto_sort_paths=True):
    '''Creates a gif from a set of images, and saves it to :paramref:`out_path`.

    Args:
        images (list | str): list of images, a directory with images or a list of directories with images
        out_path (str): dir where the video will be generated + name of the gif
        interval (int | float): time interval between frames (ms)
        images_format (str): .png, .pdf, .jpg ...
        auto_sort_paths (bool): paths to images sorted

    Returns:
        None. Writes the gif to the specified path.
    '''
    import six
    if six.PY3:
        from PIL import Image
    else:
        raise EnvironmentError(
            "PIL.Image could not be imported. Writing gifs will not work. Try on a Python 3 environment with PIL installed."
        )

    if not out_path.endswith('.gif'):
        raise ValueError('output path must be the path to a gif!')

    # make it a list if we want to auto_sort_paths since this is what find_files_and_order_them expects
    if isinstance(images, str) and (auto_sort_paths == True):
        if not os.path.isdir(images):
            raise ValueError(
                'images must be a path to a folder or a list of folders or a list of images'
            )
        images = [images]

    # call ffmpeg directly
    if isinstance(images, str) and os.path.isdir(images) and (auto_sort_paths
                                                              == False):
        frames = []
        for f in os.listdir(images):
            if f.endswith(images_format):
                frames.append(Image.open(os.path.join(images, f)))
        # Save into a GIF file that loops forever
        frames[0].save(out_path,
                       format='GIF',
                       append_images=frames[1:],
                       save_all=True,
                       duration=interval,
                       loop=0)
    elif isinstance(images, list):
        if auto_sort_paths:
            listFrames = find_files_and_order_them(images, images_format)
        else:
            listFrames = images
        with mkdtemp() as temp_folder:
            for i, file in enumerate(listFrames):
                new_name = str(i + 1).zfill(6) + images_format
                shutil.copy(file, os.path.join(temp_folder, new_name))
                frames = []
                for f in os.listdir(temp_folder):
                    if f.endswith(images_format):
                        frames.append(Image.open(os.path.join(images, f)))
                # Save into a GIF file that loops forever
                frames[0].save(out_path,
                               format='GIF',
                               append_images=frames[1:],
                               save_all=True,
                               duration=interval,
                               loop=0)
    else:
        raise ValueError(
            "images must be a list of images, a directory with images or a list of directories with images"
        )
    print('Gif created successfully!')


def _load_base64(filename, extension='png'):
    """Load a base64 file from a filename.

    Used in :py:meth:`display_animation_from_images` to embed animations.
    
    See: https://github.com/jakevdp/JSAnimation/blob/master/JSAnimation/html_writer.py
    """
    with open(filename, 'rb') as f:
        data = f.read()
    return 'data:image/{0};base64,{1}'.format(
        extension,
        b64encode(data).decode('ascii'))


def display_animation_from_images(
    files,
    interval=10,
    style=False,
    animID=None,
    embedded=False):
    '''Creates an IPython animation out of files specified in a globstring or a list of paths.

    Args:
        files (list | str): list of images, a directory with images or a list of directories with images
        interval (int | float): time interval between frames in ms.
        style (bool): whether to use the default style or not.
        animID (int): unique integer to identify the animation in the javascript environment of IPython
        embedded (bool): whether to embed the images in the html file or not.

    Returns:
        None. Displays the animation in the notebook.

    Attention: 
        The paths need to be relative to the location of the ipynb / html file, since
        the are resolved in the browser and not by python
    '''
    if animID is None:
        animID = np.random.randint(
            10000000000000)  # needs to be unique within one ipynb
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))
    template = env.get_template('animation_template.html')

    if isinstance(files, str):
        if os.path.isdir(files):  # folder provieded --> convert to globstring
            files = os.path.join(files, '*.png')
        listFrames = sorted(glob.glob(files))
    else:
        listFrames = files
    if embedded:
        listFrames = [_load_base64(f) for f in listFrames]
    htmlSrc = template.render(ID=animID,
                              listFrames=listFrames,
                              interval=interval,
                              style=style)
    IPython.display.display(IPython.display.HTML(htmlSrc))


def find_files_and_order_them(files, files_format='.png'):
    '''Find files in a list of directories or a directory and order them.
    
    These files are in order, and takes into account
    if the name of the file is a number (1 would go before 10 even if the number of the file is not 0-padded). 
    If the files param was a list of directories, the files are in order within each directory but the
    directories order is maintained.

    Args:
        files (list | str): list of files, list of directories, or a directory.
        files_format (str): format of the files to get (e.g. '.png', '.jpg')
    
    Returns:
        list: List of the files contained in the files argument. 
    
    Example:
        If files is a list of directories [dir_a,  dir_b, dir_c] containing the following files:

        .. list-table:: Example of directory contents
           :header-rows: 1

           * - dir_a
             - dir_b
             - dir_c
           * - 100
             - world
             - C
           * - 10
             - 30
             - B
           * - 2
             - 5
             - A
           * - 1
             - hello
             - 70
           * - file
             - 200
             - 9
    
        The result would be:
        1, 2, 10, 100, file, 5, 30, 200, hello, world, 9, 70, A, B, C        
    '''

    if isinstance(files, str):
        if os.path.isdir(files):  # folder provided --> convert to globstring
            files = os.path.join(files, '*' + files_format)
        listFiles = sorted(glob.glob(files))  # list of files
        files_no_number_name = [
        ]  # files whose name does not starts with a number
        files_number_name = []  # files whose name starts with a number
        numbers = []  # list of numbers in the files names to be ordered
        for file in listFiles:
            _, file_name = os.path.split(file)
            file_name, _ = os.path.splitext(file_name)
            try:
                number = int(file_name)
                files_number_name.append(file)
                numbers.append(number)
            except:
                files_no_number_name.append(file)
        idxs_in_order = sorted(range(len(numbers)), key=lambda k: numbers[k])
        files_number_name_in_order = [
            files_number_name[i] for i in idxs_in_order
        ]
        listFiles = files_number_name_in_order + files_no_number_name

    elif isinstance(files, list):
        listFiles = []
        for elem in files:
            listFiles += find_files_and_order_them(elem, files_format)
    return listFiles


class Arrow3D(FancyArrowPatch):
    """Draw a 3D annotation arrow on a matplotlib 3D plot
    
    See: https://gist.github.com/WetHat/1d6cd0f7309535311a539b42cccca89c
    
    Attributes:
        _xyz (tuple): the x, y, z coordinates of the arrow
        _dxdydz (tuple): the dx, dy, dz coordinate difference of the arrow, i.e. where it points to relative to its origin.
    """
    def __init__(self, x, y, z, dx, dy, dz, *args, **kwargs):
        """
        Args:
            x (float): x coordinate of the arrow starting point.
            y (float): y coordinate of the arrow starting point.
            z (float): z coordinate of the arrow starting point.
            dx (float): x coordinate difference of the arrow direction.
            dy (float): y coordinate difference of the arrow direction.
            dz (float): z coordinate difference of the arrow direction.
            *args: Additional positional arguments passed to FancyArrowPatch.
            **kwargs: Additional keyword arguments passed to FancyArrowPatch.
        """
        super().__init__((0, 0), (0, 0), *args, **kwargs)
        self._xyz = (x, y, z)
        self._dxdydz = (dx, dy, dz)

    def draw(self, renderer):
        """Draw the arrow."""
        x1, y1, z1 = self._xyz
        dx, dy, dz = self._dxdydz
        x2, y2, z2 = (x1 + dx, y1 + dy, z1 + dz)

        xs, ys, zs = proj_transform((x1, x2), (y1, y2), (z1, z2), self.axes.M)
        self.set_positions((xs[0], ys[0]), (xs[1], ys[1]))
        super().draw(renderer)

    def do_3d_projection(self, renderer=None):
        """Project the arrow onto the Axes3D object.
        """
        x1, y1, z1 = self._xyz
        dx, dy, dz = self._dxdydz
        x2, y2, z2 = (x1 + dx, y1 + dy, z1 + dz)

        xs, ys, zs = proj_transform((x1, x2), (y1, y2), (z1, z2), self.axes.M)
        self.set_positions((xs[0], ys[0]), (xs[1], ys[1]))

        return np.min(zs)


def _arrow3D(ax, x, y, z, dx, dy, dz, *args, **kwargs):
    '''Add an 3d arrow to an Axes3D instance.'''

    arrow = Arrow3D(x, y, z, dx, dy, dz, *args, **kwargs)
    ax.add_artist(arrow)


def draw_arrow(
        morphology,
        ax,
        highlight_section=None,
        highlight_x=None,
        highlight_arrow_kwargs=None,
        arrow_size=50):
    """Highlight a morphology section with an :py:class:`Arrow3D`.

    This method is used by :py:class:`CellMorphologyVisualizer` to annotate morphology sections.
    
    Args:
        morphology (pd.DataFrame): The morphology dataframe containing the coordinates of the sections.
        ax (matplotlib.axes.Axes): The matplotlib axes object to draw the arrow on.
        highlight_section (int, optional): The section index to highlight. If None, no section is highlighted. Default is ``None``.
        highlight_x (float, optional): The x-coordinate within the section to place the arrow. If None, the arrow is placed at the section's midpoint. Default is ``None``.
        highlight_arrow_kwargs (dict, optional): Additional keyword arguments to pass to the :py:class:`Arrow3D` constructor. Default is ``None``.
        arrow_size (int, optional): The size of the arrow. Default is 50.
    
    Returns:
        None
    
    """

    assert type(
        highlight_section
    ) == int, "Please provide the section index as an argument for highlight_arrow. You passed {}".format(
        highlight_section)
    assert highlight_section in morphology[
        'sec_n'], "The given section id is not present in the cell morphology"

    setattr(Axes3D, 'arrow3D', _arrow3D)
    if highlight_arrow_kwargs is None:
        highlight_arrow_kwargs = {}

    # overwrite defaults if they were set
    x = dict(mutation_scale=20, ec='black', fc='white')
    x.update(highlight_arrow_kwargs)
    highlight_arrow_kwargs = x

    morphology = morphology.copy()
    morphology = morphology.fillna(0)  # soma section gets 0 as section ID
    df = morphology[morphology['sec_n'] == highlight_section]
    if highlight_x is not None:
        index = np.argmin(np.abs(df.relPts - highlight_x))
        x, y, z = df.iloc[index][['x', 'y', 'z']]
    elif highlight_section is not None:
        x, y, z = morphology[morphology['sec_n'] == highlight_section][[
            'x', 'y', 'z'
        ]].mean(axis=0)
    else:
        raise ValueError(
            "Please provide either a section index to highlight, or a distance from soma x."
        )

    # get start of arrow: point down
    start_x, start_y, start_z = x, y, z
    dx, dy, dz = 0, 0, 0
    ddx = ddy = 0
    if 'orientation' in highlight_arrow_kwargs:
        orientation = highlight_arrow_kwargs['orientation']
        del highlight_arrow_kwargs['orientation']
        if 'x' in orientation:
            start_x += arrow_size
            dx -= arrow_size
        if 'y' in orientation:
            start_y += arrow_size
            dy -= arrow_size
        if 'z' in orientation:
            start_z += arrow_size
            dz -= arrow_size
    else:
        # point down by default
        start_z += arrow_size
        dz -= arrow_size

    if 'rotation' in highlight_arrow_kwargs:
        print("rotating arrow")
        alpha = highlight_arrow_kwargs['rotation']
        del highlight_arrow_kwargs['rotation']
        dx2, dz2 = np.dot(
            np.array([[np.cos(alpha), -np.sin(alpha)],
                      [np.sin(alpha), np.cos(alpha)]]), [dx, dz])
        start_x = start_x - dx2 + dx
        start_z = start_z - dz2 + dz
        dx = dx2
        dz = dz2

    #print(start_x, start_y)
    ax.arrow3D(start_x, start_y, start_z, dx, dy, dz, **highlight_arrow_kwargs)



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
