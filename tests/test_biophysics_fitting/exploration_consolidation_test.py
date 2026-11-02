import json
import os

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset
import pytest

from biophysics_fitting.exploration_from_seedpoint.RW import RW, concatenate_and_clean
from biophysics_fitting.exploration_from_seedpoint.RW_analysis import consolidate_exploration, load_exploration
from biophysics_fitting.exploration_from_seedpoint.utils import convert_all_check_columns_bool_to_float

KEYS = ['rw_errors', 'rw_inside', 'rw_outside']
INSIDE_X = [0., 1., 3., 5., 10., 11., 13.]
OUTSIDE_X = [2., 4., 6., 12., 20., 21.]


def _evaluation(x, inside, n_suggestion=1):
    '''An evaluation as RW.run_RW stores it. Outside models stopped early and lack the later objectives and the
    additional evaluation outputs. The seed evaluation of a fresh walk has no n_suggestion (pass None).'''
    evaluation = {'x': float(x), 'obj': x / 10, 'BAC_Soma_charge': 3., 'checkAP': str(x % 2 == 0)}
    if inside:
        evaluation.update({'a.check_1AP': True, 'a.raw': np.array([x, 1.]), 'b.spikecount.raw': 2})
    if n_suggestion is not None:
        evaluation['n_suggestion'] = n_suggestion
    evaluation['inside'] = inside
    return evaluation


def _checkpoint(seedpoint_dir, particle_id, iteration, evaluations, fold=True):
    path = os.path.join(seedpoint_dir, str(particle_id))
    os.makedirs(path, exist_ok=True)
    RW.__new__(RW)._save_checkpoint(iteration, evaluations, path)
    if fold:
        concatenate_and_clean(seedpoint_dir, particle_id)


@pytest.fixture
def exploration_dir(tmp_path):
    '''Seedpoint 0: particle 0 is a fresh walk folded twice, particle 1 is empty, particle 2 holds special cases and an
    unreadable file, particle 3 only an unreadable file.
    Seedpoint 1: particle 0 is a resumed walk with only outside rows and no array column.'''
    base = tmp_path / 'exploration'
    seedpoint_0 = str(base / '0')
    _checkpoint(seedpoint_0, 0, 2, [_evaluation(0, True, n_suggestion=None), _evaluation(1, True), _evaluation(2, False)],
                fold=False)
    _checkpoint(seedpoint_0, 0, 4, [_evaluation(3, True), _evaluation(4, False)])
    _checkpoint(seedpoint_0, 0, 6, [_evaluation(5, True), _evaluation(6, False)])

    (base / '0' / '1').mkdir()
    (base / '0' / '1' / '3.pickle.rngn').write_bytes(b'')

    special = base / '0' / '2'
    special.mkdir()
    seed_row = convert_all_check_columns_bool_to_float(pd.DataFrame([_evaluation(10, True)], index=[500]))
    seed_row['a.raw'] = [2.5]
    seed_row['p_id'], seed_row['init_error'], seed_row['seedpoint_id'], seed_row['iteration'] = 7, '', 99, 500
    seed_row.to_parquet(str(special / '1.parquet'))
    chunk = pd.DataFrame([_evaluation(x, x != 12) for x in (11, 12, 13)], index=[0, 0, 1])
    chunk['a.raw'] = [None, np.array([], dtype='int64'), np.array([3, 4])]
    chunk['a.check_1AP'] = [1., 0., np.nan]
    chunk['init_error'] = ''
    convert_all_check_columns_bool_to_float(chunk).to_parquet(str(special / '3.parquet'))
    (special / '5.parquet').write_bytes(b'garbage')

    (base / '0' / '3').mkdir()
    (base / '0' / '3' / '1.parquet').write_bytes(b'garbage')

    _checkpoint(str(base / '1'), 0, 12, [_evaluation(20, False), _evaluation(21, False)])
    (base / 'notes').mkdir()
    return str(base)


@pytest.fixture
def consolidated(exploration_dir, empty_db):
    summary = consolidate_exploration(exploration_dir, empty_db, 'rw')
    return empty_db, summary


def _load_all(db, columns=None):
    df = pd.concat([load_exploration(db, 'rw', subset=s, columns=columns).compute() for s in ('inside', 'outside')])
    return df.set_index(['seedpoint_id', 'particle_id', 'iteration']).sort_index()


def test_fixture_looks_like_rw_output(exploration_dir):
    assert sorted(os.listdir(os.path.join(exploration_dir, '0', '0'))) == [
        '4.parquet', '4.pickle.rngn', '6.parquet', '6.pickle.rngn']
    assert str(pd.read_parquet(os.path.join(exploration_dir, '0', '2', '3.parquet'))['a.raw'].iloc[2].dtype) == 'int64'
    folded = pd.read_parquet(os.path.join(exploration_dir, '0', '0', '4.parquet'))
    assert folded['n_suggestion'].isna().tolist() == [True, False, False, False, False]
    assert str(folded['checkAP'].dtype) == 'float64'
    assert str(folded['a.check_1AP'].dtype) == 'float64'


def test_summary_counts_rows_errors_and_empty_particles(consolidated, exploration_dir):
    db, summary = consolidated
    assert summary['n_rows'] == {'inside': 7, 'outside': 6}
    assert summary['n_partitions'] == {'inside': 2, 'outside': 3}
    assert summary['n_particles'] == 5
    assert summary['particles_without_files'] == [[0, 1]]
    assert [e['path'] for e in summary['unreadable_files']] == [
        os.path.join(exploration_dir, '0', '2', '5.parquet'), os.path.join(exploration_dir, '0', '3', '1.parquet')]
    assert all(e['error'] for e in summary['unreadable_files'])
    with open(os.path.join(db['rw_errors'], 'errors.json')) as f:
        errors = json.load(f)
    assert errors == {k: summary[k] for k in ('particles_without_files', 'unreadable_files')}
    assert sorted(db.keys()) == KEYS


def test_split_order_and_generated_columns(consolidated):
    db, _ = consolidated
    inside = load_exploration(db, 'rw').compute()
    outside = load_exploration(db, 'rw', subset='outside').compute()
    assert inside['inside'].all()
    assert not outside['inside'].any()
    assert list(inside['x']) == INSIDE_X
    assert list(outside['x']) == OUTSIDE_X
    assert list(inside['iteration']) == [0, 1, 3, 5, 0, 1, 3]
    assert list(outside['iteration']) == [2, 4, 6, 2, 0, 1]
    assert list(inside['seedpoint_id']) == [0] * 7
    assert list(outside['seedpoint_id']) == [0, 0, 0, 0, 1, 1]
    assert list(inside['particle_id']) == [0, 0, 0, 0, 2, 2, 2]
    assert list(outside['particle_id']) == [0, 0, 0, 2, 0, 0]
    assert list(inside.index) == list(range(7))
    assert list(outside.index) == list(range(6))


def test_dtypes_are_identical_in_all_partitions(consolidated):
    db, _ = consolidated
    expected = {
        'x': 'float64', 'obj': 'float64', 'BAC_Soma_charge': 'float64', 'checkAP': 'float64', 'a.check_1AP': 'float64',
        'a.raw': 'object', 'b.spikecount.raw': 'float64', 'n_suggestion': 'float64', 'inside': 'bool',
        'iteration': 'int64', 'particle_id': 'int64', 'p_id': 'float64', 'seedpoint_id': 'int64'}
    for subset in ('inside', 'outside'):
        ddf = load_exploration(db, 'rw', subset=subset)
        assert ddf.known_divisions
        assert {c: str(t) for c, t in ddf.dtypes.items()} == expected
        for partition in ddf.to_delayed():
            assert {c: str(t) for c, t in partition.compute().dtypes.items()} == expected
        key_dir = str(db._convert_key_to_path(f'rw_{subset}'))
        dataset = pyarrow.dataset.dataset([os.path.join(key_dir, f) for f in os.listdir(key_dir) if f.endswith('.parquet')])
        assert dataset.schema.field('a.raw').type == pa.list_(pa.float64())
        assert dataset.to_table().num_rows == len(ddf)


def test_seed_row_of_fresh_walk_without_n_suggestion(consolidated):
    df = _load_all(consolidated[0])
    assert np.isnan(df.loc[(0, 0, 0), 'n_suggestion'])
    assert list(df.loc[(0, 0), 'n_suggestion'].iloc[1:]) == [1.] * 6


def test_check_columns(consolidated):
    df = _load_all(consolidated[0])
    assert list(df.loc[(0, 0), 'checkAP']) == [1., 0., 1., 0., 1., 0., 1.]
    assert list(df.loc[(0, 2), 'checkAP']) == [1., 0., 1., 0.]
    assert list(df.loc[(0, 0), 'a.check_1AP'].isna()) == [False, False, True, False, True, False, True]
    assert list(df.loc[(0, 2), 'a.check_1AP'].iloc[:3]) == [1., 1., 0.]
    assert np.isnan(df.loc[(0, 2, 3), 'a.check_1AP'])


def test_other_columns(consolidated):
    df = _load_all(consolidated[0])
    assert df.loc[(0, 2, 0), 'p_id'] == 7.
    assert df['p_id'].drop((0, 2, 0)).isna().all()
    assert list(df.loc[(0, 0), 'b.spikecount.raw'].isna()) == [False, False, True, False, True, False, True]


def test_array_columns_round_trip(consolidated):
    raw = _load_all(consolidated[0], columns=['a.raw', 'iteration', 'seedpoint_id', 'particle_id'])['a.raw']
    assert list(raw.loc[(0, 0, 0)]) == [0., 1.]
    assert raw.loc[(0, 0, 2)] is None
    assert raw.loc[(0, 2, 0)] is None
    assert raw.loc[(0, 2, 1)] is None
    assert isinstance(raw.loc[(0, 2, 2)], np.ndarray)
    assert len(raw.loc[(0, 2, 2)]) == 0
    assert raw.loc[(0, 2, 3)].dtype == np.float64
    assert list(raw.loc[(0, 2, 3)]) == [3., 4.]
    assert raw.loc[(1, 0)].isna().all()


def test_stored_index_is_dropped(exploration_dir, empty_db):
    chunk = pd.DataFrame([_evaluation(30, True), _evaluation(31, False)], index=pd.Index([7, 8], name='trial'))
    convert_all_check_columns_bool_to_float(chunk).to_parquet(os.path.join(exploration_dir, '1', '0', '13.parquet'))
    consolidate_exploration(exploration_dir, empty_db, 'rw')
    columns = load_exploration(empty_db, 'rw').columns
    assert 'trial' not in columns and 'index' not in columns and '__index_level_0__' not in columns
    assert list(_load_all(empty_db).loc[(1, 0), 'x']) == [20., 21., 30., 31.]


def test_columns_selection(consolidated):
    db, _ = consolidated
    ddf = load_exploration(db, 'rw', columns=['x', 'inside'])
    assert list(ddf.columns) == ['x', 'inside']
    assert list(ddf.compute().columns) == ['x', 'inside']
    assert list(db.get('rw_outside', columns=['obj']).compute()['obj']) == [x / 10 for x in OUTSIDE_X]


def test_db_getitem_returns_dask_dataframe(consolidated):
    ddf = consolidated[0]['rw_inside']
    assert ddf.npartitions == 2
    assert len(ddf) == 7


def test_existing_keys_require_overwrite(consolidated, exploration_dir):
    db, _ = consolidated
    with pytest.raises(KeyError, match='overwrite'):
        consolidate_exploration(exploration_dir, db, 'rw')
    _checkpoint(os.path.join(exploration_dir, '1'), 0, 14, [_evaluation(30, True)])
    summary = consolidate_exploration(exploration_dir, db, 'rw', overwrite=True)
    assert summary['n_rows'] == {'inside': 8, 'outside': 6}
    assert list(load_exploration(db, 'rw').compute()['x']) == INSIDE_X + [30.]
    assert sorted(db.keys()) == KEYS


def test_non_numeric_column_raises_without_writing(exploration_dir, empty_db):
    chunk = convert_all_check_columns_bool_to_float(pd.DataFrame([_evaluation(30, True)]))
    chunk['model_name'] = 'abc'
    chunk.to_parquet(os.path.join(exploration_dir, '1', '0', '13.parquet'))
    with pytest.raises(ValueError, match='model_name'):
        consolidate_exploration(exploration_dir, empty_db, 'rw')
    assert empty_db.keys() == ()


def test_non_bool_inside_raises_naming_the_file(exploration_dir, empty_db):
    path = os.path.join(exploration_dir, '1', '0', '13.parquet')
    pd.DataFrame([_evaluation(30, 'True'), _evaluation(31, 'False')]).to_parquet(path)
    with pytest.raises(ValueError, match=f"{path}: inside must be bool, found object values.*'True'"):
        consolidate_exploration(exploration_dir, empty_db, 'rw')
    assert empty_db.keys() == ()


@pytest.mark.parametrize('chunk', [
    pd.DataFrame({'x': [30., np.nan], 'inside': [True, None], 'init_error': ['', 'Could not read 7.pickle']}),
    pd.DataFrame({'init_error': ['Could not read 7.pickle']})])
def test_error_placeholder_rows_raise_naming_the_file(exploration_dir, empty_db, chunk):
    '''Old folds turned corrupt pickles into rows with only the error text in init_error, so without an inside value.'''
    path = os.path.join(exploration_dir, '1', '0', '13.parquet')
    chunk.to_parquet(path)
    with pytest.raises(ValueError, match=f'{path} has no inside column or rows without a valid inside value'):
        consolidate_exploration(exploration_dir, empty_db, 'rw')
    assert empty_db.keys() == ()


def test_pickles_raise_with_fold_instruction_before_creating_keys(exploration_dir, empty_db):
    _checkpoint(os.path.join(exploration_dir, '0'), 0, 8, [_evaluation(7, True)], fold=False)
    _checkpoint(os.path.join(exploration_dir, '1'), 0, 14, [_evaluation(30, True)], fold=False)
    seedpoint_0 = os.path.join(exploration_dir, '0')
    with pytest.raises(ValueError, match=(
            rf"2 particle folders contain \.pickle files.*concatenate_and_clean\('{seedpoint_0}', 0\)")):
        consolidate_exploration(exploration_dir, empty_db, 'rw')
    assert empty_db.keys() == ()
    concatenate_and_clean(seedpoint_0, 0)
    concatenate_and_clean(os.path.join(exploration_dir, '1'), 0)
    summary = consolidate_exploration(exploration_dir, empty_db, 'rw')
    assert summary['n_rows'] == {'inside': 9, 'outside': 6}


def test_subset_without_rows_loads_empty(tmp_path, empty_db):
    _checkpoint(str(tmp_path / '0'), 0, 2, [_evaluation(0, False), _evaluation(1, False)])
    summary = consolidate_exploration(str(tmp_path), empty_db, 'rw')
    assert summary['n_partitions'] == {'inside': 0, 'outside': 1}
    inside = load_exploration(empty_db, 'rw')
    assert len(inside.compute()) == 0
    assert list(inside.compute().columns) == list(load_exploration(empty_db, 'rw', subset='outside').columns)
    assert len(load_exploration(empty_db, 'rw', subset='outside').compute()) == 2


def test_with_distributed_client(exploration_dir, empty_db, client):
    summary = consolidate_exploration(exploration_dir, empty_db, 'rw', client=client)
    assert summary['n_rows'] == {'inside': 7, 'outside': 6}
    assert list(load_exploration(empty_db, 'rw').compute()['x']) == INSIDE_X


def test_failed_write_keeps_existing_keys(consolidated, exploration_dir):
    db, _ = consolidated
    chunk = convert_all_check_columns_bool_to_float(pd.DataFrame([_evaluation(30, True)]))
    chunk['a.check_1AP'] = 'maybe'
    chunk.to_parquet(os.path.join(exploration_dir, '1', '0', '13.parquet'))
    with pytest.raises(ValueError, match='Could not convert column a.check_1AP'):
        consolidate_exploration(exploration_dir, db, 'rw', overwrite=True)
    assert sorted(db.keys()) == KEYS
    assert list(load_exploration(db, 'rw').compute()['x']) == INSIDE_X
    assert os.path.exists(os.path.join(db['rw_errors'], 'errors.json'))


def test_failed_write_leaves_no_key(exploration_dir, empty_db):
    chunk = convert_all_check_columns_bool_to_float(pd.DataFrame([_evaluation(30, True)]))
    chunk['a.check_1AP'] = 'maybe'
    chunk.to_parquet(os.path.join(exploration_dir, '1', '0', '13.parquet'))
    with pytest.raises(ValueError, match='Could not convert'):
        consolidate_exploration(exploration_dir, empty_db, 'rw')
    assert empty_db.keys() == ()


def test_failed_key_replacement_keeps_staging_key(consolidated, exploration_dir, monkeypatch):
    db, _ = consolidated
    rename = os.rename

    def fail_on_moving_in_outside(source, target):
        if os.path.basename(str(source)) == 'outside':
            raise OSError('rename failed')
        rename(source, target)

    monkeypatch.setattr(os, 'rename', fail_on_moving_in_outside)
    with pytest.raises(RuntimeError, match=r"Could not replace key rw_outside\. The staging key rw_consolidating_\w+ is kept.*"
                                           r"\['rw_outside', 'rw_errors'\]") as error:
        consolidate_exploration(exploration_dir, db, 'rw', overwrite=True)
    assert isinstance(error.value.__cause__, OSError)
    staging_key = [k for k in db.keys() if k.startswith('rw_consolidating_')]
    assert sorted(db.keys()) == sorted(['rw_errors', 'rw_inside'] + staging_key)
    assert staging_key[0] in str(error.value)
    assert {'errors', 'outside'} <= set(os.listdir(db[staging_key[0]]))
    assert 'inside' not in os.listdir(db[staging_key[0]])


def test_successful_overwrite_leaves_no_staging_key(consolidated, exploration_dir):
    db, _ = consolidated
    consolidate_exploration(exploration_dir, db, 'rw', overwrite=True)
    assert sorted(db.keys()) == KEYS


def test_readonly_db_raises_without_scanning(exploration_dir, empty_db):
    from data_base.isf_data_base import ISFDataBase
    readonly_db = ISFDataBase(str(empty_db._basedir), readonly=True)
    with pytest.raises(Exception, match='readonly'):
        consolidate_exploration(exploration_dir, readonly_db, 'rw')
    assert empty_db.keys() == ()
