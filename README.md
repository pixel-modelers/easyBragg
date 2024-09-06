# easyBragg
An easy install of simtbx nanoBragg, i.e. [nanoBragg](https://bl831.als.lbl.gov/~jamesh/nanoBragg/) wrappers for python.

# Install for MAC M1

#### Getting mamba

```
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh
bash ./Miniforge3-MacOSX-arm64.sh -b -u -p $PWD/simforge
source simforge/etc/profile.d/conda.sh 
```

#### Create env and Build

```
mamba create -n simtbx -c conda-forge cctbx-base libboost-devel libboost-python-devel dxtbx python=3.9 -y
conda activate simtbx
git clone -b arm64 --recurse-submodules https://github.com/pixel-modelers/easyBragg.git
cd easyBragg
mkdir build
cd build
cmake ..
make
```

# Install for Linux

This has been tested on Debian 12 (bookworm) and SUSE 15.

#### Getting conda

```
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash ./Miniconda3-latest-Linux-x86_64.sh -b -u -p $PWD/simforge
source simforge/etc/profile.d/conda.sh
```

#### Create env and Build

```
conda create -n simtbx conda-forge::cctbx-base python=3.9 -y
conda activate simtbx
conda install conda-forge::dxtbx -y
git clone --recurse-submodules https://github.com/pixel-modelers/easyBragg.git
cd easyBragg
CC=g++ ./build.sh
export PYTHONPATH=$PWD/simtbx_project:$PWD/ext
```

Alternatively, for CUDA builds, if nvcc is available, do 

```
CC=nvcc ./build.sh
```

Note, at each fresh login one should source conda, activate simtbx env, and set `PYTHONPATH`. For that, create an env script:

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

Try ```python example.py``` to display a simulated pattern:

![example](https://smb.slac.stanford.edu/~dermen/noise_img.png)

If you built the CUDA version (by setting `CC=nvcc` for `build.sh` script), then you will see an additional image displayed, showing the CPU and GPU kernel results are identical, but the GPU kernel runs faster (~100x, depending on the number of pixels, oversample-rate, number of mosaic domains, and number of sources):

![example2](https://smb.slac.stanford.edu/~dermen/cpu_vs_gpu.png)

Most of the nanoBragg tests can be run, for example:

```
python simtbx_project/simtbx/nanoBragg/tst_nanoBragg_cbf_write.py
python simtbx_project/simtbx/nanoBragg/tst_gauss_argchk.py GPU
```
