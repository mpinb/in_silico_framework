
from pathlib import Path
from .. import AVAILABLE_SYNAPSE_MAPPING_METHODS

SELECTED_SYNAPSE_MAPPING_METHOD = "udvary2022"

prefix = Path(__file__).parent.parent.parent / "barrel_cortex"

DATA_REQS_UDVARY2022 = {
    'numberOfCellsSpreadsheetName':   prefix / "nrCells.csv",
    'connectionsSpreadsheetName' :    prefix / "ConnectionsV8.csv",
    'ExPSTDensityName' :              prefix / "PST/EXNormalizationPSTs.am",
    'InhPSTDensityName' :             prefix / "PST/INHNormalizationPSTs.am",
    'boutonDensityFolderName' :       prefix / "singleaxon_boutons_ascii",
    'nrOfSamples':                    50,
}


assert SELECTED_SYNAPSE_MAPPING_METHOD in AVAILABLE_SYNAPSE_MAPPING_METHODS, \
    f"The chosen synapse mapping method {SELECTED_SYNAPSE_MAPPING_METHOD} is not available. Available methods are: {AVAILABLE_SYNAPSE_MAPPING_METHODS}"