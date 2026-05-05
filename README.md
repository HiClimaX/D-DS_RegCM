
# Run 'init.sh' to create folders as our recommendation

# The required libraries can be found in 'load-env.sh'
  - Here we use intel compiler with mvapich2, but the native intel should work
  - If users use other compiler, such as GNU, file 'load-env.sh' HAVE to be modified accordingly

# Compiling RegCM5
  - User can use our current version of RegCM5 in 'model/5.0.0.tar.gz'
  - Otherwise, the latest version can be downloaded the on github
  - To compile the model:
    1. cd model
    2. tar zxvf 5.0.0.tar.gz
    3. cd RegCM-5.0.0 # or any other folder name extracted from the 5.0.0.tar.gz
    4. ./bootstrap.sh
    5. ./configure --enable-clm45  # always use CLM45 for land-surface model (BATS is too old and simple)
    6. make -j 16  # higher number ~ faster process
    7. make install

  - sometimes 'make -j 16' may be interupted, just run it again.
  - If the error(s) still not solved, double check againt he configure step (see more in config.log)
  - the executable files, including the model, will be stored in 'bin'

------------------------------------
# Downloading dataset
To be describe later

------------------------------------
Operating RegCM5 system

# 1. Read the template namelist (progs/README.namelist) carefully
  - List out parameters that should be change in your similation

# 2. Create/Edit file 'configure-domain.tbl'
  - The file should be in the following structure
  ------------------------------------
  |  domain      params      value   |  <- this is header, the later program won't read first line  
  |  d01         domname     'd01'   |  <- a parameter of domain 1
  |  d02         domname     'd02'   |  <- a parameter of domain 2
  |  d01,d02     idynamic    3       |  <- a SHARED parameter of domain 1 & 2
  ------------------------------------

# 3. Edit and run 'scr.1.generate_namelists.sh' to create namelist files
  - Pay attention to: TEMPLATE, ODIR, TABLE, EXPNM

# 4. Run 'scr.2.1.preProc.sh' to create pre-processing files (domain, land-surface, sst, icbc)
  - The pre-processing should run on a single processor
  - There is an option for parallelly run, but not stable and depending on the system setting

# 5. Run 'scr.2.2.runRegCM.sh' to perform the simulation
  - Run the program parallelly using 'mpirun'

# NOTEs: step 4&5 is highly depend on the computer system.
  - Read 'scr.2.0.submit-HILO.sh' for your reference of a SLURM system



