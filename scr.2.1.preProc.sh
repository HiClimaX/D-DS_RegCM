#!/bin/bash

set -e ## Stop on error
source load-env.sh
ulimit -s unlimited

rday=`date +"%y-%m-%d_%Hh%M"`

## -----------------------------------------------------------------------------
bin="./regcm5-bin/"

exeterrain=$bin/terrainCLM45_
exemksurfacedata=$bin/mksurfdataCLM45_
exesst=$bin/sstCLM45_
exeicbc=$bin/icbcCLM45_

## -----------------------------------------------------------------------------
NML=$1
LNM=$2

logfile=logs/log.icbc.${LNM}.$rday

## /////////////////////////////////////////////////////////////////////////////
## BEGIN
## /////////////////////////////////////////////////////////////////////////////


# Create domain information file
echo Run Terrain
$exeterrain  $NML >  $logfile

# Create CLM4.5 surface informatin
echo Run mksurface
$exemksurfacedata  $NML >> $logfile

# Processing for SST
echo Run SST
$exesst  $NML >> $logfile

# Processing for other variable
echo Run ICBC
$exeicbc  $NML >> $logfile




### EOF
