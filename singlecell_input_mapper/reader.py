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


def read_nr_connected_cells_from_con(con_file):
    """Read a :ref:`con_file_format` and infer how many cells of each cell type are connected
    
    Args:
        con_file (str): Filename of the :ref:`con_file_format` file

    Returns:
        pd.Series: A pandas series mapping each cell type to how many of them are connected to the postsynaptic neuron.
    """
    con_pdf = pd.read_csv(
            con_file, sep="\t", skiprows=3, names=["celltype", "cell_ID", "synapse_ID"]
        )

    con_series = con_pdf.groupby("celltype").apply(func=lambda x: len(x.cell_ID.drop_duplicates()))
    return con_series