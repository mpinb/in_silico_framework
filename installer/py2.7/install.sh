#!/bin/bash
#
# This script can be used to install in-silico-framework (ISF) for Python 3.9
# 1. downloads & installs anaconda, creates a corresponding environment
# 2. Downloads & installs all conda and pip dependencies for this environment
# 3. Patches pandas-msgpack and saves it as a local package
# 4. Compiles NEURON mechanisms

set -e  # exit if error occurs

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
anaconda_installer=Anaconda2-4.2.0-Linux-x86_64.sh
channels=$SCRIPT_DIR/../../mechanisms/channels_py2
netcon=$SCRIPT_DIR/../../mechanisms/netcon_py2

function print_title {
    local str=$1
    local pad_char="-"
    local width="$(tput cols)"
    local string_length=${#string}
    local padding=$(($width - $string_length-1))  # to clean out previous long strings
    echo ""
    echo $str $(printf -- $pad_char%.s $(seq -s ' ' $(($padding-${#str}))))
    echo ""
}

usage() {
    cat << EOF
Usage: ./isf-install.sh [-p <conda-install-path>]

    -h                          Display help
    -p <conda-install-path>     The path where conda will be installed.
EOF
}

# ---------- Read command line options ----------#
CONDA_INSTALL_PATH=${1:-""}  # default is unset ("")
# If still unset (i.e. not given on cmdline): ask user
echo $CONDA_INSTALL_PATH
while [ -z $CONDA_INSTALL_PATH ]; do
    read -p "Enter the directory in which the Anaconda environment should be installed: " CONDA_INSTALL_PATH
done

# -------------------- 0. Setup -------------------- #
print_title "0/5. Preliminary checks"
# 0.0 -- Create downloads folder (if it does not exist)
if [ ! -d "$SCRIPT_DIR/downloads" ]; then
    mkdir $SCRIPT_DIR/downloads;
fi

# 0.1 -- Check 1: Is Anaconda already downloaded?
if [ -e "$SCRIPT_DIR/downloads/$anaconda_installer" ]; then
    echo "Found Anaconda installer in $SCRIPT_DIR/downloads"
    download_conda_flag="false"
else
    echo "No Anaconda installer found in $SCRIPT_DIR/downloads. It will be downloaded."
    download_conda_flag="true"
fi

# 0.2 -- Check 2: Are the conda packages already downloaded?
if [ ! -d "$SCRIPT_DIR/downloads/conda_packages" ]; then
    echo "No conda_packages directory found in downloads. Created one to download conda packages in."
    mkdir $SCRIPT_DIR/downloads/conda_packages # conda packages download directory
    download_conda_packages_flag="true"
elif [ ! "$(ls -A $SCRIPT_DIR/downloads/conda_packages)" ]; then
    echo "No conda packages found in downloads/conda_packages. They will be downloaded."
    download_conda_packages_flag="true"
else
    echo "Found conda packages in downloads/conda_packages. They will not be downloaded"
    download_conda_packages_flag="false"
fi

# 0.3 -- Check 3: Are the pip packages already downloaded?
if [ ! -d "$SCRIPT_DIR/downloads/pip_packages" ]; then
    echo "No pip_packages directory found in downloads. Created one to download PyPI packages in."
    mkdir $SCRIPT_DIR/downloads/pip_packages  # pip packages download directory
    download_pip_packages_flag="true"
elif [ ! "$(ls -A $SCRIPT_DIR/downloads/pip_packages)" ]; then
    echo "No PyPI packages found in downloads/pip_packages. They will be downloaded."
    download_pip_packages_flag="true"
else
    echo "Found PyPI packages in downloads/pip_packages. They will not be downloaded."
    download_pip_packages_flag="false"
fi

# 0.4 -- Check 4: Are there any downloads necessary?
if [[ "${download_conda_flag}" == "false" && "${download_conda_packages_flag}" == "false" && "${download_pip_packages_flag}" == "false" ]]; then
    echo "No downloads necessary."
fi

# -------------------- 1. Installing Anaconda -------------------- #
print_title "1/5. Installing Anaconda"
# 1.0 -- Downloading Anaconda (if necessary).
if [[ "${download_conda_flag}" == "true" ]]; then
    echo "Downloading ${anaconda_installer}"
    wget https://repo.anaconda.com/archive/${anaconda_installer} -N --quiet -P $SCRIPT_DIR/downloads;
fi
# 1.1 -- Installing Anaconda
echo "Anaconda will be installed in: ${CONDA_INSTALL_PATH}"
bash $SCRIPT_DIR/downloads/${anaconda_installer} -b -p ${CONDA_INSTALL_PATH};
echo "Activating environment by running \"source ${CONDA_INSTALL_PATH}/bin/activate\""
source ${CONDA_INSTALL_PATH}/bin/activate
conda info

# -------------------- 2. Downloading conda dependencies -------------------- #
print_title "2/5. Installing conda dependencies "
# 2.0 -- Downloading In-Silico-Framework conda dependencies (if necessary).
if [ "${download_conda_packages_flag}" == "true" ]; then
    echo "Downloading In-Silico-Framework conda dependencies."
    cat $SCRIPT_DIR/conda_requirements.txt | grep '^http' | xargs -t -n 1 -P 8 wget -N -q -P $SCRIPT_DIR/downloads/conda_packages
    echo "Download conda packages completed."
fi
# 2.1 -- Installing In-Silico-Framework conda dependencies.
echo "Installing In-Silico-Framework conda dependencies."
sed "s|https://.*/|$SCRIPT_DIR/downloads/conda_packages/|" $SCRIPT_DIR/conda_requirements.txt > $SCRIPT_DIR/tempfile
conda update --file $SCRIPT_DIR/tempfile --quiet

# -------------------- 3. Installing PyPI dependencies -------------------- #
print_title "3/5. Installing PyPI dependencies"
# 3.0 -- Downloading In-Silico-Framework pip dependencies (if necessary).
if [ "${download_pip_packages_flag}" == "true" ]; then
    echo "Downloading In-Silico-Framework pip dependencies."
    python -m pip --no-cache-dir download --no-deps -r $SCRIPT_DIR/pip_requirements.txt -d $SCRIPT_DIR/downloads/pip_packages
    echo "Download pip packages completed."
fi
# 3.1 -- Installing In-Silico-Framework pip dependencies.
echo "Installing In-Silico-Framework pip dependencies."
python -m pip --no-cache-dir install --no-deps -r $SCRIPT_DIR/pip_requirements.txt --no-index --find-links $SCRIPT_DIR/downloads/pip_packages

# -------------------- 4. Patching pandas library -------------------- #
print_title "4/5. Patch pandas to support CategoricalIndex"
python $SCRIPT_DIR/patch_pandas_linux64.py

# -------------------- 5. Compiling NEURON mechanisms -------------------- #
print_title "5/5. Compiling NEURON mechanisms"
echo "Compiling NEURON mechanisms."
cd $channels; nrnivmodl
cd $netcon; nrnivmodl

# -------------------- Cleanup -------------------- #
echo "Succesfully installed In-Silico-Framework for Python 2.7."
rm $SCRIPT_DIR/tempfile
exit 0