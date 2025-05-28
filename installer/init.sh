# Initialization hook for ISF
export PYTHONPATH=$(dirname "$0"):$PYTHONPATH
python installer/init_hook.py