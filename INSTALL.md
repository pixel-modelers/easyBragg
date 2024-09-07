# easyBragg

<center>

----
**An east-to-build version of simtbx nanoBragg, i.e. [nanoBragg](https://bl831.als.lbl.gov/~jamesh/nanoBragg/) wrappers for python.**

[Installation instructions](#installing)

[Testing the build](#testing_easybragg)

----

</center>

<a name="installing"></a>
# Install

This has been tested on Debian 12 (bookworm), SUSE 15.4, and Sonoma 14.5 (Apple M1).

### Part 1: Download mamba

##### mamba Linux:

```
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash ./Miniforge3-Linux-x86_64.sh -b -u -p $PWD/simforge
source simforge/etc/profile.d/conda.sh 
```

##### mamba for M1 Mac:

```
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh
bash ./Miniforge3-MacOSX-arm64.sh -b -u -p $PWD/simforge
source simforge/etc/profile.d/conda.sh 
```

Note there is also an x86_64 version of mamba for M1. If you use this, you will need to set a special cmake flag below. 

### Part 2: Get cctbx, dxtbx, and boost headers

```
mamba create -n simtbx -c conda-forge cctbx-base libboost-devel libboost-python-devel dxtbx python=3.9 -y
conda activate simtbx
```

Note, use conda to activate the env.

### Part 3: Download sources and build

Note, build uses `cmake`. If its not already in your path, simply install it with mamba: 

```
mamba install cmake
```

It can also be installed with [homebrew](https://formulae.brew.sh/formula/cmake) if using a Mac. 

For CUDA builders, set up the [typical CUDA env](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html#environment-setup), and ensure nvcc is in your path:

<details>
  <summary>`typical_cuda_setup.sh`</summary>

```
export CUDA_HOME=/usr/local/cuda/
export CUDA_PATH=$CUDA_HOME
export PATH=$PATH:${CUDA_HOME}/bin
export LD_LIBRARY_PATH=${CUDA_HOME}/lib64
```
</details>

Then get the sources and install:

```
git clone --recurse-submodules https://github.com/pixel-modelers/easyBragg.git
cd easyBragg
mkdir build
cd build
cmake ..
make
make install
```

To use the env, for now, use PYTHONPATH

```
export PYTHONPATH=${EASYBRAGG}/simtbx_project:${EASYBRAGG}/ext
```

where `$EASYBRAGG` should be the absolute path to the `easyBragg` repository.

Note, at each fresh login one should activate the simtbx env and set `PYTHONPATH`. For that, create an env script:

<details>
  <summary>`setup_ezbragg.sh`</summary>

```
SIMFORGE=/path/to/simforge
EASYBRAGG=/path/to/easyBragg
source $SIMFORGE/etc/profile.d/conda.sh
conda activate simtbx
export PYTHONPATH=${EASYBRAGG}/simtbx_project:${EASYBRAGG}/ext
```

Hence, at login run `source /path/to/setup_ezbragg.sh`.

</details>

### Install notes

If dependency resolution is slow (this is more likely to happen when using conda as opposed to mamba), try installing in steps:

```
conda create -n conda-forge::cctbx-base python=3.9 -y
conda install conda-forge::dxtbx -y
```

One can also try using the cctbx/boost headers provided as a submodule in this repo as oppposed to conda-installing the `libboost-devel` and `libboost-python-devel` packages. If so, one only needs the conda packages `cctbx-base` and `dxtbx`. Then, at the cmake step, do 

```
cmake -DSIMTBX_BOOST=$PWD/../simtbx_boost ..
```

Note, the `simtbx_boost` submodule is currently linked to version 1.84.

For folks using the x86_64 conda packages on an M1 mac, try

```
cmake -DCMAKE_OSX_ARCHITECTURES=x86_64 ..
```

<a name="testing_easybragg"></a>
### Testing the build


Try ```python example.py``` to display a simulated pattern:

![example](https://smb.slac.stanford.edu/~dermen/noise_img.png)

If you ran cmake in a CUDA environment, then you will see an additional image displayed, showing the CPU and GPU kernel results are identical, but the GPU kernel runs faster (~100x, depending on the number of pixels, oversample-rate, number of mosaic domains, and number of sources):

![example2](https://smb.slac.stanford.edu/~dermen/cpu_vs_gpu.png)

Most of the nanoBragg tests can be run, for example:

```
python simtbx_project/simtbx/nanoBragg/tst_nanoBragg_cbf_write.py
python simtbx_project/simtbx/nanoBragg/tst_gauss_argchk.py GPU
```
