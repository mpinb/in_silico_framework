import pandas as pd
import os

presynaptic_cell_types = [
    'L1', 'L2', 'L23Trans', 'L34', 'L45Peak', 'L45Sym', 'L4py', 'L4sp', 'L4ss',
    'L56Trans', 'L5st', 'L5tt', 'L6cc', 'L6ccinv', 'L6ct', 'SymLocal1',
    'SymLocal2', 'SymLocal3', 'SymLocal4', 'SymLocal5', 'SymLocal6', 'VPM'
]
presynaptic_columns = [
    'A1', 'A2', 'A3', 'A4', 'Alpha', 'B1', 'B2', 'B3', 'B4', 'Beta', 'C1', 'C2',
    'C3', 'C4', 'D1', 'D2', 'D3', 'D4', 'Delta', 'E1', 'E2', 'E3', 'E4', 'Gamma'
]


def con_file_to_NumberOfConnectedCells_sheet(con_file, write_output=True):
    '''con_file: path to .con file genereate by SingleCellInputMapper'''
    #read in .con_file
    con_pdf = pd.read_csv(con_file,
                          sep='\t',
                          skiprows=3,
                          names=['type', 'cell_ID', 'synapse_ID'])
    #groupb by celltype
    con_pdf = con_pdf.groupby('type').apply(
        lambda x: len(x.cell_ID.drop_duplicates())).to_frame(
            name='Connected presynaptic cells').reset_index()
    #split type column in celltype and column
    con_pdf['Presynaptic cell type'] = con_pdf.apply(
        lambda x: x.type.split('_')[0], axis=1)
    con_pdf['Presynaptic column'] = con_pdf.apply(
        lambda x: x.type.split('_')[1], axis=1)
    #cell-column combinations that do not contain a single cell do not appear at this point in the table
    #add entries for such cell populations
    for c in presynaptic_columns:
        c_selected_pdf = con_pdf[con_pdf['Presynaptic column'] == c]
        for z in presynaptic_cell_types:
            if len(c_selected_pdf[c_selected_pdf['Presynaptic cell type'] ==
                                  z]) == 0:
                con_pdf = con_pdf.append(
                    pd.DataFrame({
                        'Presynaptic column': [c],
                        'Presynaptic cell type': [z],
                        'Connected presynaptic cells': [0]
                    }))
    #sort and select data
    con_pdf = con_pdf.sort_values('Presynaptic column')
    con_pdf = con_pdf[[
        'Presynaptic column', 'Presynaptic cell type',
        'Connected presynaptic cells'
    ]]
    if write_output == False:
        return con_pdf
    #save in same folder as the .con file
    outpath = os.path.join(os.path.dirname(con_file),
                           'NumberOfConnectedCells.csv')
    con_pdf.sort_values('Presynaptic column').to_csv(outpath,
                                                     sep='\t',
                                                     index=False)
    return outpath