#!/bin/bash
### Name of the job
### Requested number of cores
#SBATCH -n 32
### Requested number of nodes
#SBATCH -N 1
### Requested computing time in minutes
#SBATCH -t 600
### Partition or queue name
#SBATCH -p conroy,general
### memory per cpu, in MB
#SBATCH --mem-per-cpu=1500
### Job name
#SBATCH -J '3Drun'
### output and error logs
#SBATCH -o testsed_simha_truth_%a.out
#SBATCH -e testsed_simha_truth_%a.err
### mail
#SBATCH --mail-type=END
#SBATCH --mail-user=joel.leja@gmail.com
### source activate pympi
mpirun -n 32 python $APPS/bsfh/demo/prospectr.py --param_file=$APPS/threedhst_bsfh/parameter_files/testsed_simha_truth/testsed_simha_truth_params_$SLURM_ARRAY_TASK_ID.py  --sps=fsps --custom_filter_keys=$APPS/threedhst_bsfh/filters/filter_keys_threedhst.txt 