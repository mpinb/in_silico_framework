import Interface as I

######################
# functions to extract branchpoints
######################


def connected_to_dend_beyond(cell, sec, beyond_dist, n_children_required=2):
    '''returns true if at least two children of the branchpoint reach beyond dist'''
    if cell.distance_to_soma(
            sec, 1
    ) > beyond_dist:  # and sec.label in ('ApicalDendrite', 'Dendrite'):
        return True
    else:
        dummy = sum(
            connected_to_dend_beyond(cell,
                                     c,
                                     beyond_dist,
                                     n_children_required=1)
            for c in sec.children()
            # if sec.label in ('ApicalDendrite', 'Dendrite')
        )
        if dummy >= n_children_required:
            return True
        else:
            return False


def get_inner_sec_dist_list(cell, select=['ApicalDendrite', 'Dendrite']):
    #    sec_dist_dict = {cell.distance_to_soma(sec, 1.0): sec
    sec_dist_dict = {
        sec.pts[-1][2] - 706: sec
        for sec in cell.sections
        if connected_to_dend_beyond(cell, sec, 1000) and sec.label in select
    }
    return sec_dist_dict


def get_branching_depth(cell, sec):
    depth = connected_to_dend_beyond(cell, sec, 1000)
    if sec.parent.label.lower() == 'soma':
        return depth
    else:
        return depth + get_branching_depth(cell, sec.parent)


def get_branching_depth_series(cell):
    '''
    Careful: z-depth only accurate for D2-registered cells!
    
    returns a series that contains the pia distance as index and  
    a tuple (biforcation order, section) as value'''

    inner_sections = get_inner_sec_dist_list(cell)
    import six
    inner_sections_branching_depth = {
        k: (get_branching_depth(cell, sec), sec)
        for k, sec in six.iteritems(inner_sections)
    }
    inner_sections_branching_depth = I.pd.Series(inner_sections_branching_depth)
    return inner_sections_branching_depth


def get_main_bifurcation_section(cell):
    sec_dist_list = get_branching_depth_series(cell)
    sec_dist_list_filtered = [sec[1] for sec in sec_dist_list if sec[0] == 1]
    assert len(sec_dist_list_filtered) == 1
    return sec_dist_list_filtered[0]


#######################################
# functions to read hoc files
#######################################
def get_cell_object_from_hoc(hocpath, setUpBiophysics=True):
    '''returns cell object, which allows accessing points of individual branches'''
    # import singlecell_input_mapper.singlecell_input_mapper.cell
    # ssm = singlecell_input_mapper.singlecell_input_mapper.cell.CellParser(hocpath)
    # ssm.spatialgraph_to_cell()
    # return ssm.cell
    neuron_param = {'filename': hocpath}
    neuron_param = I.scp.NTParameterSet(neuron_param)
    cell = I.scp.create_cell(neuron_param, setUpBiophysics=setUpBiophysics)
    return cell


##########################################
# database containing mikes cells
##########################################
# id: '2019-09-09_19894_YfrHaoO'
## mdb_cells = I.ModelDataBase('/nas1/Data_arco/results/20190909_VPM_contact_analysis_for_mike_review')


###########################################
# test, whether two ranges overlap
############################################
def range_overlap(beginning1, end1, beginning2, end2, bool_=True):
    out = min(end1, end2) - max(beginning1, beginning2)
    out = max(0, out)
    if bool_:
        out = bool(out)
    return out


assert not range_overlap(0, 1, 1, 2)
assert not range_overlap(0, 1, 1.1, 2)
assert not range_overlap(0, 1, 2, 3)
assert range_overlap(0, 1, 0.9, 2)
assert range_overlap(0, 1.1, 1, 2)
assert range_overlap(0, 1.1, 0.9, 1.1)
assert range_overlap(0, 1.1, 0.9, 1)
assert range_overlap(0, 1.1, -1, 2)
assert range_overlap(0, 1, 0, 1)


#########################################
# class that can visualize the synapse counts and can
# compute the density profiles
#########################################
def get_dist(x1, x2):
    assert len(x1) == len(x2)
    return I.np.sqrt(sum((xx1 - xx2)**2 for xx1, xx2 in zip(x1, x2)))


def get_L_from_sec(sec, lv):
    out = 0
    for lv in range(1, lv + 1):
        assert lv - 1 >= 0
        out += get_dist(sec.pts[lv - 1], sec.pts[lv])
    return out


class Dendrogram:

    def __init__(self, cell, title='', colormap_synapses=None):
        # cell object needs to implement the following functionality:
        #     cell.soma
        #     section.children()
        #     section.L
        self.cell = cell
        self.title = title
        self.dendrogram_db = []
        self.dendrogram_db_by_name = {}
        if colormap_synapses:
            self.colormap_synapses = colormap_synapses
        else:
            self.colormap_synapses = I.defaultdict(lambda: 'k')
        self._cell_to_dendrogram(self.cell.soma)
        self._soma_to_dendrogram(self.cell)
        self._set_initial_x()
        self._compute_main_bifurcation_section()

    def _add_synapse(self, l, label, x):
        if not 'synapses' in l:
            l['synapses'] = {}
        if not label in l['synapses']:
            l['synapses'][label] = []
        l['synapses'][label].append(x)

    def add_synapses(self,
                     label,
                     synlist,
                     mode='from_anatomical_synapse_mapper'):
        '''mode:
        
        'from_anatomical_synapse_mapper': to be used if synlist is generated from landmark as it is done
            with mikes manually mapped VPM synapses
            
        'id_relative_position': as in the syn file. Use something like [(syn.secID, syn.x) for syn in cell.synapses['VPM_C2']]
            to use synapses defined in a single_cell_parser.cell object
        '''
        if mode == 'from_anatomical_synapse_mapper':
            for syn in synlist:
                (sec_lv, seg_lv), (dist, x, point) = syn
                sec = self.cell.sections[sec_lv]
                l = self.get_db_by_sec(sec)
                x = get_L_from_sec(
                    sec, seg_lv) + x + l['x_offset'] + l['x_dist_start']
                self._add_synapse(l, label, x)
        elif mode == 'id_absolute_position':
            for syn in synlist:
                sec_lv, x = syn
                sec = self.cell.sections[sec_lv]
                l = self.get_db_by_sec(sec)
                x = x + l['x_offset'] + l['x_dist_start']
                self._add_synapse(l, label, x)
        elif mode == 'id_relative_position':
            for syn in synlist:
                sec_lv, x = syn
                sec = self.cell.sections[sec_lv]
                l = self.get_db_by_sec(sec)
                x = x * sec.L + l['x_offset'] + l['x_dist_start']
                self._add_synapse(l, label, x)

    def _cell_to_dendrogram(self, basesec=None, basename='', x_dist_base=0):
        if basename:
            basename = basename.split('__')
        else:
            basename = ('', '', '')
        for lv, sec in enumerate(
                sorted(basesec.children(), key=lambda x: x.label)):
            if sec.label not in ('Dendrite', 'ApicalDendrite', 'Soma'):
                continue

            x_offset = get_dist(basesec.pts[-1], sec.pts[0])
            x_dist_start = x_dist_base
            x_dist_end = x_dist_start + x_offset + sec.L

            name = sec.label + '__' + (basename[1] + '_' if basename[1] else
                                       '') + str(lv) + '__' + str(
                                           I.np.round(sec.L))
            self.dendrogram_db.append({
                'name': name,
                'x_dist_start': x_dist_start,
                'x_dist_end': x_dist_end,
                'sec': sec,
                'sec_id': self.cell.sections.index(sec),
                'x_offset': x_offset
            })

            self._cell_to_dendrogram(sec, name, x_dist_end)
        self.dendrogram_db_by_name = {
            d_['name']: d_ for d_ in self.dendrogram_db
        }

    def _soma_to_dendrogram(self, cell):
        soma_sections = [s for s in cell.sections if s.label.lower() == 'soma']
        print("adding {} soma sections".format(len(soma_sections)))
        for lv, sec in enumerate(soma_sections):
            self.dendrogram_db.append({
                'name': 'Soma__{}__0'.format(lv),
                'x_dist_start': I.np.NaN,
                'x_dist_end': I.np.NaN,
                'sec': sec,
                'x_offset': I.np.NaN
            })

    def _set_initial_x(self):
        for lv, l in enumerate(
                sorted(self.dendrogram_db,
                       key=lambda x: x['name'].split('__')[1])):
            l['x'] = lv

    def plot(self, fig=None):
        if fig is None:
            fig = I.plt.figure(figsize=(8, 10), dpi=200)
        ax = fig.add_subplot(211)
        ax2 = fig.add_subplot(413)
        ax3 = fig.add_subplot(414)

        xlim = self._plot_dendrogram(ax)
        self._plot_dendrite_and_synapse_counts(ax2, xlim)
        self._plot_synapse_density(ax3, xlim)
        return fig

    def _plot_dendrogram(self,
                         ax=None,
                         colormap={
                             'Dendrite': 'grey',
                             'ApicalDendrite': 'r'
                         }):
        # uses: self.colormap_synapses
        if ax is None:
            fig = I.plt.figure(figsize=(8, 10), dpi=200)
            ax = fig.add_subplot(211)

        for lv, l in enumerate(self.dendrogram_db):
            label, tree, L = l['name'].split('__')
            if not label in ['Dendrite', 'ApicalDendrite']:
                continue
            x = l['x']
            parent = self.get_parent_by_name(l['name'])
            if parent is None:
                parent_x = 0
            else:
                parent_x = parent['x']
            ax.plot([l['x_dist_start'], l['x_dist_start'] + l['x_offset']],
                    [x, x],
                    ':',
                    c='grey',
                    linewidth=.5)
            ax.plot([l['x_dist_start'] + +l['x_offset'], l['x_dist_end']],
                    [x, x],
                    c=colormap[label],
                    linewidth=.5)

            ax.plot([l['x_dist_start'], l['x_dist_start']], [x, parent_x],
                    c=colormap[label],
                    linewidth=.5)
            if 'synapses' in l:
                for syntype in l['synapses']:
                    for syn in l['synapses'][syntype]:
                        ax.plot([syn, syn], [x + .5, x - .5],
                                c=self.colormap_synapses[syntype],
                                linewidth=.3)

            if 'main_bifurcation' in l:
                ax.plot([l['x_dist_end']], [l['x']], 'o')
        ax.set_title(self.title)
        ax.set_ylabel('branch id')

        xlim = ax.get_xlim()
        return xlim

    def _compute_dendrite_and_synapse_counts(self, dist_end=None, binsize=50):
        if dist_end is None:
            dist_end = self._get_max_somadistance()
        bins = I.np.arange(0, dist_end + binsize, binsize)

        dendrite_density = [
            self.get_amount_of_dendrite_in_bin(bins[lv], bins[lv + 1])
            for lv in range(len(bins) - 1)
        ]
        synapse_density = [
            self.get_number_of_synapses_in_bin(bins[lv], bins[lv + 1])
            for lv in range(len(bins) - 1)
        ]
        synapse_density_apical = [
            self.get_number_of_synapses_in_bin(bins[lv],
                                               bins[lv + 1],
                                               select=['ApicalDendrite'])
            for lv in range(len(bins) - 1)
        ]
        synapse_density_basal = [
            self.get_number_of_synapses_in_bin(bins[lv],
                                               bins[lv + 1],
                                               select=['Dendrite'])
            for lv in range(len(bins) - 1)
        ]
        dendrite_density_apical = [
            self.get_amount_of_dendrite_in_bin(bins[lv],
                                               bins[lv + 1],
                                               select=['ApicalDendrite'])
            for lv in range(len(bins) - 1)
        ]
        dendrite_density_basal = [
            self.get_amount_of_dendrite_in_bin(bins[lv],
                                               bins[lv + 1],
                                               select=['Dendrite'])
            for lv in range(len(bins) - 1)
        ]

        self.bins = bins
        self.dendrite_density = dendrite_density = I.np.array(dendrite_density)
        self.synapse_density = synapse_density = I.np.array(synapse_density)
        self.synapse_density_apical = synapse_density_apical = I.np.array(
            synapse_density_apical)
        self.synapse_density_basal = synapse_density_basal = I.np.array(
            synapse_density_basal)
        self.dendrite_density_apical = dendrite_density_apical = I.np.array(
            dendrite_density_apical)
        self.dendrite_density_basal = dendrite_density_basal = I.np.array(
            dendrite_density_basal)

    def _plot_dendrite_and_synapse_counts(self, ax, xlim, binsize=50):
        self._compute_dendrite_and_synapse_counts(xlim[1], binsize=binsize)
        I.histogram((self.bins, self.dendrite_density),
                    label='dendrite',
                    colormap={'dendrite': 'k'},
                    fig=ax)
        ax2 = ax.twinx()
        I.histogram((self.bins, self.synapse_density),
                    label='dendrite',
                    colormap={'dendrite': 'r'},
                    fig=ax2)
        ax.set_ylabel('dendritic length / bin', color='k')
        ax2.set_ylabel('# synapses / bin', color='r')
        ax2.tick_params(axis='y', labelcolor='r')
        ax.set_xlim(xlim)

    def _plot_synapse_density(self, ax, xlim, binsize=50):
        self._compute_dendrite_and_synapse_counts(xlim[1], binsize=binsize)
        I.histogram((self.bins, self.synapse_density / self.dendrite_density),
                    label='total',
                    colormap={'total': 'k'},
                    fig=ax)
        # I.histogram((bins, synapse_density_basal / dendrite_density_basal), label = 'basal',
        #             colormap = {'basal': 'grey'}, fig = ax)
        # I.histogram((bins, synapse_density_apical / dendrite_density_apical), label = 'apical',
        #             colormap = {'apical': 'red'}, fig = ax)
        ax.legend()
        ax.set_xlim(xlim)
        ax.set_ylabel('# syn / micron dendritic length', color='k')
        ax.set_xlabel('somadistance / micron')

    def get_parent_by_name(self, name):
        sec = self.dendrogram_db_by_name[name]['sec'].parent
        if sec.label == 'Soma':
            return None
        else:
            return self.get_db_by_sec(
                sec)  # next(l for l in self.dendrogram_db if l['sec'] == sec)

    def get_parent_dist_by_name(self, name):
        parent = self.get_parent_by_name(name)
        x = self.dendrogram_db_by_name[name]['x']
        if parent is None:
            return x
        else:
            return x - parent['x']

    def get_db_by_sec(self, sec):
        return next(l for l in self.dendrogram_db if l['sec'] == sec)

    def get_amount_of_dendrite_in_bin(self,
                                      min_,
                                      max_,
                                      select=['Dendrite', 'ApicalDendrite']):

        out = 0
        for l in self.dendrogram_db:
            if not l['sec'].label in select:
                continue
            out += range_overlap(min_,
                                 max_,
                                 l['x_dist_start'],
                                 l['x_dist_end'],
                                 bool_=False)
        # if out < 50: return 0
        return out

    def get_number_of_synapses_in_bin(self,
                                      min_,
                                      max_,
                                      select=['Dendrite', 'ApicalDendrite'],
                                      label=None):
        out = 0
        for l in self.dendrogram_db:
            if not 'synapses' in l:
                continue
            if not l['sec'].label in select:
                continue
            for label in list(l['synapses'].keys()):
                for syn in l['synapses'][label]:
                    if min_ <= syn < max_:
                        out += 1
        return out

    def _compute_main_bifurcation_section(self):
        try:
            sec = get_main_bifurcation_section(self.cell)
        except AssertionError:
            print('main bifurcation could not be identified!')
            self.main_bifur_dist = None
        else:
            l = self.get_db_by_sec(sec)
            l['main_bifurcation'] = True
            self.main_bifur_dist = l['x_dist_end']

    def _get_max_somadistance(self):
        out = 0
        for l in self.dendrogram_db:
            out = max(out, l['x_dist_end'])
        self.max_somadist = out
        return out


#######################################
# class for exporting dendrogram objects
#######################################
class Synapse:
    '''mock synapse class that allows to use scp.writer.write_cell_synapse_locations'''

    def __init__(self, preCellType=None, secID=None, x=None):
        self.secID = secID
        self.x = x
        self.preCellType = preCellType


class ExportSynapses:

    def __init__(self, dendrogram):
        self.d = dendrogram
        self.synapses = None
        self.functionalMap = []
        self._create_synapses()

    def _create_synapses(self):
        d = self.d
        out = {}
        for l in d.dendrogram_db:
            sec_id = d.cell.sections.index(l['sec'])
            if 'synapses' in l:
                for syntype in list(l['synapses'].keys()):
                    if not syntype in out:
                        out[syntype] = []
                    list_ = l['synapses'][syntype]
                    for syn in list_:
                        syn = syn - l['x_offset'] - l['x_dist_start']
                        syn = syn / l['sec'].L
                        out[syntype].append(Synapse(syntype, sec_id, syn))
        for k in out:
            out[k] = sorted(out[k], key=lambda x: (x.secID, x.x))
        self.synapses = out

    def get_filtered_synapses_dict(self, synapse_types):
        '''returns self.synapses, but filtered, such that it only contains synapse types 
        that are an element of synapse_types'''
        return {k: v for k, v in self.synapses.items() if k in synapse_types}

    def create_functional_map_with_one_cell_per_synapse_from_cell_object(
            self, synapse_types=None):
        if synapse_types is None:
            synapses_dict = self.synapses
        else:
            synapses_dict = self.get_filtered_synapses_dict(synapse_types)
        functionalMap = [(k, lv, lv)
                         for k in list(synapses_dict.keys())
                         for lv in range(len(synapses_dict[k]))]
        self.functionalMap.extend(functionalMap)

    def create_functional_map_with_n_cells(self, synapse_type, n):

        synapses_dict = self.synapses
        cells = {k: [] for k in range(n)}
        synapses = list(range(len(synapses_dict[synapse_type])))
        import random
        for s in synapses:
            cell = random.choice(list(cells.keys()))
            cells[cell].append(s)

        values = [list(range(len(v))) for v in list(cells.values()) if v]
        cells = dict(list(
            zip(list(range(len(values))),
                values)))  # if cell has no assigned synapses, skip it

        functionalMap = []
        synid = 0
        for cellid in cells:
            for _ in cells[cellid]:
                functionalMap.append((synapse_type, cellid, synid))
                synid += 1

        #functionalMap = [(synapse_type, cellid, synid) for cellid in cells for synid in cells[cellid]]
        self.functionalMap.extend(functionalMap)

    def save(self, outdir):
        I.scp.writer.write_cell_synapse_locations(I.os.path.join(
            outdir, 'con.syn'),
                                                  self.synapses,
                                                  cellID='__no__anatomical__id')
        I.scp.writer.write_functional_realization_map(
            I.os.path.join(outdir, 'con.con'), self.functionalMap,
            '__no__anatomical__id')


# reload(hot_zone)
# k = 'CDK85'
# with I.silence_stdout:
#     cell = I.scp.create_cell(cell_params[k].neuron)
# d = hot_zone.Dendrogram(cell)
# path = mdb_formalized_input['network_embedding'][k]['0'].join('con.syn')
# syndict = I.scp.read_synapse_realization(path)
# for k, v in syndict.iteritems():
#     print k
#     d.add_synapses(k, v, mode = 'id_relative_position')
# exp = hot_zone.ExportSynapses(d)
# exp.create_functional_map_with_one_cell_per_synapse_from_cell_object()
# exp.save('/nas1/Data_arco/')
# syndict2 = I.scp.read_synapse_realization('/nas1/Data_arco/con.syn')

#####################################
# map synapses by profile
#####################################


def normalize_bins(bins, bifur, max_dist):
    '''normalizes bins such that soma is at 0, hot zone is at 1 and most distral branch is at 2'''
    out = []
    for b in bins:
        if b < bifur:
            out.append(float(b) / bifur)
        else:
            out.append((float(b) - bifur) / (max_dist - bifur) + 1)
    return out


def unnormalize_bins(bins, bifur, max_dist):
    '''reverses the normalization'''
    out = []
    for b in bins:
        if b < 1:
            out.append(b * bifur)
        else:
            out.append((b - 1) * (max_dist - bifur) + bifur)
    return out


bins = I.np.random.rand(10) * 10
bins2 = normalize_bins(bins, 6, 11)
bins3 = unnormalize_bins(bins2, 6, 11)
I.np.testing.assert_almost_equal(bins, bins3)


class MapSynapsesByProfile:

    def __init__(self, dendrogram):
        self.d = dendrogram
        self.profiles = {}

    def _get_sections_and_lengths_in_interval(self,
                                              min_,
                                              max_,
                                              select=[
                                                  'Dendrite', 'ApicalDendrite'
                                              ]):
        '''returns sections that can be found in a somadistance between min_ and max_.

        returns a 3-tuple, consisting of:
         - out_sec: list of PySection objects that can be found in a somadistance between min_ and max_
         - out_len: list containing the length of each section between min_ and max_
         - out_x_offset: some sections start proximal from min_. offset is the length from the beginning of
             the section till it reaches into to somadistance slice defined by min_ and max_'''

        d = self.d

        out_sec = []
        out_len = []
        out_x_offset = []
        for l in d.dendrogram_db:
            sec = l['sec']
            if not sec.label in select:
                continue
            len_ = range_overlap(min_,
                                 max_,
                                 l['x_dist_start'] + l['x_offset'],
                                 l['x_dist_end'],
                                 bool_=False)
            if len_ > 0:
                out_sec.append(l['sec'])
                out_len.append(len_)
                I.np.testing.assert_almost_equal(
                    l['x_dist_end'] - (l['x_dist_start'] + l['x_offset']),
                    sec.L)
                # taking care of sections that started proximal of min_ but reach into slice
                x_offset = min_ - l['x_dist_start'] + l['x_offset']
                x_offset = max(0, x_offset)
                out_x_offset.append(x_offset)
        return out_sec, out_len, out_x_offset

    def _map_single_synapse_in_interval(self,
                                        min_,
                                        max_,
                                        select=['Dendrite', 'ApicalDendrite'],
                                        normed=False):
        d = self.d
        out_sec, out_len, out_x_offset = self._get_sections_and_lengths_in_interval(
            min_, max_, select=select)
        id_, x = self._pick_random_point_on_segment(out_len)
        x = x + out_x_offset[id_]
        sec = out_sec[id_]
        sec_id = self.d.cell.sections.index(sec)
        if normed:
            x = x / sec.L
        return sec_id, x

    def _pick_random_point_on_segment(self, segment_lengths):
        segment_lengths_cumsum = I.np.cumsum(segment_lengths)
        r = I.np.random.rand() * segment_lengths_cumsum[-1]
        id_ = len(segment_lengths_cumsum[segment_lengths_cumsum < r])
        if id_ == 0:
            offset = 0
        else:
            offset = segment_lengths_cumsum[id_ - 1]
        return id_, r - offset

    def _get_n_syns_by_profile(self, density, n):
        return [
            self._pick_random_point_on_segment(density)[0] for lv in range(n)
        ]

    def map_synapses_by_somadistance_profile(self,
                                             name,
                                             n,
                                             select=[
                                                 'Dendrite', 'ApicalDendrite'
                                             ]):
        bins, density = self.profiles[name]
        out = []
        n_syn_per_bin = self._get_n_syns_by_profile(density, n)
        for bin_id in n_syn_per_bin:
            syn = self._map_single_synapse_in_interval(bins[bin_id],
                                                       bins[bin_id + 1],
                                                       select=select)
            out.append(syn)
        return out

    def add_profile(self, name, bins, density, mode='soma_dist_micron'):
        if mode == 'soma_dist_micron':
            pass
        elif mode == 'main_bifur':
            bifur = self.d.main_bifur_dist
            maxd = self.d._get_max_somadistance()
            # print bifur, maxd
            bins = unnormalize_bins(bins, bifur, maxd)
        else:
            raise ValueError('mode must be soma_dist_micron or main_bifur')

        density_unnormalized = [
        ]  # density was normalized by amount of dendritic structure
        for lv in range(len(density)):
            factor = self.d.get_amount_of_dendrite_in_bin(
                bins[lv], bins[lv + 1])
            density_unnormalized.append(float(density[lv]) * factor)

        self.profiles[name] = (bins, density_unnormalized)


###################################
# combining syn and con files
###################################


class NetworkEmbedding:
    '''class that can read and write syn and confiles.
    
    Allows adding connections by the + operator.
    '''

    def __init__(self):
        self.synapses = {}
        self.functionalMap = {}

    def load(self, synpath=None, conpath=None):
        if synpath is not None:
            assert synpath.endswith('.syn')
            conpath = synpath[:-4] + '.con'
        elif conpath is not None:
            assert conpath.endswith('.con')
            synpath = conpath[:-4] + '.con'
        else:
            raise ValueError("you must specify either synpath or conpath!")
        self.synapses = I.scp.reader.read_synapse_realization(synpath)
        self.functionalMap = I.scp.reader.read_functional_realization_map(
            conpath)[0]

    # def add_hoc(self, hocpath):
    #     self.hocpath = hocpath
    #     self.cell = get_cell_object_from_hoc(hocpath)
    #     self.Dendrogram = Dendrogram(self.cell)

    def _check(self):
        if not set(self.synapses.keys()) == set(self.functionalMap.keys()):
            errstr = 'Cell types, for which synapses are specified ({}) and for which '.format(
                str(list(self.synapses.keys())))
            errstr += 'functional map is specified ({}) must be identical'.format(
                str(list(self.functionalMap.keys())))
            raise RuntimeError(errstr)
        for k in list(self.synapses.keys()):
            if not len(self.synapses[k]) == len(self.functionalMap[k]):
                errstr = 'Number of entries in synapses and functional map is not the same '
                errstr += 'for type {}!'.format(k)
                raise RuntimeError(errstr)

    import six

    def _get_synapse_object_dict(self):
        out = {}
        for synapse_type, synapse_list in six.iteritems(self.synapses):
            out[synapse_type] = [
                Synapse(synapse_type, s[0], s[1]) for s in synapse_list
            ]
        #for k in out:
        #    out[k] = sorted(out[k], key = lambda x: (x.secID, x.x))
        return out

    def save(self, outdir):
        self._check()
        synapses = self._get_synapse_object_dict()
        functionalMap = []
        for k in list(synapses.keys()):
            functionalMap.extend(self.functionalMap[k])
        I.scp.writer.write_cell_synapse_locations(I.os.path.join(
            outdir, 'con.syn'),
                                                  synapses,
                                                  cellID='__no__anatomical__id')
        I.scp.writer.write_functional_realization_map(
            I.os.path.join(outdir, 'con.con'), functionalMap,
            '__no__anatomical__id')

    def __add__(self, b):
        out = NetworkEmbedding()
        out.synapses = self.synapses
        out.functionalMap = self.functionalMap
        out.synapses.update(b.synapses)
        out.functionalMap.update(b.functionalMap)
        return out


#syn = '/nas1/Data_regger/AXON_SAGA/Axon4/PassiveTouch/L5tt/network_embedding/postsynaptic_location/3x3_C2_sampling/C2center#/86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2center_synapses_20150504-1611_10389/86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2center_synapses_20150504-1611_10389.syn'
#folder_ = I.tempfile.mkdtemp()
#ne = NetworkEmbedding()
#ne.load(syn)
#ne.save(folder_)
#ne2 = NetworkEmbedding()
#ne2.load(I.os.path.join(folder_, 'con.syn'))
#I.shutil.rmtree(folder_)

#assert ne.synapses == ne2.synapses
#assert ne.functionalMap == ne2.functionalMap

######################################
# class for loading cells
#####################################


class CellLoader():

    def __init__(self):
        # see here for preprocessing of the cells: 20190909_VPM_contact_analysis_for_mike_review.ipynb
        self.identifiers = [
            'WR54_Cell2_L5ST', 'WR58_Cell5_L5TT_Final',
            'WR64_Cell8_L5TT_MikesASC', 'WR69_Cell2_L5TT',
            'WR70_Cell3_L5TT_S3_Added_Moved_to_A1', 'WR70_Cell5_L5TT',
            'WR71_ Cell6_L5TT', 'WR77_lhs_Cell5_L5TT_TuftFixed',
            'WR81_Cell1_L5TT'
        ]

        self.suffixes = {
            'unregistered':
                '.hoc',
            'D2':
                '_D2-registered.hoc',
            'landmark':
                '_Combination.landmarkAscii',
            'landmark_aligned':
                '_Combination_aligned.landmarkAscii',
            'landmark_D2':
                '_Combination_aligned_D2.landmarkAscii',
            'landmark_D2_top_bottom':
                '_Combination_aligned_D2_added_top_and_bottom_point.landmarkAscii'
        }

    def get_cell_object(self, id_, suffix):
        hocpath = mdb_cells['Data'].join(id_ + self.suffixes[suffix])
        return get_cell_object_from_hoc(hocpath)

    def get_synapses(self, id_):
        return mdb_cells[(id_, 'registered_points')]


############################################
# mapping landmarks on cell
###########################################


def get_cell_object_from_hoc_no_NEURON(hocpath, setUpBiophysics=True):
    '''returns cell object, which allows accessing points of individual branches'''
    import singlecell_input_mapper.singlecell_input_mapper.cell
    ssm = singlecell_input_mapper.singlecell_input_mapper.cell.CellParser(
        hocpath)
    ssm.spatialgraph_to_cell()
    return ssm.cell


def distance_between_points(point1, point2):
    '''returns distance between two points'''
    return I.np.sqrt(((point1 - point2)**2).sum())
    # return I.np.sqrt(sum([(p1-p2)**2 for p1, p2 in zip(point1, point2)]))


def register_point_to_line(line_point_1, line_point_2, point):
    '''registers a point to a line from line_point_1 to line_point_2.
    
    Returns: distance, x, projected_point
    
    distance: how much the poin gets moved
    x: between 0 and 1. 
        0 means, the registered point is identical to line_point_1. 
        1 means, the registered point is identical to line_point_1.
    projected_point: 3d coordinates of registered point'''
    line_point_1 = I.np.array(line_point_1)
    line_point_2 = I.np.array(line_point_2)
    point = I.np.array(point)

    line_vector_length = distance_between_points(line_point_1, line_point_2)
    line_vector = (line_point_2 - line_point_1)  # / line_vector_length
    point_vector = (point - line_point_1)
    x = I.np.dot(line_vector, point_vector)  # / line_vector_length
    if x > 1:
        x = 1
    elif x < 0:
        x = 0
    if line_vector_length == 0:
        factor = 0
    else:
        factor = 1. / (line_vector_length * line_vector_length)
    projected_point = line_point_1 + line_vector * x * factor
    distance = distance_between_points(point, projected_point)
    return distance, x * factor, projected_point


I.np.testing.assert_almost_equal(
    register_point_to_line([0, 0, 0], [0, 1, 1], [0, .5, .5])[0], 0)
I.np.testing.assert_almost_equal(
    register_point_to_line([0, 0, 0], [0, 1, 1], [0, .5, .5])[1], 0.5)
I.np.testing.assert_almost_equal(
    register_point_to_line([0, 1, 1], [0, 2, 2], [0, .5, .5])[0],
    I.np.sqrt(1 / 2.))
I.np.testing.assert_almost_equal(
    register_point_to_line([0, 1, 1], [0, 2, 2], [0, .5, .5])[1], 0)
I.np.testing.assert_almost_equal(
    register_point_to_line([0, 1, 1], [0, 2, 2], [0, 1.5, 1.5])[0], 0)
I.np.testing.assert_almost_equal(
    register_point_to_line([0, 1, 1], [0, 2, 2], [0, 1.5, 1.5])[1], 0.5)


def register_point_to_cell(point, cell, max_dist=100):

    def get_point_distances(point, cell):
        out = []
        for sec_lv, sec in enumerate(cell.sections):
            if sec.label in ('Myelin', 'AIS'):
                continue
            for lv in range(len(sec.pts) - 1):
                res_ = register_point_to_line(sec.pts[lv], sec.pts[lv + 1],
                                              point)
                res_ = (sec_lv, lv), res_
                out.append(res_)
        return out

    distances = get_point_distances(point, cell)
    print(len(distances))
    return sorted(distances, key=lambda x: x[1][0])[0]


register_point_to_cell_delayed = I.dask.delayed(register_point_to_cell)


def unregister_points_on_cell(points, cell):
    out = []
    for (sec_lv, lv), (distance, x, projected_point) in points:
        line_point_1 = I.np.array(cell.sections[sec_lv].pts[lv])
        line_point_2 = I.np.array(cell.sections[sec_lv].pts[lv + 1])
        line_vector = line_point_2 - line_point_1
        out.append(line_point_1 + line_vector * x)
    return out


############################
# function for creating color coded spike raster plots
############################


def get_st_pattern(st, event_maxtimes):
    import spike_analysis.core
    sta2 = spike_analysis.core.SpikeTimesAnalysis(None)
    sta2._db['st'] = st  # sta.get('st_df')
    sta2.apply_extractor(
        spike_analysis.core.STAPlugin_annotate_bursts_in_st(
            event_maxtimes=event_maxtimes))
    return sta2.get('bursts_st')


def event_rasterplot(st,
                     st_prox=None,
                     rasterplot_fun=I.rasterplot2,
                     event_maxtimes={
                         0: 0,
                         1: 10,
                         2: 30
                     },
                     **kwargs):
    '''like I.rasterplot2, but plots doublets red and triplets cyan'''
    if not 'ax' in kwargs:
        kwargs['ax'] = I.plt.figure(figsize=(8, 4), dpi=200).add_subplot(111)
    st_pattern = get_st_pattern(st, event_maxtimes)
    #return st_pattern, st
    rasterplot_fun(st[st_pattern == 'singlet'], c='#000000', **kwargs)
    rasterplot_fun(st[st_pattern == 'doublet'], c='#00aaaa', **kwargs)
    if st_prox is not None:
        rasterplot_fun(st_prox, c='orange', marker='.', **kwargs)
    rasterplot_fun(st[st_pattern == 'triplet'], c='#ff0000', **kwargs)


def get_doublet_triplet_times(x):
    assert x == sorted(x)
    out_triplet = []
    out_doublet = []
    lv = 0
    while lv < len(x):
        if (lv + 3 - 1 < len(x)) and (x[lv + 3 - 1] - x[lv] <= 30):
            out_triplet.append(x[lv])
            lv += 2
        elif (lv + 2 - 1 < len(x)) and (x[lv + 2 - 1] - x[lv] <= 10):
            out_doublet.append(x[lv])
            lv += 1
        lv = lv + 1
    return out_doublet, out_triplet


def get_doublet_triplet_times_series(x, return_=None):
    assert isinstance(x, I.pd.Series)
    x = list(x.dropna())
    if return_ == 'doublet':
        out = get_doublet_triplet_times(x)[0]
    elif return_ == 'triplet':
        out = get_doublet_triplet_times(x)[1]
    else:
        raise ValueError()
    return I.pd.Series(out)


############################
# ephys extraction, which I also provided to Mike for his thesis
############################
import sys

sys.path.append('../project_src/SpikeAnalysis/')
import spike_analysis.core

ReaderSmr = spike_analysis.core.ReaderSmr
SpikeDetectionCreastTrough = spike_analysis.core.SpikeDetectionCreastTrough
SpikeTimesAnalysis = spike_analysis.core.SpikeTimesAnalysis


def get_sta(path, offset=0):
    sdct = SpikeDetectionCreastTrough.load(path)
    stim = path.split('/')[-2]
    sta = SpikeTimesAnalysis(sdct, periods=periods[stim])
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_spike_times_dataframe(name='st_df',
                                                            offset=offset))
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_response_probability_in_period(
            name='p_onset', period='1onset'))
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_response_latency_in_period(
            name='latency_onset', period='1onset'))
    try:
        sta.apply_extractor(
            spike_analysis.core.STAPlugin_quantification_in_period(
                name='f_sustained', period='2sustained'))
    except KeyError:
        pass
    sta.apply_extractor(spike_analysis.core.STAPlugin_ISIn('ISIn_edf'))
    sta.apply_extractor(spike_analysis.core.STAPlugin_bursts('bursts_edf'))
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_extract_column_in_filtered_dataframe(
            name='singlet_times',
            column_name='event_time',
            source='bursts_edf',
            select={'event_class': 'singlet'}))
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_extract_column_in_filtered_dataframe(
            name='doublet_times',
            column_name='event_time',
            source='bursts_edf',
            select={'event_class': 'doublet'}))
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_extract_column_in_filtered_dataframe(
            name='triplet_times',
            column_name='event_time',
            source='bursts_edf',
            select={'event_class': 'triplet'}))
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_ongoing(name='ongoing_doublets',
                                              source='doublet_times',
                                              mode='count'))
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_ongoing(name='ongoing_triplets',
                                              source='triplet_times',
                                              mode='count'))
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_spike_times_dataframe(
            name='singlet_df', source='singlet_times'))
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_spike_times_dataframe(
            name='doublet_df', source='doublet_times'))
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_spike_times_dataframe(
            name='triplet_df', source='triplet_times'))
    sta.apply_extractor(spike_analysis.core.STAPlugin_ongoing('ongoing'))
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_ongoing('ongoing_doublet',
                                              source='doublet_times',
                                              mode='count'))
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_ongoing('ongoing_triplet',
                                              source='triplet_times',
                                              mode='count'))
    try:
        sta.apply_extractor(
            spike_analysis.core.STAPlugin_quantification_in_period(
                'n_sustained_triplet',
                source='triplet_df',
                mode='count_total',
                period='2sustained'))
    except KeyError:
        pass
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_quantification_in_period(
            'n_onset_singlet',
            source='singlet_df',
            mode='count_total',
            period='1onset'))
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_quantification_in_period(
            'n_onset_triplet',
            source='triplet_df',
            mode='count_total',
            period='1onset'))
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_quantification_in_period(
            'n_onset_doublet',
            source='doublet_df',
            mode='count_total',
            period='1onset'))
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_quantification_in_period(
            'n_spikes_in_onset_period',
            source='st_df',
            mode='count_total',
            period='1onset'))
    sta.apply_extractor(
        spike_analysis.core.STAPlugin_annotate_bursts_in_st(source='st_df'))
    return sta


#############################################################################
# functions to visualize simulation results
#############################################################################
def get_sorted_recsite_names(mdb):
    keys = mdb['dendritic_recordings'].keys()
    dist = [float(k.split('_')[-1]) for k in keys]
    return [key for _, key in sorted(zip(dist, keys))]


from model_data_base.mdb_initializers.load_simrun_general import add_dendritic_voltage_traces


class Plot:

    def __init__(self, mdb):
        self.mdb = mdb
        self.models = [
            k for k in mdb.keys() if I.utils.convertible_to_int(k[0:4])
        ]
        print('found models', self.models)
        self.select_depth = None
        self.select_value = None

    def set_selector(self, depth=None, value=None):
        '''the index is formatted like a path. You can select the [depth] element of the path to be [value]'''
        self.select_depth = depth
        self.select_value = value

    def get_individual_dataframes(self,
                                  key,
                                  subkey,
                                  n=None,
                                  value=None,
                                  sample=None,
                                  add_model_to_index=True):
        out = []
        for model in self.models:
            x = self.mdb[model][key][subkey]
            try:
                x = x.compute()
            except AttributeError:
                pass
            if self.select_depth is not None:
                select = x.index.str.split('/').str[self.select_depth].astype(
                    float)
                x = x[select == self.select_value]
            if sample is not None:
                x = x.iloc[1::sample]
            if add_model_to_index:
                x.index = ['/'.join([model, xx]) for xx in x.index]
            out.append(x)
        return out

    def get_st(self, key, sample=None):
        sts = self.get_individual_dataframes(key, 'spike_times', sample=sample)
        st = I.pd.concat(sts, axis=0)
        return st

    def rasterplot(self,
                   key,
                   ax=None,
                   offset=245,
                   sample=None,
                   raterplot_kwargs={}):
        st = self.get_st(key, sample=sample)
        st = st - offset
        fig = None
        if ax is None:
            fig = I.plt.figure(figsize=(10, 6), dpi=200)
            ax = fig.add_subplot(111)
        dist_st = self.get_dist_st(key, sample=sample)
        dist_st = dist_st - offset
        event_rasterplot(st, st_prox=dist_st, ax=ax, **raterplot_kwargs)
        # I.rasterplot2(dist_st, ax = ax, c = 'orange', **raterplot_kwargs)
        for h in I.np.cumsum([
                len(l) for l in self.get_individual_dataframes(
                    key, 'spike_times', sample=sample)
        ])[:-1]:
            I.plt.axhline(h, color='grey', linewidth=0.5, linestyle='--')
        return fig, ax

    # def get_dist_st(self, key, sample = None):
    #     out = []
    #     sts = self.get_individual_dataframes(key, 'spike_times', add_model_to_index = False)
    #     for model, st in zip(self.models, sts):
    #         if not 'dendritic_recordings' in self.mdb[model][key].keys():
    #             self._reinit_mdb(self.mdb[model][key])
    #         vt = get_prox_recsite(self.mdb[model][key])
    #         vt = vt.loc[list(st.index)].compute(get = I.dask.get)
    #         st = vt_to_st(vt, -20)
    #         if sample is not None:
    #             st = st.iloc[1::sample]
    #         out.append(st)
    #     return I.pd.concat(out, axis = 0)

    def get_dist_st(self, key, sample=None, recsite='prox', threshold='-30.0'):
        out = []
        sts = self.get_individual_dataframes(key,
                                             'spike_times',
                                             add_model_to_index=False)
        if recsite == 'prox':
            recsite = get_sorted_recsite_names(self.mdb[self.models[0]][key])[0]
        elif recsite == 'dist':
            recsite = get_sorted_recsite_names(self.mdb[self.models[0]][key])[1]
        recsite = recsite + '_' + threshold
        for model, st in zip(self.models, sts):
            if not recsite in self.mdb[model][key][
                    'dendritic_spike_times'].keys():
                self._reinit_mdb(self.mdb[model][key],
                                 dendritic_spike_times_threshold=threshold)
            x = self.mdb[model][key]['dendritic_spike_times'][recsite].loc[
                st.index]
            if sample is not None:
                x = x.iloc[1::sample]
            out.append(x)
        return I.pd.concat(out, axis=0)

    def _reinit_mdb(self,
                    mdb,
                    rewrite_in_optimized_format=False,
                    dendritic_spike_times=True,
                    repartition=True,
                    dendritic_spike_times_threshold='-30.0'):
        add_dendritic_voltage_traces(mdb,
                                     rewrite_in_optimized_format,
                                     dendritic_spike_times,
                                     repartition,
                                     dendritic_spike_times_threshold=float(
                                         dendritic_spike_times_threshold))
        # I.mdb_init_simrun_general.init(mdb, mdb['simresult_path'], client = client, rewrite_in_optimized_format = False)

    def plot_dendritic_recordings(self, key, ax=None, offset=245):
        sts = self.get_individual_dataframes(key, 'spike_times')
        for model, st in zip(self.models, sts):
            st = st - offset
            if not 'dendritic_recordings' in self.mdb[model][key].keys():
                self._reinit_mdb(self.mdb[model][key])
            plot_prox_vt(self.mdb[model][key], list(st.index))


#
def categorize_onset_response(st, tmin, tmax):
    '''the default method for determining and categorizing the onset response'''
    st = st.copy()
    early_ = I.spike_in_interval(st, tmin - 10, tmin)
    st[st < tmin] = I.np.nan
    st.values.sort()
    st[st > tmax] = I.np.nan
    st = st - tmin
    out = I.pd.Series(index=st.index)
    out[st[0] > 0] = 'singlet'
    out[(st[1] - st[0]) <= 10] = 'doublet'
    out[(st[2] - st[0]) <= 30] = 'triplet'
    out = out.fillna('no response')
    out[early_] = 'early_' + out
    return out