import Interface as I


def get_section_description_df(cell):
    import project_specific_ipynb_code
    t = 0
    main_bifurc_sec = project_specific_ipynb_code.hot_zone.get_main_bifurcation_section(
        cell)
    trunk_sections = [main_bifurc_sec]
    while True:
        sec = trunk_sections[-1].parent
        if sec.label == 'Soma':
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
        out[lv] = {'neuron_section_label': sec.label,
                   'detailed_section_label': '3_tuft' if sec in tuft_sections\
                                                        else '2_trunk' if sec in trunk_sections\
                                                        else '1_oblique' if sec in oblique_sections\
                                                        else '0_basal',
                   'section_length': sec.L}
    return I.pd.DataFrame(out).T