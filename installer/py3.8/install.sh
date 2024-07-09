#!/bin/bash
#
# This script can be used to install in-silico-framework (ISF) for Python 3.9
# 1. downloads & installs anaconda, creates a corresponding environment
# 2. Downloads & installs all conda and pip dependencies for this environment
# 3. Patches pandas-msgpack and saves it as a local package
# 4. Compiles NEURON mechanisms

set -eE
set -o pipefail

# Check if git is available
if ! command -v git &> /dev/null; then
    echo "git could not be found. Please install git."
    exit 1
fi

# Check if gcc is available
if ! command -v gcc &> /dev/null; then
    echo "gcc could not be found. Please install gcc."
    exit 1
fi

pushd . # save this dir on stack

# Global variables
WORKING_DIR=$(pwd)
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
echo "Script directory: $SCRIPT_DIR"
anaconda_installer=Anaconda3-2020.11-Linux-x86_64.sh
CONDA_INSTALL_PATH=""
INSTALL_NODE=false

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

function usage {
    cat << EOF
Usage: install [-p|--path <conda-install-path>] [--node]

    -h | --help     Display help
    -p | --path     The path where the conda environment conda will be installed.
    --node 			Install nodejs along with the python environment
EOF
}

# ---------- Read command line options ----------#
function _setArgs {
  while [ "${1:-}" != "" ]; do
    case "$1" in
      "-p" | "--path")
        shift
        CONDA_INSTALL_PATH="$1"
        ;;
      "--node")
        INSTALL_NODE=true
        ;;
      "-h" | "--help")
        usage
        exit 0
        ;;
    esac
    shift
  done
  shift $((OPTIND-1))
}
_setArgs "$@";
if [ -z $CONDA_INSTALL_PATH  ]; then
        echo 'Missing -p or --path. Please provide an installation path for the environment.' >&2
        exit 1
fi

parent_dir=$(dirname "$CONDA_INSTALL_PATH")
if [ ! -d "$parent_dir" ]; then
    echo "Error: Parent directory $parent_dir does not exist." >&2
    exit 1
fi

CONDA_INSTALL_PATH=$(realpath "$CONDA_INSTALL_PATH")

# -------------------- 0. Setup -------------------- #
print_title "0/6. Preliminary checks"
# 0.0 -- Create downloads folder (if it does not exist)
if [ ! -d "$SCRIPT_DIR/downloads" ]; then
    mkdir $SCRIPT_DIR/downloads
fi

# 0.1 -- Check 1: Is Anaconda already downloaded?
if [ -e "$SCRIPT_DIR/downloads/$anaconda_installer" ]; then
    echo "Found Anaconda installer in installer/downloads"
    download_conda_flag="false"
else
    echo "No Anaconda installer found in installer/downloads. It will be downloaded."
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
    echo "Warning: found conda packages in downloads/conda_packages. They will not be redownloaded. If you have changed the conda_requirements.txt file, you should remove this folder or its contents before attemtping a reinstall."
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
    echo "Warning: found PyPI packages in downloads/pip_packages. They will not be redownloaded. If you have changed the pip_requirements.txt file, you should remove this folder or its contents before attemtping a reinstall."
    download_pip_packages_flag="false"
fi

# 0.4 -- Check 4: Are there any downloads necessary?
if [[ "${download_conda_flag}" == "false" && "${download_conda_packages_flag}" == "false" && "${download_pip_packages_flag}" == "false" ]]; then
    echo "No downloads necessary."
fi

# -------------------- 1. Installing Anaconda -------------------- #
print_title "1/6. Installing Anaconda"
# 1.0 -- Downloading Anaconda (if necessary).
if [[ "${download_conda_flag}" == "true" ]]; then
    echo "Downloading ${anaconda_installer}"
    wget --no-check-certificate https://repo.anaconda.com/archive/${anaconda_installer} -N --quiet -P $SCRIPT_DIR/downloads
fi
# 1.1 -- Installing Anaconda
echo "Anaconda will be installed in: ${CONDA_INSTALL_PATH}"
bash ${SCRIPT_DIR}/downloads/${anaconda_installer} -b -p ${CONDA_INSTALL_PATH};
# setup conda in current shell; avoid having to restart shell
eval $($CONDA_INSTALL_PATH/bin/conda shell.bash hook)
source ${CONDA_INSTALL_PATH}/etc/profile.d/conda.sh || exit 1
echo "Activating environment by running \"conda activate ${CONDA_INSTALL_PATH}/\""
conda activate ${CONDA_INSTALL_PATH}/
conda info
echo $(which python)
echo $(python --version)

# -------------------- 2. Installing conda dependencies -------------------- #
print_title "2/6. Installing conda dependencies "
# 2.0 -- Downloading In-Silico-Framework conda dependencies (if necessary).
if [ "${download_conda_packages_flag}" == "true" ]; then
    # Get all lines starting with http (not #http), return empty string if there are none
    package_list=$(cat $SCRIPT_DIR/conda_requirements.txt | grep '^http' || echo "")
    if [ -z "$package_list" ]; then
        echo "No conda packages to download."
    else
        echo "Downloading In-Silico-Framework conda dependencies."
        echo $package_list | xargs -t -n 1 -P 8 wget -N -q -P $SCRIPT_DIR/downloads/conda_packages || exit 1
        echo "Download conda packages completed."
    fi
fi
# 2.1 -- Installing In-Silico-Framework conda dependencies.
echo "Installing In-Silico-Framework conda dependencies."
sed "s|https://.*/|$SCRIPT_DIR/downloads/conda_packages/|" $SCRIPT_DIR/conda_requirements.txt > $SCRIPT_DIR/tempfile
conda update --file $SCRIPT_DIR/tempfile --quiet

# 2.2 -- Installing nodejs if necessary
if [ "$INSTALL_NODE" = true ]; then
    echo "Installing nodejs"
    conda install -y nodejs -c conda-forge --repodata-fn=repodata.json
fi

# -------------------- 3. Installing PyPI dependencies -------------------- #
print_title "3/6. Installing PyPI dependencies"
# 3.0 -- Downloading In-Silico-Framework pip dependencies (if necessary).
if [ "${download_pip_packages_flag}" == "true" ]; then
    echo "Downloading In-Silico-Framework pip dependencies."
    python -m pip --no-cache-dir download --no-deps -r $SCRIPT_DIR/pip_requirements.txt -d $SCRIPT_DIR/downloads/pip_packages
    echo "Download pip packages completed."
fi
# 3.1 -- Installing In-Silico-Framework pip dependencies.
echo "Installing In-Silico-Framework pip dependencies."
python -m pip --no-cache-dir install --no-deps -r $SCRIPT_DIR/pip_requirements.txt --no-index --find-links $SCRIPT_DIR/downloads/pip_packages

# -------------------- 4. Patching pandas-msgpack -------------------- #
print_title "4/6. Installing & patching pandas-msgpack"
PD_MSGPACK_HOME="$SCRIPT_DIR/pandas-msgpack"
if [ ! -d "${PD_MSGPACK_HOME}" ]; then
    cd $SCRIPT_DIR
    echo "Cloning pandas-msgpack from GitHub."
    git clone https://github.com/abast/pandas-msgpack.git;
    git -C $SCRIPT_DIR/pandas-msgpack apply $SCRIPT_DIR/pandas_msgpack.patch
fi
cd $PD_MSGPACK_HOME; python setup.py build_ext --inplace --force install
pip list | grep pandas

# -------------------- 5. installing the ipykernel -------------------- #
print_title "5/6. Installing the ipykernel"
python -m ipykernel install --name base --user --display-name isf3.8

# -------------------- 6. Compiling NEURON mechanisms -------------------- #
print_title "6/6. Compiling NEURON mechanisms"
echo "Compiling NEURON mechanisms."
shopt -s extglob
for d in $(find $SCRIPT_DIR/../../mechanisms/*/*py3* -maxdepth 1 -type d)
do
    if [ $(find $d -maxdepth 1 -name "*.mod" -print -quit) ]; then
        echo "compiling mechanisms in $d"
        cd $d;
        
        COMPILATION_DIR=$(find $d -mindepth 2 -type f -name "*.c" -printf '%h\n' | head -n 1 || true)
        if [ -d "$COMPILATION_DIR" ]; then
            echo "Found previously created compilation directory ${COMPILATION_DIR}"
            echo "Deleting previously created $COMPILATION_DIR "
            rm -r $COMPILATION_DIR
        fi
        
        output=$(nrnivmodl 2>&1)
        if echo "$output" | grep -iq "error"; then
            echo "$output"
            exit 1
        else
            echo "$output"
        fi

        # Verify if compilation was succesful
        COMPILATION_DIR=$(find $d -type f -name "*.c" -printf '%h\n' | head -n 1 || true)
        if [ -d "$COMPILATION_DIR" ]; then
            SO_FILE=$(find "$COMPILATION_DIR" -name "*.so" -print -quit)
            if [ ! -f "$SO_FILE" ]; then
                echo "$COMPILATION_DIR does not contain a .so file. Compilation was unsuccesful. Please inspect the output of nrnivmodl for further information."
                exist 1;
            fi 
        else
            echo "No directory found containing *.c files. Compilation was unsuccesful."
            exit 1;
        fi
    fi
done




# -------------------- Cleanup -------------------- #
rm $SCRIPT_DIR/tempfile
exit 0
