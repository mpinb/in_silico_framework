from biophysics_fitting.setup_stim import setup_soma_step


def soma_current_injection(cell, amplitude=None, delay=None, duration=None):
    setup_soma_step(cell, amplitude=amplitude, delay=delay, duration=duration)
    return cell