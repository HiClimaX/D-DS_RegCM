#!/bin/bash


## ------------------------------------------------------------------------------------------------
## Run Pre-processing
## Usually the Pre-proessing should run only on 1 core. There is an option in RegCM5 allowing to 
## run the ICBC parallely, but it is not stable.

# SRC=scr.2.1.preProc.sh
# PARTITION=broadwell
# NODES=1
# NTPNS=1
# 
# JOBNM=2011d01
# NML="regcm5-nml/nml.201108.d01.in" ; LNM="201108.d01"
# #sbatch  --job-name=$JOBNM --output=hilolog.$LNM --exclusive --time=240:00:00 \
# #        --partition=$PARTITION --nodes=$NODES --ntasks-per-node=$NTPNS \
#         ./$SRC $NML $LNM
# 
# JOBNM=2014d01
# NML="regcm5-nml/nml.201408.d01.in" ; LNM="201408.d01"
# #sbatch  --job-name=$JOBNM --output=hilolog.$LNM --exclusive --time=240:00:00 \
# #        --partition=$PARTITION --nodes=$NODES --ntasks-per-node=$NTPNS \
#         ./$SRC $NML $LNM
# 
# JOBNM=2015d01
# NML="regcm5-nml/nml.201508.d01.in" ; LNM="201508.d01"
# #sbatch  --job-name=$JOBNM --output=hilolog.$LNM --exclusive --time=240:00:00 \
# #        --partition=$PARTITION --nodes=$NODES --ntasks-per-node=$NTPNS \
#         ./$SRC $NML $LNM

## ------------------------------------------------------------------------------------------------
## Run Model
SRC=scr.2.2.runRegCM.sh

PARTITION=scalable ; NODES=2 ; NTPNS=56
JOBNM=2011d01
NML="regcm5-nml/nml.201108.d01.in" ; LNM="201108.d01"
sbatch  --job-name=$JOBNM --output=hilolog.$LNM --exclusive --time=240:00:00 \
        --partition=$PARTITION --nodes=$NODES --ntasks-per-node=$NTPNS \
        ./$SRC $NML $LNM

JOBNM=2014d01
NML="regcm5-nml/nml.201408.d01.in" ; LNM="201408.d01"
sbatch  --job-name=$JOBNM --output=hilolog.$LNM --exclusive --time=240:00:00 \
        --partition=$PARTITION --nodes=$NODES --ntasks-per-node=$NTPNS \
        ./$SRC $NML $LNM

JOBNM=2015d01
NML="regcm5-nml/nml.201508.d01.in" ; LNM="201508.d01"
sbatch  --job-name=$JOBNM --output=hilolog.$LNM --exclusive --time=240:00:00 \
        --partition=$PARTITION --nodes=$NODES --ntasks-per-node=$NTPNS \
        ./$SRC $NML $LNM



### EOF
