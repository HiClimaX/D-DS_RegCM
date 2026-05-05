# RegCM5 Simulation Workflow

This repository contains automation scripts and instructions for compiling and operating the Regional Climate Model version 5 (RegCM5).

---

## 📋 Prerequisites & Environment

Before starting, initialize the project directory structure and load the required compiler modules.

1.  **Initialize Folders:**
    ```bash
    bash init.sh
    ```
2.  **Load Environment:**
    The required libraries are defined in `load-env.sh`.
    *   The default configuration uses the **Intel Compiler with MVAPICH2**.
    *   **Note:** If using **GNU** or other compilers, you **must** modify `load-env.sh` accordingly before proceeding.

---

## 🛠️ Installation & Compilation

### 1. Obtain the Source Code
You can use the version provided in this repository or download the latest from GitHub.
*   **Local Version:** `model/5.0.0.tar.gz`
*   **GitHub:** [RegCM GitHub Repository](https://github.com/ICTP/RegCM)

### 2. Build the Model
Run the following sequence to compile the executable:

```bash
cd model
tar zxvf 5.0.0.tar.gz
cd RegCM-5.0.0
./bootstrap.sh
./configure --enable-clm45  # CLM45 is recommended; BATS is deprecated.
make -j 16                  # Parallel build
make install
```

[!TIP]

* If `make -j 16` is interrupted, simply run the command again.
* If errors persist, check `config.log` for missing dependencies.
* Compiled executables will be stored in the `/bin` directory.

## 📂 Downloading Datasets
*(Section to be updated with specific data source links and scripts)*

## 🚀 Operating RegCM5
Follow these steps to configure and run your simulation.

### Step 1: Analyze the Namelist Template
Carefully read `progs/README.namelist`. This file contains the documentation for all parameters. Identify which variables need modification for your specific experiment.

### Step 2: Configure Domain Parameters
Edit `configure-domain.tbl`. This table allows you to manage multiple domains and shared parameters easily.

Format Example:
| domain | params | value | Note |
| :--- | :--- | :--- | :--- |
| d01 | domname | 'd01' | Specific to Domain 1 |
| d02 | domname | 'd02' | Specific to Domain 2 |
| d01,d02 | idynamic | 3 | Shared by both domains |

### Step 3: Generate Namelists
Run the generation script to create `nml.d0X.in` files based on your table:

```bash
bash scr.1.generate_namelists.sh
```
* **Check variables inside the script**: Ensure TEMPLATE, ODIR, TABLE, and EXPNM are correctly set.

### Step 4: Pre-Processing
Generate domain topography, land-surface parameters, SST, and ICBC files:

```bash
bash scr.2.1.preProc.sh
```

[!WARNING]
Pre-processing should generally be run on a **single processor**. While parallel options exist, they may be unstable depending on your system architecture.

### Step 5: Execute Simulation
Perform the model run using MPI:

```
bash scr.2.2.runRegCM.sh
```

## 🖥️ System-Specific Notes (HPC/SLURM)
Steps 4 and 5 are highly dependent on your local cluster environment.

* If your system uses the **SLURM** workload manager, refer to `scr.2.0.submit-HILO.sh` as a template for your submission scripts.
* Ensure mpirun or srun paths match your environment.

# EOF
