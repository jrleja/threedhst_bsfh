#!/bin/bash
# loop over all jobs
# look for output
# if it doesn't exist, submit it
IDFILE=$APPS"/prospector_alpha/data/gama.ids"
for ((value=1; value<=11250; value++)); do
    n1=`expr $value + 1`
    OBJID=$(sed -n "${n1}p" "$IDFILE")
    if ! ls $APPS/prospector_alpha/results/gama_continuity/*"${OBJID}"_*h5 1> /dev/null 2>&1; then
        OUTFILE=$APPS/prospector_alpha/results/gama_continuity/${OBJID}
        echo ${OBJID}, ${value}
       	sbatch -o gama_continuity_${value}.out -e gama_continuity_${value}.err submit_one_gama_continuity.sh ${OBJID} ${OUTFILE} ${value}
    fi
done
wait
