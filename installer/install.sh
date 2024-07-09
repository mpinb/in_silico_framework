#!/bin/bash

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

if ! command -v wget &> /dev/null; then
    echo "wget could not be found. Please install wget."
    exit 1
fi

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
INVOCATION_DIR=$(pwd)

# Ask the user for the Python version
while true; do
    echo "Please enter the Python version (2.7, 3.8, or 3.9):"
    read PYTHON_VERSION

    # Validate the Python version
    if [[ "$PYTHON_VERSION" == "2.7" || "$PYTHON_VERSION" == "3.8" || "$PYTHON_VERSION" == "3.9" ]]; then
        break
    else
        echo "Invalid Python version. Please enter 2.7, 3.8, or 3.9."
    fi
done

# If Python version is 3.8, ask whether or not to install Node.js
if [ "$PYTHON_VERSION" == "3.8" ]; then
    while true; do
        echo "Do you want to install Node.js alongside the Anaconda installation? ([Yy]es/[Nn]o)"
        read INSTALL_NODEJS
        if [[ "$INSTALL_NODEJS" =~ ^[Nn].*$ ]]; then
            INSTALL_NODEJS="no"
            break
        elif [[ "$INSTALL_NODEJS" =~ ^[Yy].*$ ]]; then
            INSTALL_NODEJS="yes"
            break
        else
            echo "Invalid option. Please enter 'Yes/yes/Y/y' or 'No/no/N/n'."
        fi
    done
fi

while true; do
    echo "Would you like to additionally download an anatomical model of the rat barrel cortex, compatible with ISF? ([Yy]es/[Nn]o)"
    read DOWNLOAD_BC_MODEL
    if [[ "$DOWNLOAD_BC_MODEL" =~ ^[Nn].*$ ]]; then
        DOWNLOAD_BC_MODEL="no"
        break
    elif [[ "$DOWNLOAD_BC_MODEL" =~ ^[Yy].*$ ]]; then
        DOWNLOAD_BC_MODEL="yes"
        break
    else
        echo "Invalid option. Please enter 'Yes/yes/Y/y' or 'No/no/N/n'."
    fi
done

# Ask the user for the installation directory
while true; do
    echo "Please enter the installation directory:"
    read INSTALL_DIR

    # Validate the installation directory
    PARENT_DIR=$(dirname "$INSTALL_DIR")
    if [ -d "$PARENT_DIR" ]; then
        break
    else
        echo "Invalid directory. The parent directory ${PARENT_DIR} does not exist."
    fi
done

if [ "$DOWNLOAD_BC_MODEL" == "yes" ]; then
    echo $SCRIPT_DIR
    ls $SCRIPT_DIR
    bash -x "${SCRIPT_DIR}/download_bc_model.sh" || exit 1
fi

# Invoke the installation script in the correct folder
if [ "$INSTALL_NODEJS" == "yes" ]; then
    bash "${SCRIPT_DIR}/py${PYTHON_VERSION}/install.sh" -p "${INSTALL_DIR}" --node || exit 1
else
    bash "${SCRIPT_DIR}/py${PYTHON_VERSION}/install.sh" -p "${INSTALL_DIR}" || exit 1
fi

cd $SCRIPT_DIR
if [ "$DOWNLOAD_BC_MODEL" == "yes" ]; then
    bash "${SCRIPT_DIR}/download_bc_model.sh " || exit 1
fi

echo -e <<EOF
\e[1;32m*****************************************************************\e[0m
\e[1;32m*                                                               *\e[0m
\e[1;32m*   Succesfully installed In-Silico-Framework for Python 2.7.   *\e[0m
\e[1;32m*                                                               *\e[0m
\e[1;32m*****************************************************************\e[0m

You are now ready to use ISF. Start by activating the ISF conda environment: \"source ${INSTALL_DIR}/bin/activate\"
For a general introduction to ISF, please refer to $(realpath $(dirname $SCRIPT_DIR))/getting_started/Introduction_to_ISF.ipynb
EOF