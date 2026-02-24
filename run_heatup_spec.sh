#!/bin/bash
# Usage: run_heatup_spec.sh <spec_file> <mtz_file> [hopper_heatup args...]
# Example: run_heatup_spec.sh /data/expanded/exp_ref_spec.txt /data/merged.mtz
set -euo pipefail

SCRIPTDIR=$(cd "$(dirname "$0")" && pwd)

# --- User settings ---
export CUDA_VISIBLE_DEVICES=1,2,3
export DIFFBRAGG_USE_CUDA=1
NUM_DEVICES=$(echo "$CUDA_VISIBLE_DEVICES" | tr ',' '\n' | wc -l)
WORKERS_PER_GPU=4
MPI_PROCS=$(( NUM_DEVICES * WORKERS_PER_GPU + 1 ))
MTZ_COLUMN="I(+),SIGI(+),I(-),SIGI(-)"
BASEDIR="$SCRIPTDIR/heatups"
# ----------------------

SPEC="$(realpath "$1")"; shift
MTZ="$(realpath "$1")"; shift

SPECNAME=$(basename "$(dirname "$SPEC")")
WORKDIR="$BASEDIR/$SPECNAME"
N=1; while [ -d "$WORKDIR" ]; do WORKDIR="$BASEDIR/${SPECNAME}_${N}"; N=$((N+1)); done
RUN="conda run -n simtbx"

# Read delta-phi from the first experiment in the spec file
FIRST_EXPT=$(head -1 "$SPEC" | awk '{print $1}')
DELTA_PHI=$($RUN python -c "
from dxtbx.model import ExperimentList
print(f'{ExperimentList.from_file(\"$FIRST_EXPT\")[0].scan.get_oscillation()[1]:.4f}')
" 2>/dev/null)

mkdir -p "$WORKDIR" && cd "$WORKDIR"

[ -f auto_hop.phil ] || \
    make_phil.py --spec "$SPEC" \
        --mtz "$MTZ" --mtz-column "$MTZ_COLUMN" --delta-phi "$DELTA_PHI" \
        --outdir hopper_out --estimate-G --num-devices "$NUM_DEVICES" -o auto_hop.phil

mpirun -n "$MPI_PROCS" hopper_heatup.py \
    auto_hop.phil --spec "$SPEC" \
    --mpi --stages G,RotXYZ,Nabc,B,ucell --n-gpus $NUM_DEVICES \
    --deep-dive --keep-trials -o optimized.phil --tmpdir tmp \
    --max-calls 100 --deep-dive-max-calls 500 --n-nearby 1 \
    --trials-per-worker 1 --n-shuffles 1  --tune-restraints \
    --final-refine-max-calls 2500 --roi-fraction 0.5 --spread-roi-fraction 1  \
    --tune-n-frames 5  --trials-per-worker 3 "$@"
