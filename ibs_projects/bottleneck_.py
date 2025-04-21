import Interface as I


def get_color(x, vmin, vmax, cm=I.matplotlib.cm.seismic):
    color_position = (x - vmin) / (vmax - vmin)
    ret = cm(color_position)
    if len(ret) == 1:
        raise
    return ret


def show_cell(ax, weights=None, scaling=None, t=0):
    '''uses global variables:
    trunk_sections, tuft_sections, oblique_sections'''
    for lv, sec in enumerate(cell.sections):
        if sec.label in ['Soma', 'AIS', 'Myelin']:
            continue
        n_bins = section_distances_df.loc[lv]['n_bins']
        bin_of_each_point = I.np.digitize(sec.relPts,
                                          I.np.linspace(0, 1, n_bins + 1))
        for bin_ in range(1, n_bins + 1):
            if bin_ == 1:
                x = [sec.parent.pts[-1][0]]
                z = [sec.parent.pts[-1][2]]
            else:
                x = [x[-1]]
                z = [z[-1]]
            x = x + [
                x[0] for x, b in zip(sec.pts, bin_of_each_point) if b == bin_
            ]
            z = z + [
                x[2] for x, b in zip(sec.pts, bin_of_each_point) if b == bin_
            ]

            spatial_bin_name = str(lv) + '/' + str(bin_)
            spatial_bin_index = spatial_bin_names.index(spatial_bin_name)
            if weights is None:
                color = 'grey'
                if sec in trunk_sections:
                    color = 'red'
                if sec in tuft_sections:
                    color = 'blue'
                if sec in oblique_sections:
                    color = 'green'
            else:
                spatial_bin_name = str(lv) + '/' + str(bin_)
                spatial_bin_index = spatial_bin_names.index(spatial_bin_name)
                color = get_color(weights[spatial_bin_index, t], -scaling,
                                  scaling)
            if show_bins == True:
                color = get_color(lv % bin_, 0, 3, cm=I.matplotlib.cm.jet)
            #color = get_color(weights.mean(axis = 1)[spatial_bin_index], -scaling, scaling)
            ax.plot(x, z, color=color)
            # I.plt.plot(x,z,alpha = 1)


## show morphology split up in dendrite pieces
def show_cell(ax,
              cell,
              weights=None,
              scaling=None,
              t=0,
              section_distances_df=None,
              spatial_bin_names=None,
              show_bins=False,
              spatial_bin_names_df=None):
    '''uses global variables:
    trunk_sections, tuft_sections, oblique_sections'''
    for lv, sec in enumerate(cell.sections):
        if sec.label in ['Soma', 'AIS', 'Myelin']:
            continue
        n_bins = section_distances_df.loc[lv]['n_bins']
        bin_of_each_point = I.np.digitize(sec.relPts,
                                          I.np.linspace(0, 1, n_bins + 1))
        for bin_ in range(1, n_bins + 1):
            if show_bins:
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
                z = [
                    x[2]
                    for x, b in zip(sec.pts, bin_of_each_point)
                    if b == bin_
                ]
                x = x[1:-1]
                z = z[1:-1]
            else:
                if bin_ == 1:
                    x = [sec.parent.pts[-1][0]]
                    z = [sec.parent.pts[-1][2]]
                else:
                    x = [x[-1]]
                    z = [z[-1]]
                x = x + [
                    x[0]
                    for x, b in zip(sec.pts, bin_of_each_point)
                    if b == bin_
                ]
                z = z + [
                    x[2]
                    for x, b in zip(sec.pts, bin_of_each_point)
                    if b == bin_
                ]
            spatial_bin_name = str(lv) + '/' + str(bin_)
            spatial_bin_index = spatial_bin_names.index(spatial_bin_name)
            if weights is None:
                trunk_sections = list(
                    set(spatial_bin_names_df[spatial_bin_names_df.label ==
                                             '2_trunk'].index.str.split(
                                                 '/').str[0].astype(int)))
                tuft_sections = list(
                    set(spatial_bin_names_df[spatial_bin_names_df.label ==
                                             '3_tuft'].index.str.split(
                                                 '/').str[0].astype(int)))
                oblique_sections = list(
                    set(spatial_bin_names_df[spatial_bin_names_df.label ==
                                             '1_oblique'].index.str.split(
                                                 '/').str[0].astype(int)))
                color = 'grey'
                if cell.sections.index(sec) in trunk_sections:
                    color = 'red'
                if cell.sections.index(sec) in tuft_sections:
                    color = 'blue'
                if cell.sections.index(sec) in oblique_sections:
                    color = 'green'
            else:
                spatial_bin_name = str(lv) + '/' + str(bin_)
                spatial_bin_index = spatial_bin_names.index(spatial_bin_name)
                color = get_color(weights[spatial_bin_index, t], -scaling,
                                  scaling)
            if show_bins == True:
                ax.plot(x, z)
            else:
                ax.plot(x, z, color=color)
                #color = get_color(lv%bin_, 0, 3, cm = I.matplotlib.cm.jet)
            #color = get_color(weights.mean(axis = 1)[spatial_bin_index], -scaling, scaling)
            # I.plt.plot(x,z,alpha = 1)


def plot_weights(weight,
                 bottleneck_size=None,
                 n_celltypes=None,
                 n_spatial_bins=None,
                 temporal_window_width=None,
                 sorted_index=None,
                 spatial_bin_names_df=None,
                 cell=None,
                 weight_scaling=1,
                 categories=True,
                 celltype_selected_for_dendrite_visualization=0,
                 timepoint_selected_for_dendrite_visualization=None,
                 section_distances_df=None,
                 AUCs=None,
                 train_loss=None,
                 test_loss=None,
                 savepath=None):
    ### figure specifications
    axscale = 1.5
    fig, axes = I.plt.subplots(2,
                               4,
                               gridspec_kw={'width_ratios': [20, 70, 1, 20]},
                               figsize=(9 * axscale,
                                        4 * axscale * bottleneck_size),
                               dpi=150)
    ### preprocess weights
    weights1 = weight.reshape(
        n_celltypes, n_spatial_bins,
        temporal_window_width)[:, sorted_index, :] * weight_scaling
    weights2 = weight.reshape(n_celltypes, n_spatial_bins,
                              temporal_window_width)[:, :, :] * weight_scaling
    # scaling = max(weights1.max(),-weights1.min())
    scaling = weights1.max()  # weights1[0,:,:].max()

    ### show weights
    for lv in range(n_celltypes):
        ax = axes[lv, 1]
        im = ax.imshow(I.np.transpose(weights1[lv]),
                       vmin=-scaling,
                       vmax=scaling,
                       cmap='seismic',
                       interpolation='none')
    ### colorbar
    gs = ax.get_gridspec()
    # remove the underlying axes
    for ax in axes[:, 2]:
        ax.remove()
    axbig = fig.add_subplot(gs[:, 2])
    fig.colorbar(im, cax=axbig)
    axbig.yaxis.set_ticks_position('left')
    #fig.colorbar(im, cax = axes[1,0])
    ### tickss (names and position)
    separators = spatial_bin_names_df.label.value_counts().sort_index().cumsum()
    axbig.set_aspect('auto', anchor='W')
    tick_posititions = []
    _ = 0
    for s in separators:
        tick_posititions.append((s + _) / 2)
        _ = s

    tick_names = ['basal', 'oblique', 'trunk', 'tuft']

    for lv in range(n_celltypes):
        ax = axes[lv, 1]
        ax.set_xticks(tick_posititions)
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

    ax = axcell

    if not categories:
        assert timepoint_selected_for_dendrite_visualization is not None
        assert celltype_selected_for_dendrite_visualization is not None
        show_cell(
            ax,
            cell=cell,
            weights=weights2[
                celltype_selected_for_dendrite_visualization, :, :],  # weight.reshape(n_celltypes,n_spatial_bins,temporal_window_width)[celltype_selected_for_dendrite_visualization],
            scaling=scaling,
            t=timepoint_selected_for_dendrite_visualization,
            section_distances_df=section_distances_df,
            spatial_bin_names=list(spatial_bin_names_df.index))
        #axes[0,1].axhline(t)

    else:
        show_cell(ax,
                  cell=cell,
                  section_distances_df=section_distances_df,
                  spatial_bin_names=list(spatial_bin_names_df.index),
                  spatial_bin_names_df=spatial_bin_names_df)

    I.sns.despine(ax=ax, left=True, bottom=True)
    ax.set_aspect('equal')
    ax.set_xticks([])
    ax.set_yticks([])
    axes[1, 1].get_xticklabels()[0].set_color("grey")
    axes[1, 1].get_xticklabels()[1].set_color("green")
    axes[1, 1].get_xticklabels()[2].set_color("red")
    axes[1, 1].get_xticklabels()[3].set_color("blue")

    ax = axes[0, 3]
    ax.plot(AUCs)
    ax.set_ylim(0.94, 0.98)
    ax.set_ylabel('AUROC')
    ax = axes[1, 3]
    ax.set_ylabel('loss')
    ax.plot(train_loss, label='train')
    ax.plot(test_loss, label='test')
    ax.set_xlabel('epoch')
    ax.legend()

    if savepath:
        fig.savefig(savepath)
    return axes