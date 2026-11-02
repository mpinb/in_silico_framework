# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
This module provides routines to analyze the results of a random walk exploration through biophysical parameter space.

See also:
    :mod:`~biophysics_fitting.exploration_from_seedpoint.RW`
"""

import json
import logging
import os
import uuid
from pathlib import Path

import dask
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from data_base.IO.LoaderDumper import dask_to_parquet, just_create_folder

logger = logging.getLogger("ISF").getChild(__name__)

_EXPLORATION_SUBSETS = ('inside', 'outside')
_GENERATED_COLUMNS = ('iteration', 'particle_id', 'seedpoint_id')
_INDEX_FIELD = pa.field('__index_level_0__', pa.int64())
_COMPRESSION = 'zstd'

def _scan_particle(particle_dir):
    """Count the inside and outside rows of the readable parquet files of a particle and collect their columns.

    Only the footer and the ``inside`` column are read.

    Raises:
        ValueError: if the ``inside`` column of a file is missing, not bool or has missing values.
    """
    scan = {'paths': [], 'n_rows': dict.fromkeys(_EXPLORATION_SUBSETS, 0), 'columns': {}, 'array_columns': set(),
            'unreadable_files': []}
    names = [n for n in os.listdir(particle_dir) if n.endswith('.parquet')]
    for name in sorted(names, key=lambda n: int(n.split('.')[0])): # the files are named <iteration>.extension, so sort by iteration
        path = os.path.join(particle_dir, name)
        try:
            schema = pq.read_schema(path)
            columns = schema.empty_table().to_pandas().columns
            inside = pq.read_table(path, columns=['inside'] if 'inside' in columns else []).to_pandas().get('inside')
        except Exception as e:
            logger.warning(f'Could not read {path}: {e!r}')
            scan['unreadable_files'].append({'path': path, 'error': repr(e)})
            continue
        if inside is None or inside.isna().any():
            raise ValueError(f'{path} has no inside column or rows without a valid inside value '
                             f'(error placeholder rows from an old fold of corrupt pickles?)')
        if inside.dtype != bool:
            raise ValueError(f'{path}: inside must be bool, found {inside.dtype} values {list(inside.unique()[:5])}')
        n_inside = int(inside.sum())
        scan['paths'].append(path)
        scan['n_rows']['inside'] += n_inside
        scan['n_rows']['outside'] += len(inside) - n_inside
        scan['columns'].update(dict.fromkeys(columns))
        scan['array_columns'] |= {field.name for field in schema if pa.types.is_list(field.type)}
    return scan


def _build_exploration_schema(scans):
    """Build one parquet schema for all partitions: the union of the chunk columns, the generated columns and the index."""
    columns = dict.fromkeys([c for scan in scans for c in scan['columns'] if c != 'init_error'] + list(_GENERATED_COLUMNS))
    array_columns = set().union(*(scan['array_columns'] for scan in scans))
    # Fix array columns to list<double>: pyarrow otherwise infers the type per file (list<int64>, or null
    # for all-None columns), and files of one key then cannot be read as one dataset.
    fields = [
        pa.field(c, pa.bool_() if c == 'inside' else pa.int64() if c in _GENERATED_COLUMNS
                 else pa.list_(pa.float64()) if c in array_columns else pa.float64())
        for c in columns]
    return pa.schema(fields + [_INDEX_FIELD])

def _read_particle_subset(paths, seedpoint_id, particle_id, schema, subset, first_index, n_rows):
    """Read the inside or outside rows of the parquet files of a particle, converted to ``schema``.

    Args:
        subset (str): ``'inside'`` or ``'outside'``.
        first_index (int): index of the first row of this particle in ``subset``.
        n_rows (int): number of rows of this particle in ``subset`` according to the scan.

    Raises:
        ValueError: if a column cannot be converted to its type in ``schema``.
        RuntimeError: if the number of rows differs from ``n_rows``.
    """
    chunks, n_rows_read = [], 0
    for path in paths:
        table = pq.read_table(path)
        in_subset = table['inside'].to_numpy() == (subset == 'inside')
        df = table.filter(in_subset).to_pandas().reset_index(drop=True)
        df['iteration'] = n_rows_read + np.flatnonzero(in_subset)
        df['particle_id'], df['seedpoint_id'] = particle_id, seedpoint_id
        n_rows_read += table.num_rows
        if not len(df):
            continue
        columns = {}
        for field in list(schema)[:-1]:
            values = df[field.name] if field.name in df else pd.Series(np.nan, index=df.index)
            try:
                columns[field.name] = (
                    values.map(lambda v: np.asarray(v, dtype='float64') if isinstance(v, np.ndarray) else None)
                    if pa.types.is_list(field.type) else values.astype(field.type.to_pandas_dtype()))
            except (ValueError, TypeError) as e:
                raise ValueError(f'Could not convert column {field.name} of {path} to {field.type}: {e}') from e
        chunks.append(pd.DataFrame(columns))
    if sum(map(len, chunks)) != n_rows:
        raise RuntimeError(f'The number of {subset} rows of {os.path.dirname(paths[0])} changed since the exploration '
                           f'was scanned')
    df = pd.concat(chunks, ignore_index=True)
    # Not a RangeIndex: pyarrow writes a RangeIndex as metadata only, which a fixed schema drops.
    df.index = pd.Index(np.arange(first_index, first_index + n_rows))
    return df


def consolidate_exploration(exploration_dir, db, key, client=None, overwrite=False):
    """Convert the parquet results of a RW exploration into the parquet keys ``<key>_inside`` and ``<key>_outside`` of a
    database.

    Each particle becomes one partition of each key it has rows in. All partitions share one schema: ``inside`` is bool,
    ``iteration``, ``particle_id`` and ``seedpoint_id`` are int64, array-valued columns are ``list<double>`` (non-array
    cells, e.g. the stored means in the first row of a resumed particle, become None), and all other columns are
    float64 (NaN where a column is missing in a file). ``init_error`` and the stored index are dropped. ``iteration``
    counts the rows of a particle over its readable files, and ``seedpoint_id`` and ``particle_id`` are taken from the
    folder names.

    Unreadable files and particles without files are recorded in
    ``errors.json`` in the managed folder ``db['<key>_errors']``. All three keys are written to a staging key
    ``<key>_consolidating_<id>`` first and only replace existing keys once complete, so a failure while reading or
    writing leaves existing keys untouched and removes the staging key. If replacing an existing key fails, that key
    may be deleted already, and the staging key is kept, as it holds the new data of the keys not yet replaced. If the
    process is killed, the staging key can be left behind.

    Args:
        exploration_dir (str): directory containing ``<seedpoint_id>/<particle_id>/<N>.parquet`` files.
        db (ISFDataBase): database to write the keys to.
        key (str): prefix of the keys.
        client (distributed.Client, optional): client to run the tasks on. Default: the dask default scheduler.
        overwrite (bool): whether to replace existing keys.

    Returns:
        dict: ``n_rows`` and ``n_partitions`` per subset, ``n_particles``, and the contents of ``errors.json``:
        ``particles_without_files`` and ``unreadable_files``.

    Raises:
        KeyError: if a key exists and not ``overwrite``.
        ValueError: if a particle folder contains ``.pickle`` files, which must be folded into parquet first with
            :py:func:`~biophysics_fitting.exploration_from_seedpoint.RW.concatenate_and_clean`, or if a file has no
            valid bool ``inside`` column.
        RuntimeError: if replacing an existing key fails.
    """
    keys = {name: f'{key}_{name}' for name in (*_EXPLORATION_SUBSETS, 'errors')}
    existing_keys = [k for k in keys.values() if db.check_if_key_exists(k)]
    if existing_keys and not overwrite:
        raise KeyError(f'Keys {existing_keys} already exist. Pass overwrite=True to replace them.')
    particles = [
        (int(seedpoint_id), int(particle_id))
        for seedpoint_id in sorted(filter(str.isdigit, os.listdir(exploration_dir)), key=int)
        for particle_id in sorted(filter(str.isdigit, os.listdir(os.path.join(exploration_dir, seedpoint_id))), key=int)]
    particle_dirs = [os.path.join(exploration_dir, str(s), str(p)) for s, p in particles]
    with_pickles = [d for d in particle_dirs if any(n.endswith('.pickle') for n in os.listdir(d))]
    if with_pickles:
        raise ValueError(
            f'{len(with_pickles)} particle folders contain .pickle files, e.g. {with_pickles[:3]}. Only parquet files '
            f'are converted. Once their walks have finished, fold each of them into parquet with '
            f'biophysics_fitting.exploration_from_seedpoint.RW.concatenate_and_clean(<seedpoint folder>, <particle id>), '
            f'e.g. concatenate_and_clean({os.path.dirname(with_pickles[0])!r}, {os.path.basename(with_pickles[0])})')
    staging_key = f'{key}_consolidating_{uuid.uuid4().hex[:8]}'
    staging_dir = Path(db.create_managed_folder(staging_key))
    staged_dirs = {name: staging_dir / name for name in keys}
    try:
        # Two passes, as every partition must have the same schema before we start writing
        # which columns hold arrays (if some files might only have NaN for certain columns while the others have arrays) 
        # and the row index for divisions needs to know the length the inside and outside data of each particle.
        all_scans = dask.compute(*[dask.delayed(_scan_particle)(d) for d in particle_dirs], scheduler=client)
        schema = _build_exploration_schema(all_scans)
        scans = [(particle, scan) for particle, scan in zip(particles, all_scans) if scan['paths']]

        meta = schema.empty_table().to_pandas().set_index(_INDEX_FIELD.name).rename_axis(None)
        shared_schema = dask.delayed(schema)
        n_rows, n_partitions = {}, {}
        for subset in _EXPLORATION_SUBSETS:
            counts = [scan['n_rows'][subset] for _, scan in scans]
            first_index = np.cumsum([0] + counts).tolist()
            with_rows = [i for i, n in enumerate(counts) if n]
            partitions = [
                dask.delayed(_read_particle_subset)(
                    scans[i][1]['paths'], *scans[i][0], shared_schema, subset, first_index[i], counts[i])
                for i in with_rows]
            ddf = dask.dataframe.from_delayed(
                partitions or [dask.delayed(meta)], meta=meta,
                divisions=[first_index[i] for i in with_rows] + [first_index[-1] - 1] if with_rows else None)
            staged_dirs[subset].mkdir()
            dask_to_parquet.dump(ddf, str(staged_dirs[subset]), schema=schema, client=client, repartition=False,
                                 compression=_COMPRESSION)
            db._write_metadata(dask_to_parquet, staged_dirs[subset])
            n_rows[subset], n_partitions[subset] = first_index[-1], len(with_rows)

        errors = {
            'particles_without_files': [
                list(p) for p, scan in zip(particles, all_scans) if not scan['paths'] and not scan['unreadable_files']],
            'unreadable_files': [error for scan in all_scans for error in scan['unreadable_files']]}
        staged_dirs['errors'].mkdir()
        just_create_folder.dump(None, str(staged_dirs['errors']))
        db._write_metadata(just_create_folder, staged_dirs['errors'])
        with open(staged_dirs['errors'] / 'errors.json', 'w') as f:
            json.dump(errors, f, indent=1)
    except BaseException:
        del db[staging_key]
        raise
    for name, staged_dir in staged_dirs.items():
        try:
            if db.check_if_key_exists(keys[name]):
                del db[keys[name]]
            os.rename(staged_dir, db._convert_key_to_path(keys[name]))
        except Exception as e:
            raise RuntimeError(
                f'Could not replace key {keys[name]}. The staging key {staging_key} is kept: it holds the new data of '
                f'the keys not yet replaced, {[keys[n] for n in staged_dirs if (staging_dir / n).exists()]}') from e
    del db[staging_key]
    return {
        'n_rows': n_rows, 'n_partitions': n_partitions, 'n_particles': len(particles), **errors}


def load_exploration(db, key, subset='inside', columns=None):
    """Load the inside or outside rows of a RW exploration converted with :py:func:`consolidate_exploration`.

    Args:
        db (ISFDataBase): the database in which the exploration was stored.
        key (str): the key under which the exploration was stored.
        subset (str): ``'inside'`` or ``'outside'``. The inside rows are usually those with errors below all thresholds for the objectives.
        columns (list, optional): the columns to load. Default: None (all columns).

    Returns:
        dask.dataframe.DataFrame: one partition per particle with rows in that subset, with a RangeIndex over all
        partitions and known divisions. Array-valued columns (e.g. ``*.raw`` per-spike values) are stored as
        parquet ``list<double>`` and load as object columns holding float64 arrays or ``None``. Select them
        with ``columns=`` only when needed, as they are much larger than scalar columns.
    """
    if subset not in _EXPLORATION_SUBSETS:
        raise ValueError(f'subset must be one of {_EXPLORATION_SUBSETS}, not {subset}')
    return db.get(f'{key}_{subset}', columns=columns)


# analysis functions
def normalize(df, params):
    """Normalize a pd.DataFrame according to the values of specified parameters.
    
    Args:
        df (pd.DataFrame): the dataframe to normalize
        params (pd.DataFrame): a dataframe containing the min and max values for each parameter
        
    Returns:
        pd.DataFrame: the normalized dataframe"""
    return (df-params['min'])/(params['max'] - params['min'])

idx = pd.IndexSlice

def get_param_range_evolution_from_df(df, params, iteration_group_size = 20, return_min_max = False):
    """Compute the cumulative range of each parameter explored by a RW exploration, as a fraction of its total range.

    Successful iterations differ between particles, so iterations are pooled into groups of
    ``iteration_group_size`` before taking the running min and max across all particles.

    Args:
        df (pd.DataFrame): the exploration results of successful iterations, containing the parameter columns and an ``iteration`` column.
        params (pd.DataFrame): the parameter ranges, with columns ``min`` and ``max`` and the parameter names as index.
        iteration_group_size (int): the number of consecutive iterations pooled into one group.
        return_min_max (bool): whether to return the normalized running max and min separately, rather than their difference.

    Returns:
        pd.DataFrame | (pd.DataFrame, pd.DataFrame): the explored range per parameter (columns) and iteration group (index).
        If ``return_min_max`` is True, the normalized running max and min instead."""
    param_names = list(params.index)
    df = df[param_names + ['iteration']].copy()
    df['iteration'] = (df.iteration // iteration_group_size) * iteration_group_size
    df_ranges = df.groupby('iteration').agg(['max', 'min'])
    df_min = normalize(df_ranges.loc[:, idx[:, 'min']].droplevel(1, axis=1).cummin(), params)
    df_max = normalize(df_ranges.loc[:, idx[:, 'max']].droplevel(1, axis=1).cummax(), params)
    if return_min_max:
        return df_max, df_min
    return df_max - df_min