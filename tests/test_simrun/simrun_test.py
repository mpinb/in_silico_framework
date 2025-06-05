from ..test_simrun.context import *
import os, sys, glob, dask
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
import dask
import single_cell_parser as scp
from single_cell_parser.cell_modify_functions.scale_apical_morph_86 import scale_apical_morph_86
import simrun.generate_synapse_activations
import simrun.run_new_simulations
import simrun.run_existing_synapse_activations
from data_base.IO.roberts_formats import read_pandas_synapse_activation_from_roberts_format
from ..test_simrun.context import NEUP_FN, NETP_FN, SYN_ACT_FN, SYN_ACT_SUBSAMPLED_FN, parent

assert os.path.exists(NEUP_FN)
assert os.path.exists(NETP_FN)
assert os.path.exists(SYN_ACT_FN)

T_STOP_SHORT = 20
T_STOP_FULL = 345


def test_generate_synapse_activation_returns_filelist(tmpdir, client):
    try:
        dummy = simrun.generate_synapse_activations.generate_synapse_activations(
            NEUP_FN,
            NETP_FN,
            dirPrefix=tmpdir.dirname,
            nSweeps=1,
            nprocs=1,
            tStop=T_STOP_SHORT,
            silent=True)
        dummy = client.compute(dummy).result()
    except:
        raise
    assert isinstance(dummy[0][0][0], str)


def test_run_existing_synapse_activation_returns_identifier_dataframe_and_results_folder(
        tmpdir, client):
    try:
        dummy = simrun.run_existing_synapse_activations.run_existing_synapse_activations(
            NEUP_FN,
            NETP_FN, [SYN_ACT_SUBSAMPLED_FN],
            dirPrefix=tmpdir.dirname,
            nprocs=1,
            tStop=T_STOP_SHORT,
            silent=True)
        dummy = client.compute(dummy).result()
    except:
        raise
    assert isinstance(dummy[0][0][0], pd.DataFrame)
    assert isinstance(dummy[0][0][1], str)


def test_run_new_simulations_returns_dirname(tmpdir):
    try:
        dummy = simrun.run_new_simulations.run_new_simulations(
            NEUP_FN,
            NETP_FN,
            dirPrefix=tmpdir.dirname,
            nSweeps=1,
            nprocs=1,
            tStop=T_STOP_SHORT,
            silent=True)
        # dummy is a list of delayeds
        result = dask.compute(*dummy)
    except:
        raise
    assert isinstance(result[0][0], str)


def test_position_of_morphology_does_not_matter_after_network_mapping(tmpdir, client):
    # simrun renames a dir once it finishes running
    # so create single-purpose subdirectories for simulation output
    subdir1 = tmpdir.mkdir("sub1")
    subdir2 = tmpdir.mkdir("sub2")
    subdir_params = tmpdir.mkdir("params")
    syn_act_fn = SYN_ACT_SUBSAMPLED_FN
    t_stop = T_STOP_SHORT
    
    
    try:
        dummy = simrun.run_existing_synapse_activations.run_existing_synapse_activations(
            NEUP_FN,
            NETP_FN, 
            synapseActivation=[syn_act_fn],
            dirPrefix=str(subdir1),
            nprocs=1,
            tStop=t_stop,
            silent=True)
        dummy = client.compute(dummy).result()

        cellParam = scp.build_parameters(NEUP_FN)
        # change location of cell by respecifying param file
        cellParam.neuron.filename = os.path.join(
            parent, 
            'test_simrun',
            'data',
            '86_L5_CDK20041214_nr3L5B_dend_PC_neuron_transform_registered_C2_B1border.hoc')
        cellParamName_other_position = os.path.join(
            str(subdir_params),
            'other_position.param')
        cellParam.save(cellParamName_other_position)


        dummy2 = simrun.run_existing_synapse_activations.run_existing_synapse_activations(
            cellParamName_other_position,
            NETP_FN, [syn_act_fn],
            dirPrefix=str(subdir2),
            nprocs=1,
            tStop=t_stop,
            silent=True)
        dummy2 = dummy2.compute()

        # Check that the two simulation runs have the same synapse activation
        df1 = read_pandas_synapse_activation_from_roberts_format(
            os.path.join(
                dummy[0][0][1], 'simulation_run%s_synapses.csv' %
                dummy[0][0][0].iloc[0].number))
        df2 = read_pandas_synapse_activation_from_roberts_format(
            os.path.join(
                dummy2[0][0][1], 'simulation_run%s_synapses.csv' %
                dummy[0][0][0].iloc[0].number))
        assert_frame_equal(df1, df2)
    except:
        raise


def test_reproduce_simulation_trial_from_roberts_model_control(tmpdir, client):
    # Note: these tolerances were found with trial and error, but have no further meaning
    if sys.platform.startswith('linux'):
        n_decimals=3
    elif sys.platform.startswith('darwin') or sys.platform.startswith('win32'):
        # OSX has updated NEURON version (NEURON 8), and the results are not exactly the same
        # compared to Robert's original results (NEURON < 7.8.2)
        n_decimals=1
    else:
        raise NotImplementedError("Platform not supported: %s" % sys.platform)

    syn_act_fn = SYN_ACT_FN

    try:
        dummy = simrun.run_existing_synapse_activations.run_existing_synapse_activations(
            NEUP_FN,
            NETP_FN, [syn_act_fn],
            dirPrefix=tmpdir.dirname,
            nprocs=1,
            tStop=345,
            silent=True,
            scale_apical=scale_apical_morph_86)
        dummy = client.compute(dummy).result()

        #synapse activation
        df1 = read_pandas_synapse_activation_from_roberts_format(
            os.path.join(
                dummy[0][0][1], 'simulation_run%s_synapses.csv' %
                dummy[0][0][0].iloc[0].number))
        df2 = read_pandas_synapse_activation_from_roberts_format(syn_act_fn)
        df1 = df1[[c for c in df1.columns if c.isdigit()] +
                  ['synapse_type', 'soma_distance', 'dendrite_label']]
        df2 = df2[[c for c in df1.columns if c.isdigit()] +
                  ['synapse_type', 'soma_distance', 'dendrite_label']]
        assert_frame_equal(df1, df2)

        # voltage traces
        vt_rerun_fn = glob.glob(os.path.join(dummy[0][0][1], '*_vm_all_traces*.csv'))
        assert len(vt_rerun_fn) == 1
        vt_rerun_fn = vt_rerun_fn[0]

        vt_presaved_fn = glob.glob(os.path.join(os.path.dirname(syn_act_fn), '*_vm_all_traces.csv'))
        assert len(vt_presaved_fn) == 1
        vt_presaved_fn = vt_presaved_fn[0]
        
        pdf1 = pd.read_csv(vt_presaved_fn, sep='\t')[['t', 'Vm run 00']]
        pdf2 = pd.read_csv(vt_rerun_fn, sep='\t')
        pdf2 = pdf2[pdf2['t'] >= 100].reset_index(drop=True)
        #print pdf1.values
        #print pdf2.values
        #for x,y in zip(pdf1[pdf1.t<265].values.squeeze(), pdf2[pdf2.t<265].values.squeeze()):
        #    print x,y
        
        # np.testing.assert_allclose(pdf1.values, pdf2.values, rtol=tol)
        np.testing.assert_almost_equal(pdf1.values, pdf2.values, decimal=n_decimals)
    except:
        raise
    assert isinstance(dummy[0][0][0], pd.DataFrame)
    assert isinstance(dummy[0][0][1], str)