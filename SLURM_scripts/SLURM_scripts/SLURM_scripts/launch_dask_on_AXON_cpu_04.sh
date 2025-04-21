#!/bin/bash -l
#SBATCH -p p.axon # partition (queue)
#SBATCH -N 4 # number of nodes
#SBATCH -n 4 # number of cores
#SBATCH --mem 384000 # 100000 # memory pool for all cores
#SBATCH -t 1-0:00 # time (D-HH:MM)
#SBATCH -o out.slurm.%N.%j.slurm # STDOUT
#SBATCH -e err.slurm.%N.%j.slurm # STDERR
#SBATCH --ntasks-per-node=40
unset XDG_RUNTIME_DIR
unset DISPLAY
export SLURM_CPU_BIND=none
ulimit -Sn "$(ulimit -Hn)"
module load ffmpeg
echo "ffmpeg location: $(which ffmpeg)"
srun -n4 -N4 -c40 python $MYBASEDIR/project_src/in_silico_framework/SLURM_scripts/component_1.py $MYBASEDIR/management_dir_$1
## sleep 3000
