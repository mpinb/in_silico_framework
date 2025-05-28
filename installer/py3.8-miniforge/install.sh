#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source $SCRIPT_DIR/utils.sh
# After this, the following variables/functions exist:
# Variables:
# - download_conda_flag
# - download_conda_packages_flag
# - download_pip_packages_flag
# - WOKRING_DIR
# - SCRIPT_DIR
# Functions:
# - print_title
# - usage
# - check_downloads
# - set_cli_args
# - check_prerequisites
# - setup_conda_in_shell
# - find_and_compile_mechanisms
# - patch_pandas_msgpack

# Global variables
echo "Script directory: ${SCRIPT_DIR}"
INSTALL_PATH=""
INSTALL_NODE=false
MINIFORGE="Miniforge3-$(uname)-$(uname -m).sh"
ENV_NAME="isf38"

# ---------- Read command line options ----------#
set_cli_args "$@"
INSTALL_PATH=$(realpath "$INSTALL_PATH")

# -------------------- 0. Setup -------------------- #
check_prerequisites
check_install_path $INSTALL_PATH
local_downloads_dir="$SCRIPT_DIR/downloads"
check_downloads $local_downloads_dir

# -------------------- 1. Installing Miniforge conda & mamba -------------------- #
print_title "1/5. Installing MiniForge conda & mamba"

# -- Downloading miniforge (if necessary).
if [[ "${download_conda_flag}" == "true" ]]; then
    wget "https://github.com/conda-forge/miniforge/releases/latest/download/$MINIFORGE" -N --quiet -P $SCRIPT_DIR/downloads
fi

# -- Installing miniforge
echo "Miniforge will be installed in: ${INSTALL_PATH}"
bash $MINIFORGE -b -p ${INSTALL_PATH}
# setup conda in current shell; avoid having to restart shell
setup_conda_in_shell ${INSTALL_PATH}

# init conda and mamba in current shell
source ${INSTALL_PATH}/etc/profile.d/conda.sh
source ${INSTALL_PATH}/etc/profile.d/mamba.sh 

echo "Creating environment $ENV_NAME"
# activate base env
source ${INSTALL_PATH}/bin/activate base


# -------------------- 2. Creating ISF environment -------------------- #
print_title "2/5. Creating ISF environment"

# create new env from base
mamba create -n $ENV_NAME -y python=3.8.5
mamba activate $ENV_NAME

# -- conda dependencies (if necessary).
if [ "${download_conda_packages_flag}" == "true" ]; then
    # Get all lines starting with http (not #http), return empty string if there are none
    package_list=$(cat $SCRIPT_DIR/miniforge_requirements.txt | grep '^http' || echo "")
    if [ -z "$package_list" ]; then
        echo "No conda packages to download."
    else
        echo "Downloading In-Silico-Framework conda dependencies."
        echo $package_list | xargs -t -n 1 -P 8 wget -N -q -P $SCRIPT_DIR/downloads/conda_packages || exit 1
        echo "Download conda packages completed."
    fi
fi

echo "Installing In-Silico-Framework conda dependencies."
sed "s|https://.*/|$SCRIPT_DIR/downloads/conda_packages/|" $SCRIPT_DIR/miniforge_requirements.txt > $SCRIPT_DIR/tempfile
mamba update --file $SCRIPT_DIR/tempfile --quiet
mamba info

# -- Installing nodejs if necessary
if [ "$INSTALL_NODE" = true ]; then
    echo "Installing nodejs"
    mamba install -y nodejs -c conda-forge --repodata-fn=repodata.json
fi

# -- pip dependencies (if necessary).
if [ "${download_pip_packages_flag}" == "true" ]; then
    echo "Downloading In-Silico-Framework pip dependencies."
    python -m pip --no-cache-dir download --no-deps -r $SCRIPT_DIR/pip_requirements.txt -d $SCRIPT_DIR/downloads/pip_packages
    echo "Download pip packages completed."
fi
echo "Installing In-Silico-Framework pip dependencies."
python -m pip --no-cache-dir install --no-deps -r $SCRIPT_DIR/pip_requirements.txt --no-index --find-links $SCRIPT_DIR/downloads/pip_packages

# -------------------- 4. Patching pandas-msgpack -------------------- #
print_title "3/5. Installing & patching pandas-msgpack"
pip install cython==0.29.21  
patch_pandas_msgpack $SCRIPT_DIR

# -------------------- 5. installing the ipykernel -------------------- #
print_title "4/5. Installing the ipykernel"
python -m ipykernel install --name base --user --display-name $ENV_NAME

# -------------------- 6. Compiling NEURON mechanisms -------------------- #
print_title "5/5. Compiling NEURON mechanisms"
echo "Compiling NEURON mechanisms."
find_and_compile_mechanisms $SCRIPT_DIR $python_version_glob


# -------------------- 7. Generating paramfiles -------------------- #
print_title "7. Generating paramfiles"
python $SCRIPT_DIR/../activation_hook.py