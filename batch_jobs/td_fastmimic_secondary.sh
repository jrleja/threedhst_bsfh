#!/bin/bash
### Name of the job
### Requested number of cores
#SBATCH -n 1
### Requested number of nodes
#SBATCH -N 1
### Requested computing time in minutes
#SBATCH -t 960
### Partition or queue name
#SBATCH -p conroy,serial_requeue
### memory per cpu, in MB
#SBATCH --mem-per-cpu=6500
### Job name
#SBATCH -J 'td_fastmimic_sec'
### output and error logs
#SBATCH -o td_fastmimic_sec_%a.out
#SBATCH -e td_fastmimic_sec_%a.err
### mail
#SBATCH --mail-type=END
#SBATCH --mail-user=joel.leja@gmail.com
IDFILE=$APPS"/prospector_alpha/data/3dhst/td_fastmimic.ids"
OBJID=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$IDFILE")

python $APPS/prospector_alpha/code/td_fastmimic/postprocessing.py \
$APPS/prospector_alpha/parameter_files/td_fastmimic_params.py \
--objname="$OBJID"