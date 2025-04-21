#!/bin/bash -l
#SBATCH -p CPU-long # partition (queue)
#SBATCH -N 10 # number of nodes
#SBATCH -n 480 # number of cores
#SBATCH --mem 0 # memory pool for all cores
#SBATCH -t 5-0:00 # time (D-HH:MM)
#SBATCH -o out.slurm.%N.%j.slurm # STDOUT
#SBATCH -e err.slurm.%N.%j.slurm # STDERR
##SBATCH --ntasks-per-node=20
##SBATCH --gres=gpu:1
#module load cuda
unset XDG_RUNTIME_DIR
unset DISPLAY
export SLURM_CPU_BIND=none
ulimit -Sn "$(ulimit -Hn)"
module load ffmpeg
module load git
echo "ffmpeg location: $(which ffmpeg)"
srun -n10 --cpus-per-task=48 python $MYBASEDIR/project_src/in_silico_framework/SLURM_scripts/setup_SLURM.py $MYBASEDIR/management_dir_$1
