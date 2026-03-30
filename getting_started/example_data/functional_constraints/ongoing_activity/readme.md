# Ongoing activity template files

This directory contains network parameter files that include ongoing activity for cell types.

Some naming conventions should get you started:

## templates

Files that have the word "template" in them are network parameter files with default values for ongoing activity rates. 

Only exceptions to this rule are: 

ongoing_activity_celltype_template_exc_conductances_fitted_L6ccinact.param      (No L6cc activity)
ongoing_activity_celltype_template_exc_conductances_inh_activity_fitted2.param  (Non-default ongoing activity for inhibitory cell types)
ongoing_activity_celltype_template_exc_conductances_inh_activity_fitted.param   (Non-default ongoing activity for inhibitory cell types)

## realization

Files with "realization" in the name have ongoing activity rates defined for more finely subcategorized cell types.
This data is for the barrel cortex, so each cell type is split up into columns as well.

These files have default values for ongoing rates as well (except if they are no connection with a particular cell type, then it is nan)
they have non-default values for the synapse dynamics, which can however be inferred from the filename.