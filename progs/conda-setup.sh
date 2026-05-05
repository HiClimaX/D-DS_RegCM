#!/bin/bash

WDIR=$PWD



## #############################################################################
## -----------------------------------------------------------------------------
## 
##  - Make sure RegCM5 is install succesfully on your system
##  - Latest version of RegCM can be found here:
##      https://github.com/ICTP/RegCM/releases/tag/5.0.0
##  - IMPORTANT: always enable CLM45 in RegCM configuration
##      ./configure --enable-clm45 
## -----------------------------------------------------------------------------
## #############################################################################



CONDAenv="HiClimaX"

## -----------------------------------------------------------------------------
CONDAdir=$(readlink -f $(which conda 2> /dev/null))
CONDAdir=${CONDAdir%%condabin*}
echo $CONDAdir

source $CONDAdir/etc/profile.d/conda.sh

# Deactivate current conda env
while [ `conda info | grep "shell level" | awk '{print $4}'` != 0 ] ; do
  conda deactivate
done 

## -----------------------------------------------------------------------------
## Check if the new conda env existed
if conda env list | awk '{print $1}' | grep -Fxq "$CONDAenv"; then
  echo "Announcement: The environment '$CONDAenv' already exists. Skipping creation/renaming."
else
  echo "Environment '$CONDAenv' does not exist. You can proceed with development."
  # Your creation command would go here, e.g.:
  echo "> Creating new conda environment:: $CONDAenv"
  
  
  conda create -n $CONDAenv -y
  echo "> Done!"
fi

conda activate $CONDAenv

