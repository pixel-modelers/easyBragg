#!/bin/bash

PYMAJ=$(python -c "import sys;print(sys.version_info[0])")
PYMIN=$(python -c "import sys;print(sys.version_info[1])")
PYNUM=$(echo $PYMAJ$PYMIN)
PY=$(echo python$PYMAJ.$PYMIN)
SIMTBX_BOOST=simtbx_boost
SIMTBX_PROJ=simtbx_project

LIBS="-L${CONDA_PREFIX}/lib"
INCS="-I${CONDA_PREFIX}/lib/${PY}/site-packages -I${SIMTBX_BOOST} -I${CONDA_PREFIX}/include -I ${CONDA_PREFIX}/include/${PY} -I${SIMTBX_PROJ}"
libs="-lboost_python${PYNUM} -lboost_system -lboost_numpy${PYNUM} -lstdc++ -lcctbx"
flags="-O3 -fPIC"

mkdir -p build
mkdir -p ext
g++ -c ${SIMTBX_PROJ}/simtbx/nanoBragg/nanoBragg.cpp $INCS $LIBS $libs $flags -o build/nanoBragg.o
g++ -c ${SIMTBX_PROJ}/simtbx/nanoBragg/nanoBragg_ext.cpp $INCS $LIBS $libs $flags -o build/nanoBragg_ext.o
g++ -shared build/nanoBragg.o build/nanoBragg_ext.o $LIBS $libs -o ext/simtbx_nanoBragg_ext.so

