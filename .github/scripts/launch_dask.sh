#!/usr/bin/env bash 

# Default values
NPROCS=10
PORT=8786
BOKEH_PORT=8787

# Parse options
while [[ $# -gt 0 ]]; do
  case "$1" in
    --nprocs)
      NPROCS="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --bokeh-port)
      BOKEH_PORT="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "Launching Dask scheduler..."
( \
    pixi r dask-scheduler \
    --port="$PORT" \
    --bokeh-port="$BOKEH_PORT" \
    --host=localhost \
    > ./tests/logs/dask_scheduler_$GITHUB_RUN_ID.log 2>&1\
) &

echo "Launching Dask workers..."
( \
    pixi r dask-worker \
    localhost:"$PORT" \
    --nthreads 1 \
    --nprocs "$NPROCS" \
    --memory-limit=100e15 \
    --local-directory="." \
    > ./tests/logs/dask_workers_$GITHUB_RUN_ID.log 2>&1\
) &

echo "Waiting for Dask scheduler to be ready..."
for i in {1..30}; do
    if nc -z localhost 8786; then
    echo "Dask scheduler is ready!"
    break
    fi
    echo "Waiting for Dask scheduler..."
    sleep 2
done