export MYBASEDIR="$HOME"
export ISF_HOME=$MYBASEDIR/project_src/in_silico_framework
alias source_isf='source $MYBASEDIR/anaconda_isf2.7/bin/activate; export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH; cd $MYBASEDIR'
alias source_3='source $MYBASEDIR/anaconda_isf3.8/bin/activate; export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH; cd $MYBASEDIR'
alias source_39='source $MYBASEDIR/anaconda_isf3.9/bin/activate; export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH; cd $MYBASEDIR'
alias isf='cd $ISF_HOME'