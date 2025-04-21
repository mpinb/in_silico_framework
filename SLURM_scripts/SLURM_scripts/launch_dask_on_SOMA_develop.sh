#!/bin/bash -l
#SBATCH -p GPU # partition (queue)
#SBATCH -N 4 # number of nodes
#SBATCH -n 48 # number of cores
#SBATCH --mem 0 # memory pool for all cores
#SBATCH -t 1-0:00 # time (D-HH:MM)
#SBATCH -o out.slurm.%N.%j.slurm # STDOUT
#SBATCH -e err.slurm.%N.%j.slurm # STDERR
##SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:4
module load cuda
module load ffmpeg
module load git
unset XDG_RUNTIME_DIR
unset DISPLAY
export SLURM_CPU_BIND=none
export ISF_USE_SLURM_RANK=1

master_addr=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -n 1)
export ISF_MASTER_ADDR=$master_addr
echo $master_addr

ulimit -Sn "$(ulimit -Hn)"
module load ffmpeg
echo "ffmpeg location: $(which ffmpeg)"
srun -n4 --cpus-per-task=12 python $MYBASEDIR/project_src/in_silico_framework/SLURM_scripts/setup_no_management_dir.py $1 $2

##sleep 3000
