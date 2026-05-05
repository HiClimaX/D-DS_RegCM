#!/bin/bash

set -e ## Stop on error
source load-env.sh
ulimit -s unlimited

rday=`date +"%y-%m-%d_%Hh%M"`

## -----------------------------------------------------------------------------
bin="./regcm5-bin/"

exeregcm=$bin/regcmMPICLM45


## -----------------------------------------------------------------------------
NML=$1
LNM=$2

logfile=logs/log.regcm.${LNM}.$rday

## /////////////////////////////////////////////////////////////////////////////
## BEGIN
## /////////////////////////////////////////////////////////////////////////////


# Running RegCM
mpirun  $exeregcm  $NML > $logfile



### EOF
