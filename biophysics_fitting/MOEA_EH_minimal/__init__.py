"""
This package provides mechanisms and NEURON configuration files to 
run Hay's evolutionary algorithm :cite:t:`Hay_Hill_Schuermann_Markram_Segev_2011` for the optimization of
biophysical models.

For the sake of self-containment, this directory provides copies of all mechanisms required for cortical L5 neurons.
However, these are not the mechanisms used in ISF. ISF compiles and loads mechanisms from the ``mechanisms`` directory.
If you ahve segfault issues, make sure those are compiled and loaded into the neuron hoc namespace. You can
do this by simply importing ``mechanisms.l5pt``.
"""