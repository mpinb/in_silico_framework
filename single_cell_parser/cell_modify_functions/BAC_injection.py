from biophysics_fitting.setup_stim import setup_BAC


def BAC_injection(cell, dist=None):
    '''
    This injects the BAC stimulus as defined in Hay et. al. 2011 at a specified distance.
    '''
    setup_BAC(cell, dist=dist)
    return cell