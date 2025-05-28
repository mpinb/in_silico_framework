# Initialization hook for ISF
export PYTHONPATH=$(dirname "$0"):$PYTHONPATH
python3 installer/init_hook.py