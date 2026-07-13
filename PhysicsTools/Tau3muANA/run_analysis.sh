#!/bin/bash
# run this code via submit_analysis.sub
export HOME=/lustrehome/felicenenna
export USER=felicenenna

CLUSTER_ID=$1
PROC_ID=$2
YEAR=$3
ERA=$4
STREAM=$5

echo "Running Job for Era: $ERA"

VENV_ROOT=/lustrehome/felicenenna/tau3mu_newWorkflow/CMSSW_15_1_0/src/PhysicsTools/Tau3muANA/my_dask_env
VENV_PY=$VENV_ROOT/bin/python3
export PYTHONPATH=$VENV_ROOT/lib/python3.9/site-packages:$VENV_ROOT/lib64/python3.9/site-packages:$PYTHONPATH
cd /lustrehome/felicenenna/tau3mu_newWorkflow/CMSSW_15_1_0/src/PhysicsTools/Tau3muANA/


$VENV_PY tau3mu_analysis_runner.py \
    -y $YEAR \
    -e $ERA \
    -s $STREAM \
    -t control \
    -o full_dataset_$YEAR/Era \
    -w 100