# Only tested so far on cmake version 3.26 
cmake_minimum_required(VERSION 3.2)
project(easyBragg)


# Get Python version information
execute_process(
  COMMAND python -c "import sys; print(sys.version_info[0])"
  OUTPUT_VARIABLE PYMAJ
  OUTPUT_STRIP_TRAILING_WHITESPACE
)

execute_process(
  COMMAND python -c "import sys; print(sys.version_info[1])"
  OUTPUT_VARIABLE PYMIN
  OUTPUT_STRIP_TRAILING_WHITESPACE
)

# Define variables
# cuda root folder:
if (NOT DEFINED CUDAToolkit_ROOT)
    set(CUDAToolkit_ROOT "/usr/local/cuda")
endif()
# easyBragg github folder:
if (NOT DEFINED EZBRAGG)
    set(EZBRAGG "..")
endif()

set(CONDA $ENV{CONDA_PREFIX})
set(PYNUM "${PYMAJ}${PYMIN}")
set(PY "python${PYMAJ}.${PYMIN}")
set(BOOST_INCLUDEDIR "${EZBRAGG}/simtbx_boost")
set(SIMTBX_PROJ "${EZBRAGG}/simtbx_project")
set(NANOBRAGG "${SIMTBX_PROJ}/simtbx/nanoBragg")
message(">> NANOBRAGG FOLDER: ${NANOBRAGG}")

cmake_policy(SET CMP0074 NEW)
find_package(CUDAToolkit)
find_package(Boost REQUIRED COMPONENTS python${PYNUM} system numpy${PYNUM})
find_library(CCTBX_LIB REQUIRED NAMES cctbx HINTS "${CONDA}/lib")
message(">> CCTBX library found: ${CCTBX_LIB}")

set(INCS
  ${CONDA}/lib/${PY}/site-packages
  ${BOOST_INCLUDEDIR}
  ${CONDA}/include
  ${CONDA}/include/${PY}
  ${SIMTBX_PROJ}
)

set(LIBS
  ${Boost_LIBRARIES}
  ${CCTBX_LIB}
)

add_compile_options(
    "$<$<COMPILE_LANGUAGE:CXX>:-O3;-fPIC>"
)

add_library(nanoBragg OBJECT ${NANOBRAGG}/nanoBragg.cpp)
add_library(nanoBragg_ext OBJECT ${NANOBRAGG}/nanoBragg_ext.cpp)
target_include_directories(nanoBragg PRIVATE ${INCS})
target_include_directories(nanoBragg_ext PRIVATE ${INCS})

# suppress compiler warnings (to see warnings, execute the build.sh script)
add_definitions(-w)

# the python extension module
set(CMAKE_SHARED_LIBRARY_PREFIX "")
add_library(simtbx_nanoBragg_ext SHARED)

if (EXISTS "${CUDAToolkit_NVCC_EXECUTABLE}")
    enable_language(CUDA)
    find_library(CUDART_LIB REQUIRED NAMES cudart HINTS "${CUDAToolkit_LIBRARY_DIR}")
    message(">> CUDART library found: ${CUDART_LIB}")
    set(LIBS 
        ${LIBS}
        ${CUDART_LIB}
    )

    # two new objects for cuda support
    add_library(nanoBraggCUDA OBJECT ${NANOBRAGG}/nanoBraggCUDA.cu)
    add_library(nanoBragg_cuda OBJECT ${NANOBRAGG}/nanoBragg_cuda.cpp)
    target_include_directories(nanoBraggCUDA PRIVATE ${INCS})
    target_include_directories(nanoBragg_cuda PRIVATE ${INCS})
    
    # nvcc options
    target_compile_options(nanoBraggCUDA PRIVATE $<$<COMPILE_LANGUAGE:CUDA>:
        --compiler-options=-lstdc++
        --compiler-options=-O3
        --compiler-options=-fPIC
        --expt-relaxed-constexpr
        >)

    # cuda gencodes:
    set_target_properties(nanoBraggCUDA PROPERTIES CUDA_ARCHITECTURES "50;52;60;61;70;75;80;86;89;90")
    # this silenced a warning .. not sure if its necessary though:
    set_target_properties(simtbx_nanoBragg_ext PROPERTIES CUDA_ARCHITECTURES "50;52;60;61;70;75;80;86;89;90")
    
    # preprocessor macros in nanoBragg to build CUDA
    add_compile_definitions(
        HAVE_NANOBRAGG_SPOTS_CUDA=1
        CUDAREAL=double
        NANOBRAGG_HAVE_CUDA=1
    )

    target_link_libraries(simtbx_nanoBragg_ext nanoBragg nanoBragg_ext nanoBraggCUDA nanoBragg_cuda ${LIBS})
else()
    target_link_libraries(simtbx_nanoBragg_ext nanoBragg nanoBragg_ext ${LIBS})
endif()

