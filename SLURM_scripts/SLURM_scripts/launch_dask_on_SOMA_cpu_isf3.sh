#!/bin/bash -l
#SBATCH -p 'CPU-interactive' # partition (queue)
#SBATCH -N 1 # number of nodes
#SBATCH -n 48 # number of cores
#SBATCH --mem 300000 # memory pool for all cores
#SBATCH -t 1-0:00 # time (D-HH:MM)
#SBATCH -o out.%N.%j.slurm # STDOUT
#SBATCH -e err.%N.%j.slurm # STDERR

unset DISPLAY
unset XDG_RUNTIME_DIR
export SLURM_CPU_BIND=none
ulimit -Sn "$(ulimit -Hn)"

# activate isf-py3 environment
source $HOME/conda-py3/bin/activate;
conda activate 'isf-py3';

# clone ISF in the current directory
ISF_HOME="$(pwd)/in_silico_framework"
export PYTHONPATH="$ISF_HOME:$PYTHONPATH"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$LD_LIBRARY_PATH"

echo "PYTHONPATH: $PYTHONPATH"
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"

# jupyter-lab reverse forward port
port=11113
ssh -fN -R $port:localhost:$port somalogin02

module load ffmpeg
module load git
echo "ffmpeg location: $(which ffmpeg)"

srun -n1 -N1 "$CONDA_PREFIX/bin/python" $ISF_HOME/SLURM_scripts/component_isf.py "$(pwd)/management_dir_$1" $port
