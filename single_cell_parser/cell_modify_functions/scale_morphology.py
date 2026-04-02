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
    :param:`cell` to be closer to the target morphology. The scaling is done by linearly
    interpolating each point between the current and target morphology.

    A :param:`scale` factor of 0.0 will result in the current morphology, while a factor of 1.0
    will result in the target morphology. Anything in between will be a linear interpolation.

    The target morphology must contain the same amount of points as the current morphology, 
    (ignoring AIS and Myelin), and the points must be in the same order.
    
    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The cell to scale.
        scale (float): The scaling factor.
        target_morphology (str): The path to the target morphology file.
        
    Returns:
        :class:`~single_cell_parser.cell.Cell`: The scaled cell.
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
