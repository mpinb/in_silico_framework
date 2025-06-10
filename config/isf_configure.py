"""
Configure ISF for your local system.

This script is intended to be run once after installing ISF.
It generates parameter files with resolved filepaths for your filesystem.
In addition, it compiles the L5PT mechanisms if not already compiled, 
and loads them into NEURON namespace.

Configuring ISF using the pixi installation can be done with::

    pixi r configure <force_recompile> <overwrite_param_files>

This `pixi` command has positional boolean arguments: `force_recompile` and `overwrite_param_files`.
Make sure their value maps to a Python-interpretable boolean, such as `1`, `True`, `0` and `False`.

Example::

    pixi r configure 1 0          # force recompile, don't overwrite existing parameter files
    pixi r configure False True   # don't force recompile, overwrite existing parameter files
    pixi r configure  # (default) don't force recompile or overwrite existing parameter files

Alternatively, this script can also be run directly from the command line using::

    python -m config.isf_configure --force-recompile=True/False --overwrite-param-files=True/False
    
Make sure you run this from within the ISF environment, so Python can find the ISF packages and dependencies.

See also:
    :py:func:`getting_started.generate_param_files_with_valid_references`
    
See also:
    :py:func:`mechanisms.l5pt.compile_l5pt_mechanisms`
"""
import argparse

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Configure ISF for your local system.")
    parser.add_argument(
        "--force-recompile",
        help="Force recompile L5PT mechanisms and regenerate even if they are already compiled.",
    )
    parser.add_argument(
        "--overwrite-param-files",
        help="Skip generating parameter files with valid references.",
    )   
    args = parser.parse_args()
    force_recompile = False if args.force_recompile.lower() in ["none", "false", "0"] else True
    overwrite_param_files = False if args.overwrite_param_files.lower() in ["none", "false", "0"] else True

    from getting_started import generate_param_files_with_valid_references
    from mechanisms.l5pt import compile_mechanisms
    compile_mechanisms(force_recompile=force_recompile)
    generate_param_files_with_valid_references(overwrite_param_files=overwrite_param_files)