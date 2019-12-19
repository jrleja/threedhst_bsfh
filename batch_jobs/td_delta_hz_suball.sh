#!/bin/bash
### Name of the job
### Requested number of cores
#SBATCH -n 1
### Requested number of nodes
#SBATCH -N 1
### Requested computing time in minutes
#SBATCH -t 5760
### Partition or queue name
#SBATCH -p shared,itc_cluster,conroy_requeue
### memory per cpu, in MB
#SBATCH --mem-per-cpu=4000
### output and error logs
#SBATCH -o td_delta_hz_%a.out
#SBATCH -e td_delta_hz_%a.err
### Job name
#SBATCH -J 'td_delta_hz'
IDFILE=$APPS"/prospector_alpha/data/3dhst/td_new_hz.ids"
OBJID=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$IDFILE")
srun -n 1 --mpi=pmi2 python $APPS/prospector/scripts/prospector_dynesty.py \
--param_file="$APPS"/prospector_alpha/parameter_files/td_delta_params.py \
--objname="$OBJID" \
--outfile="$APPS"/prospector_alpha/results/td_delta_hz/"$OBJID" \
--runname="td_new_hz"