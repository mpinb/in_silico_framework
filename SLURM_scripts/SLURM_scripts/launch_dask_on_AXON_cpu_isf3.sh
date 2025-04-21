#!/bin/bash -l
#SBATCH -p p.axon # partition (queue)
#SBATCH -N 1 # number of nodes
#SBATCH -n 40 # number of cores
#SBATCH --mem 384000 # memory pool for all cores
#SBATCH -t 1-0:00 # time (D-HH:MM)
#SBATCH -o out.%N.%j.slurm # STDOUT
#SBATCH -e err.%N.%j.slurm # STDERR

unset DISPLAY
unset XDG_RUNTIME_DIR
export SLURM_CPU_BIND=none
ulimit -Sn "$(ulimit -Hn)"

# activate isf-py3 environment
source $HOME/conda-py3/bin/activate
conda activate isf-py3

# expect ISF copy in user's home directory
ISF_HOME="$HOME/in_silico_framework"
export PYTHONPATH="$ISF_HOME:$PYTHONPATH"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$LD_LIBRARY_PATH"

echo "PYTHONPATH: $PYTHONPATH"
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"

# jupyter-lab reverse forward port
port=11113
ssh -fN -R $port:localhost:$port axon01.bc.rzg.mpg.de
# Uncomment line below to debug ssh proxy-tunnel connection errors
# ssh -v -fN -R $port:localhost:$port axon01.bc.rzg.mpg.de
# If connection fails please add a public key (with no passphrase)
# to the ~/.ssh/authorized_keys file  (Omar V.M.)

module load ffmpeg
echo "ffmpeg location: $(which ffmpeg)"

srun -n1 -N1 "$CONDA_PREFIX/bin/python" $ISF_HOME/SLURM_scripts/component_isf.py "$(pwd)/management_dir_$1" $port
