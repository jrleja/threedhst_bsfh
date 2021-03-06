#!/bin/bash
### Name of the job
### Requested number of cores
#SBATCH -n 2
### Requested number of nodes
#SBATCH -N 1
### Requested computing time in minutes
#SBATCH -t 5760
### Partition or queue name
#SBATCH -p ozone
### memory per cpu, in MB
#SBATCH --mem-per-cpu=4000
### Job name
#SBATCH -J 'td'
### output and error logs
#SBATCH -o td_huge_%a.out
#SBATCH -e td_huge_%a.err
IDFILE=$APPS"/prospector_alpha/data/3dhst/td_huge.ids"
x=`expr $SLURM_ARRAY_TASK_ID + 9999`
n1=`expr $x \* 2 - 1`
n2=`expr $n1 + 1`
OBJID1=$(sed -n "${n1}p" "$IDFILE")
OBJID2=$(sed -n "${n2}p" "$IDFILE")
FIELD1=${OBJID1%_*}
FIELD2=${OBJID2%_*}

srun -n 1 --exclusive --mpi=pmi2 python $APPS/prospector/scripts/prospector_dynesty.py \
--param_file="$APPS"/prospector_alpha/parameter_files/td_huge_params.py \
--objname="$OBJID1" \
--outfile="$APPS"/prospector_alpha/results/td_huge/"$FIELD1"/"$OBJID1" &

srun -n 1 --exclusive --mpi=pmi2 python $APPS/prospector/scripts/prospector_dynesty.py \
--param_file="$APPS"/prospector_alpha/parameter_files/td_huge_params.py \
--objname="$OBJID2" \
--outfile="$APPS"/prospector_alpha/results/td_huge/"$FIELD2"/"$OBJID2" &
wait