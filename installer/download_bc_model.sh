#!/bin/bash

# Downloads and extracts the barrel cortex model from Harvard DataVerse
# See: https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/JZPULNa

SCRIPT_DIR="$( cd -- "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 ; pwd -P )"
ISF_DIR=$(dirname $SCRIPT_DIR) 
echo "ISF DIR: $ISF_DIR"

echo -e "\nDownloading the axon tracings raw data as zipfiles. These can be unzipped with 7z or 7za.\n"
wget https://dataverse.harvard.edu/api/access/datafile/10256305 -O $ISF_DIR/barrel_cortex.7z.001
wget https://dataverse.harvard.edu/api/access/datafile/10256306 -O $ISF_DIR/barrel_cortex.7z.002 -P
wget https://dataverse.harvard.edu/api/access/datafile/10256307 -O $ISF_DIR/barrel_cortex.7z.003 -P


echo -e <<EOF
Downloading ISF-compatible barrel_cortex data:

    - Python code associated with the BC model (__init__.py)
    - average_barrel_field_L45_border.am
    - nrCells.csv
    - ConnectionsV8.csv
    - PST/
        - EXNormalizationPSTs.am
        - INHNormalizationsPSTs.am
EOF

mkdir $ISF_DIR/barrel_cortex/
wget  https://dataverse.harvard.edu/api/access/datafile/10247199 -O $ISF_DIR/barrel_cortex/__init__.py -P $ISF_DIR
wget  https://dataverse.harvard.edu/api/access/datafile/10247198 -O $ISF_DIR/barrel_cortex/average_barrel_field_L45_border.am -P $ISF_DIR
wget https://dataverse.harvard.edu/api/access/datafile/10247202?format=original -O $ISF_DIR/barrel_cortex/ConnectionsV8.csv -P $ISF_DIR
wget https://dataverse.harvard.edu/api/access/datafile/10251834?format=original -O $ISF_DIR/barrel_cortex/nrCells.csv -P $ISF_DIR
wget https://dataverse.harvard.edu/api/access/datafile/10247203?format=original -O $ISF_DIR/barrel_cortex/README.md -P $ISF_DIR
mkdir $ISF_DIR/barrel_cortex/PST
wget  https://dataverse.harvard.edu/api/access/datafile/10247200 -O $ISF_DIR/barrel_cortex/PST/EXNormalizationPSTs.am -P $ISF_DIR
wget  https://dataverse.harvard.edu/api/access/datafile/10247201 -O $ISF_DIR/barrel_cortex/PST/INHNormalizationsPSTs.am -P $ISF_DIR