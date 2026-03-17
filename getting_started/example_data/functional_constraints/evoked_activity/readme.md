De Kock, C. P. J., Bruno, R. M., Spors, H., & Sakmann, B. (2007). Layer- and cell-type-specific suprathreshold stimulus representation in rat primary somatosensory cortex. The Journal of Physiology, 581(1), 139–154. https://doi.org/10.1113/jphysiol.2006.124321

# Info about this data

All data in this directory contains activity data for various cell types in the juvenile Wistar rat Barrel Cortex.
All recordings were made in the C2 column.
Data is split so that each file contains one particular cell type.
Within each file, you will find multiple activity measurements for a single cell type. These correspond to 
different whisker deflections.

So e.g. "L6cc_B2" means the activity of a L6cc (located in C2) when deflecting a whisker in B2.

## Attention
Note that the suffix in these files does **NOT** correspond to the location of the recorded cell, in contrast to most other data in this repo.
It corresponds to the identity of the deflected whisker.

## Hint
While this repo only contains data for cells in the C2 column, you can augment it by assuming activity is similar
for the same *relative* coordinate. A relative coordinate is the difference between the recording column and the stimulate whisker.
Consider the whisker/barrel grid:


A1    A2        A3    A4    alpha
B1    B2        B3    B4    beta
C1    **C2**    C3    C4    gamma
D1    D2        D3    D4    delta
E1    E2        E3    E4

Where the coordinates (row, column) are ascending to (bottom, right)

Invert the absolute coordinate around C2 and you get a corresponding label between whisker stimulus and cell location of equivalent activity data.

Example:
    "L6cc_B1" means activity of L6cc cells located in the C2 column when deflecting whisker B1.
    That means activity in relative coordinates (+1, +1) wrt to the stimulated whisker.
    If we are instead interested in what activity in B1-located cells look like for a C2-stimulus,
    this should look similar to our (C2-located) activity data when whisker D3 was stimulated (also (+1, +1)).
    Thus, we fetch "L6cc_D3" data, meaning the activity of C2-located L6cc cells during a D3 stimulus.
    This will look similar to B1-located L6cc activity for a C2 whisker


See also:
    https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/21W1HR&faces-redirect=true