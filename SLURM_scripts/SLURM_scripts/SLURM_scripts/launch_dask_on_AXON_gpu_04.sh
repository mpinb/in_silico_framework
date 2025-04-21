#!/bin/bash -l
#SBATCH -p p.gpu # partition (queue)
#SBATCH -N 4 # number of nodes
#SBATCH -n 4 # number of cores
#SBATCH --mem 190000 # MaxMemPerNode # 100000 # memory pool for all cores
#SBATCH -t 1-0:00 # time (D-HH:MM)
#SBATCH -o out.slurm.%N.%j.slurm # STDOUT
#SBATCH -e err.slurm.%N.%j.slurm # STDERR
#SBATCH --ntasks-per-node=20
#SBATCH --gres=gpu:1
module load cuda
unset XDG_RUNTIME_DIR
unset DISPLAY
export SLURM_CPU_BIND=none
ulimit -Sn "$(ulimit -Hn)"
module load ffmpeg
echo "ffmpeg location: $(which ffmpeg)"
srun -n4 -N4 -c20 python $MYBASEDIR/project_src/in_silico_framework/SLURM_scripts/component_1.py $MYBASEDIR/management_dir_$1
## sleep 3000
