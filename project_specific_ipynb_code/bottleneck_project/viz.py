import Interface as I
from helper_functions import get_section_distances_df, get_spatial_bin_names, get_model_stats
from project_specific_ipynb_code.hot_zone import get_main_bifurcation_section
from helper_functions import cartesian_product
from decoder_helper_functions import forward_decoder, torch


class WeightPlot():

    def __init__(self, neuron_param_file, model_mdb, model, bottleneck_node=0):
        """
        Given a model database, this class initializes a bunch of variables to be able to plot the weight plots, such as:
        - neuron parameter file
        - cell
        - section distances dataframe, spatial bin names, sections
        """
        self.model_mdb = model_mdb
        self.model = model
        self.bottleneck_node = bottleneck_node

        self.neuron_param_file = neuron_param_file
        self.neup = I.scp.NTParameterSet(self.neuron_param_file)
        print('Building cell from neuron parameter file')
        with I.silence_stdout:
            self.cell = I.scp.create_cell(self.neup.neuron)
        self.section_distances_df = get_section_distances_df(self.neup)
        self.spatial_bin_names = get_spatial_bin_names(
            self.section_distances_df)
        self.spatial_bin_names_df = I.pd.DataFrame(
            index=get_spatial_bin_names(self.section_distances_df))
        self.sorted_index = []

        self.tuft_sections = []
        self.oblique_sections = []
        self.trunk_sections = []

        self.__parse_sections()

    def __parse_sections(self):
        main_bifurc_sec = get_main_bifurcation_section(self.cell)
        self.trunk_sections = [main_bifurc_sec]
        while True:
            sec = self.trunk_sections[-1].parent
            if sec.label == 'Soma':
                break
            else:
                self.trunk_sections.append(sec)
        self.tuft_sections = []
        self.oblique_sections = []
        for sec in self.cell.sections:
            if not sec.label == 'ApicalDendrite':
                continue
            secp = sec.parent
            while True:
                if secp.label == 'Soma':
                    if not sec in self.trunk_sections:
                        self.oblique_sections.append(sec)
                    break
                if secp == main_bifurc_sec:
                    self.tuft_sections.append(sec)
                    break
                secp = secp.parent
        self.spatial_bin_names_df['soma_dist'] = I.np.nan
        for lv, sec in enumerate(self.cell.sections):
            if not sec.label in ['Dendrite', 'ApicalDendrite']:
                continue
            n_bins = self.section_distances_df.loc[lv]['n_bins']
            bin_of_each_point = I.np.digitize(sec.relPts,
                                              I.np.linspace(0, 1, n_bins + 1))
            for bin_ in range(1, n_bins + 1):
                xs = [
                    x for x, b in zip(sec.relPts, bin_of_each_point)
                    if b == bin_
                ]
                mean_x = I.np.mean(xs)
                bin_name = str(lv) + '/' + str(bin_)
                self.spatial_bin_names_df.loc[
                    bin_name,
                    'soma_dist'] = self.cell.distance_to_soma(sec, mean_x)
                self.spatial_bin_names_df.loc[bin_name,'label'] = '3_tuft' if sec in self.tuft_sections\
                                                                else '2_trunk' if sec in self.trunk_sections\
                                                                else '1_oblique' if sec in self.oblique_sections\
                                                                else '0_basal'
        self.spatial_bin_names_df['index'] = range(
            len(self.spatial_bin_names_df))
        self.sorted_index = [0] + list(self.spatial_bin_names_df.sort_values(['label', 'soma_dist']).dropna()['index'])  #.values

    def show_cell(self, ax, weights=None, scaling=None, t=0, show_bins=False):
        for lv, sec in enumerate(self.cell.sections):
            if sec.label in ['Soma', 'AIS', 'Myelin']:
                continue
            n_bins = self.section_distances_df.loc[lv]['n_bins']
            bin_of_each_point = I.np.digitize(sec.relPts,
                                              I.np.linspace(0, 1, n_bins + 1))
            for bin_ in range(1, n_bins + 1):
                if bin_ == 1:
                    x = [sec.pts[0][0]]
                    z = [sec.pts[0][2]]
                else:
                    x = [x[-1]]
                    z = [z[-1]]

                x = [
                    x[0]
                    for x, b in zip(sec.pts, bin_of_each_point)
                    if b == bin_
                ]
                # y = [x[1] for x, b in zip(sec.pts, bin_of_each_point) if b == bin_]
                z = [
                    x[2]
                    for x, b in zip(sec.pts, bin_of_each_point)
                    if b == bin_
                ]
                # d = [sec.parent.diamList[-1]]
                x = x[1:-1]
                z = z[1:-1]
                spatial_bin_name = str(lv) + '/' + str(bin_)
                spatial_bin_index = self.spatial_bin_names.index(
                    spatial_bin_name)
                if weights is None:
                    color = 'grey'
                    if sec in self.trunk_sections:
                        color = 'red'
                    if sec in self.tuft_sections:
                        color = 'blue'
                    if sec in self.oblique_sections:
                        color = 'green'
                else:
                    spatial_bin_name = str(lv) + '/' + str(bin_)
                    spatial_bin_index = self.spatial_bin_names.index(
                        spatial_bin_name)
                    color = get_color(weights[spatial_bin_index, t], -scaling,
                                      scaling)
                if show_bins == True:
                    ax.plot(x, z)
                else:
                    ax.plot(x, z, color=color)

    def plot_weights(self,
                     n_celltypes,
                     weight_scaling,
                     n_spatial_bins,
                     temporal_window_width,
                     celltype,
                     categories=True,
                     t=0,
                     return_axes=True,
                     epoch=None,
                     ts=None):
        """
        Given the weights of a neural network, this class method makes a visualisation of the neuron, the weights per section,
        and the train and test loss.

        This function is a bit of a mess when it comes to setting up the subplots.

        Arguments:
            weight: array of network weights to be visualised. this matrix will be reshapes according to the dimensions:
            n_celltypes: amount of celltypes
            n_spatial_bins: amount of spatial bins
            n_temporal_window_width: width of temporal window
            celltype: 0 for excitatory, 1 for inhibitory
            categories: (bool) label the different sections of the neuron
            epoch: index of the epoch to be plotted. If None, plots the best epoch.
            ts: timescale

        Returns:
            the axes if return_axes=True, else None
        """

        def add_cell_to_ax(wp, ax):
            if not categories:
                wp.show_cell(
                    ax,
                    weights=weights.reshape(n_celltypes, n_spatial_bins,
                                            temporal_window_width)[celltype] *
                    weight_scaling,
                    scaling=scaling,
                    t=t)
                #axes[0,1].axhline(t)

            else:
                wp.show_cell(ax)

            I.sns.despine(ax=ax, left=True, bottom=True)
            ax.set_aspect('equal')
            ax.set_xticks([])
            ax.set_yticks([])
            return ax

        def add_weights_to_axes(wp, axes):
            """Sets ups a plot that shows the cell object with weight values spatially resolved, two scatter plots showing the weight values and location labels, and two additional plots showing the AUC scores and training loss.

            Args:
                wp (WeightPlot): shoudl be self
                axes: the axes to add the plot to
            """

            def get_tick_positions_from_separators(separators):
                # Find out where the names of the categories should end up
                tick_positions = []
                _ = 0
                for s in separators:
                    tick_positions.append((s + _) / 2)
                    _ = s
                return tick_positions

            ### show weights
            for lv in range(n_celltypes):
                ax = axes[lv, 1]
                im = ax.imshow(I.np.transpose(weights1[lv]) * weight_scaling,
                               vmin=-scaling,
                               vmax=scaling,
                               cmap='seismic',
                               interpolation='none')
            gs = ax.get_gridspec()
            # remove the underlying axes
            for ax in axes[:, 2]:
                ax.remove()
            axbig = fig.add_subplot(gs[:, 2])
            fig.colorbar(im, cax=axbig)
            axbig.yaxis.set_ticks_position('left')
            separators = wp.spatial_bin_names_df.label.value_counts(
            ).sort_index().cumsum()
            axbig.set_aspect('auto', anchor='W')
            tick_positions = get_tick_positions_from_separators(separators)

            tick_names = ['basal', 'oblique', 'trunk', 'tuft']

            for lv in range(n_celltypes):
                ax = axes[lv, 1]
                ax.set_xticks(tick_positions)
                if lv < n_celltypes - 1:
                    ax.set_xticklabels('')
                else:
                    ax.set_xticklabels(tick_names)

                for lv in separators:
                    ax.axvline(lv + 0.5, color='k', linestyle='--', linewidth=1)

                ax.set_yticks([0, 20, 40, 60, 80])
                ax.set_yticklabels([-80, -60, -40, -20, 'now'])

            axes[0, 1].set_ylabel('EXC\ninput history / ms')
            axes[1, 1].set_ylabel('INH\ninput history / ms')
            axes[0, 1].set_aspect('equal', anchor='SE')
            axes[1, 1].set_aspect('equal', anchor='NE')

            #axes[0,1].set_title('EXC')
            #axes[1,1].set_title('INH')

            I.plt.tight_layout()
            I.sns.despine()

            gs = ax.get_gridspec()
            # remove the underlying axes
            for ax in axes[:, 0]:
                ax.remove()
            axcell = fig.add_subplot(gs[:, 0])

            add_cell_to_ax(wp, axcell)
            axes[1, 1].get_xticklabels()[0].set_color("grey")
            axes[1, 1].get_xticklabels()[1].set_color("green")
            axes[1, 1].get_xticklabels()[2].set_color("red")
            axes[1, 1].get_xticklabels()[3].set_color("blue")

            return axes

        def plot_aucs(axes):
            # plot AUCs
            ax = axes[0, 3]
            ax.plot(AUCs)
            ax.set_ylim(0.94, 0.98)
            ax.set_ylabel('AUROC')

            return axes

        def plot_loss(axes):
            # plot loss
            ax = axes[1, 3]
            ax.set_ylabel('loss')
            ax.plot(train_loss, label='train')
            ax.plot(test_loss, label='test')
            ax.set_xlabel('epoch')
            ax.legend()

            return axes

        _, best_epoch, AUCs, train_loss, test_loss, weights = get_model_stats(
            mdb=self.model_mdb,
            model=self.model,
            bottleneck_node=self.bottleneck_node)

        epoch = epoch if epoch else best_epoch

        ### figure specifications
        axscale = 1.5
        fig, axes = I.plt.subplots(
            2,
            4,
            gridspec_kw={'width_ratios': [20, 70, 1, 20]},
            figsize=(9 * axscale, 4 * axscale),
            dpi=150)
        ### preprocess weights
        weights1 = weights.reshape(n_celltypes, n_spatial_bins,
                                   temporal_window_width)[:,
                                                          self.sorted_index, :]
        scaling = max(weights1.max(), -weights1.min())

        axes = add_weights_to_axes(self, axes)
        axes = plot_aucs(axes)
        axes = plot_loss(axes)

        if ts is not None:
            title = 'history: {} ms'.format(-ts[t] - 1)
            axes[0, 1].set_title(title)
        if epoch is not None:
            axes[0, 3].axvline(epoch - 1,
                               color='k',
                               linestyle='--',
                               linewidth=1)
            axes[1, 3].axvline(epoch - 1,
                               color='k',
                               linestyle='--',
                               linewidth=1)
        axes[celltype, 1].axhline(t, color='k', linestyle='--', linewidth=1)

        if return_axes:
            return axes

    def save_plot_of_weights_at_t(self, t, n_celltypes, weight_scaling,
                                  n_spatial_bins, temporal_window_width,
                                  celltype, outdir):
        self.plot_weights(n_celltypes,
                          weight_scaling,
                          n_spatial_bins,
                          temporal_window_width,
                          categories=False,
                          celltype=celltype,
                          t=t,
                          return_axes=False)  # to make interactive plot
        I.plt.title("Time: {}".format(t))
        I.plt.savefig(outdir.join("frames/l5pt_weights_t={:03d}.png".format(t)),
                      dpi=100)
        I.plt.close()


def get_color(x, vmin, vmax, cm=I.matplotlib.cm.seismic):
    color_position = (x - vmin) / (vmax - vmin)
    return cm(color_position)


def write_frame_at_synaptic_input(weighted_input,
                                  df,
                                  stepsize=0.2,
                                  ax_lim=(0, 300),
                                  show=False):
    """
    Given a value for synaptic input (i.e. the first bottleneck node), writes out a frame with a 
    scatterplot of the training data that has an aggregated synaptic input between 
    :param weighted_input: and :param weighted_input: + :param stepsize:

    These can then be stitched together using ffmpeg by going to the directory where these frames are stored and running
    ```
    ml ffmpeg
    ffmpeg -framerate 12 -pattern_type glob -i "frames/training_data_input=*.png" -q:v 2 <output_name>.mp4
    ```
    """
    # setup figure
    I.plt.xlabel('soma_isi (ms)')
    I.plt.ylabel('dend_isi (ms)')
    I.plt.ylim(ax_lim)
    I.plt.xlim(ax_lim)
    I.plt.minorticks_off()  # speedup?

    # plot data
    data = df[(df["bottleneck_node"] <= weighted_input + stepsize) &
              (df["bottleneck_node"]
               > weighted_input)]  # this is surprisingly quick
    I.plt.scatter(data["soma_isi"].values,
                  data["dend_isi"].values,
                  s=3,
                  c=data["model_output"],
                  cmap="viridis",
                  vmin=0,
                  vmax=1)
    I.plt.title("weighted_input={}".format(round(weighted_input, 2)))
    I.plt.colorbar()

    # plot y=x for visual guide to see equal timing dend and soma
    I.plt.plot(ax_lim, ax_lim, color="black", linewidth=1)
    I.plt.plot(ax_lim, ax_lim, color="white", linewidth=.5)

    # save plot to disk -> largest bottleneck on speed so far
    suffix = int(str(round(weighted_input + 10,
                           2)).replace(".", ""))  # id for filename
    # I.plt.savefig(outdir.join("frames/training_data_input={:03d}.png".format(suffix)), dpi=200)
    if show:
        I.plt.show()
    I.plt.close()


@I.dask.delayed  # there is a lot of io going on, so running this with dask may crash dask
def write_overlay_frame(model,
                        weighted_input,
                        df,
                        outdir,
                        stepsize=0.2,
                        ax_lim=(0, 300),
                        show=False):
    """
    Given a value for synaptic input (i.e. the first bottleneck node), writes out a frame with:
    - All possible bottleneck values given the synaptic input (i.e. full range of dend_isi and soma_isi)
    - A scatterplot of the training data that has an aggregated synaptic input between
     :param weighted_input: and :param weighted_input: + :param stepsize:

    These can then be stitched together using ffmpeg by going to the directory where these frames are stored and running
    ```
    ml ffmpeg
    ffmpeg -framerate 12 -pattern_type glob -i "frames/overlay_SI=*.png" -q:v 2 <output_name>.mp4
    ```

    Args:
        - model: the bottleneck ANN model
        - weighted_input
        - df (pd.DataFrame): a pandas dataframe containing, for each entry, somatic inter-spike interval (ISI), dendritic ISI, the total weighted synaptic input that's being summed to the bottleneck, and the eventual model output prediciton
        - outdir: where to save the frames to for a video
    """
    # setup figure
    I.plt.xlabel('soma_isi (ms)')
    I.plt.ylabel('dend_isi (ms)')
    I.plt.ylim(ax_lim)
    I.plt.xlim(ax_lim)
    I.plt.minorticks_off()  # speedup?
    # data = df[(df["bottleneck_node"] <=weighted_input+stepsize) & (df["bottleneck_node"] > weighted_input)]

    # Construct full grid of possible decoder inputs with a specific dend_ISI
    bottleneck_values = I.np.array([-1 * weighted_input])  # flipped model
    soma_isi_inputs = I.np.arange(-0, 300, 1)
    ISI_dend_values = I.np.arange(-0, 300, 1)
    decoder_input = cartesian_product(bottleneck_values, soma_isi_inputs,
                                      ISI_dend_values)
    decoder_input_torch = torch.Tensor(decoder_input)
    # :,0 is bottleneck_node
    # :,1 is soma_isi
    # :,2 is dend_isi

    # Calculate model outputs of all inputs
    model_out_torch = forward_decoder(model, decoder_input_torch)
    model_out_torch = torch.sigmoid(model_out_torch)
    model_out_ = model_out_torch.cpu().detach().numpy()
    # plot all model predictions
    I.plt.scatter(decoder_input[:, 1],
                  decoder_input[:, 2],
                  s=2,
                  c=model_out_,
                  alpha=.1,
                  vmin=0,
                  vmax=1,
                  cmap='viridis')

    # plot ACTUAL input data
    # plot data
    data = df[(df["bottleneck_node"] <= weighted_input + stepsize) &
              (df["bottleneck_node"]
               > weighted_input)]  # this is surprisingly quick
    I.plt.scatter(data["soma_isi"].values,
                  data["dend_isi"].values,
                  s=3,
                  c=data["model_output"],
                  cmap="viridis",
                  vmin=0,
                  vmax=1)
    I.plt.title("weighted_input={}".format(round(weighted_input, 2)))
    I.plt.colorbar()

    # save plot
    suffix = int(str(round(weighted_input + 10,
                           2)).replace(".", ""))  # id for filename

    I.plt.savefig(outdir.join("frames/model_only={:03d}.png".format(suffix)),
                  dpi=200)
    if show:
        I.plt.show()
    I.plt.close()
