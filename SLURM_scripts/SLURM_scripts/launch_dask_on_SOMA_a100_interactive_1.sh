#!/bin/bash -l
#SBATCH -p GPU-a100 # partition (queue)
#SBATCH -N 1 # number of nodes
#SBATCH -n 32 # number of cores
#SBATCH --mem 0 # memory pool for all cores
#SBATCH -t infinite # time (D-HH:MM)
#SBATCH -o out.slurm.%N.%j.slurm # STDOUT
#SBATCH -e err.slurm.%N.%j.slurm # STDERR
##SBATCH --ntasks-per-node=20
#SBATCH --gres=gpu:4
#SBATCH --qos GPU-a100
#module load cuda
unset XDG_RUNTIME_DIR
unset DISPLAY
export SLURM_CPU_BIND=none
ulimit -Sn "$(ulimit -Hn)"
module load ffmpeg
module load git
echo "ffmpeg location: $(which ffmpeg)"
srun -n1 -N1 -c32 python $MYBASEDIR/project_src/in_silico_framework/SLURM_scripts/setup_SLURM.py $MYBASEDIR/management_dir_$1
##sleep 3000
