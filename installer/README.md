# Installation
ISF requires `gcc` and `git` to be installed.

To install ISF on UNIX systems using the interactive installer, simply run:
```bash
./installer/install.sh
```

The installation will:
1. Download Anaconda for Python 2.7/3.8/3.9
2. Download and install conda dependencies
3. Download and install PyPI dependencies
4. Install `pandas-msgpack`
4. Patch `pandas-msgpack` (only for Py3.x) or `pandas` to support `CategoricalIndex` (only for Py2.7)
5. Install a corresponding ipykernel for notebooks
6. Compile all mechanisms in the [mechanisms](../mechanisms/) directory using `nrnivmodl`.

Tested on: 
| OS | `gcc` version | `git` version |
| -------- | -------- | -------- |
| `CentOS 7.9.2009`    | 4.8.5   | 2.31   |
| `Ubuntu 18.04.02 LTS`   | 7.5.0   | 2.42.0   |


<details>
  <summary>The output should look something like this (click to expand)</summary>
    
    ```bash
    >>> [user@localhost py3.8] ./installer/install.sh

    Enter the directory in which the Anaconda environment should be installed: some-absolute-path/anaconda_isf3.8

    0/6. Preliminary checks ----------------------------------------------------------------------------
    Found Anaconda installer in installer/downloads
    No conda packages found in downloads/conda_packages. They will be downloaded.
    Warning: found PyPI packages in downloads/pip_packages. They will not be redownloaded. If you have changed the pip_requirements.txt file, you should remove this folder or its contents before attemtping a reinstall.

    1/6. Installing Anaconda ---------------------------------------------------------------------------

    Anaconda will be installed in: some-absolute-path/anaconda_isf3.8
    PREFIX=some-absolute-path/anaconda_isf3.8
    Unpacking payload ...
    Collecting package metadata (current_repodata.json): done                                                                                                                                                                       
    Solving environment: done

    ## Package Plan ##

    environment location: /gpfs/soma_fs/scratch/meulemeester/test

    added / updated specs:
    ...

    2/6. Installing conda dependencies -----------------------------------------------------------------

    No conda packages to download.
    Installing In-Silico-Framework conda dependencies.
    Preparing transaction: ...working... done
    Verifying transaction: ...working... done
    Executing transaction: ...working... done

    3/6. Installing PyPI dependencies ------------------------------------------------------------------

    Installing In-Silico-Framework pip dependencies.
    Looking in links: /gpfs/soma_fs/scratch/meulemeester/project_src/in_silico_framework/installer/py3.8/downloads/pip_packages
    ...

    4/6. Installing & patching pandas-msgpack ----------------------------------------------------------
    ...

    5/6. Installing the ipykernel ----------------------------------------------------------------------

    Installed kernelspec base in /gpfs/soma_fs/home/meulemeester/.local/share/jupyter/kernels/base

    6/6. Compiling NEURON mechanisms -------------------------------------------------------------------

    Compiling NEURON mechanisms.
    ...

    Succesfully installed In-Silico-Framework for Python 3.8
    ```

</details>

## Additional installation configuration
It is possible to have an installation that includes nodejs for the Python 3.8 version. The interactive installer will prompt you.

## Non-interactive installation
To avoid interaction with the installer (for automated installation e.g.), you can also directly invoke the installer script that corresponds to the Python version you want to install:
```bash
./installer/py2.7/install.sh -p <installation_directory>
./installer/py3.8/install.sh -p <isntallation_directory> [--node]
./installer/py3.9/install.sh -p <installation_directory>
```