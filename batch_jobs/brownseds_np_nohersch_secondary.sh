#!/bin/bash
### Name of the job
### Requested number of cores
#SBATCH -n 1
### Requested number of nodes
#SBATCH -N 1
### Requested computing time in minutes
#SBATCH -t 480
### Partition or queue name
#SBATCH -p conroy,serial_requeue
### memory per cpu, in MB
#SBATCH --mem-per-cpu=10000
### Job name
#SBATCH -J 'bseds_np_sec'
### output and error logs
#SBATCH -o brownseds_np_nohersch_sec_%a.out
#SBATCH -e brownseds_np_nohersch_sec_%a.err
### mail
#SBATCH --mail-type=END
#SBATCH --mail-user=joel.leja@gmail.com
### source activate pympi
python $APPS/prospector_alpha/code/extra_output.py $APPS/prospector_alpha/parameter_files/brownseds_np_nohersch/brownseds_np_nohersch_params_$SLURM_ARRAY_TASK_ID.py 