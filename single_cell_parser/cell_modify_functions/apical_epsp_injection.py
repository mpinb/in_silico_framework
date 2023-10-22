from biophysics_fitting.setup_stim import setup_apical_epsp_injection as setup_apical_epsp_injection_


def apical_epsp_injection(cell,
                          dist=None,
                          amplitude=None,
                          delay=None,
                          rise=1.0,
                          decay=5):
    '''
    This injects epsp shaped current at a certain distance from the soma.
    '''
    setup_apical_epsp_injection_(cell,
                                 dist=dist,
                                 amplitude=amplitude,
                                 delay=delay,
                                 rise=rise,
                                 decay=decay)
    return cell
