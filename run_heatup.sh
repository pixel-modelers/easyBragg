#!/bin/bash
# Usage: run_heatup.sh <xia2_proc_dir> [hopper_heatup args...]
# Example: run_heatup.sh /data/scratch/.../B3_si_mode_7112eV_1.proc
set -euo pipefail

SCRIPTDIR=$(cd "$(dirname "$0")" && pwd)

# --- User settings ---
export CUDA_VISIBLE_DEVICES=1,2,3
export DIFFBRAGG_USE_CUDA=1
NUM_DEVICES=$(echo "$CUDA_VISIBLE_DEVICES" | tr ',' '\n' | wc -l)
WORKERS_PER_GPU=4
MPI_PROCS=$(( NUM_DEVICES * WORKERS_PER_GPU + 1 ))
STEP=8
MTZ_COLUMN="I(+),SIGI(+),I(-),SIGI(-)"
BASEDIR="$SCRIPTDIR/heatups"
# ----------------------

XIA2_DIR="$1"; shift
XIA2_NAME=$(basename "$XIA2_DIR" .proc)
WORKDIR="$BASEDIR/$XIA2_NAME"
N=1; while [ -d "$WORKDIR" ]; do WORKDIR="$BASEDIR/${XIA2_NAME}_${N}"; N=$((N+1)); done
RUN="conda run -n simtbx"

# Find inputs
EXPT=$(ls "$XIA2_DIR"/DEFAULT/NATIVE/SWEEP1/*/${STEP}_*.expt 2>/dev/null | head -1)
REFL="${EXPT%.expt}.refl"
MTZ="$XIA2_DIR/DEFAULT/scale/AUTOMATIC_DEFAULT_scaled.mtz"
DELTA_PHI=$($RUN python -c "
from dxtbx.model import ExperimentList
print(f'{ExperimentList.from_file(\"$EXPT\")[0].scan.get_oscillation()[1]:.4f}')
" 2>/dev/null)

mkdir -p "$WORKDIR" && cd "$WORKDIR"

[ -f expanded/exp_ref_spec.txt ] || \
    expand_rotation_to_stills.py "$EXPT" "$REFL" --outdir expanded

[ -f auto_hop.phil ] || \
    make_phil.py --spec expanded/exp_ref_spec.txt \
        --mtz "$MTZ" --mtz-column "$MTZ_COLUMN" --delta-phi "$DELTA_PHI" \
        --outdir hopper_out --estimate-G --num-devices "$NUM_DEVICES" -o auto_hop.phil

mpirun -n "$MPI_PROCS" hopper_heatup.py \
    auto_hop.phil --spec expanded/exp_ref_spec.txt \
    --mpi --stages G,RotXYZ,Nabc,B,ucell --n-gpus $NUM_DEVICES \
    --deep-dive --keep-trials -o optimized.phil --tmpdir tmp \
    --max-calls 100 --deep-dive-max-calls 500 --n-nearby 1 \
    --trials-per-worker 1 --n-shuffles 1  --tune-restraints \
    --final-refine-max-calls 2500 --roi-fraction 0.5 --spread-roi-fraction 1  \
    --tune-n-frames 5  --trials-per-worker 3 "$@"
