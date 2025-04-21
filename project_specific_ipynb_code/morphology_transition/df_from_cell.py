import Interface as I
def get_section_description_df(cell):
    import project_specific_ipynb_code
    t = 0
    main_bifurc_sec = project_specific_ipynb_code.hot_zone.get_main_bifurcation_section(cell)
    trunk_sections = [main_bifurc_sec]
    while True:
        sec = trunk_sections[-1].parent
        if  sec.label == 'Soma':
            break
        else:
            trunk_sections.append(sec)
    tuft_sections = []
    oblique_sections = []
    for sec in cell.sections:
        if not sec.label == 'ApicalDendrite':
            continue
        secp = sec.parent
        while True:
            if secp.label == 'Soma':
                if not sec in trunk_sections:
                    oblique_sections.append(sec)
                break
            if secp == main_bifurc_sec:
                tuft_sections.append(sec)
                break
            secp = secp.parent
    out = {}
    for lv, sec in enumerate(cell.sections):
        if not sec.label in ['Dendrite', 'ApicalDendrite']:
            continue
        out[lv] = {'neuron_section_label':sec.label,
                   'detailed_section_label': '3_tuft' if sec in tuft_sections\
                                                        else '2_trunk' if sec in trunk_sections\
                                                        else '1_oblique' if sec in oblique_sections\
                                                        else '0_basal',
                   'section_length': sec.L}
    return I.pd.DataFrame(out).T

def get_detailed_section_label_of_parent(cell, detailed_section_df, section_id):
    parent = cell.sections[section_id].parent
    parent_id = cell.sections.index(parent)
    if parent_id == 0:
        return 'Soma'
    parent_label = detailed_section_df.loc[parent_id].detailed_section_label
    return parent_label

def add_soma_distance_from_base(cell, detailed_section_df):
    
    def helper(sec):
        out = 0.
        while sec.parent != cell.soma:
            out += sec.parent.L
            sec = sec.parent
        return out
        
    from neuron import h
    detailed_section_df['soma_distance'] = detailed_section_df.apply(lambda row: helper(cell.sections[row.name]),
                                                                     axis = 1)
    
def get_section_description_with_parent(cell):
    df = get_section_description_df(cell)
    add_soma_distance_from_base(cell, df)
    df['detailed_section_label_parent'] = df.apply(lambda row: get_detailed_section_label_of_parent(cell, 
                                                                                                    df, 
                                                                                                    row.name), 
                                                   axis = 1)
    return df
