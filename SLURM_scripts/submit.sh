#!/bin/bash -l

# Default options
nodes="1"
partition="CPU"
cores="0"
mem="0"  # max
memstr="max"
time="1-0:00"
tpn=""
gres="0"  # default for GPU jobs (half of max)
qosline=""  # not set yet
cuda=$'\n#module load cuda'  # If working on a GPU partition: load cuda with single hashtag, idk why?
interactive="0"
notebook=""
notebook_kwargs=""

PYTHON_EXECUTABLE="$(which python)"

help() {
  cat <<EOF
    Usage: $0 [options] {job name}

    Arguments:

    name
      Name of the job
      Required

    -h, --help
      Display this usage message and exit.

    -N <val>
      Amount of nodes
      Default: $nodes

    -n <val>
      Amount of cores
      Default: $cores

    -m <val>
      Amount of memory (in MB)
      default: $mem MB

    -t <val>
      Amount of time
      Format: "d-hh:mm:ss"
      default: $time

    -g
      Request a GPU partition.

    -i
      Launch an interactive job.

    -I
      Run on GPU-interactive node, with defaults the same as GPU.

    -p <val>
      Request a specific partition. Overwrites the -i and -g flags.
      Default: $partition
      Options: [CPU, CPU-interactive, GPU, GPU-interactive, GPU-a100]

    -A
      Request resources on the A100 nodes.
      Overwrites the -g, -i and -p flags.

    -T <val>
      Amount of tasks per node
      Default: Not used

    -r <val>
      Set value for gres.
      Default:
        2 for GPU jobs
        4 for GPU-a100 jobs

    -b <val>
      Run a notebook
      Pass the name of a notebook to submit it as a batch job
      Default:
        None
EOF
}

usage() {
  cat << EOF
  Usage: $0 [options] {job name}
EOF
}

function args_precheck {
  if [ $1 -eq "0" ] ; then
    echo "Warning: no arguments passed. Launching a job with default parameters and no name."
  elif [ $2 = "--help" ] || [ $2 = "-h" ] ; then
    help
    exit 0
  fi
}

#######################################
# Given a string, continuously prints the string with an 
# updated "..." icon
# Arguments:
#   1. A string
#######################################
# Little spinning icon
dot[0]="   "
dot[1]=".  "
dot[2]=".. "
dot[3]="..."
function printf_with_dots {
    local string=$1
    local width="$(tput cols)"
    local string_length=${#string}
    local padding=$(($width - $string_length - 4))  # to clean out previous long strings
    for i in "${dot[@]}"
    do
        # \r removes previous line
        # \b$i is the ... icon
        # >&2 writes to stdout
        printf "\r$1\b$i%*s" "$padding">&2
        sleep 0.3
    done
}

#######################################
# Checks if a job is already running with same name
# Arguments:
#   1: The name of the job
#######################################
function check_name {
    local n_matches="$(squeue -u $USER | grep ${1:0:8} | wc -l)"
    if [ $n_matches -gt 0 ]; then
      echo "A job with this name is already running. Requested resources will be appended to job \"$1\""
    fi
    return 0
}

#######################################
# Checks for QOS errors
# Arguments:
#   1: The ID of the job
#######################################
function QOS_precheck {
    local width="$(tput cols)"

    while [[ $(squeue --me | grep $1 ) == "" ]]; do
        printf_with_dots "Waiting for job $1 to be submitted "
    done;
    # grep for ID, then grep for something inbetween brackets (the QOS reason)
    reason="$(squeue --me | grep $1 | grep -oP '\(\K[^\)]+' | tail -n1)"
    printf $reason
    while [[ $reason == "None" ]]; do
        printf_with_dots "Waiting for job \"$1\" to be submitted "
        reason="$(squeue --me | grep -oP '\(\K[^\)]+' | tail -n1)";
    done;
    if [[ "$reason" =~ .*"QOS".* ]]; then  # reason has QOS in the name: something went wrong
        local string="Job can't be started (right now). Reason: $reason"
        local string_length=${#string}
        local padding=$(($width - $string_length))  # to clean out previous long strings
        printf "\r$string%*s" "$padding";
        exit 1;
    else
      local string="Job $1 submitted succesfully"
      local string_length=${#string}
      local padding=$(($width - $string_length))  # to clean out previous long strings
      printf "\r$string%*s" "$padding";
    fi;
}

args_precheck $# $1;

# Parse options
while getopts "hN:n:m:t:cgiIp:T:r:Ab:K:" OPT;
do
  case "$OPT" in
    h) usage
        exit;;
    N) nodes=${OPTARG};;
    n) cores=${OPTARG};;
    m) mem=${OPTARG};memstr=$mem;;
    t) time=${OPTARG};;
    c) partition="CPU";;
    g) partition="GPU";;
    i) interactive="1";;
    p) partition=${OPTARG};;  # overwrites i or c flag
    T) tpn=${OPTARG};;
    r) gres=${OPTARG};;
    A) partition="GPU-a100";;  # appendix to start the correct python file
    b) notebook=${OPTARG};;
    K) notebook_kwargs=${OPTARG};;
    \?) # incorrect option
      echo "Error: Invalid option"
      exit 1;;
  esac
done
shift $(( OPTIND - 1 ))  # shift the option index to point to the first non-option argument (should be name of the job)
name=$1
shift;

if [ -z "$name" ]; then
  echo "Warning: no jobname was passed. Job will start without a name."
fi
check_name $name

################### Cluster logic ###################
# Here, some extra variables are changed or created to add to the SLURM script depending on your needs

### 1. Figure out which partition is requested with the flags

# Adapt partition name for interactive jobs requested with -i flag
if [ ${#partition} == 3 -a $interactive == "1" ]; then
  # GPU or CPU interactive session
  # adapt partition name to have -interactive in it
  partition=$partition"-interactive"
fi

#### 2. Depending on the partition, reset default values to max if they have not been explicitly specified.
#### 2.1: CPU partitions (CPU or CPU-interactive)
if [[ ${partition:0:3} == CPU ]]; then 
  gres="0"  # no GPUs
  if [ $mem == "0" ]; then  # memory is unspecified
    mem=93750  # half of max of a CPU node
  fi
  if [ $cores == "0" ]; then  # amount of cores is unspecified
    cores=24
  fi
#### 2.2: GPU partitions (GPU or GPU-interactive)
elif [[ ${partition:0:3} == GPU ]] && [[ $partition != "GPU-a100" ]]; then  
  if [ $gres == "0" ]; then  # gres is unspecified
    gres="2"  # by default, set to half of max gres for GPU partitions
  fi
  if [ $mem == "0" ]; then  # memory is unspecified
    mem=187500  # half of max of a GPU node
  fi
  if [ $cores == "0" ]; then  # amount of cores is unspecified for the user
    cores=24
  fi
else  #### 2.3 GPU-a100
  if [ $cores == "0" ]; then  # amount of cores is unspecified for the user
    cores=32
  fi
  if [ $gres == "0" ]; then  # gres is unspecified
    gres="4"  # by default, set to half of max gres for GPU partitions
  fi
  # set qos
  qosline=$'\n#SBATCH --qos=GPU-a100'
  # if memory is unspecified, it will simply pass 0, which still works for the A-100
fi


#### 3. Depending on interactive/bash, load cuda
if [ $interactive == 1 ]; then
  interactive_string=" interactive"
  cuda=$'\n#module load cuda'
else
  interactive_string=""
fi

if [ ! -z "$tpn" ]; then
  tpn="#SBATCH --ntasks-per-node="$tpn
fi

################### Normal submission (batch or interactive job) ###################
run_str="srun -n1 -N$nodes -c$cores $PYTHON_EXECUTABLE -u \$MYBASEDIR/project_src/in_silico_framework/SLURM_scripts/setup_SLURM.py \$MYBASEDIR/management_dir_$name"
if [ $interactive == "1" ]; then
  run_str=$run_str" --launch_jupyter_server"
fi

################### Submitting a notebook: adapt the run_str ###################
if [ ! -z $notebook ]; then
  if [ $interactive == 1 ]; then
    echo "Please submit notebooks as a batch job, not interactive."
    echo "Beware that the default submit options is interactive."
    echo "You can e.g. manually set the partition to GPU/CPU with the -p flag"
    exit 1
  fi
  run_str=$run_str" --notebook_name $notebook"
fi

if [ ! -z $notebook_kwargs ]; then
  if [ $interactive == 1 ]; then
    echo "Please submit notebooks as a batch job, not interactive."
    echo "Beware that the default submit options is interactive."
    echo "You can e.g. manually set the partition to GPU/CPU with the -p flag"
    exit 1
  fi
  if [ -z $notebook ]; then
    echo "Warning: notebook_kwargs passed, but no notebook name passed. Please pass a notebook name with the -b flag."
    exit 1
  fi
  run_str=$run_str" --nb_kwargs $notebook_kwargs"
fi

# TODO: hard thing is to get SLURM to run two tasks and distribute resources accordingly. Maybe it's easier to implement nbrun in setup_SLURM and consider it 1 task?

################### Print out job info ###################
width="$(tput cols)"
printf '%0.s-' $(seq 1 $width)  # fill width with "-" char
echo "
Launching$interactive_string job named \""$name"\" on $partition with
- $nodes nodes
- $cores cores 
- $memstr MB memory
- gres: $gres
- for $time
"

################### Run SLURM scripts ###################
# create wrapper script to start batch job with given parameters
# using EoF or EoT makes it easier to pass multi-line text with argument values
# This submits the job and catches the output
output=$(sbatch <<EoF
#!/bin/bash -l
#SBATCH --job-name=$name
#SBATCH -p $partition # partition (queue)
#SBATCH -N $nodes # number of nodes
#SBATCH -n $cores # number of tasks
#SBATCH --mem $mem # memory pool for all tasks
#SBATCH -t $time # time (D-HH:MM)
#SBATCH -o out.slurm.%N.%j.slurm # STDOUT
#SBATCH -e err.slurm.%N.%j.slurm # STDERR
#SBATCH --gres=gpu:$gres$qosline$cuda
$tpn
unset XDG_RUNTIME_DIR
unset DISPLAY
module unload ffmpeg
module load ffmpeg/4.4
export SLURM_CPU_BIND=none
ulimit -Sn "\$(ulimit -Hn)"
$run_str
EoF
)

if [[ $output == "" ]]; then
  # If a job can not be started due to an sbatch error (unavailable node configuration),
  # then sbatch will print an error itself to stdout
  # and the command output will be empty
  exit 1;
else
  # sbatch does not throw an error, but some errors might still appear
  id=$(echo $output | tr -d -c 0-9)
  # check for QOS errors
  QOS_precheck $id  # the job ID

  # No QOS errors, continue setting up management dir, and jupyter servers
  printf '%0.s-' $(seq 1 $width)  # fill width with "-" char
  echo ""
  # setup jupyter server if it is an interactive job
  if [ $interactive == "1" ]; then
    # fetch working directory of current script
    __dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    # also run jupyter_link to fetch the link where the jupyter server is running
    bash ${__dir}/jupyter_link.sh $name
  # don't setup jupyter server if it is not an interactive job
  else
    printf "Batch job: no jupyter server will be launched.\n"
  fi
fi

