
cmake_minimum_required(VERSION 3.2)
project(easyBragg)

set (CMAKE_CXX_STANDARD 14)

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
set(DIFFBRAGG "${SIMTBX_PROJ}/simtbx/diffBragg/src")
set(EXAFEL "${SIMTBX_PROJ}/simtbx/gpu")
message(">> NANOBRAGG SOURCE FOLDER: ${NANOBRAGG}")
message(">> DIFFBRAGG SOURCE FOLDER: ${DIFFBRAGG}")
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
message(">> CCTBX library found: ${CCTBX_LIB}")

set(INCS
  ${SIMTBX_PROJ}
  ${CONDA}/lib/${PY}/site-packages
  ${CONDA}/include
  ${CONDA}/include/${PY}
  ${EZBRAGG}/eigen
)

if (DEFINED SIMTBX_BOOST)
    set(INCS
      ${INCS}
      ${SIMTBX_BOOST}
    )
endif()

set(LIBS
  ${BOOST_LIBS}
  ${CCTBX_LIB}
)

add_compile_options(
    "$<$<COMPILE_LANGUAGE:CXX>:-O3;-fPIC>"
)



add_library(nanoBragg OBJECT ${NANOBRAGG}/nanoBragg.cpp)
add_library(nanoBragg_ext OBJECT ${NANOBRAGG}/nanoBragg_ext.cpp)
add_library(diffBragg OBJECT ${DIFFBRAGG}/diffBragg.cpp ${DIFFBRAGG}/diffBragg_cpu_kernel.cpp)
add_library(diffBragg_ext OBJECT ${DIFFBRAGG}/diffBragg_ext.cpp)
target_include_directories(nanoBragg PRIVATE ${INCS})
target_include_directories(nanoBragg_ext PRIVATE ${INCS})
target_include_directories(diffBragg PRIVATE ${INCS})
target_include_directories(diffBragg_ext PRIVATE ${INCS})

# suppress compiler warnings (to see warnings, execute the build.sh script)
add_definitions(-w)

# the python extension module
set(CMAKE_SHARED_LIBRARY_PREFIX "")
set(CMAKE_SHARED_LIBRARY_SUFFIX_CXX ".so")
add_library(simtbx_nanoBragg_ext SHARED)
add_library(simtbx_diffBragg_ext SHARED)

if (EXISTS "${CUDAToolkit_NVCC_EXECUTABLE}" AND NOT DEFINED NOCUDA)
    enable_language(CUDA)
    find_library(CUDART_LIB REQUIRED NAMES cudart HINTS "${CUDAToolkit_LIBRARY_DIR}")
    message(">> CUDART library found: ${CUDART_LIB}; Version ${CUDAToolkit_VERSION}")

    set(LIBS 
        ${LIBS}
        ${CUDART_LIB}
    )

    add_library(nanoBraggCUDA OBJECT ${NANOBRAGG}/nanoBraggCUDA.cu)
    add_library(nanoBragg_cuda OBJECT ${NANOBRAGG}/nanoBragg_cuda.cpp)
    target_include_directories(nanoBraggCUDA PRIVATE ${INCS})
    target_include_directories(nanoBragg_cuda PRIVATE ${INCS})
    
    add_library(diffBraggCUDA OBJECT ${DIFFBRAGG}/diffBragg_gpu_kernel.cu ${DIFFBRAGG}/diffBraggCUDA.cu)
    target_include_directories(diffBraggCUDA PRIVATE ${INCS})

    add_library(simtbx_gpu_ext SHARED)
    add_library(exafel_ext OBJECT ${EXAFEL}/gpu_ext.cpp)
    target_include_directories(exafel_ext PRIVATE ${INCS})
    add_library(exafel OBJECT ${EXAFEL}/detector.cu ${EXAFEL}/structure_factors.cu ${EXAFEL}/simulation.cu)
    target_include_directories(exafel PRIVATE ${INCS})
    
    # nvcc options
    math(EXPR cuda_major_diff "${CUDAToolkit_VERSION_MAJOR} - 11")
    math(EXPR cuda_minor_diff "${CUDAToolkit_VERSION_MINOR} - 3")
    message(">> major diff: ${cuda_major_diff}")
    message(">> minor diff: ${cuda_minor_diff}")
    set(GPU_COMP_OPT
        --compiler-options=-lstdc++
        --compiler-options=-O3
        --compiler-options=-fPIC
        --expt-relaxed-constexpr
    )

    if (${cuda_major_diff} EQUAL 0)
      if(NOT ${cuda_minor_diff} LESS 0)
        message(">> USING multi thread nvcc compile")
        set(GPU_COMP_OPT
          ${GPU_COMP_OPT}
          -t 8
        )
      endif()
    elseif(${cuda_major_diff} GREATER 0)
      message(">> USING multi thread nvcc compile")
      set(GPU_COMP_OPT
        ${GPU_COMP_OPT}
        -t 8
      )
    endif()

    target_compile_options(nanoBraggCUDA PRIVATE $<$<COMPILE_LANGUAGE:CUDA>:
        ${GPU_COMP_OPT}
        >)
    
    target_compile_options(diffBraggCUDA PRIVATE $<$<COMPILE_LANGUAGE:CUDA>:
        ${GPU_COMP_OPT}
        >)
    
    target_compile_options(exafel PRIVATE $<$<COMPILE_LANGUAGE:CUDA>:
        ${GPU_COMP_OPT}
        >)

    # cuda gencodes:
    set(ARCH_ALL "50;52;60;61;70;75;80;86;89;90")
    set(ARCH_ATOMIC_DOUBLE "61;70;75;80;86;89;90")
    set_target_properties(nanoBraggCUDA PROPERTIES CUDA_ARCHITECTURES "${ARCH_ALL}")
    set_target_properties(diffBraggCUDA PROPERTIES CUDA_ARCHITECTURES "${ARCH_ATOMIC_DOUBLE}")
    set_target_properties(exafel PROPERTIES CUDA_ARCHITECTURES "${ARCH_ALL}")
    # this silenced a warning .. not sure if its necessary though:
    set_target_properties(simtbx_nanoBragg_ext PROPERTIES CUDA_ARCHITECTURES "${ARCH_ALL}")
    set_target_properties(simtbx_diffBragg_ext PROPERTIES CUDA_ARCHITECTURES "${ARCH_ATOMIC_DOUBLE}")
    set_target_properties(simtbx_gpu_ext PROPERTIES CUDA_ARCHITECTURES "${ARCH_ALL}")
    
    # preprocessor macros in nanoBragg to build CUDA
    add_compile_definitions(
        HAVE_NANOBRAGG_SPOTS_CUDA=1
        CUDAREAL=double
        NANOBRAGG_HAVE_CUDA=1
        DIFFBRAGG_HAVE_CUDA=1
    )

    target_link_libraries(simtbx_nanoBragg_ext nanoBragg nanoBragg_ext nanoBraggCUDA nanoBragg_cuda ${LIBS})
    target_link_libraries(simtbx_diffBragg_ext diffBragg diffBragg_ext diffBraggCUDA ${LIBS})
    target_link_libraries(simtbx_gpu_ext exafel exafel_ext nanoBraggCUDA ${LIBS})
else()
  if (${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
    set(LIBS
      ${LIBS}
      "-undefined dynamic_lookup"
    )
  endif()
  target_link_libraries(simtbx_nanoBragg_ext nanoBragg nanoBragg_ext ${LIBS})
  target_link_libraries(simtbx_diffBragg_ext diffBragg diffBragg_ext ${LIBS})
endif()

set(CMAKE_INSTALL_PREFIX "${EZBRAGG}")
message(">> INSTALL PREFIX: ${CMAKE_INSTALL_PREFIX}")
set(ext_mods 
  simtbx_nanoBragg_ext
  simtbx_diffBragg_ext
)
if(TARGET simtbx_gpu_ext)
  set(ext_mods
    ${ext_mods}
    simtbx_gpu_ext
  )
endif()

install(TARGETS ${ext_mods} DESTINATION ext)
# copy extension module to site-packages
set(PYSITE "${CONDA}/lib/python${PYMAJ}.${PYMIN}/site-packages")
if (IS_DIRECTORY "${PYSITE}")
  message(">> PYTHON SITE PACKAGES: ${PYSITE}")
  install (TARGETS ${ext_mods} DESTINATION ${PYSITE})
endif()

