import pandas as pd
import single_cell_parser as scp

def read_cell_number_file(cell_nr_fn):
    """Load the cell number file.
    
    The cell number file must have the following format::
    
        Anatomical_area (optional)  Presynaptic_cell_type   n_cells
        A1	                        cell_type_1	            8
        A1	                        cell_type_2	            14
        ...

    Args:
        cellNumberFileName (str): Path to the cell number file.
        
    Returns:
        dict: Dictionary of the form {celltype: {column: nr_of_cells}}
        
    Example:
        >>> load_cell_number_file(
        ...    'getting_started/example_data/anatomical_constraints/'
        ...    'example_embedding_86_C2_center/'
        ...    'NumberOfConnectedCells.csv'
        ...    )
        {
            'L4py': {
                'A1': 8, 
                'A2': 1, 
                'A3': 7, 
                'A4': 3, 
                'Alpha': 9, 
                'B1': 72, 
                'B2': 30, 
                'B3': 97, 
                'B4': 30, 
                'Beta': 0, 
                'C1': 59, 
                'C2': 374, 
                'C3': 88, 
                'C4': 3, 
                'D1': 22, 
                'D2': 89, 
                'D3': 59, 
                'D4': 0, 
                'Delta': 0, 
                'E1': 0, 
                'E2': 0, 
                'E3': 0, 
                'E4': 0, 
                'Gamma': 16}, 
                'L6cc': {...}, 
                ... 
    """
    df = pd.read_csv(cell_nr_fn, sep="\t", skiprows=1, names=['anatomical_area', 'cell_type', 'nr_of_cells'])
    return df.groupby("anatomical_area").apply(lambda x: dict(zip(x["cell_type"], x["nr_of_cells"]))).to_dict()


def read_evoked_PSTH(fn, key):
    """
    Fetch the PSTHs of each celltype in a barrel cortex :param:`column` for evoked activity reflecting 
    a passive whisker touch scenario.
    This method does not generate such data, but reads it in from existing files containing such empirical measurements, 
    and parses it. These existing data files are set as global variables in this runfile. For other activity data, adapt these file names.
    
    The data linked in this runfile are for experiments where the C2 whisker was deflected.
    For situations where other :param:`deflectedwhisker` are requested, activity data of equivalent
    columns relative to the C2 is requested.
    
    Example:
        >>> column = 'B2'  # I want activity from B2 column
        >>> deflectedWhisker = 'C1'  # I want activity reflecting deflection of C1 whisker (not C2)
        >>> cellType = 'L6ct'
        >>> params = whisker_evoked_PSTH(column=column, deflectedWhisker=deflectedWhisker, cellType=cellType)
        >>> print(params)  # This is activity data from the C3 column for C2 whisker deflection i.e. equivalent activity
        {
            'distribution': 'PSTH', 
            'intervals': [(40.0, 41.0), (43.0, 44.0), (49.0, 50.0)], 
            'probabilities': [0.0057, 0.0057, 0.0057]
            }

    Args:
        cellType (str): Which cell type you want the PSTH for.

    Returns:
        parameters.NTParameterSet: 
            The PSTH for the given cell type in a C2-relative equivalent column, reflecting the deflection of the given whisker.
    """
    cell_type_evoked_activity = scp.build_parameters(filename=fn) 
    PSTH = cell_type_evoked_activity.get(key)
    return PSTH