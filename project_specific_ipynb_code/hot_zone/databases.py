import Interface as I

# spike times
mdb_VPM = I.ModelDataBase(
    '/gpfs/soma_fs/ibs/current_data/Data_arco/results/20191202_rajeev_ongoing_VPM'
)
mdb_RN_BC = I.ModelDataBase(
    '/gpfs/soma_fs/ibs/current_data/Data_arco/results/20210520_analyze_rajeevs_barrel_cortex_air_puff_responses_for_hot_zone_paper/'
)
mdb_MG = I.ModelDataBase(
    '/gpfs/soma_fs/ibs/current_data/Data_arco/results/20200117_analysis_of_led_and_airpuff_recordings_paper_review'
)

# example simulation trials for figure 3 with fitted sustained activity
mdb_fig3_with_sustained = I.ModelDataBase(
    '/gpfs/soma_fs/scratch/abast/results/20230312_hot_zone_figure_3_v2')

# database with morphologies registered to 9 positions and network embeddings
anatomical_model_mdb = I.ModelDataBase(
    '/gpfs/soma_fs/scratch/abast/backup_axon_scratch_20211217/results/20200130_network_embedding_for_hot_zone_simulations/',
    readonly=True)

# mdb with simulations
mdb = I.ModelDataBase(
    '/gpfs/soma_fs/scratch/abast/results/20221030_hot_zone_on_interactive+big_simulations_many_morphologies_redo/'
)

# morphologies for biophysical simulations
morphologies_folder = mdb.create_managed_folder('morphologies', raise_=False)

# biopysics mdb
mdb_biopysics_selection = I.ModelDataBase(
    '/gpfs/soma_fs/scratch/abast/results/20221020_hot_zone_biophysical_composition',
    readonly=True)
mdb_biophysics_py3_BAC2_step = I.ModelDataBase(
    '/gpfs/soma_fs/scratch/abast/results/20220325_run_low_refractory_period_optimization3_two_BAC_plus_step'
)
mdb_WR69_step = I.ModelDataBase(
    '/gpfs/soma_fs/scratch/abast/backup_axon_scratch_20211217/results/20191231_fitting_WR69_2_Kv3_1_slope_variable_dend_scale_cluster_step/',
    readonly=True)
