import logging

log = logging.getLogger("ISF").getChild(__name__)


def scale_apical(cell, scale=None, compartment='ApicalDendrite'):
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
    log.info('Scaled {:d} apical sections...'.format(scaleCount))
    return cell