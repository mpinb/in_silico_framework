import logging
import os

import cloudpickle
import dask
import numpy as np
import pandas as pd
import pytest

from biophysics_fitting.exploration_from_seedpoint.RW import RW
from biophysics_fitting.exploration_from_seedpoint.RW_analysis import read_pickle
from biophysics_fitting.exploration_from_seedpoint.utils import read_df_file, read_particle_df


def _head_robust_read_pickle(path):
    '''robust_read_pickle as it was before read_df_file, to check the deprecated read_pickle alias against.'''
    try:
        df = pd.read_pickle(path)
        df['init_error'] = ''
        return df
    except:
        return pd.Series({"init_error": "Could not read {}".format(1)}).to_frame('init_error')


def _head_read_pickle(seed_folder, particle_id):
    '''read_pickle as it was before read_particle_df, to check the deprecated alias against.'''
    path = os.path.join(seed_folder, str(particle_id))
    df_names = [p for p in os.listdir(path) if p.endswith('.pickle')]
    df_names = sorted(df_names, key=lambda x: int(x.split('.')[0]))
    dfs = [_head_robust_read_pickle(os.path.join(path, p)) for p in df_names]
    if len(dfs) == 0:
        return 'empty'
    df = pd.concat(dfs).reset_index(drop=True)
    df['iteration'] = df.index
    df['particle_id'] = particle_id
    return df


def _results(first_value, n_rows):
    return pd.DataFrame({
        'x': np.arange(first_value, first_value + n_rows, dtype='float64'),
        'inside': np.arange(n_rows) % 2 == 0,
    })


@pytest.fixture
def particle_dir(tmp_path):
    '''Particle 0 of seedpoint 0 with 2.parquet (x 0-1), 10.pickle (x 2-4), 3.pickle (x 5-6) and a stray rngn file.'''
    path = tmp_path / '0' / '0'
    path.mkdir(parents=True)
    _results(0, 2).to_parquet(str(path / '2.parquet'))
    _results(2, 3).to_pickle(str(path / '10.pickle'))
    _results(5, 2).to_pickle(str(path / '3.pickle'))
    (path / '3.pickle.rngn').write_bytes(b'')
    return path


@pytest.mark.parametrize('extension', ['.pickle', '.parquet'])
def test_read_df_file_reads_both_types(tmp_path, extension):
    path = str(tmp_path / f'0{extension}')
    getattr(_results(0, 3), 'to_' + extension[1:])(path)
    pd.testing.assert_frame_equal(read_df_file(path), _results(0, 3))
    df = read_df_file(path, robust=True)
    pd.testing.assert_frame_equal(df.drop(columns='init_error'), _results(0, 3))
    assert (df['init_error'] == '').all()


def test_read_df_file_raises_unless_robust(tmp_path, caplog):
    bad = str(tmp_path / '0.parquet')
    with open(bad, 'wb') as f:
        f.write(b'garbage')
    with pytest.raises(Exception):
        read_df_file(bad)
    with caplog.at_level(logging.WARNING):
        df = read_df_file(bad, robust=True)
    assert list(df.columns) == ['init_error'] and len(df) == 1
    assert df['init_error'].iloc[0].startswith(f'Could not read {bad}: ')
    assert 'Could not read' in caplog.text


@pytest.mark.parametrize('reader, extension', [('read_pickle', '.pickle'), ('read_parquet', '.parquet')])
def test_read_df_file_lets_keyboard_interrupt_through(tmp_path, monkeypatch, reader, extension):
    def interrupted(path):
        raise KeyboardInterrupt()
    monkeypatch.setattr(pd, reader, interrupted)
    with pytest.raises(KeyboardInterrupt):
        read_df_file(str(tmp_path / f'0{extension}'), robust=True)


@pytest.mark.parametrize('robust', [False, True])
def test_read_df_file_keeps_stored_init_error(tmp_path, robust):
    path = str(tmp_path / '0.parquet')
    pd.DataFrame({'x': [1., 2.], 'init_error': ['', 'stored error']}).to_parquet(path)
    assert list(read_df_file(path, robust=robust)['init_error']) == ['', 'stored error']


@pytest.mark.parametrize('robust', [False, True])
def test_read_df_file_rejects_unknown_extension(tmp_path, robust):
    path = str(tmp_path / '0.pickle.rngn')
    _results(0, 1).to_pickle(path)
    with pytest.raises(ValueError, match='file extension'):
        read_df_file(path, robust=robust)


def test_read_particle_df_orders_by_iteration(particle_dir):
    df = read_particle_df(str(particle_dir.parent), 0)
    assert list(df['x']) == [0., 1., 5., 6., 2., 3., 4.]
    assert list(df['iteration']) == list(range(7))
    assert (df['particle_id'] == 0).all()
    assert (df['init_error'] == '').all()


def test_read_particle_df_non_robust_returns_stored_columns(particle_dir):
    df = read_particle_df(str(particle_dir.parent), 0, robust=False)
    assert list(df.columns) == ['x', 'inside', 'iteration', 'particle_id']


@pytest.mark.parametrize('file_types, expected_x', [
    (('.pickle',), [5., 6., 2., 3., 4.]),
    (('.parquet',), [0., 1.]),
    (['.parquet'], [0., 1.]),
])
def test_read_particle_df_filters_file_types(particle_dir, file_types, expected_x):
    df = read_particle_df(str(particle_dir.parent), 0, file_types=file_types)
    assert list(df['x']) == expected_x


def test_read_particle_df_empty(tmp_path):
    (tmp_path / '0' / '1').mkdir(parents=True)
    (tmp_path / '0' / '1' / '3.pickle.rngn').write_bytes(b'')
    assert read_particle_df(str(tmp_path / '0'), 1) == 'empty'


def test_read_particle_df_robust_and_raising(particle_dir):
    with open(str(particle_dir / '20.pickle'), 'wb') as f:
        f.write(b'garbage')
    df = read_particle_df(str(particle_dir.parent), 0)
    assert len(df) == 8
    assert df['init_error'].iloc[-1].startswith('Could not read')
    assert np.isnan(df['x'].iloc[-1])
    with pytest.raises(Exception):
        read_particle_df(str(particle_dir.parent), 0, robust=False)


def test_read_particle_df_mixes_empty_string_and_float_init_error(tmp_path):
    '''Some resume checkpoints store init_error as 0.0 instead of ''.'''
    path = tmp_path / '0' / '0'
    path.mkdir(parents=True)
    _results(0, 1).assign(init_error=0.0).to_parquet(str(path / '1.parquet'))
    _results(1, 2).to_parquet(str(path / '2.parquet'))
    _results(3, 2).assign(init_error='').to_parquet(str(path / '3.parquet'))
    df = read_particle_df(str(path.parent), 0)
    assert list(df['x']) == [0., 1., 2., 3., 4.]
    assert list(df['init_error']) == [0.0, '', '', '', '']


def test_deprecated_aliases_match_previous_behaviour(particle_dir):
    seed_folder = str(particle_dir.parent)
    new = read_pickle(seed_folder, 0)
    pd.testing.assert_frame_equal(new, _head_read_pickle(seed_folder, 0))
    assert (new['init_error'] == '').all()
    os.mkdir(os.path.join(seed_folder, '1'))
    assert read_pickle(seed_folder, 1) == _head_read_pickle(seed_folder, 1) == 'empty'


def test_deprecated_read_pickle_robust_to_unreadable_files(particle_dir):
    with open(str(particle_dir / '20.pickle'), 'wb') as f:
        f.write(b'garbage')
    new = read_pickle(str(particle_dir.parent), 0)
    old = _head_read_pickle(str(particle_dir.parent), 0)
    pd.testing.assert_frame_equal(new.drop(columns='init_error'), old.drop(columns='init_error'))
    assert new['init_error'].iloc[-1].startswith('Could not read') and old['init_error'].iloc[-1] == 'Could not read 1'


def test_deprecated_read_pickle_works_with_dask_delayed(particle_dir):
    delayed = dask.delayed(read_pickle)(str(particle_dir.parent), 0)
    df = delayed.compute(scheduler='synchronous')
    pd.testing.assert_frame_equal(df, _head_read_pickle(str(particle_dir.parent), 0))


@pytest.fixture
def checkpoint_dir(tmp_path):
    '''Particle 0 of seedpoint 0 with checkpoint pickles 10, 20 and 30, each with an rngn file as written by RW._save_checkpoint.'''
    path = tmp_path / '0' / '0'
    path.mkdir(parents=True)
    for i, iteration in enumerate([10, 20, 30]):
        _results(10 * i, 2).to_pickle(str(path / f'{iteration}.pickle'))
        (path / f'{iteration}.pickle.rngn').write_bytes(b'')
    return path


def test_concatenate_and_clean_merges_pickles_into_parquet(checkpoint_dir):
    RW.__new__(RW)._concatenate_and_clean(str(checkpoint_dir.parent), 0)
    assert sorted(os.listdir(str(checkpoint_dir))) == ['30.parquet', '30.pickle.rngn']
    df = pd.read_parquet(str(checkpoint_dir / '30.parquet'))
    assert list(df['x']) == [0., 1., 10., 11., 20., 21.]
    assert 'init_error' not in df.columns


def test_concatenate_and_clean_raises_on_corrupt_pickle_and_keeps_pickles(checkpoint_dir):
    with open(str(checkpoint_dir / '20.pickle'), 'wb') as f:
        f.write(b'garbage')
    files_before = sorted(os.listdir(str(checkpoint_dir)))
    with pytest.raises(Exception):
        RW.__new__(RW)._concatenate_and_clean(str(checkpoint_dir.parent), 0)
    assert sorted(os.listdir(str(checkpoint_dir))) == files_before


def test_load_existing_exploration_resumes_from_last_inside_model(tmp_path):
    '''The newest file (130.pickle) has no model inside the space, so the last inside model of 120.parquet is resumed from.'''
    pd.DataFrame({'a': [1., 2., 3.], 'inside': [True, True, False]}).to_parquet(str(tmp_path / '120.parquet'))
    pd.DataFrame({'a': [4.], 'inside': [False]}).to_pickle(str(tmp_path / '130.pickle'))
    with open(str(tmp_path / '130.pickle.rngn'), 'wb') as f:
        cloudpickle.dump('rngn state', f)
    rw = RW.__new__(RW)
    rw.all_param_names = pd.Index(['a'])
    p, iteration, pickle_count, rngn = rw._load_existing_exploration(str(tmp_path), [130, 120], os.listdir(str(tmp_path)))
    assert p['a'] == 2. and list(p.index) == ['a']
    assert (iteration, pickle_count, rngn) == (130, 1, 'rngn state')
