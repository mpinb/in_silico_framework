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