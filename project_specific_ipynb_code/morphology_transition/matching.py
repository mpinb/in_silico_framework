import Interface as I
from biophysics_fitting.utils import get_main_bifurcation_section
from .df_from_cell import get_section_description_with_parent
from itertools import zip_longest

###### Tree stuff

def get_total_number_of_descendants(sec):
    out = len(sec.children())
    for child in sec.children():
        out += get_total_number_of_descendants(child)
    return out

def treematch(cell1, sec1, cell2, sec2, matchlist = None, method = 'descendants', filter_ = None):
    assert(method in ['descendants', 'length'])
    assert matchlist is not None
    if filter_ is None:
        c1 = [c for c in sec1.children()]
        c2 = [c for c in sec2.children()]
    else:
        c1 = [c for c in sec1.children() if c.label in filter_]
        c2 = [c for c in sec2.children() if c.label in filter_]
    if method == 'length':
        # match by length
        c1 = [(c, c.L) for c in c1]
        c2 = [(c, c.L) for c in c2]
    elif method == 'descendants':
        c1 = [(c, get_total_number_of_descendants(c)) for c in c1]
        c2 = [(c, get_total_number_of_descendants(c)) for c in c2]
        
    c1 = sorted(c1, key = lambda x: x[1], reverse=True)
    c2 = sorted(c2, key = lambda x: x[1], reverse=True)
    
    for a,b in zip_longest(c1,c2):
        if a is None:
            #matchlist.append(('missing in start', cell2.sections.index(b[0])))
            add_missing(cell2, b[0], 'start', matchlist)
            continue 
        if b is None:
            #matchlist.append((cell1.sections.index(a[0]), 'missing in target'))
            add_missing(cell1, a[0], 'target', matchlist)
            continue
        a_id = cell1.sections.index(a[0])
        b_id = cell2.sections.index(b[0])
        matchlist.append([a_id, b_id])
        treematch(cell1, a[0], cell2, b[0], matchlist, method, filter_)
    return matchlist

def get_all_children(sec):
    children = sec.children()
    grandkids = [get_all_children(c) for c in children]
    grandkids_flattened = [x for x in grandkids for x in x]
    return children + grandkids_flattened

def add_missing(cell, sec, missinginstartortarget, matchlist):
    if isinstance(sec, int):
        sec = cell.sections[sec]
    secid = cell.sections.index(sec)
    if missinginstartortarget == 'start':
        matchlist.append(('missing in start', secid))
    elif missinginstartortarget == 'target':
        matchlist.append((secid, 'missing in target'))
    else:
        raise ValueError()
    for c in sec.children():
        add_missing(cell, c, missinginstartortarget, matchlist)
        
###### Trunk stuff

def split_trunk_sections(start_cell, target_cell):
        'split trunk such that number of trunk sections match'
        n_trunk_start = get_n_trunk_sections(start_cell)
        n_trunk_target = get_n_trunk_sections(target_cell)
        diff = n_trunk_start - n_trunk_target
        if diff:
            print('n trunk sections start cell', n_trunk_start)
            print('n trunk sections target cell', n_trunk_target)
            add_to = 'start_cell' if diff < 0 else 'target_cell'
            cell_to_modify = start_cell if diff < 0 else target_cell
            print(f'adjusting number of sections in {add_to}')
            for _ in range(abs(diff)):
                split_longest_trunk_section_in_half(cell_to_modify)
                # print(f'adding {abs(diff)} to {'cell1' if diff > 0 else 'cell2'}')
        n_trunk_start = get_n_trunk_sections(start_cell)
        n_trunk_target = get_n_trunk_sections(target_cell)
        assert n_trunk_start == n_trunk_target
        
def remove_item_in_list_with_2_new(list_, item, new1, new2):
    'replaces one item in a list with two new items'
    i = list_.index(item)
    list_.pop(i)
    for x in reversed([new1, new2]):
        list_.insert(i, x)

def split_longest_trunk_section_in_half(cell):
    'identify longest trunk section and split it in 2'
    from neuron import h
    from single_cell_parser import PySection
    df = get_section_description_with_parent(cell)
    d = df[(df.detailed_section_label == '2_trunk')]
    longest_trunk_section = d.sort_values('section_length').index[-1]
    # longest_trunk_section
    sec = cell.sections[longest_trunk_section]
    diams = sec.diamList
    pts = sec.pts
    # disconnect long section
    parent_sec = sec.parent
    h.disconnect(sec=sec)
    assert(len(parent_sec.children()) == 1)
    # basic checks
    npts = len(pts)
    if npts < 2:
        raise ValueError(f"Section has too few points to split.")
    mid_idx = npts // 2  # integer division
    # disconnect all children
    children = sec.children()
    for c in children:
        assert c.parentseg().x == 1
        h.disconnect(sec = c)
    # create two new sections
    sec1 = PySection('', cell.id, 'ApicalDendrite')
    sec1.set_3d_geometry(pts[:mid_idx], diams[:mid_idx])
    sec2 = PySection('', cell.id, 'ApicalDendrite')
    sec2.set_3d_geometry(pts[mid_idx:], diams[mid_idx:])
    # connect 
    sec1.connect(parent_sec, 1, 0)
    sec1.parent = h.SectionRef(sec=sec1).parent  
    assert sec1.parent is parent_sec
    sec2.connect(sec1, 1, 0)
    sec2.parent = h.SectionRef(sec=sec2).parent  
    assert sec2.parent is sec1
    for c in children:
        c.connect(sec2, 1, 0)
        c.parent = h.SectionRef(sec=c).parent  
        assert c.parent is sec2
    assert len(parent_sec.children()) == 2
    assert len(sec1.children()) == 1
    assert len(sec2.children()) == 2
    remove_item_in_list_with_2_new(cell.sections,sec,sec1,sec2)
    assert sec not in cell.sections
    for sec in cell.sections:
        if sec.label == 'Soma':
            continue
        assert len(sec.children()) <=2
    assert sec1.parent is not None
    assert sec2.parent is not None

def get_n_trunk_sections(cell):
    df = get_section_description_with_parent(cell)
    d = df[(df.detailed_section_label == '2_trunk')]
    return len(d)

def match_trunk(start_cell, target_cell, matchlist = None):
    assert get_n_trunk_sections(start_cell) == get_n_trunk_sections(target_cell)
    df = get_section_description_with_parent(start_cell)
    d = df[(df.detailed_section_label == '2_trunk')]
    d1 = d.sort_values('soma_distance')
    df = get_section_description_with_parent(target_cell)
    d = df[(df.detailed_section_label == '2_trunk')]
    d2 = d.sort_values('soma_distance') 
    for sec1, sec2 in zip_longest(d1.index, d2.index, fillvalue = None):
            m = (sec1, sec2)
            if sec1 is None:
                matchlist.append(('missing in start', sec2))
            elif sec2 is None:
                matchlist.append((sec1, 'missing in target'))
            else:
                matchlist.append(m)
                      
def helper_get_trunk_get_oblique(cell, sec, o, t):
    'takes a trunk section and returns the child trunk section and the child oblique section'
    last_trunc_section_index = t['soma_distance'].idxmax()
    sec_index = cell.sections.index(sec)
    assert sec_index in t.index
    if sec_index == last_trunc_section_index: # last trunk section: both children are tuft
        return None, None 
    cs = sec.children()
    if len(cs) == 1: # no oblique child, so it must be a trunk child
        c_trunk = cs[0]
        assert cell.sections.index(c_trunk) in t.index
        return c_trunk, None
    if len(cs) == 2:
        c_trunk, c_oblique = cs # just an assumption, it might be inversed, we check below
        if cell.sections.index(c_trunk) in t.index:
            assert cell.sections.index(c_oblique) in o.index
            return c_trunk, c_oblique
        c_trunk, c_oblique = c_oblique, c_trunk # assumption was wrong, flip
        if cell.sections.index(c_trunk) in t.index:
            assert cell.sections.index(c_oblique) in o.index
            return c_trunk, c_oblique
        raise RuntimeError() # we should never get here
    if len(cs) >2:
        raise RuntimeError() # shouldn't happen, we always have bifurcations

def match_obliques_on_trunk_v2(cell1, cell2, matchlist = None):
    '''matches obliques on trunk in the order of increasing soma distance
    modified to take care of different number of trunk sections'''
    d1_o = get_obliques_df(cell1)
    d2_o = get_obliques_df(cell2)
    df = get_section_description_with_parent(cell1)
    d = df[(df.detailed_section_label == '2_trunk')]
    d1_t = d.sort_values('soma_distance')
    df = get_section_description_with_parent(cell2)
    d = df[(df.detailed_section_label == '2_trunk')]
    d2_t = d.sort_values('soma_distance')
    assert len(d1_t) == len(d2_t)
    for trunk_id_1, trunk_id_2 in zip(d1_t.index, d2_t.index):
        trunk_sec_1 = cell1.sections[trunk_id_1]
        trunk_sec_2 = cell2.sections[trunk_id_2]
        trunk_child_sec_1, trunk_oblique_child_sec_1 = helper_get_trunk_get_oblique(cell1, trunk_sec_1, d1_o, d1_t)
        trunk_child_sec_2, trunk_oblique_child_sec_2 = helper_get_trunk_get_oblique(cell2, trunk_sec_2, d2_o, d2_t)
        if (trunk_oblique_child_sec_1) is None and (trunk_oblique_child_sec_2 is None):
            continue # this is the case if we got the last trunk section, i.e. all children are tuft
        elif trunk_oblique_child_sec_1 is None:
            add_missing(cell2, cell2.sections.index(trunk_oblique_child_sec_2), 'start', matchlist)
        elif trunk_oblique_child_sec_2 is None:
            add_missing(cell1, cell1.sections.index(trunk_oblique_child_sec_1), 'target', matchlist)
        else:
            m = cell1.sections.index(trunk_oblique_child_sec_1), cell2.sections.index(trunk_oblique_child_sec_2)
            matchlist.append(m)

def match_obliques_on_trunk(cell1, cell2, matchlist = None):
    '''matches obliques on trunk in the order of increasing soma distance'''
    raise('NO')
    d1 = get_obliques_df(cell1)
    d2 = get_obliques_df(cell2)
    for sec1, sec2 in zip_longest(d1.index, d2.index, fillvalue = None):
        m = (sec1, sec2)
        if sec1 is None:
            #matchlist.append('missing in start', sec2)
            add_missing(cell2, sec2, 'start', matchlist)
        elif sec2 is None:
            #matchlist.append(sec1, 'missing in target')
            add_missing(cell1, sec1, 'target', matchlist)
        else:
            matchlist.append(m)

####### oblique stuff

def get_obliques_df(cell, on_trunk = True):
    df = get_section_description_with_parent(cell)
    trunk_length = df[df.detailed_section_label == '2_trunk'].section_length.sum()
    d = df[(df.detailed_section_label == '1_oblique') & (df.detailed_section_label_parent == '2_trunk')]
    d = d.sort_values('soma_distance')
    d['soma_distance_normalized'] = d.soma_distance / trunk_length
    return d

# TABLE stuff

def find_new_sec_id_by_old_sec_id(TABLE, old_sec_id, startortarget = None):
    if startortarget == 'start':
        out = [row for row in TABLE if row['sec_id_start'] == old_sec_id]
        assert len(out) == 1
        return out[0]['new_sec_id']
    elif startortarget == 'target':
        out = [row for row in TABLE if row['sec_id_target'] == old_sec_id]
        assert len(out) == 1
        return out[0]['new_sec_id']  
    else:
        raise ValueError()
        
####### point stuff

def get_pts_from_cell_by_secid(cell, sec):
    if isinstance(sec, int):
        sec = cell.sections[sec]
    out = []
    for lv in range(len(sec.pts)):
        x,y,z = sec.pts[lv]
        d = sec.diamList[lv]
        out.append([x,y,z,d])
    return out

def upsample_pts_to_desired_n(pts, n):
    #chatgpt
    from copy import deepcopy
    pts = deepcopy(pts)
    points_needed = n - len(pts)
    
    if points_needed == 0:
        return pts
    assert points_needed > 0, "The desired number of points must be greater than the current number of points."

    # Calculate step size for duplication
    stepsize = len(pts) / points_needed
    indices_to_duplicate = [int(i * stepsize) for i in range(points_needed)]
    
    for lv, i in enumerate(indices_to_duplicate):
        pts.insert(i + 1 + lv, pts[i + lv])
    
    return pts
assert upsample_pts_to_desired_n([1],11) == [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

assert upsample_pts_to_desired_n([1,6,2,5,8,9,3], 15) == [1, 1, 1, 6, 6, 2, 2, 5, 5, 8, 8, 9, 9, 3, 3]

import project_specific_ipynb_code.hot_zone
class TABLEGenerator():
    def __init__(self, start_cell, target_cell):
        if isinstance(start_cell, str):
            start_cell = project_specific_ipynb_code.hot_zone.get_cell_object_from_hoc(start_cell)
        if isinstance(target_cell, str):
            target_cell = project_specific_ipynb_code.hot_zone.get_cell_object_from_hoc(target_cell)
        self.start_cell = start_cell
        self.target_cell = target_cell
        self._match()
        self._make_table()
        self._wire_table()
        self._add_pts()
        
    def _match(self):
        start_cell = self.start_cell
        target_cell = self.target_cell
        
        matches_trunk = []
        split_trunk_sections(start_cell, target_cell)
        match_trunk(start_cell, target_cell, matches_trunk)

        matches_obliques = []
        match_obliques_on_trunk_v2(start_cell, target_cell, matchlist = matches_obliques)

        matches_oblique_trees = []
        for match in matches_obliques:
            if isinstance(match[0], str) or isinstance(match[1], str):
                continue 
            treematch(start_cell, start_cell.sections[match[0]],
                      target_cell, target_cell.sections[match[1]],
                      matchlist = matches_oblique_trees)

        matches_tuft = []
        treematch(start_cell, get_main_bifurcation_section(start_cell),
                  target_cell, get_main_bifurcation_section(target_cell),
                  matchlist = matches_tuft)    

        matches_basal = []
        treematch(start_cell, start_cell.soma,
                  target_cell, target_cell.soma,
                  matchlist = matches_basal,
                  filter_ = ['Dendrite'],
                  method = 'length')  
        
        self.matches_trunk = matches_trunk
        self.matches_obliques = matches_obliques
        self.matches_oblique_trees = matches_oblique_trees
        self.matches_tuft = matches_tuft
        self.matches_basal = matches_basal

    def _make_table(self):
        start_cell = self.start_cell
        target_cell = self.target_cell
        TABLE = []
        columns = ['new_sec_id', 
                   'n_points', 
                   'detailed_label',
                   'sec_id_start', 
                   'sec_id_target',
                   'start_L',
                   'target_L',
                   'start_points',
                   'target_points',
                   'parent']

        counter = 0

        # Soma
        row = {}
        row['new_sec_id'] = 0
        row['detailed_label'] = 'Soma'
        row['start_points'] = len(start_cell.soma.pts)
        row['target_points'] = len(target_cell.soma.pts)
        row['n_points'] = max(row['start_points'], row['target_points'])
        row['start_L'] = start_cell.soma.L
        row['target_L'] = target_cell.soma.L
        row['parent'] = 'none'
        row['sec_id_start'] = 0
        row['sec_id_target'] = 0
        TABLE.append(row)
        counter += 1

        # Trunk
        for a,b in self.matches_trunk:
            try:
                sec1 = start_cell.sections[a]
            except IndexError:
                sec1 = None
            try:
                sec2 = target_cell.sections[b]
            except IndexError:
                sec2 = None
            row = {}
            row['new_sec_id'] = counter
            row['detailed_label'] = '2_trunk'
            row['start_points'] = len(sec1.pts) if sec1 else 0
            row['target_points'] = len(sec2.pts) if sec2 else 0
            row['n_points'] = max(row['start_points'], row['target_points'])
            row['start_L'] = sec1.L if sec1 else 0. 
            row['target_L'] = sec2.L if sec2 else 0. 
            row['parent'] = 'none'
            row['sec_id_start'] = a
            row['sec_id_target'] = b
            TABLE.append(row)
            counter += 1

        # obliques
        for a,b in self.matches_obliques + self.matches_oblique_trees:
            try:
                sec1 = start_cell.sections[a]
            except TypeError:
                sec1 = None
            try:
                sec2 = target_cell.sections[b]
            except TypeError:
                sec2 = None
            row = {}
            row['new_sec_id'] = counter
            row['detailed_label'] = '1_obliques'
            row['start_points'] = len(sec1.pts) if sec1 else 0
            row['target_points'] = len(sec2.pts) if sec2 else 0
            row['n_points'] = max(row['start_points'], row['target_points'])
            row['start_L'] = sec1.L if sec1 else 0. 
            row['target_L'] = sec2.L if sec2 else 0. 
            row['parent'] = 'none'
            row['sec_id_start'] = a
            row['sec_id_target'] = b
            TABLE.append(row)
            counter += 1

        # # apical
        # for a,b in matches_apical:
        #     try:
        #         sec1 = start_cell.sections[a]
        #     except TypeError:
        #         sec1 = None
        #     try:
        #         sec2 = target_cell.sections[b]
        #     except TypeError:
        #         sec2 = None
        #     row = {}
        #     row['new_sec_id'] = counter
        #     row['detailed_label'] = '0_basal'
        #     row['start_points'] = len(sec1.pts) if sec1 else 0
        #     row['target_points'] = len(sec2.pts) if sec2 else 0
        #     row['n_points'] = max(row['start_points'], row['target_points'])
        #     row['start_L'] = sec1.L if sec1 else 0. 
        #     row['target_L'] = sec2.L if sec2 else 0. 
        #     row['parent'] = 'none'
        #     row['sec_id_start'] = a
        #     row['sec_id_target'] = b
        #     TABLE.append(row)
        #     counter += 1
        # basal
        for a,b in self.matches_basal:
            try:
                sec1 = start_cell.sections[a]
            except TypeError:
                sec1 = None
            try:
                sec2 = target_cell.sections[b]
            except TypeError:
                sec2 = None
            row = {}
            row['new_sec_id'] = counter
            row['detailed_label'] = '0_basal'
            row['start_points'] = len(sec1.pts) if sec1 else 0
            row['target_points'] = len(sec2.pts) if sec2 else 0
            row['n_points'] = max(row['start_points'], row['target_points'])
            row['start_L'] = sec1.L if sec1 else 0. 
            row['target_L'] = sec2.L if sec2 else 0. 
            row['parent'] = 'none'
            row['sec_id_start'] = a
            row['sec_id_target'] = b
            TABLE.append(row)
            counter += 1

        # tuft
        for a,b in self.matches_tuft:
            try:
                sec1 = start_cell.sections[a]
            except TypeError:
                sec1 = None
            try:
                sec2 = target_cell.sections[b]
            except TypeError:
                sec2 = None
            row = {}
            row['new_sec_id'] = counter
            row['detailed_label'] = '3_tuft'
            row['start_points'] = len(sec1.pts) if sec1 else 0
            row['target_points'] = len(sec2.pts) if sec2 else 0
            row['n_points'] = max(row['start_points'], row['target_points'])
            row['start_L'] = sec1.L if sec1 else 0. 
            row['target_L'] = sec2.L if sec2 else 0. 
            row['parent'] = 'none'
            row['sec_id_start'] = a
            row['sec_id_target'] = b
            TABLE.append(row)
            counter += 1
        self.TABLE = TABLE

    def _wire_table(self):
        start_cell = self.start_cell
        target_cell = self.target_cell
        TABLE = self.TABLE
        # wire table
        for row in TABLE:
            # print(1)
            #lookup parent in start_cell
            if row['detailed_label'] == 'Soma':
                continue # soma has no parent
            if isinstance(row['sec_id_start'], str): # string means it is missing
                parent1_new_id = None
            else:
                parent1 = start_cell.sections[row['sec_id_start']].parent
                parent1 = start_cell.sections.index(parent1)
                parent1_new_id = find_new_sec_id_by_old_sec_id(TABLE, parent1, 'start')
            if isinstance(row['sec_id_target'], str):
                parent2_new_id = None
            else:
                parent2 = target_cell.sections[row['sec_id_target']].parent
                parent2 = target_cell.sections.index(parent2)   
                parent2_new_id = find_new_sec_id_by_old_sec_id(TABLE, parent2, 'target')
            if (parent1_new_id is not None) and (parent2_new_id is not None):
                assert parent1_new_id == parent2_new_id
            if parent1_new_id is not None:
                parent_new_id = parent1_new_id
            elif parent2_new_id is not None:
                parent_new_id = parent2_new_id
            else:
                raise RuntimeError()
            row['parent'] = parent_new_id
            assert (parent1 is not None) or (parent2 is not None) or row['detailed_label'] == 'Soma'

    def _add_pts(self):
        start_cell = self.start_cell
        target_cell = self.target_cell
        TABLE = self.TABLE
        for row in TABLE:
            if isinstance(row['sec_id_start'], int): # segment present in start cell
                pts = get_pts_from_cell_by_secid(start_cell, row['sec_id_start'])
                row['pts_start'] = upsample_pts_to_desired_n(pts, row['n_points'])
            else:
                row2 = row
                while not isinstance(row2['sec_id_start'], int):
                    row2 = TABLE[row2['parent']]
                pts = get_pts_from_cell_by_secid(start_cell, row2['sec_id_start'])
                pts = [pts[-1]]
                row['pts_start'] = upsample_pts_to_desired_n(pts, row['n_points'])
            if isinstance(row['sec_id_target'], int): # segment present in target cell
                pts = get_pts_from_cell_by_secid(target_cell, row['sec_id_target'])
                row['pts_target'] = upsample_pts_to_desired_n(pts, row['n_points'])
            else:
                row2 = row
                while not isinstance(row2['sec_id_target'], int):
                    row2 = TABLE[row2['parent']]
                pts = get_pts_from_cell_by_secid(target_cell, row2['sec_id_target'])
                pts = [pts[-1]]
                row['pts_target'] = upsample_pts_to_desired_n(pts, row['n_points'])
                
    def make_NEURON_friendly(self):
        'uses x as global variable'
        global x
        from copy import deepcopy
        def translate_x_to_y():
            global x
            x = I.np.array(x)
            translation_x = deepcopy(x[0])
            translation_x[3] = 0.
            translation_y = deepcopy(y[0])
            translation_y[3] = 0.
            x = x-translation_x+translation_y
            assert(x[:,3].min()>0)

            pts = x.tolist()
            pts_zero_length = [pts[0]]*len(pts)
            pts_zero_length = [pts[0]]*len(pts)
            pts_np = I.np.array(pts)
            pts_np[:,3] = 0.
            pts_zero_diam = pts_np.tolist()
            pts_first_zero_diam = deepcopy(pts)
            pts_first_zero_diam[0][3]=0.
            pts_zero_length_zero_diam = [[pts[0][0], pts[0][1], pts[0][2], 0.]]*len(pts)
            # x = pts # this will not change anything
            x = pts_first_zero_diam

        TABLE = self.TABLE
        for row in TABLE:
            if isinstance(row['sec_id_start'], str):
                y, x = row['pts_start'], row['pts_target']
                translate_x_to_y()
                row['pts_start'] = x
            if isinstance(row['sec_id_target'], str):
                x,y = row['pts_start'], row['pts_target']
                translate_x_to_y()
                row['pts_target'] = x
######## visualize stuff

def visualize_TABLE(TABLE):
    fig = I.plt.figure(figsize = (30,5), dpi = 200)
    for lv, alpha in enumerate([0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]):
        for row in TABLE:
            arr = I.np.array(row['pts_start']) * (1-alpha) + I.np.array(row['pts_target']) * alpha
            I.plt.plot(arr[:,0]+ 500 * lv, arr[:,2])
    I.plt.gca().set_aspect('equal')
