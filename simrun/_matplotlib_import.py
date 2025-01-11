""":skip-doc:"""
import warnings
try:
    import matplotlib
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        matplotlib.use('Agg')
except ImportError:
    pass
