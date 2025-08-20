import hashlib
import pandas as pd
import dask.dataframe as dd
from .config import (
    OPTIMIZED_CATEGORIZED_DASK_DUMPER,
    OPTIMIZED_DASK_DUMPER,
    OPTIMIZED_PANDAS_DUMPER
)

def _hash_file_content(fn):
    with open(fn, 'rb') as content:
        h = hashlib.md5(content.read()).hexdigest()
    return h


def _get_dumper(value, categorized=False):
    """Infer the best dumper for a dataframe.

    Infers the correct parquet dumper for either a pandas or dask dataframe.

    Args:
        value (pd.DataFrame or dd.DataFrame): Dataframe to infer the dumper for.

    Returns:
        module: Dumper module to use for the dataframe.

    Raises:
        NotImplementedError: If the dataframe is not a pandas or dask dataframe.
    """
    if isinstance(value, pd.DataFrame):
        return OPTIMIZED_PANDAS_DUMPER
    elif isinstance(value, dd.DataFrame):
        if categorized:
            return OPTIMIZED_CATEGORIZED_DASK_DUMPER
        else:
            return OPTIMIZED_DASK_DUMPER
    else:
        raise NotImplementedError(
            "Dataframe type not supported: {}.\nOnly the following dataframe types are supported: {}".format(
                type(value), [pd.DataFrame , dd.DataFrame]
                ))

        
def convert_df_columns_to_str(df):
    """Convenience method to convert all columns of a dataframe to strings.

    :skip-doc:
    """
    df = df.rename(
        columns={col: "{}".format(col) for col in df.columns if type(col) != str}
    )
    return df
