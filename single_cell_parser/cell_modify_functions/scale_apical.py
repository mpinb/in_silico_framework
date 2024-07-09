import logging
from biophysics_fitting.utils import augment_cell_with_detailed_labels
logger = logging.getLogger("ISF").getChild(__name__)


def scale_apical(cell, scale=None, compartment='ApicalDendrite'):
    if compartment == 'ApicalDendrite':
        return scale_apical_dendrite(cell, scale=scale, compartment='ApicalDendrite')
    elif compartment == 'Trunk':
        return scale_by_detailed_compartment(cell, trunk = scale)
    else:
        raise ValueError()
    
def scale_apical_dendrite(cell, scale=None, compartment='ApicalDendrite'):
    '''
    This is the function used to scale the apical dendrite in the following
    optimizations:
    
    20190117_fitting_CDK_morphologies_Kv3_1_slope_variable_dend_scale.ipynb
    20190125_fitting_CDK_morphologies_Kv3_1_slope_variable_dend_scale_step.ipynb
    
    scale apical diameters depending on
    distance to soma; therefore only possible
    after creating complete cell
    '''
    import neuron
    h = neuron.h
    scaleCount = 0
    for sec in cell.sections:
        if sec.label == 'ApicalDendrite':
            dist = cell.distance_to_soma(sec, 1.0)
            scaleCount += 1
            for i in range(sec.nrOfPts):
                oldDiam = sec.diamList[i]
                newDiam = scale * oldDiam
                h.pt3dchange(i, newDiam, sec=sec)
    logger.info('Scaled {:d} apical sections...'.format(scaleCount))
    return cell

def scale_by_detailed_compartment(cell, **kwargs):
    '''allows scaling subcellular compartments discriminating
    basal, trunk, tuft, oblique. 
    
    Uses biophysics_fitting.utils.augment_cell_with_detailed_labels
    to auto-detect the labels from the morphology. For non-L5PT neurons 
    or L5PT neurons from any other brain area than barrel cortex, 
    make sure this function assignes labels as you want them to be.'''
    # check if detailed labels are available
    try:
        cell.sections[0].label_detailed
    except AttributeError:
        augment_cell_with_detailed_labels(cell)
    
    # input validation
    compartments = {sec.label_detailed for sec in cell.sections}
    for k in kwargs:
        assert k in compartments
        
    # scaling
    import neuron
    h = neuron.h
    scaleCount = 0
    for sec in cell.sections:
        if sec.label_detailed in kwargs:
            scale = kwargs[sec.label_detailed]
            scaleCount += 1
            for i in range(sec.nrOfPts):
                oldDiam = sec.diamList[i]
                newDiam = scale * oldDiam
                h.pt3dchange(i, newDiam, sec=sec)
    logger.info('Scaled {:d} sections...'.format(scaleCount)) 
    return cell