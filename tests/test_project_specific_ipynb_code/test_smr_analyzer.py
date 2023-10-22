from simrun2 import generate_synapse_activations
import dask
from .context import cellParamName, networkName


def test_generate_synapse_activation_returns_filelist(tmpdir):
    dirPrefix = tmpdir.dirname
    try:
        dummy = generate_synapse_activations.generate_synapse_activations(
            cellParamName,
            networkName,
            dirPrefix=dirPrefix,
            nSweeps=1,
            nprocs=1,
            tStop=345,
            silent=True)
        dummy = dummy.compute(get=dask.get)
    except:
        raise
    assert isinstance(dummy[0][0][0], str)
