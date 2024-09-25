"""Scale the apical dendrite of a cell."""
import logging
from biophysics_fitting.utils import augment_cell_with_detailed_labels
logger = logging.getLogger("ISF").getChild(__name__)


def scale_apical(cell, scale=None, compartment='ApicalDendrite'):
    '''Scale the apical dendrite of a cell.

    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The cell to scale.
        scale (float): The scaling factor.
        compartment (str): The compartment to scale.
            If "ApicalDendrite", the cell is assumed to have sections with label "ApicalDendrite".
            If "Trunk", the cell is assumed to have ``detailed_labels`` assigned manually, or by :py:meth:`biophysics_fitting.utils.augment_cell_with_detailed_labels`.
            Currently, only "ApicalDendrite" and "Trunk" are supported compartments.
    
    Returns:
        :class:`~single_cell_parser.cell.Cell`: The scaled cell.

    Raises:
        ValueError: If the compartment is not "ApicalDendrite" or "Trunk".
    '''
    if compartment == 'ApicalDendrite':
        return scale_apical_dendrite(cell, scale=scale, compartment='ApicalDendrite')
    elif compartment == 'Trunk':
        return scale_by_detailed_compartment(cell, trunk=scale)
    else:
        raise ValueError()
    
def scale_apical_dendrite(cell, scale=None, compartment='ApicalDendrite'):
    '''Scales the apical dendrite of a cell.

    Assumes the cell has sections with label "ApicalDendrite".
    If not, nothing gets scaled.

    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The cell to scale.
        scale (float): The scaling factor.

    Returns:
        :class:`~single_cell_parser.cell.Cell`: The scaled cell.
    '''

    # This is the function used to scale the apical dendrite in the following
    # optimizations:
    
    # 20190117_fitting_CDK_morphologies_Kv3_1_slope_variable_dend_scale.ipynb
    # 20190125_fitting_CDK_morphologies_Kv3_1_slope_variable_dend_scale_step.ipynb
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
    '''Scales subcellular compartments based on ``detailed_labels``.

    If not yet assigned, detailed labels are assigned by :py:meth:`biophysics_fitting.utils.augment_cell_with_detailed_labels`.
    and include ``basal``, ``trunk``, ``tuft``, and ``oblique``.
    
    Attention:
        For non-L5PT neurons or L5PT neurons from any other brain area than barrel cortex, 
        make sure :py:meth:`~biophysics_fitting.utils.augment_cell_with_detailed_labels` 
        assigns labels as you want them to be.
        
        Alternatively, assign them manually with the :py:attr:`biophysics_fitting.cell.Cell.sections.label_detailed` attribute.

    Args:
        cell (:class:`~single_cell_parser.cell.Cell`): The cell to scale.
        **kwargs (dict): Detailed lables with associated scaling factors.

    Returns:
        :class:`~single_cell_parser.cell.Cell`: The scaled cell.
    '''
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