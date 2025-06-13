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
Scale the apical dendrite of morphology 86.

This is used by the Oberlaender lab in Bonn, and is unlikely to be needed by anyone else.

:skip-doc:
"""

import logging

logger = logging.getLogger("ISF").getChild(__name__)


def scale_apical_morph_86(cell):
    '''
    This is the method robert has used for scaling the apical dendrite of CDK morphology 86
    
    scale apical diameters depending on
    distance to soma; therefore only possible
    after creating complete cell
    
    :skip-doc:
    '''
    import neuron
    h = neuron.h
    dendScale = 2.5
    scaleCount = 0
    for sec in cell.sections:
        if sec.label == 'ApicalDendrite':
            dist = cell.distance_to_soma(sec, 1.0)
            if dist > 1000.0:
                continue
            # for cell 86:
            if scaleCount > 32:
                break
            scaleCount += 1
            #            dummy = h.pt3dclear(sec=sec)
            for i in range(sec.nrOfPts):
                oldDiam = sec.diamList[i]
                newDiam = dendScale * oldDiam
                h.pt3dchange(i, newDiam, sec=sec)
                # x, y, z = sec.pts[i]
                # sec.diamList[i] = sec.diamList[i]*dendScale
                # d = sec.diamList[i]
                # dummy = h.pt3dadd(x, y, z, d, sec=sec)

    logger.info('Scaled {:d} apical sections...'.format(scaleCount))
    return cell