from biophysics_fitting.setup_stim import setup_soma_step


def apical_current_injection(cell,
                             amplitude=None,
                             delay=None,
                             duration=None,
                             dist=None):
    # note: setup_soma_step has been extended to support a dist parameter
    setup_soma_step(cell,
                    amplitude=amplitude,
                    delay=delay,
                    duration=duration,
                    dist=dist)
    return cell
