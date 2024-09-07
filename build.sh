#!/bin/bash
# NOTE, this script is for debug purposes. Try using cmake
#
# Set compiler to nvcc for a CUDA build, and g++ for a CPU-only build
#CC=nvcc

PYMAJ=$(python -c "import sys;print(sys.version_info[0])")
PYMIN=$(python -c "import sys;print(sys.version_info[1])")
PYNUM=$(echo $PYMAJ$PYMIN)
PY=$(echo python$PYMAJ.$PYMIN)
SIMTBX_BOOST=simtbx_boost
SIMTBX_PROJ=simtbx_project
NANOBRAGG=${SIMTBX_PROJ}/simtbx/nanoBragg

LIBS="-L${CONDA_PREFIX}/lib"
INCS="-I${CONDA_PREFIX}/lib/${PY}/site-packages -I${SIMTBX_BOOST} -I${CONDA_PREFIX}/include -I ${CONDA_PREFIX}/include/${PY} -I${SIMTBX_PROJ}"
libs="-lboost_python${PYNUM} -lboost_system -lboost_numpy${PYNUM} -lstdc++ -lcctbx -undefined dynamic_lookup"
flags="-O3 -fPIC -std=c++14"

mkdir -p build
mkdir -p ext

targets=""
# update for CUDA?
if [[ $CC == "nvcc" ]]
then
  flags="--compiler-options=-lstdc++,-fPIC,-O3,-DNANOBRAGG_HAVE_CUDA,-DHAVE_NANOBRAGG_SPOTS_CUDA,-DCUDAREAL=double --expt-relaxed-constexpr"
  for sm in 50 52 60 61 70 75 80 86 89 90
  do
    flags="${flags} -gencode arch=compute_${sm},code=sm_${sm}"
  done

  LIBS="$LIBS -L${CUDA_HOME}/lib64"
  libs="$libs -lcudart"

  $CC -c ${NANOBRAGG}/nanoBragg_cuda.cpp $INCS $LIBS $libs $flags -o build/nanoBragg_cuda.o
  $CC -c ${NANOBRAGG}/nanoBraggCUDA.cu $INCS $LIBS $libs $flags -o build/nanoBraggCUDA.o
  targets="${targets} build/nanoBragg_cuda.o build/nanoBraggCUDA.o"
fi

$CC -c ${NANOBRAGG}/nanoBragg.cpp $INCS $LIBS $libs $flags -o build/nanoBragg.o
$CC -c ${NANOBRAGG}/nanoBragg_ext.cpp $INCS $LIBS $libs $flags -o build/nanoBragg_ext.o
targets="${targets} build/nanoBragg.o build/nanoBragg_ext.o"

# link
g++ -shared $targets $LIBS $libs -o ext/simtbx_nanoBragg_ext.so
# for M1 with arm64 conda-packages:
#g++ -arch arm64 -shared $targets $LIBS $libs -o ext/simtbx_nanoBragg_ext.so
#
