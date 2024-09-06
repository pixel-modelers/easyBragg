# Only tested so far on cmake version 3.26 
cmake_minimum_required(VERSION 3.2)
project(easyBragg)

set(CMAKE_OSX_ARCHITECTURES "x86_64")
set (CMAKE_CXX_STANDARD 11)

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
    get_filename_component(EZBRAGG ".." REALPATH BASE_DIR "${CMAKE_BINARY_DIR}")
endif()

message(">> EZBRAGG: ${EZBRAGG}")
set(CONDA $ENV{CONDA_PREFIX})
set(PYNUM "${PYMAJ}${PYMIN}")
set(PY "python${PYMAJ}.${PYMIN}")
set(SIMTBX_PROJ "${EZBRAGG}/simtbx_project")
set(NANOBRAGG "${SIMTBX_PROJ}/simtbx/nanoBragg")
message(">> NANOBRAGG FOLDER: ${NANOBRAGG}")
message(">> SIMTBX PROJECT: ${SIMTBX_PROJ}")

cmake_policy(SET CMP0074 NEW)
find_package(CUDAToolkit)
find_library(BOOST_PY REQUIRED NAMES boost_python${PYNUM} HINTS "${CONDA}/lib")
find_library(BOOST_SYS REQUIRED NAMES boost_system HINTS "${CONDA}/lib")
find_library(BOOST_NP REQUIRED NAMES boost_numpy${PYNUM} HINTS "${CONDA}/lib")
set(BOOST_LIBS
    ${BOOST_PY}
    ${BOOST_SYS}
    ${BOOST_NP}
)
message(">> Boost libraries found: ${BOOST_LIBS}")
find_library(CCTBX_LIB REQUIRED NAMES cctbx HINTS "${CONDA}/lib")
find_library(PY_LIB REQUIRED NAMES python${PYMAJ}.${PYMIN} HINTS "${CONDA}/lib")
message(">> CCTBX library found: ${CCTBX_LIB}")
message(">> PYTHON library found: ${PY_LIB}")

set(INCS
  ${SIMTBX_PROJ}
  ${CONDA}/lib/${PY}/site-packages
  ${CONDA}/include
  ${CONDA}/include/${PY}
)

set(LIBS
  ${BOOST_LIBS}
  ${CCTBX_LIB}
  ${PY_LIB}
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

