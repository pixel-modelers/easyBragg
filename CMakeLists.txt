cmake_minimum_required(VERSION 3.1)

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
if (NOT DEFINED CUDAToolkit_ROOT)
    set(CUDAToolkit_ROOT "/usr/local/cuda")
endif()
if (NOT DEFINED EZBRAGG)
    set(EZBRAGG "..")
endif()
if (NOT DEFINED BOOST_INCLUDEDIR)
    set(BOOST_INCLUDEDIR "../simtbx_boost")
endif()

set(CONDA $ENV{CONDA_PREFIX})
set(PYNUM "${PYMAJ}${PYMIN}")
set(PY "python${PYMAJ}.${PYMIN}")
set(SIMTBX_BOOST "${EZBRAGG}/simtbx_boost")
set(SIMTBX_PROJ "${EZBRAGG}/simtbx_project")
set(NANOBRAGG "${SIMTBX_PROJ}/simtbx/nanoBragg")
set(CMAKE_SHARED_LIBRARY_PREFIX "")
message(">> NANOBRAGG FOLDER: ${NANOBRAGG}")

find_package(CUDAToolkit)
find_package(Boost REQUIRED COMPONENTS python${PYNUM} system numpy${PYNUM})
find_library(CCTBX_LIB REQUIRED NAMES cctbx HINTS "${CONDA}/lib")
message(">> CCTBX library found: ${CCTBX_LIB}")

set(INCS
  ${CONDA}/lib/${PY}/site-packages
  ${SIMTBX_BOOST}
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

target_compile_options(nanoBragg PRIVATE $<$<COMPILE_LANGUAGE:CXX>:
    -O3
    -fPIC
    >)
target_compile_options(nanoBragg_ext PRIVATE $<$<COMPILE_LANGUAGE:CXX>:
    -O3
    -fPIC
    >)

# suppress compiler warnings (to see warnings, execute the build.sh script)
add_definitions(-w)

# the python extension module
add_library(simtbx_nanoBragg_ext SHARED)

if (EXISTS "${CUDAToolkit_NVCC_EXECUTABLE}")
    enable_language(CUDA)
    message(STATUS "CMAKE_CUDA_COMPILER = ${CMAKE_CUDA_COMPILER}")
    find_library(CUDART_LIB REQUIRED NAMES cudart HINTS "${CUDAToolkit_LIBRARY_DIR}")
    message(">> CUDART library found: ${CUDART_LIB}")
    set(LIBS 
        ${LIBS}
        ${CUDART_LIB}
    )

    set(codes "")
    set(SMlist 50;52;60;61;70;75;80;86;89;90)
    foreach(sm IN LISTS SMlist) 
      set(codes "${codes}-gencode arch=compute_${sm},code=sm_${sm} ")
    endforeach()
    message(">> gencodes=${codes}")

    # two new objects
    add_library(nanoBraggCUDA OBJECT ${NANOBRAGG}/nanoBraggCUDA.cu)
    add_library(nanoBragg_cuda OBJECT ${NANOBRAGG}/nanoBragg_cuda.cpp)
    # add the includes
    target_include_directories(nanoBraggCUDA PRIVATE ${INCS})
    target_include_directories(nanoBragg_cuda PRIVATE ${INCS})
    
    # nvcc options
    target_compile_options(nanoBraggCUDA PRIVATE $<$<COMPILE_LANGUAGE:CUDA>:
        --compiler-options=-fPIC
        --compiler-options=-lstdc++
        --compiler-options=-O3
        --expt-relaxed-constexpr
        >)
    target_compile_options(nanoBraggCUDA PRIVATE $<$<COMPILE_LANGUAGE:CUDA>:
        --compiler-options=-fPIC
        --compiler-options=-lstdc++
        --compiler-options=-O3
        --expt-relaxed-constexpr
        >)

    target_compile_options(nanoBraggCUDA PRIVATE
      "$<$<COMPILE_LANGUAGE:CUDA>:SHELL:${codes}>"
      )
    
    add_compile_definitions(
        HAVE_NANOBRAGG_SPOTS_CUDA=1
        CUDAREAL=double
        NANOBRAGG_HAVE_CUDA=1
    )

    target_link_libraries(simtbx_nanoBragg_ext nanoBragg nanoBragg_ext nanoBraggCUDA nanoBragg_cuda ${LIBS})
else()
    target_link_libraries(simtbx_nanoBragg_ext nanoBragg nanoBragg_ext ${LIBS})
endif()

#message(INCS: "${INCS}")
#message(LIBS: "${LIBS}")


